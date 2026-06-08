import sys
import io
import time
from pathlib import Path

# Force UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    MENU_REQUIRED_COLUMNS, SAMPLE_DATA_DIR, REPORTS_DIR,
    USE_MOCK_API,
)
from src.ingestion.data_loader import load_csv, validate_schema, clean_data
from src.analysis.menu_engineering import classify_boston_matrix, summarize
from src.db.history import init_db, log_entry


def run_menu_analysis(input_path: Path, output_path: Path):
    print(f"  [1/4] 载入数据: {input_path.name}")
    df = load_csv(input_path)
    validate_schema(df, MENU_REQUIRED_COLUMNS)
    df = clean_data(df)
    print(f"        有效行数: {len(df)}")

    print("  [2/4] 波士顿矩阵分类")
    df_result = classify_boston_matrix(df)

    print("  [3/4] 输出菜单报告")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df_result.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary = summarize(df_result)
    summary_path = output_path.parent / "menu_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("  [4/4] 分类汇总")
    print(summary.to_string(index=False))
    for cat, label in [("Star","[Star]明星"), ("Plow Horse","[Plow]耕马"), ("Puzzle","[Puzzle]谜题"), ("Dog","[Dog]瘦狗")]:
        dishes = df_result[df_result["matrix_category"] == cat]["dish_name"].tolist()
        print(f"        {label}: {', '.join(dishes) if dishes else '无'}")

    return df_result, summary


def run_sentiment_phase(reviews_path: Path, output_path: Path):
    from src.analysis.sentiment_analyzer import run_sentiment_analysis, extract_themes

    print(f"  [1/2] 载入评价: {reviews_path.name}")
    df_sentiment = run_sentiment_analysis(reviews_path, output_path)

    print("  [2/2] 主题提取")
    results_raw = [
        {"topics": [t for t in row.split("，") if t]}
        for row in df_sentiment["topics"].fillna("")
    ]
    themes = extract_themes(results_raw)
    top5 = list(themes.items())[:5]
    print(f"        TOP5 主题: {top5}")
    return df_sentiment, themes


def run_competitor_phase(my_menu_df, competitor_path: Path, output_path: Path):
    from src.analysis.competitor_analysis import run_competitor_analysis

    print(f"  [1/1] 载入竞品数据: {competitor_path.name}")
    df_competitor = load_csv(competitor_path)
    print(f"        竞品行数: {len(df_competitor)}")
    df_pricing, positioning = run_competitor_analysis(my_menu_df, df_competitor, output_path)
    for r in positioning["by_restaurant"]:
        print(f"        {r['restaurant_name']}: 均价¥{r['avg_price']} 评分{r['avg_rating']}")
    return df_pricing, positioning, df_competitor


def run_report_phase(df_matrix, summary, df_sentiment, themes,
                     df_pricing, positioning, output_path: Path):
    from src.output.report_generator import (
        generate_analysis_report, generate_menu_suggestions, generate_marketing_copy,
    )
    from src.output.html_report import render_html_report

    matrix_categories = {
        cat: df_matrix[df_matrix["matrix_category"] == cat]["dish_name"].tolist()
        for cat in ["Star", "Plow Horse", "Puzzle", "Dog"]
    }
    data = {
        "menu_summary": summary.to_dict("records"),
        "matrix_categories": matrix_categories,
        "sentiment_counts": {k: int(v) for k, v in df_sentiment["sentiment"].value_counts().items()},
        "top_themes": dict(list(themes.items())[:10]),
        "competitor_pricing": df_pricing.to_dict("records"),
        "positioning": positioning,
    }

    print("  [1/4] 生成 AI 分析报告")
    analysis_report = generate_analysis_report(data)

    print("  [2/4] 生成菜单优化建议")
    suggestions = generate_menu_suggestions(data)
    for s in suggestions[:3]:
        print(f"        {s['dish']} → {s['action']}  [{s['priority']}]")

    print("  [3/4] 生成营销文案方向")
    marketing_copy = generate_marketing_copy("主打菜品", data)

    print("  [4/4] 渲染 HTML 报告")
    render_html_report(
        df_matrix=df_matrix,
        summary=summary,
        df_sentiment=df_sentiment,
        themes=themes,
        df_pricing=df_pricing,
        positioning=positioning,
        suggestions=suggestions,
        analysis_report_md=analysis_report,
        marketing_copy=marketing_copy,
        output_path=output_path,
    )
    print(f"        报告已写入 -> {output_path}")


def run_all():
    init_db()
    t0 = time.time()
    mode = "Mock" if USE_MOCK_API else "Claude API"
    print(f"\n{'='*54}")
    print(f"  Restaurant Analyzer  [{mode} Mode]")
    print(f"{'='*54}")

    print("\n[Phase 1] Menu Engineering")
    df_matrix, summary = run_menu_analysis(
        input_path=SAMPLE_DATA_DIR / "menu_sample.csv",
        output_path=REPORTS_DIR / "menu_analysis.csv",
    )

    print("\n[Phase 2] Sentiment Analysis")
    df_sentiment, themes = run_sentiment_phase(
        reviews_path=SAMPLE_DATA_DIR / "reviews_sample.csv",
        output_path=REPORTS_DIR / "sentiment_report.csv",
    )

    print("\n[Phase 3] Competitor Analysis")
    df_pricing, positioning, _ = run_competitor_phase(
        my_menu_df=df_matrix,
        competitor_path=SAMPLE_DATA_DIR / "competitor_sample.csv",
        output_path=REPORTS_DIR / "competitor_report.csv",
    )

    print("\n[Phase 4] Report Generation")
    run_report_phase(
        df_matrix=df_matrix,
        summary=summary,
        df_sentiment=df_sentiment,
        themes=themes,
        df_pricing=df_pricing,
        positioning=positioning,
        output_path=REPORTS_DIR / "final_report.html",
    )

    elapsed = round(time.time() - t0, 2)
    log_entry(
        f"Full pipeline done | dishes:{len(df_matrix)} | reviews:{len(df_sentiment)} | elapsed:{elapsed}s",
        analysis_type="full",
    )

    print(f"\n{'='*54}")
    print(f"  DONE  ({elapsed}s)")
    print("  Output files:")
    for f in sorted(REPORTS_DIR.iterdir()):
        print(f"    reports/{f.name}  ({f.stat().st_size:,} bytes)")
    print(f"{'='*54}\n")


if __name__ == "__main__":
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode_arg == "all":
        run_all()
    else:
        print(f"用法: python main.py [all]")
