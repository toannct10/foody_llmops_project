# Airflow local runbook

From the repository root, with Docker Desktop and the existing Review-2
PostgreSQL service available:

```powershell
$files = @('-f','docker-compose.yml','-f','docker-compose.devops.yml','-f','docker-compose.airflow.yml')
$env:GIT_SHA = (git rev-parse HEAD)
docker compose @files --profile airflow config --quiet
docker compose @files --profile airflow build airflow
docker compose @files --profile airflow up -d airflow
docker compose @files --profile airflow exec -T airflow airflow dags list
docker compose @files --profile airflow exec -T airflow airflow dags unpause foody_daily_batch
docker compose @files --profile airflow exec -T airflow airflow dags trigger -r manual__foody_acceptance foody_daily_batch
docker compose @files --profile airflow exec -T airflow airflow dags list-runs -d foody_daily_batch
docker compose @files --profile airflow exec -T airflow airflow tasks states-for-dag-run foody_daily_batch manual__foody_acceptance
```

The Airflow UI is at `http://127.0.0.1:8088`. Airflow standalone generates
local login credentials during initialization; inspect its startup logs
privately and never commit credentials. Leave the DAG unpaused for daily 02:00
Vietnam-time runs. `catchup=False` prevents historical backfill. Airflow
metadata and logs stay under `state/airflow/` and `logs/airflow/`; project
run summaries stay under `outputs/airflow/`.

The controlled quality-failure trigger is:

```powershell
docker compose @files --profile airflow exec -T airflow airflow dags trigger -r manual__foody_bad_schema -c '{"quality_fixture":"invalid_review_schema"}' foody_daily_batch
```

The fixture deliberately omits the Review `Address` column. The
`validate_source` task must fail and downstream tasks must not run. Do not
clear/retry it against production data. Inspect the Airflow task logs and the
corresponding run summary. The production sources remain untouched.
