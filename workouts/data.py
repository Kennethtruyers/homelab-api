
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

            cur.execute(TAXONOMY_SQL)

            cur.execute(EXERCISES_META)

            cur.execute(TAXONOMY_MAPPING_SQL)

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



TAXONOMY_SQL = """
    CREATE TABLE IF NOT EXISTS muscle_taxonomy (
    path        text PRIMARY KEY,
    name        text NOT NULL,
    parent_path text
    );

    INSERT INTO muscle_taxonomy(path, name, parent_path) VALUES
    -- Regions
    ('upper','Upper Body',NULL),
    ('lower','Lower Body',NULL),
    ('core','Core',NULL),

    -- Upper body groups
    ('upper.chest','Chest','upper'),
    ('upper.back','Back','upper'),
    ('upper.shoulders','Shoulders','upper'),
    ('upper.arms','Arms','upper'),
    ('upper.forearms','Forearms','upper'),
    ('upper.traps','Trapezius','upper'),

    -- Lower body groups
    ('lower.quads','Quadriceps','lower'),
    ('lower.hamstrings','Hamstrings','lower'),
    ('lower.glutes','Glutes','lower'),
    ('lower.calves','Calves','lower'),
    ('lower.adductors','Adductors','lower'),

    -- Core groups
    ('core.abs','Abs','core'),
    ('core.obliques','Obliques','core'),
    ('core.spinal_erectors','Spinal Erectors','core'),
    ('core.hip_flexors','Hip Flexors','core'),

    -- Chest muscles
    ('upper.chest.pectoralis_major','Pectoralis Major','upper.chest'),
    ('upper.chest.pectoralis_major.clavicular','Pec Major (Clavicular)','upper.chest.pectoralis_major'),
    ('upper.chest.pectoralis_major.sternal','Pec Major (Sternal)','upper.chest.pectoralis_major'),
    ('upper.chest.pectoralis_major.abdominal','Pec Major (Abdominal)','upper.chest.pectoralis_major'),
    ('upper.chest.pectoralis_minor','Pectoralis Minor','upper.chest'),
    ('upper.chest.serratus_anterior','Serratus Anterior','upper.chest'),

    -- Back muscles
    ('upper.back.latissimus_dorsi','Latissimus Dorsi','upper.back'),
    ('upper.back.teres_major','Teres Major','upper.back'),
    ('upper.back.rhomboids','Rhomboids','upper.back'),
    ('upper.back.trapezius.upper','Trapezius Upper','upper.traps'),
    ('upper.back.trapezius.middle','Trapezius Middle','upper.traps'),
    ('upper.back.trapezius.lower','Trapezius Lower','upper.traps'),
    ('upper.back.levator_scapulae','Levator Scapulae','upper.back'),

    -- Shoulders
    ('upper.shoulders.deltoid','Deltoid','upper.shoulders'),
    ('upper.shoulders.deltoid.anterior','Anterior Deltoid','upper.shoulders.deltoid'),
    ('upper.shoulders.deltoid.lateral','Lateral Deltoid','upper.shoulders.deltoid'),
    ('upper.shoulders.deltoid.posterior','Posterior Deltoid','upper.shoulders.deltoid'),
    ('upper.shoulders.rotator_cuff.supraspinatus','Supraspinatus','upper.shoulders'),
    ('upper.shoulders.rotator_cuff.infraspinatus','Infraspinatus','upper.shoulders'),
    ('upper.shoulders.rotator_cuff.teres_minor','Teres Minor','upper.shoulders'),
    ('upper.shoulders.rotator_cuff.subscapularis','Subscapularis','upper.shoulders'),

    -- Arms
    ('upper.arms.biceps_brachii','Biceps Brachii','upper.arms'),
    ('upper.arms.biceps_brachii.short_head','Biceps Short Head','upper.arms.biceps_brachii'),
    ('upper.arms.biceps_brachii.long_head','Biceps Long Head','upper.arms.biceps_brachii'),
    ('upper.arms.brachialis','Brachialis','upper.arms'),
    ('upper.arms.brachioradialis','Brachioradialis','upper.arms'),
    ('upper.arms.triceps_brachii','Triceps Brachii','upper.arms'),
    ('upper.arms.triceps_brachii.long_head','Triceps Long Head','upper.arms.triceps_brachii'),
    ('upper.arms.triceps_brachii.lateral_head','Triceps Lateral Head','upper.arms.triceps_brachii'),
    ('upper.arms.triceps_brachii.medial_head','Triceps Medial Head','upper.arms.triceps_brachii'),

    -- Forearms
    ('upper.forearms.flexors','Wrist Flexors','upper.forearms'),
    ('upper.forearms.extensors','Wrist Extensors','upper.forearms'),
    ('upper.forearms.pronator_teres','Pronator Teres','upper.forearms'),
    ('upper.forearms.supinator','Supinator','upper.forearms'),

    -- Lower body: quads
    ('lower.quads.rectus_femoris','Rectus Femoris','lower.quads'),
    ('lower.quads.vastus_lateralis','Vastus Lateralis','lower.quads'),
    ('lower.quads.vastus_medialis','Vastus Medialis','lower.quads'),
    ('lower.quads.vastus_intermedius','Vastus Intermedius','lower.quads'),

    -- Lower body: hamstrings
    ('lower.hamstrings.biceps_femoris.long_head','Biceps Femoris Long Head','lower.hamstrings'),
    ('lower.hamstrings.biceps_femoris.short_head','Biceps Femoris Short Head','lower.hamstrings'),
    ('lower.hamstrings.semitendinosus','Semitendinosus','lower.hamstrings'),
    ('lower.hamstrings.semimembranosus','Semimembranosus','lower.hamstrings'),

    -- Lower body: glutes
    ('lower.glutes.gluteus_maximus','Gluteus Maximus','lower.glutes'),
    ('lower.glutes.gluteus_medius','Gluteus Medius','lower.glutes'),
    ('lower.glutes.gluteus_minimus','Gluteus Minimus','lower.glutes'),

    -- Lower body: calves
    ('lower.calves.gastrocnemius.medial','Gastrocnemius Medial','lower.calves'),
    ('lower.calves.gastrocnemius.lateral','Gastrocnemius Lateral','lower.calves'),
    ('lower.calves.soleus','Soleus','lower.calves'),

    -- Lower body: adductors
    ('lower.adductors.adductor_magnus','Adductor Magnus','lower.adductors'),
    ('lower.adductors.adductor_longus','Adductor Longus','lower.adductors'),
    ('lower.adductors.adductor_brevis','Adductor Brevis','lower.adductors'),
    ('lower.adductors.pectineus','Pectineus','lower.adductors'),
    ('lower.adductors.gracilis','Gracilis','lower.adductors'),

    -- Core
    ('core.abs.rectus_abdominis','Rectus Abdominis','core.abs'),
    ('core.obliques.external','External Obliques','core.obliques'),
    ('core.obliques.internal','Internal Obliques','core.obliques'),
    ('core.deep.transversus_abdominis','Transversus Abdominis','core'),
    ('core.deep.multifidus','Multifidus','core.spinal_erectors'),
    ('core.spinal_erectors.lumbar','Erector Spinae (Lumbar)','core.spinal_erectors'),
    ('core.spinal_erectors.thoracic','Erector Spinae (Thoracic)','core.spinal_erectors'),
    ('core.deep.quadratus_lumborum','Quadratus Lumborum','core')
    ON CONFLICT DO NOTHING;
    """

