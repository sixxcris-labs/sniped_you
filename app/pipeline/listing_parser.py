from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.utils.dedupe import dedupe_listings
from app.utils.hashing import calc_hash


def _coerce_price(value: Any) -> Optional[float]:
    """Convert a price-like value to float, returning None if invalid."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def normalize(
    site: str, raw: List[Dict[str, Any]], category: str
) -> List[Dict[str, Any]]:
    """
    Normalize raw scraper output into a consistent listing format.

    Args:
        site: Source site identifier (e.g. "ebay", "craigslist").
        raw: List of raw scraped item dicts.
        category: The listing category (e.g. "bikes", "furniture").

    Returns:
        List of normalized listing dicts.
    """
    normalized: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for record in raw:
        title = record.get("title")
        normalized.append(
            {
                "brand": None,  # optional LLM-based inference
                "model": title,
                "title": title,
                "price": _coerce_price(record.get("price")),
                "category": category,
                "location": record.get("location"),
                "image": record.get("image"),
                "url": record.get("url"),
                "source": record.get("source", site),
                "timestamp": record.get("posted_at") or now_iso,
                "confidence": 1.0 if title else 0.6,
            }
        )

    return normalized
