"""Webhook 消息推送服务

支持企业微信机器人 Webhook 推送。
"""
import logging
from typing import Optional
from datetime import date

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """消息推送服务"""

    def __init__(self):
        self.wecom_url = settings.wecom_webhook_url

    async def push_daily_report(
        self, products: list, target_date: date, stats: dict, active_festivals: list
    ) -> bool:
        """推送每日选品报告到企业微信"""
        if not self.wecom_url:
            logger.info("Webhook URL not configured, skipping push")
            return False

        try:
            festival_str = ", ".join(f["name_zh"] for f in active_festivals[:3]) if active_festivals else "无"

            markdown = f"""## 🛒 每日选品报告 - {target_date.isoformat()}

> 从 **{stats.get('total_candidates', 0)}** 个候选商品中精选 **{stats.get('selected_count', 0)}** 个SKU
> 平均毛利率: **{stats.get('avg_margin', 0):.1%}**
> 活跃节日: {festival_str}

| # | 商品 | 成本¥ | 售价¥ | 毛利率 |
|---|------|-------|-------|--------|
"""

            for p in products[:15]:
                title = p.get("product", {}).get("title_zh", "")[:25]
                cost = p.get("cost", {}).get("total_cost_rmb", 0)
                price = p.get("pricing", {}).get("suggested_price_rmb", 0)
                margin = p.get("pricing", {}).get("estimated_margin", 0)
                markdown += f"| {p.get('rank', '')} | {title} | ¥{cost:.0f} | ¥{price:.0f} | {margin:.0%} |\n"

            markdown += "\n> 📊 [查看完整Dashboard](http://localhost:3000)"

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self.wecom_url,
                    json={"msgtype": "markdown", "markdown": {"content": markdown}},
                )
                if resp.status_code == 200:
                    logger.info("Wecom webhook sent successfully")
                    return True
                else:
                    logger.warning(f"Wecom webhook failed: {resp.status_code} {resp.text}")
                    return False

        except Exception as e:
            logger.error(f"Webhook push error: {e}")
            return False
