from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .cache_layer import CacheLayer

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _slope_normalized(values: List[float]) -> float:
    """Least-squares slope normalized to 0..1.

    - Positive, strong uptrend -> near 1.0
    - Flat -> ~0.5
    - Strong downtrend -> near 0.0
    """
    n = len(values)
    if n < 2:
        return 0.5
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den = sum((x - x_mean) ** 2 for x in xs) or 1.0
    slope = num / den

    # Normalize by value range to avoid scale sensitivity
    vmin, vmax = min(values), max(values)
    span = max(1.0, (vmax - vmin))
    norm = slope / span
    # Map from roughly [-1,1] to [0,1]
    return _clip01(0.5 + norm)


@dataclass
class GoogleTrendsAdapter:
    cache: CacheLayer
    token: str | None = None

    def fetch_series(self, keyword: str) -> List[float]:
        # Placeholder series; override in real usage. Cached for stability.
        key = f"gtrends:{keyword}"
        cached = self.cache.get(key)
        if cached:
            return [float(x) for x in cached]
        series = [30, 32, 31, 35, 40, 42, 41, 45, 50, 48]
        self.cache.set(key, series, ttl_seconds=60 * 30)
        return series

    def trend_score(self, keyword: str) -> float:
        series = [float(x) for x in self.fetch_series(keyword) if x is not None]
        if not series:
            return 0.5
        return _slope_normalized(series)
