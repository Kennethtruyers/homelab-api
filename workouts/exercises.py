from fastapi import APIRouter, Request
from data import (create_exercise, delete_exercise)
from notion import (fetch_notion_page, parse_exercise)

router = APIRouter()

@router.post("/added")
async def exercise_added(req: Request):
    page_id = (await req.json())["page_id"]
    page = fetch_notion_page(page_id)
    result = parse_exercise(page)
    if result:
        workout_id, name, meta = result
        create_exercise(workout_id, name, meta)
    return {"status": "ok"}

@router.post("/changed")
async def exercise_changed(req: Request):
    page_id = (await req.json())["page_id"]
    page = fetch_notion_page(page_id)
    result = parse_exercise(page)
    if result:
        workout_id, name, meta = result
        delete_exercise(workout_id, name)
        create_exercise(workout_id, name, meta)
    return {"status": "ok"}

@app.post("/deleted")
async def exercise_deleted(req: Request):
    body = await req.json()
    workout_id = body.get("workout_id")
    name = body.get("name")
    if workout_id and name:
        delete_exercise(workout_id.replace("-", ""), name)
    return {"status": "ok"}