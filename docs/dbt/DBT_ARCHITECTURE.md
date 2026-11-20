# dbt architecture and lineage

```text
FOODY.RAW.SALES_SOURCE ──→ stg_sales ──→ fact_order ──→ daily Sales
                                  └──→ dim_restaurant     ├── weekly Sales
FOODY.RAW.REVIEWS_SOURCE → stg_reviews → fact_review      ├── monthly Sales
                                  └──→ dim_restaurant     └── Sales summary
                                                 fact_review → monthly Reviews
```

The project lives in `dbt/`. `source()` declares RAW inputs; `ref()` defines
model lineage. A project macro maps custom schemas directly to `STAGING` and
`MART` instead of prefixing the profile's schema. No dbt package dependency,
seed, snapshot, or local PostgreSQL adapter was needed.

Staging and fact models use Snowflake incremental `merge` with stable
`order_id`/`review_id` keys. Incremental filters select source rows whose
`LOADED_AT` is at or after the destination's latest arrival; the merge makes
same-timestamp reruns idempotent. Deterministic row ranking chooses the newest
RAW version for each key. `dim_restaurant` is a small table rebuild; the
analytical marts are views over the facts. A full refresh rebuilds cloud
staging/facts from all RAW batches and never touches PostgreSQL or RAG.

Changed Review text creates a new content-derived Review ID; this RAW-only
phase has no deletion/CDC feed to retract a prior Review fact. A future cloud
CDC policy must address that case before treating the cloud mart as a full
replacement for the accepted local Review mart.

Optional cloud Airflow path:

```text
detect_source → validate_source → upload_s3 → load_snowflake_raw
  → dbt_run → dbt_test → quality_gate → publish
```

`FOODY_CLOUD_DBT_ENABLED=true` is required before the cloud DAG starts.
It is paused/manual and has one active run. The accepted local Airflow DAG
and PostgreSQL serving path remain separate.
