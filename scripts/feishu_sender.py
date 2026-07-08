#!/usr/bin/env python3
"""飞书消息卡片发送器 - 通过Webhook推送全部选品日报到飞书群"""
import json
import os
import sys
import requests
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def send_feishu_report(products: list, stats: dict, today_str: str, report_url: str = ""):
    """发送飞书Interactive Card消息卡片，推送全部SKU摘要列表。

    Args:
        products: 商品列表（从latest.json读取）
        stats: 统计信息
        today_str: 日期字符串
        report_url: GitHub仓库内Markdown完整报告URL
    """
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "")
    if not webhook_url:
        print("⚠️  未设置 FEISHU_WEBHOOK_URL 环境变量，跳过飞书推送")
        return False

    total = len(products)
    avg_margin = sum(p.get("pricing", {}).get("estimated_margin", 0) for p in products) / total * 100 if total else 0
    avg_price = sum(p.get("pricing", {}).get("suggested_price_mxn", 0) for p in products) / total if total else 0

    # 飞书卡片元素列表
    elements = []

    # ── 摘要栏 ──
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 今日精选 {total} 个SKU** | **平均毛利率 {avg_margin:.1f}%** | **均售价 ${avg_price:.0f} MXN**"
        }
    })
    elements.append({"tag": "hr"})

    # ── 全部商品摘要列表 ──
    import re
    for p in products:
        prod = p.get("product", {})
        pricing = p.get("pricing", {})
        cost = p.get("cost", {})
        store = p.get("store", {})
        reason = p.get("reason", {})
        rank = p.get("rank", 0)
        score = p.get("score", 0)

        title = prod.get("title_zh", "")
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
                m = re.search(r'销量: ([\d,]+)', d)
                if m:
                    sales = m.group(1)
                break

        festival_badge = f" 🎪`{festival}`" if festival else ""
        sales_text = f" | 🔥{sales}件" if sales else ""

        content = (
            f"**#{rank} {title}**{festival_badge}\n"
            f"💰 ¥{purchase:.1f} → ${price_mxn:.0f} MXN | 毛利{margin:.0f}% | ⭐{store_rating} | 🚚{delivery}h{sales_text}\n"
            f"[🔗 1688货源]({url})"
        )

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })
        elements.append({"tag": "hr"})

    # ── 底部：查看完整报告按钮 ──
    if report_url:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📋 查看完整报告（含物流/竞品/描述详情）"},
                "url": report_url,
                "type": "primary"
            }]
        })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "📋 完整报告详见仓库 output/daily/latest_report.md"}
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
            data=json.dumps(card, ensure_ascii=False),
            timeout=10
        )
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print(f"✅ 飞书推送成功！共推送全部 {total} 个SKU")
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
