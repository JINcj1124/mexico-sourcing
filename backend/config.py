"""全局配置管理"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """应用配置"""

    # --- 运行环境 ---
    env: str = "development"
    debug: bool = True

    # --- 数据库 ---
    db_path: str = str(PROJECT_ROOT / "data" / "sourcing.db")

    # --- 物流参数（可动态覆盖） ---
    air_freight_per_kg: float = 55.0        # 中墨空运 RMB/kg
    volumetric_divisor: float = 6000.0       # 体积重除数 cm³/kg
    packaging_fee: float = 3.0               # 一件代发打包费 RMB
    last_mile_base_fee: float = 18.0         # 尾程费基数 RMB
    damage_rate: float = 0.015               # 物损率
    commission_rate: float = 0.08            # 平台佣金率

    # --- 定价参数 ---
    mxn_to_rmb: float = 0.42                 # 墨西哥比索汇率
    min_markup: float = 6.0                  # 最低溢价倍率
    max_purchase_price: float = 25.0         # 进货价上限 RMB
    min_purchase_price: float = 12.0         # 进货价下限 RMB
    max_weight_kg: float = 2.0               # 重量上限 kg
    min_weight_kg: float = 0.1               # 重量下限 kg
    target_sku_count: int = 20               # 每日精选数量

    # --- 爬虫参数 ---
    crawler_request_interval_min: float = 3.0
    crawler_request_interval_max: float = 8.0
    crawler_headless: bool = True
    crawler_timeout_ms: int = 30000
    search_pages_per_keyword: int = 3

    # --- Webhook ---
    wecom_webhook_url: str = ""
    dingtalk_webhook_url: str = ""

    # --- 输出路径 ---
    output_daily_dir: str = str(PROJECT_ROOT / "output" / "daily")
    output_excel_dir: str = str(PROJECT_ROOT / "output" / "excel")

    # --- 日历文件 ---
    festival_calendar_path: str = str(PROJECT_ROOT / "data" / "festival_calendar.json")
    category_mapping_path: str = str(PROJECT_ROOT / "data" / "category_mapping.json")
    keyword_templates_path: str = str(PROJECT_ROOT / "data" / "keyword_templates.json")

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
