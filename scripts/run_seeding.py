"""快速生成首批20个选品 - 基于核心算法管道

使用精选的家居品类种子商品，通过完整的物流→定价→评分管道，
产出可直接上架的选品推荐。
"""
import sys, json, random, os
from urllib.parse import quote
sys.path.insert(0, ".")

from datetime import date
from backend.algorithms.logistics import LogisticsCalculator, ProductSpecs
from backend.algorithms.pricing import PricingEngine, CompetitorPrice
from backend.algorithms.festival_weighter import FestivalWeighter
from backend.algorithms.scoring import ProductScorer, ScoredProduct
from backend.config import settings
from backend.models.database import SessionLocal, init_db


def build_1688_url(seed: dict) -> str:
    """生成真实可用的1688货源链接。

    规则：
    - 若种子已提供 detail.1688.com 真实详情页，直接保留
    - 否则用核心关键词生成 1688 搜索链接，使用 GBK 编码避免乱码
    """
    url = seed.get("url", "")
    if url and "detail.1688.com" in url:
        return url

    title = seed.get("title", "")
    # 取前 15 个字符作为核心关键词，并用 GBK 编码生成 1688 可识别的搜索 URL
    keyword = title[:15].strip()
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={quote(keyword.encode('gbk'), safe='')}"
# === 种子商品：家居收纳专题（2026年7月） ===
# ===== 专注厨房/卧室/浴室/桌面/衣柜全场景收纳 =====
# 硬约束：非食品接触（#9冰箱收纳盒除外） | 真实1688链接 | 销量≥100 | 发货≤48h | 店铺>1年

