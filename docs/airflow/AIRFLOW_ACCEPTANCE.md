# Local Airflow acceptance — 2026-11-07

## Final rebuilt-image verification

After the final changed-source safety guard, only the Airflow image/container
was rebuilt. Manual run `manual__foody_acceptance_verified_20261107` completed
**SUCCESS** in **107.447 s**, with all ten stages recorded in
`outputs/airflow/runs/10cb35ba4df9ba4f242d.json`. It processed 415,639
source rows (400,000 Sales and 15,639 Review), detected 183 exact Review
duplicates and zero failed rows, verified 400,000 Sales facts, 15,456 Review
facts, 76,535 monthly mart rows, 15,454 Chroma/BM25 documents, and passed
all four lightweight evaluation checks. The ready pointer names this run.

The controlled run `manual__foody_bad_schema_verified_20261107` completed
**FAILED** in **12.771 s**. Its ledger is
`outputs/airflow/runs/f5aee8924a76edf52e9d.json`. `validate_source`
rejected the one-row fixture for missing required columns; the eight later
stages, including enrichment, index update and publication, were blocked.
The ready pointer still names the successful run. The older runs below remain
as additional idempotency and failure-history evidence.

Regression checks on this tree: focused Airflow tests **5 passed**; full
pytest **464 passed, 1 warning**; Ruff **PASS**; compileall **PASS**;
combined base/Review-2/Airflow Compose config **PASS**; demo-preflight
**PASS**. The rebuilt Airflow UI `/health` returned HTTP 200. Airflow task
states for the controlled run were `failed` for validation and
`upstream_failed` for all eight downstream tasks.

## Final runtime

Apache Airflow **2.11.1** runs in the optional `foody-airflow:2.11.1-local`
Compose service with `SequentialExecutor` and a local SQLite metadata volume.
`airflow dags list-import-errors` returned **No data found**; the DAG list
contained `foody_daily_batch`, unpaused. `python -m pip check` returned
**No broken requirements found**. The Airflow UI `/health` returned HTTP 200
at `127.0.0.1:8088`. The existing Qwen/Review-2 services were not rebuilt
or repointed for this DAG.

Schedule: `0 2 * * *` in `Asia/Ho_Chi_Minh`, `catchup=False`,
`max_active_runs=1`. A manual trigger is also supported. Default transient
retry policy is one retry after two minutes, with a 30-minute timeout;
`validate_source` and `data_quality_gate` have **zero retries**. The RAG
index task has a 90-minute timeout. All dependencies are an explicit linear
chain using Airflow's `all_success` rule.

## Successful end-to-end DAG run

Run ID: `manual__foody_acceptance_final_20261107`.
Airflow state: **success**; all ten task instances completed successfully.
Run ledger: `outputs/airflow/runs/74da0638244ddf1ea7a1.json`.
Git base commit: `65eadd438885bf0ca0732431c2f661e49a116d2d`
(the working tree contained this phase's uncommitted implementation).
Batch ID: `896d0b521a4ee20edd60`; duration: **143.401 s**.

| Evidence | Measured value |
|---|---:|
| Sales source rows / PostgreSQL `fact_order` | 400,000 / 400,000 |
| Review source rows | 15,639 |
| Exact duplicate Review rows | 183 |
| Enriched / PostgreSQL Review facts | 15,456 / 15,456 |
| Monthly Sales mart rows | 76,535 |
| Chroma / BM25 documents | 15,454 / 15,454 |
| Failed rows | 0 |
| Lightweight evaluation checks | 4/4 PASS |

Review source SHA256:
`4a5e4cc1d7b1f9eb9b2d392e551545e6c3b9082bbc8dfe01ddf17002aea8e787`.
Sales source SHA256:
`6ba29ff7641b75a623a1e5e8a83b65d3578ba2eda01c443bf9eb8e3f451435cf`.
The source hashes matched the accepted artifacts: source detection,
preparation, marts, enrichment and indexes recorded `SKIPPED_DUPLICATE`.
This proves a repeat run did not duplicate rows or rebuild the accepted
Chroma/BM25 indexes. The source/transform/quality/evaluation checks still
ran. `outputs/airflow/ready.json` points to this successful run. No Qwen
generation or three-model benchmark was run.

## Intentional Data Quality failure

Run ID: `manual__foody_bad_schema_final_20261107`.
Airflow state: **failed**. Run ledger:
`outputs/airflow/runs/9b68041a4781d5fd9df2.json`.
Batch ID: `b60c3ed83711fb262547`; duration: **11.965 s**;
failed fixture rows: **1**. The checked-in fixture omitted the required
Review `Address` column. `detect_source_data` succeeded and `validate_source`
failed with the exact column-contract reason. Airflow reported
`upstream_failed` for `prepare_or_load_data`, `transform_data`,
`data_quality_gate`, `update_marts`, `review_enrichment`,
`update_rag_indexes`, `run_evaluation`, and `publish_ready`. None executed.
The ready pointer still names the successful run. Validation had zero retries.

The first automatic scheduled run on an earlier image failed because a
validation import pulled in MLflow. That import was moved into the training
function, and the **final** image and manual runs above passed. The earlier
failed run remains in Airflow history as audit evidence; it is not counted as
acceptance success.

## Limits

This acceptance reused unchanged current sources. It does not claim a live
new-source index rollout. Existing index builders deliberately reject a
changed document hash at the active index path; the DAG fails closed rather
than replacing a live index. The accepted Review data ends 2026-06-30, so
daily scheduling checks source/manifest currency rather than new-review
recency. Airflow metadata uses local SQLite and `SequentialExecutor`; it is
appropriate for the requested local demonstration, not a distributed
production deployment.
