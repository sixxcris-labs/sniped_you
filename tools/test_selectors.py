import sys
from playwright.sync_api import sync_playwright
from app.scrapers.sites.craigslist_scraper import load_selectors as load_craig
from app.scrapers.sites.ebay_scraper import load_selectors as load_ebay

# --------------------------------------------------------------------
# Fixed search URLs — bikes (consistent layout for both sites)
# --------------------------------------------------------------------
SITES = {
    "ebay": {
        "url": "https://www.ebay.com/sch/i.html?_nkw=bikes&_sop=10&_ipg=60",
        "loader": load_ebay,
    },
    "craigslist": {
        "url": "https://houston.craigslist.org/search/bia?sort=date",
        "loader": load_craig,
    },
}

# --------------------------------------------------------------------
# Test each site’s selectors
# --------------------------------------------------------------------
def test_site(site: str, url: str, loader):
    print(f"\n--- Testing {site.upper()} ---")
    selectors = loader(site)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print(f"[debug] Navigating to {url}...")
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        for name, sels in selectors.items():
            for sel in sels:
                try:
                    count = len(page.query_selector_all(sel))
                    print(f"{name:15} {sel:60} → {count} matches")
                except Exception as e:
                    print(f"{name:15} {sel:60} → ERROR: {e}")

        browser.close()

# --------------------------------------------------------------------
# Run both eBay and Craigslist
# --------------------------------------------------------------------
if __name__ == "__main__":
    for site, cfg in SITES.items():
        test_site(site, cfg["url"], cfg["loader"])
