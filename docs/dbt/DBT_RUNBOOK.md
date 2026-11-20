# dbt runbook

Prerequisites: complete the cloud foundation in `docs/cloud/CLOUD_RUNBOOK.md`,
load the accepted Sales/Review CSVs into Snowflake RAW, and grant the transform
role the updated `sql/snowflake/bootstrap.sql` privileges. The versioned
`dbt/profiles.yml` contains environment lookups only; it stores no password.
The optional cloud image installs dbt in a separate virtual environment so
its protobuf requirements do not alter the Airflow interpreter.

Offline validation without credentials:

```powershell
$files = @('-f','docker-compose.yml','-f','docker-compose.devops.yml','-f','docker-compose.airflow.yml')
docker compose @files -f docker-compose.cloud.yml --profile airflow build airflow
docker run --rm --entrypoint /home/airflow/dbt-venv/bin/dbt foody-airflow-cloud:local parse --project-dir /app/dbt --profiles-dir /app/dbt --no-partial-parse
docker run --rm --entrypoint /home/airflow/dbt-venv/bin/dbt foody-airflow-cloud:local ls --project-dir /app/dbt --profiles-dir /app/dbt
```

For live Snowflake, configure `.env.cloud` privately with `AWS_REGION`,
`FOODY_S3_BUCKET`, AWS credentials via the SDK chain, `SNOWFLAKE_ACCOUNT`,
`SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ROLE=FOODY_INGEST_ROLE`
for RAW ingestion, `SNOWFLAKE_DBT_ROLE=FOODY_TRANSFORM_ROLE` for dbt,
`SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, and
`FOODY_CLOUD_DBT_ENABLED=true`. The same Snowflake user must be granted both
the ingest and transform roles; each step selects its own least-privilege
role. Do not grant the read-only AI role write access.

Run dbt through the cloud Compose overlay so `target/` and logs persist:

```powershell
$files = @('-f','docker-compose.yml','-f','docker-compose.devops.yml','-f','docker-compose.airflow.yml','-f','docker-compose.cloud.yml')
docker compose @files --profile airflow run --rm --no-deps --entrypoint /home/airflow/dbt-venv/bin/dbt airflow deps --project-dir /app/dbt --profiles-dir /app/dbt
docker compose @files --profile airflow run --rm --no-deps --entrypoint /home/airflow/dbt-venv/bin/dbt airflow debug --project-dir /app/dbt --profiles-dir /app/dbt
docker compose @files --profile airflow run --rm --no-deps --entrypoint /home/airflow/dbt-venv/bin/dbt airflow run --project-dir /app/dbt --profiles-dir /app/dbt
docker compose @files --profile airflow run --rm --no-deps --entrypoint /home/airflow/dbt-venv/bin/dbt airflow source freshness --project-dir /app/dbt --profiles-dir /app/dbt
docker compose @files --profile airflow run --rm --no-deps --entrypoint /home/airflow/dbt-venv/bin/dbt airflow test --project-dir /app/dbt --profiles-dir /app/dbt
docker compose @files --profile airflow run --rm --no-deps --entrypoint /home/airflow/dbt-venv/bin/dbt airflow docs generate --project-dir /app/dbt --profiles-dir /app/dbt
```

The commands above need network access to Snowflake. The Compose cloud
overlay persists `run_results.json`, logs and generated docs under ignored
`outputs/dbt/target` and `logs/dbt`. An explicit
`dbt run --full-refresh` rebuilds only cloud incremental models from RAW;
review its cost and the Review content-ID policy first. The local PostgreSQL
and Review RAG paths are not rebuilt by dbt.
