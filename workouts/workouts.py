from fastapi import APIRouter, Request
from workouts.data import (create_workout, delete_workout)
from workouts.notion import (fetch_notion_page, parse_workout)

router = APIRouter()
@router.post("/added")
async def workout_added(req: Request):
    page_id = (await req.json())["page_id"]
    page = fetch_notion_page(page_id)
    notion_id, date, metadata = parse_workout(page)
    create_workout(notion_id, date, metadata)
    return {"status": "ok"}

@router.post("/changed")
async def workout_changed(req: Request):
    page_id = (await req.json())["page_id"]
    notion_id = page_id.replace("-", "")
    delete_workout(notion_id)

    page = fetch_notion_page(page_id)
    notion_id, date, metadata = parse_workout(page)
    create_workout(notion_id, date, metadata)
    return {"status": "ok"}

@router.post("/deleted")
async def workout_deleted(req: Request):
    page_id = (await req.json())["page_id"]
    notion_id = page_id.replace("-", "")
    delete_workout(notion_id)
    return {"status": "ok"}