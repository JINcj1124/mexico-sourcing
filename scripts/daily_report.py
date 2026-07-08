#!/usr/bin/env python3
"""每日选品日报一键脚本 - GitHub Actions定时触发

流程：选品算法 → 推送飞书消息卡片
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    today_str = date.today().isoformat()
    print(f"=== 墨西哥选品日报生成 {today_str} ===")

    # Step 1: 运行选品算法
    print("\n[1/2] 运行选品算法...")
    from scripts.run_seeding import run as run_seeding
    run_seeding()

    # Step 2: 推送飞书消息卡片
    print("\n[2/2] 推送飞书消息卡片...")
    from scripts.feishu_sender import send_feishu_report

    json_path = PROJECT_ROOT / "output" / "daily" / "latest.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    send_feishu_report(products, {}, today_str, "")

    print(f"\n=== 日报生成完成 ===")
    print(f"   日期: {today_str}")
    print(f"   SKU数: {len(products)}")
    print(f"   飞书推送: 完成")


if __name__ == "__main__":
    main()
