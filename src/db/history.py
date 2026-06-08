"""
SQLite-backed chat/analysis history.

Table: analysis_history
  id            INTEGER PRIMARY KEY
  timestamp     TEXT
  session_id    TEXT
  role          TEXT  — 'user' | 'assistant' | 'system'
  content       TEXT
  analysis_type TEXT  — 'menu' | 'sentiment' | 'competitor' | 'report' | 'full'
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from config.settings import DB_PATH


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT    NOT NULL,
                session_id    TEXT    NOT NULL,
                role          TEXT    NOT NULL,
                content       TEXT    NOT NULL,
                analysis_type TEXT
            )
        """)
        conn.commit()


def log_entry(
    content: str,
    role: str = "system",
    analysis_type: str = "full",
    session_id: str | None = None,
) -> str:
    if session_id is None:
        session_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """INSERT INTO analysis_history
               (timestamp, session_id, role, content, analysis_type)
               VALUES (?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(timespec="seconds"), session_id, role, content, analysis_type),
        )
        conn.commit()
    return session_id


def get_history(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_history WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]
