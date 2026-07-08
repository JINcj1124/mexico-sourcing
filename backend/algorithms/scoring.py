"""综合评分排序算法

五维加权评分（优质选品导向）：
- 利润率 20%
- 销量验证 20%     ← 新增：真实市场验证
- 竞争度 20%
- 节日匹配 20%
- 店铺信誉 20%     ← 含评价
"""
from dataclasses import dataclass
from typing import List


@dataclass
class ScoredProduct:
    """待评分商品"""
    estimated_margin: float = 0.0
    sales_volume: int = 0
    competitor_count: int = 0
    festival_match_score: float = 0.0
    store_years_active: float = 0.0
    store_rating: float = 0.0
    store_delivery_hours: int = 72


class ProductScorer:
    """五维加权评分器"""

    WEIGHTS = {
        "profit_margin": 0.20,
        "sales_volume": 0.20,
        "competition": 0.20,
        "festival_match": 0.20,
        "store_reputation": 0.20,
    }

    def score(self, product: ScoredProduct) -> float:
        """综合评分 0-100"""
        scores = {
            "profit_margin": self._score_profit(product),
            "sales_volume": self._score_sales(product),
            "competition": self._score_competition(product),
            "festival_match": self._score_festival(product),
            "store_reputation": self._score_store(product),
        }
        total = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        return round(total, 2)

    def _score_profit(self, p: ScoredProduct) -> float:
        """利润率评分：20%以上满分"""
        return min(p.estimated_margin / 0.30 * 100, 100)

    def _score_sales(self, p: ScoredProduct) -> float:
        """销量验证：1000以上满分，验证市场真实需求"""
        if p.sales_volume >= 5000:
            return 100.0
        if p.sales_volume >= 1000:
            return 70 + (p.sales_volume - 1000) / 4000 * 30
        if p.sales_volume >= 100:
            return 30 + (p.sales_volume - 100) / 900 * 40
        return max(0, p.sales_volume / 100 * 30)

    def _score_competition(self, p: ScoredProduct) -> float:
        """竞争度评分：无竞品满分，每个竞品-15分"""
        if p.competitor_count == 0:
            return 100.0
        return max(0, 100 - p.competitor_count * 15)

    def _score_festival(self, p: ScoredProduct) -> float:
        """节日匹配度"""
        return min(p.festival_match_score * 100, 100)

    def _score_store(self, p: ScoredProduct) -> float:
        """店铺信誉：
        - 年限：3年以上满分40
        - 评价：4.8以上满分40
        - 发货时效：24h内满分20
        """
        year_score = min(p.store_years_active / 3 * 40, 40)
        rating_score = min(p.store_rating / 5.0 * 40, 40) if p.store_rating > 0 else 20
        delivery_score = max(0, 20 - max(0, p.store_delivery_hours - 24) * 0.4)
        return min(year_score + rating_score + delivery_score, 100)

    def rank(self, products: List[ScoredProduct]) -> List[ScoredProduct]:
        """排序并返回（降序）"""
        scored = [(p, self.score(p)) for p in products]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in scored]
