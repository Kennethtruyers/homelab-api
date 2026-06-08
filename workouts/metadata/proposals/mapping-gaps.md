# Mapping gaps proposal

Data from exports (2026-06-07). Fill **your_decision** per row.

## How to decide


| Value     | Meaning                                       |
| --------- | --------------------------------------------- |
| `approve` | Apply as proposed                             |
| `reject`  | Skip — handle manually later                  |
| `skip`    | No action needed (inherits or already mapped) |
| `edit: …` | Approve with your notes                       |


**Recommended** column is the agent's suggestion.

---

## 1. Orphan meta — in catalog, no effective mapping

From `01_exercise_meta_status.csv` where `mapping_status = no_mapping`.


| name                   | variation       | logged | type  | resolution                                          | recommended                   | your_decision             |
| ---------------------- | --------------- | ------ | ----- | --------------------------------------------------- | ----------------------------- | ------------------------- |
| Bicep Curl             | Standing        | 0      | minor | Inherit from base — no new rows                     | **skip**                      | **skip**                  |
| One-Arm Row            | Flared          | 0      | minor | Inherit from base                                   | **skip**                      | **skip**                  |
| One-Arm Row            | Normal          | 0      | minor | Inherit from base                                   | **skip**                      | **skip**                  |
| One-Arm Row            | Flared Pronated | 0      | minor | Inherit from base                                   | **skip**                      | **skip**                  |
| Pull-up                | Normal Grip     | 0      | minor | Inherit from base                                   | **skip**                      | **skip**                  |
| Floor Press            | *(base)*        | 0      | major | Add mapping §3                                      | **approve** (when you log it) | approve                   |
| Push-up wide feet up   | *(base)*        | 0      | minor | Add mapping §3                                      | **approve** (when you log it) | approve                   |
| Incline Reverse Crunch | *(base)*        | 0      | minor | Add mapping §3 OR merge with Reverse Crunch/Incline | **approve** §3                | merge with reverse crunch |
| Frog Pump              | *(base)*        | 1      | minor | Add mapping §3 — **logged & unmapped**              | **approve**                   | approve                   |
| Frog Pump Hold         | *(base)*        | 1      | minor | Add mapping §3 — **logged & unmapped**              | **approve**                   | approve                   |


**Options:** `skip` for inherit-only rows · `approve` for §3 INSERT blocks · `reject` to leave unmapped.

---

## 1b. Incomplete meta — mapping exists but no muscle-level (depth 3) rows


| name                 | variation | logged | mapping_rows | recommended                               | your_decision |
| -------------------- | --------- | ------ | ------------ | ----------------------------------------- | ------------- |
| Incline Leg Raise    | *(base)*  | 0      | 2            | Add muscle-level rows §3b                 | **approve**   |
| Straight Leg Stretch | *(base)*  | 1      | 2            | Add `lower.hamstrings.*` depth-3 rows §3b | **approve**   |


---

## 1c. Already resolved in DB (no action)

These were orphan in seed data but now have mappings:


| name           | variation | logged | status      |
| -------------- | --------- | ------ | ----------- |
| Prone Y Raises | *(base)*  | 1      | ok (3 rows) |
| Side Bend      | *(base)*  | 13     | ok (3 rows) |


**Recommended:** **skip** — verify muscle targets are correct; edit contributions in a follow-up if needed.

---

## 2. Redundant duplicate mappings — delete after reclassifying to minor

Identical rows to `(name, '')`. Delete once variation is `minor` and inheritance is active.


| name                      | variation     | logged | action                  | recommended | your_decision |
| ------------------------- | ------------- | ------ | ----------------------- | ----------- | ------------- |
| Bench Press               | Flat          | 0      | DELETE rows + set minor | **approve** | approve       |
| Chest Fly                 | Flat          | 6      | DELETE rows + set minor | **approve** | approve       |
| Bench Dips                | Feet Elevated | 6      | DELETE rows             | **approve** | approve       |
| Sit-Up                    | Incline       | 4      | DELETE rows             | **approve** | approve       |
| Sit-Up                    | Decline       | 2      | DELETE rows             | **approve** | approve       |
| Leg raises                | Incline       | 2      | DELETE rows             | **approve** | approve       |
| Side Plank with Hip Drops | Elevated      | 3      | DELETE rows             | **approve** | approve       |
| Heel Drop                 | Single Leg    | 2      | DELETE rows             | **approve** | approve       |
| Side-Lying Hip Abduction  | Bent Knee     | 2      | DELETE rows             | **approve** | approve       |


