from __future__ import annotations
import time
from fastapi import APIRouter
from app.watchers.high_value_drop_manager import WatcherManager
from app.config_loader import get as load_cfg
from app.utils.logger import log

router = APIRouter(prefix="/watchers", tags=["watchers"])

@router.post("/run-once")
async def run_once_endpoint():
    """Run all configured watchers once and return summary metrics."""
    settings = load_cfg("SNIPER_SETTINGS", "config/settings.yaml") or {}
    mgr = WatcherManager(settings)

    t0 = time.perf_counter()
    alerts = await mgr.run_once()
    duration = time.perf_counter() - t0

    result = {
        "alerts_sent": alerts,
        "listings_seen": mgr.metrics.counters.get("listings_seen", 0),
        "duration_secs": round(duration, 3),
    }

    log.info("[api] /watchers/run-once -> %s", result)
    return result
