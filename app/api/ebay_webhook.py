from __future__ import annotations
import os
import hashlib
from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv

from app.utils.logger import log


# Load environment variables from .env if present
load_dotenv(override=False)

router = APIRouter(prefix="/ebay", tags=["ebay"])


def _absolute_endpoint_from_request(request: Request) -> str:
    url = request.url
    # Build scheme://host[:port]/path without query
    host = url.hostname
    port = f":{url.port}" if url.port and url.port not in (80, 443) else ""
    return f"{url.scheme}://{host}{port}{url.path}"


@router.get("/account_deletion")
async def ebay_account_deletion_challenge(
    request: Request,
    challenge_code: str | None = None,
    challengeCode: str | None = None,
    format: str | None = None,
):
    """
    eBay expects challengeResponse = sha256(challengeCode + verificationToken + endpointUrl).
    endpointUrl must exactly match the value configured in eBay settings.
    """
    code = challenge_code or challengeCode
    if not code:
        return JSONResponse({"challengeResponse": None, "message": "Provide ?challenge_code=..."}, status_code=400)

    verification_token = os.getenv("EBAY_VERIFICATION_TOKEN", "").strip()
    # Prefer EBAY_REDIRECT_URI if present; else derive from the incoming request
    configured_endpoint_env = os.getenv("EBAY_REDIRECT_URI", "").strip()
    configured_endpoint = configured_endpoint_env or _absolute_endpoint_from_request(request)

    hasher = hashlib.sha256()
    hasher.update(code.encode("utf-8"))
    hasher.update(verification_token.encode("utf-8"))
    hasher.update(configured_endpoint.encode("utf-8"))
    digest = hasher.hexdigest()

    log.info(
        "[eBay] Challenge received; digest ready | endpoint=%s env_set=%s",
        configured_endpoint,
        bool(configured_endpoint_env),
    )

    # eBay often expects plain text response body. Support JSON for manual testing via ?format=json
    if (format or "").lower() == "json":
        return {"challengeResponse": digest}
    return PlainTextResponse(content=digest, status_code=200)


def _header_token(request: Request) -> str | None:
    """Read verification token from common header names."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    return (
        headers.get("x-ebay-verification-token")
        or headers.get("verificationtoken")
        or headers.get("x-ebay-token")
    )


@router.post("/account_deletion")
async def ebay_account_deletion_webhook(request: Request) -> Dict[str, Any]:
    """
    Receives eBay account deletion events and validates via EBAY_VERIFICATION_TOKEN.
    Logs payload and returns acknowledgement.
    """
    secret = os.getenv("EBAY_VERIFICATION_TOKEN", "").strip()
    if secret:
        token = _header_token(request)
        if token != secret:
            log.warning("[eBay] Invalid verification token header: %s", token)
            raise HTTPException(status_code=401, detail="Invalid verification token")

    try:
        payload = await request.json()
    except Exception:
        payload = {"_raw": (await request.body()).decode("utf-8", errors="replace")}

    log.info("[eBay] Account deletion event received: %s", payload)
    return {"ok": True}
