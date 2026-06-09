# -*- coding: utf-8 -*-
"""
每日情报任务入口 — 采集 + 生成报告
用法：python run_daily.py
"""

import sys
import io
import webbrowser
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from collector import init_db, run_collection
from reporter import generate_report


def main():
    print("\n" + "="*50)
    print("  🍽️  餐饮行业情报 · 每日采集")
    print("="*50)

    print("\n[1/2] 采集情报...")
    init_db()
    run_collection()

    print("\n[2/2] 生成简报...")
    report_path = generate_report()

    print("\n" + "="*50)
    print("  ✅ 完成！")
    if report_path and report_path.exists():
        print(f"  报告路径: {report_path}")
        webbrowser.open(report_path.as_uri())
        print("  已自动在浏览器打开报告")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
