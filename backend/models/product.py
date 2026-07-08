"""商品模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from backend.models.database import Base


class Product(Base):
    """采集的原始商品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(128), unique=True, index=True, comment="1688商品ID")
    title_zh = Column(String(512), comment="中文标题")
    title_es = Column(String(512), default="", comment="西班牙语标题（机器翻译）")
    category = Column(String(128), comment="品类")
    image_url = Column(String(1024), comment="主图URL")
    source_url = Column(String(1024), comment="1688商品链接")
    description = Column(Text, default="", comment="中文产品描述")
    description_es = Column(Text, default="", comment="西班牙语描述")

    # 成本
    purchase_price_rmb = Column(Float, comment="1688进货价(RMB)")

    # 物流规格
    actual_weight_kg = Column(Float, comment="实际重量(kg)")
    length_cm = Column(Float, default=0.0)
    width_cm = Column(Float, default=0.0)
    height_cm = Column(Float, default=0.0)

    # 店铺
    store_name = Column(String(256))
    store_years_active = Column(Float, default=0.0)
    store_rating = Column(Float, default=0.0)
    store_delivery_hours = Column(Integer, default=72)

    # 1688元数据
    sales_volume = Column(Integer, default=0, comment="1688销量")
    supports_dropshipping = Column(Boolean, default=False, comment="支持一件代发")

    # 算法计算结果（在流程中填充）
    volumetric_weight_kg = Column(Float, default=0.0)
    chargeable_weight_kg = Column(Float, default=0.0)
    air_freight_rmb = Column(Float, default=0.0)
    total_cost_rmb = Column(Float, default=0.0)

    # 定价
    suggested_price_rmb = Column(Float, default=0.0)
    suggested_price_mxn = Column(Float, default=0.0)
    markup_ratio = Column(Float, default=0.0)
    estimated_margin = Column(Float, default=0.0)

    # 竞品
    temu_mx_lowest_mxn = Column(Float, nullable=True)
    shopee_mx_lowest_mxn = Column(Float, nullable=True)
    competitor_count = Column(Integer, default=0)

    # 评分
    score = Column(Float, default=0.0)
    festival_match_score = Column(Float, default=0.0)

    # 选品理由
    reason_primary = Column(String(512), default="")
    reason_details = Column(Text, default="")
    festival_relevance = Column(String(256), default="")

    # 前端标签
    tags = Column(JSON, default=list)

    # 审计
    is_selected = Column(Boolean, default=False, comment="是否被选入当日Top-20")
    selection_date = Column(DateTime, nullable=True, comment="被选中的日期")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
