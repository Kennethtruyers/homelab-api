
from garmin.data import init as init_garmin
from workouts.data import init as init_workouts
from withings.data import init as init_withings
from cashflow.data import init as init_cashflow
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from workouts.workouts import router as workouts_router
from workouts.exercises import router as exercises_router
from workouts.sync import router as sync_router
from nutrition.api import router as nutrition_router
from tanita.api import router as tanita_router
from garmin.api import router as garmin_router
from withings.api import router as withings_router
from cashflow.api import router as cashflow_router


print("Initializing tables")
init_garmin()
init_workouts()
init_withings()
init_cashflow()

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
app.include_router(sync_router, prefix="/workouts", tags=["sync"])

''' Nutrition '''
app.include_router(nutrition_router, prefix="/nutrition", tags=["nutrition"])

''' Tanita '''
app.include_router(tanita_router, prefix="/tanita", tags=["tanita"])

''' Garmin '''
app.include_router(garmin_router, prefix="/garmin", tags=["garmin"])

''' Withings '''
app.include_router(withings_router, prefix="/withings", tags=["withings"])

''' CashFlow '''
app.include_router(cashflow_router, prefix="/cashflow", tags=["cashflow"])



@app.get("/ping")
async def ping():
    return {"status": "ok"}