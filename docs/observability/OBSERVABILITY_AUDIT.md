# Observability audit — 2026-11-07

> Historical audit of the earlier streaming demo. Kafka metrics and panels were
> retired; see `OBSERVABILITY_ARCHITECTURE.md` for the current batch stack.

Existing local telemetry: backend and Streamlit expose Prometheus metrics for API requests/errors/latency, RAG requests/routes/evidence/generation/tokens, Sales/Cross requests, Text-to-SQL validation/execution/fallback and gateway model/task/tokens. Kafka consumer exports consumed/failed events. Grafana's provisioned Foody dashboard had 13 API/RAG/Kafka/Sales panels. SQLite `state/llmops.sqlite` stores request-level model, prompt version, latency, token, route, status and failure metadata; `outputs/airflow/runs/*.json` plus `ready.json` store accepted Airflow run and quality-gate evidence. The System Monitor already showed RAG, Sales, Kafka, API and research metrics. Compose health checks existed for Qwen, PostgreSQL, Kafka, Prometheus and Grafana; backend/Streamlit expose HTTP health URLs.

Missing before this phase: Prometheus alert rules and alert history; current service health, Airflow ledger gauges and resource/cost summary in System Monitor; retrieval/grounding/fallback and structured-output metrics; GPU/VRAM display when measurable; provisioned operational Grafana panels. No Alertmanager existed. Cloud credentials and actual AWS/Snowflake spend remain unavailable.

Cardinality: existing `route/status/model/task` labels are bounded in code. The Text-to-SQL `reason` label is a fixed validator category and `table` is a four-name allowlist. New pipeline metrics have only a three-value `kind` label; service labels are fixed names. Request IDs, question/SQL text, restaurant/review IDs, filenames, prompt text and exception strings belong in neither Prometheus labels nor alert annotations.

Local acceptance evidence in older reports describes earlier runs; this phase distinguishes current HTTP/metric checks from those historical observations. Cloud metrics are `NOT_CONFIGURED`/`LIVE_ACCEPTANCE_PENDING` until AWS/Snowflake access is available.
