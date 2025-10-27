import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class CacheLayer:
    """Lightweight SQLite cache with TTL support.

    - Stores JSON-serialized values by key.
    - Keys are application-defined strings (caller should namespace).
    - File lives under `data/output/cache.sqlite` by default.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        default_path = Path("data/output/cache.sqlite")
        self.db_path = Path(db_path) if db_path else default_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path.as_posix())

    def _init_db(self) -> None:
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  expires_at INTEGER
                )
                """
            )

    def get(self, key: str) -> Optional[Any]:
        now = int(time.time())
        with self._conn() as con:
            cur = con.execute("SELECT value, expires_at FROM cache WHERE key=?", (key,))
            row = cur.fetchone()
            if not row:
                return None
            value, expires_at = row
            if expires_at is not None and expires_at < now:
                con.execute("DELETE FROM cache WHERE key=?", (key,))
                return None
            try:
                return json.loads(value)
            except Exception:
                return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        expires_at = int(time.time()) + int(ttl_seconds) if ttl_seconds else None
        payload = json.dumps(value)
        with self._conn() as con:
            con.execute(
                "REPLACE INTO cache(key, value, expires_at) VALUES (?, ?, ?)",
                (key, payload, expires_at),
            )
