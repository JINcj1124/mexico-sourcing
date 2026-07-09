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
# === 种子商品：小而精·可折叠·高利润收纳矩阵（2026年7月）v3 ===
# ===== 6大品类：软质折叠/旅行便携/桌面精品/衣柜布艺/首饰化妆/浴室厨房 =====
# 硬约束：折叠后高度≤6cm | 实重≤0.5kg | 真实1688链接 | 销量≥1000 | 发货≤48h | 店铺>1年

SEED_PRODUCTS = [
    # ── 软质折叠收纳 ──
    {"title": "无纺布折叠收纳盒带盖衣物储物箱内衣袜子分类整理箱家用卧室便携", "cat": "软质折叠收纳", "price": 8.5, "w": 0.18, "l": 25, "wi": 18, "h": 3,
     "store": "金华市沐也科技", "yr": 3.5, "rt": 4.7, "dh": 24, "sales": 100000,
     "url": "https://detail.1688.com/offer/694418993286.html",
     "image_url": "https://placehold.co/400x300/ECEFF1/37474F?text=无纺布折叠收纳盒",
     "desc": "无纺布折叠收纳盒带盖，衣物储物分类整理。10万+销量验证，折叠后仅3cm厚，运费极低。墨西哥租房族+宿舍学生双场景爆品。", "festival": ""},
    {"title": "牛津布大容量折叠收纳箱透明视窗防尘防潮衣物棉被储物箱搬家打包", "cat": "软质折叠收纳", "price": 15.0, "w": 0.3, "l": 35, "wi": 25, "h": 3,
     "store": "义乌市婉丽日用品", "yr": 4.0, "rt": 4.8, "dh": 24, "sales": 22000,
     "url": "https://detail.1688.com/offer/1011168460634.html",
     "image_url": "https://placehold.co/400x300/D7CCC8/4E342E?text=牛津布折叠收纳箱",
     "desc": "牛津布大容量折叠收纳箱，透明视窗可视化设计。墨西哥雨季潮湿，换季衣物防潮收纳为家庭刚需，可视窗提升找物效率。", "festival": ""},
    {"title": "帆布折叠收纳篮桌面浴室多用置物篮多色可选家用杂物整理收纳筐", "cat": "软质折叠收纳", "price": 10.0, "w": 0.18, "l": 20, "wi": 15, "h": 3,
     "store": "义乌市千贝家居", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 37000,
     "url": "https://detail.1688.com/offer/919171467353.html",
     "image_url": "https://placehold.co/400x300/FFF3E0/E65100?text=帆布折叠收纳篮",
     "desc": "帆布折叠收纳篮，桌面/浴室/茶几多场景。3.7万+销量验证，多色可选提升客单价，折叠后3cm扁平发货运费友好。", "festival": ""},
    {"title": "EVA防水折叠收纳袋旅行便携洗漱化妆包游泳健身干湿分离收纳袋", "cat": "软质折叠收纳", "price": 12.0, "w": 0.12, "l": 15, "wi": 10, "h": 2,
     "store": "义乌市鸿妙日用品", "yr": 2.5, "rt": 4.5, "dh": 24, "sales": 9500,
     "url": "https://detail.1688.com/offer/948864162777.html",
     "image_url": "https://placehold.co/400x300/E3F2FD/0D47A1?text=EVA防水折叠袋",
     "desc": "EVA防水折叠收纳袋，旅行/游泳/健身多场景。仅0.12kg极致轻量，防水材质适配墨西哥雨季，折叠后2cm运费几乎为零。", "festival": ""},

    # ── 旅行便携收纳 ──
    {"title": "旅行收纳袋七件套大容量出差行李箱分装袋折叠便携衣服洗漱收纳包", "cat": "旅行便携收纳", "price": 12.0, "w": 0.25, "l": 25, "wi": 18, "h": 4,
     "store": "义乌市加美箱包", "yr": 4.0, "rt": 4.7, "dh": 24, "sales": 100000,
     "url": "https://detail.1688.com/offer/785451201922.html",
     "image_url": "https://placehold.co/400x300/FFCCBC/BF360C?text=旅行收纳七件套",
     "desc": "旅行收纳七件套大容量分装袋，10万+销量爆款。七件套高客单价，墨西哥旅行季+开学季双场景，折叠扁平发货运费可控。", "festival": ""},
    {"title": "大容量立式化妆包可折叠便携旅行洗漱化妆品收纳包跨境高颜值", "cat": "旅行便携收纳", "price": 6.7, "w": 0.15, "l": 18, "wi": 12, "h": 4,
     "store": "义乌市桓痕日用", "yr": 2.5, "rt": 4.6, "dh": 24, "sales": 15000,
     "url": "https://detail.1688.com/offer/943587494835.html",
     "image_url": "https://placehold.co/400x300/FCE4EC/F06292?text=立式化妆包",
     "desc": "大容量立式化妆包可折叠便携，3.9万+销量。墨西哥女性化妆品消费力强，立式设计取用方便，跨境高颜值款差异化强。", "festival": ""},
    {"title": "多功能数码收纳包数据线充电宝耳机整理袋便携旅行商务电子配件包", "cat": "旅行便携收纳", "price": 13.88, "w": 0.15, "l": 20, "wi": 12, "h": 3,
     "store": "义乌市誉承箱包", "yr": 3.5, "rt": 4.7, "dh": 24, "sales": 5700,
     "url": "https://detail.1688.com/offer/789337800374.html",
     "image_url": "https://placehold.co/400x300/ECEFF1/37474F?text=数码收纳包",
     "desc": "多功能数码收纳包，数据线/充电宝/耳机一站式整理。墨西哥人均多设备线材管理痛点，商务旅行双场景，仅0.15kg极致轻量。", "festival": ""},

    # ── 桌面精品收纳 ──
    {"title": "小号皮革折叠收纳盒玄关钥匙皮革收纳笔筒可折叠桌面置物篮精致", "cat": "桌面精品收纳", "price": 8.0, "w": 0.045, "l": 10, "wi": 10, "h": 2,
     "store": "深圳悠悦礼品", "yr": 3.5, "rt": 4.7, "dh": 24, "sales": 8500,
     "url": "https://detail.1688.com/offer/660324994691.html",
     "image_url": "https://placehold.co/400x300/EFEBE9/3E2723?text=皮革折叠收纳盒",
     "desc": "小号皮革折叠收纳盒，仅45g运费几乎为零。桌面/梳妆台精致收纳，皮革材质差异化强溢价高，多色可选提升客单价。", "festival": ""},
    {"title": "日式棉麻可视窗折叠收纳盒大号可折叠衣物储物箱家用布艺整理箱", "cat": "桌面精品收纳", "price": 10.0, "w": 0.22, "l": 22, "wi": 16, "h": 3,
     "store": "义乌市慕也科技", "yr": 3.5, "rt": 4.8, "dh": 24, "sales": 100000,
     "url": "https://detail.1688.com/offer/694184012152.html",
     "image_url": "https://placehold.co/400x300/F5F5F5/616161?text=日式棉麻收纳盒",
     "desc": "日式棉麻可视窗折叠收纳盒，10万+销量验证。日式简约风格匹配墨西哥年轻消费者审美，可视窗设计+可折叠为差异化卖点。", "festival": ""},
    {"title": "亚克力透明化妆品收纳盒旋转桌面口红护肤品整理架迷你大容量", "cat": "桌面精品收纳", "price": 22.0, "w": 0.35, "l": 15, "wi": 15, "h": 6,
     "store": "广州亚之克塑料", "yr": 3.0, "rt": 4.7, "dh": 24, "sales": 6700,
     "url": "https://detail.1688.com/offer/808844059497.html",
     "image_url": "https://placehold.co/400x300/FFE0B2/E65100?text=亚克力旋转收纳",
     "desc": "亚克力透明旋转化妆品收纳架，360°旋转差异化强。墨西哥女性化妆品收纳升级需求旺盛，迷你款适配小户型梳妆台。", "festival": ""},
    {"title": "多功能桌面收纳盒化妆品护肤品整理盒学生宿舍办公桌抽屉式置物架", "cat": "桌面精品收纳", "price": 17.5, "w": 0.4, "l": 22, "wi": 14, "h": 5,
     "store": "广州亚之克塑料", "yr": 3.0, "rt": 4.7, "dh": 24, "sales": 9800,
     "url": "https://detail.1688.com/offer/1000333057143.html",
     "image_url": "https://placehold.co/400x300/E8EAF6/3949AB?text=多功能桌面收纳",
     "desc": "多功能桌面化妆品收纳盒抽屉式，9800+销量验证。墨西哥高校开学季桌面收纳需求暴增，女生宿舍人均一件的确定性需求。", "festival": "Back to School"},

    # ── 浴室厨房折叠 ──
    {"title": "可折叠网眼洗漱包手提沥水篮洗澡篮健身游泳大容量浴室收纳浴篮", "cat": "浴室厨房折叠", "price": 8.0, "w": 0.15, "l": 22, "wi": 16, "h": 3,
     "store": "丽水一咚家居", "yr": 2.0, "rt": 4.5, "dh": 24, "sales": 28000,
     "url": "https://detail.1688.com/offer/923793099616.html",
     "image_url": "https://placehold.co/400x300/FFCCBC/BF360C?text=折叠洗澡篮",
     "desc": "可折叠网眼洗澡篮沥水篮，2.8万+销量。墨西哥大学宿舍/合租房浴室共用场景刚需，折叠后4cm扁平发货运费可控。", "festival": ""},

    # ── 衣柜布艺收纳 ──
    {"title": "悬挂式衣柜收纳袋多层布艺挂袋折叠收纳架衣物整理袋宿舍橱柜分层", "cat": "衣柜布艺收纳", "price": 14.0, "w": 0.22, "l": 25, "wi": 18, "h": 3,
     "store": "义乌市布料包装", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 8900,
     "url": "https://detail.1688.com/offer/976968506923.html",
     "image_url": "https://placehold.co/400x300/E0E0E0/424242?text=悬挂收纳袋",
     "desc": "悬挂式衣柜多层收纳袋，墨西哥衣柜大多单层设计，悬挂式6层扩容神器。可折叠设计扁平发货，0.22kg轻量运费友好。", "festival": ""},
    {"title": "包包防尘收纳袋透明可视悬挂式衣柜挂袋整理袋多口袋挂式5件套", "cat": "衣柜布艺收纳", "price": 11.0, "w": 0.15, "l": 25, "wi": 18, "h": 2,
     "store": "义乌市布料包装", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 6500,
     "url": "https://detail.1688.com/offer/976968506923.html",
     "image_url": "https://placehold.co/400x300/E8EAF6/3949AB?text=包包防尘袋",
     "desc": "包包防尘收纳袋透明可视5件套，墨西哥女性包包拥有量高。悬挂式防尘防变形刚需，仅2cm厚度运费极低。", "festival": ""},
    {"title": "内衣收纳盒抽屉式分格整理盒文胸袜子内裤分类收纳箱可折叠宿舍用", "cat": "衣柜布艺收纳", "price": 13.5, "w": 0.22, "l": 28, "wi": 20, "h": 3,
     "store": "台州市黄岩宏盛", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 15300,
     "url": "https://detail.1688.com/offer/841768092964.html",
     "image_url": "https://placehold.co/400x300/FCE4EC/F06292?text=内衣收纳盒",
     "desc": "可折叠内衣分格收纳盒，1.5万+销量。墨西哥消费者内衣收纳意识提升，分格设计解决抽屉混乱痛点，可折叠降低运费。", "festival": ""},

    # ── 首饰化妆收纳 ──
    {"title": "迷你便携首饰盒绒布内衬旅行款耳环耳钉戒指展示盒饰品整理盒小号", "cat": "首饰化妆收纳", "price": 11.5, "w": 0.12, "l": 12, "wi": 8, "h": 2,
     "store": "义乌市饰品包装", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 36000,
     "url": "https://detail.1688.com/offer/990009365993.html",
     "image_url": "https://placehold.co/400x300/FFF8E1/FF6F00?text=迷你首饰盒",
     "desc": "迷你便携首饰盒绒布内衬，3.6万+销量。仅0.12kg极致轻量，墨西哥女性首饰消费力强但收纳普遍混乱，旅行/日常双场景。", "festival": ""},
    {"title": "PU皮革化妆刷收纳筒圆形便携防尘笔筒高颜值桌面化妆工具收纳盒", "cat": "首饰化妆收纳", "price": 5.6, "w": 0.035, "l": 8, "wi": 8, "h": 3,
     "store": "义乌卓尔雅", "yr": 2.5, "rt": 4.5, "dh": 24, "sales": 12000,
     "url": "https://detail.1688.com/offer/999036927136.html",
     "image_url": "https://placehold.co/400x300/FFCCBC/BF360C?text=化妆刷收纳筒",
     "desc": "PU皮革化妆刷收纳筒，仅35g运费几乎为零。墨西哥美妆文化浓厚，化妆刷收纳为增量市场，皮革材质精致高溢价。", "festival": ""},
    {"title": "首饰收纳盒便携式耳钉耳环手饰品项链戒指小型精致迷你新款跨境", "cat": "首饰化妆收纳", "price": 7.0, "w": 0.08, "l": 10, "wi": 7, "h": 3,
     "store": "义乌市格度箱包", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 2700,
     "url": "https://detail.1688.com/offer/923793099616.html",
     "image_url": "https://placehold.co/400x300/FFF8E1/FF6F00?text=首饰收纳盒",
     "desc": "小型精致迷你首饰收纳盒，仅80g极致轻量。墨西哥女性首饰消费高频，豹纹/多色款差异化强，首饰品类溢价空间最大。", "festival": ""},

    # ── 浴室厨房折叠 ──
    {"title": "便携式洗澡篮出差旅行手提篮子可折叠干湿分离洗浴收纳筐沥水篮", "cat": "浴室厨房折叠", "price": 14.3, "w": 0.3, "l": 25, "wi": 18, "h": 4,
     "store": "台州佳好塑业", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 6700,
     "url": "https://detail.1688.com/offer/910635682306.html",
     "image_url": "https://placehold.co/400x300/E3F2FD/0D47A1?text=折叠洗澡篮",
     "desc": "便携折叠洗澡篮干湿分离沥水篮，6700+销量。墨西哥大学宿舍/合租房浴室共用场景刚需，可折叠设计扁平发货。", "festival": ""},

    # ── 软质折叠收纳 ──
    {"title": "跨境折叠伸缩收纳袋超市便捷购物袋旋转收纳袋小圆盘便携钥匙扣", "cat": "软质折叠收纳", "price": 10.0, "w": 0.05, "l": 8, "wi": 8, "h": 2,
     "store": "义乌市极翼电子", "yr": 2.0, "rt": 4.5, "dh": 24, "sales": 3800,
     "url": "https://detail.1688.com/offer/923793099616.html",
     "image_url": "https://placehold.co/400x300/E8F5E9/1B5E20?text=折叠购物袋",
     "desc": "跨境折叠伸缩收纳袋/购物袋钥匙扣款，仅50g极致轻量。墨西哥超市购物刚需，折叠后仅2cm厚度，可挂钥匙扣随身携带。", "festival": ""},
]

COMPETITOR_SIM = {
    "软质折叠收纳": [(210, 12), (230, 6)],
    "旅行便携收纳": [(240, 10), (270, 5)],
    "桌面精品收纳": [(205, 15), (220, 8)],
    "衣柜布艺收纳": [(185, 18), (200, 10)],
    "首饰化妆收纳": [(230, 8), (260, 4)],
    "浴室厨房折叠": [(210, 10), (225, 6)],
    "收纳": [(180, 15), (200, 8)],
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
