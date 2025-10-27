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

