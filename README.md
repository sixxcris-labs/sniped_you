snipped_you
High-signal marketplace watcher and scoring service with FastAPI, Playwright scraping, OCR, and webhook notifications.

Overview

- FastAPI service exposes health, readiness, and watcher endpoints.
- Scrapers and pipelines enrich listings, score signals, and send signed webhooks.
- Docker + Compose for local dev; tests with pytest.

Requirements

- Python 3.11+
- Node dependencies handled by Playwright image if using Docker; otherwise install Playwright locally.
- Optional: Docker and Docker Compose

Quick Start (no Docker)

- Create virtualenv: `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\Activate`)
- Install deps: `pip install -r requirements.txt`
- Set up configs and secrets:
  - Copy `config/api_keys.example.yaml` to `config/api_keys.yaml` and fill values.
  - Copy `config/webhook_secrets.example.yaml` to `config/webhook_secrets.yaml` and set a strong `hmac_secret`.
  - Create `.env` at project root for environment variables (see “Environment Variables”).
- Run API: `uvicorn app.main:app --reload`
- Visit: `http://localhost:8000/health`

Docker

- Build and run: `docker compose up --build`
- Uses a Postgres `db` service matching defaults in `db.py`.
- Mounts the project in the `api` container for quick iteration.

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

snipped_you
├─ app
│ ├─ adapters
│ │ ├─ adapters
│ │ ├─ cache_layer.py
│ │ ├─ ebay_adapter.py
│ │ ├─ google_trends_adapter.py
│ │ ├─ google_trends_enricher.py
│ │ ├─ keepa_adapter.py
│ │ ├─ reddit_adapter.py
│ │ └─ **init**.py
│ ├─ api
│ │ └─ watchers_router.py
│ ├─ config_loader.py
│ ├─ main.py
│ ├─ metrics
│ │ ├─ collector.py
│ │ └─ **init**.py
│ ├─ models.py
│ ├─ notifiers
│ │ ├─ discord.py
│ │ ├─ webhook_dispatcher.py
│ │ └─ **init**.py
│ ├─ obs
│ │ ├─ structured_log.py
│ │ └─ **init**.py
│ ├─ ocr
│ │ ├─ easyocr_engine.py
│ │ ├─ paddleocr_wrapper.py
│ │ └─ **init**.py
│ ├─ parsers
│ │ ├─ listing_parser.py
│ │ └─ **init**.py
│ ├─ pipelines
│ │ ├─ extract_ocr.py
│ │ ├─ postprocess_refined.py
│ │ ├─ profitability_scorer.py
│ │ ├─ refine_llm.py
│ │ └─ unified_market_pipeline.py
│ ├─ scoring
│ │ ├─ heuristics.py
│ │ ├─ rarity_utils.py
│ │ ├─ scoring_model.py
│ │ ├─ scoring_utils.py
│ │ └─ **init**.py
│ ├─ scrapers
│ │ ├─ market_scraper.py
│ │ ├─ sites
│ │ │ ├─ craigslist_scraper.py
│ │ │ ├─ ebay_scraper.py
│ │ │ ├─ fb_marketplace_sniper.py
│ │ │ └─ nextdoor_scraper.py
│ │ └─ **init**.py
│ ├─ scripts
│ │ └─ **init**.py
│ ├─ storage
│ │ ├─ scoring_logger.py
│ │ └─ storage.py
│ ├─ tests
│ │ ├─ integration
│ │ │ ├─ fixtures
│ │ │ │ ├─ craigslist_sample.html
│ │ │ │ ├─ ebay_sample.html
│ │ │ │ ├─ mercari_sample.html
│ │ │ │ └─ offerup_sample.html
│ │ │ ├─ test_market_craigslist.py
│ │ │ ├─ test_market_ebay.py
│ │ │ ├─ test_market_mercari.py
│ │ │ ├─ test_market_offerup.py
│ │ │ └─ test_notifier_integration.py
│ │ ├─ test_adapters.py
│ │ ├─ test_adapters_integration.py
│ │ ├─ test_discovery.py
│ │ ├─ test_playwright_client.py
│ │ ├─ test_scorer.py
│ │ ├─ test_scorer_pipeline.py
│ │ └─ test_webhook_dispatcher.py
│ ├─ utils
│ │ ├─ custom_dataloader.py
│ │ ├─ dedupe.py
│ │ ├─ deps.py
│ │ ├─ hashing.py
│ │ ├─ logger.py
│ │ ├─ metrics.py
│ │ ├─ nike_scraper.py
│ │ ├─ proxies.py
│ │ ├─ webhooks.py
│ │ └─ **init**.py
│ └─ watchers
│ ├─ high_value_drop_manager.py
│ ├─ nike_drop_watcher.py
│ ├─ nike_watcher_playwright.py
│ └─ **init**.py
├─ config
│ ├─ api_keys.example.yaml
│ ├─ scoring.yaml
│ ├─ selectors
│ │ └─ craigslist.json
│ └─ webhook_secrets.example.yaml
├─ db.py
├─ docker-compose.yml
├─ Dockerfile
├─ LICENSE
├─ README.md
├─ requirements.txt
├─ scripts
│ ├─ analyze_ocr_results.ps1
│ ├─ clean_env_loader.ps1
│ ├─ clean_ocr_encoding.ps1
│ ├─ get_ebay_token.ps1
│ ├─ run_backtest.ps1
│ ├─ run_notify.ps1
│ ├─ run_ocr_benchmark.ps1
│ ├─ run_score.ps1
│ ├─ run_scrape.ps1
│ ├─ run_trend_enrichment.ps1
│ ├─ setup_env.ps1
│ └─ test_google_apis.ps1
├─ tools
│ ├─ local_receiver.py
│ ├─ ocr_benchmark.py
│ ├─ selector_logger.py
│ └─ test_selectors.py
├─ urls.txt
└─ VAR_appmain

```

```
