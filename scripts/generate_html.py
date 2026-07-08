#!/usr/bin/env python3
"""生成自包含HTML选品日报 - GitHub Pages 部署用 index.html"""
import json
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "daily"


def generate_html():
    today = date.today().isoformat()
    json_path = OUTPUT_DIR / "latest.json"

    if not json_path.exists():
        print(f"❌ 找不到 {json_path}，请先运行选品算法")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    festivals = data.get("active_festivals", [])

    total = len(products)
    avg_margin = sum(p.get("pricing", {}).get("estimated_margin", 0) for p in products) / total * 100 if total else 0
    avg_price = sum(p.get("pricing", {}).get("suggested_price_mxn", 0) for p in products) / total if total else 0
    avg_score = sum(p.get("score", 0) for p in products) / total if total else 0

    # 各品类统计
    cat_counts = {}
    for p in products:
        cat = p.get("product", {}).get("category", "其他")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # 产品卡片
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
        img = prod.get("image_url", f"https://placehold.co/400x300/e2e8f0/64748b?text={category}")
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

        # 提取销量
        sales = ""
        for d in details:
            if "销量" in d:
                import re
                m = re.search(r'销量: ([\d,]+)', d)
                if m:
                    sales = m.group(1)
                break

        # 毛利率颜色
        margin_pct = margin * 100
        if margin_pct >= 20:
            margin_color = "#16a34a"
        elif margin_pct >= 10:
            margin_color = "#2563eb"
        else:
            margin_color = "#ea580c"

        tag_colors = {
            "green": ("#dcfce7", "#15803d"),
            "red": ("#fee2e2", "#b91c1c"),
            "purple": ("#f3e8ff", "#7e22ce"),
            "orange": ("#ffedd5", "#c2410c"),
            "blue": ("#dbeafe", "#1d4ed8"),
        }
        tags_html = "".join(
            f'<span style="display:inline-block;padding:2px 8px;font-size:10px;font-weight:600;border-radius:12px;background:{tag_colors.get(t.get("color","blue"),tag_colors["blue"])[0]};color:{tag_colors.get(t.get("color","blue"),tag_colors["blue"])[1]};margin-right:4px;margin-bottom:4px;">{t["label"]}</span>'
            for t in tags
        )

        comp_html = ""
        if temu_price:
            comp_html += f'<span style="color:#c2410c;font-weight:600;">Temu ${temu_price}</span> '
        if shopee_price:
            comp_html += f'<span style="color:#dc2626;font-weight:600;">Shopee ${shopee_price}</span>'
        if not comp_html:
            comp_html = '<span style="color:#9ca3af;">无竞品数据</span>'

        festival_badge = f'<div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:6px;padding:4px 8px;margin-bottom:8px;font-size:11px;color:#7e22ce;">🎪 {festival}</div>' if festival else ""

        cards.append(f'''
        <div class="card" data-cat="{category}">
          <div class="card-img">
            <img src="{img}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22><rect fill=%22%23e2e8f0%22 width=%22400%22 height=%22300%22/><text fill=%22%2394a3b8%22 x=%22200%22 y=%22150%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2240%22>📦</text></svg>'">
            <span class="rank-badge">#{rank}</span>
            <span class="score-badge">{score:.0f}分</span>
          </div>
          <div class="card-body">
            <div style="margin-bottom:8px;">{tags_html}</div>
            <h3 title="{title}">{title}</h3>
            <p class="desc">{desc}</p>

            <div class="stats-grid">
              <div class="stat"><span class="stat-label">进货价</span><span class="stat-val">¥{purchase:.1f}</span></div>
              <div class="stat"><span class="stat-label">售价 MXN</span><span class="stat-val" style="color:#2563eb;">${price_mxn:.0f}</span></div>
              <div class="stat"><span class="stat-label">总成本</span><span class="stat-val">¥{total_cost:.1f}</span></div>
              <div class="stat"><span class="stat-label">毛利率</span><span class="stat-val" style="color:{margin_color};">{margin_pct:.1f}%</span></div>
            </div>

            <div class="detail-row">
              📦 {weight}kg | ✈️ ¥{air:.1f} | {dims.get("l","")}×{dims.get("w","")}×{dims.get("h","")}cm
            </div>
            <div class="detail-row">
              🏪 {store_name} · ⭐{store_rating} · 📅{store_years}年 · 🚚{delivery}h · 🔥{sales}件
            </div>

            <div class="comp-box">
              <span style="color:#6b7280;">竞品:</span> {comp_html}
              {'<div style="color:#16a34a;font-weight:600;margin-top:4px;">✓ '+advantage+'</div>' if advantage else ''}
            </div>

            {festival_badge}

            <a href="{url}" target="_blank" class="source-btn">🔗 1688货源详情页</a>
          </div>
        </div>''')

    # 节日倒计时
    festival_bar = ""
    if festivals:
        items = "".join(
            f'<div class="festival-chip"><span>🎪 {f.get("name_zh", f.get("name",""))}</span> <b>{f.get("days_until",0)}天</b></div>'
            for f in festivals[:3]
        )
        festival_bar = f'<div class="festival-bar"><div class="festival-inner">{items}</div></div>'

    # 品类过滤
    filter_buttons = '<button class="filter-btn active" data-cat="all">全部 ({})</button>'.format(total)
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        filter_buttons += f'<button class="filter-btn" data-cat="{cat}">{cat} ({cnt})</button>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🇲🇽 墨西哥跨境选品日报 | {today}</title>
<style>
  *,*::before,*::after {{margin:0;padding:0;box-sizing:border-box}}
  body {{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f1f5f9;color:#334155;min-height:100vh}}
  .header {{background:linear-gradient(135deg,#1e3a5f,#2563eb,#0891b2);color:white;padding:24px 16px}}
  .header-inner {{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px}}
  .header h1 {{font-size:22px;font-weight:700}}
  .header .sub {{font-size:13px;color:#93c5fd;margin-top:4px}}
  .stat-box {{background:rgba(255,255,255,0.12);border-radius:10px;padding:10px 18px;text-align:center}}
  .stat-box .num {{font-size:22px;font-weight:700}}
  .stat-box .label {{font-size:11px;color:#bfdbfe}}
  .festival-bar {{background:white;border-bottom:1px solid #e2e8f0;padding:10px 0}}
  .festival-inner {{max-width:1200px;margin:0 auto;padding:0 16px;display:flex;gap:12px;flex-wrap:wrap}}
  .festival-chip {{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:white;border-radius:8px;padding:6px 16px;font-size:13px;display:flex;align-items:center;gap:8px}}
  .toolbar {{max-width:1200px;margin:0 auto;padding:16px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}}
  .filter-bar {{display:flex;gap:6px;flex-wrap:wrap}}
  .filter-btn {{padding:6px 14px;font-size:12px;font-weight:500;background:white;color:#64748b;border:1px solid #e2e8f0;border-radius:8px;cursor:pointer;transition:all 0.2s}}
  .filter-btn:hover {{border-color:#2563eb;color:#2563eb}}
  .filter-btn.active {{background:#2563eb;color:white;border-color:#2563eb}}
  .grid {{max-width:1200px;margin:0 auto;padding:0 16px 32px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}}
  .card {{background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);border:1px solid #f1f5f9;transition:box-shadow 0.3s,transform 0.2s}}
  .card:hover {{box-shadow:0 8px 25px rgba(0,0,0,0.12);transform:translateY(-2px)}}
  .card-img {{position:relative;height:160px;overflow:hidden;background:#f8fafc}}
  .card-img img {{width:100%;height:100%;object-fit:cover}}
  .rank-badge {{position:absolute;top:8px;left:8px;background:#2563eb;color:white;font-size:12px;font-weight:700;padding:3px 10px;border-radius:12px}}
  .score-badge {{position:absolute;top:8px;right:8px;background:rgba(255,255,255,0.9);color:#1e40af;font-size:12px;font-weight:700;padding:3px 10px;border-radius:12px}}
  .card-body {{padding:12px}}
  .card-body h3 {{font-size:13px;font-weight:600;line-height:1.4;margin-bottom:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
  .card-body .desc {{font-size:11px;color:#94a3b8;line-height:1.5;margin-bottom:10px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
  .stats-grid {{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px}}
  .stat {{background:#f8fafc;border-radius:6px;padding:6px 8px;display:flex;flex-direction:column;gap:2px}}
  .stat-label {{font-size:10px;color:#94a3b8}}
  .stat-val {{font-size:13px;font-weight:700}}
  .detail-row {{font-size:11px;color:#94a3b8;margin-bottom:4px;line-height:1.5}}
  .comp-box {{background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:6px 8px;margin-bottom:8px;font-size:11px}}
  .source-btn {{display:block;text-align:center;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:white;font-size:12px;font-weight:600;padding:8px;border-radius:8px;text-decoration:none;transition:all 0.2s}}
  .source-btn:hover {{background:linear-gradient(135deg,#1d4ed8,#1e40af);transform:scale(1.02)}}
  .footer {{background:#1e293b;color:#94a3b8;text-align:center;padding:20px;font-size:12px;line-height:1.8}}
  @media (max-width:600px) {{.header h1{{font-size:18px}} .grid{{grid-template-columns:1fr}} }}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div>
      <h1>🇲🇽 墨西哥跨境选品日报</h1>
      <div class="sub">{today} · 自动化选品智能体 · 1688货源</div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <div class="stat-box"><div class="num">{total}</div><div class="label">精选SKU</div></div>
      <div class="stat-box"><div class="num">{avg_margin:.1f}%</div><div class="label">平均毛利率</div></div>
      <div class="stat-box"><div class="num">${avg_price:.0f}</div><div class="label">均价MXN</div></div>
      <div class="stat-box"><div class="num">{avg_score:.1f}</div><div class="label">平均评分</div></div>
    </div>
  </div>
</div>

{festival_bar}

<div class="toolbar">
  <div class="filter-bar">{filter_buttons}</div>
  <span style="font-size:12px;color:#94a3b8">🕐 每日 10:00 CST 自动更新</span>
</div>

<div class="grid" id="grid">
{"".join(cards)}
</div>

<div class="footer">
  <p>🤖 墨西哥跨境电商自动化选品智能体 · 每日 10:00 CST 自动更新</p>
  <p>选品约束: 进货价≈¥20 | 溢价≥6倍 | 重量1-2kg | 店铺>1年 | 发货≤48h | 非食品接触类</p>
  <p style="margin-top:4px">数据采集自 1688 · Temu MX · Shopee MX | 仅供参考</p>
</div>

<script>
(function(){{
  var btns=document.querySelectorAll('.filter-btn');
  btns.forEach(function(b){{
    b.onclick=function(){{
      var cat=this.dataset.cat;
      btns.forEach(function(x){{x.classList.remove('active')}});
      this.classList.add('active');
      document.querySelectorAll('#grid>.card').forEach(function(c){{
        c.style.display=(cat==='all'||c.dataset.cat===cat)?'':'none';
      }});
    }};
  }});
}})();
</script>

</body>
</html>'''

    # 写入 output/daily/index.html（GitHub Pages 入口）
    output_path = OUTPUT_DIR / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ HTML 日报已生成: {output_path}")
    print(f"   文件大小: {size_kb:.1f} KB | SKU: {total}")
    return str(output_path)


if __name__ == "__main__":
    generate_html()
