import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import HTTPException
from withings.data import get_tokens, upsert_tokens
from urllib.parse import urlencode

CLIENT_ID = os.getenv("WITHINGS_CLIENT_ID")
CLIENT_SECRET = os.getenv("WITHINGS_CLIENT_SECRET")
CALLBACK_URI = "https://homelab-api.kenneth-truyers.net/withings"
WBSAPI_URL = "https://wbsapi.withings.net"
REFRESH_GRACE_SECONDS = 30  # refresh if expiring within next 30s

def subscribe(user_id : str, appli : int, url: str):
    send_authenticated_request("/notify", {
        "action": "subscribe",
        "callbackurl": f"https://homelab-api.kenneth-truyers.net/withings/{url}",
        "appli": appli
    }, user_id)

def get_measures(user_id, meastypes : list[int], startdate : int, enddate: int):
    params = {
        "action": "getmeas",
        "meastypes": ",".join(str(m) for m in meastypes),
        "category": 1
    }

    if startdate: 
        params["startdate"] = startdate

    if enddate: 
        params["enddate"] = enddate


    all_groups: List[Dict[str, Any]] = []
    more = 1
    offset = None

    while more:
        if offset is not None:
            params["offset"] = offset

        resp = send_authenticated_request("/measure", params, user_id)

        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 0 or "body" not in data:
            raise RuntimeError(f"Withings getmeas error: {data}")

        body = data["body"]
        groups = body.get("measuregrps", [])
        all_groups.extend(groups)

        more = int(body.get("more", 0))
        offset = body.get("offset")

        # Optional: stop if server doesn't return new groups (safety)
        if not more or not offset:
            break

    return parse_measure_groups(all_groups)

def parse_measure_groups(
    merged_body: Dict[str, Any],
    type_map: Dict[int, str] = TYPE_MAP
) -> List[Dict[str, Any]]:
    """
    Transforms measuregrps into a list of dicts:
    {
      "timestamp": 1755938448,
      "datetime": "2025-09-22T12:34:56Z",  # optional convenience field
      "timezone": "Europe/Madrid",
      "data": {
          "weight_kg": 70.9,
          "fat_mass_kg": 6.0,
          "fat_ratio_pct": 8.463,
          "fat_free_mass_kg": 64.9,
          ...
      }
    }
    """
    tz = merged_body.get("timezone")
    rows: List[Dict[str, Any]] = []

    for grp in merged_body.get("measuregrps", []):
        ts = grp.get("date")
        dt_str = (
            datetime.utcfromtimestamp(ts).isoformat() + "Z"
            if isinstance(ts, int)
            else None
        )

        for m in grp.get("measures", []):
            m_type = m.get("type")
            m_val = m.get("value")
            m_unit = m.get("unit", 0)
            if m_type is None or m_val is None:
                continue

            normalized = float(m_val) * (10.0 ** m_unit)
            field_name = type_map.get(m_type, f"type_{m_type}")

            row = {
                "datetime": dt_str,
                "timestamp": ts,
                "timezone": tz,
                "key": field_name,
                "value": normalized,
                "fm": m.get("fm", None),
                "algo": m.get("algo", None)
            }
            rows.append(row)

    return rows

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

def send_authenticated_request(url : str, query : Dict[str, Any], user_id: str):
    token = get_access_token(user_id)
    querystring = get_query_string(query)
    print(querystring)
    return send_request(f"{url}?{querystring}", None, token)

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

def get_query_string(payload : Dict[str, any]):
    if not payload:
        return ""
    return urlencode(payload)

def _normalize_value(value: int, unit_exp: int) -> float:
    """Withings measure normalization: value * 10**unit."""
    return float(value) * (10.0 ** unit_exp)


TYPE_MAP: Dict[int, str] = {
    1:   "weight_kg",
    5:   "fat_free_mass_kg",
    6:   "fat_ratio_pct",
    8:   "fat_mass_kg",
    11:  "heart_pulse_bpm",               # Standing HR from scale
    76:  "muscle_mass_kg",
    77:  "total_body_water_kg",
    88:  "bone_mass_kg",
    91:  "pulse_wave_velocity_mps",
    130: "ecg_atrial_fibrillation",
    135: "ecg_qrs_interval_ms",
    136: "ecg_pr_interval_ms",
    137: "ecg_qt_interval_ms",
    138: "ecg_qtc_interval_ms",
    155: "vascular_age",
    167: "nerve_health_score_conductance",  # feet electrodes
    168: "extracellular_water_kg",
    169: "intracellular_water_kg",
    170: "visceral_fat_index",
    174: "segmental_fat_mass",              # per-limb/trunk values
    175: "segmental_muscle_mass",           # per-limb/trunk values
    196: "electrodermal_activity_feet",
    226: "basal_metabolic_rate_kcal",
    229: "electrochemical_skin_conductance",
}