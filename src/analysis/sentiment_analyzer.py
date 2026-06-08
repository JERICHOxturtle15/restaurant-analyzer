"""
Phase 2 — Sentiment analysis powered by Claude API.

Public interface
----------------
analyze_reviews(reviews)  -> list[dict]   per-review: sentiment / topics / key_phrases
extract_themes(results)   -> dict         topic-frequency map across all results
run_sentiment_analysis(reviews_path, output_path) -> pd.DataFrame

When USE_MOCK_API is True (no API key), all Claude calls return realistic mock data.
"""

import json
import re
import random
import anthropic
import pandas as pd
from pathlib import Path

from config.settings import ANTHROPIC_API_KEY, USE_MOCK_API

_BATCH_SIZE = 10

_client: anthropic.Anthropic | None = None

# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_TOPICS_POOL = [
    ["口味好", "性价比高"],
    ["服务好", "口味好"],
    ["口味好", "份量足"],
    ["性价比高", "环境好"],
    ["口味好"],
    ["服务慢", "等待时间长"],
    ["口味一般", "价格偏高"],
    ["新鲜", "口味好", "推荐"],
    ["服务好", "环境好", "性价比高"],
    ["口味好", "火候到位"],
]

_MOCK_PHRASES_POOL = [
    ["嫩滑", "推荐", "必点"],
    ["新鲜", "好吃"],
    ["下饭", "性价比高"],
    ["等太久", "一般"],
    ["香浓", "入味"],
    ["鲜嫩", "满意"],
    ["偏贵", "还好"],
    ["百吃不厌", "经典"],
]

_MOCK_SENTIMENTS = (
    ["positive"] * 7 + ["neutral"] * 2 + ["negative"] * 1
)


def _mock_analyze_reviews(reviews: list[str]) -> list[dict]:
    random.seed(42)
    results = []
    for i in range(len(reviews)):
        results.append({
            "sentiment": _MOCK_SENTIMENTS[i % len(_MOCK_SENTIMENTS)],
            "topics": _MOCK_TOPICS_POOL[i % len(_MOCK_TOPICS_POOL)],
            "key_phrases": _MOCK_PHRASES_POOL[i % len(_MOCK_PHRASES_POOL)],
        })
    return results


# ── Real API helpers ──────────────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _build_batch_prompt(reviews: list[str]) -> str:
    numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reviews))
    return f"""你是一位专业的餐饮评价分析师。请对下列顾客评价进行情感分析。

评价列表：
{numbered}

请严格以 JSON 数组返回，每条评价对应一个对象，字段如下：
{{
  "sentiment": "positive" | "negative" | "neutral",
  "topics": ["主题标签列表，如：口味好、服务慢、性价比高、环境好等，最多5个"],
  "key_phrases": ["2-4个最能代表评价的关键词或短语"]
}}

数组长度必须等于输入评价数量（{len(reviews)} 条）。只返回 JSON 数组，不要有任何额外文字。"""


def _parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def _real_analyze_reviews(reviews: list[str]) -> list[dict]:
    client = _get_client()
    all_results: list[dict] = []

    for start in range(0, len(reviews), _BATCH_SIZE):
        batch = reviews[start: start + _BATCH_SIZE]
        full_text = ""

        with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": _build_batch_prompt(batch)}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text

        parsed = _parse_json_array(full_text)
        while len(parsed) < len(batch):
            parsed.append({"sentiment": "neutral", "topics": [], "key_phrases": []})
        all_results.extend(parsed[: len(batch)])

    return all_results


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_reviews(reviews: list[str]) -> list[dict]:
    """
    Analyze review texts. Uses Claude API when key is configured, mock otherwise.

    Returns list of dicts (same length as input):
      - sentiment:   "positive" | "negative" | "neutral"
      - topics:      list[str]
      - key_phrases: list[str]
    """
    if not reviews:
        return []
    if USE_MOCK_API:
        return _mock_analyze_reviews(reviews)
    return _real_analyze_reviews(reviews)


def extract_themes(results: list[dict]) -> dict:
    """
    Count topic frequencies across analyze_reviews() results.

    Returns dict sorted by descending count:
      {"口味好": 18, "服务慢": 12, ...}
    """
    counts: dict[str, int] = {}
    for item in results:
        for topic in item.get("topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


def run_sentiment_analysis(reviews_path: Path, output_path: Path) -> pd.DataFrame:
    """
    Load reviews CSV, analyze every row, write sentiment_report.csv.

    Input CSV:  dish_name, review_text
    Output CSV: dish_name, review_text, sentiment, topics, key_phrases
    """
    df = pd.read_csv(reviews_path, encoding="utf-8-sig")
    reviews = df["review_text"].tolist()
    mode = "mock" if USE_MOCK_API else "Claude API"
    print(f"      共 {len(reviews)} 条评价，模式: {mode}")

    results = analyze_reviews(reviews)

    df["sentiment"] = [r.get("sentiment", "neutral") for r in results]
    df["topics"] = [
        "，".join(r.get("topics", [])) if isinstance(r.get("topics"), list) else ""
        for r in results
    ]
    df["key_phrases"] = [
        "，".join(r.get("key_phrases", [])) if isinstance(r.get("key_phrases"), list) else ""
        for r in results
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df
