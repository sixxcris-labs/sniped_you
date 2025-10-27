import os

import json
import hmac
import time
import hashlib
import uuid
import requests
from typing import Any, Dict, Optional
from app.config_loader import get as load_cfg

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "SnipedYou/1.0",
}


def _get_secret() -> str:
    """Load webhook HMAC secret from env or config."""
    secret = os.environ.get("SNIPER_WEBHOOK_SECRET")
    if secret:
        return secret
    cfg = load_cfg("SNIPER_WEBHOOK_SECRET_CFG", "config/webhook_secrets.yaml")
    return cfg.get("hmac_secret") or "dev-secret"


def _sign(secret: str, timestamp: str, body: str) -> str:
    msg = f"{timestamp}.{body}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def send_webhook(
    event_name: str,
    payload: Dict[str, Any],
    url: Optional[str] = None,
    max_retries: int = 4,
) -> bool:
    """Send a signed webhook with retry and idempotency headers."""
    target_url = url or os.environ.get("SNIPER_WEBHOOK_URL")
    if not target_url:
        print("[webhook] No webhook URL configured")
        return False

    secret = _get_secret()
    body = json.dumps(payload, separators=(",", ":"))
    timestamp = str(int(time.time()))
    signature = _sign(secret, timestamp, body)
    idem_key = str(uuid.uuid4())

    headers = {
        **DEFAULT_HEADERS,
        "X-Sniper-Signature": signature,
        "X-Sniper-Timestamp": timestamp,
        "X-Sniper-Event": event_name,
        "X-Sniper-Idempotency-Key": idem_key,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(target_url, data=body, headers=headers, timeout=5)
            if 200 <= resp.status_code < 300:
                print(f"[webhook] Delivered → {target_url} ({resp.status_code})")
                return True
            print(f"[webhook] Attempt {attempt} failed ({resp.status_code})")
        except requests.RequestException as e:
            print(f"[webhook] Attempt {attempt} error: {e}")
        time.sleep(2 ** (attempt - 1))  # exponential backoff

    print("[webhook] Permanent failure after retries")
    return False


if __name__ == "__main__":
    # Quick manual test stub
    sample = {"flipScore": 0.92, "brand": "Nike", "price": 120}
    send_webhook("listing.scored", sample)
