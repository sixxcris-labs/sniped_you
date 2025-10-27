from __future__ import annotations
import json
import os
import sys
import glob
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
from app.utils.metrics import Metrics
from app.storage.storage import save_listing_batch

# Config loader
from app.config_loader import get as load_cfg

# Logging
from app.utils.logger import log

# ============================================================
# Scoring module imports
# ============================================================

from app.scoring.scoring_utils import to_float, clamp, normalize_confidence
from app.scoring.heuristics import category_weight, brand_signal, price_gap
from app.scoring.rarity_utils import apply_rarity_flipscore
from app.scoring.scoring_model import compute_base_score

# ============================================================
# Constants
# ============================================================

OUTPUT_DIR = "data/output"

DEFAULT_SCORING: Dict[str, Any] = {
    "w_confidence": 0.20,
    "w_price_gap": 0.55,
    "w_brand_signal": 0.15,
    "w_category": 0.10,
    "min_valid_price": 10,
    "max_valid_price": 5000,
    "default_anchor_multiplier": 1.20,
    "brand_bonus_known": 0.10,
    "brand_penalty_unknown": -0.05,
}

# ============================================================
# Data model
# ============================================================

@dataclass
class Listing:
    brand: Optional[str]
    model: Optional[str]
    category: Optional[str]
    price: Optional[float]
    confidence: Optional[float]
    market_anchor: Optional[float]
    raw: Dict[str, Any]

# ============================================================
# Core scoring logic
# ============================================================

def score_listing(item: Listing, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Compute weighted flip score for a listing using shared scoring modules."""
    price = item.price
    valid = price is not None and cfg["min_valid_price"] <= price <= cfg["max_valid_price"]

    conf = normalize_confidence(item.confidence)
    brand_adj = brand_signal(item.brand, cfg)
    cat_wt = category_weight(item.category)
    anchor = item.market_anchor or (price * cfg["default_anchor_multiplier"] if price else None)
    gap = price_gap(price, anchor)

    # Core score computation via scoring_model
    base_score = compute_base_score(conf, gap, brand_adj, cat_wt, cfg)

    # Optional rarity adjustment (safe default = 1.0)
    flip_score = apply_rarity_flipscore(base_score, rarity_factor=1.0)

    profit_margin = anchor - price if (anchor and price) else None
    margin_pct = (profit_margin / anchor * 100) if (profit_margin and anchor) else None
    suggested_buy = round(price * 0.9, 2) if price else None

    return {
        **item.raw,
        "flipScore": round(clamp(flip_score), 4),
        "profitMargin": round(profit_margin, 2) if profit_margin else None,
        "marginPct": round(margin_pct, 2) if margin_pct else None,
        "suggested_buy_price": suggested_buy,
        "valid": valid,
    }

def _as_listing(data: Dict[str, Any]) -> Listing:
    """Normalize dict to Listing object."""
    return Listing(
        brand=data.get("brand"),
        model=data.get("model"),
        category=data.get("category") or data.get("type") or data.get("category_hint"),
        price=to_float(data.get("price")),
        confidence=to_float(data.get("confidence")),
        market_anchor=to_float(data.get("market_avg") or data.get("anchor_price")),
        raw=data,
    )

# ============================================================
# File utilities
# ============================================================

def _resolve_path(env_var: str, default: str, base_dir: str = OUTPUT_DIR) -> str:
    """Safely resolve file path from env var with sandboxing."""
    raw_path = os.environ.get(env_var, default)
    abs_base = os.path.abspath(base_dir)
    candidate = os.path.abspath(os.path.join(abs_base, os.path.basename(raw_path)))

    if not candidate.startswith(abs_base):
        print(f"[warn] Unsafe path in {env_var}: {raw_path!r}, using default.")
        candidate = os.path.join(abs_base, os.path.basename(default))
    os.makedirs(os.path.dirname(candidate), exist_ok=True)
    return candidate

def merge_scored_outputs(output_dir: str = OUTPUT_DIR) -> Path:
    """Merge all scored_*.json files into a single sorted file."""
    files = glob.glob(f"{output_dir}/scored_*.json")
    merged: List[Dict[str, Any]] = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    merged.extend(data)
        except Exception as e:
            print(f"[warn] Skipping {f}: {e}")

    merged.sort(key=lambda x: x.get("flipScore", 0), reverse=True)
    out_path = Path(output_dir) / "all_scored_listings.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)
    print(f"[done] Merged scored outputs → {out_path}")
    return out_path

# ============================================================
# CLI entrypoint
# ============================================================

from app.storage.storage import save_listing_batch  # add this near other imports

import argparse

def main() -> int:
    parser = argparse.ArgumentParser(description="Compute profitability scores for listings.")
    parser.add_argument("--input", default=f"{OUTPUT_DIR}/cleaned.json", help="Input JSON path")
    parser.add_argument("--output", default=f"{OUTPUT_DIR}/scored.json", help="Output JSON path")
    args = parser.parse_args()

    input_path = args.input
    cfg = {**DEFAULT_SCORING, **load_cfg("SNIPER_SCORING_CFG", "config/scoring.yaml")}

    if not os.path.exists(input_path):
        print(f"[scorer] Input not found: {input_path}")
        return 2

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[scorer] Error reading {input_path}: {e}")
        return 4

    listings = data.get("listings") if isinstance(data, dict) else data
    if not isinstance(listings, list):
        print("[scorer] Invalid JSON structure: expected list or { 'listings': [...] }.")
        return 3

    scored = [score_listing(_as_listing(d), cfg) for d in listings]

    out_path = Path(args.output)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(scored, f, indent=2)
    except OSError as e:
        print(f"[scorer] Error writing {out_path}: {e}")
        return 5

    try:
        save_listing_batch(scored)
    except Exception as e:
        print(f"[db] Failed to save listings to database: {e}")

    print(f"[scorer] ✅ Scored {len(scored)} listings → {out_path}")
    merge_scored_outputs()
    return 0

if __name__ == "__main__":
    sys.exit(main())
