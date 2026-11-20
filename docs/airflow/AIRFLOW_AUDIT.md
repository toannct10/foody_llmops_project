# Airflow orchestration audit

Audit date: 2026-11-07. This checkout has **no Apache Airflow service, DAG,
schedule, run history, or Airflow task logs**. `docker-compose.yml` has an
optional Prefect server/scheduler profile, but its `shopee_data_pipeline`
flow still targets the historical Shopee crawler and Databricks. It must not
be reused for the current Foody batch.

The working local components are:

| Stage | Existing reusable code | Existing behavior |
|---|---|---|
| Sales source audit | `src.sales.audit` | Checks schema, IDs, dates, amounts, statuses, duplicate order IDs and conservative review-name mapping. |
| Sales load | `src.sales.loader.load_sales` | Transactional PostgreSQL upsert; source hash/state and order count return `unchanged` for duplicate batches. |
| Review source / IDs | `src.foody.review_migration` | Strict six-column source, stable review IDs, exact Sales ID/name alignment and accepted source manifest. |
| Review preparation | `src.foody.review_migration.prepare` | Cleans, deduplicates, enriches with frozen sentiment/aspect classifiers, writes Parquet and RAG JSONL; no training or Qwen call. |
| Review warehouse | `src.warehouse.review_loader.load` | Transactional, source-hash aware load into PostgreSQL review facts. |
| RAG indexes | `scripts.build_review_2025_2026_index`, `src.rag.vector_store`, `src.rag_v2.lexical` | Chroma/MiniLM and SQLite BM25 manifests, both currently 15,454 documents; builders verify existing indexes and return without embedding when hashes/counts match. |
| Evaluation | `src.demo.demo_preflight` | Read-only checks for source, models, indexes, Qwen metadata and warehouse artifacts. |

The accepted Review source has 15,639 rows, 183 exact duplicate rows,
15,456 distinct review IDs, 817 restaurants and 15,454 eligible RAG
documents. Its data ends 2026-06-30; this is a historical accepted batch.
Daily freshness must therefore mean **source hash and manifest currency**,
not a claim that new reviews arrived today. The 400,000-row Sales CSV is
loaded into PostgreSQL with an existing source hash and unique order IDs.

Missing before this phase: one Foody DAG, explicit quality-gated dependencies,
daily schedule, bounded retries/timeouts, source-specific batch ledger,
intentional quality-failure fixture, Airflow UI/logging, and a real DAG-run
acceptance record. Local paths and PostgreSQL are retained; cloud storage and
warehouse adapters can replace the source/load functions later.

Safety: existing active Review indexes are immutable for a changed document
hash. A routine unchanged batch can verify and reuse them. Rebuilding a
changed active corpus in place while live RAG serves it is unsafe; the DAG
must fail closed until a separate versioned index switch is approved.
