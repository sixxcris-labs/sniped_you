from __future__ import annotations
import json
import re
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse, quote_plus
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from app.utils.logger import log
from app.utils.proxies import get_proxies, rotate
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import pytesseract

# ------------------------------------------------------------
# Paths and constants
# ------------------------------------------------------------
ROOT = Path(".")
URLS_FILE = ROOT / "urls.txt"
STORAGE_PATH = ROOT / "data/browser_storage/fb_storage_state.json"
OUTPUT_DIR = ROOT / "data/output"
SCREENSHOT_DIR = ROOT / "data/screenshots"

for d in (OUTPUT_DIR, SCREENSHOT_DIR):
    d.mkdir(parents=True, exist_ok=True)

PRICE_REGEX = re.compile(r"\$[\d,]+(?:\.\d{2})?")

try:
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
except Exception:
    RESAMPLE_BICUBIC = Image.BICUBIC

# ------------------------------------------------------------
# OCR helpers
# ------------------------------------------------------------
def _preprocess(img: Image.Image, upscale: int = 2) -> Image.Image:
    img = img.convert("L")
    w, h = img.size
    img = img.resize((int(w * upscale), int(h * upscale)), resample=RESAMPLE_BICUBIC)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3)).filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    return img

def _ocr_try_configs(img: Image.Image) -> str:
    cfgs = [
        "--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.$ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "--psm 7 --oem 3",
        "--psm 11 --oem 3",
    ]
    best = ""
    for cfg in cfgs:
        try:
            txt = pytesseract.image_to_string(img, config=cfg)
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt and len(txt) > len(best):
                best = txt
        except Exception:
            continue
    return best

def ocr_title_price_from_image(image_path: Path) -> Tuple[str, str]:
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            text_area = img.crop((int(w * 0.03), int(h * 0.55), int(w * 0.97), int(h * 0.92)))
            processed = _preprocess(text_area, upscale=3)
            raw_text = _ocr_try_configs(processed)
            price_match = PRICE_REGEX.search(raw_text)
            price = price_match.group(0) if price_match else ""
            title_text = PRICE_REGEX.sub("", raw_text)
            title_text = re.sub(r"\s+", " ", title_text).strip()
            return (title_text if len(title_text) >= 3 else ""), price
    except Exception as e:
        log.error(f"[OCR error] {e}")
        return "", ""

# ------------------------------------------------------------
# Listing extraction
# ------------------------------------------------------------
def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_") or quote_plus(url)
    return re.sub(r"[^A-Za-z0-9_.-]", "_", slug)[:140]

def extract_single_listing(page, url: str) -> Path:
    ts = int(time.time())
    slug = slug_from_url(url) or f"fb_listing_{ts}"
    screenshot_path = SCREENSHOT_DIR / f"{slug}_{ts}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        page.screenshot(path=str(screenshot_path), full_page=False)
    title, price = ocr_title_price_from_image(screenshot_path)
    data = {
        "url": url,
        "title": title or None,
        "price": price or None,
        "screenshot_path": str(screenshot_path.resolve()),
        "scrape_time": ts,
    }
    out_file = OUTPUT_DIR / f"{slug}_{ts}.json"
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"[saved] {out_file.name}")
    return out_file