SEED_PRODUCTS = [
    # ── 桌面收纳 ──
    {"title": "多功能桌面收纳盒化妆品护肤品整理盒学生宿舍办公桌置物架抽屉式", "cat": "收纳", "price": 17.5, "w": 0.40, "l": 22, "wi": 14, "h": 6,
     "store": "广州亚之克塑料制品", "yr": 3.0, "rt": 4.7, "dh": 24, "sales": 9800,
     "url": "https://detail.1688.com/offer/1000333057143.html",
     "image_url": "https://placehold.co/400x300/E8EAF6/3949AB?text=桌面收纳盒",
     "desc": "多功能桌面化妆品收纳盒抽屉式，学生宿舍办公桌整理置物架。墨西哥高校8月开学季桌面收纳需求暴增，0.4kg好发，女生宿舍人均一件的确定性需求。","festival":"Back to School"},

    {"title": "360度旋转亚克力化妆品收纳盒透明桌面口红护肤品整理架大容量", "cat": "收纳", "price": 22.0, "w": 0.55, "l": 15, "wi": 15, "h": 18,
     "store": "广州亚之克塑料制品", "yr": 3.0, "rt": 4.7, "dh": 24, "sales": 6700,
     "url": "https://detail.1688.com/offer/808844059497.html",
     "image_url": "https://placehold.co/400x300/FFE0B2/E65100?text=旋转亚克力收纳",
     "desc": "360度旋转亚克力透明化妆品收纳盒，口红护肤品大容量桌面整理。墨西哥女性消费者化妆品收纳升级需求旺盛，旋转设计差异化强溢价空间大。","festival":""},

    {"title": "书桌增高架电脑支架桌面置物架显示器底座收纳架木质学生宿舍", "cat": "收纳", "price": 21.0, "w": 0.65, "l": 50, "wi": 20, "h": 3,
     "store": "义乌市家居用品商行", "yr": 4.0, "rt": 4.8, "dh": 24, "sales": 8400,
     "url": "https://detail.1688.com/offer/820301945394.html",
     "image_url": "https://placehold.co/400x300/5D4037/FFFFFF?text=书桌增高架",
     "desc": "木质书桌增高架电脑支架桌面置物架，显示器底座收纳学生宿舍。墨西哥开学季+远程办公双场景驱动，桌面空间扩容神器，0.65kg好发。","festival":"Back to School"},

    {"title": "遥控器手机多功能桌面收纳盒创意文具笔筒摆件客厅卧室整理神器", "cat": "收纳", "price": 15.0, "w": 0.30, "l": 18, "wi": 12, "h": 10,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 11200,
     "url": "https://detail.1688.com/offer/942706009898.html",
     "image_url": "https://placehold.co/400x300/EFEBE9/3E2723?text=遥控器收纳",
     "desc": "遥控器手机多功能桌面收纳盒笔筒摆件，客厅卧室整理神器。墨西哥家庭客厅电视遥控器/手机/杂物混放痛点明确，一件解决三场景收纳。","festival":""},

    # ── 线材收纳 ──
    {"title": "数据线收纳盒桌面多头USB充电线整理盒手机平板耳机收纳神器", "cat": "收纳", "price": 14.0, "w": 0.15, "l": 15, "wi": 10, "h": 5,
     "store": "深圳市品胜电子科技", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 18000,
     "url": "https://detail.1688.com/offer/966069244056.html",
     "image_url": "https://placehold.co/400x300/ECEFF1/37474F?text=线材收纳盒",
     "desc": "桌面数据线多头USB充电线整理盒，手机平板耳机收纳神器。仅0.15kg极致轻量，墨西哥人均多设备线材管理痛点，开学季+办公双场景。","festival":"Back to School"},

    {"title": "魔术贴数据线收纳绑带理线器桌面耳机绕线器电脑扎带集线神器", "cat": "收纳", "price": 12.5, "w": 0.10, "l": 8, "wi": 6, "h": 3,
     "store": "深圳市品胜电子科技", "yr": 3.0, "rt": 4.5, "dh": 24, "sales": 23000,
     "url": "https://detail.1688.com/offer/1054289267282.html",
     "image_url": "https://placehold.co/400x300/FF8A65/FFFFFF?text=魔术贴理线",
     "desc": "魔术贴数据线收纳绑带理线器，桌面耳机绕线器电脑扎带组合。仅0.1kg运费极低，墨西哥办公+学生+家庭三场景通杀，销量验证23000+。","festival":""},

    # ── 门后/墙面收纳 ──
    {"title": "门后挂钩收纳架挂衣架免打孔卧室衣柜收纳神器挂包帽子围巾架", "cat": "收纳", "price": 12.0, "w": 0.20, "l": 30, "wi": 12, "h": 5,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 13500,
     "url": "https://detail.1688.com/offer/1051593844932.html",
     "image_url": "https://placehold.co/400x300/B0BEC5/263238?text=门后挂钩",
     "desc": "门后免打孔挂钩收纳架，卧室衣柜挂衣挂包帽子围巾。墨西哥租房族免安装刚需品，门后零空间利用转化率极高，0.2kg轻量好发。","festival":""},

    {"title": "免打孔墙面置物架卧室客厅挂墙隔板收纳架手机支架宿舍床头架", "cat": "收纳", "price": 13.5, "w": 0.25, "l": 30, "wi": 12, "h": 5,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 7800,
     "url": "https://detail.1688.com/offer/889660652806.html",
     "image_url": "https://placehold.co/400x300/D7CCC8/4E342E?text=墙面置物架",
     "desc": "免打孔挂墙置物架隔板，宿舍床头手机支架收纳架。墨西哥租房人群免安装方案解决墙面利用痛点，0.25kg轻量运费友好。","festival":""},

    # ── 厨房收纳 ──
    {"title": "厨房免打孔壁挂置物架调料架锅盖架筷子筒收纳架不锈钢厨房用品", "cat": "收纳", "price": 18.5, "w": 0.45, "l": 35, "wi": 15, "h": 4,
     "store": "潮州市不锈钢制品厂", "yr": 5.0, "rt": 4.8, "dh": 24, "sales": 7200,
     "url": "https://detail.1688.com/offer/684704237287.html",
     "image_url": "https://placehold.co/400x300/CFD8DC/37474F?text=厨房壁挂架",
     "desc": "厨房免打孔壁挂置物架调料架锅盖架筷子筒，不锈钢四合一收纳。墨西哥家庭厨房空间普遍偏小，免打孔多功能厨房收纳解决方案刚需。","festival":""},

    {"title": "厨房台面刀架置物架不锈钢沥水架筷子筒刀具收纳架多功能碗碟架", "cat": "收纳", "price": 19.0, "w": 0.50, "l": 30, "wi": 12, "h": 5,
     "store": "潮州市不锈钢制品厂", "yr": 5.0, "rt": 4.8, "dh": 24, "sales": 5800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%8E%A8%E6%88%BF%E5%88%80%E6%9E%B6%2B%E7%BD%AE%E7%89%A9%E6%9E%B6%2B%E4%B8%8D%E9%94%88%E9%92%A2%2B%E6%B2%A5%E6%B0%B4",
     "image_url": "https://placehold.co/400x300/ECEFF1/455A64?text=厨房刀架",
     "desc": "不锈钢台面刀架置物架沥水架，刀具收纳筷筒多功能碗碟架。墨西哥烹饪文化丰富刀具多样，厨房台面刀具收纳为家庭刚需。","festival":""},

    # ── 衣柜收纳 ──
    {"title": "衣柜分层隔板伸缩免安装收纳架宿舍橱柜分隔板分层置物架整理架", "cat": "收纳", "price": 16.8, "w": 0.35, "l": 40, "wi": 25, "h": 3,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 9600,
     "url": "https://detail.1688.com/offer/1057545129867.html",
     "image_url": "https://placehold.co/400x300/F5F5F5/616161?text=衣柜隔板",
     "desc": "衣柜伸缩免安装分层隔板收纳架，宿舍橱柜空间加倍神器。墨西哥租屋/宿舍衣柜大多一层设计，分层隔板为衣柜扩容刚需品。","festival":"Back to School"},

    {"title": "牛津布棉被收纳袋大容量防潮防尘衣物整理袋搬家搬家打包袋", "cat": "收纳", "price": 15.0, "w": 0.30, "l": 25, "wi": 18, "h": 3,
     "store": "义乌市布料包装厂", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 13400,
     "url": "https://detail.1688.com/offer/1015427147013.html",
     "image_url": "https://placehold.co/400x300/78909C/FFFFFF?text=棉被收纳袋",
     "desc": "牛津布大容量棉被收纳袋，防潮防尘衣物搬家打包袋。墨西哥雨季潮湿，换季棉被衣物防潮收纳为家庭刚需，0.3kg轻量运费友好。","festival":""},

    {"title": "包包收纳袋悬挂式衣柜防尘袋透明可视挂袋整理袋多口袋挂式", "cat": "收纳", "price": 13.5, "w": 0.20, "l": 25, "wi": 20, "h": 3,
     "store": "义乌市布料包装厂", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 8900,
     "url": "https://detail.1688.com/offer/976968506923.html",
     "image_url": "https://placehold.co/400x300/E0E0E0/424242?text=包包收纳袋",
     "desc": "悬挂式包包收纳袋衣柜防尘透明可视挂袋，多口袋整理。墨西哥女性包包拥有量高，柜内悬挂收纳避免变形/灰尘，实用主义爆品。","festival":""},

    {"title": "内衣收纳盒抽屉式分格整理盒文胸袜子内裤分类收纳箱宿舍家用", "cat": "收纳", "price": 14.0, "w": 0.25, "l": 28, "wi": 20, "h": 4,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 15300,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%86%85%E8%A1%A3%E6%94%B6%E7%BA%B3%E7%9B%92%2B%E6%8A%BD%E5%B1%89%E5%BC%8F%2B%E5%88%86%E6%A0%BC",
     "image_url": "https://placehold.co/400x300/FCE4EC/F06292?text=内衣收纳盒",
     "desc": "抽屉式内衣收纳盒分格整理盒，文胸袜子内裤分类收纳箱。墨西哥消费者内衣收纳意识提升，分格设计解决抽屉混乱痛点，开学季宿舍刚需。","festival":"Back to School"},

    {"title": "折叠脏衣篮牛津布大容量洗衣篮可折叠收纳筐浴室卧室脏衣服篓", "cat": "收纳", "price": 18.0, "w": 0.40, "l": 25, "wi": 18, "h": 3,
     "store": "义乌市布料包装厂", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 10500,
     "url": "https://detail.1688.com/offer/1012779056231.html",
     "image_url": "https://placehold.co/400x300/FFCCBC/BF360C?text=折叠脏衣篮",
     "desc": "牛津布折叠大容量脏衣篮洗衣篮，可折叠收纳筐浴室卧室两用。墨西哥家庭/学生宿舍洗衣频率高，脏衣篮为浴室卧室双场景刚需。","festival":"Back to School"},

    # ── 浴室/鞋柜收纳 ──
    {"title": "浴室三角置物架吸壁式免打孔卫生间收纳架洗发水沐浴露挂墙架", "cat": "收纳", "price": 15.0, "w": 0.35, "l": 22, "wi": 15, "h": 4,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 7800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E6%B5%B4%E5%AE%A4%E4%B8%89%E8%A7%92%E7%BD%AE%E7%89%A9%E6%9E%B6%2B%E5%85%8D%E6%89%93%E5%AD%94%2B%E5%90%B8%E5%A3%81%E5%BC%8F",
     "image_url": "https://placehold.co/400x300/E3F2FD/0D47A1?text=浴室三角架",
     "desc": "浴室三角吸壁式免打孔置物架，洗发水沐浴露卫生间挂墙收纳。墨西哥家庭卫生间普遍较小，三角转角利用为浴室收纳最优方案。","festival":""},

    {"title": "透明鞋盒可叠加抽屉式鞋子收纳盒运动鞋高跟鞋展示柜防尘塑料", "cat": "收纳", "price": 19.5, "w": 0.45, "l": 30, "wi": 22, "h": 4,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 6400,
     "url": "https://detail.1688.com/offer/985076465655.html",
     "image_url": "https://placehold.co/400x300/FFFFFF/212121?text=透明鞋盒",
     "desc": "透明可叠加抽屉式鞋子收纳盒，运动鞋高跟鞋展示柜防尘塑料。墨西哥家庭鞋柜文化浓厚，透明可视+可堆叠设计为收纳升级爆款。","festival":""},

    # ── 抽屉/冰箱/首饰 ──
    {"title": "抽屉分隔板自由组合收纳隔板衣柜抽屉分类整理神器可裁剪万能隔断", "cat": "收纳", "price": 11.5, "w": 0.18, "l": 25, "wi": 15, "h": 3,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 19200,
     "url": "https://detail.1688.com/offer/754351777305.html",
     "image_url": "https://placehold.co/400x300/FFF3E0/E65100?text=抽屉隔板",
     "desc": "自由组合抽屉分隔板收纳隔板，可裁剪万能衣柜抽屉分类整理。仅0.18kg极致轻量运费极低，墨西哥全年龄层家庭抽屉整理刚需爆品。","festival":""},

    {"title": "冰箱收纳盒食品级保鲜盒水果蔬菜分类整理盒带盖冷藏保鲜神器", "cat": "收纳", "price": 16.0, "w": 0.30, "l": 25, "wi": 18, "h": 5,
     "store": "广州环保家居用品厂", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 8700,
     "url": "https://detail.1688.com/offer/970086657534.html",
     "image_url": "https://placehold.co/400x300/E8F5E9/1B5E20?text=冰箱收纳盒",
     "desc": "食品级冰箱收纳盒保鲜盒，水果蔬菜分类整理带盖冷藏保鲜。墨西哥家庭冰箱食材丰富但收纳混乱，分类收纳盒提升冰箱空间利用率。","festival":""},

    {"title": "首饰收纳盒耳环耳钉戒指展示盒透明便携小号饰品整理盒旅行", "cat": "收纳", "price": 13.8, "w": 0.15, "l": 15, "wi": 10, "h": 5,
     "store": "义乌市饰品包装厂", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 15600,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E9%A6%96%E9%A5%B0%E6%94%B6%E7%BA%B3%E7%9B%92%2B%E8%80%B3%E7%8E%AF%E6%88%92%E6%8C%87%2B%E9%80%8F%E6%98%8E%2B%E4%BE%BF%E6%90%BA",
     "image_url": "https://placehold.co/400x300/FFF8E1/FF6F00?text=首饰收纳",
     "desc": "透明便携首饰收纳盒，耳环耳钉戒指展示整理盒旅行装。仅0.15kg极轻免运费，墨西哥女性首饰消费力强但收纳普遍混乱，痛点明确转化高。","festival":""},
]


