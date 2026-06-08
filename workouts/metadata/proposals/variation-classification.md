# Variation classification proposal

Data from `exports/01_exercise_meta_status.csv` and `exports/02_logged_exercises.csv` (2026-06-07).

## How to decide

Fill **your_decision** with one of:


| Value   | Meaning                                                               |
| ------- | --------------------------------------------------------------------- |
| `keep`  | Keep current `variation_type`                                         |
| `minor` | Change to minor — inherits `(name, '')` mapping when no explicit rows |
| `major` | Change to major — needs own muscle mapping                            |


**Recommended** column is the agent's suggestion. Leave **your_decision** blank until you've reviewed.

---

## Bicep Curl


| variation      | logged | current | recommended | mapping               | rationale                                  | your_decision |
| -------------- | ------ | ------- | ----------- | --------------------- | ------------------------------------------ | ------------- |
| *(base)*       | 2      | major   | **keep**    | ok                    | Standard curl; 50/50 long/short head       | keep          |
| Incline        | 12     | major   | **keep**    | ok                    | Long-head bias (70/30)                     | keep          |
| Hammer         | 3      | major   | **keep**    | ok                    | Brachialis/brachioradialis emphasis        | keep          |
| Hammer Incline | 26     | major   | **keep**    | ok                    | Most-logged curl variant; distinct mapping | keep          |
| Zottman        | 1      | major   | **keep**    | ok                    | Brachioradialis + rotation                 | keep          |
| Standing       | 0      | minor   | **keep**    | no_mapping → inherits | Same as base; not logged yet               | keep          |


**Options:** All `keep` unless you want Standing as `major` (if you plan distinct standing curl mapping).

---

## One-Arm Row


| variation       | logged | current | recommended | mapping               | rationale                                                   | your_decision |
| --------------- | ------ | ------- | ----------- | --------------------- | ----------------------------------------------------------- | ------------- |
| *(base)*        | 23     | minor   | **keep**    | ok                    | Default lat/rhomboid/posterior delt                         | keep          |
| Pronated        | 18     | minor   | **major**   | ok                    | Different lat/rhomboid/trap split — already has own mapping | major         |
| Flared          | 0      | minor   | **keep**    | no_mapping → inherits | Elbow path tweak                                            | keep          |
| Normal          | 0      | minor   | **keep**    | no_mapping → inherits | Same as base                                                | keep          |
| Flared Pronated | 0      | minor   | **keep**    | no_mapping → inherits | Inherit from base (not logged)                              | keep          |


**Options for Pronated:** `keep` (minor, inherits base — wrong, has explicit mapping) · `**major`** (correct — mapping differs) · `minor` (only if you delete Pronated mapping and merge into base).

---

## Bench Press


| variation | logged | current | recommended | mapping        | rationale                             | your_decision |
| --------- | ------ | ------- | ----------- | -------------- | ------------------------------------- | ------------- |
| *(base)*  | 53     | major   | **keep**    | ok             | Flat/sternal pec                      | keep          |
| Flat      | 0      | major   | **minor**   | ok (duplicate) | Not logged; identical mapping to base | minor         |
| Incline   | 17     | major   | **keep**    | ok             | Clavicular pec + anterior delt        | keep          |


**Options for Flat:** `**minor*`* (delete duplicate rows, inherit) · `keep` (keep redundant major + duplicate rows) · `major` (only if you later add distinct flat mapping).

---

## Chest Fly


| variation | logged | current | recommended | mapping        | rationale                 | your_decision |
| --------- | ------ | ------- | ----------- | -------------- | ------------------------- | ------------- |
| *(base)*  | 17     | minor   | **keep**    | ok             | Sternal pec fly           | keep          |
| Flat      | 6      | major   | **minor**   | ok (duplicate) | Identical mapping to base | keep          |


**Options for Flat:** `**minor*`* · `keep` · `major`.

---

## Bench Dips


| variation     | logged | current | recommended | mapping        | rationale                           | your_decision |
| ------------- | ------ | ------- | ----------- | -------------- | ----------------------------------- | ------------- |
| *(base)*      | 12     | minor   | **keep**    | ok             | Triceps                             | keep          |
| Feet Elevated | 6      | minor   | **keep**    | ok (duplicate) | Same muscles; delete duplicate rows | keep          |


