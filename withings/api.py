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

@router.api_route("/notify", methods=["POST", "HEAD"])
async def notify(request: Request):
    if request.method == "HEAD":
        # Withings (and other webhook providers) sometimes ping with HEAD
        return Response(status_code=200)

    form = await request.form()
    data = dict(form)  # converts MultiDict into a plain dict
    print(data)        # {'userid': '44454286', 'startdate': '1755933497', ...}
    
    return {"status": "ok"}