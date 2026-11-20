# dbt data quality tests

The parsed project declares generic `not_null`, `unique`, `accepted_values`
and `relationships` tests on sources, staging and facts. RAW Sales uniqueness
is checked per **batch** because a later immutable source batch may contain
the same order IDs. RAW Review exact duplicates are expected and deduplicated
in staging, so RAW Review has no global uniqueness test.

Seven singular SQL assertions check RAW batch/audit row reconciliation,
within-batch order IDs, nonnegative Sales amounts, rating range, Delivered-only
daily revenue and cancellation denominator, daily/weekly/monthly/summary row
totals, and unique restaurant-period mart grain. The source freshness rule
uses RAW `LOADED_AT` with a 30-day warning threshold, no automatic error for
the accepted historical dataset.

`dbt test` writes `target/run_results.json`. The Airflow quality gate requires
at least one result and every result to be `pass`; `warn`, `fail`, `error` or
missing artifacts block publication. `dbt source freshness` runs before tests.
Offline `dbt parse` and `dbt ls` validate syntax, source/ref graph and tests;
only a live Snowflake `dbt run/test` can prove SQL execution and row metrics.
