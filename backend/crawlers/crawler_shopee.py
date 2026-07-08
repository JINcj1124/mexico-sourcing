"""Shopee 墨西哥站比价爬虫"""
import asyncio
import logging
from typing import List
from dataclasses import dataclass

from backend.crawlers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


@dataclass
class ShopeeItem:
    title: str = ""
    price_mxn: float = 0.0
    url: str = ""
    sold_count: int = 0


class ShopeeMXCrawler(BaseCrawler):
    """Shopee 墨西哥站价格采集"""

    BASE_URL = "https://shopee.com.mx"

    def __init__(self):
        super().__init__(name="shopee_mx")

    async def search(self, keyword_es: str, max_items: int = 10) -> List[ShopeeItem]:
        """搜索 Shopee 墨西哥站商品"""
        items: List[ShopeeItem] = []
        context = await self.new_context()
        page = await context.new_page()

        try:
            from urllib.parse import quote
            search_url = f"{self.BASE_URL}/search?keyword={quote(keyword_es)}"
            await self.safe_goto(page, search_url)
            await self.random_delay()
            await self._scroll(page)

            cards = await page.query_selector_all(".shopee-search-item-result__item")
            for card in cards[:max_items]:
                try:
                    item = ShopeeItem()
                    title_el = await card.query_selector(".shopee-item-card__text-name")
                    if title_el:
                        item.title = (await title_el.inner_text()).strip()

                    price_el = await card.query_selector(".shopee-item-card__current-price")
                    if price_el:
                        price_text = (await price_el.inner_text()).strip()
                        import re
                        nums = re.findall(r"[\d.,]+", price_text)
                        if nums:
                            item.price_mxn = float(nums[0].replace(",", ""))

                    link_el = await card.query_selector("a[href]")
                    if link_el:
                        item.url = (await link_el.get_attribute("href")) or ""

                    items.append(item)
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Shopee search '{keyword_es}' failed: {e}")
        finally:
            await context.close()

        return items

    async def _scroll(self, page, times: int = 3):
        for _ in range(times):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(0.5)
