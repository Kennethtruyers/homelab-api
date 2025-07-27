from fastapi import APIRouter, Request
import notion


router = APIRouter()
@router.post("/resync")
async def resync():
    notion.delete_all_workouts_and_exercises()

    workouts = notion.fetch_all_workouts()
    for page in workouts:
        notion_id, date, personal_notes, coach_notes, metadata = notion.parse_workout(page)
        notion.create_workout(notion_id, date, personal_notes, coach_notes, metadata)

    exercises = notion.fetch_all_exercises()
    for page in exercises:
        parsed = notion.parse_exercise(page)
        if parsed:
            workout_notion_id, exercise_name, variation, sets, reps, weight, rir, notes, metadata = parsed
            notion.create_exercise(workout_notion_id, exercise_name, variation, sets, reps, weight, rir, notes, metadata)

    return {"status": "resync complete"}


