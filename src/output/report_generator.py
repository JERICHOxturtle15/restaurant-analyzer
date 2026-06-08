"""
Phase 4 — AI report generation via Claude API.

Functions
---------
generate_analysis_report(data)    -> str (Markdown)
generate_menu_suggestions(data)   -> list[dict]
generate_marketing_copy(theme, data) -> str

When USE_MOCK_API is True all functions return realistic placeholder content.
Replace mock: set ANTHROPIC_API_KEY in .env — USE_MOCK_API flips automatically.
"""

import json
import anthropic
from config.settings import ANTHROPIC_API_KEY, USE_MOCK_API

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _stream_text(prompt: str, max_tokens: int = 2048) -> str:
    client = _get_client()
    full = ""
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full += text
    return full


# ── Mock responses ────────────────────────────────────────────────────────────

_MOCK_REPORT = """# 餐厅菜单综合分析报告

## 执行摘要

本次分析覆盖 **20 道菜品**，结合波士顿矩阵、顾客情感评价与竞品定价数据，形成以下核心结论：

- **明星菜品（Star）** 9 道，以麻婆豆腐、番茄炒蛋、宫保鸡丁为代表，贡献约 65% 月利润
- **顾客整体满意度高**，正面评价占比约 70%，"口味好"与"性价比高"为最高频正面标签
- **定价竞争力**：主菜类定价较竞品均价高约 8%，海鲜类高约 15%，存在结构性下调空间

---

## 菜单结构建议

### 重点主推
1. **番茄炒蛋 / 麻婆豆腐**：高点单 + 高利润，建议设计双拼套餐，提升客单价
2. **白切鸡 / 宫保鸡丁**：评分 ≥ 4.7，建议在菜单封面及店内海报重点展示

### 待优化
1. **东坡肘子（Puzzle）**：利润率高但点单仅 40 份/月，建议节假日家庭套餐主推
2. **炒年糕（Dog）**：利润与人气双低，建议试调价至 32 元观察一个月，若无改善则下架

---

## 竞品应对策略

- 竹香园家常菜定价低 12%，建议将番茄炒蛋、清炒时蔬下调 3-5 元增强竞争力
- 御厨阁海鲜溢价明显（+35%），我店清蒸鲈鱼定价 158 元具备合理性，无需调整
- 老饕居白切鸡（95元）与我店（88元）接近，建议通过服务和摆盘形成差异化

---

## 数据支撑

| 维度 | 本店 | 竞品均值 |
|------|------|----------|
| 主菜均价 | 66 元 | 61 元 |
| 顾客评分 | 4.55 | 4.62 |
| 月均点单 | 248 份 | 215 份 |

> *以上数据基于样本数据生成，API Key 就位后将接入真实 Claude 分析。*
"""

_MOCK_SUGGESTIONS = [
    {
        "dish": "东坡肘子",
        "action": "调价",
        "current_price": 98,
        "suggested_price": 88,
        "reason": "竞品同档菜均价 85 元，现价偏高 15%，建议下调 10 元测试市场反应",
        "priority": "高",
    },
    {
        "dish": "清蒸鲈鱼",
        "action": "主推",
        "current_price": 158,
        "suggested_price": 158,
        "reason": "高利润明星菜，评分 4.8，建议设为招牌菜并配套套餐",
        "priority": "高",
    },
    {
        "dish": "炒年糕",
        "action": "下架评估",
        "current_price": 38,
        "suggested_price": 32,
        "reason": "低利润低点单，评价平淡，建议先试降价，一个月无明显改善则下架",
        "priority": "中",
    },
    {
        "dish": "番茄炒蛋",
        "action": "套餐化",
        "current_price": 32,
        "suggested_price": 32,
        "reason": "点单量最高（520/月），建议打包至午市套餐，带动其他菜品销量",
        "priority": "高",
    },
    {
        "dish": "蒜蓉粉丝蒸虾",
        "action": "优化成本",
        "current_price": 128,
        "suggested_price": 128,
        "reason": "利润率 57%，偏低。建议与供应商谈量采协议降低食材成本",
        "priority": "中",
    },
]

