# dbt transformation audit — 2026-11-07

No dbt project existed before this phase. `sql/snowflake/bootstrap.sql`
defines `FOODY.RAW.SALES_SOURCE`, `FOODY.RAW.REVIEWS_SOURCE`, and `LOAD_AUDIT`.
The two RAW tables preserve the six accepted CSV fields as text plus
`SOURCE_FILE`, `SOURCE_HASH`, `BATCH_ID`, and `LOADED_AT`. Cloud RAW loading is
implemented but **live acceptance is pending** without AWS/Snowflake credentials.

Local PostgreSQL provides `dim_sales_restaurant`, `fact_order`, `fact_review_v2`,
and daily/weekly/monthly Sales views. Its accepted policies are Delivered-only
revenue, AOV = Delivered revenue / Delivered order count, cancellation and
refund rates = respective status count / all order count, Monday-start weeks,
and Vietnam-time exclusion of future Sales dates. Source audits enforce Sales
IDs/status/date/amount validity and direct Sales/Review restaurant ID/name
alignment. The local Review pipeline deduplicates 15,639 source rows to 15,456
facts and enriches them with frozen sentiment/aspect classifiers.

The Snowflake target uses `stg_sales`, `stg_reviews` in `STAGING`, followed by
`dim_restaurant`, `fact_order`, `fact_review`, daily/weekly/monthly Sales views,
Sales summary, and monthly Review summary in `MART`. RAW Review lacks the
classifier outputs, so the cloud `fact_review` contains rating/text and
lineage only; it does not invent sentiment/aspect predictions. The Snowflake
content-hash Review key is stable within the cloud project but is not claimed
byte-identical to the Python local `review_id` encoding. Restaurant alignment
uses the verified direct `restaurant_id` namespace.

The local PostgreSQL marts and serving stack remain the demo runtime. The
optional cloud Airflow DAG is paused and manual. The dbt models cannot be
compared against live Snowflake row counts until the cloud foundation is
provisioned and loaded.
