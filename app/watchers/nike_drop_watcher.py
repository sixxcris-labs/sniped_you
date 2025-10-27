import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.utils.hashing import calc_hash
from app.utils.webhooks import dispatch_webhook


class NikeDropWatcher:
    source = "nike.com"
    poll_interval_secs = 300
    tracked_urls: List[str] = [
        "https://www.nike.com/t/air-jordan-1-mid-mens-shoes-X5pM6h"
    ]
    state_path = Path("data/state/nike_last_snapshot.json")

    async def fetch_snapshot(self) -> Dict[str, Any]:
        products: List[Dict[str, Any]] = []
        for url in self.tracked_urls:
            try:
                product_data = await url
                products.append(product_data)
            except Exception as exc:  # keep stub simple for now
                return {"error": f"Failed to fetch data for {url}: {exc}"}
        return {
            "products": products,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_change(self, snapshot: Dict[str, Any]) -> bool:
        new_hash = calc_hash(snapshot)
        old_hash: Optional[str] = None

        if self.state_path.exists():
            try:
                old_data = json.loads(self.state_path.read_text(encoding="utf-8"))
                old_hash = calc_hash(old_data)
            except json.JSONDecodeError:
                old_hash = None

        if new_hash != old_hash:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            return True
        return False

    async def handle_update(self, snapshot: Dict[str, Any]) -> None:
        await dispatch_webhook(snapshot)

    async def run_once(self) -> None:
        print(
            f"[{self.source}] Checking product pages at "
            f"{datetime.now(timezone.utc).isoformat()}..."
        )
        snapshot = await self.fetch_snapshot()

        if "error" in snapshot:
            print(f"[{self.source}] Error: {snapshot['error']}")
            return

        if await self.detect_change(snapshot):
            print(f"[{self.source}] Change detected -> dispatching webhook.")
            await self.handle_update(snapshot)
        else:
            print(f"[{self.source}] No change detected.")

    async def watch_loop(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception as exc:
                print(f"[{self.source}] Exception during watch loop: {exc}")
            await asyncio.sleep(self.poll_interval_secs)


if __name__ == "__main__":
    asyncio.run(NikeDropWatcher().watch_loop())
