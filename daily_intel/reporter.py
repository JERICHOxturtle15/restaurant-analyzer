# -*- coding: utf-8 -*-
"""
每日简报生成器 — TO C 洞察版
按洞察类型分类：打法、产品、互动体验、商业模式
支持 DeepSeek AI 提炼
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "intel.db"
REPORTS_DIR = BASE_DIR / "reports"

# 采集分类 → 洞察标签映射
CATEGORY_META = {
    "小红书种草":   {"icon": "📱", "tag": "种草信号",  "color": "#e74c3c"},
    "抖音爆款":     {"icon": "🎬", "tag": "抖音爆款",  "color": "#e67e22"},
    "大众点评热门": {"icon": "⭐", "tag": "消费者热评", "color": "#f39c12"},
    "体验与互动":   {"icon": "✨", "tag": "体验互动",  "color": "#27ae60"},
    "打法与模式":   {"icon": "🚀", "tag": "打法模式",  "color": "#2980b9"},
    "特色产品":     {"icon": "🍽️", "tag": "特色产品",  "color": "#8e44ad"},
    "自定义方向":   {"icon": "📌", "tag": "自定义",    "color": "#16a085"},
}


def get_today_items(target_date: str = None) -> list:
    target = target_date or date.today().isoformat()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM intel_items WHERE date=? ORDER BY category, source",
        (target,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ai_summarize(items: list) -> str:
    """用 DeepSeek 提炼今日要点，面向餐饮品牌策划视角"""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        content = "\n".join(
            f"[{it['category']}] {it['title']}"
            for it in items[:50]
        )
        resp = client.chat.completions.create(
            model=model,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": (
                    "你是一位资深餐饮品牌策划顾问。以下是今日从抖音、小红书、大众点评等平台采集的消费行为信号，"
                    "请从品牌策划视角提炼出最有价值的洞察：\n\n"
                    "**输出格式（严格按此结构）：**\n\n"
                    "🔥 今日最强信号（1条，最值得立即关注的消费趋势）\n"
                    "> 用一句话说清楚：什么人、在哪个平台、为什么被这个东西吸引\n\n"
                    "💡 可落地打法（2-3条，每条一句话，格式：【打法名】具体怎么做）\n\n"
                    "🍽️ 值得关注的产品方向（1-2条，有特色的品类或单品）\n\n"
                    "✨ 品牌/体验创新（1条，某个品牌做了什么值得借鉴的体验设计）\n\n"
                    "⚡ 今日行动建议（1条，给正在做餐饮项目的策划人）\n\n"
                    f"情报内容：\n{content}\n\n"
                    "每条控制在40字以内，要具体、可落地，避免空话。"
                )
            }]
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI提炼失败: {e}"


def group_by_category(items: list) -> dict:
    groups = {}
    for it in items:
        cat = it["category"]
        groups.setdefault(cat, []).append(it)
    return groups


def render_html(items: list, ai_summary: str, target_date: str) -> str:
    groups = group_by_category(items)

    # AI 洞察块
    if ai_summary:
        formatted = ai_summary.replace("\n", "<br>")
        ai_block = f"""
        <div class="ai-block">
            <div class="ai-header">⚡ DeepSeek AI · 今日品牌策划洞察</div>
            <div class="ai-content">{formatted}</div>
        </div>"""
    else:
        ai_block = """
        <div class="ai-block no-key">
            <div class="ai-header">⚡ AI 洞察</div>
            <p style="margin:0;color:#999">配置 DEEPSEEK_API_KEY 后自动启用 AI 提炼，从消费行为信号中提取可落地打法。</p>
        </div>"""

    # 按分类渲染卡片
    category_blocks = ""
    for cat, its in groups.items():
        meta = CATEGORY_META.get(cat, {"icon": "📌", "tag": cat, "color": "#666"})
        rows = ""
        for it in its:
            link = f'<a href="{it["url"]}" target="_blank">{it["title"]}</a>' if it["url"] else it["title"]
            rows += f'<li class="item">{link}</li>'
        category_blocks += f"""
        <div class="cat-block">
            <div class="cat-header" style="border-left-color:{meta['color']}">
                {meta['icon']} {meta['tag']}
                <span class="count">{len(its)} 条</span>
            </div>
            <ul>{rows}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>餐饮消费行为情报 · {target_date}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    max-width: 860px; margin: 36px auto; padding: 0 16px;
    color: #1a1a1a; background: #f4f4f2; font-size: 14px;
  }}
  h1 {{ font-size: 22px; color: #111; margin-bottom: 4px; }}
  .meta {{ color: #999; font-size: 12px; margin-bottom: 24px; }}
  .badge {{
    display: inline-block; background: #111; color: #fff;
    font-size: 11px; padding: 2px 8px; border-radius: 20px; margin-left: 8px;
  }}
  .ai-block {{
    background: #fffbf0; border: 1px solid #f0d060;
    border-radius: 10px; padding: 20px; margin-bottom: 24px;
  }}
  .ai-block.no-key {{
    background: #f7f7f7; border-color: #ddd;
  }}
  .ai-header {{
    font-weight: 700; font-size: 15px; margin-bottom: 14px; color: #333;
  }}
  .ai-content {{
    line-height: 2; color: #222; white-space: pre-wrap;
  }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }}
  .cat-block {{
    background: white; border-radius: 10px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }}
  .cat-header {{
    font-weight: 700; font-size: 13px; color: #333;
    border-left: 4px solid #ccc; padding-left: 10px;
    margin-bottom: 12px; display: flex; align-items: center;
    justify-content: space-between;
  }}
  .count {{ font-weight: 400; color: #aaa; font-size: 12px; }}
  ul {{ margin: 0; padding: 0; list-style: none; }}
  .item {{
    padding: 6px 0; border-bottom: 1px solid #f0f0f0;
    line-height: 1.5;
  }}
  .item:last-child {{ border-bottom: none; }}
  a {{ color: #1a73e8; text-decoration: none; font-size: 13px; }}
  a:hover {{ text-decoration: underline; }}
  .footer {{ text-align: center; color: #ccc; font-size: 11px; margin-top: 30px; }}
</style>
</head>
<body>
<h1>🍽️ 餐饮消费行为情报
  <span class="badge">TO C · {target_date}</span>
</h1>
<p class="meta">
  精选 {len(items)} 条 &nbsp;·&nbsp;
  来自抖音 / 小红书 / 大众点评相关内容 &nbsp;·&nbsp;
  面向品牌策划视角
</p>

{ai_block}

<div class="grid">
{category_blocks}
</div>

<p class="footer">Restaurant Analyzer · Daily Intel · 自动生成</p>
</body>
</html>"""


def render_empty_html(target_date: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>餐饮消费行为情报 · {target_date}</title>
<style>
  body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 860px; margin: 100px auto;
         text-align: center; color: #999; background: #f4f4f2; }}
  h1 {{ font-size: 20px; color: #ccc; }}
  p {{ font-size: 14px; line-height: 2; }}
</style>
</head>
<body>
<h1>📭 {target_date} 今日暂无新内容</h1>
<p>
  过去48小时内，目标关键词没有检索到符合条件的新资讯。<br>
  可能原因：今日相关内容较少 / 网络问题 / 关键词覆盖不足。<br><br>
  你可以在 <code>topics.json</code> 的 <code>custom_directions</code> 中补充新的监控方向。
</p>
</body>
</html>"""


def generate_report(target_date: str = None) -> Path:
    target = target_date or date.today().isoformat()
    items = get_today_items(target)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"intel_{target}.html"

    if not items:
        print(f"  [报告] {target} 今日无新内容，生成空状态页面")
        out.write_text(render_empty_html(target), encoding="utf-8")
        return out

    print(f"  → {len(items)} 条新内容，AI提炼中...")
    ai_summary = ai_summarize(items)
    if ai_summary:
        print("  → AI提炼完成")

    html = render_html(items, ai_summary, target)
    out.write_text(html, encoding="utf-8")
    print(f"  ✓ 报告已生成: {out}")
    return out


if __name__ == "__main__":
    generate_report()
