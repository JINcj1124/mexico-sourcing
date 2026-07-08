"""商品相关 API 路由"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.product import Product
from backend.models.daily_result import DailyResult
from backend.api.schemas import ProductOut, DailyResultOut

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/today")
def get_today_products(db: Session = Depends(get_db)):
    """获取今日选品结果"""
    today_str = date.today().isoformat()
    daily = db.query(DailyResult).filter(DailyResult.date == today_str).first()
    if not daily:
        return {"date": today_str, "products": [], "summary": {}, "active_festivals": []}
    return {
        "date": daily.date,
        "generated_at": daily.generated_at.isoformat() if daily.generated_at else "",
        "products": daily.products_json or [],
        "active_festivals": daily.active_festivals or [],
        "summary": {
            "total_candidates": daily.total_candidates,
            "selected_count": daily.selected_count,
            "avg_margin": daily.avg_margin,
            "avg_price_mxn": daily.avg_price_mxn,
        },
    }


@router.get("/history")
def get_history(
    limit: int = Query(30, le=90),
    db: Session = Depends(get_db),
):
    """获取历史选品记录"""
    results = (
        db.query(DailyResult)
        .order_by(DailyResult.date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "date": r.date,
            "selected_count": r.selected_count,
            "avg_margin": r.avg_margin,
            "avg_price_mxn": r.avg_price_mxn,
            "active_festivals": r.active_festivals or [],
        }
        for r in results
    ]


@router.get("/date/{target_date}")
def get_products_by_date(target_date: str, db: Session = Depends(get_db)):
    """按日期查询选品结果"""
    daily = db.query(DailyResult).filter(DailyResult.date == target_date).first()
    if not daily:
        return {"date": target_date, "products": [], "summary": {}, "active_festivals": []}
    return {
        "date": daily.date,
        "generated_at": daily.generated_at.isoformat() if daily.generated_at else "",
        "products": daily.products_json or [],
        "active_festivals": daily.active_festivals or [],
        "summary": {
            "total_candidates": daily.total_candidates,
            "selected_count": daily.selected_count,
            "avg_margin": daily.avg_margin,
            "avg_price_mxn": daily.avg_price_mxn,
        },
    }
