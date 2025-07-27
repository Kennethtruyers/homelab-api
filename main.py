
from garmin.data import init as init_garmin
from workouts.data import init as init_workouts
from fastapi import FastAPI
from workouts.workouts import router as workouts_router
from workouts.sync import router as sync_router
from nutrition.api import router as nutrition_router
from tanita.api import router as tanita_router
from garmin.api import router as garmin_router


print("Initializing tables")
init_garmin()
init_workouts()

print("Starting API")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.myfitnesspal.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

''' Workouts '''
app.include_router(workouts_router, prefix="/workouts/workouts", tags=["workouts"])
app.include_router(exercises_router, prefix="/workouts/exercises", tags=["exercises"])
app.include_router(sync_router, prefix="/workouts/", tags=["sync"])

''' Nutrition '''
app.include_router(nutrition_router, prefix="/nutrition/", tags=["nutrition"])

''' Tanita '''
app.include_router(tanita_router, prefix="/tanita/", tags=["tanita"])

''' Garmin '''
app.include_router(garmin_router, prefix="/garmin/", tags=["garmin"])



@app.get("/ping")
async def ping():
    return {"status": "ok"}