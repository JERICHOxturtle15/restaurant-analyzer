"""
Render all pipeline results into reports/final_report.html using Jinja2.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from config.settings import TEMPLATES_DIR, USE_MOCK_API


def _sentiment_counts(df_sentiment: pd.DataFrame) -> dict:
    if "sentiment" not in df_sentiment.columns:
        return {"positive": 0, "neutral": 0, "negative": 0}
    vc = df_sentiment["sentiment"].value_counts()
    return {
        "positive": int(vc.get("positive", 0)),
        "neutral":  int(vc.get("neutral",  0)),
        "negative": int(vc.get("negative", 0)),
    }


def _top_themes(themes: dict, n: int = 10) -> list[dict]:
    return [{"theme": k, "count": v} for k, v in list(themes.items())[:n]]


def render_html_report(
    df_matrix: pd.DataFrame,
    summary: pd.DataFrame,
    df_sentiment: pd.DataFrame,
    themes: dict,
    df_pricing: pd.DataFrame,
    positioning: dict,
    suggestions: list[dict],
    analysis_report_md: str,
    marketing_copy: str,
    output_path: Path,
) -> None:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    template = env.get_template("report_template.html")

    # Safely convert numeric columns for the template
    menu_table = df_matrix[
        ["dish_name", "category", "price", "cost", "profit_margin", "monthly_orders", "matrix_category"]
    ].copy()
    menu_table["profit_margin"] = menu_table["profit_margin"].round(4)

    context = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_mode": "Mock（无 API Key）" if USE_MOCK_API else "Claude API",
        "menu_table":         menu_table.to_dict("records"),
        "menu_summary_table": summary.to_dict("records"),
        "sentiment_counts":   _sentiment_counts(df_sentiment),
        "top_themes":         _top_themes(themes),
        "comp_by_restaurant": positioning.get("by_restaurant", []),
        "comp_pricing_rows":  _pricing_rows(df_pricing),
        "suggestions":        suggestions,
        "analysis_report_md": analysis_report_md,
        "marketing_copy":     marketing_copy,
    }

    html = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def _pricing_rows(df_pricing: pd.DataFrame) -> list[dict]:
    keep = ["category", "my_avg_price", "competitor_avg", "price_gap", "gap_pct"]
    cols = [c for c in keep if c in df_pricing.columns]
    return df_pricing[cols].to_dict("records")
