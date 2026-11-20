# dbt model contract

| Model | Materialization | Key / purpose |
|---|---|---|
| `stg_sales` | incremental merge | `order_id`; parse dates/amounts, canonical statuses, trim IDs/names, preserve batch/file/hash/time. |
| `stg_reviews` | incremental merge | Content-derived `review_id`; parse dates/ratings, normalize whitespace, collapse exact accepted Review duplicates, preserve lineage. |
| `dim_restaurant` | table | Direct Sales restaurant ID; most frequent nonempty Sales name with alphabetic tie break; Review presence. |
| `fact_order` | incremental merge | Source order ID, date key, amount/status and lineage. |
| `fact_review` | incremental merge | Content-derived Review ID, direct restaurant ID, date key, rating/text and lineage. |
| `restaurant_daily_sales` | view | Delivered-only revenue, counts, AOV and cancellation/refund rates; excludes future dates in Vietnam time. |
| `restaurant_weekly_sales` | view | Monday-start aggregation and prior calendar-week growth. |
| `restaurant_monthly_sales` | view | Calendar-month aggregation and prior calendar-month growth. |
| `restaurant_sales_summary` | view | All observable Sales dates per restaurant. |
| `restaurant_monthly_reviews` | view | Deduplicated monthly Review count and mean rating; no inferred sentiment. |

Source `LOADED_AT` is ingestion freshness, not the historical order/review
event date. Source freshness warns after 30 days without a new cloud load;
it does not assert that historical customer data is new. Sales RAW contains
future-dated source rows through 2026-12-31; the Sales analytical views apply
the accepted Vietnam-time observed-date cutoff.
