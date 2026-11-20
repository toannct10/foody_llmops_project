# Cloud RAW architecture

```text
Accepted local Sales/Review CSVs
  → existing schema/ID/date/business-rule audits + SHA256
  → immutable hash-addressed S3 CSV objects + JSON manifests
  → Snowflake external stage and strict CSV file format
  → COPY into temporary RAW-shaped table
  → row/ID/date/hash reconciliation
  → transactional RAW insert + LOAD_AUDIT
```

`src/cloud_foundation.py` is the reusable implementation; `scripts/cloud_foundation.py`
is its CLI. The separate `foody_cloud_raw` Airflow DAG is paused by default,
manual, sequential and credential-optional at import time. Its graph is
`detect_source → validate_source → upload_s3 → load_snowflake_raw`. The accepted
`foody_daily_batch` DAG is unchanged. Both call the same source audits, so
there is no second schema contract. The joint batch ID uses the existing
local Airflow Review-hash/Sales-hash ordering. AWS/Snowflake SDKs are lazy imports from
`requirements-cloud.txt`, installed only in the optional cloud image.

Snowflake RAW is a cloud analytical landing zone. PostgreSQL remains the
current local/demo warehouse. The optional dbt transformation project now
defines STAGING and MART models; see `docs/dbt/DBT_ARCHITECTURE.md`. Live
Snowflake and dbt acceptance remain pending credentials.

The local run audit is `outputs/cloud/runs/<batch_id>.json`; Airflow also keeps
task logs, XCom summaries and query IDs. No query text, credentials or customer
comment text is written to the run audit. Failures record an error category.
