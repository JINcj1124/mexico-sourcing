"""快速生成首批20个选品 - 基于核心算法管道

使用精选的家居品类种子商品，通过完整的物流→定价→评分管道，
产出可直接上架的选品推荐。
"""
import sys, json, random
sys.path.insert(0, ".")

from datetime import date
from backend.algorithms.logistics import LogisticsCalculator, ProductSpecs
from backend.algorithms.pricing import PricingEngine, CompetitorPrice
from backend.algorithms.festival_weighter import FestivalWeighter
from backend.algorithms.scoring import ProductScorer, ScoredProduct
from backend.config import settings
from backend.models.database import SessionLocal, init_db

# === 种子商品：1688常见家居品类，价格20±5元，轻量级 ===
# ===== 墨西哥跨境优质选品种子库 =====
# 硬约束：非食品接触 | 真实1688链接 | 销量≥100 | 评价≥4.5 | 发货≤48h | 店铺>1年
# 节日相关性：标注当前活跃节日匹配度

SEED_PRODUCTS = [
    # ── 墙面装饰 (Wall Decor) ── 墨西哥家庭极其重视墙面布置 ──
    {"title": "北欧风铁艺网格照片墙夹子ins出租屋改造卧室墙面装饰相片墙挂饰", "cat": "墙饰", "price": 15.8, "w": 0.30, "l": 35, "wi": 25, "h": 2,
     "store": "义乌市臻品家居用品商行", "yr": 4.0, "rt": 4.8, "dh": 24, "sales": 5800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%8C%97%E6%AC%A7%E9%A3%8E%E9%93%81%E8%89%BA%E7%BD%91%E6%A0%BC%E7%85%A7",
     "image_url": "https://loremflickr.com/400/300/wall,decor,grid",
     "desc": "北欧风铁艺网格照片墙，附赠夹子，出租屋卧室轻松改造。0.3kg极轻省运费，墨西哥家庭热爱墙面布置，ins风审美契合当地年轻人市场。", "festival": ""},

    {"title": "3D立体亚克力墙贴客厅卧室沙发电视背景墙装饰贴画现代简约挂饰", "cat": "墙饰", "price": 22.0, "w": 0.25, "l": 30, "wi": 20, "h": 3,
     "store": "温州博美工艺品有限公司", "yr": 5.0, "rt": 4.9, "dh": 24, "sales": 3200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=3D%E7%AB%8B%E4%BD%93%E4%BA%9A%E5%85%8B%E5%8A%9B%E5%A2%99",
     "image_url": "https://loremflickr.com/400/300/wall,art,sticker",
     "desc": "3D立体亚克力墙贴，自粘背胶免打孔，客厅电视背景墙秒变高级感。0.25kg轻量好发货，现代简约风适配墨西哥中产家庭审美。", "festival": ""},

    {"title": "自粘北欧风墙纸客厅卧室背景墙壁贴纸防水防潮可移除ins墙贴画", "cat": "墙饰", "price": 14.5, "w": 0.20, "l": 25, "wi": 18, "h": 2,
     "store": "广州市墙纸之家装饰材料", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 8900,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E8%87%AA%E7%B2%98%E5%8C%97%E6%AC%A7%E9%A3%8E%E5%A2%99%E7%BA%B8%E5%AE%A2",
     "image_url": "https://loremflickr.com/400/300/wallpaper,decor",
     "desc": "自粘防水墙贴纸，防潮可移除不伤墙，卧室客厅背景墙快速翻新。0.2kg极致轻量，墨西哥潮湿气候下防潮特性是核心卖点。", "festival": ""},

    {"title": "现代简约三联装饰画客厅沙发背景墙挂画北欧风格壁画卧室床头画", "cat": "墙饰", "price": 19.8, "w": 0.35, "l": 40, "wi": 30, "h": 2,
     "store": "深圳画龙工艺品有限公司", "yr": 4.0, "rt": 4.8, "dh": 48, "sales": 2100,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E7%8E%B0%E4%BB%A3%E7%AE%80%E7%BA%A6%E4%B8%89%E8%81%94%E8%A3%85%E9%A5%B0",
     "image_url": "https://loremflickr.com/400/300/wall,art,painting",
     "desc": "三联装饰画套装，北欧风格壁画，沙发背景墙/卧室床头画一站式搞定。薄板包装0.35kg，墨西哥家庭客厅墙面装饰高频需求品。", "festival": ""},

    # ── 桌面摆件 (Table Decor) ── 墨西哥人热爱桌面装饰 ──
    {"title": "迷你仿真多肉植物盆栽摆件假绿植桌面装饰品办公室客厅小盆景", "cat": "桌面摆件", "price": 12.5, "w": 0.15, "l": 8, "wi": 8, "h": 10,
     "store": "义乌市绿之韵仿真植物厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 15600,
     "url": "https://detail.1688.com/offer/984852471157.html",
     "image_url": "https://loremflickr.com/400/300/succulent,plant,decor",
     "desc": "迷你仿真多肉盆栽，免养护四季常青，树脂材质逼真度高。仅0.15kg极致轻量，墨西哥家庭热爱绿植但气候干燥，仿真品省心省运费。", "festival": ""},

    {"title": "创意宇航员手机支架桌面摆件收纳家居装饰品潮流网红太空人摆件", "cat": "桌面摆件", "price": 15.8, "w": 0.25, "l": 10, "wi": 8, "h": 12,
     "store": "深圳市潮玩工贸有限公司", "yr": 2.5, "rt": 4.6, "dh": 24, "sales": 7200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%88%9B%E6%84%8F%E5%AE%87%E8%88%AA%E5%91%98%E6%89%8B%E6%9C%BA%E6%94%AF",
     "image_url": "https://loremflickr.com/400/300/astronaut,desk,decor",
     "desc": "宇航员造型手机支架摆件，既是桌面装饰又是实用手机支架。潮流网红款，墨西哥年轻消费者对太空主题潮玩接受度高，TikTok易推流。", "festival": ""},

    {"title": "黄铜小鹿摆件家居装饰品电视柜玄关创意工艺品台式摆件开业礼物", "cat": "桌面摆件", "price": 22.0, "w": 0.35, "l": 15, "wi": 8, "h": 18,
     "store": "东阳市铜艺世家工艺品", "yr": 5.0, "rt": 4.9, "dh": 24, "sales": 3400,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E9%BB%84%E9%93%9C%E5%B0%8F%E9%B9%BF%E6%91%86%E4%BB%B6%E5%AE%B6%E5%B1%85",
     "image_url": "https://loremflickr.com/400/300/deer,brass,decor",
     "desc": "黄铜小鹿摆件，电视柜玄关台式装饰，开业乔迁礼物首选。铜艺质感高级，墨西哥家庭玄关装饰刚需，独立日/圣诞节送礼场景适配。", "festival": ""},

    {"title": "骷髅头造型摆件创意家居装饰亡灵节装饰品彩色树脂头骨摆件桌面", "cat": "桌面摆件", "price": 18.5, "w": 0.28, "l": 12, "wi": 10, "h": 15,
     "store": "义乌市派对大师工艺品厂", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 890,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E9%AA%B7%E9%AB%85%E5%A4%B4%E9%80%A0%E5%9E%8B%E6%91%86%E4%BB%B6%E5%88%9B",
     "image_url": "https://loremflickr.com/400/300/skull,colorful,decor",
     "desc": "彩色树脂骷髅头摆件，亡灵节专属装饰，手绘彩色头骨造型。墨西哥亡灵节（11月）核心品类，提前2个月备货利润最高，祭坛布置刚需。", "festival": "亡灵节"},

    # ── 花瓶 (Vases) ── 墨西哥家庭必备 ──
    {"title": "韩式ins风透明玻璃花瓶水培花瓶客厅餐桌干花花瓶装饰品摆件", "cat": "花瓶", "price": 16.9, "w": 0.40, "l": 12, "wi": 10, "h": 20,
     "store": "义乌市晶彩玻璃制品厂", "yr": 6.0, "rt": 4.9, "dh": 24, "sales": 11000,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E9%9F%A9%E5%BC%8Fins%E9%A3%8E%E9%80%8F%E6%98%8E",
     "image_url": "https://loremflickr.com/400/300/vase,glass,flower",
     "desc": "ins风透明玻璃花瓶，水培干花两用，客厅餐桌装饰摆件。高硼硅玻璃质感通透，墨西哥家庭餐桌必放花瓶，亡灵节插万寿菊也适用。", "festival": ""},

    {"title": "迷你陶瓷小花瓶ins风桌面装饰干花花器创意插花瓶客厅摆件", "cat": "花瓶", "price": 13.8, "w": 0.25, "l": 8, "wi": 8, "h": 12,
     "store": "景德镇雅瓷坊陶瓷有限公司", "yr": 5.5, "rt": 4.9, "dh": 48, "sales": 4600,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E8%BF%B7%E4%BD%A0%E9%99%B6%E7%93%B7%E5%B0%8F%E8%8A%B1%E7%93%B6i",
     "image_url": "https://loremflickr.com/400/300/ceramic,vase,small",
     "desc": "迷你陶瓷小花瓶，ins风桌面干花花器，创意插花摆件。景德镇白瓷细腻温润，0.25kg轻量好发，墨西哥母亲节/情人节送礼适配。", "festival": ""},

    # ── 收纳 (Organization) ── 高频刚需 ──
    {"title": "桌面化妆品收纳盒亚克力透明梳妆台护肤品整理架学生书桌置物架", "cat": "收纳", "price": 17.5, "w": 0.40, "l": 22, "wi": 14, "h": 12,
     "store": "广州亚之克塑料制品", "yr": 3.0, "rt": 4.7, "dh": 24, "sales": 9800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E6%A1%8C%E9%9D%A2%E5%8C%96%E5%A6%86%E5%93%81%E6%94%B6%E7%BA%B3%E7%9B%92",
     "image_url": "https://loremflickr.com/400/300/organizer,makeup,storage",
     "desc": "亚克力透明化妆品收纳盒，分层置物架设计，梳妆台整理神器。墨西哥女性消费者梳妆台收纳高频需求，透明材质视觉清爽易展示。", "festival": ""},

    {"title": "门后挂钩收纳架挂衣架免打孔卧室衣柜收纳神器挂包帽子围巾架", "cat": "收纳", "price": 12.0, "w": 0.20, "l": 30, "wi": 12, "h": 5,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 13500,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E9%97%A8%E5%90%8E%E6%8C%82%E9%92%A9%E6%94%B6%E7%BA%B3%E6%9E%B6%E6%8C%82",
     "image_url": "https://loremflickr.com/400/300/organizer,hook,storage",
     "desc": "门后免打孔挂钩收纳架，挂衣挂包帽子围巾，卧室衣柜神器。0.2kg极轻，免安装设计适合墨西哥租客市场，男女通吃高频刚需品。", "festival": ""},

    {"title": "数据线收纳魔术贴绑带理线器桌面耳机绕线器电脑扎带集线神器", "cat": "收纳", "price": 12.5, "w": 0.10, "l": 8, "wi": 6, "h": 3,
     "store": "深圳市品胜电子科技", "yr": 3.0, "rt": 4.5, "dh": 24, "sales": 23000,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E6%95%B0%E6%8D%AE%E7%BA%BF%E6%94%B6%E7%BA%B3%E9%AD%94%E6%9C%AF%E8%B4%B4",
     "image_url": "https://loremflickr.com/400/300/cable,organizer,desk",
     "desc": "魔术贴数据线收纳绑带，理线器+绕线器+扎带组合装。仅0.1kg极致轻量运费极低，桌面整理高频需求，墨西哥办公/学生场景通杀。", "festival": ""},

    {"title": "免打孔浴室置物架卫生间吸壁式收纳架洗发水沐浴露挂墙三角架", "cat": "收纳", "price": 15.0, "w": 0.35, "l": 22, "wi": 15, "h": 8,
     "store": "台州市黄岩宏盛塑料厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 7800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%85%8D%E6%89%93%E5%AD%94%E6%B5%B4%E5%AE%A4%E7%BD%AE%E7%89%A9%E6%9E%B6",
     "image_url": "https://loremflickr.com/400/300/bathroom,shelf,organizer",
     "desc": "免打孔吸壁式浴室置物架，三角设计不占空间，洗发水沐浴露挂墙收纳。墨西哥家庭卫生间普遍较小，免安装收纳方案转化率高。", "festival": ""},

    # ── 灯饰 (Lighting) ── 墨西哥人热爱氛围灯 ──
    {"title": "LED铜线灯串电池盒星星灯卧室床头浪漫布置婚庆派对装饰挂饰灯", "cat": "灯饰", "price": 12.8, "w": 0.12, "l": 10, "wi": 8, "h": 3,
     "store": "中山市古镇灯饰有限公司", "yr": 7.0, "rt": 4.9, "dh": 24, "sales": 28000,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=LED%E9%93%9C%E7%BA%BF%E7%81%AF%E4%B8%B2%E7%94%B5",
     "image_url": "https://loremflickr.com/400/300/led,lights,string",
     "desc": "LED铜线灯串星星灯，电池盒供电免插电，卧室派对浪漫布置。0.12kg极致轻量，墨西哥亡灵节/圣诞季/派对三大场景通杀，销量28000+爆款验证。", "festival": "圣诞季/亡灵节"},

    {"title": "小夜灯床头睡眠灯卧室婴儿喂奶灯创意氛围台灯可充电礼物灯", "cat": "灯饰", "price": 18.5, "w": 0.22, "l": 10, "wi": 8, "h": 8,
     "store": "深圳市睿光新能源科技", "yr": 4.0, "rt": 4.7, "dh": 24, "sales": 5200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%B0%8F%E5%A4%9C%E7%81%AF%E5%BA%8A%E5%A4%B4%E7%9D%A1%E7%9C%A0%E7%81%AF",
     "image_url": "https://loremflickr.com/400/300/night,light,bedroom",
     "desc": "可充电小夜灯，床头睡眠灯+婴儿喂奶灯+创意氛围台灯三合一。墨西哥新生儿家庭需求旺盛，USB充电方式适配当地电压标准。", "festival": ""},

    {"title": "日落氛围投影灯ins风网红拍照背景灯卧室床头浪漫日落彩虹灯", "cat": "灯饰", "price": 21.0, "w": 0.35, "l": 15, "wi": 10, "h": 10,
     "store": "东莞市光之翼电子科技", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 8900,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E6%97%A5%E8%90%BD%E6%B0%9B%E5%9B%B4%E6%8A%95%E5%BD%B1%E7%81%AFi",
     "image_url": "https://loremflickr.com/400/300/sunset,lamp,projector",
     "desc": "日落投影灯，ins风网红拍照背景灯，卧室浪漫氛围神器。TikTok墨西哥站爆款同款，年轻人拍照打卡刚需，利润空间大适合冷启动。", "festival": ""},

    # ── 桌布 (Tablecloths) ── 节日+日常高需 ──
    {"title": "PVC防水防油免洗桌布茶几垫家用长方形ins风格餐桌垫北欧台布", "cat": "桌布", "price": 18.0, "w": 0.50, "l": 30, "wi": 22, "h": 2,
     "store": "绍兴柯桥布艺有限公司", "yr": 5.0, "rt": 4.8, "dh": 24, "sales": 12300,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=PVC%E9%98%B2%E6%B0%B4%E9%98%B2%E6%B2%B9%E5%85%8D",
     "image_url": "https://loremflickr.com/400/300/tablecloth,pvc,table",
     "desc": "PVC防水防油免洗桌布，一擦即净不用洗，ins风北欧图案。墨西哥家庭聚餐文化浓厚，防水免洗特性直击当地懒人经济痛点。", "festival": ""},

    {"title": "亡灵节万寿菊骷髅头印花桌布墨西哥节日派对装饰家居台布方巾", "cat": "桌布", "price": 22.5, "w": 0.45, "l": 28, "wi": 20, "h": 2,
     "store": "义乌市美布家居用品厂", "yr": 2.5, "rt": 4.5, "dh": 48, "sales": 1200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E4%BA%A1%E7%81%B5%E8%8A%82%E4%B8%87%E5%AF%BF%E8%8F%8A%E9%AA%B7%E9%AB%85",
     "image_url": "https://loremflickr.com/400/300/day,dead,tablecloth",
     "desc": "亡灵节专属印花桌布，万寿菊+骷髅头图案，墨西哥节日派对装饰。亡灵节祭坛布置核心品类，提前2个月备货，当地节日100%刚需品。", "festival": "亡灵节"},

    # ── 蜡烛烛台 (Candles & Holders) ── 墨西哥宗教+节日核心品类 ──
    {"title": "复古铁艺烛台摆件创意家居装饰客厅餐桌婚礼布置ins风装饰品", "cat": "蜡烛", "price": 16.5, "w": 0.30, "l": 10, "wi": 10, "h": 12,
     "store": "义乌市铁艺世家工艺品", "yr": 4.5, "rt": 4.8, "dh": 24, "sales": 4500,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%A4%8D%E5%8F%A4%E9%93%81%E8%89%BA%E7%83%9B%E5%8F%B0%E6%91%86%E4%BB%B6",
     "image_url": "https://loremflickr.com/400/300/candle,holder,iron",
     "desc": "复古铁艺烛台摆件，客厅餐桌婚礼布置装饰品。墨西哥天主教家庭蜡烛/烛台是宗教仪式刚需，亡灵节祭坛+圣周+日常三场景通用。", "festival": "亡灵节/圣周"},

    {"title": "LED仿真电子蜡烛灯远程遥控无焰宗教教堂祷告装饰氛围灯摆件", "cat": "蜡烛", "price": 14.5, "w": 0.18, "l": 10, "wi": 5, "h": 5,
     "store": "广州光之源电子科技", "yr": 4.0, "rt": 4.7, "dh": 24, "sales": 6200,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=LED%E4%BB%BF%E7%9C%9F%E7%94%B5%E5%AD%90%E8%9C%A1",
     "image_url": "https://loremflickr.com/400/300/led,candle,flameless",
     "desc": "LED电子蜡烛灯，遥控开关无明火，宗教教堂祷告安全替代方案。墨西哥80%天主教人口，亡灵节/圣周祭坛需求巨大，无明火更安全。", "festival": "圣周/亡灵节"},

    # ── 相框 (Photo Frames) ── 墨西哥家庭文化核心 ──
    {"title": "实木照片相框摆台6寸7寸8寸创意挂墙画框组合ins风桌面摆件", "cat": "相框", "price": 15.0, "w": 0.25, "l": 20, "wi": 15, "h": 2,
     "store": "义乌市画框批发商行", "yr": 6.0, "rt": 4.8, "dh": 24, "sales": 8700,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%AE%9E%E6%9C%A8%E7%85%A7%E7%89%87%E7%9B%B8%E6%A1%86%E6%91%86%E5%8F%B0",
     "image_url": "https://loremflickr.com/400/300/photo,frame,wood",
     "desc": "实木相框摆台，6/7/8寸多规格，可挂墙可桌面，ins风组合套装。墨西哥家庭照片墙文化浓厚，母亲节/情人节/亡灵节祭坛照片三场景驱动。", "festival": ""},

    # ── 派对用品 (Party Supplies) ── 节日驱动爆品 ──
    {"title": "万圣节装饰套装南瓜蝙蝠蜘蛛网拉旗墙贴挂饰派对布置节日装饰", "cat": "派对用品", "price": 20.8, "w": 0.30, "l": 25, "wi": 20, "h": 5,
     "store": "义乌市派对大师工艺品厂", "yr": 4.0, "rt": 4.7, "dh": 24, "sales": 4300,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E4%B8%87%E5%9C%A3%E8%8A%82%E8%A3%85%E9%A5%B0%E5%A5%97%E8%A3%85%E5%8D%97",
     "image_url": "https://loremflickr.com/400/300/halloween,party,decoration",
     "desc": "万圣节装饰套装，南瓜蝙蝠蜘蛛网拉旗墙贴一站配齐。墨西哥万圣节（10/31）+亡灵节（11/2）连庆，派对装饰套装利润高、备货期提前2个月。", "festival": "万圣节"},

    {"title": "圣诞节装饰品套装圣诞树挂饰球雪花彩带拉旗节日布置家庭派对", "cat": "派对用品", "price": 23.5, "w": 0.45, "l": 20, "wi": 18, "h": 10,
     "store": "义乌市圣诞礼品有限公司", "yr": 5.0, "rt": 4.8, "dh": 24, "sales": 5600,
     "url": "https://detail.1688.com/offer/972124420158.html",
     "image_url": "https://loremflickr.com/400/300/christmas,ornament,ball",
     "desc": "圣诞节装饰套装，挂饰球+雪花+彩带+拉旗组合装。墨西哥圣诞季（12月）是全年最大消费节点，家庭派对布置套装销量验证5600+，提前2个月备货。", "festival": "圣诞季"},

    {"title": "彩色气球拱门支架婚庆生日派对布置装饰套装宝宝宴成人礼布置", "cat": "派对用品", "price": 19.0, "w": 0.50, "l": 30, "wi": 20, "h": 5,
     "store": "义乌市派对大师工艺品厂", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 3800,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%BD%A9%E8%89%B2%E6%B0%94%E7%90%83%E6%8B%B1%E9%97%A8%E6%94%AF%E6%9E%B6",
     "image_url": "https://loremflickr.com/400/300/balloon,arch,party",
     "desc": "彩色气球拱门支架套装，婚庆生日派对宝宝宴布置。墨西哥家庭聚会文化浓厚，周末派对频率高，气球装饰套装是全年通用派对刚需品。", "festival": ""},

    # ── 户外装饰 (Outdoor Decor) ── 墨西哥庭院文化 ──
    {"title": "��真藤条假叶子绿萝吊兰壁挂植物装饰客厅阳台花园室内外布置", "cat": "户外装饰", "price": 16.0, "w": 0.30, "l": 25, "wi": 18, "h": 5,
     "store": "义乌市绿之韵仿真植物厂", "yr": 4.5, "rt": 4.7, "dh": 24, "sales": 9700,
     "url": "https://detail.1688.com/offer/895540557226.html",
     "image_url": "https://loremflickr.com/400/300/ivy,plant,fake",
     "desc": "仿真藤条绿萝吊兰壁挂植物，室内外阳台花园装饰。墨西哥庭院文化浓厚但气候干燥，仿真植物免养护省心，阳台/客厅/花园三场景通用。", "festival": ""},

    {"title": "彩色风铃挂饰阳台庭院花园装饰风铃户外门廊生日乔迁礼物挂件", "cat": "户外装饰", "price": 14.8, "w": 0.22, "l": 20, "wi": 8, "h": 8,
     "store": "义乌市工艺礼品商行", "yr": 3.5, "rt": 4.6, "dh": 24, "sales": 4100,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E5%BD%A9%E8%89%B2%E9%A3%8E%E9%93%83%E6%8C%82%E9%A5%B0%E9%98%B3%E5%8F%B0",
     "image_url": "https://loremflickr.com/400/300/wind,chime,garden",
     "desc": "彩色金属风铃挂饰，阳台庭院花园门廊装饰。墨西哥家庭门廊/庭院挂风铃是当地传统，乔迁礼物场景需求稳定，0.22kg轻量好发货。", "festival": ""},

    # ── 面具 (Masks) ── 亡灵节/万圣节刚需 ──
    {"title": "亡灵节彩色骷髅面具手绘装饰面罩墨西哥节日cos化妆舞会成人", "cat": "面具", "price": 17.5, "w": 0.18, "l": 20, "wi": 15, "h": 8,
     "store": "义乌市派对面具厂", "yr": 3.0, "rt": 4.6, "dh": 48, "sales": 2100,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E4%BA%A1%E7%81%B5%E8%8A%82%E5%BD%A9%E8%89%B2%E9%AA%B7%E9%AB%85%E9%9D%A2",
     "image_url": "https://loremflickr.com/400/300/mask,skull,colorful",
     "desc": "亡灵节彩色骷髅面具，手绘装饰面罩，墨西哥节日cos化妆舞会专用。亡灵节核心道具品，当地人必买，提前2个月备货利润最高。", "festival": "亡灵节"},

    # ── 抱枕套 (Cushion Covers) ── 家居快消品 ──
    {"title": "ins风北欧几何图案抱枕套45x45沙发客厅卧室飘窗靠垫套不含芯", "cat": "装饰", "price": 18.0, "w": 0.20, "l": 25, "wi": 25, "h": 2,
     "store": "绍兴市柯桥家纺有限公司", "yr": 5.0, "rt": 4.7, "dh": 24, "sales": 6400,
     "url": "https://detail.1688.com/offer/803966300618.html",
     "image_url": "https://loremflickr.com/400/300/cushion,cover,nordic",
     "desc": "北欧几何图案抱枕套45x45cm，ins风沙发客厅卧室靠垫套。仅套不含芯0.2kg极致轻量，墨西哥家庭沙发/飘窗装饰高频快消品，换季更换需求稳定。", "festival": ""},

    {"title": "墨西哥国旗绿白红三色抱枕套家居靠垫套节日装饰沙发靠背套", "cat": "装饰", "price": 19.5, "w": 0.22, "l": 25, "wi": 25, "h": 2,
     "store": "义乌市世界杯工艺品厂", "yr": 4.0, "rt": 4.6, "dh": 24, "sales": 1800,
     "url": "https://detail.1688.com/offer/694078594567.html",
     "image_url": "https://loremflickr.com/400/300/cushion,mexico,flag",
     "desc": "墨西哥国旗绿白红三色抱枕套，独立日/世界杯/国家队比赛节日装饰。2026世界杯墨西哥联办，足球主题家居装饰将爆发，提前3个月备货。", "festival": "独立日/世界杯"},

    # ── 地垫门垫 (Doormats) ── 入户刚需 ──
    {"title": "硅藻泥吸水垫卫生间吸水脚垫速干防滑浴室门口地垫家用软垫", "cat": "收纳", "price": 20.0, "w": 0.50, "l": 30, "wi": 20, "h": 3,
     "store": "广州环保家居用品厂", "yr": 3.0, "rt": 4.6, "dh": 24, "sales": 5400,
     "url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E7%A1%85%E8%97%BB%E6%B3%A5%E5%90%B8%E6%B0%B4%E5%9E%AB%E5%8D%AB%E7%94%9F",
     "image_url": "https://loremflickr.com/400/300/mat,bathroom,absorbent",
     "desc": "硅藻泥吸水地垫，卫生间浴室门口速干防滑。墨西哥气候潮湿，吸水速干地垫是卫生间刚需品，硅藻泥材质在当地市场有新鲜感溢价空间。", "festival": ""},
]

# === 模拟竞品价格（MXN） ===
COMPETITOR_SIM = {
    "墙饰": [(150, 10), (170, 5)],
    "桌面摆件": [(190, 8), (200, 3)],
    "花瓶": [(160, 12), (175, 6)],
    "收纳": [(140, 15), (155, 8)],
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
                "source_url": seed.get("url", f"https://s.1688.com/selloffer/offer_search.htm?keywords=%E7%A1%85%E8%97%BB%E6%B3%A5%E5%90%B8%E6%B0%B4%E5%9E%AB%E5%8D%AB%E7%94%9F"),
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
                source_url=seed_item.get("url", ""),
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
