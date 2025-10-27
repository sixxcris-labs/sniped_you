from typing import Dict, Iterable
from app.utils.hashing import calc_hash

def dedupe_listings(listings: Iterable[Dict]) -> list[Dict]:
    """Return listings with duplicate URLs removed."""
    seen = set()
    result = []
    for entry in listings:
        key = entry.get("url") or entry.get("link")
        if key and key not in seen:
            seen.add(key)
            result.append(entry)
    return result
