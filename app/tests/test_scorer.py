from app.pipelines.profitability_scorer import score_one, Listing, DEFAULT_SCORING


def test_score_happy_path():
    ls = Listing(
        brand="Nike",
        model="Air Force 1",
        category="sneakers",
        price=120.0,
        confidence=0.85,
        market_anchor=200.0,
        raw={
            "brand": "Nike",
            "model": "Air Force 1",
            "category": "sneakers",
            "price": 120,
            "confidence": 0.85,
        },
    )
    out = score_one(ls, DEFAULT_SCORING)
    assert 0.0 <= out["flipScore"] <= 1.0
    assert out["profitMargin"] == 80.0
    assert out["valid"] is True


def test_invalid_price_filtered():
    ls = Listing(
        brand="Sony",
        model="XM5",
        category="electronics",
        price=5.0,
        confidence=0.9,
        market_anchor=200.0,
        raw={},
    )
    out = score_one(ls, DEFAULT_SCORING)
    assert out["valid"] is False


def test_no_anchor_uses_multiplier():
    ls = Listing(
        brand="Unknown",
        model=None,
        category=None,
        price=100.0,
        confidence=0.5,
        market_anchor=None,
        raw={},
    )
    out = score_one(ls, DEFAULT_SCORING)
    assert out["profitMargin"] == 20.0  # 1.2*100 - 100
