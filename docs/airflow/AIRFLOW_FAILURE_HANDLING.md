# Airflow failure, retry and idempotency policy

- Deterministic `validate_source` and `data_quality_gate` failures have zero
  retries. The source quality fixture is restricted to one checked-in CSV.
- Other tasks have one retry after two minutes, with 30-minute task timeout;
  index work has a 90-minute timeout. There is no infinite retry.
- Every stage writes its own status and duration to an atomic JSON ledger.
  On failure, it records a bounded reason/category and marks downstream
  stages `BLOCKED_UPSTREAM`. Airflow task logs retain the traceback and retry
  history. Publication uses `all_success` and a second explicit critical-task
  check; a failed run cannot update `ready.json`.
- Review source SHA256 plus Sales source SHA256 form a batch ID. An unchanged
  Review manifest/canonical/JSONL reuses accepted artifacts; Sales and Review
  PostgreSQL loaders use their own source state and unique IDs. The Chroma
  and BM25 manifests/counts are verified and reused when identical.
- The accepted Review corpus is historical, ending 2026-06-30. Freshness
  means the accepted manifest matches the current source hash/version; it
  does not imply that new customer reviews arrived today.
- A changed document hash against an existing active RAG index fails closed.
  The current index builders prohibit in-place overwrite. A separate
  versioned index rollout is required before publication; no live Chroma
  directory is destructively replaced by this daily DAG.
- The lightweight evaluation checks Sales/Review mart rows and Chroma/BM25
  counts after all upstream stages. It performs no Qwen generation or
  three-model benchmark.
