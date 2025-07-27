# garmin_to_postgres.py
import os
import json
from garminconnect import Garmin
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from fastapi import APIRouter, Request
from garmin.data import insert_activity, insert_exercise

router = APIRouter()


@router.post("/fetch")
def fetchData(startDate, endDate):
    TOKEN_DIR = os.getenv("TOKEN_STORE_PATH", "/app/token-store")

    if not startDate or not endDate:
        raise Exception("startDate and endDate must be set")


    start = parse_date(startDate).date()
    end = parse_date(endDate).date()

    print(f"Fetching activities from {start} to {end}")

    garmin = Garmin()
    garmin.login(TOKEN_DIR)
    print("Logged into Garmin")

    activities = garmin.get_activities_by_date(start.isoformat(), end.isoformat())
    print(f"Fetched {len(activities)} activities")

    for a in activities:
        aid = str(a["activityId"])
        activityType = a.get("activityType", {}).get("typeKey")
        print(f"Inserting activity {aid} of type {activityType}")

        insert_activity(
            aid, 
                a.get("startTimeLocal"),
                a.get("activityType", {}).get("typeKey"),
                a.get("duration"),
                a.get("distance"),
                a.get("calories"),
                a.get("averageHR"),
                a.get("maxHR"),
                a.get("steps"),
                a.get("elevationGain"),
                json.dumps(a)
        )

        if activityType == "strength_training":
            try:
                print(f"Fetching strength sets for activity {aid}")
                detail = garmin.get_activity_exercise_sets(aid)
                sets = detail.get("exerciseSets", [])
                for idx, s in enumerate(sets):
                    if s.get("setType") != "ACTIVE":
                        continue

                    best_exercise = max(s.get("exercises", []), key=lambda e: e.get("probability", 0), default={})
                    category = best_exercise.get("category")
                    name = best_exercise.get("name") or best_exercise.get("category")

                    start_time = parse_date(s.get("startTime"))
                    duration = s.get("duration", 0.0)
                    end_time = start_time + timedelta(seconds=duration)
                    reps = s.get("repetitionCount") or 0
                    weight = s.get("weight")

                    # Derived effort time (in minutes)
                    rep_tempo = 3.0  # average seconds per rep
                    effort_time_min = (reps * rep_tempo) / 60.0

                    # MET scaling by reps
                    met = max(4.0, 6.5 - 0.1 * reps)

                    # Scaled kcal output (per kg bodyweight)
                    per_kg_kcal = effort_time_min * met * 0.0175

                    # Get rest duration from the next REST set
                    rest_duration = None
                    for next_set in sets[idx+1:]:
                        if next_set.get("setType") == "REST":
                            rest_duration = next_set.get("duration")
                            break

                    exercise_id = f"{aid}-{idx}"
                    insert_exercise(aid, exercise_id, category, name, duration, reps, weight, start_time, end_time, rest_duration, per_kg_kcal)
            except Exception as e:
                print(f"Warning: failed to fetch or insert strength sets for {aid}: {e}")

    print("Done inserting new activities and strength sets.")
