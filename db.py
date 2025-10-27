from __future__ import annotations
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    # Prefer full DATABASE_URL if present; otherwise use discrete DB_* values
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url, cursor_factory=RealDictCursor)
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "sniped"),
        user=os.getenv("DB_USER", "sniper"),
        password=os.getenv("DB_PASSWORD", "sniped_pass"),
        cursor_factory=RealDictCursor,
    )
    return conn


def test_connection() -> bool:
    try:
        con = get_connection()
        with con.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
        con.close()
        return result and list(result.values())[0] == 1
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
