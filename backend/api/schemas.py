"""Pydantic 请求/响应模式定义"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


# === 商品相关 ===
class ProductOut(BaseModel):
    id: int
    rank: int
    score: float
    product: dict
    cost: dict
    pricing: dict
    competition: dict
    logistics: dict
    reason: dict
    store: dict
    tags: list

    class Config:
        from_attributes = True


class DailyResultOut(BaseModel):
    date: str
    generated_at: str
    summary: dict
    active_festivals: list
    products: list


# === Dashboard ===
class DashboardSummary(BaseModel):
    today_date: str
    today_product_count: int
    today_avg_margin: float
    active_festivals: list
    recent_dates: list


class HistoryItem(BaseModel):
    date: str
    selected_count: int
    avg_margin: float
    avg_price_mxn: float
    active_festivals: list


# === Admin/设置 ===
class LogisticsParamsUpdate(BaseModel):
    air_freight_per_kg: Optional[float] = None
    volumetric_divisor: Optional[float] = None
    packaging_fee: Optional[float] = None
    last_mile_base_fee: Optional[float] = None
    damage_rate: Optional[float] = None
    commission_rate: Optional[float] = None
    mxn_to_rmb: Optional[float] = None


class TriggerPipelineRequest(BaseModel):
    target_date: Optional[str] = None  # YYYY-MM-DD, None = today


class PipelineStatus(BaseModel):
    status: str
    message: str
    products_count: int = 0
