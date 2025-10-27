from __future__ import annotations
from dataclasses import dataclass
from .cache_layer import CacheLayer

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

@dataclass
class KeepaAdapter:
    cache: CacheLayer
    api_key: str | None = None

    def retail_anchor(self, avg_90d_price: float, msrp: float) -> float:
        """Return a 0..1 anchor where values near 1 mean good resale margin.

        Uses a simple heuristic: if avg_90d_price is much lower than msrp, the
        anchor is higher. Completely bounded to [0,1].
        """
        if msrp <= 0:
            return 0.0
        discount = (msrp - max(0.0, avg_90d_price)) / msrp
        return _clip01(discount)
