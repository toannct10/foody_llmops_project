# Foody cloud foundation audit — 2026-11-07

The accepted local path is CSV → strict Sales/Review audits → PostgreSQL facts
and marts → frozen Review enrichment → Chroma/BM25 → Streamlit. The local
`foody_daily_batch` Airflow DAG is accepted and remains the demo path. No
working AWS/Snowflake ingestion or cloud credentials were present at audit.
The old Shopee Databricks code is unrelated to these Foody sources.

| Source | Accepted file | Rows | SHA256 | Size |
|---|---|---:|---|---:|
| Sales | `data/foody/source/order_cleaning.csv` | 400,000 | `6ba29ff7641b75a623a1e5e8a83b65d3578ba2eda01c443bf9eb8e3f451435cf` | 36,095,547 bytes |
| Review | `data/foody/source/data_2025_2026.csv` | 15,639 | `4a5e4cc1d7b1f9eb9b2d392e551545e6c3b9082bbc8dfe01ddf17002aea8e787` | 7,514,232 bytes |

The Review accepted manifest is `data/foody/processed/reviews_2025_2026_manifest.json`
(`review_2025_2026_v1`). The RAW cloud load preserves **source rows**, including
the 183 exact Review duplicates. The deduplicated 15,456-row local Review mart
is a separate downstream product. Sales has six columns: `order_id`,
`order_date`, `sales_amount`, `order_status`, `restaurant_id`,
`restaurant_name`. Review has six columns: `Review Time`, `Rating`, `Comment`,
`RestaurantID`, `Restaurant Name`, `Address`.
Sales dates span 2025-01-01 through 2026-12-31; the existing local live
analytics already exclude future-dated orders. RAW preserves them as source
evidence. Review dates span 2025-01-01 through 2026-06-30.

The cloud addition is an optional `foody_cloud_raw` DAG and CLI, an S3 prefix,
and Snowflake RAW/STAGING/MART foundation. PostgreSQL, local Airflow, Qwen,
RAG, Text-to-SQL, Cross Analysis, Streamlit and Docker serving remain the
working runtime. No dbt model is added in this phase.

Credentials needed for a live run: AWS SDK credentials scoped to the bucket
prefix, a Snowflake ingest identity, and a preconfigured Snowflake S3 storage
integration with AWS trust. The bootstrap role needs one-time account-level
DDL/grant permissions. Keep passwords/private keys outside Git. Expected costs
are S3 storage and requests, Snowflake X-Small warehouse compute while loading,
and transfer/scan charges; auto-suspend is 60 seconds. Never turn on an
unbounded daily cloud schedule before cost and idempotency acceptance.
