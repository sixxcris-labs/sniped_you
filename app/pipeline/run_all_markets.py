from __future__ import annotations
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict

from app.utils.logger import log
from app.utils.metrics import Metrics
from app.utils.dedupe import dedupe_listings

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
OUTPUT_DIR = "data/output"
SCRAPERS = {
    "ebay": "app.scrapers.sites.ebay_scraper",
    "craigslist": "app.scrapers.sites.craigslist_scraper",
    "facebook": "app.scrapers.sites.fb_marketplace_sniper",
}

metrics = Metrics()


# --------------------------------------------------------------------
# SCRAPER RUNNERS
# --------------------------------------------------------------------
def run_scraper(site: str, category: str, limit: int = 30) -> Path:
    """Run a scraper module for a given marketplace (isolated subprocess)."""
    category_safe = category.replace(" ", "_")
    out_path = Path(OUTPUT_DIR) / f"{site}_{category_safe}_results.json"
    log.info(f"[scrape] Running {site} scraper for '{category}'...")

    cmd = ["python", "-m", SCRAPERS[site], "--category", category, "--limit", str(limit)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.warning(f"[warn] {site} scraper exited with code {result.returncode}")
        log.warning(result.stderr.strip() or "No stderr output.")

    if not out_path.exists():
        raise FileNotFoundError(f"Scraper output missing: {out_path}")

    log.info(f"[scrape] {site} output → {out_path}")
    return out_path


# --------------------------------------------------------------------
# FACEBOOK REFINEMENT STAGE
# --------------------------------------------------------------------
def refine_facebook(raw_path: Path) -> Path:
    """Normalize and deduplicate Facebook scraped listings."""
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen = set()
    refined = []

    for item in data:
        title = (item.get("title") or item.get("name") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)

        price = item.get("price") or 0
        url = item.get("url")
        category = item.get("category") or "unknown"

        words = title.lower().split()
        brand = next((w for w in words if w in {"nike", "trek", "apple", "samsung"}), None)
        model = " ".join(words[:3])

        # Clearer conditional extraction (fix for SonarQube S3358)
        if category != "unknown":
            category_hint = category
        elif "bike" in words:
            category_hint = "bike"
        else:
            category_hint = "unknown"

        refined.append({
            "brand": brand,
            "model": model,
            "category": category_hint,
            "price": price,
            "confidence": 0.75,
            "source": "facebook",
            "url": url,
        })

    out_path = Path(OUTPUT_DIR) / f"facebook_refined_{raw_path.stem}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(refined, f, indent=2)

    log.info(f"[refine] Facebook unified refine complete → {out_path}")
    return out_path


# --------------------------------------------------------------------
# PROFITABILITY SCORER WRAPPER
# --------------------------------------------------------------------
def run_scorer(input_path: Path):
    """Run profitability scorer on the given input file."""
    log.info(f"[score] Scoring {input_path.name}...")
    cmd = ["python", "app/pipeline/profitability_scorer.py", "--input", str(input_path)]
    subprocess.run(cmd, check=False)


# --------------------------------------------------------------------
# MAIN ORCHESTRATION
# --------------------------------------------------------------------
def main(category: str, limit: int = 30):
    """Run the full unified marketplace pipeline."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results: List[Path] = []

    metrics.start_timer("pipeline_run")

    # 1. Run scrapers (each in its own browser session)
    for site in SCRAPERS:
        try:
            raw_path = run_scraper(site, category, limit)
            if site == "facebook":
                refined = refine_facebook(raw_path)
                results.append(refined)
            else:
                results.append(raw_path)
        except Exception as e:
            log.warning(f"[warn] Skipping {site}: {e}")

    # 2. Deduplicate merged listings (optional)
    try:
        dedupe_listings(OUTPUT_DIR)
    except Exception:
        pass

    # 3. Run profitability scoring
    for path in results:
        run_scorer(path)

    metrics.stop_timer("pipeline_run")
    metrics.report()

    merged_path = Path(OUTPUT_DIR) / "all_scored_listings.json"
    log.info(f"[done] Unified scoring complete → {merged_path}")


# --------------------------------------------------------------------
# CLI Entrypoint
# --------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="Product category (e.g. bikes, electronics)")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    main(args.category, args.limit)
