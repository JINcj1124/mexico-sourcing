#!/usr/bin/env python3
"""飞书消息卡片发送器 - 通过Webhook推送选品日报到飞书群"""
import json
import os
import sys
import requests
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def send_feishu_report(products: list, stats: dict, today_str: str, report_url: str = ""):
    """发送飞书Interactive Card消息卡片

    Args:
        products: 商品列表（从latest.json读取）
        stats: 统计信息
        today_str: 日期字符串
        report_url: GitHub仓库内Markdown完整报告URL
    """
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "")
    if not webhook_url:
        print("⚠️  未设置 FEISHU_WEBHOOK_URL 环境变量，跳过飞书推送")
        print("   设置方法: export FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'")
        return False

    total = len(products)
    avg_margin = sum(p.get("pricing", {}).get("estimated_margin", 0) for p in products) / total * 100 if total else 0
    avg_price = sum(p.get("pricing", {}).get("suggested_price_mxn", 0) for p in products) / total if total else 0

    # 构建Top 5商品卡片元素
    elements = []

    # 摘要栏
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 今日精选 {total} 个SKU** | **平均毛利率 {avg_margin:.1f}%** | **均售价 ${avg_price:.0f} MXN**"
        }
    })

    elements.append({"tag": "hr"})

    # Top 5商品
    for p in products[:5]:
        prod = p.get("product", {})
        pricing = p.get("pricing", {})
        cost = p.get("cost", {})
        store = p.get("store", {})
        reason = p.get("reason", {})
        rank = p.get("rank", 0)
        score = p.get("score", 0)

        title = prod.get("title_zh", "")[:30]
        purchase = cost.get("purchase_price_rmb", 0)
        price_mxn = pricing.get("suggested_price_mxn", 0)
        margin = pricing.get("estimated_margin", 0) * 100
        url = prod.get("source_url", "")
        store_name = store.get("name", "")
        store_rating = store.get("rating", 0)
        delivery = store.get("delivery_hours", 0)
        festival = reason.get("festival_relevance", "")

        # 提取销量
        sales = ""
        for d in reason.get("details", []):
            if "销量" in d:
                import re
                m = re.search(r'销量: ([\d,]+)', d)
                if m:
                    sales = m.group(1)
                break

        festival_str = f" 🎪 {festival}" if festival else ""

        content = (
            f"**#{rank} {title}** (评分{score}){festival_str}\n"
            f"💰 进货价 ¥{purchase:.1f} → 售价 ${price_mxn:.0f} MXN | 毛利{margin:.0f}%\n"
            f"🔥 销量 {sales} | ⭐ {store_rating}分 | 🚚 {delivery}h发货\n"
            f"🔗 [点击查看1688货源]({url})"
        )

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })
        elements.append({"tag": "hr"})

    # 查看完整日报按钮
    if report_url:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": f"📋 查看完整日报（全部{total}个SKU）"},
                "url": report_url,
                "type": "primary"
            }]
        })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"📋 完整日报共 {total} 个SKU，详见仓库 output/daily/latest_report.md"}
        })

    # 构建消息卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🇲🇽 墨西哥跨境选品日报 | {today_str}"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }

    # 发送
    try:
        resp = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(card),
            timeout=10
        )
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print(f"✅ 飞书推送成功！共推送 {min(5, total)} 个Top商品卡片")
            return True
        else:
            print(f"❌ 飞书推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 飞书推送异常: {e}")
        return False


def main():
    today_str = date.today().isoformat()
    json_path = PROJECT_ROOT / "output" / "daily" / "latest.json"

    if not json_path.exists():
        print(f"❌ 找不到日报JSON: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    stats = {"total": len(products)}

    # 默认完整报告链接
    default_report_url = f"https://github.com/JINcj1124/mexico-sourcing/blob/main/output/daily/latest_report.md"
    report_url = os.environ.get("REPORT_URL", default_report_url)

    send_feishu_report(products, stats, today_str, report_url)


if __name__ == "__main__":
    main()
