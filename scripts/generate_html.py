#!/usr/bin/env python3
"""生成自包含HTML选品日报 - 无CDN依赖，内联CSS/JS，双击即开"""
import json
import os
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "daily"
WORKSPACE_DIR = Path("/workspace")


def generate_html():
    today = date.today().isoformat()
    json_path = OUTPUT_DIR / "latest.json"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    stats = data.get("stats", {})
    festivals = data.get("active_festivals", [])

    # Stats
    total = len(products)
    avg_margin = sum(p.get("pricing", {}).get("estimated_margin", 0) for p in products) / total * 100 if total else 0
    avg_price = sum(p.get("pricing", {}).get("suggested_price_mxn", 0) for p in products) / total if total else 0
    avg_score = sum(p.get("score", 0) for p in products) / total if total else 0

    # Build cards
    cards = []
    for p in products:
        prod = p.get("product", {})
        cost = p.get("cost", {})
        pricing = p.get("pricing", {})
        comp = p.get("competition", {})
        logi = p.get("logistics", {})
        store = p.get("store", {})
        reason = p.get("reason", {})
        tags = p.get("tags", [])

        title = prod.get("title_zh", "N/A")
        category = prod.get("category", "")
        url = prod.get("source_url", "")
        img = prod.get("image_url", "")
        desc = prod.get("description", "")

        purchase = cost.get("purchase_price_rmb", 0)
        total_cost = cost.get("total_cost_rmb", 0)
        air = cost.get("air_freight_rmb", 0)

        price_mxn = pricing.get("suggested_price_mxn", 0)
        margin = pricing.get("estimated_margin", 0)
        markup = pricing.get("markup_ratio", 0)

        temu_price = comp.get("temu_mx_lowest_mxn")
        shopee_price = comp.get("shopee_mx_lowest_mxn")
        advantage = comp.get("price_advantage", "")

        weight = logi.get("actual_weight_kg", 0)
        vol_weight = logi.get("volumetric_weight_kg", 0)
        chargeable = logi.get("chargeable_weight_kg", 0)
        dims = logi.get("dimensions_cm", {})

        store_name = store.get("name", "")
        store_years = store.get("years_active", 0)
        store_rating = store.get("rating", 0)
        delivery = store.get("delivery_hours", 0)

        score = p.get("score", 0)
        rank = p.get("rank", 0)

        details = reason.get("details", [])
        festival = reason.get("festival_relevance", "")

        # Extract sales
        sales = ""
        for d in details:
            if "销量" in d:
                parts = d.split("销量: ")
                if len(parts) > 1:
                    sales = parts[1].replace("件", "")
                break

        # Tags
        tag_colors = {
            "green": ("#dcfce7", "#15803d", "#86efac"),
            "red": ("#fee2e2", "#b91c1c", "#fca5a5"),
            "purple": ("#f3e8ff", "#7e22ce", "#d8b4fe"),
            "orange": ("#ffedd5", "#c2410c", "#fdba74"),
            "blue": ("#dbeafe", "#1d4ed8", "#93c5fd"),
        }
        tags_html = ""
        for t in tags:
            bg, text, border = tag_colors.get(t.get("color", "blue"), tag_colors["blue"])
            tags_html += f'<span style="display:inline-block;padding:2px 8px;font-size:11px;font-weight:600;border-radius:12px;background:{bg};color:{text};border:1px solid {border};margin-right:4px;">{t["label"]}</span>'

        # Competitor info
        comp_html = ""
        if temu_price:
            comp_html += f'<span style="color:#c2410c;font-weight:600;">Temu: ${temu_price} MXN</span> &nbsp; '
        if shopee_price:
            comp_html += f'<span style="color:#dc2626;font-weight:600;">Shopee: ${shopee_price} MXN</span>'
        if not comp_html:
            comp_html = '<span style="color:#9ca3af;">无竞品数据</span>'

        margin_pct = margin * 100
        if margin_pct >= 20:
            margin_color = "#16a34a"
        elif margin_pct >= 15:
            margin_color = "#2563eb"
        else:
            margin_color = "#ea580c"

        # Image with fallback
        img_html = f'''<img src="{img}" loading="lazy" style="width:100%;height:140px;object-fit:cover;border-radius:8px;"
            onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
            <div style="width:100%;height:140px;background:linear-gradient(135deg,#dbeafe,#e9d5ff);border-radius:8px;display:none;align-items:center;justify-content:center;font-size:40px;">📦</div>'''

        # Festival badge
        festival_html = ""
        if festival:
            festival_html = f'<div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:6px;padding:6px 8px;margin-bottom:8px;font-size:11px;color:#7e22ce;">🎪 节日: {festival}</div>'

        cards.append(f'''
        <div class="card">
          <div style="position:relative;">
            {img_html}
            <div style="position:absolute;top:8px;left:8px;background:#2563eb;color:white;font-size:13px;font-weight:700;padding:3px 10px;border-radius:12px;">#{rank}</div>
            <div style="position:absolute;top:8px;right:8px;background:rgba(255,255,255,0.95);color:#1e40af;font-size:13px;font-weight:700;padding:3px 10px;border-radius:12px;">{score}分</div>
          </div>
          <div style="padding:12px;">
            <div style="margin-bottom:8px;">{tags_html}</div>
            <h3 style="font-size:13px;font-weight:600;color:#1f2937;margin:0 0 6px 0;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;" title="{title}">{title}</h3>
            <p style="font-size:11px;color:#6b7280;margin:0 0 10px 0;line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{desc}</p>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;font-size:11px;">
              <div style="background:#f9fafb;border-radius:6px;padding:6px 8px;">
                <div style="color:#9ca3af;">进货价</div>
                <div style="font-weight:700;color:#1f2937;">¥{purchase:.1f}</div>
              </div>
              <div style="background:#f9fafb;border-radius:6px;padding:6px 8px;">
                <div style="color:#9ca3af;">建议售价</div>
                <div style="font-weight:700;color:#2563eb;">${price_mxn:.0f} MXN</div>
              </div>
              <div style="background:#f9fafb;border-radius:6px;padding:6px 8px;">
                <div style="color:#9ca3af;">总成本</div>
                <div style="font-weight:700;color:#1f2937;">¥{total_cost:.1f}</div>
              </div>
              <div style="background:#f9fafb;border-radius:6px;padding:6px 8px;">
                <div style="color:#9ca3af;">毛利率</div>
                <div style="font-weight:700;color:{margin_color};">{margin_pct:.1f}%</div>
              </div>
            </div>

            <div style="font-size:11px;color:#9ca3af;margin-bottom:8px;line-height:1.6;">
              <div>📦 重量: {weight}kg | 体积重: {vol_weight:.2f}kg | {dims.get("l","")}×{dims.get("w","")}×{dims.get("h","")}cm</div>
              <div>✈️ 空运费: ¥{air:.1f} | 计费重: {chargeable}kg</div>
              <div>🏪 {store_name}</div>
              <div>⭐ {store_rating}分 | 📅 {store_years}年 | 🚚 {delivery}h发货 | 🔥 销量: {sales}</div>
            </div>

            <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:6px 8px;margin-bottom:8px;font-size:11px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="color:#6b7280;">竞品比价</span>
                <span>{comp_html}</span>
              </div>
              {f'<div style="color:#16a34a;font-weight:600;margin-top:4px;">✓ {advantage}</div>' if advantage else ''}
            </div>

            {festival_html}

            <a href="{url}" target="_blank" style="display:block;text-align:center;background:#2563eb;color:white;font-size:13px;font-weight:500;padding:8px;border-radius:8px;text-decoration:none;transition:background 0.2s;"
               onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">
              🔗 查看1688货源
            </a>
          </div>
        </div>''')

    # Festival bar
    festival_bar = ""
    if festivals:
        items = ""
        for f in festivals[:3]:
            name = f.get("name_zh", f.get("name", ""))
            days = f.get("days_until", 0)
            items += f'<div style="background:linear-gradient(to right,#8b5cf6,#ec4899);color:white;border-radius:8px;padding:6px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;"><span style="font-weight:500;">🎪 {name}</span><span style="font-size:13px;">还有 <b style="font-size:18px;">{days}</b> 天</span></div>'
        festival_bar = f'<div style="background:white;border-bottom:1px solid #e5e7eb;box-shadow:0 1px 3px rgba(0,0,0,0.05);"><div style="max-width:80rem;margin:0 auto;padding:10px 16px;display:flex;gap:12px;flex-wrap:wrap;">{items}</div></div>'

    # Category filter buttons
    cat_counts = {}
    for p in products:
        cat = p.get("product", {}).get("category", "其他")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    filter_buttons = f'<button class="filter-btn active" onclick="filterProducts(\'all\')" data-cat="all">全部 ({total})</button>'
    for cat, count in cat_counts.items():
        filter_buttons += f'<button class="filter-btn" onclick="filterProducts(\'{cat}\')" data-cat="{cat}">{cat} ({count})</button>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🇲🇽 墨西哥跨境选品日报 | {today}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; background:#f9fafb; min-height:100vh; color:#333; }}

  .header {{ background:linear-gradient(to right,#1d4ed8,#2563eb,#06b6d4); color:white; }}
  .header-inner {{ max-width:80rem; margin:0 auto; padding:24px 16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; }}
  .header h1 {{ font-size:24px; font-weight:700; display:flex; align-items:center; gap:8px; }}
  .header .subtitle {{ font-size:14px; color:#dbeafe; margin-top:4px; }}
  .stat-box {{ background:rgba(255,255,255,0.15); border-radius:8px; padding:8px 16px; text-align:center; }}
  .stat-box .num {{ font-size:24px; font-weight:700; }}
  .stat-box .label {{ font-size:12px; color:#dbeafe; }}

  .toolbar {{ max-width:80rem; margin:0 auto; padding:16px; }}
  .toolbar-inner {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; }}
  .filter-bar {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .filter-btn {{ padding:6px 14px; font-size:13px; font-weight:500; background:white; color:#6b7280; border:1px solid #e5e7eb; border-radius:8px; cursor:pointer; transition:all 0.2s; }}
  .filter-btn:hover {{ background:#eff6ff; }}
  .filter-btn.active {{ background:#2563eb; color:white; border-color:#2563eb; }}

  .grid {{ max-width:80rem; margin:0 auto; padding:0 16px 32px; display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }}
  @media (max-width:1024px) {{ .grid {{ grid-template-columns:repeat(3,1fr); }} }}
  @media (max-width:768px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
  @media (max-width:480px) {{ .grid {{ grid-template-columns:1fr; }} }}

  .card {{ background:white; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,0.1); border:1px solid #f3f4f6; overflow:hidden; transition:box-shadow 0.3s; }}
  .card:hover {{ box-shadow:0 10px 25px rgba(0,0,0,0.1); }}

  .footer {{ background:#1f2937; color:#9ca3af; text-align:center; padding:16px; font-size:12px; }}
  .footer p {{ margin:4px 0; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div>
      <h1>🇲🇽 墨西哥跨境选品日报</h1>
      <div class="subtitle">{today} · 自动化选品智能体 · 1688货源</div>
    </div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
      <div class="stat-box"><div class="num">{total}</div><div class="label">精选SKU</div></div>
      <div class="stat-box"><div class="num">{avg_margin:.1f}%</div><div class="label">平均毛利率</div></div>
      <div class="stat-box"><div class="num">${avg_price:.0f}</div><div class="label">均售价MXN</div></div>
      <div class="stat-box"><div class="num">{avg_score:.1f}</div><div class="label">平均评分</div></div>
    </div>
  </div>
</div>

{festival_bar}

<div class="toolbar">
  <div class="toolbar-inner">
    <div class="filter-bar">{filter_buttons}</div>
  </div>
</div>

<div class="grid" id="grid">
{''.join(cards)}
</div>

<div class="footer">
  <p>🤖 墨西哥跨境电商自动化选品智能体 · 每日10:00 CST自动更新</p>
  <p>硬约束: 进货价≈¥20 | 售价≥6倍 | 重量1-2kg | 店铺>1年 | 发货≤48h | 非食品接触类</p>
</div>

<script>
  const products = {json.dumps(products, ensure_ascii=False)};
  function filterProducts(cat) {{
    const cards = document.querySelectorAll('#grid > .card');
    const btns = document.querySelectorAll('.filter-btn');
    btns.forEach(b => {{
      if (b.getAttribute('data-cat') === cat) {{ b.classList.add('active'); }}
      else {{ b.classList.remove('active'); }}
    }});
    cards.forEach((card, i) => {{
      const p = products[i];
      const pcat = (p.product && p.product.category) || '其他';
      card.style.display = (cat === 'all' || pcat === cat) ? '' : 'none';
    }});
  }}
</script>

</body>
</html>'''

    # Write to /workspace
    output_path = WORKSPACE_DIR / f"墨西哥选品日报_{today}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"HTML generated: {output_path}")
    print(f"File size: {size_kb:.1f} KB")
    print(f"Products: {total}")
    return output_path


if __name__ == "__main__":
    generate_html()
