-- Post-deploy cleanup. Run AFTER homelab-api restart (init() handles inserts/upserts/views).
-- psql "${POSTGRES_CON}fitness" -f migrations/apply-approved-changes.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Remove merged / deprecated meta
-- ---------------------------------------------------------------------------
DELETE FROM exercise_target_map WHERE name = 'Incline Reverse Crunch';
DELETE FROM exercise_meta WHERE name = 'Incline Reverse Crunch';

-- ---------------------------------------------------------------------------
-- 2. Redundant duplicate mappings (minor variations inherit base)
-- ---------------------------------------------------------------------------
DELETE FROM exercise_target_map WHERE name = 'Bench Press' AND variation = 'Flat';
DELETE FROM exercise_target_map WHERE name = 'Chest Fly' AND variation = 'Flat';
DELETE FROM exercise_target_map WHERE name = 'Bench Dips' AND variation = 'Feet Elevated';
DELETE FROM exercise_target_map WHERE name = 'Sit-Up' AND variation = 'Incline';
DELETE FROM exercise_target_map WHERE name = 'Sit-Up' AND variation = 'Decline';
DELETE FROM exercise_target_map WHERE name = 'Leg raises' AND variation = 'Incline';
DELETE FROM exercise_target_map WHERE name = 'Side Plank with Hip Drops' AND variation = 'Elevated';
DELETE FROM exercise_target_map WHERE name = 'Heel Drop' AND variation = 'Single Leg';
DELETE FROM exercise_target_map WHERE name = 'Side-Lying Hip Abduction' AND variation = 'Bent Knee';

-- ---------------------------------------------------------------------------
-- 3. Stale / incorrect mappings removed from seed (init cannot delete)
-- ---------------------------------------------------------------------------

-- Side Bend: QL-only mapping was wrong; obliques are primary
DELETE FROM exercise_target_map
WHERE name = 'Side Bend' AND variation = '' AND target_path = 'core.deep';
DELETE FROM exercise_target_map
WHERE name = 'Side Bend' AND variation = ''
  AND target_path = 'core.deep.quadratus_lumborum' AND contribution > 0.20;

-- Side Plank with Hip Drops: QL overweighted in old DB
DELETE FROM exercise_target_map
WHERE name = 'Side Plank with Hip Drops' AND target_path = 'core.deep.quadratus_lumborum';

-- Bird dog: stale QL row
DELETE FROM exercise_target_map
WHERE name = 'Bird dog plank' AND target_path = 'core.deep.quadratus_lumborum';

-- Prone Y Raises: was erector-only; now posterior shoulder / lower trap
DELETE FROM exercise_target_map WHERE name = 'Prone Y Raises';

-- Reverse Curl: was extensors-only
DELETE FROM exercise_target_map WHERE name = 'Reverse Curl';

-- Zottman: rebalance biceps / extensors
DELETE FROM exercise_target_map
WHERE name = 'Bicep Curl' AND variation = 'Zottman'
  AND target_path IN (
    'upper.arms.brachioradialis',
    'upper.arms.biceps_brachii.long_head',
    'upper.arms.biceps_brachii.short_head'
  );

-- Lat Pullover: add teres major split
DELETE FROM exercise_target_map
WHERE name = 'Lat Pullover' AND target_path = 'upper.back.latissimus_dorsi'
  AND contribution = 0.80;

-- Sit-Up: was rectus-only; hip flexors are major in full sit-up
DELETE FROM exercise_target_map
WHERE name = 'Sit-Up' AND variation = '' AND target_path = 'core.abs.rectus_abdominis'
  AND contribution = 1.0;
DELETE FROM exercise_target_map
WHERE name = 'Sit-Up' AND variation IN ('Incline', 'Decline')
  AND target_path = 'core.hip_flexors';

-- RDL: rebalance hamstring heads
DELETE FROM exercise_target_map WHERE name = 'RDL' AND target_path LIKE 'lower.hamstrings.%'
  AND contribution = 0.30;

-- Hamstring Floor Curl: calves / generic glutes / core were overweighted
DELETE FROM exercise_target_map
WHERE name = 'Hamstring Floor Curl'
  AND target_path IN ('lower.calves', 'lower.glutes', 'core');

-- Superman: add glutes / hamstrings
DELETE FROM exercise_target_map WHERE name = 'Superman';

-- Wall/Floor Glides: spinal erectors are not a primary target
DELETE FROM exercise_target_map
WHERE name = 'Wall/Floor Glides' AND target_path LIKE 'core.spinal_erectors%';

