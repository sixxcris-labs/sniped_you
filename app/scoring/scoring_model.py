from __future__ import annotations
from typing import Dict
from app.scoring.scoring_utils import clamp, sigmoid

# ============================================================
# Base scoring model
# ============================================================

def compute_base_score(
    confidence: float,
    price_gap: float,
    brand_adj: float,
    category_weight: float,
    cfg: Dict[str, float],
) -> float:
    """
    Compute the base flip score using weighted components.

    Formula:
        score_raw = (
            w_confidence * confidence
          + w_price_gap * price_gap
          + w_brand_signal * (0.5 + brand_adj)
          + w_category * category_weight
        )

    The result is clamped to [0, 1] and smoothed with a mild sigmoid.
    """
    score_raw = (
        cfg["w_confidence"] * confidence
        + cfg["w_price_gap"] * price_gap
        + cfg["w_brand_signal"] * (0.5 + brand_adj)
        + cfg["w_category"] * category_weight
    )

    # Apply mild smoothing to reduce noise and extreme spikes
    smoothed = sigmoid(score_raw ** 0.9)
    return round(clamp(smoothed, 0.0, 1.0), 4)
