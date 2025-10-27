import os
import json
import logging
import hmac
import hashlib
import base64
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment
# ------------------------------------------------------------
load_dotenv()

EBAY_VERIFICATION_TOKEN = os.getenv("EBAY_VERIFICATION_TOKEN", "").strip()
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "").strip()
EBAY_REDIRECT_URI = os.getenv("EBAY_REDIRECT_URI", "").strip()
EBAY_SIGNING_KEY = os.getenv("EBAY_SIGNING_KEY", "").strip()

# ------------------------------------------------------------
# Logger setup
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ebay_webhook")

# ------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------
app = FastAPI(title="eBay Webhook Verification")

# ------------------------------------------------------------
# Signature verification (optional)
# ------------------------------------------------------------
def verify_signature(payload: dict, signature_header: str) -> bool:
    if not EBAY_SIGNING_KEY:
        return True  # skip if not configured

    try:
        computed_signature = base64.b64encode(
            hmac.new(
                EBAY_SIGNING_KEY.encode("utf-8"),
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        return hmac.compare_digest(computed_signature, signature_header)
    except Exception as e:
        logger.error(f"[eBay] Signature verification failed: {e}")
        return False

# ------------------------------------------------------------
# Route: Challenge verification
# ------------------------------------------------------------
@app.get("/ebay/account_deletion")
async def verify_ebay(request: Request, format: str | None = None):
    code = request.query_params.get("challenge_code") or request.query_params.get("challengeCode")
    if not code:
        logger.warning("[eBay] Missing challenge_code in verification request")
        return JSONResponse({"challengeResponse": None, "message": "Provide ?challenge_code=..."}, status_code=400)

    # Compute challengeResponse = sha256(code + EBAY_VERIFICATION_TOKEN + EBAY_REDIRECT_URI)
    token = EBAY_VERIFICATION_TOKEN
    endpoint = EBAY_REDIRECT_URI
    digest = hashlib.sha256((code + token + endpoint).encode("utf-8")).hexdigest()
    logger.info("[eBay] Challenge received; responding with sha256 digest")

    if (format or "").lower() == "json":
        return {"challengeResponse": digest}
    return PlainTextResponse(content=digest, status_code=200)

# ------------------------------------------------------------
# Route: Account deletion webhook
# ------------------------------------------------------------
@app.post("/ebay/account_deletion")
async def ebay_account_deletion(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[eBay Webhook] Invalid JSON payload: {e}")
        return Response(content="Invalid JSON", status_code=400)

    signature_header = request.headers.get("x-ebay-signature", "")
    if not verify_signature(payload, signature_header):
        return Response(content="Invalid signature", status_code=412)

    user_id = payload.get("userId") or payload.get("user_id", "unknown")
    reason = payload.get("reason", "unspecified")
    timestamp = payload.get("timestamp", "unknown")

    logger.info(f"[eBay] Account deletion received: user={user_id}, reason={reason}, timestamp={timestamp}")

    # Simulate data cleanup
    deleted = await remove_user_data(user_id)
    if deleted:
        logger.info(f"[Cleanup] Completed user deletion for {user_id}")
    else:
        logger.warning(f"[Cleanup] Could not delete data for {user_id}")

    return Response(content="OK", status_code=200)

# ------------------------------------------------------------
# Cleanup simulation
# ------------------------------------------------------------
def remove_user_data(user_id: str) -> bool:
    try:
        path = f"data/users/{user_id}.json"
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"[Cleanup] Deleted file for {user_id}")
        return True
    except Exception as e:
        logger.error(f"[Cleanup] Error removing user data: {e}")
        return False
