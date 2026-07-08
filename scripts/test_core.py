"""核心模块单元测试"""
import sys
sys.path.insert(0, ".")

from backend.algorithms.logistics import LogisticsCalculator, ProductSpecs
from backend.algorithms.pricing import PricingEngine, CompetitorPrice
from backend.algorithms.festival_weighter import FestivalWeighter
from backend.algorithms.scoring import ProductScorer, ScoredProduct

# 测试物流
calc = LogisticsCalculator()
specs = ProductSpecs(actual_weight_kg=0.3, length_cm=20, width_cm=15, height_cm=8, purchase_price_rmb=20.0)
result = calc.evaluate(specs)
print(f"物流测试: 体积重={result.volumetric_weight_kg:.2f}kg, 计费重={result.chargeable_weight_kg:.2f}kg, "
      f"空运费=¥{result.air_freight_rmb:.2f}, 总成本=¥{result.total_cost_rmb:.2f}, "
      f"最低售价=¥{result.min_viable_price_rmb:.2f}")

# 测试定价
engine = PricingEngine()
competitors = [CompetitorPrice(platform="temu_mx", price_mxn=180, price_rmb=180 * 0.42)]
pricing = engine.evaluate(20.0, result.total_cost_rmb, competitors)
print(f"定价测试: 售价=¥{pricing.suggested_price_rmb:.2f}, MXN=${pricing.suggested_price_mxn:.2f}, "
      f"毛利={pricing.estimated_margin:.2%}, 可行={pricing.is_viable}, 理由={pricing.reason}")

# 测试节日权重
weighter = FestivalWeighter()
active = weighter.get_active_festivals()
print(f"节日测试: 活跃节日={[f['name_zh'] for f in active]}")

# 测试评分
scorer = ProductScorer()
scored = ScoredProduct(
    estimated_margin=0.25, competitor_count=1,
    festival_match_score=0.6, store_years_active=2,
    store_rating=4.5, store_delivery_hours=24
)
s = scorer.score(scored)
print(f"评分测试: 综合得分={s}")

# 测试无竞品定价
pricing2 = engine.evaluate(20.0, result.total_cost_rmb, [])
print(f"无竞品定价: 售价=¥{pricing2.suggested_price_rmb:.2f}, 毛利={pricing2.estimated_margin:.2%}, 可行={pricing2.is_viable}")

print("\n所有核心模块测试通过")
