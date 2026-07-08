"""管理接口：手动触发、参数配置"""
import asyncio
import logging
from datetime import date, datetime
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.database import get_db
from backend.api.schemas import TriggerPipelineRequest, PipelineStatus, LogisticsParamsUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# 全局状态（简单内存状态，生产环境应改用Redis）
_pipeline_status = {"status": "idle", "message": "", "products_count": 0}


def _run_pipeline_sync(target_date_str: str = None):
    """在后台线程中运行选品流程"""
    global _pipeline_status
    try:
        _pipeline_status = {"status": "running", "message": "Pipeline started", "products_count": 0}

        from backend.services.sourcing_pipeline import SourcingPipeline
        pipeline = SourcingPipeline()

        target = None
        if target_date_str:
            target = datetime.strptime(target_date_str, "%Y-%m-%d").date()

        # 在同步上下文中运行异步
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        products = loop.run_until_complete(pipeline.run(target))
        loop.close()

        _pipeline_status = {
            "status": "completed",
            "message": f"Successfully selected {len(products)} products",
            "products_count": len(products),
        }
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        _pipeline_status = {"status": "failed", "message": str(e), "products_count": 0}


@router.post("/trigger", response_model=PipelineStatus)
def trigger_pipeline(
    req: TriggerPipelineRequest = None,
    background_tasks: BackgroundTasks = None,
):
    """手动触发选品流程"""
    global _pipeline_status
    if _pipeline_status["status"] == "running":
        return PipelineStatus(status="busy", message="Pipeline is already running")

    target_date_str = req.target_date if req else None
    background_tasks.add_task(_run_pipeline_sync, target_date_str)
    return PipelineStatus(status="triggered", message="Pipeline started in background")


@router.get("/status", response_model=PipelineStatus)
def get_pipeline_status():
    """查询选品流程运行状态"""
    return PipelineStatus(**_pipeline_status)


@router.put("/logistics-params")
def update_logistics_params(params: LogisticsParamsUpdate):
    """更新物流参数（运行时覆盖）"""
    updates = {}
    if params.air_freight_per_kg is not None:
        settings.air_freight_per_kg = params.air_freight_per_kg
        updates["air_freight_per_kg"] = params.air_freight_per_kg
    if params.volumetric_divisor is not None:
        settings.volumetric_divisor = params.volumetric_divisor
        updates["volumetric_divisor"] = params.volumetric_divisor
    if params.packaging_fee is not None:
        settings.packaging_fee = params.packaging_fee
        updates["packaging_fee"] = params.packaging_fee
    if params.last_mile_base_fee is not None:
        settings.last_mile_base_fee = params.last_mile_base_fee
        updates["last_mile_base_fee"] = params.last_mile_base_fee
    if params.damage_rate is not None:
        settings.damage_rate = params.damage_rate
        updates["damage_rate"] = params.damage_rate
    if params.commission_rate is not None:
        settings.commission_rate = params.commission_rate
        updates["commission_rate"] = params.commission_rate
    if params.mxn_to_rmb is not None:
        settings.mxn_to_rmb = params.mxn_to_rmb
        updates["mxn_to_rmb"] = params.mxn_to_rmb

    return {"success": True, "updated": updates, "message": "Params updated (runtime only)"}


@router.get("/festivals")
def get_festival_calendar():
    """获取完整节日日历"""
    from backend.algorithms.festival_weighter import FestivalWeighter
    weighter = FestivalWeighter()
    active = weighter.get_active_festivals()
    all_festivals = weighter.festivals
    return {"all": all_festivals, "active": active}