_MOCK_MARKETING = """## 小红书 / 抖音营销文案方向

### 文案方向 1 — 「家的味道」情感向
> 在城市里找到一口家常味 🍳
> 番茄炒蛋 32元 / 麻婆豆腐 38元
> 不是最贵的，是最暖心的那种
> #家常菜 #宝藏小馆 #打工人治愈食堂

### 文案方向 2 — 「性价比爆款」种草向
> 月销 500+ 的番茄炒蛋，真的绝！🔥
> 老板说这是「不能下架的镇店之宝」
> 下午两点来还要排队那种
> #性价比餐厅 #人均50吃撑 #好吃不贵

### 文案方向 3 — 「招牌菜」展示向
> 白切鸡选用当日新鲜食材 🐔
> 皮滑肉嫩 火候精准到秒
> 评分 4.9 不是吹出来的
> #白切鸡 #粤式料理 #招牌菜实拍

---
> *以上文案为 mock 占位内容，API Key 就位后将根据实际菜品数据和主题生成个性化文案。*
"""


# ── Public API ────────────────────────────────────────────────────────────────

def generate_analysis_report(data: dict) -> str:
    """
    Generate a Markdown analysis report from combined pipeline data.

    data keys expected: menu_summary, matrix_categories, sentiment_counts,
                        top_themes, competitor_pricing, positioning
    """
    if USE_MOCK_API:
        return _MOCK_REPORT

    summary_text = json.dumps(data.get("menu_summary", []), ensure_ascii=False, indent=2)
    themes_text = json.dumps(list(data.get("top_themes", {}).items())[:10], ensure_ascii=False)
    comp_text = json.dumps(data.get("positioning", {}), ensure_ascii=False, indent=2)

    prompt = f"""你是专业餐饮顾问，请根据以下数据生成一份结构化 Markdown 分析报告（约 600 字）。

菜单分类汇总：
{summary_text}

顾客评价高频主题（TOP10）：
{themes_text}

竞品定位数据：
{comp_text}

报告需包含：执行摘要、菜单结构建议、竞品应对策略、数据对比表格。"""
    return _stream_text(prompt, max_tokens=2048)


def generate_menu_suggestions(data: dict) -> list[dict]:
    """
    Generate menu optimization suggestions.

    Returns list of dicts: dish / action / current_price / suggested_price / reason / priority
    """
    if USE_MOCK_API:
        return _MOCK_SUGGESTIONS

    matrix_text = json.dumps(data.get("matrix_categories", {}), ensure_ascii=False, indent=2)
    pricing_text = json.dumps(data.get("competitor_pricing", [])[:10], ensure_ascii=False)

    prompt = f"""根据菜单波士顿矩阵分类和竞品定价，生成 5 条菜单优化建议。

矩阵分类：
{matrix_text}

竞品价格参考：
{pricing_text}

请严格以 JSON 数组返回，每项包含：dish, action（调价/主推/下架评估/套餐化/优化成本）, current_price, suggested_price, reason, priority（高/中/低）。
只返回 JSON 数组。"""

    raw = _stream_text(prompt, max_tokens=1024)
    try:
        import re
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        return json.loads(match.group()) if match else json.loads(raw)
    except Exception:
        return _MOCK_SUGGESTIONS


def generate_marketing_copy(theme: str, data: dict) -> str:
    """
    Generate social media marketing copy directions.

    theme: e.g. "主打菜品", "性价比", "新品上市"
    """
    if USE_MOCK_API:
        return _MOCK_MARKETING

    star_dishes = data.get("matrix_categories", {}).get("Star", [])[:5]
    prompt = f"""你是专业餐饮品牌文案策划，请以「{theme}」为主题，
为以下明星菜品生成 3 个不同风格的小红书/抖音文案方向（各含标题、正文、话题标签）。

明星菜品：{star_dishes}

每个方向用 ### 标题分隔，Markdown 格式输出。"""
    return _stream_text(prompt, max_tokens=1024)
