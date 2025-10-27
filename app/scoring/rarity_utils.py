from __future__ import annotations
from typing import Optional
from app.scoring.scoring_utils import clamp

# ============================================================
# Rarity adjustment utilities
# ============================================================

def rarity_boost(listing_count: Optional[int], category_avg: Optional[int]) -> float:
    """
    Compute a rarity multiplier ∈ [0.8, 1.3].

    - Boosts rare listings (<25% of category avg)
    - Slight boost for moderately rare (<50%)
    - Penalizes oversupplied listings (>150%)
    - Returns 1.0 for balanced markets
    """
    if not listing_count or not category_avg or category_avg <= 0:
        return 1.0

    ratio = listing_count / category_avg
    if ratio < 0.25:
        factor = 1.3
    elif ratio < 0.5:
        factor = 1.15
    elif ratio > 1.5:
        factor = 0.8
    else:
        factor = 1.0

    return round(clamp(factor, 0.8, 1.3), 4)


def apply_rarity_flipscore(base_score: float, rarity_factor: float) -> float:
    """
    Apply rarity multiplier to flip score, keeping result in [0, 1].

    Args:
        base_score: base computed flip score
        rarity_factor: rarity multiplier (from rarity_boost)
    """
    adjusted = base_score * rarity_factor
    return round(clamp(adjusted, 0.0, 1.0), 4)
