from connections import get_connection

def init():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS garmin_activities (
                    activity_id TEXT PRIMARY KEY,
                    start_time TIMESTAMPTZ,
                    activity_type TEXT,
                    duration_seconds INT,
                    distance_meters FLOAT,
                    calories FLOAT,
                    average_hr INT,
                    max_hr INT,
                    steps INT,
                    elevation_gain FLOAT,
                    json_payload JSONB
                )
                """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS garmin_strength_exercises (
                    activity_id TEXT,
                    exercise_id TEXT,
                    category TEXT,
                    exercise_name TEXT,
                    variation TEXT,
                    duration FLOAT,
                    repetitions INT,
                    weight FLOAT,
                    rir INTEGER,
                    notes TEXT,
                    start_time TIMESTAMPTZ,
                    end_time TIMESTAMPTZ,
                    rest_duration FLOAT,
                    per_kg_kcal DOUBLE PRECISION,
                    estimated_1rm DOUBLE PRECISION
                        GENERATED ALWAYS AS (
                        CASE 
                            WHEN weight IS NOT NULL AND repetitions IS NOT NULL 
                            THEN weight * (1 + (repetitions::DOUBLE PRECISION / 30.0))
                            ELSE NULL
                        END
                        ) STORED,
                    PRIMARY KEY (activity_id, exercise_id)
                )
                """)

def insert_activity(id, startTime, activityType,duration, distance, calories, averageHR, maxHR, steps, elevationGain, metadata):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM garmin_activities WHERE activity_id = %s", (id,))
            if cur.fetchone():
                return false  # already exists

            cur.execute(
            """
            INSERT INTO garmin_activities (
                activity_id, start_time, activity_type, duration_seconds,
                distance_meters, calories, average_hr, max_hr, steps,
                elevation_gain, json_payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (id, startTime, activityType,duration, distance, calories, averageHR, maxHR, steps, elevationGain, metadata))
            return true

def insert_exercise(aid, exercise_id, category, name, duration, reps, weight, start_time, end_time, rest_duration, per_kg_kcal):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO garmin_strength_exercises (
                    activity_id, exercise_id, category, exercise_name, duration,
                    repetitions, weight, start_time, end_time, rest_duration, per_kg_kcal
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (activity_id, exercise_id) DO NOTHING
                """,
                (aid, exercise_id, category, name, duration, reps, weight, start_time, end_time, rest_duration, per_kg_kcal))