"""数据清洗服务

对1688原始数据进行清洗、去重、归一化。
"""
import re
import hashlib
from typing import List, Set
from backend.crawlers.crawler_1688 import RawProduct


class DataCleaner:
    """1688原始数据清洗器"""

    def __init__(self):
        self._seen_ids: Set[str] = set()

    def clean(self, raw_products: List[RawProduct]) -> List[RawProduct]:
        """清洗管道：去重 → 价格归一化 → 标题清洗 → 重量默认值"""
        products = self._deduplicate(raw_products)
        products = [self._normalize(p) for p in products]
        products = [p for p in products if self._is_valid(p)]
        return products

    def _deduplicate(self, products: List[RawProduct]) -> List[RawProduct]:
        """按 source_id 去重"""
        seen = set()
        result = []
        for p in products:
            if p.source_id and p.source_id not in seen:
                seen.add(p.source_id)
                result.append(p)
        return result

    def _normalize(self, p: RawProduct) -> RawProduct:
        """数据归一化"""
        # 价格：限制在合理范围
        if p.purchase_price_rmb <= 0 or p.purchase_price_rmb > 1000:
            p.purchase_price_rmb = 0.0

        # 标题清洗：去HTML、去多余空格
        p.title_zh = re.sub(r"<[^>]+>", "", p.title_zh)
        p.title_zh = re.sub(r"\s+", " ", p.title_zh).strip()

        # 重量默认：如果没有抓到重量，按中位数预估 0.3kg
        if p.actual_weight_kg <= 0:
            p.actual_weight_kg = 0.3

        # 尺寸默认
        if p.length_cm <= 0:
            p.length_cm = 15.0
        if p.width_cm <= 0:
            p.width_cm = 10.0
        if p.height_cm <= 0:
            p.height_cm = 5.0

        return p

    def _is_valid(self, p: RawProduct) -> bool:
        """基础有效性校验"""
        if not p.title_zh or len(p.title_zh) < 3:
            return False
        if not p.source_id:
            return False
        return True


class HardFilter:
    """硬性约束过滤器"""

    def __init__(self, max_price: float = 25.0, min_price: float = 12.0,
                 max_weight: float = 2.0, min_weight: float = 0.1,
                 min_years: float = 1.0, max_delivery: int = 48):
        self.max_price = max_price
        self.min_price = min_price
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.min_years = min_years
        self.max_delivery = max_delivery

    def apply(self, products: List[RawProduct]) -> List[RawProduct]:
        """逐层过滤"""
        passed = []

        for p in products:
            # 价格区间
            if p.purchase_price_rmb < self.min_price or p.purchase_price_rmb > self.max_price:
                continue

            # 重量区间（如果有数据）
            if p.actual_weight_kg > 0:
                if p.actual_weight_kg < self.min_weight or p.actual_weight_kg > self.max_weight:
                    continue

            # 店铺年限
            if p.store_years_active > 0 and p.store_years_active < self.min_years:
                continue

            # 发货时效
            if p.store_delivery_hours > self.max_delivery:
                continue

            # 体积粗筛（单边不超过60cm）
            if p.length_cm > 60 or p.width_cm > 60 or p.height_cm > 60:
                continue

            passed.append(p)

        return passed