**Options for Feet Elevated:** `**keep*`* (minor + delete duplicate mapping rows) · `major` (only if feet-elevated shifts emphasis materially — current mapping says no).

---

## Sit-Up


| variation | logged | current | recommended | mapping        | rationale             | your_decision |
| --------- | ------ | ------- | ----------- | -------------- | --------------------- | ------------- |
| *(base)*  | 2      | minor   | **keep**    | ok             | Rectus abdominis      | keep          |
| Incline   | 4      | minor   | **keep**    | ok (duplicate) | Same mapping; inherit | keep          |
| Decline   | 2      | minor   | **keep**    | ok (duplicate) | Same mapping; inherit | keep          |


**Options:** All `**keep*`* + delete duplicate rows in mapping-gaps §2.

---

## Leg raises


| variation | logged | current | recommended | mapping        | rationale             | your_decision |
| --------- | ------ | ------- | ----------- | -------------- | --------------------- | ------------- |
| *(base)*  | 9      | minor   | **keep**    | ok             | Hip flexors + rectus  | keep          |
| Incline   | 2      | minor   | **keep**    | ok (duplicate) | Same mapping; inherit | keep          |


---

## Side Plank with Hip Drops


| variation | logged | current | recommended | mapping        | rationale             | your_decision |
| --------- | ------ | ------- | ----------- | -------------- | --------------------- | ------------- |
| *(base)*  | 13     | minor   | **keep**    | ok             | Obliques + TVA        | keep          |
| Elevated  | 3      | minor   | **keep**    | ok (duplicate) | Same mapping; inherit | keep          |


---

## Heel Drop


| variation            | logged | current | recommended | mapping        | rationale                               | your_decision |
| -------------------- | ------ | ------- | ----------- | -------------- | --------------------------------------- | ------------- |
| *(base)*             | 22     | minor   | **keep**    | ok             | Gastroc + soleus                        | keep          |
| Single Leg           | 2      | minor   | **keep**    | ok (duplicate) | Unilateral; same pattern                | keep          |
| Bent Knee            | 1      | minor   | **major**   | ok             | 80% soleus — different exercise         | keep          |
| Bent Knee Single Leg | 1      | minor   | **major**   | ok             | Soleus-dominant, unilateral             | keep          |
| Unsupported          | 2      | —       | **minor**   | missing_meta   | Not in catalog — add meta, inherit base | minor         |


**Options for Bent Knee / Bent Knee Single Leg:** `**major*`* · `keep` (wrong — masks different muscle emphasis).

**Unsupported:** Add to meta as minor variation of Heel Drop (see mapping-gaps §4).

---

## Side-Lying Hip Abduction


| variation | logged | current | recommended | mapping        | rationale             | your_decision |
| --------- | ------ | ------- | ----------- | -------------- | --------------------- | ------------- |
| *(base)*  | 7      | minor   | **keep**    | ok             | Glute med/min         | keep          |
| Bent Knee | 2      | minor   | **keep**    | ok (duplicate) | Same mapping; inherit | keep          |


---

## Pull-up


| variation   | logged | current | recommended | mapping               | rationale                                               | your_decision |
| ----------- | ------ | ------- | ----------- | --------------------- | ------------------------------------------------------- | ------------- |
| *(base)*    | 59     | minor   | **keep**    | ok                    | Lat + biceps + posterior delt                           | keep          |
| Normal Grip | 0      | minor   | **keep**    | no_mapping → inherits | Not logged; inherit from base                           | keep          |
| Wide Grip   | 2      | —       | **major**   | missing_meta          | Wider grip = more lat, less biceps — add meta + mapping | major         |


**Options for Wide Grip:** `**major`** (own mapping) · `minor` (inherit base — understates lat emphasis).

---

## Bulgarian Split Squat


| variation | logged | current | recommended | mapping      | rationale                             | your_decision |
| --------- | ------ | ------- | ----------- | ------------ | ------------------------------------- | ------------- |
| *(base)*  | 14     | major   | **keep**    | ok           | Quads + glutes; already mapped        | keep          |
| Glutes    | 1      | —       | **minor**   | missing_meta | Stance emphasis; inherit base mapping | minor         |