**Options:** `**approve`** (delete + inherit) · `reject` (keep duplicate rows).

---

## 3. Proposed new mappings — existing meta, no/incomplete mapping

### Frog Pump *(logged 1×, unmapped)*

```sql
INSERT INTO exercise_target_map VALUES
('Frog Pump','', 'lower',1.0),
('Frog Pump','', 'lower.glutes',1.0),
('Frog Pump','', 'lower.glutes.gluteus_maximus',0.90),
('Frog Pump','', 'lower.adductors.adductor_magnus',0.10)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


### Frog Pump Hold *(logged 1×, unmapped)*

```sql
INSERT INTO exercise_target_map VALUES
('Frog Pump Hold','', 'lower',1.0),
('Frog Pump Hold','', 'lower.glutes',1.0),
('Frog Pump Hold','', 'lower.glutes.gluteus_maximus',0.90),
('Frog Pump Hold','', 'lower.adductors.adductor_magnus',0.10)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


### Floor Press *(not logged)*

```sql
INSERT INTO exercise_target_map VALUES
('Floor Press','', 'upper',1.0),
('Floor Press','', 'upper.chest',1.0),
('Floor Press','', 'upper.chest.pectoralis_major.sternal',0.65),
('Floor Press','', 'upper.arms.triceps_brachii.long_head',0.30),
('Floor Press','', 'upper.shoulders.deltoid.anterior',0.05)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


### Push-up wide feet up *(not logged)*

```sql
INSERT INTO exercise_target_map VALUES
('Push-up wide feet up','', 'upper',1.0),
('Push-up wide feet up','', 'upper.chest',1.0),
('Push-up wide feet up','', 'upper.chest.pectoralis_major.clavicular',0.45),
('Push-up wide feet up','', 'upper.chest.pectoralis_major.sternal',0.25),
('Push-up wide feet up','', 'upper.arms.triceps_brachii.lateral_head',0.20),
('Push-up wide feet up','', 'upper.shoulders.deltoid.anterior',0.10)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


### Incline Reverse Crunch *(not logged; Reverse Crunch/Incline logged 1× instead)*

```sql
INSERT INTO exercise_target_map VALUES
('Incline Reverse Crunch','', 'core',1.0),
('Incline Reverse Crunch','', 'core.abs',1.0),
('Incline Reverse Crunch','', 'core.abs.rectus_abdominis',0.80),
('Incline Reverse Crunch','', 'core.hip_flexors',1.0),
('Incline Reverse Crunch','', 'core.deep.transversus_abdominis',0.20)
ON CONFLICT DO NOTHING;
```


| recommended                                                                    | your_decision |
| ------------------------------------------------------------------------------ | ------------- |
| **approve** — also add `Reverse Crunch/Incline` meta (§4) for the logged entry | approve       |


### 3b. Incomplete mapping fixes

**Incline Leg Raise** — add muscle-level rows:

```sql
INSERT INTO exercise_target_map VALUES
('Incline Leg Raise','', 'core.abs.rectus_abdominis',0.55),
('Incline Leg Raise','', 'core.hip_flexors',1.0),
('Incline Leg Raise','', 'core.deep.transversus_abdominis',0.45)
ON CONFLICT DO NOTHING;
```

**Straight Leg Stretch** — add muscle-level rows:

```sql
INSERT INTO exercise_target_map VALUES
('Straight Leg Stretch','', 'lower.hamstrings.semitendinosus',0.35),
('Straight Leg Stretch','', 'lower.hamstrings.semimembranosus',0.35),
('Straight Leg Stretch','', 'lower.hamstrings.biceps_femoris.long_head',0.30)
ON CONFLICT DO NOTHING;
```


