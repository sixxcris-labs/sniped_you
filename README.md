     

An Autonomous AI system that scans marketplaces, extracts data, and ranks listings for profitable flips.

 Overview

Sniped You is an AI-powered deal discovery engine that combines OCR, LLM reasoning, and real-market scoring to identify undervalued listings across marketplaces like eBay, Craigslist, and Nike.

It integrates live APIs, local AI inference, and ethical scraping for end-to-end automation — from image to profit alert.

 System Architecture
Layer	Purpose
OCR Engine	Extracts text from images using EasyOCR → PaddleOCR-VL 0.9B (upgrade)
LLM Refiner	Parses unstructured OCR text into structured JSON fields
Scoring Model	Computes resale potential via multi-source API signals
Watcher Modules	Monitors live marketplaces (Nike, eBay, Craigslist, StockX)
Adapters	eBay, Google Trends, Reddit (Pushshift), Keepa integrations
Cache Layer	Local Redis/SQLite caching for API results
Notifier	Sends alerts when flip_score > threshold
Dashboard (Metabase)	Visualizes profit trends, ROI, and agent performance
⚙️ Scoring Model

Defined in /config/scoring_model.json:

{
  "sources": {
    "resale_anchor": { "api": "ebay.sell", "metric": "median_sold_price_last_30d", "weight": 0.4 },
    "liquidity": { "api": "ebay.active_vs_sold", "metric": "sell_through_rate", "weight": 0.2 },
    "demand": { "api": ["google.trends", "reddit.api"], "metric": "normalized_trend_slope", "weight": 0.25 },
    "retail_anchor": { "api": "keepa", "metric": "mean_bottom_quartile_90d", "weight": 0.15 }
  },
  "formulas": {
    "margin_ratio": "(resale_anchor - acquisition_price) / resale_anchor",
    "flip_score_base": "margin_ratio * liquidity",
    "flip_score": "sigmoid(flip_score_base * (0.8 + 0.4 * demand))"
  }
}

 
 Roadmap Summary
Phase 2 — Market Validation

Integrate eBay, Craigslist, and Google Trends APIs.

Produce validated JSON output with consistent pricing and timestamp fields.

Phase 3 — Analytics & Visualization

Add Metabase dashboards for flip trends, ROI, and demand correlation.

Phase 4 — Reinforcement Learning

Integrate Agent Lightning + ART to self-optimize scoring weights and OCR accuracy.

Phase 5 — Hybrid Agent Orchestration

Unify under Microsoft Agent Framework with contextual memory and tool-aware reasoning.

Phase 6 — SaaS Launch

Deploy web app with flip alerts, user dashboards, and subscription tiers ($29–$499/mo).

🔧 Installation (Local Dev)
git clone https://github.com/yourrepo/sniped_you.git
cd sniped_you
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt


For scraping and local inference:

docker compose up -d changedetection metabase redis

🧪 Running the Pipeline
python app/main.py --source ebay --category sneakers


Output: JSON with fields title, price, flip_score, and url.

🛠️ Upcoming Upgrades
Upgrade	Function	ROI
Mistral 7B (Quantized)	Local NLP inference + RAG	🔥 High
PaddleOCR-VL 0.9B	Structured OCR	🔥 High
Playwright + Stealth + Proxy Rotation	Bot-resistant scraping	🔥 High
AI Price Filter (Swoopa-style)	Undervalued deal detection	🔥 High
Ethical Compliance Toolkit	Rate-limit, TOS, and robots.txt adherence	⚖️ Medium
Environment Variables (.env)

- Common variables:
  - `DB_HOST=db`
  - `DB_PORT=5432`
  - `DB_NAME=sniped`
  - `DB_USER=sniper`
  - `DB_PASSWORD=sniped_pass`
  - `SNIPER_WEBHOOK_URL` (target URL for outgoing webhooks)
  - `SNIPER_WEBHOOK_SECRET` (optional; overrides file-based secret)
  - `SNIPER_WEBHOOK_SECRET_CFG` (optional; path to YAML secrets file; defaults to `config/webhook_secrets.yaml`)
  - `SNIPER_SETTINGS` (optional; path to settings YAML; defaults to `config/settings.yaml`)

Secrets and Configs

- Do not commit real secrets. `.gitignore` excludes:
  - `config/api_keys.yaml`
  - `config/webhook_secrets.yaml`
- Examples you should copy and edit:
  - `config/api_keys.example.yaml`
  - `config/webhook_secrets.example.yaml`

Running Tests

- Activate venv, then: `pytest -q`

Project Structure (selected)

- `app/main.py` – FastAPI entrypoint, routes, static files.
- `app/api/watchers.py` – API router for watcher runs.
- `app/utils/logger.py` – Consistent structured logging.
- `app/notifiers/webhook_dispatcher.py` – Signed webhook sender with retries.
- `app/...` – OCR, parsers, scoring, scrapers, pipelines.
- `config/` – Settings, selectors, and example secrets.
- `tests/` – Unit, integration, and smoke tests.

Notes

- Compose includes a Postgres service referenced by `db.py` defaults.
- For production, set strong secrets via environment variables and managed secret stores.
- Large data and logs are ignored by Git; see `.gitignore` for details.

