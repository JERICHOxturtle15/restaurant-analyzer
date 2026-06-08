# -*- coding: utf-8 -*-
"""
每日餐饮行业情报采集器 — TO C 消费行为版
目标：每日 30-50 条高质量消费者信号，来自抖音/小红书/大众点评相关内容
"""

import json
import time
import hashlib
import sqlite3
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, date, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
TOPICS_FILE = BASE_DIR / "topics.json"
DB_FILE = BASE_DIR / "intel.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 排除这些词的标题——行业报告/宏观分析，不是消费者行为
EXCLUDE_KEYWORDS = [
    "报告", "白皮书", "峰会", "论坛", "指数", "融资", "上市", "亿元",
    "招股", "财报", "季报", "年报", "调研", "分析师", "政策", "监管",
    "展会", "博览会", "发布会", "投资", "并购", "数据显示", "同比增长"
]

# 消费者行为信号关键词 — 每组限取最多 8 条，共 6 组 = ~48 条上限
SEARCH_GROUPS = [
    {
        "query": "小红书 餐厅 爆款 打卡 种草",
        "category": "小红书种草",
        "limit": 8,
    },
    {
        "query": "抖音 餐饮 爆火 创意 新玩法",
        "category": "抖音爆款",
        "limit": 8,
    },
    {
        "query": "大众点评 网红菜 必点 好评 体验",
        "category": "大众点评热门",
        "limit": 8,
    },
    {
        "query": "餐厅 互动 仪式感 顾客体验 创新",
        "category": "体验与互动",
        "limit": 6,
    },
    {
        "query": "餐饮 新模式 门店 消费 爆款打法",
        "category": "打法与模式",
        "limit": 6,
    },
    {
        "query": "新中式 茶饮 烘焙 特色菜品 网红",
        "category": "特色产品",
        "limit": 6,
    },
]


def load_topics() -> dict:
    with open(TOPICS_FILE, encoding="utf-8") as f:
        return json.load(f)


def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intel_items (
            id TEXT PRIMARY KEY,
            date TEXT,
            source TEXT,
            category TEXT,
            title TEXT,
            url TEXT,
            summary TEXT,
            pub_date TEXT,
            collected_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def item_id(source: str, title: str) -> str:
    return hashlib.md5(f"{source}:{title}".encode()).hexdigest()


def save_items(items: list) -> int:
    if not items:
        return 0
    conn = sqlite3.connect(DB_FILE)
    today = date.today().isoformat()
    now = datetime.now().isoformat()
    saved = 0
    for it in items:
        iid = item_id(it["source"], it["title"])
        cur = conn.execute(
            "INSERT OR IGNORE INTO intel_items VALUES (?,?,?,?,?,?,?,?,?)",
            (iid, today, it["source"], it.get("category", ""),
             it["title"], it.get("url", ""), it.get("summary", ""),
             it.get("pub_date", ""), now)
        )
        saved += cur.rowcount
    conn.commit()
    conn.close()
    return saved


MAX_AGE_HOURS = 48  # 超过48小时的内容直接丢弃


def is_relevant(title: str) -> bool:
    """过滤掉行业报告/宏观分析类标题"""
    return not any(kw in title for kw in EXCLUDE_KEYWORDS)


def is_fresh(pub_date_str: str) -> bool:
    """检查发布时间是否在 MAX_AGE_HOURS 以内"""
    if not pub_date_str:
        return False
    try:
        pub_dt = parsedate_to_datetime(pub_date_str)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - pub_dt
        return age <= timedelta(hours=MAX_AGE_HOURS)
    except Exception:
        return False


def parse_rss_items(content: bytes, limit: int, category: str) -> list:
    items = []
    try:
        root = ET.fromstring(content)
        for entry in root.findall(".//item"):
            if len(items) >= limit:
                break
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            desc = (entry.findtext("description") or "").strip()
            pub = (entry.findtext("pubDate") or "").strip()

            src_el = entry.find("source")
            source = src_el.text.strip() if src_el is not None and src_el.text else "资讯"

            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                if not source or source == "资讯":
                    source = parts[1].strip()

            if title and is_relevant(title) and is_fresh(pub):
                items.append({
                    "source": source,
                    "category": category,
                    "title": title,
                    "url": link,
                    "summary": desc[:150] if desc else "",
                    "pub_date": pub,
                })
    except Exception as e:
        print(f"    RSS解析错误: {e}")
    return items


def fetch_group(group: dict) -> list:
    """从 Google News 抓取一组关键词，限制条数并过滤"""
    try:
        # when:1d 限制只返回过去24小时的内容
        query_with_time = group["query"] + " when:1d"
        q = urllib.parse.quote(query_with_time)
        url = f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.content, group["limit"], group["category"])
        time.sleep(1.2)
        return items
    except Exception as e:
        print(f"    [{group['category']}] 抓取失败: {e}")
        return []


def fetch_custom_directions(directions: list) -> list:
    real = [d for d in directions if not d.startswith("在这里添加")]
    items = []
    for d in real:
        group = {"query": d, "category": "自定义方向", "limit": 5}
        result = fetch_group(group)
        if result:
            items += result
            print(f"    [自定义:{d[:12]}] {len(result)} 条")
    return items


def deduplicate(items: list) -> list:
    seen = set()
    result = []
    for it in items:
        key = it["title"][:25]
        if key not in seen:
            seen.add(key)
            result.append(it)
    return result


def run_collection() -> list:
    topics = load_topics()
    all_items = []

    print("  → 消费者行为信号采集（6个方向）...")
    for group in SEARCH_GROUPS:
        result = fetch_group(group)
        all_items += result
        print(f"    [{group['category']}] {len(result)} 条")

    # 用户自定义方向
    custom = topics.get("custom_directions", [])
    real_custom = [d for d in custom if not d.startswith("在这里添加")]
    if real_custom:
        print(f"  → 自定义方向 ({len(real_custom)} 个)...")
        all_items += fetch_custom_directions(real_custom)

    all_items = deduplicate(all_items)
    saved = save_items(all_items)
    print(f"  ✓ 精选 {len(all_items)} 条，新增 {saved} 条入库")
    return all_items
