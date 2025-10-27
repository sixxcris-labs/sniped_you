from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .cache_layer import CacheLayer

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

@dataclass
class RedditAdapter:
    cache: CacheLayer
    client_id: str | None = None
    client_secret: str | None = None

    def fetch_weekly_mentions(self, keyword: str) -> List[int]:
        # Placeholder; override in production. Cache for stability.
        key = f"reddit:mentions:{keyword}"
        cached = self.cache.get(key)
        if cached:
            return [int(x) for x in cached]
        series = [2, 3, 4, 5, 7, 6, 8, 9]
        self.cache.set(key, series, ttl_seconds=60 * 30)
        return series

    def mention_score(self, keyword: str) -> float:
        series = self.fetch_weekly_mentions(keyword)
        if not series:
            return 0.0
        # Normalize by max in the window, then average.
        m = max(1, max(series))
        avg = sum(x / m for x in series) / len(series)
        return _clip01(avg)
