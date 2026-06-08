#!/usr/bin/env bash
# Export exercise metadata for review. Requires POSTGRES_CON (trailing slash).
set -euo pipefail

if [[ -z "${POSTGRES_CON:-}" ]]; then
  echo "Set POSTGRES_CON (e.g. postgresql://user:pass@host:5432/)"
  exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/exports"
mkdir -p "$OUT"

DB="${POSTGRES_CON}fitness"

psql "$DB" -c "\copy (
  SELECT
    em.name,
    em.variation,
    em.measurement_type,
    em.variation_type,
    COUNT(DISTINCT etm.target_path) AS mapping_rows,
    COUNT(DISTINCT etm.target_path) FILTER (
      WHERE array_length(string_to_array(etm.target_path, '.'), 1) = 3
    ) AS muscle_level_rows,
    CASE
      WHEN COUNT(etm.target_path) = 0 THEN 'no_mapping'
      WHEN COUNT(etm.target_path) FILTER (
        WHERE array_length(string_to_array(etm.target_path, '.'), 1) = 3
      ) = 0 THEN 'incomplete'
      ELSE 'ok'
    END AS mapping_status
  FROM exercise_meta em
  LEFT JOIN exercise_target_map etm
    ON etm.name = em.name AND etm.variation = em.variation
  GROUP BY em.name, em.variation, em.measurement_type, em.variation_type
  ORDER BY em.name, em.variation
) TO '$OUT/01_exercise_meta_status.csv' CSV HEADER"

psql "$DB" -c "\copy (
  WITH logged AS (
    SELECT
      e.name,
      COALESCE(e.variation, '') AS variation,
      w.date
    FROM exercises e
    JOIN workouts w ON w.notion_id = e.workout_notion_id
  )
  SELECT
    l.name,
    l.variation,
    COUNT(*) AS log_count,
    MIN(l.date) AS first_logged,
    MAX(l.date) AS last_logged,
    em.variation_type,
    CASE
      WHEN em.name IS NULL THEN 'missing_meta'
      WHEN EXISTS (
        SELECT 1 FROM exercise_target_map m
        WHERE m.name = l.name AND m.variation = l.variation
      ) THEN 'explicit_mapping'
      WHEN em.variation_type = 'minor' AND l.variation <> ''
           AND EXISTS (
        SELECT 1 FROM exercise_target_map m
        WHERE m.name = l.name AND m.variation = ''
      ) THEN 'inherits_base'
      ELSE 'unmapped'
    END AS mapping_status
  FROM logged l
  LEFT JOIN exercise_meta em
    ON em.name = l.name AND em.variation = l.variation
  GROUP BY l.name, l.variation, em.variation_type, em.name
  ORDER BY log_count DESC, l.name, l.variation
) TO '$OUT/02_logged_exercises.csv' CSV HEADER"

psql "$DB" -c "\copy (
  SELECT name, variation, target_path, contribution
  FROM exercise_target_map
  ORDER BY name, variation, target_path
) TO '$OUT/03_current_mappings.csv' CSV HEADER"

psql "$DB" -c "\copy (
  SELECT path, name, parent_path,
         array_length(string_to_array(path, '.'), 1) AS depth
  FROM muscle_taxonomy
  ORDER BY path
) TO '$OUT/04_muscle_taxonomy.csv' CSV HEADER"

echo "Exported to $OUT/"
