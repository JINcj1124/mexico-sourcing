"""APScheduler 定时任务定义"""
import asyncio
import logging
from datetime import date

from backend.config import settings

logger = logging.getLogger(__name__)


async def daily_sourcing_pipeline():
    """每日选品主流程 - 08:00触发"""
    logger.info("=== Daily sourcing job triggered ===")
    try:
        from backend.services.sourcing_pipeline import SourcingPipeline
        pipeline = SourcingPipeline()
        products = await pipeline.run(date.today())
        logger.info(f"Daily sourcing completed: {len(products)} products selected")
    except Exception as e:
        logger.error(f"Daily sourcing failed: {e}", exc_info=True)


def cleanup_old_data():
    """清理旧数据（每周一02:00执行）"""
    from backend.models.database import SessionLocal
    from backend.models.product import Product
    from datetime import timedelta

    db = SessionLocal()
    try:
        cutoff = date.today() - timedelta(days=90)
        # 清理90天前的非选中商品
        deleted = (
            db.query(Product)
            .filter(Product.created_at < cutoff, Product.is_selected == False)
            .delete()
        )
        db.commit()
        logger.info(f"Cleaned up {deleted} old products")
    except Exception as e:
        db.rollback()
        logger.error(f"Cleanup failed: {e}")
    finally:
        db.close()


def update_exchange_rate():
    """每月1日更新汇率"""
    logger.info("Exchange rate update placeholder - configure API key for live rates")
    # 可接入 exchangerate-api.com 等汇率服务
