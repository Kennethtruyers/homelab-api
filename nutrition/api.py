from fastapi import APIRouter, Request
from datetime import datetime
import pytz
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from connections import get_influx_client
import os

router = APIRouter()
load_dotenv()



MEAL_TIMES = {
    "breakfast": "06:00:00",
    "morning": "19:00:00",
    "lunch": "12:00:00",
    "afternoon": "15:00:00",
    "dinner": "19:00:00",
    "snacks": "21:00:00"
}

def get_timestamp(date_str, time_str):
    return datetime.fromisoformat(f"{date_str}T{time_str}").replace(tzinfo=pytz.UTC).isoformat()

@router.post("/day")
async def day(request: Request):
    client = get_influx_client("fitness")
    payload = await request.json()
    date = payload.get("date")
    items = payload.get("items", [])
    totals = payload.get("totals", {})

    if not date or not items:
        return {"error": "Missing required fields"}

    # Time range for deletion
    start_ts = f"{date}T00:00:00Z"
    end_ts = f"{date}T23:59:59Z"

    for measurement in ["mfp_item", "mfp_meal", "mfp_day", "mfp_entry"]:
        client.query(f"DELETE FROM {measurement} WHERE time >= '{start_ts}' AND time <= '{end_ts}'")

    # InfluxDB points
    influx_points = []

    # 1. Item-level entries (mfp_item)
    for item in items:
        meal = item.get("meal", "unknown").lower()
        meal_time = MEAL_TIMES.get(meal, "10:00:00")  # fallback
        timestamp = get_timestamp(date, meal_time)

        influx_points.append({
            "measurement": "mfp_item",
            "tags": {
                "meal": meal,
                "name": item.get("name", "unknown")
            },
            "time": timestamp,
            "fields": {
                "calories": float(item.get("calories", 0)),
                "carbs": float(item.get("carbs", 0)),
                "fat": float(item.get("fat", 0)),
                "protein": float(item.get("protein", 0)),
                "sugar": float(item.get("sugar", 0))
            }
        })

    # 2. Meal-level aggregates (mfp_meal)
    meal_sums = {}
    for item in items:
        meal = item.get("meal", "unknown").lower()
        meal_sums.setdefault(meal, {
            "calories": 0, "carbs": 0, "fat": 0, "protein": 0, "sugar": 0
        })
        for field in meal_sums[meal]:
            meal_sums[meal][field] += float(item.get(field, 0))

    for meal, fields in meal_sums.items():
        timestamp = get_timestamp(date, MEAL_TIMES.get(meal, "10:00:00"))
        influx_points.append({
            "measurement": "mfp_meal",
            "tags": {
                "meal": meal
            },
            "time": timestamp,
            "fields": fields
        })

    # 3. Day-level total (mfp_day)
    if totals:
        influx_points.append({
            "measurement": "mfp_day",
            "tags": {},
            "time": get_timestamp(date, "23:59:00"),
            "fields": {
                "calories": float(totals.get("calories", 0)),
                "carbs": float(totals.get("carbs", 0)),
                "fat": float(totals.get("fat", 0)),
                "protein": float(totals.get("protein", 0)),
                "sugar": float(totals.get("sugar", 0))
            }
        })

    if influx_points:
        client.write_points(influx_points)

    return {"status": "ok", "inserted": len(influx_points)}