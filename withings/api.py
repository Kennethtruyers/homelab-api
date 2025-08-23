from fastapi import APIRouter, Request, Query
import requests
import workouts.notion as notion
import workouts.data as data
import os
from withings.data import upsert_tokens, get_tokens
import withings.withings_api  as withings_api
router = APIRouter()

@router.get("/")
async def get_token(code: str = Query(...), state: str = Query(...)):
    r_token = withings_api.get_token_from_code(code)
    
    userid = r_token["body"]["userid"]
    access_token = r_token["body"]["access_token"]
    refresh_token = r_token["body"]["refresh_token"]
    expires_in = r_token["body"]["expires_in"]

    upsert_tokens(access_token, refresh_token, expires_in, userid)

    return {"status": "ok"}

@router.post("/setup-notifications")
async def set_notifications(userid: str = Query(...)):
    withings_api.subscribe(userid, 1, "notify")
    withings_api.subscribe(userid, 54, "notify")

@router.post("/notify")
async def notify(request: Request):
    raw = await request.body()
    print(raw.decode())