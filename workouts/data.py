
from datetime import datetime
from connections import get_connection

def init():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    notion_id TEXT PRIMARY KEY,
                    date DATE,
                    personal_notes TEXT,
                    coach_notes TEXT,
                    metadata JSONB
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    workout_notion_id TEXT REFERENCES workouts(notion_id),
                    name TEXT,
                    variation TEXT,
                    sets INT,
                    reps INT, 
                    weight numeric(10,2),
                    rir INT,
                    notes TEXT,
                    estimated_1rm numeric(10,2) GENERATED ALWAYS AS (weight * (1 + reps::NUMERIC / 30)) STORED,
                    metadata JSONB,
                    PRIMARY KEY (workout_notion_id, name)
                );
            """)

def create_workout(notion_id, date, personal_notes, coach_notes, metadata):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO workouts (notion_id, date, personal_notes, coach_notes, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (notion_id) DO UPDATE SET
                  date = EXCLUDED.date,
                  personal_notes = EXCLUDED.personal_notes,
                  coach_notes = EXCLUDED.coach_notes,
                  metadata = EXCLUDED.metadata
            """, (notion_id, date, personal_notes, coach_notes, metadata))

def delete_workout(notion_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM exercises WHERE workout_notion_id = %s", (notion_id,))
            cur.execute("DELETE FROM workouts WHERE notion_id = %s", (notion_id,))

def create_exercise(workout_notion_id, name, variation, sets, reps, weight, rir, notes, metadata):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO exercises (workout_notion_id, name, variation, sets, reps, weight, rir, notes, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workout_notion_id, name) DO UPDATE SET
                  variation = EXCLUDED.variation,
                  sets = EXCLUDED.sets,
                  reps = EXCLUDED.reps,
                  weight = EXCLUDED.weight,
                  rir = EXCLUDED.rir,
                  notes = EXCLUDED.notes,
                  metadata = EXCLUDED.metadata
            """, (workout_notion_id, name, variation, sets, reps, weight, rir, notes, metadata))

def delete_exercise(workout_notion_id, name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM exercises WHERE workout_notion_id = %s AND name = %s
            """, (workout_notion_id, name))

def delete_all_workouts_and_exercises():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM exercises")
            cur.execute("DELETE FROM workouts")
