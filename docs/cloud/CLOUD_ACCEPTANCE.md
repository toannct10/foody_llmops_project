# Cloud foundation acceptance — 2026-11-07

Status: **LIVE_CLOUD_ACCEPTANCE_PENDING**.

The source files were inspected locally: Sales 400,000 rows, 36,095,547 bytes,
SHA256 `6ba29ff7641b75a623a1e5e8a83b65d3578ba2eda01c443bf9eb8e3f451435cf`;
Review 15,639 rows, 7,514,232 bytes, SHA256
`4a5e4cc1d7b1f9eb9b2d392e551545e6c3b9082bbc8dfe01ddf17002aea8e787`.
The S3 and Snowflake SDK calls are covered by offline mocks. No AWS region,
bucket, AWS identity, Snowflake account/user/authentication, or storage
integration was configured in this session. No S3 object or Snowflake table
was claimed to exist, and no live query/load ID is reported.

Local validation: focused cloud + local Airflow tests **15 passed**; full
pytest **474 passed, 1 warning**; Ruff **PASS**; compileall **PASS**; local
and cloud Compose configurations **PASS**; demo-preflight **PASS**. The
optional cloud Airflow image built and `pip check` found no broken
requirements. Airflow's `DagBag` imported both `foody_cloud_raw` and
`foody_daily_batch` with zero import errors. The cloud DAG was not run.
The prior local Airflow `ready.json` still names its accepted successful run.
The local Airflow/PostgreSQL containers were stopped during this phase, so a
live Airflow HTTP health check was not claimed; the services were not started
solely for this optional cloud change.

Pending live gates: provision scoped bucket/IAM and Snowflake storage
integration, run the bootstrap, upload both accepted CSVs, verify RAW counts
equal 400,000/15,639, inspect `LOAD_AUDIT` query IDs and hashes, then rerun
and confirm duplicate skips. Use `CLOUD_RUNBOOK.md` for exact commands.