def extract_multiple_cards(page, url: str) -> Path:
    """
    Extract multiple marketplace card listings (title, price, link) from a search results page.
    Returns path to JSON array file.
    """
    ts = int(time.time())
    slug = slug_from_url(url) or f"fb_cards_{ts}"
    out_path = OUTPUT_DIR / f"{slug}_{ts}.json"
    listings = []

    try:
        # Select multiple cards by their CSS selector
        card_elements = page.query_selector_all("a[href*='/marketplace/item/']")
        for el in card_elements:
            href = el.get_attribute("href")
            title = el.inner_text() or ""
            price_match = PRICE_REGEX.search(title)
            price = price_match.group(0) if price_match else ""
            clean_title = PRICE_REGEX.sub("", title).strip()
            listings.append(
                {
                    "url": f"https://www.facebook.com{href}" if href else url,
                    "title": clean_title or None,
                    "price": price or None,
                    "scrape_time": ts,
                }
            )
        out_path.write_text(json.dumps(listings, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(f"[saved] {len(listings)} card screenshots → {out_path.name}")
    except Exception as e:
        log.error(f"[extract_multiple_cards] {e}")
    return out_path

def process_url(context, url: str) -> Optional[Path]:
    """Open URL and return the path to an output JSON with listings."""
    page = context.new_page()
    page.set_default_timeout(30000)
    try:
        log.info(f"[open] {url}")
        page.goto(url, timeout=60000)
        time.sleep(3)
        # Trigger lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
        time.sleep(1.5)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

        if "/marketplace/item/" in url:
            return extract_single_listing(page, url)          # → JSON object
        else:
            return extract_multiple_cards(page, url)          # → JSON array
    except PWTimeout:
        log.warning(f"[timeout] Loading: {url}")
        return None
    except Exception as exc:
        log.error(f"[error] {url}: {exc}")
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


def _merge_outputs(paths: List[Path]) -> List[Dict[str, Any]]:
    """Merge a mix of array/object JSON files into a single list."""
    merged: List[Dict[str, Any]] = []
    for p in paths:
        if not p or not p.exists():
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(obj, list):
                merged.extend(obj)
            elif isinstance(obj, dict):
                merged.append(obj)
        except Exception as e:
            log.warning(f"[merge] Skipping {p.name}: {e}")
    return merged


def _validate_env() -> List[str]:
    """Validate prerequisites and return non-empty URL list."""
    if not URLS_FILE.exists():
        raise SystemExit("Create urls.txt with one Facebook URL per line.")
    if not STORAGE_PATH.exists():
        raise SystemExit(f"Missing {STORAGE_PATH}. Run save_fb_storage_state.py first.")
    urls = [u.strip() for u in URLS_FILE.read_text(encoding="utf-8").splitlines() if u.strip()]
    if not urls:
        raise SystemExit("urls.txt is empty.")
    return urls


def _scrape_with_proxy(proxy: Optional[str], urls: List[str], limit: int, headless: bool) -> List[Path]:
    """Launch browser with proxy and process given URLs."""
    out_paths: List[Path] = []
    log.info(f"[proxy] Using proxy: {proxy or 'none'}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            proxy={"server": proxy} if proxy else None,
            args=["--start-maximized"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            storage_state=str(STORAGE_PATH),
        )
        try:
            for url in urls[:limit]:
                if path := process_url(context, url):
                    out_paths.append(path)
                time.sleep(1.5)
        finally:
            context.close()
            browser.close()
    return out_paths


def _finalize_output(category: str, out_paths: List[Path]) -> None:
    """Merge all per-URL outputs into one refined file."""
    refined = _merge_outputs(out_paths)
    category_safe = category.replace(" ", "_")
    final_path = OUTPUT_DIR / f"facebook_refined_{category_safe}_results.json"
    final_path.write_text(json.dumps(refined, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"[refine] wrote {final_path} ({len(refined)} items)")
    log.info("✅ Full OCR extraction complete.")


def main(category: str = "facebook pokemon cards", limit: int = 10, headless: bool = False) -> None:
    """Scrape FB pages, OCR cards, and write a unified refined file."""
    urls = _validate_env()
    proxies = rotate(get_proxies()) or [None]
    out_paths: List[Path] = []

    for proxy in proxies:
        try:
            out_paths = _scrape_with_proxy(proxy, urls, limit, headless)
            if out_paths:
                break
        except Exception as e:
            log.warning(f"[proxy] Proxy {proxy or 'none'} failed: {e}")
            continue

    _finalize_output(category, out_paths)

