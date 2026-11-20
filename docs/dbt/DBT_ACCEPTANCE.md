# dbt transformation acceptance — 2026-11-07

Status: **LIVE_DBT_ACCEPTANCE_PENDING**. No Snowflake credentials or live RAW
tables were available. No live `dbt debug`, `dbt run`, `dbt test` or
`dbt docs generate` result, Snowflake mart count or warehouse query ID is
claimed. Cloud foundation remains `LIVE_CLOUD_ACCEPTANCE_PENDING`.

Offline acceptance: the pinned isolated runtime was built; both its dbt and
Airflow interpreters passed `pip check`. `dbt parse --no-partial-parse` passed
without a Snowflake connection. `dbt ls` discovered **10 models, 65 data
tests, 3 sources** and the expected source → staging → fact → mart lineage.
The cloud Airflow DAG was not triggered; its dbt mode is disabled by default.

Repository checks: focused cloud/dbt/Airflow tests **20 passed**; full pytest
**479 passed** (one third-party deprecation warning); Ruff **PASS**;
`compileall -q src app scripts dags` **PASS**; base plus cloud Compose
`config --quiet` **PASS**; `demo-preflight` **PASS**. Both local and cloud
Airflow DAGs imported from the optional image with no import errors. The
restricted Windows test runtime stalled on an existing crawler asyncio case;
the same case and full suite passed outside that restriction.

Pending live acceptance: complete S3/Snowflake RAW loading, run `dbt deps`,
`dbt debug`, `dbt run`, `dbt source freshness`, `dbt test`, and
`dbt docs generate`; capture run IDs, failures, materialized model/test counts,
RAW-to-staging/fact row reconciliation, Sales mart totals, Review fact count
and generated lineage artifacts. The exact commands are in `DBT_RUNBOOK.md`.
