"""
Simple SQLite logger for Sniped You scoring results.
Stores each run of the profitability scorer for future analytics.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any


DB_PATH = Path("data/output/scoring_history.db")


def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS scoring_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            brand TEXT,
            model TEXT,
            price REAL,
            flipScore REAL,
            profitMargin REAL,
            marginPct REAL,
            demand REAL,
            resale_anchor REAL,
            liquidity REAL,
            retail_anchor REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def log_score(result: Dict[str, Any]) -> None:
    """Append a single scoring result to the SQLite database."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    metrics = result.get("metrics", {})
    c.execute(
        """
        INSERT INTO scoring_history
        (title, brand, model, price, flipScore, profitMargin, marginPct,
         demand, resale_anchor, liquidity, retail_anchor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.get("title"),
            result.get("brand"),
            result.get("model"),
            result.get("price"),
            result.get("flipScore"),
            result.get("profitMargin"),
            result.get("marginPct"),
            metrics.get("demand"),
            metrics.get("resale_anchor"),
            metrics.get("liquidity"),
            metrics.get("retail_anchor"),
        ),
    )
    conn.commit()
    conn.close()
    print(f"[log] Added score record to {DB_PATH}")


def fetch_all(limit: int = 10) -> list[Dict[str, Any]]:
    """Retrieve recent scoring results."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM scoring_history ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
