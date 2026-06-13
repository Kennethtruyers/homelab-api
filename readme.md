# Homelab API

## Garmin

- `/garmin/fetch?start_date=<date>&end_date=<date>`: Fetches activities and stores them in postgres

## Nutrition

- `/nutrition/day`: Accepts a JSON payload for logging a daily food log

## Tanita

- `/tanita/scrape`: Scrapes the last day from MyTanita
- `/tanita/ingest-csv`: Downloads and ingests the complete CSV from MyTanita

## Workouts

- `/workouts/exercises/added`: Webhook for when an exercises is added
- `/workouts/exercises/changed`: Webhook for when an exercises is changed
- `/workouts/exercises/deleted`: Webhook for when an exercises is deleted

- `/workouts/workouts/added`: Webhook for when a workout is added
- `/workouts/workouts/changed`: Webhook for when a workout is changed
- `/workouts/workouts/deleted`: Webhook for when a workout is deleted

- `/workouts/sync`: Load all workouts and reingests to Postgres

## Cashflow

App to manage finance forecast

## IPTV

Filtered M3U playlists for Dispatcharr. Rules live in `iptv/rules.yaml`.

- `GET /iptv/playlists` — list configured playlists
- `GET /iptv/live.m3u` — filtered live playlist
- `GET /iptv/movies.m3u` — filtered movies playlist
- `GET /iptv/series.m3u` — filtered series playlist
- `GET /iptv/{name}.m3u?refresh=true` — bypass upstream cache
- `GET /iptv/{name}.m3u?include_stats=true` — add `X-IPTV-*` count headers
- `POST /iptv/cache/invalidate` — clear upstream cache

Env vars:

- `IPTV_UPSTREAM_URL` — provider M3U URL (required in cluster; provisioned via `iptv-env` secret)
- `IPTV_CACHE_TTL_SECONDS` — upstream cache TTL (default `3600`)
- `IPTV_RULES_PATH` — optional override for rules file
- `IPTV_FETCH_TIMEOUT_SECONDS` — upstream fetch timeout (default `300`)

### Adding a rule

Edit `iptv/rules.yaml` under the playlist's `rules` list. Rules are first-match-wins.

```yaml
- name: my new rule
  action: exclude   # or include
  field: group      # or name
  pattern: '(?i)PLUTO'
```

Redeploy (or restart pod) after rule changes unless rules are mounted from a ConfigMap.