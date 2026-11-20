# Local monitoring runbook

From the repository root, validate syntax and start only the existing services needed for the local demo:

```powershell
$files = @('-f','docker-compose.yml','-f','docker-compose.devops.yml','-f','docker-compose.airflow.yml')
docker compose @files --profile airflow config --quiet
docker compose @files --profile airflow build rag-backend
docker compose @files --profile airflow up -d rag-backend streamlit prometheus grafana airflow
docker compose @files --profile airflow ps
```

Check `http://127.0.0.1:8000/health`, `:8501/_stcore/health`, `:8193/health`, `:8088/health`, `:9090/-/healthy` and `:3000/api/health`. Query `http://127.0.0.1:9090/api/v1/query?query=foody_service_health` and `/api/v1/alerts`; view the provisioned Foody dashboard and the existing System Monitor. Backend `/metrics` refreshes Airflow ledger and resource gauges. The Airflow service is optional for ordinary local demos; set `FOODY_AIRFLOW_MONITOR_ENABLED=true` only when it is intentionally running and visible to backend.

Use an existing accepted run ledger rather than rerunning ingestion just to display pipeline status. For live smoke, submit one Review and one Sales Text-to-SQL question through the existing UI, then verify the corresponding Prometheus counters and SQLite events. Do not run a model benchmark. Alert history is captured when System Monitor polls Prometheus; retention is 30 days. The SQLite file remains local, ignored by Git. Refresh the dashboard after a scrape interval (15 seconds). Cloud status stays pending.
