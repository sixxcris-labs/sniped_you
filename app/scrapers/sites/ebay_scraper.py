from __future__ import annotations
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache
from playwright.sync_api import sync_playwright

from app.utils.logger import log
from app.utils.proxies import get_proxies, rotate

# --------------------------------------------------------------------
# Config
# --------------------------------------------------------------------
OUTPUT_DIR = Path("data/output")
KEYWORDS_FILE = Path("config/keywords.json")
DEFAULT_CATEGORY = "pokemon cards"

# --------------------------------------------------------------------
# Selector loader
# --------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_selectors(site: str = "ebay") -> Dict[str, str]:
    """Load CSS selectors for a given site from config (cached)."""
    cfg_path = Path(__file__).resolve().parents[3] / "config" / "selectors" / f"{site}.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Selector config not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

# --------------------------------------------------------------------
# Keyword Management
# --------------------------------------------------------------------
def _load_keywords() -> dict[str, str]:
    if KEYWORDS_FILE.exists():
        try:
            with KEYWORDS_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def _save_keywords(keywords: dict[str, str]) -> None:
    KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with KEYWORDS_FILE.open("w", encoding="utf-8") as f:
        json.dump(keywords, f, indent=2)

def _build_url(category: str) -> str:
    keywords = _load_keywords()
    query = keywords.get(category.lower(), category)
    if category.lower() not in keywords:
        keywords[category.lower()] = category
        _save_keywords(keywords)
    params = {"_nkw": query, "_sop": "10", "_ipg": "60"}
    return "https://www.ebay.com/sch/i.html?" + urllib.parse.urlencode(params)

# --------------------------------------------------------------------
# Browser Setup
# --------------------------------------------------------------------
def _setup_browser(playwright, headless: bool, proxy: Optional[str] = None):
    log.info(f"[proxy] Launching browser {'with proxy' if proxy else 'without proxy'}: {proxy or 'none'}")
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

# --------------------------------------------------------------------
# Parsing Helpers
# --------------------------------------------------------------------
def _parse_price(raw: str) -> Optional[float]:
    if not raw:
        return None
    raw = raw.replace("$", "").replace(",", "")
    for token in raw.split():
        try:
            return float(token)
        except ValueError:
            continue
    return None

