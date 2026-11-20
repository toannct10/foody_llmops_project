# Local Airflow batch architecture

```text
detect_source_data
  → validate_source
  → prepare_or_load_data
  → transform_data
  → data_quality_gate
  → update_marts
  → review_enrichment
  → update_rag_indexes
  → run_evaluation
  → publish_ready
```

`dags/foody_daily_batch.py` is the single primary DAG. Each PythonOperator
calls a reusable function in `src/airflow_batch.py`; it does not duplicate
Sales, Review, index or warehouse algorithms. All edges use Airflow's default
`all_success` trigger rule. A validation/quality failure blocks marts,
enrichment, indexing, evaluation and publication. The DAG runs daily at
02:00 `Asia/Ho_Chi_Minh`, has `catchup=False`, `max_active_runs=1`, and also
supports manual triggers. The Airflow service is an optional Compose overlay,
so the existing Review-2 stack remains unchanged when it is not enabled.

The current local adapters are the strict CSV source readers, transactionally
idempotent PostgreSQL Sales/Review loaders, frozen sentiment/aspect Review
preparation, and Chroma/BM25 manifest-verified indexes. Qwen is not loaded by
these batch stages. The evaluation is read-only SQL/count/hash verification;
the expensive three-model benchmark remains manual research work. The
source/load/index functions are the explicit seams for a later S3/Snowflake
adapter, without adding those technologies now.

Each run writes `outputs/airflow/runs/<sha256-of-run-id>.json` with the
original DAG run ID, logical date, source hashes, batch ID, Git SHA when
available, stage statuses/durations/results, processed/failed/duplicate
counts, quality/mart/index/evaluation status, and total duration. The ready
pointer is `outputs/airflow/ready.json` and is written only after all
critical gates pass. Airflow itself retains graph, task state, retry history,
durations and logs in its local metadata/log volumes.
