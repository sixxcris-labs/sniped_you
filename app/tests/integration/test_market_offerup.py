import time
from pathlib import Path

import pytest

try:
    from scrapers.offerup import Listing, extract_offerup
except ModuleNotFoundError:  # pragma: no cover
    from app.scraper.marketplaces.offerup import Listing, extract_offerup


def _sample_uri(name: str) -> str:
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    return (fixture_dir / name).resolve().as_uri()


@pytest.mark.integration
def test_offerup_extraction_smoke() -> None:
    url = _sample_uri("offerup_sample.html")
    started = time.time()
    results = extract_offerup(url, headless=True, max_items=1)
    assert isinstance(results, list)
    assert results, "Expected at least one listing"
    listing = results[0]
    assert isinstance(listing, Listing)
    assert listing.market == "offerup"
    assert listing.url.startswith("https://offerup.com/")
    assert isinstance(listing.title, str) and listing.title.strip()
    assert started - 60 <= listing.timestamp <= time.time()
    assert listing.price is None or (
        isinstance(listing.price, str) and listing.price.strip()
    )
