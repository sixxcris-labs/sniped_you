from fastapi import FastAPI, Request
import hashlib, os

app = FastAPI()

# Use same env names as the main app
VERIFICATION_TOKEN = os.getenv("EBAY_VERIFICATION_TOKEN", os.getenv("EBAY_VERIFY_TOKEN", "")).strip()
ENDPOINT_URL = os.getenv("EBAY_REDIRECT_URI", os.getenv("EBAY_DELETE_ENDPOINT", "https://yourdomain.com/ebay/account_deletion")).strip()

@app.get("/ebay/account_deletion")
async def verify(request: Request):
    code = request.query_params.get("challenge_code", "")
    if not code:
        return {"challengeResponse": ""}
    h = hashlib.sha256()
    h.update(code.encode("utf-8"))
    h.update(VERIFICATION_TOKEN.encode("utf-8"))
    h.update(ENDPOINT_URL.encode("utf-8"))
    return {"challengeResponse": h.hexdigest()}
