from __future__ import annotations
from typing import Any, Dict
from db import get_connection


def init_db() -> None:
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    price REAL,
                    permalink TEXT UNIQUE,
                    score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        con.commit()
    finally:
        con.close()


def insert_listing(row: Dict[str, Any]) -> bool:
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (id, title, price, permalink, score)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
                """,
                (
                    row["id"],
                    row.get("title"),
                    row.get("price"),
                    row.get("permalink"),
                    row.get("score"),
                ),
            )
        con.commit()
        return True
    except Exception as e:
        print(f"Insert failed: {e}")
        return False
    finally:
        con.close()


def fetch_recent(limit: int = 10) -> list[Dict[str, Any]]:
    """Return the most recent listings."""
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, price, permalink, score, created_at
                FROM listings
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return rows
    finally:
        con.close()
