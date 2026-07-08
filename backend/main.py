"""墨西哥选品智能体 - FastAPI 应用入口

启动FastAPI服务 + APScheduler定时任务。
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings
from backend.models.database import init_db

# --- 日志 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# --- 定时任务调度器 ---
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info("Starting Mexico Sourcing Agent...")
    init_db()
    logger.info("Database initialized")

    # 注册定时任务
    from backend.scheduler.jobs import daily_sourcing_pipeline, cleanup_old_data, update_exchange_rate

    scheduler.add_job(
        daily_sourcing_pipeline,
        trigger=CronTrigger(hour=10, minute=0, timezone="Asia/Shanghai"),
        id="daily_sourcing",
        name="每日选品全流程",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_data,
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0, timezone="Asia/Shanghai"),
        id="weekly_cleanup",
    )
    scheduler.add_job(
        update_exchange_rate,
        trigger=CronTrigger(day=1, hour=6, minute=0, timezone="Asia/Shanghai"),
        id="monthly_exchange_rate",
    )
    scheduler.start()
    logger.info("Scheduler started - daily sourcing at 08:00 CST")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Mexico Sourcing Agent stopped")


# --- FastAPI App ---
app = FastAPI(
    title="墨西哥跨境选品智能体",
    description="Mexico Cross-border E-commerce Automated Sourcing Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 路由注册 ---
from backend.api.routes_products import router as products_router
from backend.api.routes_dashboard import router as dashboard_router
from backend.api.routes_admin import router as admin_router

app.include_router(products_router)
app.include_router(dashboard_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "name": "墨西哥跨境选品智能体",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --- 直接运行入口 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
