from fastapi import APIRouter, Request
import workouts.notion as notion
import workouts.data as data

router = APIRouter()
@router.post("/")
def test():
    return {"status": "ok"}