def _clean_title(title: str) -> str:
    """Remove noise, marketing phrases, and normalize product titles."""
    if not title:
        return ""

    # Remove eBay-specific junk
    noise_patterns = [
        r"NEW LISTING",
        r"Opens in a new window or tab",
        r"Shop on eBay",
        r"Learn more",
        r"Free shipping",
    ]
    for pat in noise_patterns:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # Remove 'Pack' counts, year suffixes, and excessive punctuation
    title = re.sub(r"\b\d+\s*Pack\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b\d{4}\b", "", title)  # remove year numbers
    title = re.sub(r"[\n\r\t]+", " ", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()


def _parse_card(card, selectors: Dict[str, str], category: str) -> Optional[Dict[str, Any]]:
    """Extract structured listing data from a single card."""
    get_text = lambda key: (card.query_selector(selectors[key]).inner_text().strip()
                            if selectors.get(key) and card.query_selector(selectors[key]) else "")
    get_attr = lambda key, attr: (card.query_selector(selectors[key]).get_attribute(attr)
                                  if selectors.get(key) and card.query_selector(selectors[key]) else None)
    title = _clean_title(get_text("title"))
    if not title:
        return None
    return {
        "source": "ebay",
        "title": title,
        "price": _parse_price(get_text("price")),
        "url": get_attr("url", "href"),
        "location": get_text("location"),
        "image": get_attr("image", "src"),
        "posted_at": None,
        "category": category,
    }

def _log_selector_counts(page, selectors: Dict[str, str]) -> None:
    print("\n--- Selector Validation ---")
    for key, sel in selectors.items():
        try:
            print(f"{key:15} {sel:45} → {len(page.query_selector_all(sel))} matches")
        except Exception as e:
            print(f"{key:15} {sel:45} → ERROR: {e}")

# --------------------------------------------------------------------
# Scraper
# --------------------------------------------------------------------
def scrape(*, category: str, limit: int = 30, headless: bool = True) -> List[Dict[str, Any]]:
    """Scrape eBay listings by category (supports .s-item and .s-card layouts)."""
    url = _build_url(category)
    log.info(f"[scrape] Launching browser to scrape: {url}")
    items: List[Dict[str, Any]] = []

    selectors = _get_selectors()
    with sync_playwright() as p:
        browser, context, page = _setup_browser(p, headless, proxy=None)
        try:
            _navigate_to_results(page, url)
            _log_selector_counts(page, selectors)

            cards = _get_cards(page, limit)
            for card in cards:
                item = _extract_card_data(card, selectors, category)
                if item:
                    items.append(item)

        except Exception as e:
            log.warning(f"[scrape] eBay scrape failed: {e}")
        finally:
            context.close()
            browser.close()

    _report_scrape_summary(items)
    return items

# --------------------------------------------------------------------
# Helpers to reduce cognitive complexity
# --------------------------------------------------------------------
def _get_selectors() -> Dict[str, str]:
    return {
        "title": "span[role='heading'], h3.s-item__title, .s-item__title, .s-card__title",
        "price": ".s-item__price, .s-card__price",
        "url": "a.s-item__link, a.su-link",
        "location": ".s-item__location, .s-item__dynamic .s-item__location.s-item__itemLocation",
        "image": "img.s-item__image-img, img.s-item__image, img.s-card__image",
    }

def _navigate_to_results(page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("li.s-item, li.s-card", timeout=30_000)

def _get_cards(page, limit: int):
    return page.query_selector_all("li.s-item, li.s-card")[:limit]

def _extract_card_data(card, selectors: Dict[str, str], category: str) -> Optional[Dict[str, Any]]:
    """Parse one eBay listing card and skip ad/promotional tiles."""
    def get_text(key: str) -> str:
        el = card.query_selector(selectors[key])
        return el.inner_text().strip() if el else ""

    def get_attr(key: str, attr: str) -> Optional[str]:
        el = card.query_selector(selectors[key])
        return el.get_attribute(attr) if el else None

    title = get_text("title")
    if not title or "shop on ebay" in title.lower() or "learn more" in title.lower():
        return None

    # Clean eBay-specific noise
    title = re.sub(r"\bOpens in a new window or tab\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s{2,}", " ", title).strip()

    raw_price = get_text("price").replace("$", "").replace(",", "")
    price_val = next((float(p) for p in raw_price.split() if p.replace('.', '', 1).isdigit()), None)

    return {
        "source": "ebay",
        "title": title,
        "price": price_val,
        "url": get_attr("url", "href"),
        "location": get_text("location") or None,
        "image": get_attr("image", "src"),
        "posted_at": None,
        "category": category,
    }

def _report_scrape_summary(items: List[Dict[str, Any]]) -> None:
    if not items:
        log.error("[warn] No listings found — page layout may have changed.")
    else:
        log.info(f"[done] Scraped {len(items)} items from eBay.")

def _save_updated_selectors(site: str, selectors: Dict[str, str]) -> None:
    """Persist updated selector map after successful auto-fallback."""
    cfg_path = Path(__file__).resolve().parents[3] / "config" / "selectors" / f"{site}.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(selectors, indent=2), encoding="utf-8")
    log.info(f"[save] Updated selectors → {cfg_path}")

# --------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------
if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    results = scrape(category=args.category, limit=args.limit, headless=args.headless)
    safe_name = args.category.replace(" ", "_")
    output_path = OUTPUT_DIR / f"ebay_{safe_name}_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log.info(f"[done] wrote {output_path} ({len(results)} items)")
