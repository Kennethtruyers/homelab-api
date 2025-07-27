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


