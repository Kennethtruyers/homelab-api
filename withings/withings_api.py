import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import HTTPException
from withings.data import get_tokens, upsert_tokens

CLIENT_ID = os.getenv("WITHINGS_CLIENT_ID")
CLIENT_SECRET = os.getenv("WITHINGS_CLIENT_SECRET")
CALLBACK_URI = "https://homelab-api.kenneth-truyers.net/withings"
WBSAPI_URL = "https://wbsapi.withings.net"
REFRESH_GRACE_SECONDS = 30  # refresh if expiring within next 30s

def subscribe(user_id : str, appli : int, url: str):
    querystring = f"action=subscribe&callbackUrl=https://homelab-api.kenneth-truyers.net/withings/{url}&appli={appli}"
    token = get_access_token(user_id)
    send_request(f"{CALLBACK_URI}/notify?{querystring}")

def get_token_from_code(code: str) -> Dict[str, Any]:
    payload = {
        "action": "requesttoken",
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URI,
    }
    return send_request("v2/oauth2", payload)


def get_token_from_refresh_token(refresh_token: str) -> Dict[str, Any]:
    payload = {
        "action": "refreshtoken",
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    return send_request("v2/oauth2", payload)


def send_request(url: str, payload: Dict[str, Any], token: str = None) -> Dict[str, Any]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.post(f"{WBSAPI_URL}/{url}", json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != 0 or "body" not in data:
        raise RuntimeError(f"Withings API error: {data}")
    return data


def _to_utc(dt) -> datetime:
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00")).astimezone(tz=None).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow() - timedelta(seconds=1)


def get_access_token(user_id: str) -> str:
    row = get_tokens(user_id)
    if not row:
        raise HTTPException(status_code=500, detail="Withings tokens not found in database")

    access_token = row.get("access_token")
    refresh_token = row.get("refresh_token")
    expires_at = _to_utc(row.get("expires_at"))

    now_utc = datetime.utcnow()
    needs_refresh = (expires_at is None) or (expires_at <= now_utc + timedelta(seconds=REFRESH_GRACE_SECONDS))

    if not needs_refresh and access_token:
        return access_token

    if not refresh_token:
        raise HTTPException(status_code=500, detail="Refresh token missing; re-link Withings account")

    try:
        body = get_token_from_refresh_token(refresh_token)["body"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Withings refresh failed: {e}")

    new_access = body["access_token"]
    new_refresh = body["refresh_token"]
    expires_in = body["expires_in"]

    # Persist new tokens
    upsert_tokens(new_access, new_refresh, expires_in, user_id)

    return new_access
