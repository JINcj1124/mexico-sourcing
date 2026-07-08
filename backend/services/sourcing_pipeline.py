"""每日选品主流程编排

9阶段流水线：节日权重 → 关键词生成 → 1688采集 → 清洗去重 →
硬约束过滤 → 竞品比价 → 物流计算 → 利润过滤 → 评分排序 → Top-20输出
"""
import asyncio
import logging
from datetime import date, datetime
from typing import List

from backend.config import settings
from backend.models.database import SessionLocal
from backend.models.product import Product
from backend.models.daily_result import DailyResult, CrawlerLog
from backend.crawlers.crawler_1688 import Alibaba1688Crawler, RawProduct
from backend.crawlers.crawler_temu import TemuMXCrawler
from backend.crawlers.crawler_shopee import ShopeeMXCrawler
from backend.algorithms.logistics import LogisticsCalculator, ProductSpecs
from backend.algorithms.pricing import PricingEngine, CompetitorPrice
from backend.algorithms.festival_weighter import FestivalWeighter
from backend.algorithms.scoring import ProductScorer, ScoredProduct
from backend.services.data_cleaner import DataCleaner, HardFilter
from backend.services.keyword_generator import KeywordGenerator
from backend.services.output_service import OutputService
from backend.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class SourcingPipeline:
    """每日选品全流程"""

    def __init__(self):
        self.festival_weighter = FestivalWeighter()
        self.keyword_generator = KeywordGenerator(self.festival_weighter)
        self.crawler_1688 = Alibaba1688Crawler()
        self.crawler_temu = TemuMXCrawler()
        self.crawler_shopee = ShopeeMXCrawler()
        self.data_cleaner = DataCleaner()
        self.hard_filter = HardFilter(
            max_price=settings.max_purchase_price,
            min_price=settings.min_purchase_price,
            max_weight=settings.max_weight_kg,
        )
        self.logistics_calc = LogisticsCalculator()
        self.pricing_engine = PricingEngine()
        self.scorer = ProductScorer()
        self.output_service = OutputService()
        self.webhook_service = WebhookService()

    async def run(self, target_date: date = None):
        """执行完整选品流程"""
        today = target_date or date.today()
        logger.info(f"=== Sourcing Pipeline START for {today.isoformat()} ===")

        # === Step 1: 节日权重 ===
        active_festivals = self.festival_weighter.get_active_festivals(today)
        category_weights = self.festival_weighter.get_festival_categories(today)
        logger.info(f"[1/9] Active festivals: {[f['name_zh'] for f in active_festivals]}")

        # === Step 2: 关键词 ===
        keywords_zh = self.keyword_generator.generate(today)
        logger.info(f"[2/9] Keywords: {len(keywords_zh)} total")

        # === Step 3: 1688采集 ===
        all_raw: List[RawProduct] = []
        await self.crawler_1688.start()
        try:
            for kw in keywords_zh[:20]:  # 限制并发量
                try:
                    raw_list = await self.crawler_1688.search_products(kw, page_count=2)
                    all_raw.extend(raw_list)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Keyword '{kw}' search failed: {e}")
        finally:
            await self.crawler_1688.close()

        logger.info(f"[3/9] Collected {len(all_raw)} raw products from 1688")

        # === Step 4: 清洗去重 ===
        cleaned = self.data_cleaner.clean(all_raw)
        logger.info(f"[4/9] After cleaning: {len(cleaned)} products")

        # === Step 5: 硬约束过滤 ===
        filtered = self.hard_filter.apply(cleaned)
        logger.info(f"[5/9] After hard filter: {len(filtered)} products")

        if len(filtered) == 0:
            logger.warning("No products passed hard filters!")
            return []

        # === Step 6: 竞品比价 ===
        keywords_es = self.keyword_generator.generate_es(today)[:5]
        competitor_data = {}

        await self.crawler_temu.start()
        await self.crawler_shopee.start()
        try:
            for kw_es in keywords_es:
                try:
                    temu_items = await self.crawler_temu.search(kw_es, max_items=5)
                    for item in temu_items:
                        key = self._normalize_key(item.title)
                        if key not in competitor_data:
                            competitor_data[key] = {"temu": [], "shopee": []}
                        competitor_data[key]["temu"].append(item)
                except Exception as e:
                    logger.warning(f"Temu search '{kw_es}' failed: {e}")

                try:
                    shopee_items = await self.crawler_shopee.search(kw_es, max_items=5)
                    for item in shopee_items:
                        key = self._normalize_key(item.title)
                        if key not in competitor_data:
                            competitor_data[key] = {"temu": [], "shopee": []}
                        competitor_data[key]["shopee"].append(item)
                except Exception as e:
                    logger.warning(f"Shopee search '{kw_es}' failed: {e}")
        finally:
            await self.crawler_temu.close()
            await self.crawler_shopee.close()

        logger.info(f"[6/9] Competitor data: {len(competitor_data)} title groups")

        # === Step 7-8: 物流计算 + 定价 + 评分 ===
        scored_results = []
        for raw in filtered:
            # 物流计算
            specs = ProductSpecs(
                actual_weight_kg=raw.actual_weight_kg,
                length_cm=raw.length_cm,
                width_cm=raw.width_cm,
                height_cm=raw.height_cm,
                purchase_price_rmb=raw.purchase_price_rmb,
            )
            logistics = self.logistics_calc.evaluate(specs)
            if logistics.is_overweight or logistics.is_oversized:
                continue

            # 竞品匹配（简单字符串相似度）
            competitors = self._match_competitors(raw.title_zh, competitor_data)

            # 定价
            pricing = self.pricing_engine.evaluate(
                raw.purchase_price_rmb, logistics.total_cost_rmb, competitors
            )
            if not pricing.is_viable:
                continue

            # 节日匹配分
            festival_score = category_weights.get(raw.category, 1.0) / 3.0

            # 综合评分
            scored = ScoredProduct(
                estimated_margin=pricing.estimated_margin,
                competitor_count=len(competitors),
                festival_match_score=festival_score,
                store_years_active=raw.store_years_active,
                store_rating=raw.store_rating,
                store_delivery_hours=raw.store_delivery_hours,
            )
            score = self.scorer.score(scored)

            # 保存到数据库
            db = SessionLocal()
            try:
                product = Product(
                    source_id=raw.source_id,
                    title_zh=raw.title_zh,
                    category=raw.category,
                    image_url=raw.image_url,
                    source_url=raw.source_url,
                    purchase_price_rmb=raw.purchase_price_rmb,
                    actual_weight_kg=raw.actual_weight_kg,
                    length_cm=raw.length_cm,
                    width_cm=raw.width_cm,
                    height_cm=raw.height_cm,
                    store_name=raw.store_name,
                    store_years_active=raw.store_years_active,
                    store_rating=raw.store_rating,
                    store_delivery_hours=raw.store_delivery_hours,
                    sales_volume=raw.sales_volume,
                    supports_dropshipping=raw.supports_dropshipping,
                    volumetric_weight_kg=logistics.volumetric_weight_kg,
                    chargeable_weight_kg=logistics.chargeable_weight_kg,
                    air_freight_rmb=logistics.air_freight_rmb,
                    total_cost_rmb=logistics.total_cost_rmb,
                    suggested_price_rmb=pricing.suggested_price_rmb,
                    suggested_price_mxn=pricing.suggested_price_mxn,
                    markup_ratio=pricing.markup_ratio,
                    estimated_margin=pricing.estimated_margin,
                    temu_mx_lowest_mxn=next((c.price_mxn for c in competitors if c.platform == "temu_mx"), None),
                    shopee_mx_lowest_mxn=next((c.price_mxn for c in competitors if c.platform == "shopee_mx"), None),
                    competitor_count=len(competitors),
                    score=score,
                    festival_match_score=festival_score,
                    reason_primary=pricing.reason,
                    reason_details=pricing.competitor_reference,
                    festival_relevance=", ".join(f["name_zh"] for f in active_festivals[:2]) if active_festivals else "",
                )
                db.add(product)
                db.commit()
                db.refresh(product)

                scored_results.append((product, score, pricing, logistics))
            except Exception as e:
                db.rollback()
                logger.error(f"DB insert error: {e}")
            finally:
                db.close()

        logger.info(f"[7-8/9] Viable products after pricing+scoring: {len(scored_results)}")

        # === Step 9: 取Top-20 + 输出 ===
        scored_results.sort(key=lambda x: x[1], reverse=True)
        top_n = min(settings.target_sku_count, len(scored_results))
        top_products = scored_results[:top_n]

        # 构建输出
        product_dicts = []
        for rank, (prod, score, pricing, logistics) in enumerate(top_products, 1):
            # 标记为选中
            db = SessionLocal()
            try:
                p = db.query(Product).filter(Product.id == prod.id).first()
                if p:
                    p.is_selected = True
                    p.selection_date = today
                    db.commit()
            finally:
                db.close()

            d = self.output_service.build_product_dict(prod, rank)
            d["score"] = score
            if pricing.price_advantage:
                d["competition"]["price_advantage"] = pricing.price_advantage
            product_dicts.append(d)

        # 统计
        avg_margin = sum(p["pricing"]["estimated_margin"] for p in product_dicts) / len(product_dicts) if product_dicts else 0
        avg_price_mxn = sum(p["pricing"]["suggested_price_mxn"] for p in product_dicts) / len(product_dicts) if product_dicts else 0
        stats = {
            "total_candidates": len(all_raw),
            "selected_count": len(product_dicts),
            "avg_margin": round(avg_margin, 4),
            "avg_price_mxn": round(avg_price_mxn, 2),
        }

        # 保存每日结果
        db = SessionLocal()
        try:
            daily = DailyResult(
                date=today.isoformat(),
                total_candidates=len(all_raw),
                selected_count=len(product_dicts),
                avg_margin=stats["avg_margin"],
                avg_price_mxn=stats["avg_price_mxn"],
                active_festivals=active_festivals,
                products_json=product_dicts,
            )
            db.add(daily)
            db.commit()
        finally:
            db.close()

        # 输出文件
        json_path = self.output_service.to_daily_json(product_dicts, today, active_festivals, stats)
        excel_path = self.output_service.to_excel(product_dicts, today)

        # Webhook 推送
        await self.webhook_service.push_daily_report(product_dicts, today, stats, active_festivals)

        logger.info(f"[9/9] DONE! Top-{len(product_dicts)} selected. JSON: {json_path}, Excel: {excel_path}")
        return product_dicts

    def _normalize_key(self, title: str) -> str:
        """简单文本归一化用于竞品匹配"""
        import re
        return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "", title.lower())[:30]

    def _match_competitors(self, title_zh: str, competitor_data: dict) -> List[CompetitorPrice]:
        """根据商品标题匹配竞品数据"""
        results = []
        norm_title = self._normalize_key(title_zh)

        for key, data in competitor_data.items():
            # 简单关键词重叠匹配
            if any(word in key for word in norm_title[:10]) or any(word in norm_title for word in key[:10]):
                for item in data.get("temu", []):
                    results.append(CompetitorPrice(
                        platform="temu_mx",
                        price_mxn=item.price_mxn,
                        price_rmb=self.pricing_engine.mxn_to_rmb_price(item.price_mxn),
                        title=item.title,
                        url=item.url,
                    ))
                for item in data.get("shopee", []):
                    results.append(CompetitorPrice(
                        platform="shopee_mx",
                        price_mxn=item.price_mxn,
                        price_rmb=self.pricing_engine.mxn_to_rmb_price(item.price_mxn),
                        title=item.title,
                        url=item.url,
                    ))

        return results
