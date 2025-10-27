import time
from pathlib import Path

import pytest

try:  # prefer local sandbox modules while allowing copied tests to run in app package
    from scrapers.ebay import Listing, extract_ebay
except ModuleNotFoundError:  # pragma: no cover - executed in main repo test run
    from app.scraper.marketplaces.ebay import Listing, extract_ebay


def _sample_uri(name: str) -> str:
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    return (fixture_dir / name).resolve().as_uri()


@pytest.mark.integration
def test_ebay_extraction_smoke() -> None:
    url = _sample_uri("ebay_sample.html")
    started = time.time()
    results = extract_ebay(url, headless=True, max_items=1)
    assert isinstance(results, list)
    assert results, "Expected at least one listing"
    listing = results[0]
    assert isinstance(listing, Listing)
    assert listing.market == "ebay"
    assert listing.url.startswith("https://www.ebay.com/itm/")
    assert isinstance(listing.title, str) and listing.title.strip()
    assert started - 60 <= listing.timestamp <= time.time()
    assert listing.price is None or (
        isinstance(listing.price, str) and listing.price.strip()
    )
