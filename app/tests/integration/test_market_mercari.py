import time
from pathlib import Path

import pytest

try:
    from scrapers.mercari import Listing, extract_mercari
except ModuleNotFoundError:  # pragma: no cover
    from app.scraper.marketplaces.mercari import Listing, extract_mercari


def _sample_uri(name: str) -> str:
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    return (fixture_dir / name).resolve().as_uri()


@pytest.mark.integration
def test_mercari_extraction_smoke() -> None:
    url = _sample_uri("mercari_sample.html")
    started = time.time()
    results = extract_mercari(url, headless=True, max_items=1)
    assert isinstance(results, list)
    assert results, "Expected at least one listing"
    listing = results[0]
    assert isinstance(listing, Listing)
    assert listing.market == "mercari"
    assert listing.url.startswith("https://www.mercari.com/")
    assert isinstance(listing.title, str) and listing.title.strip()
    assert started - 60 <= listing.timestamp <= time.time()
    assert listing.price is None or (
        isinstance(listing.price, str) and listing.price.strip()
    )
