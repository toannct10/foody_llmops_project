# Security acceptance — 2026-11-07

## Local acceptance

Static and focused tests cover the PostgreSQL role/view allowlist, optional DSN fallback, Snowflake grants, IAM scope, tracked-secret scan, SQL attack rejection, model registry bounds, sanitized API errors and content-free SQLite audit events. The existing SQL executor still enforces read-only transactions, timeout, result limit and verified facts. Focused security/Text-to-SQL/gateway/cloud/dbt/Airflow tests: **86 passed** before the final audit-ID test; the final security-only rerun was **11 passed**, and cloud/dbt/Airflow rerun was **20 passed**. Final full pytest: **490 passed**, one third-party deprecation warning. Ruff, compileall, secret scan, base/DevOps/cloud Compose validation and demo-preflight: **PASS**.

**LIVE_POSTGRES_READONLY_PENDING:** the optional role has not yet been installed into a running local PostgreSQL instance or probed with SELECT/write attempts. Until configured, the accepted demo uses its compatibility DSN with transaction-level read-only protection.

## Cloud design and live acceptance

Role and IAM design is implemented and statically checked. **LIVE_CLOUD_ACCEPTANCE_PENDING** and **LIVE_DBT_ACCEPTANCE_PENDING** remain. No AWS/Snowflake role assumption, denied-action probe, dbt execution, cloud run ID or mart query is claimed.

## Remaining work

Apply and probe the PostgreSQL role, rotate workstation demo passwords before sharing a deployment, verify Snowflake existing-installation revocations, and perform AWS/Snowflake allow/deny probes when credentials are available.