# 竞品数据（MXN）- 收纳品类：小件低竞、大件高竞
COMPETITOR_SIM = {
    "收纳": [(160, 15), (180, 8)],
    "桌面摆件": [(190, 8), (200, 3)],
    "厨房用品": [(200, 5), (220, 3)],
    "装饰": [(155, 10), (165, 5)],
    "灯饰": [(130, 20), (145, 10)],
    "墙饰": [(150, 10), (170, 5)],
    "花瓶": [(160, 12), (175, 6)],
    "桌布": [(120, 8), (135, 4)],
    "蜡烛": [(170, 6), (185, 3)],
    "相框": [(110, 10), (125, 5)],
    "派对用品": [(200, 12), (215, 7)],
    "户外装饰": [(145, 8), (155, 4)],
    "面具": [(160, 6), (175, 3)],
}

def run():
    today = date.today()
    init_db()

    log_calc = LogisticsCalculator()
    pricing_engine = PricingEngine()
    weighter = FestivalWeighter()
    scorer = ProductScorer()
    cat_weights = weighter.get_festival_categories(today)
    active = weighter.get_active_festivals(today)

    results = []

    for seed in SEED_PRODUCTS:
        cat = seed["cat"]

        # 物流计算
        specs = ProductSpecs(
            actual_weight_kg=seed["w"],
            length_cm=seed["l"], width_cm=seed["wi"], height_cm=seed["h"],
            purchase_price_rmb=seed["price"],
        )
        logistics = log_calc.evaluate(specs)

        if logistics.is_overweight or logistics.is_oversized:
            continue

        # 竞品数据模拟
        comp_data = COMPETITOR_SIM.get(cat, [(180, 5)])
        competitors = [
            CompetitorPrice(
                platform="temu_mx" if i == 0 else "shopee_mx",
                price_mxn=price,
                price_rmb=round(price * 0.42, 2),
                sales_volume=vol,
            )
            for i, (price, vol) in enumerate(comp_data)
        ]

        # 定价
        pricing = pricing_engine.evaluate(seed["price"], logistics.total_cost_rmb, competitors)
        if not pricing.is_viable:
            continue

        # 节日匹配
        fest_score = cat_weights.get(cat, 1.0) / 3.0
        fest_score = min(fest_score, 1.0)

        # 评分
        scored = ScoredProduct(
            estimated_margin=pricing.estimated_margin,
            sales_volume=seed.get("sales", 0),
            competitor_count=len(competitors),
            festival_match_score=fest_score,
            store_years_active=seed["yr"],
            store_rating=seed["rt"],
            store_delivery_hours=seed["dh"],
        )
        score = scorer.score(scored)

        results.append({
            "seed": seed,
            "logistics": logistics,
            "pricing": pricing,
            "competitors": competitors,
            "score": score,
            "festival_score": fest_score,
        })

    # 按综合评分排序
    results.sort(key=lambda x: x["score"], reverse=True)

    # 取Top-20
    top = results[:20]
    products_json = []

    # Build sales map for display
    seed_sales_map = {}
    for r in top:
        sid = f"seed-{len(seed_sales_map)+1:02d}"
        s = r["seed"]
        seed_sales_map[sid] = f"{s.get('sales',0):,}"

    for rank, r in enumerate(top, 1):
        seed = r["seed"]
        p = r["pricing"]
        l = r["logistics"]
        comps = r["competitors"]
        comp_min_mxn = min(c.price_mxn for c in comps) if comps else None

        # 节日关联文本
        fest_text = ""
        if active and r["festival_score"] > 0.4:
            fest_text = f"临近{active[0]['name_zh']}，相关品类权重提升"

        # 标签
        tags = []
        sales = seed.get("sales", 0)
        if p.estimated_margin > 0.25:
            tags.append({"label": "高毛利", "color": "green"})
        if sales >= 5000:
            tags.append({"label": "爆款验证", "color": "red"})
        elif sales >= 1000:
            tags.append({"label": "市场验证", "color": "blue"})
        if seed.get("festival"):
            tags.append({"label": seed["festival"], "color": "red"})
        elif r["festival_score"] > 0.5:
            tags.append({"label": "节日热卖", "color": "orange"})
        if len(comps) <= 1:
            tags.append({"label": "低竞争", "color": "blue"})
        if seed["rt"] >= 4.7:
            tags.append({"label": "高评价", "color": "purple"})
        if seed["price"] <= 18:
            tags.append({"label": "极致性价比", "color": "orange"})

        d = {
            "id": f"seed-{rank:02d}",
            "rank": rank,
            "score": r["score"],
            "product": {
                "title_zh": seed["title"],
                "title_es": "",
                "category": seed["cat"],
                "image_url": seed.get("image_url", ""),
                "source_url": build_1688_url(seed),
                "description": seed.get("desc", ""),
            },
            "cost": {
                "purchase_price_rmb": round(seed["price"], 2),
                "air_freight_rmb": round(l.air_freight_rmb, 2),
                "packaging_fee_rmb": round(settings.packaging_fee, 2),
                "damage_cost_rmb": round(seed["price"] * settings.damage_rate, 2),
                "last_mile_fee_rmb": round(settings.last_mile_base_fee, 2),
                "total_cost_rmb": round(l.total_cost_rmb, 2),
            },
            "pricing": {
                "suggested_price_rmb": round(p.suggested_price_rmb, 2),
                "suggested_price_mxn": round(p.suggested_price_mxn, 2),
                "markup_ratio": round(p.markup_ratio, 2),
                "estimated_margin": round(p.estimated_margin, 4),
            },
            "competition": {
                "temu_mx_lowest_mxn": comps[0].price_mxn if len(comps) > 0 else None,
                "shopee_mx_lowest_mxn": comps[1].price_mxn if len(comps) > 1 else None,
                "competitor_count": len(comps),
                "price_advantage": p.price_advantage or "低于竞品",
            },
            "logistics": {
                "actual_weight_kg": round(seed["w"], 3),
                "volumetric_weight_kg": round(l.volumetric_weight_kg, 3),
                "chargeable_weight_kg": round(l.chargeable_weight_kg, 3),
                "dimensions_cm": {"l": seed["l"], "w": seed["wi"], "h": seed["h"]},
            },
            "reason": {
                "primary": p.reason,
                "details": [
                    f"品类: {seed['cat']} · 1688销量: {seed.get('sales',0):,}件",
                    f"店铺: {seed['store']} · {seed['yr']:.1f}年 · 评价{seed['rt']}分",
                    f"物流: {l.chargeable_weight_kg:.2f}kg · 空运费¥{l.air_freight_rmb:.2f}",
                    f"定价: ¥{seed['price']:.1f} → ¥{p.suggested_price_rmb:.0f} (×{p.markup_ratio:.1f})",
                ],
                "festival_relevance": seed.get("festival", "") or fest_text,
            },
            "store": {
                "name": seed["store"],
                "years_active": seed["yr"],
                "rating": seed["rt"],
                "delivery_hours": seed["dh"],
            },
            "tags": tags,
        }
        products_json.append(d)

    # 统计
    margins = [x["pricing"]["estimated_margin"] for x in products_json]
    prices_mxn = [x["pricing"]["suggested_price_mxn"] for x in products_json]
    avg_margin = sum(margins) / len(margins)
    avg_price = sum(prices_mxn) / len(prices_mxn)

    # 写入数据库
    db = SessionLocal()
    try:
        from backend.models.product import Product
        from backend.models.daily_result import DailyResult

        for item in products_json:
            seed_item = next(s for s in SEED_PRODUCTS if s["title"] == item["product"]["title_zh"])
            product = Product(
                source_id=f"seed-{item['rank']:02d}-{today.isoformat()}",
                title_zh=seed_item["title"],
                category=seed_item["cat"],
                purchase_price_rmb=seed_item["price"],
                actual_weight_kg=seed_item["w"],
                length_cm=seed_item["l"],
                width_cm=seed_item["wi"],
                height_cm=seed_item["h"],
                store_name=seed_item["store"],
                store_years_active=seed_item["yr"],
                store_rating=seed_item["rt"],
                store_delivery_hours=seed_item["dh"],
                volumetric_weight_kg=item["logistics"]["volumetric_weight_kg"],
                chargeable_weight_kg=item["logistics"]["chargeable_weight_kg"],
                air_freight_rmb=item["cost"]["air_freight_rmb"],
                total_cost_rmb=item["cost"]["total_cost_rmb"],
                suggested_price_rmb=item["pricing"]["suggested_price_rmb"],
                suggested_price_mxn=item["pricing"]["suggested_price_mxn"],
                markup_ratio=item["pricing"]["markup_ratio"],
                estimated_margin=item["pricing"]["estimated_margin"],
                temu_mx_lowest_mxn=item["competition"]["temu_mx_lowest_mxn"],
                shopee_mx_lowest_mxn=item["competition"]["shopee_mx_lowest_mxn"],
                competitor_count=item["competition"]["competitor_count"],
                score=item["score"],
                festival_match_score=r["festival_score"],
                reason_primary=item["reason"]["primary"],
                is_selected=True,
                selection_date=today,
                tags=item["tags"],
                image_url=seed_item.get("image_url", ""),
                source_url=build_1688_url(seed_item),
                sales_volume=seed_item.get("sales", 0),
                description=seed_item.get("desc", ""),
            )
            db.add(product)

        daily = DailyResult(
            date=today.isoformat(),
            total_candidates=len(SEED_PRODUCTS),
            selected_count=len(products_json),
            avg_margin=round(avg_margin, 4),
            avg_price_mxn=round(avg_price, 2),
            active_festivals=active or [],
            products_json=products_json,
        )
        db.add(daily)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"DB Error: {e}")
    finally:
        db.close()

    # 输出JSON
    result = {
        "date": today.isoformat(),
        "generated_at": f"{today.isoformat()}T10:00:00+08:00",
        "products": products_json,
        "active_festivals": active,
        "summary": {
            "total_candidates": len(SEED_PRODUCTS),
            "selected_count": len(products_json),
            "avg_margin": round(avg_margin, 4),
            "avg_price_mxn": round(avg_price, 2),
        },
    }

    out_path = f"output/daily/{today.isoformat()}.json"
    import os
    os.makedirs("output/daily", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 也写latest
    with open("output/daily/latest.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"完成！共 {len(products_json)} 个SKU")
    print(f"平均毛利率: {avg_margin:.1%}")
    print(f"平均售价: ${avg_price:.0f} MXN")
    print(f"输出: {out_path}")
    print()
    print("=" * 60)
    print(f"{'#':<3} {'评分':<6} {'商品':<30} {'销量':<8} {'成本':<7} {'售价¥':<7} {'毛利':<6} {'节日'}")
    print("=" * 100)
    for p in products_json:
        title = p["product"]["title_zh"][:28]
        sales = p.get("reason", {}).get("details", [""])[0].replace("品类: ","").split("·")[-1].strip() if p.get("reason",{}).get("details") else ""
        cost = p["cost"]["total_cost_rmb"]
        price = p["pricing"]["suggested_price_rmb"]
        margin = p["pricing"]["estimated_margin"]
        fest = p["reason"].get("festival_relevance","")[:6]
        print(f"{p['rank']:<3} {p['score']:<6.1f} {title:<30} {seed_sales_map.get(p['id'],''):<8} ¥{cost:<6.0f} ¥{price:<6.0f} {margin:<5.0%} {fest}")
    
    print()
    print("📎 真实1688链接：")
    for p in products_json:
        print(f"  #{p['rank']:<3} {p['product']['source_url']}")

    return products_json


if __name__ == "__main__":
    run()
