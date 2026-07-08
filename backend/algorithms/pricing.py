"""定价对标引擎

实现"比价引流，薄利多销"定价策略：
1. 默认售价 = 进货价 × 6
2. 比对 Temu/Shopee 墨西哥站同款，售价必须低于竞品
3. 扣除佣金后必须保本
"""
from dataclasses import dataclass, field
from typing import List, Tuple
from backend.config import settings


@dataclass
class CompetitorPrice:
    """竞品价格记录"""
    platform: str           # "temu_mx" | "shopee_mx"
    price_mxn: float        # 墨西哥比索价格
    price_rmb: float        # 换算后人民币
    title: str = ""
    url: str = ""
    sales_volume: int = 0


@dataclass
class PricingResult:
    """定价决策结果"""
    suggested_price_rmb: float = 0.0
    suggested_price_mxn: float = 0.0
    markup_ratio: float = 0.0
    estimated_margin: float = 0.0
    is_viable: bool = False
    reason: str = ""
    competitor_reference: str = ""
    price_advantage: str = ""


class PricingEngine:
    """定价对标引擎"""

    def __init__(self, mxn_rate: float = None):
        self.mxn_to_rmb = mxn_rate or settings.mxn_to_rmb
        self.min_markup = settings.min_markup
        self.commission_rate = settings.commission_rate

    def rmb_to_mxn(self, price_rmb: float) -> float:
        return round(price_rmb / self.mxn_to_rmb, 2) if self.mxn_to_rmb > 0 else 0.0

    def mxn_to_rmb_price(self, price_mxn: float) -> float:
        return round(price_mxn * self.mxn_to_rmb, 2)

    def calc_base_suggested(self, purchase_price: float) -> float:
        """基准建议售价 = 进货价 × 最低溢价倍率"""
        return round(purchase_price * self.min_markup, 2)

    def get_competitor_min(self, competitors: List[CompetitorPrice]) -> float:
        """竞品最低价 (RMB)，无竞品返回 inf"""
        if not competitors:
            return float("inf")
        return min(c.price_rmb for c in competitors)

    def calc_margin(self, sell_price: float, total_cost: float) -> float:
        """毛利率 = (售价 - 售价×佣金 - 总成本) / 售价"""
        if sell_price <= 0:
            return 0.0
        net_revenue = sell_price * (1 - self.commission_rate)
        return (net_revenue - total_cost) / sell_price

    def evaluate(
        self,
        purchase_price: float,
        total_cost_rmb: float,
        competitors: List[CompetitorPrice],
    ) -> PricingResult:
        """
        定价评估核心方法

        规则:
        1. 默认售价 = 进货价 × 6
        2. 若竞品价更低 → 售价调整到比竞品低1元（仍需保本）
        3. 若无法保本 → 淘汰
        """
        result = PricingResult()

        base_price = self.calc_base_suggested(purchase_price)

        # 扣除佣金后必须保本的最低售价
        min_viable = total_cost_rmb / (1 - self.commission_rate)

        comp_min = self.get_competitor_min(competitors)

        # 决策逻辑
        if base_price < min_viable:
            # 6倍溢价仍然不保本 → 淘汰
            result.reason = f"6倍溢价售价¥{base_price}仍低于保本价¥{min_viable:.2f}"
            return result

        if comp_min != float("inf") and base_price >= comp_min:
            # 竞品更低 → 尝试调整
            target_price = comp_min - 1.0  # 比竞品低1元
            if target_price > min_viable:
                result.suggested_price_rmb = round(target_price, 2)
                result.reason = f"价格对标：低于竞品最低¥{comp_min}，调整至¥{target_price}"
                result.price_advantage = f"低于竞品¥{comp_min - target_price:.0f}"
            else:
                result.reason = f"调整至竞品价以下¥{target_price}无法保本（底线¥{min_viable:.2f}）"
                return result
        else:
            result.suggested_price_rmb = base_price
            if comp_min == float("inf"):
                result.reason = "无直接竞品，按6倍溢价定价"
                result.price_advantage = "无竞品"
            else:
                result.reason = f"6倍溢价¥{base_price}已低于竞品最低¥{comp_min}"
                result.price_advantage = f"低于竞品¥{comp_min - base_price:.0f}"

        # 填充结果
        result.suggested_price_mxn = self.rmb_to_mxn(result.suggested_price_rmb)
        result.markup_ratio = round(result.suggested_price_rmb / purchase_price, 2) if purchase_price > 0 else 0
        result.estimated_margin = round(self.calc_margin(result.suggested_price_rmb, total_cost_rmb), 4)
        result.is_viable = True

        if competitors:
            result.competitor_reference = f"Temu: ${competitors[0].price_mxn:.0f} MXN" if competitors else ""

        return result
