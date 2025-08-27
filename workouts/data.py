
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