---

## Pistol Squat


| variation | logged | current | recommended | mapping      | rationale                                | your_decision |
| --------- | ------ | ------- | ----------- | ------------ | ---------------------------------------- | ------------- |
| *(base)*  | 14     | —       | **major**   | missing_meta | Single-leg squat; needs full mapping     | major         |
| Assisted  | 1      | —       | **minor**   | missing_meta | Same pattern, reduced load; inherit base | minor         |


---

## Side Plank


| variation  | logged | current | recommended | mapping      | rationale                                 | your_decision |
| ---------- | ------ | ------- | ----------- | ------------ | ----------------------------------------- | ------------- |
| *(base)*   | 7      | —       | **major**   | missing_meta | Distinct from Side Plank with Hip Drops   | major         |
| Copenhagen | 3      | —       | **major**   | missing_meta | Adductors + obliques — different exercise | major         |


**Options for Side Plank (base):** `**major*`* (add own mapping) · `minor` (merge into Side Plank with Hip Drops in Notion — would need rename).

---

## Plank


| variation     | logged | current | recommended | mapping      | rationale                               | your_decision |
| ------------- | ------ | ------- | ----------- | ------------ | --------------------------------------- | ------------- |
| *(base)*      | 34     | minor   | **keep**    | ok           | TVA + rectus + obliques                 | keep          |
| Feet Elevated | 1      | —       | **minor**   | missing_meta | Slightly harder; same muscles — inherit | minor         |


---

## Reverse Crunch


| variation | logged | current | recommended | mapping      | rationale                                                                          | your_decision |
| --------- | ------ | ------- | ----------- | ------------ | ---------------------------------------------------------------------------------- | ------------- |
| *(base)*  | 36     | minor   | **keep**    | ok           | Hip flexors + rectus                                                               | keep          |
| Incline   | 1      | —       | **minor**   | missing_meta | Same as Incline Reverse Crunch meta row — add as variation, inherit Reverse Crunch | minor         |


**Options for Incline:** `**minor*`* (add `Reverse Crunch/Incline` meta, inherit) · merge Notion entry to existing `Incline Reverse Crunch` exercise name.

---

## Single-variation exercises in meta