EXERCISES_META = """
    CREATE TABLE IF NOT EXISTS exercise_meta (
    name    text NOT NULL,
    variation text NOT NULL DEFAULT '',
    measurement_type text NOT NULL,   -- load | reps | hybrid | time | stretch
    variation_type   text NOT NULL,   -- minor | major
    PRIMARY KEY (name, variation)
    );

    INSERT INTO exercise_meta (name, variation, measurement_type, variation_type) VALUES
    -- Biceps / forearms
    ('Bicep Curl','Incline','load','major'),
    ('Bicep Curl','Hammer','load','major'),
    ('Bicep Curl','Standing','load','minor'),
    ('Bicep Curl','Hammer Incline','load','major'),
    ('Bicep Curl','Zottman','load','major'),
    ('Bicep Curl','','load','major'),
    ('Reverse Curl','', 'load','minor'),
    ('Reverse wrist curl','', 'load','minor'),
    ('Seated Forearm Curl','', 'load','minor'),

    -- Rows / pulls
    ('One-Arm Row','','load','minor'),
    ('One-Arm Row','Flared','load','minor'),
    ('One-Arm Row','Pronated','load','minor'),
    ('One-Arm Row','Normal','load','minor'),
    ('One-Arm Row','Flared Pronated','load','minor'),
    ('Rear Delt Row','', 'load','minor'),
    ('Lat Pullover','', 'load','minor'),
    ('Scapular row','', 'reps','minor'),

    -- Shoulders
    ('Lateral Raise','', 'load','minor'),
    ('Front Raise','', 'load','minor'),
    ('Reverse Fly','', 'load','minor'),
    ('Shrug','', 'load','minor'),
    ('Prone Y Raises','', 'load','minor'),
    ('Shoulder Press','', 'load','minor'),
    ('Lying Shoulder Internal Rotation','', 'load','minor'),
    ('Lying Shoulder External Rotation','', 'load','minor'),
    ('Wall/Floor Glides','', 'stretch','minor'),

    -- Chest
    ('Bench Press','','load','major'),
    ('Bench Press','Flat','load','major'),
    ('Bench Press','Incline','load','major'),
    ('Floor Press','', 'load','major'),
    ('Chest Fly','', 'load','minor'),
    ('Chest Fly','Flat','load','major'),

    -- Triceps
    ('Kickbacks','', 'load','minor'),
    ('Db Kickbacks','', 'load','minor'),
    ('Bench Dips','', 'hybrid','minor'),
    ('Bench Dips','Feet Elevated','hybrid','minor'),

    -- Bodyweight pushes
    ('Push-up','', 'hybrid','minor'),
    ('Push-up wide feet up','', 'hybrid','minor'),

    -- Core / abs (rep-based unless pure holds)
    ('Crunch','', 'reps','minor'),
    ('Reverse Crunch','', 'reps','minor'),
    ('Incline Reverse Crunch','', 'reps','minor'),
    ('Leg Raise + Reverse Crunch','', 'reps','minor'),
    ('Sit-Up','', 'reps','minor'),
    ('Sit-Up','Incline','reps','minor'),
    ('Sit-Up','Decline','reps','minor'),
    ('Ab Rollout','', 'reps','minor'),
    ('Bird dog plank','', 'reps','minor'),
    ('Russian Twist','', 'reps','minor'),
    ('Dead Bug','', 'reps','minor'),
    ('Hanging Leg Raise','', 'reps','minor'),
    ('Leg raises','', 'reps','minor'),
    ('Leg raises','Incline', 'reps','minor'),
    ('Incline Leg Raise','', 'reps','major'),

    -- Planks / holds (time-based)
    ('Plank','', 'time','minor'),
    ('Side Plank with Hip Drops','', 'reps','minor'),
    ('Side Plank with Hip Drops','Elevated','reps','minor'),
    ('Hollow Hold','', 'time','minor'),
    ('Fingerboard Hang','', 'time','minor'),

    -- Hips / glutes / lower body
    ('Glute Bridge','', 'hybrid','minor'),
    ('Frog Pump','', 'reps','minor'),
    ('Frog Pump Hold','', 'time','minor'),
    ('Hip Thrust','', 'load','major'),
    ('Fire Hydrant','', 'reps','minor'),
    ('Step back Lunge','', 'hybrid','minor'),
    ('RDL','', 'load','major'),

    -- Pull-ups / scapular
    ('Pull-up','', 'hybrid','minor'),
    ('Pull-up','Normal Grip','hybrid','minor'),
    ('Scapular pull-up','', 'reps','minor'),

    -- Calves / achilles (rehab style)
    ('Heel Drop','', 'reps','minor'),
    ('Heel Drop','Single Leg','reps','minor'),
    ('Heel Drop','Bent Knee','reps','minor'),
    ('Heel Drop','Bent Knee Single Leg','reps','minor'),

    -- Abduction / small implements
    ('Side-Lying Hip Abduction','', 'reps','minor'),
    ('Side-Lying Hip Abduction','Bent Knee','reps','minor'),

    -- Mobility / pelvic control / stretches
    ('Supine Pelvic Tilts','', 'reps','minor'),
    ('Pelvic Tilt','', 'reps','minor'),
    ('Straight Leg Stretch','', 'stretch','minor'),
    ('Hip Rotation Stretch','', 'stretch','minor'),

    -- Misc
    ('Side Bend','', 'load','minor')
    ON CONFLICT (name, variation)
    DO UPDATE SET
    measurement_type = EXCLUDED.measurement_type,
    variation_type   = EXCLUDED.variation_type;
    """

