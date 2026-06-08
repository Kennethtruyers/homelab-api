# Exercise metadata review workflow

## Steps

1. **Export** — run `./export.sh` (or queries below) against the `fitness` DB
2. **Review** — fill `your_decision` in `proposals/*.md`
3. **Audit** — `python3 workouts/metadata/audit_mappings.py` (validates seed before deploy)
4. **Deploy** homelab-api — init() upserts meta, inserts new mappings/taxonomy, refreshes views
5. **Cleanup** — `psql "${POSTGRES_CON}fitness" -f migrations/apply-approved-changes.sql` (deletes stale rows init can't remove)

## Prerequisites

```bash
export POSTGRES_CON="postgresql://user:pass@host:5432/"   # must end with /
cd homelab-api/workouts/metadata
./export.sh
```

## Diagnostic views (after app restart / init)

```sql
SELECT * FROM vw_unmapped_logged_exercises ORDER BY log_count DESC;
SELECT * FROM vw_orphan_meta ORDER BY name, variation;
SELECT * FROM vw_incomplete_meta_mappings;
```

## Export queries

See [export.sh](export.sh) for copy-paste `\copy` commands.
