"""Temu 墨西哥站比价爬虫"""
import asyncio
import logging
from typing import List
from dataclasses import dataclass

from backend.crawlers.base_crawler import BaseCrawler
from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TemuItem:
    title: str = ""
    price_mxn: float = 0.0
    url: str = ""
    sales_text: str = ""


class TemuMXCrawler(BaseCrawler):
    """Temu 墨西哥站价格采集"""

    BASE_URL = "https://www.temu.com/mx"

    def __init__(self):
        super().__init__(name="temu_mx")

    async def search(self, keyword_es: str, max_items: int = 10) -> List[TemuItem]:
        """搜索 Temu 墨西哥站商品"""
        items: List[TemuItem] = []
        context = await self.new_context()
        page = await context.new_page()

        try:
            search_url = f"{self.BASE_URL}/search_result.html?search_key={keyword_es}"
            await self.safe_goto(page, search_url)
            await self.random_delay()
            await self._scroll(page)

            # 解析商品卡片
            cards = await page.query_selector_all("[data-testid='product-item'], .product-card")
            for card in cards[:max_items]:
                try:
                    item = TemuItem()
                    title_el = await card.query_selector(".product-title, .title")
                    if title_el:
                        item.title = (await title_el.inner_text()).strip()

                    price_el = await card.query_selector(".price, .current-price")
                    if price_el:
                        price_text = (await price_el.inner_text()).strip()
                        import re
                        nums = re.findall(r"[\d.,]+", price_text)
                        if nums:
                            item.price_mxn = float(nums[0].replace(",", ""))

                    link_el = await card.query_selector("a[href]")
                    if link_el:
                        href = await link_el.get_attribute("href")
                        item.url = f"{self.BASE_URL}{href}" if href and href.startswith("/") else (href or "")

                    items.append(item)
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Temu search '{keyword_es}' failed: {e}")
        finally:
            await context.close()

        return items

    async def _scroll(self, page, times: int = 3):
        for _ in range(times):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(0.5)
