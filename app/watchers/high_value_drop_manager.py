import asyncio
import os
from typing import Any, Dict, List
from app.models import insert_listing
from app.config_loader import get as load_cfg
from app.utils.logger import log
from app.utils.metrics import Metrics
from app.notifiers.webhook_dispatcher import dispatch_webhook
from app.pipelines.profitability_scorer import score_one, DEFAULT_SCORING


class HighValueDropManager:
    """Fetches, scores, stores, and alerts on high-value product drops."""

    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings = settings
        self.metrics = Metrics()
        self.scoring_cfg = {
            **DEFAULT_SCORING,
            **load_cfg("SNIPER_SCORING_CFG", "config/scoring.yaml"),
        }
        self.alert_threshold = float(settings.get("alert_threshold", 0.7))
        self.webhook_cfg: Dict[str, Any] = settings.get("webhook", {})
        self.drop_sites: List[str] = settings.get("drop_sites", [])

    def fetch_new(self) -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        for site in self.drop_sites:
            log.info(f"[drops] Checking site: {site}")
            listings.append(
                {
                    "source": site,
                    "title": "Sample High-Value Drop",
                    "brand": "Nike",
                    "model": "Travis Scott Reverse Mocha",
                    "price": 150.0,
                    "url": f"https://{site}/drops/sample",
                }
            )
        return listings

    async def run_once(self) -> int:
        """Fetch, score, save, and alert once."""
        listings = self.fetch_new()
        if not listings:
            log.info("[high_value_drop_manager] No new drops found.")
            return 0

        alerts = 0
        scored = [
            await asyncio.to_thread(score_one, listing, self.scoring_cfg)
            for listing in listings
        ]

        for item in scored:
            flip_score = float(item.get("flipScore", 0.0))
            self.metrics.incr("listings_seen")

            # --- DB insert ---
            row = {
                "id": item.get("id") or str(hash(item.get("url"))),
                "title": item.get("title"),
                "price": float(item.get("price") or 0),
                "permalink": item.get("url"),
                "score": flip_score,
            }
            insert_listing(row)
            # -----------------

            if flip_score >= self.alert_threshold:
                if dispatch_webhook("drop.alert", item, self.webhook_cfg):
                    self.metrics.incr("alerts_sent")
                    alerts += 1

        log.info(
            "[high_value_drop_manager] alerts_sent=%d listings_seen=%d",
            alerts,
            self.metrics.counters.get("listings_seen", 0),
        )
        return alerts

    async def run_loop(self, interval: int = 60) -> None:
        """Continuously poll for new high-value drops."""
        log.info("[high_value_drop_manager] polling every %ss", interval)
        while True:
            try:
                await self.run_once()
            except Exception as e:
                log.exception("Watcher loop error: %s", e)
            await asyncio.sleep(interval)


async def _main() -> None:
    settings = load_cfg("SNIPER_SETTINGS", "config/settings.yaml") or {}
    interval = int(os.environ.get("WATCHER_INTERVAL_SECS", "60"))
    mode = os.environ.get("WATCHER_MODE", "once").lower()

    mgr = HighValueDropManager(settings)
    if mode == "loop":
        await mgr.run_loop(interval)
    else:
        await mgr.run_once()


if __name__ == "__main__":
    asyncio.run(_main())
