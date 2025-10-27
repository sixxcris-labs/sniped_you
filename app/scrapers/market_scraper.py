from __future__ import annotations
import os
from pathlib import Path
import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = "data/output"
RAW_PATH = os.path.join(OUT_DIR, "scraped_raw.json")
PARSED_PATH = os.path.join(OUT_DIR, "parsed_listings.json")


def save_json(path: str, obj: Any) -> None:
    """Write JSON to disk with UTF-8 encoding."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def parse_listings(
    site: str, raw: List[Dict[str, Any]], category: str
) -> List[Dict[str, Any]]:
    """Import and call the listing parser to normalize scraped data."""
    mod = importlib.import_module("app.parsers.listing_parser")
    normalize = getattr(mod, "normalize", None)
    if not callable(normalize):
        raise RuntimeError("listing_parser.normalize is missing or not callable")
    return normalize(site, raw, category)


# -----------------------------
# SAFE SCRAPER WHITELIST
# -----------------------------
SCRAPER_MODULES: Dict[str, str] = {
    "craigslist": "app.scrapers.sites.craigslist_scraper",
    "ebay": "app.scrapers.sites.ebay_scraper",
    "nextdoor": "app.scrapers.sites.nextdoor_scraper",
}


def load_scraper(site: str):
    """
    Safely import a scraper module from the trusted whitelist.
    Prevents arbitrary import path injection.
    """
    if site not in SCRAPER_MODULES:
        raise ValueError(
            f"Invalid site '{site}'. Allowed: {', '.join(sorted(SCRAPER_MODULES))}"
        )

    module_name = SCRAPER_MODULES[site]
    try:
        mod = importlib.import_module(module_name)
    except ImportError as e:
        raise RuntimeError(f"Failed to import {module_name}: {e}") from e

    scrape_fn = getattr(mod, "scrape", None)
    if not callable(scrape_fn):
        raise RuntimeError(
            f"Module '{module_name}' does not define a callable 'scrape'"
        )

    return scrape_fn


# -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape marketplace listings by site/category."
    )
    parser.add_argument("--site", required=True, choices=list(SCRAPER_MODULES.keys()))
    parser.add_argument(
        "--category", required=True, help="e.g. bikes, electronics, furniture"
    )
    parser.add_argument(
        "--region", help="e.g. houston for Craigslist; optional for eBay"
    )
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument(
        "--visible", action="store_true", help="Run non-headless for debugging"
    )
    args = parser.parse_args()

    headless = not args.visible

    try:
        scrape_fn = load_scraper(args.site)
    except Exception as exc:
        print(f"[error] {exc}")
        return 2

    # Run scraper
    raw = scrape_fn(
        category=args.category,
        region=args.region,
        limit=args.limit,
        headless=headless,
    )
    meta = {
        "site": args.site,
        "category": args.category,
        "region": args.region,
        "count": len(raw),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    save_json(RAW_PATH, {"meta": meta, "items": raw})

    parsed = parse_listings(args.site, raw, args.category)
    save_json(PARSED_PATH, {"meta": meta, "items": parsed})

    print(f"[scrape] {args.site}/{args.category}: raw={len(raw)} parsed={len(parsed)}")
    print(f"[scrape] wrote {RAW_PATH} and {PARSED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
