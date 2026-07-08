#!/usr/bin/env python3
"""每日选品日报一键脚本 - GitHub Actions定时触发

流程：选品算法 → 生成Markdown完整报告 → 推送飞书消息卡片
"""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORT_MD_PATH = PROJECT_ROOT / "output" / "daily" / "latest_report.md"
REPORT_HTML_PATH = PROJECT_ROOT / "output" / "daily" / "latest_report.html"
GITHUB_REPO = "JINcj1124/mexico-sourcing"


def generate_markdown_report(data: dict) -> str:
    """生成可直接在GitHub上查看的Markdown完整日报。"""
    today = data.get("date", date.today().isoformat())
    products = data.get("products", [])
    summary = data.get("summary", {})

    lines = [
        f"# 🇲🇽 墨西哥跨境选品日报 | {today}",
        "",
        "> 本报告由自动化选品系统每日生成，包含完整SKU清单、定价、竞品、物流与1688货源链接。",
        "",
        "## 📊 核心指标",
        "",
        f"| 指标 | 数值 |",
        f"| :--- | :--- |",
        f"| 精选SKU数 | {summary.get('selected_count', len(products))} |",
        f"| 平均毛利率 | {summary.get('avg_margin', 0):.1%} |",
        f"| 平均售价 | ${summary.get('avg_price_mxn', 0):.0f} MXN |",
        f"| 生成时间 | {data.get('generated_at', datetime.now().isoformat())} |",
        "",
        "---",
        "",
    ]

    for p in products:
        prod = p["product"]
        cost = p["cost"]
        pricing = p["pricing"]
        store = p["store"]
        reason = p["reason"]
        logistics = p["logistics"]
        competition = p["competition"]

        title = prod.get("title_zh", "")
        url = prod.get("source_url", "")
        festival = reason.get("festival_relevance", "")
        festival_badge = f" 🎪 `{festival}`" if festival else ""

        lines.extend([
            f"### #{p['rank']} {title}{festival_badge}",
            "",
            f"**采购价**: ¥{cost['purchase_price_rmb']:.1f} → **建议售价**: ¥{pricing['suggested_price_rmb']:.0f} / ${pricing['suggested_price_mxn']:.0f} MXN | **毛利**: {pricing['estimated_margin']:.1%} | **溢价**: ×{pricing['markup_ratio']:.1f}",
            "",
            f"**店铺**: {store['name']} · {store['years_active']:.1f}年 · 评分{store['rating']} · {store['delivery_hours']}h发货",
            "",
            f"**物流**: 实重{logistics['actual_weight_kg']:.2f}kg / 体积重{logistics['volumetric_weight_kg']:.2f}kg / 计费{logistics['chargeable_weight_kg']:.2f}kg | 尺寸 {logistics['dimensions_cm']['l']}×{logistics['dimensions_cm']['w']}×{logistics['dimensions_cm']['h']}cm",
            "",
            f"**竞品**: Temu ${competition['temu_mx_lowest_mxn']} MXN · Shopee ${competition['shopee_mx_lowest_mxn']} MXN · {competition['price_advantage']}",
            "",
            f"**1688货源**: [{url}]({url})",
            "",
            f"**选品理由**: {reason['primary']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "*数据说明：售价为系统根据竞品与成本测算的建议价，实际定价请结合平台活动与汇率调整。*",
        "",
    ])

    return "\n".join(lines)


def write_report_files(data: dict):
    """把Markdown报告写入本地。"""
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    md = generate_markdown_report(data)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    return md


def main():
    today_str = date.today().isoformat()
    print(f"=== 墨西哥选品日报生成 {today_str} ===")

    # Step 1: 运行选品算法
    print("\n[1/3] 运行选品算法...")
    from scripts.run_seeding import run as run_seeding
    run_seeding()

    # Step 2: 生成完整Markdown报告
    print("\n[2/3] 生成Markdown完整报告...")
    json_path = PROJECT_ROOT / "output" / "daily" / "latest.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    write_report_files(data)
    print(f"   报告已保存: {REPORT_MD_PATH}")

    # Step 3: 推送飞书消息卡片
    print("\n[3/3] 推送飞书消息卡片...")
    from scripts.feishu_sender import send_feishu_report

    products = data.get("products", [])
    # 完整报告链接：GitHub仓库内的 latest_report.md
    report_url = f"https://github.com/{GITHUB_REPO}/blob/main/output/daily/latest_report.md"
    send_feishu_report(products, data.get("summary", {}), today_str, report_url)

    print(f"\n=== 日报生成完成 ===")
    print(f"   日期: {today_str}")
    print(f"   SKU数: {len(products)}")
    print(f"   Markdown报告: {REPORT_MD_PATH}")
    print(f"   飞书推送: 完成")


if __name__ == "__main__":
    main()
