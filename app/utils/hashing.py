import hashlib
import json
from typing import Any


def calc_hash(data: Any) -> str:
    """Return a stable hash for JSON-serializable data structures."""
    normalized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