| recommended      | your_decision |
| ---------------- | ------------- |
| **approve** both | approve       |


---

## 4. Logged exercises missing from meta

From `02_logged_exercises.csv` where `mapping_status = missing_meta`.

### High volume (prioritize)

#### Pistol Squat *(14 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Pistol Squat','', 'hybrid','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Pistol Squat','', 'lower',1.0),
('Pistol Squat','', 'lower.quads',1.0),
('Pistol Squat','', 'lower.quads.vastus_lateralis',0.25),
('Pistol Squat','', 'lower.quads.vastus_medialis',0.25),
('Pistol Squat','', 'lower.quads.rectus_femoris',0.20),
('Pistol Squat','', 'lower.glutes.gluteus_maximus',0.20),
('Pistol Squat','', 'lower.hamstrings.semitendinosus',0.10)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Pistol Squat / Assisted *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Pistol Squat','Assisted', 'hybrid','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
-- no mapping rows; inherits Pistol Squat base
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Finger Rolls *(13 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Finger Rolls','', 'reps','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Finger Rolls','', 'upper',1.0),
('Finger Rolls','', 'upper.forearms',1.0),
('Finger Rolls','', 'upper.forearms.flexors',0.70),
('Finger Rolls','', 'upper.forearms.extensors',0.30)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Squat *(10 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Squat','', 'hybrid','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Squat','', 'lower',1.0),
('Squat','', 'lower.quads',1.0),
('Squat','', 'lower.quads.vastus_lateralis',0.25),
('Squat','', 'lower.quads.vastus_medialis',0.25),
('Squat','', 'lower.quads.rectus_femoris',0.20),
('Squat','', 'lower.glutes.gluteus_maximus',0.20),
('Squat','', 'lower.hamstrings.semitendinosus',0.10)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Toe Lifts *(8 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Toe Lifts','', 'reps','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Toe Lifts','', 'lower',1.0),
('Toe Lifts','', 'lower.calves',1.0),
('Toe Lifts','', 'lower.calves.tibialis_anterior',1.0)  -- NOTE: tibialis_anterior not in taxonomy; use gastroc/soleus or add taxonomy node
ON CONFLICT DO NOTHING;
```

**Note:** `tibialis_anterior` is not in `muscle_taxonomy`. **Recommended:** map to `lower.calves.soleus` (0.60) + `lower.calves.gastrocnemius.medial` (0.40) as proxy, or add taxonomy node first.

Revised without new taxonomy:

```sql
INSERT INTO exercise_target_map VALUES
('Toe Lifts','', 'lower',1.0),
('Toe Lifts','', 'lower.calves',1.0),
('Toe Lifts','', 'lower.calves.soleus',0.60),
('Toe Lifts','', 'lower.calves.gastrocnemius.medial',0.40)
ON CONFLICT DO NOTHING;
```


| recommended                                                    | your_decision               |
| -------------------------------------------------------------- | --------------------------- |
| **approve** (proxy mapping) · or `edit: add tibialis taxonomy` | edit: add tibialis taxonomy |


#### Side Plank *(7 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Side Plank','', 'time','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Side Plank','', 'core',1.0),
('Side Plank','', 'core.obliques.external',0.50),
('Side Plank','', 'core.obliques.internal',0.30),
('Side Plank','', 'core.deep.transversus_abdominis',0.20)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Side Plank / Copenhagen *(3 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Side Plank','Copenhagen', 'time','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Side Plank','Copenhagen', 'lower',1.0),
('Side Plank','Copenhagen', 'lower.adductors',1.0),
('Side Plank','Copenhagen', 'lower.adductors.adductor_magnus',0.50),
('Side Plank','Copenhagen', 'core.obliques.external',0.30),
('Side Plank','Copenhagen', 'core.deep.transversus_abdominis',0.20)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Chest supported row *(5 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Chest supported row','', 'load','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Chest supported row','', 'upper',1.0),
('Chest supported row','', 'upper.back',1.0),
('Chest supported row','', 'upper.back.latissimus_dorsi',0.50),
('Chest supported row','', 'upper.back.rhomboids',0.30),
('Chest supported row','', 'upper.shoulders.deltoid.posterior',0.20)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


### Medium / low volume

#### Reverse Lunge *(3 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Reverse Lunge','', 'hybrid','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Reverse Lunge','', 'lower',1.0),
('Reverse Lunge','', 'lower.quads',1.0),
('Reverse Lunge','', 'lower.quads.vastus_lateralis',0.20),
('Reverse Lunge','', 'lower.quads.vastus_medialis',0.20),
('Reverse Lunge','', 'lower.quads.rectus_femoris',0.20),
('Reverse Lunge','', 'lower.glutes.gluteus_maximus',0.25),
('Reverse Lunge','', 'lower.hamstrings.semitendinosus',0.15)
ON CONFLICT DO NOTHING;
```


| recommended                                                 | your_decision |
| ----------------------------------------------------------- | ------------- |
| **approve** — or `edit: minor variation of Step back Lunge` | approve       |


#### Pull-up / Wide Grip *(2 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Pull-up','Wide Grip', 'hybrid','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Pull-up','Wide Grip', 'upper',1.0),
('Pull-up','Wide Grip', 'upper.back',1.0),
('Pull-up','Wide Grip', 'upper.back.latissimus_dorsi',0.75),
('Pull-up','Wide Grip', 'upper.shoulders.deltoid.posterior',0.15),
('Pull-up','Wide Grip', 'upper.arms.biceps_brachii.long_head',0.10)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Heel Drop / Unsupported *(2 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Heel Drop','Unsupported', 'reps','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
-- inherits Heel Drop base mapping
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Frog Stand *(2 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Frog Stand','', 'time','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Frog Stand','', 'core',1.0),
('Frog Stand','', 'core.deep.transversus_abdominis',0.40),
('Frog Stand','', 'upper.forearms.flexors',0.40),
('Frog Stand','', 'core.abs.rectus_abdominis',0.20)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Lunge *(2 logs)*

```sql
INSERT INTO exercise_meta VALUES ('Lunge','', 'hybrid','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Lunge','', 'lower',1.0),
('Lunge','', 'lower.quads',1.0),
('Lunge','', 'lower.quads.vastus_lateralis',0.25),
('Lunge','', 'lower.quads.vastus_medialis',0.25),
('Lunge','', 'lower.quads.rectus_femoris',0.20),
('Lunge','', 'lower.glutes.gluteus_maximus',0.20),
('Lunge','', 'lower.hamstrings.semitendinosus',0.10)
ON CONFLICT DO NOTHING;
```


| recommended                                         | your_decision |
| --------------------------------------------------- | ------------- |
| **approve** — or `edit: merge with Step back Lunge` | approve       |


#### Bulgarian Split Squat / Glutes *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Bulgarian Split Squat','Glutes', 'load','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
-- inherits Bulgarian Split Squat base
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Plank / Feet Elevated *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Plank','Feet Elevated', 'time','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
-- inherits Plank base
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Reverse Crunch / Incline *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Reverse Crunch','Incline', 'reps','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
-- inherits Reverse Crunch base
```


| recommended                                                         | your_decision |
| ------------------------------------------------------------------- | ------------- |
| **approve** — preferred over separate `Incline Reverse Crunch` name | approve       |


#### Quad curl *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Quad curl','', 'load','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Quad curl','', 'lower',1.0),
('Quad curl','', 'lower.quads',1.0),
('Quad curl','', 'lower.quads.vastus_lateralis',0.30),
('Quad curl','', 'lower.quads.vastus_medialis',0.35),
('Quad curl','', 'lower.quads.rectus_femoris',0.35)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### L-Sit / Floor Raised *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('L-Sit','Floor Raised', 'time','major') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('L-Sit','Floor Raised', 'core',1.0),
('L-Sit','Floor Raised', 'core.hip_flexors',1.0),
('L-Sit','Floor Raised', 'core.abs.rectus_abdominis',0.60),
('L-Sit','Floor Raised', 'core.deep.transversus_abdominis',0.40)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Superman *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Superman','', 'reps','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Superman','', 'core',1.0),
('Superman','', 'core.spinal_erectors',1.0),
('Superman','', 'core.spinal_erectors.lumbar',0.60),
('Superman','', 'core.spinal_erectors.thoracic',0.40)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


#### Wall Sit *(1 log)*

```sql
INSERT INTO exercise_meta VALUES ('Wall Sit','', 'time','minor') ON CONFLICT DO UPDATE SET measurement_type=EXCLUDED.measurement_type, variation_type=EXCLUDED.variation_type;
INSERT INTO exercise_target_map VALUES
('Wall Sit','', 'lower',1.0),
('Wall Sit','', 'lower.quads',1.0),
('Wall Sit','', 'lower.quads.vastus_lateralis',0.30),
('Wall Sit','', 'lower.quads.vastus_medialis',0.40),
('Wall Sit','', 'lower.quads.rectus_femoris',0.30)
ON CONFLICT DO NOTHING;
```


| recommended | your_decision |
| ----------- | ------------- |
| **approve** | approve       |


---

## 5. Logged exercises still unmapped

From `02_logged_exercises.csv` where `mapping_status = unmapped`:


| name           | variation | logged | fix       | recommended | your_decision |
| -------------- | --------- | ------ | --------- | ----------- | ------------- |
| Frog Pump      | *(base)*  | 1      | §3 INSERT | **approve** | approve       |
| Frog Pump Hold | *(base)*  | 1      | §3 INSERT | **approve** | approve       |


After §3 + §4 applied, re-run:

```sql
SELECT * FROM vw_unmapped_logged_exercises ORDER BY log_count DESC;
```

Expected: empty.

---

## 6. Variation type changes

```sql
UPDATE exercise_meta SET variation_type = 'minor' WHERE name = 'Bench Press' AND variation = 'Flat';
UPDATE exercise_meta SET variation_type = 'minor' WHERE name = 'Chest Fly' AND variation = 'Flat';
UPDATE exercise_meta SET variation_type = 'major' WHERE name = 'One-Arm Row' AND variation = 'Pronated';
UPDATE exercise_meta SET variation_type = 'major' WHERE name = 'Heel Drop' AND variation = 'Bent Knee';
UPDATE exercise_meta SET variation_type = 'major' WHERE name = 'Heel Drop' AND variation = 'Bent Knee Single Leg';
```


| recommended       | your_decision |
| ----------------- | ------------- |
| **approve** all 5 | approve       |


---

## 7. Redundant mapping DELETE statements

```sql
DELETE FROM exercise_target_map WHERE name = 'Bench Press' AND variation = 'Flat';
DELETE FROM exercise_target_map WHERE name = 'Chest Fly' AND variation = 'Flat';
DELETE FROM exercise_target_map WHERE name = 'Bench Dips' AND variation = 'Feet Elevated';
DELETE FROM exercise_target_map WHERE name = 'Sit-Up' AND variation = 'Incline';
DELETE FROM exercise_target_map WHERE name = 'Sit-Up' AND variation = 'Decline';
DELETE FROM exercise_target_map WHERE name = 'Leg raises' AND variation = 'Incline';
DELETE FROM exercise_target_map WHERE name = 'Side Plank with Hip Drops' AND variation = 'Elevated';
DELETE FROM exercise_target_map WHERE name = 'Heel Drop' AND variation = 'Single Leg';
DELETE FROM exercise_target_map WHERE name = 'Side-Lying Hip Abduction' AND variation = 'Bent Knee';
```


| recommended       | your_decision |
| ----------------- | ------------- |
| **approve** all 9 | approve       |


---

## Priority order (recommended apply sequence)

1. §6 variation type changes
2. §7 delete redundant mappings
3. §3 Frog Pump / Frog Pump Hold (fixes live unmapped logs)
4. §4 high-volume missing meta (Pistol Squat, Finger Rolls, Squat, Toe Lifts, Side Plank)
5. §4 remainder + §3 catalog-only entries
6. §3b incomplete fixes

