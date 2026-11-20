# Metric taxonomy

| Area | Metrics | Bounded labels / notes |
|---|---|---|
| API and Streamlit | `foody_api_requests_total`, `foody_api_request_duration_seconds`, scrape `up` | HTTP route/status; no user input |
| LLM | `foody_model_gateway_requests_total`, latency, input/output tokens, `foody_llm_structured_output_failures_total` | model `qwen/llama/deepseek/other`; task `text_to_sql/review/cross/other`; success/failure |
| Review RAG | requests, generation mode, retrieval route, evidence histogram, retrieval/LLM latency, grounding, insufficient evidence, fallback | fixed enums, never review text or IDs |
| Text-to-SQL | request/success/validation/execution/fallback counters; generation/execution/total latency; tokens and execution mode | fixed validator reasons, four approved table names |
| Airflow/data quality | `foody_pipeline_last_run_failed`, quality gate, last success timestamp, duration and `foody_pipeline_last_rows{kind}` | latest non-fixture ledger; kinds processed/failed/duplicate |
| Infrastructure | `foody_service_health{service}`, visible host memory ratio, backend RSS, scrape `up` | fixed service list; GPU/VRAM are UI best effort |
| Cost/resource | token counters, generation duration from SQLite, optional `foody_local_estimated_cost` | estimate metric appears only after explicit device/rate opt-in; no cloud actual-cost series |

Null violations, cloud freshness/reconciliation and actual AWS/Snowflake spend are unavailable until the source systems emit measured data. Do not equate absence of a metric with zero. The high-memory gauge reflects the memory view of the backend container and may include host memory, depending on Docker runtime.
