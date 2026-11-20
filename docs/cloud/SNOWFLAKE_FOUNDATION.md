# Snowflake foundation

`sql/snowflake/bootstrap.sql` is an idempotent template. Render it with
`python -m scripts.cloud_foundation bootstrap-sql`; an authorized bootstrap
role may execute it using the CLI `bootstrap` command. It creates an X-Small
auto-suspending warehouse (`FOODY_WH`), database (`FOODY`), schemas `RAW`,
`STAGING`, `MART`, strict UTF-8 CSV format, external S3 stage, two RAW tables,
and `LOAD_AUDIT`. Names are configurable and validated as SQL identifiers.

The external storage integration (`FOODY_S3_INTEGRATION` by default) is an
**administrator prerequisite**: it needs an AWS IAM role ARN and Snowflake's
external-ID trust handshake. This repository does not invent or create that
role. Confirm its `STORAGE_ALLOWED_LOCATIONS` includes the configured S3 RAW
prefix, then inspect the rendered stage URL before bootstrap.

RAW tables preserve the six CSV fields as `VARCHAR` in their original order.
Review names map to SQL-safe columns: `Review Time→REVIEW_TIME`,
`RestaurantID→RESTAURANT_ID`, `Restaurant Name→RESTAURANT_NAME`.
Both tables append `SOURCE_FILE`, `SOURCE_HASH`, `BATCH_ID`, `LOADED_AT`.
`LOAD_AUDIT` records source, batch/hash, S3 key, row/rejection counts and
Snowflake COPY/insert query IDs. No Review text is sent to logs.

Roles: `FOODY_INGEST_ROLE` gets stage/format usage and SELECT/INSERT only on
RAW/audit, plus `CREATE TABLE` in RAW for the session-scoped temporary COPY
table; `FOODY_TRANSFORM_ROLE` gets RAW read and creation rights in STAGING
and MART for the future phase; `FOODY_AI_READONLY_ROLE` gets USAGE and future
MART SELECT, no ingest or RAW customer-text access. Assign roles to users
separately. Snowflake primary/unique keys on standard tables are not an
enforced deduplication mechanism; the single-run Airflow limit and explicit
batch-audit checks enforce this workflow's idempotency.
