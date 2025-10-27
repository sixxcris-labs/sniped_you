from __future__ import annotations
import os
from typing import Any, Dict, List
from playwright.sync_api import sync_playwright


# NOTE:
# Nextdoorâ€™s marketplace generally requires login.
# Set a valid session cookie in the environment variable `NEXTDOOR_COOKIE`
# to enable scraping. Without it, the scraper returns an empty list.


def scrape(*, category: str, limit: int, headless: bool) -> List[Dict[str, Any]]:
    """
    Scrape Nextdoor marketplace listings (requires authentication).

    Args:
        category: Listing category name (used only for tagging results).
        limit: Maximum number of items to retrieve.
        headless: Whether to run the browser in headless mode.

    Returns:
        A list of listing dictionaries.
    """
    cookie = os.getenv("NEXTDOOR_COOKIE")
    if not cookie:
        print("[nextdoor] NEXTDOOR_COOKIE not set; skipping scrape.")
        return []

    base_url = "https://nextdoor.com/for_sale_and_free/"
    items: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122 Safari/537.36"
            ),
            locale="en-US",
        )

        # Apply login cookie
        try:
            context.add_cookies(
                [
                    {
                        "name": "nd_session",
                        "value": cookie,
                        "domain": "nextdoor.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                    }
                ]
            )
        except Exception as e:
            print(f"[nextdoor] Failed to add cookie: {e}")

        page = context.new_page()
        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)

        # Selectors may need updates after inspecting logged-in DOM
        cards = page.query_selector_all("[data-test='marketplace-card'], article")

        for card in cards[:limit]:
            title_el = card.query_selector("h3, h2, [data-test='title']")
            price_el = card.query_selector("[data-test='price'], .price")
            url_el = card.query_selector("a[href]")
            img_el = card.query_selector("img")

            title = title_el.inner_text().strip() if title_el else None
            href = url_el.get_attribute("href") if url_el else None
            price_txt = (
                (price_el.inner_text().strip() if price_el else "")
                .replace("$", "")
                .replace(",", "")
            )

            try:
                price = float(price_txt)
            except ValueError:
                price = None

            items.append(
                {
                    "source": "nextdoor",
                    "title": title,
                    "price": price,
                    "url": href,
                    "location": None,
                    "image": img_el.get_attribute("src") if img_el else None,
                    "posted_at": None,
                    "category": category,
                }
            )

        context.close()
        browser.close()

    return items
