from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright
from app.utils.logger import log
from app.utils.proxies import get_proxies, rotate

KEYWORDS_FILE = Path("config/keywords.json")

# --------------------------------------------------------------------
# Keyword utilities
# --------------------------------------------------------------------
def _load_keywords() -> dict:
    if KEYWORDS_FILE.exists():
        with KEYWORDS_FILE.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

def _save_keywords(keywords: dict) -> None:
    KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with KEYWORDS_FILE.open("w", encoding="utf-8") as f:
        json.dump(keywords, f, indent=2)

def get_search_query(category: str) -> str:
    keywords = _load_keywords()
    query = keywords.get(category.lower(), category)
    if category.lower() not in keywords:
        keywords[category.lower()] = category
        _save_keywords(keywords)
    return query

# --------------------------------------------------------------------
# Selector utilities
# --------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_selectors(site: str = "craigslist") -> Dict[str, List[str]]:
    cfg_path = Path(__file__).resolve().parents[3] / "config" / "selectors" / f"{site}.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Selector config not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def query_first(page, selectors: List[str]):
    for s in selectors:
        try:
            el = page.query_selector(s)
            if el:
                return el
        except Exception:
            continue
    return None

# --------------------------------------------------------------------
# Craigslist scraping logic
# --------------------------------------------------------------------
def _build_url(region: Optional[str], category: str) -> str:
    """Craigslist title-only search URL."""
    base = f"https://{region}.craigslist.org" if region else "https://www.craigslist.org"
    query = get_search_query(category)
    return f"{base}/search/sss?query={query.replace(' ', '+')}&srchType=T&sort=date"

def _setup_browser(playwright, headless: bool, proxy: str | None = None):
    browser = playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
        proxy={"server": proxy} if proxy else None,
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
        locale="en-US",
        viewport={"width": 1280, "height": 900},
    )
    return browser, context, context.new_page()

def _extract_field(card, selectors, attr: str | None = None):
    el = query_first(card, selectors)
    if not el:
        return None
    return el.get_attribute(attr) if attr else el.inner_text().strip()

import re

def _build_result(card, selectors, category: str) -> Dict[str, Any]:
    """Parse one listing card into structured data with better price and location parsing."""
    title = _extract_field(card, selectors["title"])
    if not title:
        return {}

    href = _extract_field(card, selectors["title"], "href")
    price_raw = _extract_field(card, selectors["price"]) or ""
    price_text = re.search(r"\$?\s?(\d+(?:\.\d{1,2})?)", price_raw or title or "")
    price = float(price_text.group(1)) if price_text else None

    location = _extract_field(card, ["span.result-hood"]) or ""
    location = location.strip(" ()")

    return {
        "source": "craigslist",
        "title": title.strip(),
        "price": price,
        "url": href,
        "location": location,
        "posted_at": _extract_field(card, selectors["time"], "title")
                     or _extract_field(card, selectors["time"]),
        "image": _extract_field(card, selectors.get("image", []), "src"),
        "category": category,
    }


def _extract_listings(page, selectors, url: str, limit: int, category: str) -> List[Dict[str, Any]]:
    log.info(f"[scrape] Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("div.cl-search-result", timeout=15000)
    page.wait_for_timeout(2000)
    items: List[Dict[str, Any]] = []
    for container_sel in selectors.get("listing_container", []):
        for el in page.query_selector_all(container_sel)[:limit]:
            data = _build_result(el, selectors, category)
            if data:
                items.append(data)
    # Filter by keyword relevance
    keyword = category.lower()
    items = [r for r in items if keyword in (r["title"] or "").lower()]
    return items

def scrape(*, category: str, region: str | None = None, limit: int = 30, headless: bool = True) -> List[Dict[str, Any]]:
    selectors = load_selectors("craigslist")
    url = _build_url(region, category)
    results: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        browser, context, page = _setup_browser(p, headless, proxy=None)
        try:
            log.info(f"[scrape] Launching browser for '{category}' in {region}")
            results = _extract_listings(page, selectors, url, limit, category)
        except Exception as e:
            log.warning(f"[scrape] Craigslist scrape failed: {e}")
        finally:
            context.close()
            browser.close()
    category_safe = category.replace(" ", "_")
    out_path = Path("data/output") / f"craigslist_{category_safe}_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log.info(f"[done] wrote {out_path} ({len(results)} items)")
    return results

# --------------------------------------------------------------------
# CLI entrypoint
# --------------------------------------------------------------------
if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--category", default="pokemon cards")
    parser.add_argument("--region", default="houston")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()
    data = scrape(category=args.category, region=args.region, limit=args.limit, headless=args.headless)
    print(f"[output] Scraped {len(data)} relevant items")
