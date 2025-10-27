import base64
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SUBSCRIPTION_URL = "https://api.ebay.com/developer/notification/v1/subscription"


def env_or_exit(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"Missing required env: {key}")
        sys.exit(2)
    return val


def get_access_token(client_id: str, client_secret: str, scope: Optional[str]) -> str:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
    }
    if scope:
        data["scope"] = scope

    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    if resp.status_code != 200:
        print("Failed to obtain access token:")
        print(resp.status_code, resp.text)
        sys.exit(3)
    token = resp.json().get("access_token")
    if not token:
        print("No access_token in response")
        sys.exit(3)
    return token


def register_webhook(access_token: str, endpoint: str, verification_token: str) -> None:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "topic": "MARKETPLACE_ACCOUNT_DELETION",
        "endpoint": endpoint,
        "verificationToken": verification_token,
    }
    resp = requests.post(SUBSCRIPTION_URL, headers=headers, json=body, timeout=30)
    if resp.status_code in (200, 201):
        print("Webhook registration: SUCCESS")
        print(resp.json())
    else:
        print("Webhook registration: FAILED")
        print(resp.status_code, resp.text)
        sys.exit(4)


def main() -> None:
    load_dotenv(override=False)
    endpoint = env_or_exit("EBAY_REDIRECT_URI")
    verification_token = env_or_exit("EBAY_VERIFICATION_TOKEN")
    scope = os.getenv("EBAY_OAUTH_SCOPE", "https://api.ebay.com/oauth/api_scope")
    # Prefer a pre-existing OAuth token if provided
    token = os.getenv("EBAY_AUTH_TOKEN")
    if not token:
        client_id = env_or_exit("EBAY_CLIENT_ID")
        client_secret = env_or_exit("EBAY_CLIENT_SECRET")
        token = get_access_token(client_id, client_secret, scope)
    register_webhook(token, endpoint, verification_token)


if __name__ == "__main__":
    main()
