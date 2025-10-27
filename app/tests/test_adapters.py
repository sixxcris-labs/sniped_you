import math

from app.scoring.adapters import (
    CacheLayer,
    EbayAdapter,
    GoogleTrendsAdapter,
    RedditAdapter,
    KeepaAdapter,
)


def _in01(x: float) -> bool:
    return 0.0 <= float(x) <= 1.0 and not math.isnan(float(x))


def test_ebay_adapter_normalization():
    cache = CacheLayer(db_path=":memory:")

    class FakeEbay(EbayAdapter):
        def fetch_counts(self, query: str):
            # sold 30, active 10 -> strong sell-through
            return 30, 10, 110.0, 150.0

    adapter = FakeEbay(cache)
    m = adapter.compute_metrics("test")
    assert _in01(m["sell_through_rate"]) and _in01(m["resale_anchor"])  # bounded


def test_trends_adapter_trend_score_bounds():
    cache = CacheLayer(db_path=":memory:")

    class FakeTrends(GoogleTrendsAdapter):
        def fetch_series(self, keyword: str):
            return [10, 12, 15, 20, 28]  # clear uptrend

    t = FakeTrends(cache)
    s = t.trend_score("kw")
    assert _in01(s)


def test_reddit_adapter_bounds():
    cache = CacheLayer(db_path=":memory:")

    class FakeReddit(RedditAdapter):
        def fetch_weekly_mentions(self, keyword: str):
            return [1, 3, 3, 2, 5, 8]

    r = FakeReddit(cache)
    s = r.mention_score("bike")
    assert _in01(s)


def test_keepa_retail_anchor_bounds():
    cache = CacheLayer(db_path=":memory:")
    k = KeepaAdapter(cache)
    v = k.retail_anchor(avg_90d_price=70.0, msrp=100.0)
    assert _in01(v)
