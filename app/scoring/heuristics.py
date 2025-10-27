from __future__ import annotations
from typing import Optional, Dict
from app.scoring.scoring_utils import clamp

# ============================================================
# Domain heuristics for marketplace scoring *rule of thumbs*
# ============================================================

KNOWN_BRANDS = {
    "nike", "apple", "samsung", "sony", "trek",
    "ray-ban", "meta", "canon", "dell", "lenovo", "hp",
}

CATEGORY_WEIGHTS = {
    "sneakers": 0.9,
    "electronics": 1.0,
    "bike": 0.8,
    "glasses": 0.7,
    "unknown": 0.6,
}


def category_weight(category: Optional[str]) -> float:
    """Return normalized weight for a given category."""
    key = (category or "unknown").lower()
    return CATEGORY_WEIGHTS.get(key, CATEGORY_WEIGHTS["unknown"])


def brand_signal(brand: Optional[str], cfg: Dict[str, float]) -> float:
    """Apply brand bonus or penalty based on known brand list."""
    if not brand:
        return cfg.get("brand_penalty_unknown", -0.05)
    return cfg.get("brand_bonus_known", 0.10) if brand.lower() in KNOWN_BRANDS else 0.0


def price_gap(price: Optional[float], anchor: Optional[float]) -> float:
    """Compute undervaluation score (lower ratio = better deal)."""
    if not price or price <= 0:
        return 0.0
    if not anchor or anchor <= 0:
        return 0.5
    ratio = price / anchor
    return clamp(1.2 - ratio)