| name                             | logged | current | recommended | mapping status | your_decision |
| -------------------------------- | ------ | ------- | ----------- | -------------- | ------------- |
| Ab Rollout                       | 1      | minor   | keep        | ok             | keep          |
| Bird dog plank                   | 2      | minor   | keep        | ok             | keep          |
| Crunch                           | 15     | minor   | keep        | ok             | keep          |
| Db Kickbacks                     | 5      | minor   | keep        | ok             | keep          |
| Dead Bug                         | 56     | minor   | keep        | ok             | keep          |
| Fingerboard Hang                 | 13     | minor   | keep        | ok             | keep          |
| Fire Hydrant                     | 25     | minor   | keep        | ok             | keep          |
| Floor Press                      | 0      | major   | keep        | no_mapping     | keep          |
| Front Raise                      | 1      | minor   | keep        | ok             | keep          |
| Glute Bridge                     | 7      | minor   | keep        | ok             | keep          |
| Hamstring Floor Curl             | 18     | major   | keep        | ok             | keep          |
| Hanging Leg Raise                | 4      | minor   | keep        | ok             | keep          |
| Hip Rotation Stretch             | 1      | minor   | keep        | ok             | keep          |
| Hip Thrust                       | 6      | major   | keep        | ok             | keep          |
| Hollow Hold                      | 17     | minor   | keep        | ok             | keep          |
| Incline Leg Raise                | 0      | major   | keep        | incomplete     | keep          |
| Incline Reverse Crunch           | 0      | minor   | keep        | no_mapping     | keep          |
| Kickbacks                        | 3      | minor   | keep        | ok             | keep          |
| Lat Pullover                     | 20     | minor   | keep        | ok             | keep          |
| Leg Raise + Reverse Crunch       | 4      | minor   | keep        | ok             | keep          |
| Lying Shoulder External Rotation | 12     | minor   | keep        | ok             | keep          |
| Lying Shoulder Internal Rotation | 7      | minor   | keep        | ok             | keep          |
| Pelvic Tilt                      | 1      | minor   | keep        | ok             | keep          |
| Prone Y Raises                   | 1      | minor   | keep        | ok             | keep          |
| Push-up                          | 6      | minor   | keep        | ok             | keep          |
| Push-up wide feet up             | 0      | minor   | keep        | no_mapping     | keep          |
| RDL                              | 4      | major   | keep        | ok             | keep          |
| Rear Delt Row                    | 11     | minor   | keep        | ok             | keep          |
| Reverse Curl                     | 3      | minor   | keep        | ok             | keep          |
| Reverse Fly                      | 12     | minor   | keep        | ok             | keep          |
| Reverse wrist curl               | 27     | minor   | keep        | ok             | keep          |
| Russian Twist                    | 5      | minor   | keep        | ok             | keep          |
| Scapular pull-up                 | 7      | minor   | keep        | ok             | keep          |
| Scapular row                     | 1      | minor   | keep        | ok             | keep          |
| Seated Forearm Curl              | 0      | minor   | keep        | ok             | keep          |
| Shoulder Press                   | 63     | minor   | keep        | ok             | keep          |
| Shrug                            | 2      | minor   | keep        | ok             | keep          |
| Side Bend                        | 13     | minor   | keep        | ok             | keep          |
| Step back Lunge                  | 1      | minor   | keep        | ok             | keep          |
| Straight Leg Stretch             | 1      | minor   | keep        | incomplete     | keep          |
| Supine Pelvic Tilts              | 1      | minor   | keep        | ok             | keep          |
| Wall/Floor Glides                | 1      | minor   | keep        | ok             | keep          |
| Wrist Curl                       | 15     | major   | keep        | ok             | keep          |
| Frog Pump                        | 1      | minor   | keep        | no_mapping     | keep          |
| Frog Pump Hold                   | 1      | minor   | keep        | no_mapping     | keep          |


All single-variation rows: `**keep**` unless noted in mapping-gaps.md.

---

## Logged exercises — not in meta (need new catalog entries)


| name                  | variation     | logged | recommended type | your_decision |
| --------------------- | ------------- | ------ | ---------------- | ------------- |
| Pistol Squat          | *(base)*      | 14     | major            | major         |
| Pistol Squat          | Assisted      | 1      | minor            | minor         |
| Finger Rolls          | *(base)*      | 13     | major            | major         |
| Squat                 | *(base)*      | 10     | major            | major         |
| Toe Lifts             | *(base)*      | 8      | minor            | minor         |
| Side Plank            | *(base)*      | 7      | major            | major         |
| Side Plank            | Copenhagen    | 3      | major            | major         |
| Chest supported row   | *(base)*      | 5      | major            | major         |
| Reverse Lunge         | *(base)*      | 3      | major            | major         |
| Pull-up               | Wide Grip     | 2      | major            | major         |
| Heel Drop             | Unsupported   | 2      | minor            | minor         |
| Frog Stand            | *(base)*      | 2      | major            | major         |
| Lunge                 | *(base)*      | 2      | major            | major         |
| Bulgarian Split Squat | Glutes        | 1      | minor            | minor         |
| Plank                 | Feet Elevated | 1      | minor            | minor         |
| Reverse Crunch        | Incline       | 1      | minor            | minor         |
| Quad curl             | *(base)*      | 1      | major            | major         |
| L-Sit                 | Floor Raised  | 1      | major            | major         |
| Superman              | *(base)*      | 1      | minor            | minor         |
| Wall Sit              | *(base)*      | 1      | minor            | minor         |


See mapping-gaps.md §4 for proposed muscle mappings.

---

## Summary of recommended type changes


| name        | variation            | current → recommended |
| ----------- | -------------------- | --------------------- |
| Bench Press | Flat                 | major → **minor**     |
| Chest Fly   | Flat                 | major → **minor**     |
| One-Arm Row | Pronated             | minor → **major**     |
| Heel Drop   | Bent Knee            | minor → **major**     |
| Heel Drop   | Bent Knee Single Leg | minor → **major**     |


All other existing meta entries: **keep**.