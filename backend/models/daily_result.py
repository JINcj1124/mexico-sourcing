"""每日选品结果模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from backend.models.database import Base


class DailyResult(Base):
    """每日选品结果快照"""
    __tablename__ = "daily_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, index=True, comment="日期 YYYY-MM-DD")
    generated_at = Column(DateTime, default=datetime.utcnow)

    # 统计摘要
    total_candidates = Column(Integer, default=0)
    selected_count = Column(Integer, default=0)
    avg_margin = Column(Float, default=0.0)
    avg_price_mxn = Column(Float, default=0.0)

    # 活跃节日
    active_festivals = Column(JSON, default=list)

    # 选品结果JSON（存储完整数据以避免连表查询）
    products_json = Column(JSON, default=list)


class CrawlerLog(Base):
    """爬虫运行日志"""
    __tablename__ = "crawler_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crawler_name = Column(String(64), comment="爬虫名称")
    task_date = Column(String(10), comment="任务日期")
    status = Column(String(32), default="running", comment="running/success/failed")
    items_collected = Column(Integer, default=0)
    error_message = Column(String(1024), default="")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
