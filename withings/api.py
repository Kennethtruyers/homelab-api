from fastapi import APIRouter, Request, Query
import requests
import workouts.notion as notion
import workouts.data as data
import os
from withings.data import upsert_tokens, get_tokens
import withings.withings_api  as withings_api
from urllib.parse import parse_qs

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

    raw = await request.body()
    parsed = parse_qs(raw.decode())
    data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    print(data)

    response = withings_api.get_measure(data["userid"], [
        1,   # Weight (kg)
        5,   # Fat Free Mass (kg)
        6,   # Fat Ratio (%)
        8,   # Fat Mass Weight (kg)
        11,  # Heart Pulse (bpm, standing HR from scale)
        76,  # Muscle Mass (kg)
        77,  # Hydration / Total Body Water (kg)
        88,  # Bone Mass (kg)
        91,  # Pulse Wave Velocity (m/s)
        130, # Atrial fibrillation result (ECG)
        135, # QRS interval duration (ECG)
        136, # PR interval duration (ECG)
        137, # QT interval duration (ECG)
        138, # Corrected QT interval duration (ECG)
        155, # Vascular age (derived from PWV)
        167, # Nerve Health Score / Conductance (feet electrodes)
        168, # Extracellular Water (kg)
        169, # Intracellular Water (kg)
        170, # Visceral Fat (index, unitless)
        174, # Segmental Fat Mass (arms, legs, trunk)
        175, # Segmental Muscle Mass (arms, legs, trunk)
        196, # Electrodermal Activity (feet)
        226, # Basal Metabolic Rate (BMR)
        229, # Electrochemical Skin Conductance
    ], data["startdate"], data["enddate"])

    print(response)

    return {"status": "ok"}