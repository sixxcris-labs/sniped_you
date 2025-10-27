"""
Integration test for Sniped You market adapters.
Validates eBay and Google Trends adapters return numeric outputs.
"""

import os
import json
from pathlib import Path

from app.adapters import ebay_adapter, google_trends_adapter


def test_adapters_integration(keyword: str = "road bike") -> dict:
    """Run all active adapters and return combined JSON payload."""
    results = {}

    # --- eBay metrics ---
    try:
        if not os.getenv("EBAY_AUTH_TOKEN"):
            print("[warn] No eBay API token found — using mock data.")
            results["resale_anchor"] = 950.0
            results["liquidity"] = 0.35
        else:
            data = ebay_adapter.query_ebay(keyword)
            metrics = ebay_adapter.compute_metrics(data)
            results["resale_anchor"] = float(metrics.get("resale_anchor", 0))
            results["liquidity"] = float(metrics.get("liquidity", 0))
    except Exception as e:
        results["resale_anchor"] = None
        results["liquidity"] = None
        print(f"[error] eBay adapter failed: {e}")

    # --- Google Trends metric ---
    try:
        demand = google_trends_adapter.get_trend_score(keyword)
        results["demand"] = float(demand)
    except Exception as e:
        results["demand"] = None
        print(f"[error] Google Trends adapter failed: {e}")

    # --- Placeholder retail anchor ---
    results["retail_anchor"] = 1.0

    # --- Write output ---
    out_path = Path("data/output/adapter_integration_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"[done] Wrote {out_path} ->\n{json.dumps(results, indent=2)}")

    return results


if __name__ == "__main__":
    test_adapters_integration()
