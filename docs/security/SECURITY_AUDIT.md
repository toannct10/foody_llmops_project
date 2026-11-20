# Security audit — 2026-11-07

## Existing controls

- Local PostgreSQL is bound to `127.0.0.1:5433`; application SQL uses parameters. The Text-to-SQL path already pre-checks unsafe questions, validates one PostgreSQL SELECT AST against approved tables/columns/functions, enforces a restaurant scope or explicit global ranking, limits rows/time, starts a read-only transaction, and verifies returned facts.
- PostgreSQL migration owner `foody` loads data and builds marts. The default local demo DSN uses the documented demo-only password; it is not a production credential.
- Snowflake bootstrap separates ingest, transform and AI roles. S3 application IAM is prefix-scoped and excludes delete; Snowflake storage integration has a separate trust identity.
- Model candidate IDs come from a frozen registry; users cannot submit a model path through the UI. SQLite LLMOps telemetry records bounded metadata. CI has `contents: read`.
- `.env`, `.env.*` other than `.env.example`, model weights, local databases and runtime artifacts are ignored by Git.

## Gaps addressed here

- Text-to-SQL previously reused the loader's write-capable PostgreSQL login, despite a read-only transaction. An optional `foody_ai_readonly` identity and isolated `ai_sales` view schema now provide a database privilege boundary.
- The earlier Snowflake bootstrap granted the AI role SELECT on *future* MART tables/views, including future facts. New installs grant no blanket MART SELECT; a post-dbt allowlist grants only approved views and the restaurant dimension. Existing installations need the documented revocation migration.
- API exception strings and local Airflow failure reasons could expose internal paths or credentials. API errors now use a generic response; the Airflow ledger records exception class only.
- Security failures previously lacked a consistent category-only SQLite event. The new helper records component, status, sanitized category and optional bounded request/run ID. A lightweight CI scan detects tracked private artifacts and high-confidence credentials.

## Remaining live checks

The read-only PostgreSQL role has not been enabled or tested against a live local database in this change. AWS IAM, Snowflake RBAC and secret-provider integration cannot be accepted live without cloud credentials. A static scanner cannot replace repository history/host secret scanning. Existing local demo credentials must be replaced for any shared deployment.
