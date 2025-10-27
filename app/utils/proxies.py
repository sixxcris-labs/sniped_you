import random
from typing import List, Dict, Optional

# --------------------------------------------------------------------
# Proxy utilities (NO PROXIES by default)
# --------------------------------------------------------------------

def get_proxies() -> List[Dict[str, str]]:
    """Return an empty list so scrapers run without proxies."""
    return []


def rotate(proxies: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """
    Return an empty list when no proxies are configured.
    Scrapers should iterate over this result safely.
    """
    if not proxies:
        return []
    return [random.choice(proxies)]