-- Invalid taxonomy parent rollup rows from older seed (not in current data.py)
DELETE FROM exercise_target_map WHERE target_path = 'core.deep';

-- ---------------------------------------------------------------------------
-- 4. Contribution updates (ON CONFLICT DO NOTHING won't refresh these)
-- ---------------------------------------------------------------------------
UPDATE exercise_target_map SET contribution = 0.15
WHERE name = 'Side Bend' AND variation = ''
  AND target_path = 'core.deep.quadratus_lumborum'
  AND contribution <> 0.15;

UPDATE exercise_target_map SET contribution = 1.0
WHERE name = 'Incline Leg Raise' AND variation = ''
  AND target_path = 'core.hip_flexors'
  AND contribution <> 1.0;

UPDATE exercise_target_map SET contribution = 0.70
WHERE name = 'Lat Pullover' AND variation = ''
  AND target_path = 'upper.back.latissimus_dorsi'
  AND contribution = 0.80;

UPDATE exercise_target_map SET contribution = 0.35
WHERE name = 'Bird dog plank' AND target_path = 'core.deep.multifidus' AND contribution = 0.50;

UPDATE exercise_target_map SET contribution = 0.25
WHERE name = 'Bird dog plank' AND target_path = 'core.spinal_erectors.lumbar' AND contribution = 0.30;

UPDATE exercise_target_map SET contribution = 0.15
WHERE name = 'Bird dog plank' AND target_path = 'lower.glutes.gluteus_maximus' AND contribution = 0.20;

UPDATE exercise_target_map SET contribution = 0.40
WHERE name = 'Side Plank' AND variation = '' AND target_path = 'core.obliques.external' AND contribution = 0.50;

UPDATE exercise_target_map SET contribution = 0.25
WHERE name = 'Side Plank' AND variation = '' AND target_path = 'core.obliques.internal' AND contribution = 0.30;

UPDATE exercise_target_map SET contribution = 0.15
WHERE name = 'Side Plank' AND variation = '' AND target_path = 'core.deep.transversus_abdominis' AND contribution = 0.20;

UPDATE exercise_target_map SET contribution = 0.30
WHERE name = 'Side Plank' AND variation = 'Copenhagen' AND target_path = 'lower.adductors.adductor_magnus' AND contribution = 0.50;

UPDATE exercise_target_map SET contribution = 0.25
WHERE name = 'Side Plank' AND variation = 'Copenhagen' AND target_path = 'core.obliques.external' AND contribution = 0.30;

UPDATE exercise_target_map SET contribution = 0.15
WHERE name = 'Side Plank' AND variation = 'Copenhagen' AND target_path = 'core.deep.transversus_abdominis' AND contribution = 0.20;

UPDATE exercise_target_map SET contribution = 0.45
WHERE name = 'Side Plank with Hip Drops' AND variation = '' AND target_path = 'core.obliques.external' AND contribution = 0.50;

UPDATE exercise_target_map SET contribution = 0.25
WHERE name = 'Side Plank with Hip Drops' AND variation = '' AND target_path = 'core.obliques.internal' AND contribution = 0.30;

UPDATE exercise_target_map SET contribution = 0.15
WHERE name = 'Side Plank with Hip Drops' AND variation = '' AND target_path = 'core.deep.transversus_abdominis' AND contribution = 0.20;

-- ---------------------------------------------------------------------------
-- 5. Inserts for paths changed in seed (safe if deploy already inserted)
-- ---------------------------------------------------------------------------
INSERT INTO exercise_target_map (name, variation, target_path, contribution) VALUES
-- Reverse Curl (rebuilt)
('Reverse Curl', '', 'upper', 1.0),
('Reverse Curl', '', 'upper.arms', 0.80),
('Reverse Curl', '', 'upper.arms.brachioradialis', 0.50),
('Reverse Curl', '', 'upper.arms.brachialis', 0.30),
('Reverse Curl', '', 'upper.forearms', 0.20),
('Reverse Curl', '', 'upper.forearms.extensors', 0.20),

-- Zottman
('Bicep Curl', 'Zottman', 'upper.arms.brachioradialis', 0.45),
('Bicep Curl', 'Zottman', 'upper.arms.biceps_brachii.long_head', 0.25),
('Bicep Curl', 'Zottman', 'upper.arms.biceps_brachii.short_head', 0.15),
('Bicep Curl', 'Zottman', 'upper.forearms.extensors', 0.15),

-- Lat Pullover
('Lat Pullover', '', 'upper.back.teres_major', 0.10),

-- Prone Y Raises (rebuilt)
('Prone Y Raises', '', 'upper', 0.70),
('Prone Y Raises', '', 'upper.back', 0.50),
('Prone Y Raises', '', 'upper.back.trapezius.lower', 0.35),
('Prone Y Raises', '', 'upper.back.rhomboids', 0.15),
('Prone Y Raises', '', 'upper.shoulders', 0.50),
('Prone Y Raises', '', 'upper.shoulders.deltoid.posterior', 0.30),
('Prone Y Raises', '', 'upper.chest.serratus_anterior', 0.20),

-- Sit-Up hip flexor credit
('Sit-Up', '', 'core.abs', 1.0),
('Sit-Up', '', 'core.abs.rectus_abdominis', 0.55),
('Sit-Up', '', 'core.hip_flexors', 0.45),

-- RDL
('RDL', '', 'lower.hamstrings.semitendinosus', 0.28),
('RDL', '', 'lower.hamstrings.semimembranosus', 0.28),
('RDL', '', 'lower.hamstrings.biceps_femoris.long_head', 0.28),
('RDL', '', 'lower.hamstrings.biceps_femoris.short_head', 0.10),
('RDL', '', 'core.spinal_erectors.lumbar', 0.06),

-- Bird dog glute stabilizers
('Bird dog plank', '', 'lower', 0.45),
('Bird dog plank', '', 'lower.glutes.gluteus_medius', 0.20),
('Bird dog plank', '', 'lower.glutes.gluteus_minimus', 0.10),

-- Side plank stabilizers
('Side Plank', '', 'lower.glutes.gluteus_medius', 0.25),
('Side Plank', '', 'lower.glutes.gluteus_minimus', 0.10),
('Side Plank', 'Copenhagen', 'lower.adductors.adductor_longus', 0.25),
('Side Plank', 'Copenhagen', 'lower.glutes.gluteus_medius', 0.20),
('Side Plank', 'Copenhagen', 'lower.glutes.gluteus_minimus', 0.10),

-- Side plank hip drops
('Side Plank with Hip Drops', '', 'lower.glutes.gluteus_medius', 0.15),

-- Hamstring floor curl
('Hamstring Floor Curl', '', 'lower.glutes.gluteus_maximus', 0.25),
('Hamstring Floor Curl', '', 'lower.glutes.gluteus_medius', 0.15),
('Hamstring Floor Curl', '', 'lower.glutes.gluteus_minimus', 0.05),
('Hamstring Floor Curl', '', 'core.deep.transversus_abdominis', 0.15),

-- Lower-body glute med/min additions
('Squat', '', 'lower.quads.vastus_intermedius', 0.08),
('Squat', '', 'lower.glutes.gluteus_medius', 0.15),
('Squat', '', 'lower.glutes.gluteus_minimus', 0.05),
('Squat', '', 'core.spinal_erectors.lumbar', 0.07),
('Pistol Squat', '', 'lower.glutes.gluteus_medius', 0.40),
('Pistol Squat', '', 'lower.glutes.gluteus_minimus', 0.15),
('Lunge', '', 'lower.glutes.gluteus_medius', 0.25),
('Lunge', '', 'lower.glutes.gluteus_minimus', 0.10),
('Reverse Lunge', '', 'lower.glutes.gluteus_medius', 0.25),
('Reverse Lunge', '', 'lower.glutes.gluteus_minimus', 0.10),
('Step back Lunge', '', 'lower.glutes.gluteus_medius', 0.20),
('Step back Lunge', '', 'lower.glutes.gluteus_minimus', 0.10),
('Bulgarian Split Squat', '', 'lower.glutes.gluteus_minimus', 0.10),

-- Superman (rebuilt)
('Superman', '', 'core', 1.0),
('Superman', '', 'core.spinal_erectors', 1.0),
('Superman', '', 'core.spinal_erectors.lumbar', 0.45),
('Superman', '', 'core.spinal_erectors.thoracic', 0.25),
('Superman', '', 'lower', 0.35),
('Superman', '', 'lower.glutes.gluteus_maximus', 0.20),
('Superman', '', 'lower.hamstrings.semitendinosus', 0.10)
ON CONFLICT DO NOTHING;

COMMIT;

-- Verify
SELECT * FROM vw_unmapped_logged_exercises ORDER BY log_count DESC;
SELECT * FROM vw_orphan_meta ORDER BY name, variation;
SELECT * FROM vw_incomplete_meta_mappings;
