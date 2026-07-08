"""Dashboard 数据接口"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.daily_result import DailyResult
from backend.algorithms.festival_weighter import FestivalWeighter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Dashboard 摘要数据"""
    today_str = date.today().isoformat()

    # 今日数据
    today_data = db.query(DailyResult).filter(DailyResult.date == today_str).first()

    # 最近7天日期列表
    recent_dates = [
        (date.today() - timedelta(days=i)).isoformat()
        for i in range(7)
    ]

    # 活跃节日
    weighter = FestivalWeighter()
    active = weighter.get_active_festivals()

    return {
        "today_date": today_str,
        "today_product_count": today_data.selected_count if today_data else 0,
        "today_avg_margin": today_data.avg_margin if today_data else 0,
        "active_festivals": active,
        "recent_dates": recent_dates,
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """统计面板数据"""
    # 最近30天
    thirty_days = (date.today() - timedelta(days=30)).isoformat()
    results = (
        db.query(DailyResult)
        .filter(DailyResult.date >= thirty_days)
        .order_by(DailyResult.date.asc())
        .all()
    )

    margin_trend = [{"date": r.date, "value": round(r.avg_margin * 100, 1)} for r in results if r.avg_margin]
    count_trend = [{"date": r.date, "value": r.selected_count} for r in results]

    # 总览
    total = db.query(DailyResult).count()
    avg_all = db.query(func.avg(DailyResult.avg_margin)).scalar() or 0

    return {
        "total_days": total,
        "overall_avg_margin": round(avg_all * 100, 1),
        "margin_trend": margin_trend[-14:],
        "count_trend": count_trend[-14:],
    }
