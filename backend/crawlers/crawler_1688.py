"""1688 商品数据采集器

采集流程：
1. 根据关键词搜索商品列表
2. 进入详情页提取规格参数
3. 提取店铺信息
"""
import asyncio
import logging
import re
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from urllib.parse import quote

from backend.crawlers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


@dataclass
class RawProduct:
    """1688原始商品数据"""
    source_id: str = ""
    title_zh: str = ""
    image_url: str = ""
    source_url: str = ""
    purchase_price_rmb: float = 0.0
    actual_weight_kg: float = 0.0
    length_cm: float = 0.0
    width_cm: float = 0.0
    height_cm: float = 0.0
    store_name: str = ""
    store_years_active: float = 0.0
    store_rating: float = 0.0
    store_delivery_hours: int = 72
    sales_volume: int = 0
    supports_dropshipping: bool = False
    category: str = ""
    raw_spec_text: str = ""


class Alibaba1688Crawler(BaseCrawler):
    """1688商品采集器"""

    SEARCH_URL = "https://s.1688.com/selloffer/offer_search.htm"
    DETAIL_URL = "https://detail.1688.com/offer/{}.html"

    def __init__(self):
        super().__init__(name="1688")

    async def search_products(
        self, keyword: str, page_count: int = None
    ) -> List[RawProduct]:
        """搜索商品并返回原始数据列表"""
        pages = page_count or settings.search_pages_per_keyword
        products: List[RawProduct] = []

        context = await self.new_context()
        page = await context.new_page()

        for p in range(pages):
            try:
                url = f"{self.SEARCH_URL}?keywords={quote(keyword)}&page={p+1}"
                await self.safe_goto(page, url)
                await self._scroll_page(page)

                items = await page.query_selector_all(".offer-list-item, .offer-item")
                for item in items:
                    try:
                        raw = await self._parse_search_item(item)
                        if raw and raw.title_zh:
                            products.append(raw)
                    except Exception as e:
                        logger.debug(f"parse item error: {e}")
                        continue

                await self.random_delay()
            except Exception as e:
                logger.warning(f"Search page {p+1} for '{keyword}' failed: {e}")
                break

        await context.close()
        return products

    async def _parse_search_item(self, item) -> Optional[RawProduct]:
        """解析搜索结果单项"""
        raw = RawProduct()

        # 标题
        title_el = await item.query_selector(".offer-title, .title")
        if title_el:
            raw.title_zh = (await title_el.inner_text()).strip()

        # 价格
        price_el = await item.query_selector(".price, .offer-price")
        if price_el:
            price_text = (await price_el.inner_text()).strip()
            nums = re.findall(r"[\d.]+", price_text)
            if nums:
                raw.purchase_price_rmb = float(nums[0])

        # 链接
        link_el = await item.query_selector("a[href]")
        if link_el:
            href = await link_el.get_attribute("href")
            raw.source_url = href if href else ""
            # 提取商品ID
            offer_id = re.search(r"offer/(\d+)", raw.source_url)
            if offer_id:
                raw.source_id = offer_id.group(1)

        # 图片
        img_el = await item.query_selector("img")
        if img_el:
            raw.image_url = (await img_el.get_attribute("src")) or ""

        # 销量
        sales_el = await item.query_selector(".sale-count, .offer-sale")
        if sales_el:
            sales_text = (await sales_el.inner_text()).strip()
            nums = re.findall(r"(\d+)", sales_text)
            if nums:
                raw.sales_volume = int(nums[0])

        return raw if raw.source_id else None

    async def get_product_detail(self, offer_id: str) -> Optional[RawProduct]:
        """获取商品详情（重量、尺寸、材质）"""
        context = await self.new_context()
        page = await context.new_page()

        try:
            url = self.DETAIL_URL.format(offer_id)
            await self.safe_goto(page, url)
            await self.random_delay()

            raw = RawProduct(source_id=offer_id, source_url=url)

            # 标题
            raw.title_zh = await self.safe_text(page, "h1", "")

            # 价格区间
            price_text = await self.safe_text(page, ".price", "")
            nums = re.findall(r"[\d.]+", price_text)
            if nums:
                raw.purchase_price_rmb = float(nums[0])

            # 规格参数 - 尝试提取重量和尺寸
            spec_text = await page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('.mod-detail-attributes tr, .sku-item');
                    return Array.from(rows).map(r => r.innerText).join('|');
                }
            """)
            raw.raw_spec_text = spec_text

            # 解析重量 (克/kg)
            weight_match = re.search(r"(?:重量|净重|毛重)[：:\s]*(\d+[.]?\d*)\s*(kg|克|g|千克)", spec_text, re.I)
            if weight_match:
                w = float(weight_match.group(1))
                unit = weight_match.group(2).lower()
                raw.actual_weight_kg = w if "k" in unit else w / 1000

            # 解析尺寸
            dim_match = re.search(r"(?:尺寸|规格)[：:\s]*(\d+[.]?\d*)[×xX*](\d+[.]?\d*)[×xX*](\d+[.]?\d*)", spec_text)
            if dim_match:
                raw.length_cm = float(dim_match.group(1))
                raw.width_cm = float(dim_match.group(2))
                raw.height_cm = float(dim_match.group(3))

            # 店铺信息
            raw.store_name = await self.safe_text(page, ".company-name, .shop-name", "")

            return raw
        except Exception as e:
            logger.warning(f"Detail page {offer_id} failed: {e}")
            return None
        finally:
            await context.close()

    async def get_store_info(self, store_url: str) -> Dict:
        """获取店铺信息（年限、评分、发货时效）"""
        context = await self.new_context()
        page = await context.new_page()

        info = {
            "years_active": 0.0,
            "rating": 0.0,
            "delivery_hours": 72,
            "dropshipping": False,
        }

        try:
            await self.safe_goto(page, store_url)
            await self.random_delay()

            # 店铺年限
            year_text = await self.safe_text(page, ".shop-year, .biz-year", "")
            years = re.findall(r"(\d+)", year_text)
            if years:
                info["years_active"] = float(years[0])

            # 评分
            rating_text = await self.safe_text(page, ".shop-rating, .score", "")
            ratings = re.findall(r"([\d.]+)", rating_text)
            if ratings:
                info["rating"] = float(ratings[0])

            # 发货时效
            delivery_text = await page.evaluate("""
                () => document.body.innerText.match(/(\\d+)\\s*(?:小时|h|H)/)
            """)
            if delivery_text:
                info["delivery_hours"] = int(delivery_text[1])

        except Exception as e:
            logger.warning(f"Store info failed: {e}")
        finally:
            await context.close()

        return info

    async def _scroll_page(self, page, times: int = 3):
        """模拟滚动"""
        for _ in range(times):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
            await asyncio.sleep(0.5)