TAXONOMY_MAPPING_SQL = """
    -- === LINKING EXERCISES TO TAXONOMY ===
    -- Structure: (name, variation, target_path, contribution)
    CREATE TABLE IF NOT EXISTS exercise_target_map (
        name    text NOT NULL,
        variation text NOT NULL DEFAULT '',
        target_path      text NOT NULL REFERENCES muscle_taxonomy(path),
        contribution     numeric NOT NULL DEFAULT 1.0,  -- 0..1, sums can exceed 1.0 if you want overlapping credit
        PRIMARY KEY (name, variation, target_path),
        FOREIGN KEY (name, variation)
            REFERENCES exercise_meta(name, variation) ON DELETE CASCADE
    );

    -- Biceps / Forearms
    INSERT INTO exercise_target_map VALUES
    ('Bicep Curl','Incline','upper',1.0),
    ('Bicep Curl','Incline','upper.arms',1.0),
    ('Bicep Curl','Incline','upper.arms.biceps_brachii.long_head',0.70),
    ('Bicep Curl','Incline','upper.arms.biceps_brachii.short_head',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bicep Curl','Hammer','upper',1.0),
    ('Bicep Curl','Hammer','upper.arms',1.0),
    ('Bicep Curl','Hammer','upper.arms.brachialis',0.60),
    ('Bicep Curl','Hammer','upper.arms.brachioradialis',0.30),
    ('Bicep Curl','Hammer','upper.arms.biceps_brachii.long_head',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bicep Curl','', 'upper',1.0),
    ('Bicep Curl','', 'upper.arms',1.0),
    ('Bicep Curl','', 'upper.arms.biceps_brachii.long_head',0.50),
    ('Bicep Curl','', 'upper.arms.biceps_brachii.short_head',0.50)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bicep Curl','Hammer Incline','upper',1.0),
    ('Bicep Curl','Hammer Incline','upper.arms',1.0),
    ('Bicep Curl','Hammer Incline','upper.arms.brachialis',0.50),
    ('Bicep Curl','Hammer Incline','upper.arms.biceps_brachii.long_head',0.40),
    ('Bicep Curl','Hammer Incline','upper.arms.brachioradialis',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bicep Curl','Zottman','upper',1.0),
    ('Bicep Curl','Zottman','upper.arms',1.0),
    ('Bicep Curl','Zottman','upper.arms.brachioradialis',0.50),
    ('Bicep Curl','Zottman','upper.arms.biceps_brachii.long_head',0.30),
    ('Bicep Curl','Zottman','upper.arms.biceps_brachii.short_head',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Reverse Curl','', 'upper',1.0),
    ('Reverse Curl','', 'upper.forearms',1.0),
    ('Reverse Curl','', 'upper.forearms.extensors',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Reverse wrist curl','', 'upper',1.0),
    ('Reverse wrist curl','', 'upper.forearms',1.0),
    ('Reverse wrist curl','', 'upper.forearms.extensors',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Seated Forearm Curl','', 'upper',1.0),
    ('Seated Forearm Curl','', 'upper.forearms',1.0),
    ('Seated Forearm Curl','', 'upper.forearms.flexors',1.0)
    ON CONFLICT DO NOTHING;

    -- Rotator cuff / Shoulder mobility
    INSERT INTO exercise_target_map VALUES
    ('Lying Shoulder Internal Rotation','', 'upper',1.0),
    ('Lying Shoulder Internal Rotation','', 'upper.shoulders',1.0),
    ('Lying Shoulder Internal Rotation','', 'upper.shoulders.rotator_cuff.subscapularis',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Lying Shoulder External Rotation','', 'upper',1.0),
    ('Lying Shoulder External Rotation','', 'upper.shoulders',1.0),
    ('Lying Shoulder External Rotation','', 'upper.shoulders.rotator_cuff.infraspinatus',0.70),
    ('Lying Shoulder External Rotation','', 'upper.shoulders.rotator_cuff.teres_minor',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Wall/Floor Glides','', 'upper',1.0),
    ('Wall/Floor Glides','', 'upper.shoulders',1.0),
    ('Wall/Floor Glides','', 'upper.chest.serratus_anterior',0.50),
    ('Wall/Floor Glides','', 'upper.shoulders.rotator_cuff.infraspinatus',0.25),
    ('Wall/Floor Glides','', 'upper.shoulders.rotator_cuff.subscapularis',0.25)
    ON CONFLICT DO NOTHING;

    -- Delts / traps / upper back
    INSERT INTO exercise_target_map VALUES
    ('Lateral Raise','', 'upper',1.0),
    ('Lateral Raise','', 'upper.shoulders',1.0),
    ('Lateral Raise','', 'upper.shoulders.deltoid.lateral',0.80),
    ('Lateral Raise','', 'upper.shoulders.rotator_cuff.supraspinatus',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Front Raise','', 'upper',1.0),
    ('Front Raise','', 'upper.shoulders',1.0),
    ('Front Raise','', 'upper.shoulders.deltoid.anterior',0.90),
    ('Front Raise','', 'upper.chest.pectoralis_major.clavicular',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Reverse Fly','', 'upper',1.0),
    ('Reverse Fly','', 'upper.back',1.0),
    ('Reverse Fly','', 'upper.shoulders.deltoid.posterior',0.60),
    ('Reverse Fly','', 'upper.back.rhomboids',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Rear Delt Row','', 'upper',1.0),
    ('Rear Delt Row','', 'upper.back',1.0),
    ('Rear Delt Row','', 'upper.shoulders.deltoid.posterior',0.60),
    ('Rear Delt Row','', 'upper.back.rhomboids',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Shrug','', 'upper',1.0),
    ('Shrug','', 'upper.traps',1.0),
    ('Shrug','', 'upper.back.trapezius.upper',0.80),
    ('Shrug','', 'upper.back.trapezius.middle',0.20)
    ON CONFLICT DO NOTHING;

    -- Pressing / Chest
    INSERT INTO exercise_target_map VALUES
    ('Shoulder Press','', 'upper',1.0),
    ('Shoulder Press','', 'upper.shoulders',1.0),
    ('Shoulder Press','', 'upper.shoulders.deltoid.anterior',0.50),
    ('Shoulder Press','', 'upper.shoulders.deltoid.lateral',0.30),
    ('Shoulder Press','', 'upper.arms.triceps_brachii.lateral_head',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bench Press','', 'upper',1.0),
    ('Bench Press','', 'upper.chest',1.0),
    ('Bench Press','', 'upper.chest.pectoralis_major.sternal',0.60),
    ('Bench Press','', 'upper.arms.triceps_brachii.long_head',0.25),
    ('Bench Press','', 'upper.shoulders.deltoid.anterior',0.15)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bench Press','Flat', 'upper',1.0),
    ('Bench Press','Flat', 'upper.chest',1.0),
    ('Bench Press','Flat', 'upper.chest.pectoralis_major.sternal',0.60),
    ('Bench Press','Flat', 'upper.arms.triceps_brachii.long_head',0.25),
    ('Bench Press','Flat', 'upper.shoulders.deltoid.anterior',0.15)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bench Press','Incline','upper',1.0),
    ('Bench Press','Incline','upper.chest',1.0),
    ('Bench Press','Incline','upper.chest.pectoralis_major.clavicular',0.50),
    ('Bench Press','Incline','upper.arms.triceps_brachii.long_head',0.20),
    ('Bench Press','Incline','upper.shoulders.deltoid.anterior',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Chest Fly','', 'upper',1.0),
    ('Chest Fly','', 'upper.chest',1.0),
    ('Chest Fly','', 'upper.chest.pectoralis_major.sternal',0.85),
    ('Chest Fly','', 'upper.shoulders.deltoid.anterior',0.15)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Chest Fly','Flat','upper',1.0),
    ('Chest Fly','Flat','upper.chest',1.0),
    ('Chest Fly','Flat','upper.chest.pectoralis_major.sternal',0.85),
    ('Chest Fly','Flat','upper.shoulders.deltoid.anterior',0.15)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Push-up','', 'upper',1.0),
    ('Push-up','', 'upper.chest',1.0),
    ('Push-up','', 'upper.chest.pectoralis_major.sternal',0.60),
    ('Push-up','', 'upper.arms.triceps_brachii.lateral_head',0.25),
    ('Push-up','', 'upper.shoulders.deltoid.anterior',0.15)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bench Dips','', 'upper',1.0),
    ('Bench Dips','', 'upper.arms',1.0),
    ('Bench Dips','', 'upper.arms.triceps_brachii.long_head',0.40),
    ('Bench Dips','', 'upper.arms.triceps_brachii.lateral_head',0.40),
    ('Bench Dips','', 'upper.arms.triceps_brachii.medial_head',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bench Dips','Feet Elevated','upper',1.0),
    ('Bench Dips','Feet Elevated','upper.arms',1.0),
    ('Bench Dips','Feet Elevated','upper.arms.triceps_brachii.long_head',0.40),
    ('Bench Dips','Feet Elevated','upper.arms.triceps_brachii.lateral_head',0.40),
    ('Bench Dips','Feet Elevated','upper.arms.triceps_brachii.medial_head',0.20)
    ON CONFLICT DO NOTHING;

    -- Rows / Pulls
    INSERT INTO exercise_target_map VALUES
    ('One-Arm Row','', 'upper',1.0),
    ('One-Arm Row','', 'upper.back',1.0),
    ('One-Arm Row','', 'upper.back.latissimus_dorsi',0.60),
    ('One-Arm Row','', 'upper.back.rhomboids',0.20),
    ('One-Arm Row','', 'upper.shoulders.deltoid.posterior',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('One-Arm Row','Pronated','upper',1.0),
    ('One-Arm Row','Pronated','upper.back',1.0),
    ('One-Arm Row','Pronated','upper.back.latissimus_dorsi',0.50),
    ('One-Arm Row','Pronated','upper.back.rhomboids',0.30),
    ('One-Arm Row','Pronated','upper.back.trapezius.middle',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Lat Pullover','', 'upper',1.0),
    ('Lat Pullover','', 'upper.back',1.0),
    ('Lat Pullover','', 'upper.back.latissimus_dorsi',0.80),
    ('Lat Pullover','', 'upper.arms.triceps_brachii.long_head',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Pull-up','', 'upper',1.0),
    ('Pull-up','', 'upper.back',1.0),
    ('Pull-up','', 'upper.back.latissimus_dorsi',0.60),
    ('Pull-up','', 'upper.arms.biceps_brachii.long_head',0.25),
    ('Pull-up','', 'upper.shoulders.deltoid.posterior',0.15)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Scapular pull-up','', 'upper',1.0),
    ('Scapular pull-up','', 'upper.back',1.0),
    ('Scapular pull-up','', 'upper.back.trapezius.lower',0.60),
    ('Scapular pull-up','', 'upper.chest.serratus_anterior',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Scapular row','', 'upper',1.0),
    ('Scapular row','', 'upper.back',1.0),
    ('Scapular row','', 'upper.back.trapezius.middle',0.50),
    ('Scapular row','', 'upper.back.rhomboids',0.50)
    ON CONFLICT DO NOTHING;

    -- Core / Abs / Holds
    INSERT INTO exercise_target_map VALUES
    ('Crunch','', 'core',1.0),
    ('Crunch','', 'core.abs',1.0),
    ('Crunch','', 'core.abs.rectus_abdominis',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Reverse Crunch','', 'core',1.0),
    ('Reverse Crunch','', 'core.abs',1.0),
    ('Reverse Crunch','', 'core.abs.rectus_abdominis',0.80),
    ('Reverse Crunch','', 'core.hip_flexors',1.0),
    ('Reverse Crunch','', 'core.deep.transversus_abdominis',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Plank','', 'core',1.0),
    ('Plank','', 'core.deep.transversus_abdominis',0.50),
    ('Plank','', 'core.abs.rectus_abdominis',0.25),
    ('Plank','', 'core.obliques.external',0.25)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Hollow Hold','', 'core',1.0),
    ('Hollow Hold','', 'core.deep.transversus_abdominis',0.40),
    ('Hollow Hold','', 'core.abs.rectus_abdominis',0.40),
    ('Hollow Hold','', 'core.obliques.internal',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Dead Bug','', 'core',1.0),
    ('Dead Bug','', 'core.deep.transversus_abdominis',0.60),
    ('Dead Bug','', 'core.abs.rectus_abdominis',0.20),
    ('Dead Bug','', 'core.spinal_erectors.lumbar',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Bird dog plank','', 'core',1.0),
    ('Bird dog plank','', 'core.spinal_erectors',1.0),
    ('Bird dog plank','', 'core.deep.multifidus',0.50),
    ('Bird dog plank','', 'core.spinal_erectors.lumbar',0.30),
    ('Bird dog plank','', 'lower.glutes.gluteus_maximus',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Ab Rollout','', 'core',1.0),
    ('Ab Rollout','', 'core.abs',1.0),
    ('Ab Rollout','', 'core.abs.rectus_abdominis',0.60),
    ('Ab Rollout','', 'upper.chest.serratus_anterior',0.20),
    ('Ab Rollout','', 'upper.back.latissimus_dorsi',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Russian Twist','', 'core',1.0),
    ('Russian Twist','', 'core.obliques',1.0),
    ('Russian Twist','', 'core.obliques.external',0.60),
    ('Russian Twist','', 'core.obliques.internal',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Side Plank with Hip Drops','', 'core',1.0),
    ('Side Plank with Hip Drops','', 'core.obliques.external',0.50),
    ('Side Plank with Hip Drops','', 'core.obliques.internal',0.30),
    ('Side Plank with Hip Drops','', 'core.deep.transversus_abdominis',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Side Plank with Hip Drops','Elevated', 'core',1.0),
    ('Side Plank with Hip Drops','Elevated', 'core.obliques.external',0.50),
    ('Side Plank with Hip Drops','Elevated', 'core.obliques.internal',0.30),
    ('Side Plank with Hip Drops','Elevated', 'core.deep.transversus_abdominis',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Leg raises','', 'core',1.0),
    ('Leg raises','', 'core.abs',1.0),
    ('Leg raises','', 'core.abs.rectus_abdominis',0.60),
    ('Leg raises','', 'core.hip_flexors',1.0),
    ('Leg raises','', 'core.deep.transversus_abdominis',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Leg raises','Incline', 'core',1.0),
    ('Leg raises','Incline', 'core.abs',1.0),
    ('Leg raises','Incline', 'core.abs.rectus_abdominis',0.60),
    ('Leg raises','Incline', 'core.hip_flexors',1.0),
    ('Leg raises','Incline', 'core.deep.transversus_abdominis',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Leg Raise + Reverse Crunch','', 'core',1.0),
    ('Leg Raise + Reverse Crunch','', 'core.abs.rectus_abdominis',0.70),
    ('Leg Raise + Reverse Crunch','', 'core.hip_flexors',1.0),
    ('Leg Raise + Reverse Crunch','', 'core.deep.transversus_abdominis',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Hanging Leg Raise','', 'core',1.0),
    ('Hanging Leg Raise','', 'core.abs.rectus_abdominis',0.60),
    ('Hanging Leg Raise','', 'core.hip_flexors',1.0),
    ('Hanging Leg Raise','', 'core.deep.transversus_abdominis',0.40)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Sit-Up','', 'core',1.0),
    ('Sit-Up','', 'core.abs.rectus_abdominis',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Sit-Up','Incline', 'core',1.0),
    ('Sit-Up','Incline', 'core.abs.rectus_abdominis',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Sit-Up','Decline', 'core',1.0),
    ('Sit-Up','Decline', 'core.abs.rectus_abdominis',1.0)
    ON CONFLICT DO NOTHING;

    -- Hips / Glutes / Lower
    INSERT INTO exercise_target_map VALUES
    ('RDL','', 'lower',1.0),
    ('RDL','', 'lower.hamstrings',1.0),
    ('RDL','', 'lower.hamstrings.semitendinosus',0.30),
    ('RDL','', 'lower.hamstrings.semimembranosus',0.30),
    ('RDL','', 'lower.hamstrings.biceps_femoris.long_head',0.30),
    ('RDL','', 'lower.glutes.gluteus_maximus',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Step back Lunge','', 'lower',1.0),
    ('Step back Lunge','', 'lower.quads',1.0),
    ('Step back Lunge','', 'lower.quads.rectus_femoris',0.30),
    ('Step back Lunge','', 'lower.quads.vastus_lateralis',0.20),
    ('Step back Lunge','', 'lower.quads.vastus_medialis',0.20),
    ('Step back Lunge','', 'lower.glutes.gluteus_maximus',0.20),
    ('Step back Lunge','', 'lower.hamstrings.semitendinosus',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Glute Bridge','', 'lower',1.0),
    ('Glute Bridge','', 'lower.glutes',1.0),
    ('Glute Bridge','', 'lower.glutes.gluteus_maximus',0.80),
    ('Glute Bridge','', 'lower.hamstrings.semitendinosus',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Hip Thrust','', 'lower',1.0),
    ('Hip Thrust','', 'lower.glutes',1.0),
    ('Hip Thrust','', 'lower.glutes.gluteus_maximus',0.70),
    ('Hip Thrust','', 'lower.hamstrings.semitendinosus',0.20),
    ('Hip Thrust','', 'lower.quads.rectus_femoris',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Fire Hydrant','', 'lower',1.0),
    ('Fire Hydrant','', 'lower.glutes',1.0),
    ('Fire Hydrant','', 'lower.glutes.gluteus_medius',0.70),
    ('Fire Hydrant','', 'lower.glutes.gluteus_minimus',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Side-Lying Hip Abduction','', 'lower',1.0),
    ('Side-Lying Hip Abduction','', 'lower.glutes',1.0),
    ('Side-Lying Hip Abduction','', 'lower.glutes.gluteus_medius',0.70),
    ('Side-Lying Hip Abduction','', 'lower.glutes.gluteus_minimus',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Side-Lying Hip Abduction','Bent Knee', 'lower',1.0),
    ('Side-Lying Hip Abduction','Bent Knee', 'lower.glutes',1.0),
    ('Side-Lying Hip Abduction','Bent Knee', 'lower.glutes.gluteus_medius',0.70),
    ('Side-Lying Hip Abduction','Bent Knee', 'lower.glutes.gluteus_minimus',0.30)
    ON CONFLICT DO NOTHING;

    -- Calves / Achilles
    INSERT INTO exercise_target_map VALUES
    ('Heel Drop','', 'lower',1.0),
    ('Heel Drop','', 'lower.calves',1.0),
    ('Heel Drop','', 'lower.calves.gastrocnemius.medial',0.35),
    ('Heel Drop','', 'lower.calves.gastrocnemius.lateral',0.35),
    ('Heel Drop','', 'lower.calves.soleus',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Heel Drop','Single Leg','lower',1.0),
    ('Heel Drop','Single Leg','lower.calves',1.0),
    ('Heel Drop','Single Leg','lower.calves.gastrocnemius.medial',0.35),
    ('Heel Drop','Single Leg','lower.calves.gastrocnemius.lateral',0.35),
    ('Heel Drop','Single Leg','lower.calves.soleus',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Heel Drop','Bent Knee','lower',1.0),
    ('Heel Drop','Bent Knee','lower.calves',1.0),
    ('Heel Drop','Bent Knee','lower.calves.soleus',0.80),
    ('Heel Drop','Bent Knee','lower.calves.gastrocnemius.medial',0.10),
    ('Heel Drop','Bent Knee','lower.calves.gastrocnemius.lateral',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Heel Drop','Bent Knee Single Leg','lower',1.0),
    ('Heel Drop','Bent Knee Single Leg','lower.calves',1.0),
    ('Heel Drop','Bent Knee Single Leg','lower.calves.soleus',0.80),
    ('Heel Drop','Bent Knee Single Leg','lower.calves.gastrocnemius.medial',0.10),
    ('Heel Drop','Bent Knee Single Leg','lower.calves.gastrocnemius.lateral',0.10)
    ON CONFLICT DO NOTHING;

    -- Dips / Triceps accessory variation
    INSERT INTO exercise_target_map VALUES
    ('Kickbacks','', 'upper',1.0),
    ('Kickbacks','', 'upper.arms',1.0),
    ('Kickbacks','', 'upper.arms.triceps_brachii.long_head',0.40),
    ('Kickbacks','', 'upper.arms.triceps_brachii.lateral_head',0.40),
    ('Kickbacks','', 'upper.arms.triceps_brachii.medial_head',0.20)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Db Kickbacks','', 'upper',1.0),
    ('Db Kickbacks','', 'upper.arms',1.0),
    ('Db Kickbacks','', 'upper.arms.triceps_brachii.long_head',0.40),
    ('Db Kickbacks','', 'upper.arms.triceps_brachii.lateral_head',0.40),
    ('Db Kickbacks','', 'upper.arms.triceps_brachii.medial_head',0.20)
    ON CONFLICT DO NOTHING;

    -- Stretches / Mobility
    INSERT INTO exercise_target_map VALUES
    ('Straight Leg Stretch','', 'lower',1.0),
    ('Straight Leg Stretch','', 'lower.hamstrings',1.0)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Hip Rotation Stretch','', 'lower',1.0),
    ('Hip Rotation Stretch','', 'lower.glutes',1.0),
    ('Hip Rotation Stretch','', 'lower.glutes.gluteus_medius',0.60),
    ('Hip Rotation Stretch','', 'lower.glutes.gluteus_minimus',0.40)
    ON CONFLICT DO NOTHING;

    -- Misc / Holds
    INSERT INTO exercise_target_map VALUES
    ('Fingerboard Hang','', 'upper',1.0),
    ('Fingerboard Hang','', 'upper.forearms',1.0),
    ('Fingerboard Hang','', 'upper.forearms.flexors',0.90),
    ('Fingerboard Hang','', 'upper.forearms.extensors',0.10)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Pelvic Tilt','', 'core',1.0),
    ('Pelvic Tilt','', 'core.deep.transversus_abdominis',0.70),
    ('Pelvic Tilt','', 'core.deep.multifidus',0.30)
    ON CONFLICT DO NOTHING;

    INSERT INTO exercise_target_map VALUES
    ('Supine Pelvic Tilts','', 'core',1.0),
    ('Supine Pelvic Tilts','', 'core.deep.transversus_abdominis',0.70),
    ('Supine Pelvic Tilts','', 'core.deep.multifidus',0.30)
    ON CONFLICT DO NOTHING;
    """
