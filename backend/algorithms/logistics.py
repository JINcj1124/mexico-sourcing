"""物流运费计算模型

空运跨境物流成本计算，包含体积重、计费重、空运费及全链成本。
"""
from dataclasses import dataclass, field
from backend.config import settings


@dataclass
class ProductSpecs:
    """商品规格输入"""
    actual_weight_kg: float
    length_cm: float
    width_cm: float
    height_cm: float
    purchase_price_rmb: float


@dataclass
class LogisticsResult:
    """物流计算结果"""
    volumetric_weight_kg: float = 0.0
    chargeable_weight_kg: float = 0.0
    air_freight_rmb: float = 0.0
    packaging_fee_rmb: float = 0.0
    damage_cost_rmb: float = 0.0
    last_mile_fee_rmb: float = 0.0
    total_cost_rmb: float = 0.0
    min_viable_price_rmb: float = 0.0
    is_oversized: bool = False
    is_overweight: bool = False
    warnings: list = field(default_factory=list)


class LogisticsCalculator:
    """跨境物流成本计算器"""

    def __init__(self):
        self.air_rate = settings.air_freight_per_kg
        self.vol_divisor = settings.volumetric_divisor
        self.packaging_fee = settings.packaging_fee
        self.last_mile_base = settings.last_mile_base_fee
        self.damage_rate = settings.damage_rate
        self.commission_rate = settings.commission_rate

    def calc_volumetric_weight(self, l: float, w: float, h: float) -> float:
        """体积重 (kg) = 长×宽×高(cm) / 除数"""
        if l <= 0 or w <= 0 or h <= 0:
            return 0.0
        return (l * w * h) / self.vol_divisor

    def calc_chargeable_weight(self, actual_kg: float, vol_kg: float) -> float:
        """计费重量 = max(实重, 体积重)"""
        return max(actual_kg, vol_kg)

    def calc_air_freight(self, chargeable_kg: float) -> float:
        """空运费 = 计费重量 × 单价"""
        return chargeable_kg * self.air_rate

    def calc_damage_cost(self, purchase_price: float) -> float:
        """物损费 = 进货价 × 物损率"""
        return purchase_price * self.damage_rate

    def calc_total_cost(self, purchase_price: float, air_freight: float) -> float:
        """总成本 = 进货价 + 空运费 + 打包费 + 物损费 + 尾程费"""
        return (
            purchase_price
            + air_freight
            + self.packaging_fee
            + self.calc_damage_cost(purchase_price)
            + self.last_mile_base
        )

    def calc_min_viable_price(self, total_cost: float) -> float:
        """最低保本售价 = 总成本 / (1 - 佣金率)"""
        return total_cost / (1 - self.commission_rate)

    def evaluate(self, specs: ProductSpecs) -> LogisticsResult:
        """完整评估一个商品"""
        result = LogisticsResult()
        result.packaging_fee_rmb = self.packaging_fee
        result.last_mile_fee_rmb = self.last_mile_base

        # 体积重
        result.volumetric_weight_kg = self.calc_volumetric_weight(
            specs.length_cm, specs.width_cm, specs.height_cm
        )

        # 计费重
        result.chargeable_weight_kg = self.calc_chargeable_weight(
            specs.actual_weight_kg, result.volumetric_weight_kg
        )

        # 超重检查
        if result.chargeable_weight_kg > settings.max_weight_kg:
            result.is_overweight = True
            result.warnings.append(
                f"计费重{result.chargeable_weight_kg:.2f}kg超过上限{settings.max_weight_kg}kg"
            )

        # 体积重惩罚检查（泡货）
        if result.volumetric_weight_kg > specs.actual_weight_kg * 1.5:
            result.is_oversized = True
            result.warnings.append(
                f"体积重{result.volumetric_weight_kg:.2f}kg远超实重{specs.actual_weight_kg:.2f}kg，属泡货"
            )

        # 空运费
        result.air_freight_rmb = self.calc_air_freight(result.chargeable_weight_kg)

        # 物损费
        result.damage_cost_rmb = self.calc_damage_cost(specs.purchase_price_rmb)

        # 总成本
        result.total_cost_rmb = self.calc_total_cost(
            specs.purchase_price_rmb, result.air_freight_rmb
        )

        # 最低保本售价
        result.min_viable_price_rmb = self.calc_min_viable_price(result.total_cost_rmb)

        return result
