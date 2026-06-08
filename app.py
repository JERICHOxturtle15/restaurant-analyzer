"""
FastAPI backend for Restaurant Analyzer.

Endpoints
---------
POST /upload          — upload menu CSV
GET  /analyze         — run full pipeline and return summary JSON
GET  /report          — serve final_report.html
GET  /history         — list past analysis sessions from SQLite
GET  /                — serve frontend/index.html
"""

import sys
import uuid
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles

from config.settings import (
    SAMPLE_DATA_DIR, REPORTS_DIR, DATA_DIR, FRONTEND_DIR,
    MENU_REQUIRED_COLUMNS,
)
from src.db.history import init_db, log_entry, get_history

app = FastAPI(title="Restaurant Analyzer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state (reset on server restart; falls back to sample data)
_state: dict = {
    "last_menu_path": None,
    "last_session_id": None,
}


@app.on_event("startup")
def startup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    init_db()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "frontend/index.html not found")
    return HTMLResponse(index.read_text(encoding="utf-8"))


@app.post("/upload")
async def upload_menu(file: UploadFile = File(...)):
    """Accept a CSV file upload. Returns saved filename."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are accepted")

    dest = DATA_DIR / "raw" / f"upload_{uuid.uuid4().hex[:8]}_{file.filename}"
    async with aiofiles.open(dest, "wb") as f:
        content = await file.read()
        await f.write(content)

    _state["last_menu_path"] = str(dest)
    return {"status": "ok", "saved_as": dest.name, "size_bytes": len(content)}


@app.get("/analyze")
def analyze():
    """Run full pipeline (Phase 1→4). Returns summary JSON and path to HTML report."""
    import pandas as pd
    from src.ingestion.data_loader import load_csv, validate_schema, clean_data
    from src.analysis.menu_engineering import classify_boston_matrix, summarize
    from src.analysis.sentiment_analyzer import run_sentiment_analysis, extract_themes
    from src.analysis.competitor_analysis import run_competitor_analysis
    from src.output.report_generator import (
        generate_analysis_report, generate_menu_suggestions, generate_marketing_copy,
    )
    from src.output.html_report import render_html_report

    session_id = str(uuid.uuid4())
    _state["last_session_id"] = session_id
    t0 = time.time()

    # Phase 1
    menu_path = Path(_state["last_menu_path"]) if _state["last_menu_path"] else SAMPLE_DATA_DIR / "menu_sample.csv"
    df_menu = load_csv(menu_path)
    validate_schema(df_menu, MENU_REQUIRED_COLUMNS)
    df_menu = clean_data(df_menu)
    df_matrix = classify_boston_matrix(df_menu)
    summary = summarize(df_matrix)

    # Phase 2
    df_sentiment = run_sentiment_analysis(
        SAMPLE_DATA_DIR / "reviews_sample.csv",
        REPORTS_DIR / "sentiment_report.csv",
    )
    results_raw = [
        {"topics": [t for t in row.split("，") if t]}
        for row in df_sentiment["topics"].fillna("")
    ]
    themes = extract_themes(results_raw)

    # Phase 3
    df_competitor = load_csv(SAMPLE_DATA_DIR / "competitor_sample.csv")
    df_pricing, positioning = run_competitor_analysis(
        df_menu, df_competitor, REPORTS_DIR / "competitor_report.csv"
    )

    # Phase 4 — AI generation (mock when no key)
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

    analysis_report = generate_analysis_report(data)
    suggestions = generate_menu_suggestions(data)
    marketing_copy = generate_marketing_copy("主打菜品", data)

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
        output_path=REPORTS_DIR / "final_report.html",
    )

    elapsed = round(time.time() - t0, 2)

    summary_text = (
        f"分析完成 | 菜品数: {len(df_matrix)} | 评价数: {len(df_sentiment)} "
        f"| 竞品数据: {len(df_competitor)} 行 | 耗时: {elapsed}s"
    )
    log_entry(summary_text, role="system", analysis_type="full", session_id=session_id)

    return {
        "status": "ok",
        "session_id": session_id,
        "elapsed_seconds": elapsed,
        "report_url": "/report",
        "summary": {
            "menu_items": len(df_matrix),
            "reviews_analyzed": len(df_sentiment),
            "competitor_rows": len(df_competitor),
            "top3_themes": list(themes.keys())[:3],
            "matrix_counts": {
                cat: len(df_matrix[df_matrix["matrix_category"] == cat])
                for cat in ["Star", "Plow Horse", "Puzzle", "Dog"]
            },
        },
    }


@app.get("/report", response_class=HTMLResponse)
def get_report():
    """Return the generated final_report.html."""
    report_path = REPORTS_DIR / "final_report.html"
    if not report_path.exists():
        raise HTTPException(404, "报告尚未生成，请先调用 /analyze")
    return HTMLResponse(report_path.read_text(encoding="utf-8"))


@app.get("/history")
def history(limit: int = 20):
    """Return recent analysis history entries from SQLite."""
    rows = get_history(limit=limit)
    return {"count": len(rows), "entries": rows}
