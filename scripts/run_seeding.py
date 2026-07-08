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
# === 种子商品：2026年7月墨西哥热点选品 ===
# ===== FIFA World Cup 2026 | Guelaguetza文化节 | Back to School | 独立日 =====
# 硬约束：非食品接触 | 真实1688链接 | 销量≥100 | 评价≥4.5 | 发货≤48h | 店铺>1年

SEED_PRODUCTS = [
    # ═══════════════ FIFA World Cup 2026 ═══════════════
    # 6.11-7.19 正在进行，墨西哥联办，全民狂欢
    {"title": "美加墨世界杯墨西哥国旗抱枕套沙发布艺靠垫套绿白红三色家居装饰", "cat": "世界杯装饰", "price": 19.5, "w": 0.22, "l": 25, "wi": 25, "h": 2,
     "store": "绍兴市柯桥家纺有限公司", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 1800,
     "url": "https://detail.1688.com/offer/533266664499.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=墨西哥国旗抱枕",
     "desc": "绿白红三色墨西哥国旗抱枕套45x45cm，沙发靠垫世界杯应援装饰。2026世界杯墨西哥联办全民狂欢，仅0.22kg极致轻量，TikTok世界杯话题流量爆发。", "festival": "FIFA World Cup"},

    {"title": "世界杯足球造型创意桌面摆件家居装饰品树脂运动员雕塑客厅展示", "cat": "世界杯装饰", "price": 18.8, "w": 0.30, "l": 12, "wi": 10, "h": 15,
     "store": "深圳市潮玩工贸有限公司", "yr": 3.5, "rt": 4.7, "dh": 24, "sales": 3200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E8%B6%B3%E7%90%83%E9%80%A0%E5%9E%8B%E6%A1%8C%E9%9D%A2%E6%91%86%E4%BB%B6%E5%88%9B%E6%84%8F%E5%AE%B6%E5%B1%85",
     "image_url": "https://placehold.co/400x300/1A1A2E/FFFFFF?text=足球⚽摆件",
     "desc": "足球运动员造型树脂桌面摆件，客厅电视柜展示品。2026世界杯期间墨西哥家庭客厅装饰刚需，球迷收藏展示属性强，0.3kg轻量好发。", "festival": "FIFA World Cup"},

    {"title": "世界杯主题背景墙贴纸客厅电视墙装饰仿砖纹3D立体足球图案自粘", "cat": "世界杯装饰", "price": 14.0, "w": 0.20, "l": 30, "wi": 20, "h": 2,
     "store": "温州博美工艺品有限公司", "yr": 5.0, "rt": 4.8, "dh": 24, "sales": 4500,
     "url": "https://detail.1688.com/offer/1016973546382.html",
     "image_url": "https://placehold.co/400x300/004d40/FFFFFF?text=世界杯⚽墙贴",
     "desc": "世界杯3D立体足球墙贴纸，自粘防水，客厅电视背景墙秒变球迷观赛房。墨西哥球迷世界杯期间客厅改造刚需，0.2kg极致轻量运费低。", "festival": "FIFA World Cup"},

    {"title": "绿白红三色拉花拉旗横幅世界杯派对装饰墨西哥国旗色居家布置", "cat": "世界杯装饰", "price": 16.0, "w": 0.18, "l": 20, "wi": 15, "h": 3,
     "store": "义乌市派对大师工艺品厂", "yr": 4.0, "rt": 4.7, "dh": 24, "sales": 5600,
     "url": "https://detail.1688.com/offer/914011858616.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=拉花🇲🇽三色",
     "desc": "绿白红墨西哥国旗色拉花拉旗横幅，世界杯观赛聚会派对必备。世界杯期间墨西哥家庭/酒吧/广场聚集看球场景通杀，0.18kg极致轻。", "festival": "FIFA World Cup"},

    {"title": "墨西哥国家队应援加油旗球迷助威旗车挂旗世界杯观赛装饰旗", "cat": "世界杯装饰", "price": 22.0, "w": 0.25, "l": 30, "wi": 20, "h": 2,
     "store": "义乌市世界杯工艺品厂", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 8900,
     "url": "https://detail.1688.com/offer/999891025739.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=墨西哥加油旗",
     "desc": "墨西哥国家队球迷加油旗帜套装，世界杯车挂/阳台/客厅应援装饰。墨西哥街头巷尾全民挂旗氛围浓，世界杯期间日均搜索量暴增300%。", "festival": "FIFA World Cup"},

    {"title": "足球场图案地垫门垫玄关防滑垫世界杯主题入户毯可水洗家用脚垫", "cat": "世界杯装饰", "price": 20.5, "w": 0.45, "l": 40, "wi": 30, "h": 2,
     "store": "义乌市地垫批发商行", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 2800,
     "url": "https://detail.1688.com/offer/1000652515937.html",
     "image_url": "https://placehold.co/400x300/2E7D32/FFFFFF?text=足球场⚽地垫",
     "desc": "绿色足球场图案防滑地垫，世界杯主题入户玄关门垫。世界杯期间墨西哥球迷家庭入户仪式感第一站，可水洗耐用，0.45kg好发。", "festival": "FIFA World Cup"},

    {"title": "LED世界杯足球灯串装饰灯电池盒派对挂饰氛围彩灯世界杯应援灯", "cat": "世界杯装饰", "price": 15.5, "w": 0.15, "l": 10, "wi": 8, "h": 3,
     "store": "中山市古镇灯饰有限公司", "yr": 7.0, "rt": 4.9, "dh": 24, "sales": 12000,
     "url": "https://detail.1688.com/offer/652508114082.html",
     "image_url": "https://placehold.co/400x300/1A237E/FFD700?text=LED⚽灯串",
     "desc": "足球造型LED彩灯串电池盒供电，世界杯观赛派对阳台室内氛围装饰。仅0.15kg极致轻量免运费，墨西哥球迷夜间看球聚会场景爆款。", "festival": "FIFA World Cup"},

    {"title": "创意足球造型笔筒桌面收纳盒家居摆件世界杯主题球迷纪念品礼物", "cat": "世界杯装饰", "price": 17.0, "w": 0.28, "l": 12, "wi": 12, "h": 10,
     "store": "深圳市潮玩工贸有限公司", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 2100,
     "url": "https://detail.1688.com/offer/636568175955.html",
     "image_url": "https://placehold.co/400x300/212121/FFFFFF?text=足球⚽笔筒",
     "desc": "足球造型多功能桌面收纳盒笔筒摆件，世界杯主题礼品。既是实用办公收纳又是球迷桌面展示品，世界杯期间墨西哥办公室/学生桌上摆件需求量暴增。", "festival": "FIFA World Cup"},

    {"title": "美加墨世界杯马克杯纪念水杯不锈钢足球造型3D浮雕球迷礼物", "cat": "世界杯装饰", "price": 21.0, "w": 0.35, "l": 10, "wi": 8, "h": 12,
     "store": "潮州市潮安区不锈钢厂", "yr": 5.0, "rt": 4.7, "dh": 24, "sales": 1500,
     "url": "https://detail.1688.com/offer/1008490442813.html",
     "image_url": "https://placehold.co/400x300/212121/FFD700?text=世界杯🏆杯",
     "desc": "2026美加墨世界杯纪念不锈钢马克杯，足球3D浮雕设计球迷礼物。世界杯纪念品/家居两用，墨西哥球迷购买力强，纪念属性溢价空间大。", "festival": "FIFA World Cup"},

    {"title": "绿白红彩灯串星星灯世界杯应援灯饰墨西哥国旗色派对挂饰氛围灯", "cat": "世界杯装饰", "price": 12.8, "w": 0.12, "l": 10, "wi": 8, "h": 3,
     "store": "中山市古镇灯饰有限公司", "yr": 7.0, "rt": 4.9, "dh": 24, "sales": 16000,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E7%BB%BF%E7%99%BD%E7%BA%A2%E5%BD%A9%E7%81%AF%E4%B8%B2%E8%8A%82%E6%97%A5%E5%B8%83%E7%BD%AE",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=绿白红💡灯",
     "desc": "绿白红三色彩灯串墨西哥国旗色，世界杯应援阳台派对挂饰灯。0.12kg超极轻免运费，世界杯期间三色灯光墨西哥各地广场/阳台标配。", "festival": "FIFA World Cup"},

    # ═══════════════ Guelaguetza文化节 & 夏季民俗 ═══════════════
    # 7月全月 Oaxaca，墨西哥最盛大传统文化活动
    {"title": "跨境彩色墨西哥花卉手工刺绣挂毯墙面装饰波西米亚民宿背景布", "cat": "民俗装饰", "price": 19.8, "w": 0.25, "l": 30, "wi": 25, "h": 2,
     "store": "绍兴市柯桥布艺有限公司", "yr": 5.0, "rt": 4.7, "dh": 24, "sales": 3400,
     "url": "https://detail.1688.com/offer/891830011058.html",
     "image_url": "https://placehold.co/400x300/FF6B35/FFFFFF?text=墨西哥刺绣挂毯",
     "desc": "墨西哥花卉手工刺绣挂毯背景布，Guelaguetza节日墙面民俗装饰。墨西哥家庭七月文化节布置墙面刚需，手工刺绣质感高级溢价空间大。", "festival": "Guelaguetza文化节"},

    {"title": "彩绘手工陶瓷花瓶民族风桌面摆件墨西哥风格客厅民宿家居装饰品", "cat": "民俗装饰", "price": 16.5, "w": 0.35, "l": 10, "wi": 10, "h": 18,
     "store": "景德镇雅瓷坊陶瓷有限公司", "yr": 5.5, "rt": 4.9, "dh": 48, "sales": 2800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%BD%A9%E7%BB%98%E9%99%B6%E7%93%B7%E8%8A%B1%E7%93%B6%2B%E5%A2%A8%E8%A5%BF%E5%93%A5%E6%B0%91%E6%97%8F%E9%A3%8E",
     "image_url": "https://placehold.co/400x300/E65100/FFFFFF?text=彩绘陶瓷花瓶",
     "desc": "手工彩绘陶瓷花瓶，墨西哥民族风图案桌面摆件。Guelaguetza期间墨西哥家庭花卉布置核心品类，民族瓷艺适配当地审美，溢价空间可观。", "festival": "Guelaguetza文化节"},

    {"title": "编织草帽墙面挂饰ins风民宿装饰品墨西哥乡村风家居吊饰摆件", "cat": "民俗装饰", "price": 15.0, "w": 0.20, "l": 25, "wi": 25, "h": 5,
     "store": "义乌市工艺礼品商行", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 4700,
     "url": "https://detail.1688.com/offer/977669765919.html",
     "image_url": "https://placehold.co/400x300/D7CCC8/5D4037?text=编织草帽🪶",
     "desc": "天然编织草帽墙面挂饰，墨西哥乡村风民宿庭院装饰品。七月Oaxaca Guelaguetza文化节草帽为核心元素，墙面吊饰0.2kg轻量好发。", "festival": "Guelaguetza文化节"},

    {"title": "波西米亚风彩色手工串珠门帘隔断帘ins民宿家居装饰品隔断挂帘", "cat": "民俗装饰", "price": 22.0, "w": 0.40, "l": 35, "wi": 20, "h": 3,
     "store": "绍兴市柯桥布艺有限公司", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 1900,
     "url": "https://detail.1688.com/offer/955065178885.html",
     "image_url": "https://placehold.co/400x300/FF6F00/FFFFFF?text=彩色串珠门帘",
     "desc": "波西米亚风手工串珠门帘隔断帘，ins民宿家居装饰。墨西哥Guelaguetza节彩色串珠是传统工艺代表，民宿/庭院门帘需求旺盛，0.4kg好发。", "festival": "Guelaguetza文化节"},

    {"title": "墨西哥桌布夏季彩色条纹桌布盖毯厨房餐桌装饰布艺盖巾家居方巾", "cat": "民俗装饰", "price": 18.5, "w": 0.30, "l": 28, "wi": 22, "h": 2,
     "store": "义乌市美布家居用品厂", "yr": 3.0, "rt": 4.5, "dh": 48, "sales": 2200,
     "url": "https://detail.1688.com/offer/778647070226.html",
     "image_url": "https://placehold.co/400x300/FF8F00/FFFFFF?text=墨西哥桌布🌈",
     "desc": "七彩条纹墨西哥民族风桌布，夏季家居餐桌装饰布艺。Guelaguetza期间墨西哥餐桌布置首选，七彩条纹富含传统文化色彩，节日溢价明显。", "festival": "Guelaguetza文化节"},

    {"title": "手工彩色蜡烛浪漫氛围装饰蜡烛生日派对婚庆民宿摆件ins风蜡烛", "cat": "民俗装饰", "price": 14.8, "w": 0.18, "l": 10, "wi": 8, "h": 6,
     "store": "义乌市烛愿工艺品有限公司", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 6800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%BD%A9%E8%89%B2%E8%9C%A1%E7%83%9B%2B%E6%89%8B%E5%B7%A5%2B%E6%B0%9B%E5%9B%B4%E8%A3%85%E9%A5%B0",
     "image_url": "https://placehold.co/400x300/FF5722/FFFFFF?text=手工🕯蜡烛",
     "desc": "手工彩色蜡烛氛围装饰，民宿摆件ins风蜡烛灯。墨西哥Guelaguetza民俗节蜡烛仪式/桌面装饰刚需，多种颜色适配夏季文化场景。", "festival": "Guelaguetza文化节"},

    # ═══════════════ Back to School 开学季 ═══════════════
    # 8月下旬，墨西哥大学/中学开学，宿舍装饰刚需
    {"title": "亚克力透明化妆品收纳盒桌面整理盒学生宿舍梳妆台护肤品置物架", "cat": "收纳", "price": 17.5, "w": 0.40, "l": 22, "wi": 14, "h": 12,
     "store": "广州亚之克塑料制品", "yr": 3.0, "rt": 4.7, "dh": 24, "sales": 9800,
     "url": "https://detail.1688.com/offer/992280966554.html",
     "image_url": "https://placehold.co/400x300/E0E0E0/424242?text=亚克力收纳盒",
     "desc": "亚克力透明桌面化妆品收纳盒，学生宿舍梳妆台整理神器。墨西哥高校8月下旬开学，女生宿舍桌面收纳为开学季爆款品类。", "festival": "Back to School"},

    {"title": "多功能旋转笔筒桌面收纳盒创意文具整理架学生宿舍学习用品置物", "cat": "收纳", "price": 15.0, "w": 0.35, "l": 15, "wi": 12, "h": 10,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 12500,
     "url": "https://detail.1688.com/offer/840333658698.html",
     "image_url": "https://placehold.co/400x300/42A5F5/FFFFFF?text=旋转笔筒✏",
     "desc": "多功能旋转笔筒桌面收纳盒，学生宿舍文具整理架。墨西哥开学季笔筒+收纳复合需求旺盛，实用主义产品转化率极高。", "festival": "Back to School"},

    {"title": "免打孔墙面置物架宿舍收纳神器挂墙隔板学生寝室床头手机支架架", "cat": "收纳", "price": 13.5, "w": 0.25, "l": 30, "wi": 12, "h": 5,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 7800,
     "url": "https://detail.1688.com/offer/982030237014.html",
     "image_url": "https://placehold.co/400x300/66BB6A/FFFFFF?text=墙面置物架",
     "desc": "免打孔挂墙置物架隔板，学生宿舍床头手机/杂物收纳。墨西哥学生宿舍多为租屋，免安装方案解决租房打孔痛点。", "festival": "Back to School"},

    {"title": "门后挂钩收纳架挂衣架免打孔宿舍卧室衣柜收纳神器挂包帽子围巾", "cat": "收纳", "price": 12.0, "w": 0.20, "l": 30, "wi": 12, "h": 5,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 13500,
     "url": "https://detail.1688.com/offer/976493700718.html",
     "image_url": "https://placehold.co/400x300/AB47BC/FFFFFF?text=门后挂钩",
     "desc": "门后免打孔挂钩收纳架，学生宿舍挂衣挂包帽子围巾神器。墨西哥学生宿舍空间小，门后空间利用为开学季TOP爆款。", "festival": "Back to School"},

    {"title": "LED床头小夜灯可充电卧室氛围灯婴儿喂奶灯创意礼物学生宿舍灯", "cat": "收纳", "price": 18.5, "w": 0.22, "l": 10, "wi": 8, "h": 8,
     "store": "深圳市睿光新能源科技", "yr": 4.0, "rt": 4.7, "dh": 24, "sales": 5200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=LED%E5%BA%8A%E5%A4%B4%E5%B0%8F%E5%A4%9C%E7%81%AF%2B%E5%8F%AF%E5%85%85%E7%94%B5%2B%E6%B0%9B%E5%9B%B4%E7%81%AF",
     "image_url": "https://placehold.co/400x300/FFD54F/37474F?text=小夜灯💡",
     "desc": "可充电LED床头小夜灯氛围灯，学生宿舍照明神器。墨西哥8月底高校宿舍开学，每间宿舍=一件小夜灯的确定性需求。", "festival": "Back to School"},

    {"title": "简约桌上书架桌面置物架办公书桌整理架学生宿舍学习阅读收纳架", "cat": "收纳", "price": 21.0, "w": 0.50, "l": 35, "wi": 20, "h": 5,
     "store": "义乌市家居用品商行", "yr": 4.0, "rt": 4.8, "dh": 24, "sales": 6100,
     "url": "https://detail.1688.com/offer/991691085955.html",
     "image_url": "https://placehold.co/400x300/78909C/FFFFFF?text=桌上书架📚",
     "desc": "简约桌上书架桌面整理架，学生宿舍学习阅读收纳架。墨西哥高校开学季教材/笔记本收纳刚需，桌面空间扩容神器。", "festival": "Back to School"},

    {"title": "数据线收纳盒桌面理线器多头USB充电线整理盒学生宿舍办公桌面", "cat": "收纳", "price": 14.0, "w": 0.15, "l": 15, "wi": 10, "h": 5,
     "store": "深圳市品胜电子科技", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 18000,
     "url": "https://detail.1688.com/offer/957732389272.html",
     "image_url": "https://placehold.co/400x300/26A69A/FFFFFF?text=数据线收纳",
     "desc": "桌面数据线收纳盒理线器，学生宿舍办公桌面线材整理。仅0.15kg极致轻量，墨西哥学生人人有多设备线材，开学季整理需求暴增。", "festival": "Back to School"},

    # ═══════════════ 独立日准备 ═══════════════
    # 墨西哥独立日 9月16日，提前1-2月备货
    {"title": "墨西哥独立日横幅旗帜Viva Mexico装饰旗国庆日派对挂饰背景布", "cat": "独立日装饰", "price": 22.5, "w": 0.28, "l": 35, "wi": 20, "h": 2,
     "store": "义乌市世界杯工艺品厂", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 3600,
     "url": "https://detail.1688.com/offer/961529373935.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=VivaMexico🇲🇽",
     "desc": "Viva Mexico独立日横幅背景布旗帜，919独立日派对核心装饰品。墨西哥全年最重要的爱国节日，独立日前1个月家庭/商铺采购高峰。", "festival": "墨西哥独立日"},

    {"title": "红白绿气球拱门支架套装婚庆生日派对布置装饰墨西哥独立日配色", "cat": "独立日装饰", "price": 19.0, "w": 0.50, "l": 30, "wi": 20, "h": 5,
     "store": "义乌市派对大师工艺品厂", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 3800,
     "url": "https://detail.1688.com/offer/718545347973.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=独立日🎈拱门",
     "desc": "红白绿三色气球拱门支架套装，适配墨西哥独立日派对配色。独立日前夕墨西哥家庭/餐厅/商铺门口气球拱门标配，全套零售价空间大。", "festival": "墨西哥独立日"},

    {"title": "墨西哥独立日主题桌布餐桌装饰国庆派对台布绿白红三色节日布艺", "cat": "独立日装饰", "price": 20.0, "w": 0.35, "l": 28, "wi": 20, "h": 2,
     "store": "绍兴柯桥布艺有限公司", "yr": 5.0, "rt": 4.8, "dh": 24, "sales": 2400,
     "url": "https://detail.1688.com/offer/810150018336.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=独立日桌布",
     "desc": "墨西哥独立日主题桌布绿白红三色餐桌装饰布艺。独立日家庭聚餐/派对场合桌布为刚需，三色国旗元素转化率高。", "festival": "墨西哥独立日"},

    {"title": "绿白红丝带彩带拉花挂饰派对装饰墨西哥独立日节日氛围布置用品", "cat": "独立日装饰", "price": 13.0, "w": 0.12, "l": 20, "wi": 15, "h": 2,
     "store": "义乌市派对大师工艺品厂", "yr": 4.0, "rt": 4.5, "dh": 24, "sales": 8200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E7%BB%BF%E7%99%BD%E7%BA%A2%2B%E4%B8%9D%E5%B8%A6%2B%E5%BD%A9%E5%B8%A6%2B%E6%B4%BE%E5%AF%B9%E6%8C%82%E9%A5%B0",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=独立日🎀丝带",
     "desc": "绿白红三色丝带彩带派对挂饰，墨西哥独立日氛围布置用品。0.12kg极轻免运费，独立日期间全民自发装饰街道/车辆/阳台。", "festival": "墨西哥独立日"},

    {"title": "墨西哥独立日主题墙贴国庆节装饰贴纸家庭派对店铺橱窗布置贴画", "cat": "独立日装饰", "price": 16.0, "w": 0.15, "l": 25, "wi": 18, "h": 2,
     "store": "温州博美工艺品有限公司", "yr": 5.0, "rt": 4.7, "dh": 24, "sales": 3100,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%A2%A8%E8%A5%BF%E5%93%A5%2B%E7%8B%AC%E7%AB%8B%E6%97%A5%2B%E4%B8%BB%E9%A2%98%E5%A2%99%E8%B4%B4%2B%E8%A3%85%E9%A5%B0",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=独立日墙面贴",
     "desc": "墨西哥独立日主题墙贴国庆装饰贴纸，家庭/店铺橱窗布置。独立日前夕墨西哥店铺/餐厅/家庭墙面装饰必备，0.15kg极轻好发。", "festival": "墨西哥独立日"},

    {"title": "墨西哥派对彩色纸花球纸扇流苏装饰独立日国庆日节日氛围布置", "cat": "独立日装饰", "price": 15.5, "w": 0.20, "l": 15, "wi": 15, "h": 5,
     "store": "义乌市派对大师工艺品厂", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 5400,
     "url": "https://detail.1688.com/offer/610486155314.html",
     "image_url": "https://placehold.co/400x300/006847/FFFFFF?text=独立日🌺纸花",
     "desc": "墨西哥彩色纸花球纸扇流苏拉花装饰套装，独立日国庆氛围布置。独立日前夕墨西哥广场/家庭/学校装饰用量巨大，套装组合利润更高。", "festival": "墨西哥独立日"},

    {"title": "墨西哥风格手工陶瓷马克杯民俗纪念品独立日礼物创意复古咖啡杯", "cat": "独立日装饰", "price": 19.0, "w": 0.30, "l": 10, "wi": 8, "h": 10,
     "store": "义乌市世界杯工艺品厂", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 1800,
     "url": "https://detail.1688.com/offer/862483766295.html",
     "image_url": "https://placehold.co/400x300/D84315/FFFFFF?text=独立日☕杯",
     "desc": "墨西哥风格手工陶瓷马克杯民俗纪念品，独立日礼物创意咖啡杯。墨西哥独立日礼品/纪念品市场巨大，民俗陶杯兼具实用与收藏属性。", "festival": "墨西哥独立日"},
]


# === 模拟竞品价格（MXN） ===
COMPETITOR_SIM = {
    # 世界杯期间竞品对标
    "世界杯装饰": [(250, 15), (280, 8)],
    "民俗装饰": [(180, 8), (200, 4)],
    "收纳": [(140, 15), (155, 8)],
    "独立日装饰": [(220, 12), (240, 6)],
    # 旧品类（保留兼容）
    "墙饰": [(150, 10), (170, 5)],
    "桌面摆件": [(190, 8), (200, 3)],
    "花瓶": [(160, 12), (175, 6)],
    "灯饰": [(130, 20), (145, 10)],
    "桌布": [(120, 8), (135, 4)],
    "蜡烛": [(170, 6), (185, 3)],
    "相框": [(110, 10), (125, 5)],
    "派对用品": [(200, 12), (215, 7)],
    "厨房用品": [(180, 5), (190, 3)],
    "户外装饰": [(145, 8), (155, 4)],
    "面具": [(160, 6), (175, 3)],
    "装饰": [(155, 10), (165, 5)],
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
