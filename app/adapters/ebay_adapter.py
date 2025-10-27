from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from .cache_layer import CacheLayer

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass
class EbayAdapter:
    """Compute resale metrics from eBay-like counts.

    This adapter is intentionally network-agnostic. Provide counts directly
    or implement `fetch_counts` in your own subclass that calls eBay APIs and
    returns `(sold_count, active_count, avg_sold_price, avg_active_price)`.
    """

    cache: CacheLayer
    app_id: Optional[str] = None

    def fetch_counts(self, query: str) -> Tuple[int, int, float, float]:
        """Placeholder fetch. Override or monkeypatch in prod/tests.

        Returns: sold_count, active_count, avg_sold_price, avg_active_price
        """
        cache_key = f"ebay:counts:{query}"
        cached = self.cache.get(cache_key)
        if cached:
            return (
                int(cached.get("sold", 0)),
                int(cached.get("active", 0)),
                float(cached.get("avg_sold", 0.0)),
                float(cached.get("avg_active", 0.0)),
            )

        # Default conservative placeholder; set by external fetchers in real usage.
        result = {"sold": 10, "active": 20, "avg_sold": 120.0, "avg_active": 150.0}
        self.cache.set(cache_key, result, ttl_seconds=60 * 30)
        return 10, 20, 120.0, 150.0

    def compute_metrics(self, query: str) -> Dict[str, float]:
        sold, active, avg_sold, avg_active = self.fetch_counts(query)

        total = max(1, sold + active)
        sell_through = _clip01(sold / total)

        if avg_active <= 0:
            resale_anchor = 0.0
        else:
            ratio = (avg_active - avg_sold) / max(1.0, avg_active)
            resale_anchor = _clip01(ratio)

        return {"sell_through_rate": sell_through, "resale_anchor": resale_anchor}
