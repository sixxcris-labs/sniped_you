from __future__ import annotations
import math
from typing import Any, Optional

# ============================================================
# Math utilities
# ============================================================

def sigmoid(x: float) -> float:
    """Stable sigmoid used in scoring formulas."""
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Safely divide two numbers with fallback."""
    return a / b if b not in (0, None) else default


def clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, val))


# ============================================================
# Conversion and normalization helpers
# ============================================================

def to_float(value: Any) -> Optional[float]:
    """Convert numeric-like value to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def normalize_confidence(value: Any) -> float:
    """Normalize a confidence score to [0, 1], default 0.5 if missing."""
    val = to_float(value)
    return clamp(val if val is not None else 0.5)
