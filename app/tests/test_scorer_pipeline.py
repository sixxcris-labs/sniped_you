"""
Validation test for Sniped You Profitability Scorer.
Feeds adapter integration results into score_listing() and prints computed flip_score.
"""

import json
from pathlib import Path

from app.pipelines import profitability_scorer


def test_scorer_pipeline(
    input_path: str = "data/output/adapter_integration_results.json",
) -> dict:
    """Load adapter results and compute flip_score via profitability scorer."""
    in_path = Path(input_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Missing input JSON: {in_path}")

    data = json.loads(in_path.read_text())

    # Mock acquisition price (example: Craigslist price)
    acquisition_price = 600.0

    # Build payload compatible with Listing schema
    payload = {
        "title": "Generic Road Bike",
        "brand": "Generic",
        "model": "Road Bike",
        "price": acquisition_price,
        "metrics": data,
    }

    try:
        # Convert dict → Listing object
        listing_obj = profitability_scorer._as_listing(payload)

        # Score listing
        result = profitability_scorer.score_listing(
            listing_obj, profitability_scorer.DEFAULT_SCORING
        )
    except Exception as e:
        print(f"[error] Scorer failed: {e}")
        return {}

    # Write output
    out_path = Path("data/output/scoring_validation.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"[done] Wrote {out_path} ->\n{json.dumps(result, indent=2)}")
    from app.storage import scoring_logger

    scoring_logger.log_score(result)

    return result


if __name__ == "__main__":
    test_scorer_pipeline()
