from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path("data/listings.db")

def _init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            title TEXT,
            brand TEXT,
            model TEXT,
            category TEXT,
            price REAL,
            flip_score REAL,
            profit_margin REAL,
            margin_pct REAL,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def save_listing_batch(records: List[Dict[str, Any]], db_path: str | Path = DB_PATH):
    """Save a batch of scored listings into SQLite."""
    if not records:
        print("[db] No records to save.")
        return

    conn = sqlite3.connect(db_path)
    _init_db(conn)

    with conn:
        conn.executemany("""
            INSERT INTO listings
                (source, title, brand, model, category, price, flip_score, profit_margin, margin_pct, url)
            VALUES
                (:source, :title, :brand, :model, :category, :price, :flipScore, :profitMargin, :marginPct, :url)
        """, records)
    conn.close()
    print(f"[db] Inserted {len(records)} records into {db_path}")
