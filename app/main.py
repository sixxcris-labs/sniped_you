from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.watchers_router import router as watchers_router
from app.api import ebay_webhook
from app.obs.structured_log import setup_logging
from app.metrics.collector import get_daily_metrics
from app.utils.logger import init_logger
from app.utils.deps import verify_dependencies

setup_logging()
log = init_logger("snipped_you")
app = FastAPI()
app.include_router(watchers_router)
app.include_router(ebay_webhook.router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ready")
def ready():
    return {"ok": True}


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/metrics")
def metrics():
    return get_daily_metrics()


log.info("App started successfully")
