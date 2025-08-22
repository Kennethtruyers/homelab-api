from fastapi import APIRouter, Request, Query
import requests
import workouts.notion as notion
import workouts.data as data
import os
from withings.data import upsert_tokens, get_tokens
router = APIRouter()

CLIENT_ID = os.getenv("WITHINGS_CLIENT_ID")
CLIENT_SECRET = os.getenv("WITHINGS_CLIENT_SECRET")
CALLBACK_URI = "https://homelab-api.kenneth-truyers.net/withings"
WBSAPI_URL = "https://wbsapi.withings.net"

@router.get("/")
async def get_token(code: str = Query(...), state: str = Query(...)):
    """
    Callback route when the user has accepted to share his data.
    Withings servers send back an authorization code and the original state.
    """

    payload = {
        "action": "requesttoken",
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URI,
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(f"{WBSAPI_URL}/v2/oauth2", json=payload, headers=headers)
    print(r.status_code)
    print(r.text)   
    r_token = r.json()
    access_token = r_token.get("access_token", "")
    refresh_token = r_token.get("refresh_token", "")
    expires_in = r_token.get("expires_in", "")

    upsert_tokens(access_token, refresh_token, expires_in)

    return r_token

    # # List devices of returned user
    # r_getdevice = requests.get(
    #     f"{WBSAPI_URL}/v2/user",
    #     headers=headers,
    #     params=payload
    # ).json()

    # return r_getdevice