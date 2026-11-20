# Module 13 observability acceptance — 2026-11-08

## LOCAL LIVE ACCEPTANCE: PASS

The local Compose serving and monitoring stack was restarted after a machine shutdown. The ingestion `pipeline` service was not started. The optional Airflow scheduler resumed its existing schedule and published a successful ledger run. One live Review RAG request returned HTTP 200 with five retrieved items and an extractive fallback. One live Streamlit Sales question returned SQL-verified Delivered revenue of 722,432 VND for Hanuri (restaurant 1858), May 2026. Both requests have SQLite LLMOps events.

### Service health

| Service | Endpoint | HTTP |
| --- | --- | ---: |
| Qwen | `127.0.0.1:8193/health` | 200 |
| Backend | `127.0.0.1:8000/health` | 200 |
| Streamlit | `127.0.0.1:8501/_stcore/health` | 200 |
| Prometheus | `127.0.0.1:9090/-/healthy` | 200 |
| Grafana | `127.0.0.1:3000/api/health` | 200 |
| Airflow | `127.0.0.1:8088/health` | 200 |

### Prometheus samples

The Prometheus HTTP query API returned these values after the live requests. Counters reset on container restart; these are point-in-time samples, not project totals.

| Metric query | Observed value |
| --- | ---: |
| `sum(foody_api_requests_total)` | 74 |
| `sum(foody_api_request_duration_seconds_count)` | 74 |
| `sum(foody_model_gateway_requests_total)` | 3 |
| `sum(foody_llm_latency_seconds_count)` | 1 |
| `sum(foody_llm_input_tokens_total)` | 2,446 |
| `sum(foody_llm_output_tokens_total)` | 162 |
| `sum(foody_rag_requests_total)` | 1 |
| `sum(foody_rag_retrieval_latency_seconds_count)` | 1 |
| `sum(foody_rag_generation_mode_total)` | 1 |
| `sum(foody_rag_retrieval_route_total)` | 1 |
| `sum(text_to_sql_requests_total)` | 1 |
| `sum(text_to_sql_success_total)` | 1 |
| `sum(text_to_sql_generation_latency_seconds_count)` | 1 |
| `sum(text_to_sql_execution_latency_seconds_count)` | 1 |
| `foody_pipeline_last_success_timestamp_seconds` | 1,794,121,438.13435 |
| `foody_pipeline_last_duration_seconds` | 80.211 |
| `foody_pipeline_quality_gate_failed` | 0 |
| `foody_visible_cpu_percent` / `foody_host_memory_usage_ratio` | present |

Backend and Streamlit emit separate process-visible resource samples. GPU/VRAM and estimated monetary cost have no Prometheus series when unavailable or unconfigured. Failure counters need not be nonzero in a healthy smoke test.

### Airflow ledger and System Monitor

The running Streamlit container read the Airflow ledger through the read-only mount. The existing System Monitor rendered without an exception and displayed **Last Airflow Run: SUCCESS**, **Quality Gate: PASS**, **Processed Rows: 415,639**, the last accepted publication timestamp, and **Latest Airflow pipeline duration: 80.211 s**. The direct ledger reader returned zero failed rows and 183 duplicate rows. The page retained the three top-level workspaces and showed AI Operations, Data Platform, System Health, DevOps + LLMOps, and Cost & Alerts.

### Alerts and Grafana

`promtool check rules /etc/prometheus/alerts.yml` reported **SUCCESS: 10 rules found**. Prometheus loaded one group with all 10 rules: QwenServiceDown, RAGBackendDown, StreamlitDown, AirflowPipelineFailure, DataQualityGateFailed, HighLLMLatency, TextToSQLValidationFailureSpike, TextToSQLExecutionFailureSpike, RAGInsufficientEvidenceSpike, and HighMemoryUsage. All were inactive and `/api/v1/alerts` had zero firing alerts during the healthy smoke. A controlled firing/resolution was not induced because it would require disrupting a healthy service or temporarily altering alert thresholds. Offline tests verified firing/resolved SQLite history transitions and sanitization.

Grafana's authenticated dashboard API returned the repository-provisioned **Foody DevOps & LLMOps** dashboard with **29 panels**, covering service health, application/LLM latency and tokens, RAG, Text-to-SQL, Airflow/data quality, resources, alerts, and configured local cost. Alertmanager is not in the default stack; Prometheus rules and System Monitor alert history remain available without a notification sink.

### Cost and SQLite audit

The Streamlit cost service reported **417 generation calls**, **372,548 input tokens**, **34,336 output tokens**, and **5,096.908 generation seconds** from the existing SQLite LLMOps log, with model `qwen` and tasks `review` and `text_to_sql`. This historical SQLite aggregate is distinct from the since-restart Prometheus counters. Local CPU/GPU seconds and monetary cost were `NOT_CONFIGURED` because no inference device and hourly rate were configured. AWS actual cost and Snowflake actual cost were null with status `NOT_CONFIGURED`. Recent SQLite rows included the live RAG generation/request and Sales Text-to-SQL generation/request events.

### Validation

- Focused observability, model gateway, Text-to-SQL, Airflow, Review-2 and Streamlit UI: **78 passed**, one upstream Starlette deprecation warning.
- Focused RAG V3: **35 passed**.
- Full repository pytest: **497 passed**, one upstream Starlette deprecation warning.
- Ruff: **PASS** (`.venv\\Scripts\\python.exe -m ruff check .`).
- Compileall: **PASS** (`.venv\\Scripts\\python.exe -m compileall -q src app scripts`).
- Tracked-file secret scan: **PASS** (`.venv\\Scripts\\python.exe scripts/security_scan.py`).
- Combined base + DevOps + Airflow Compose config: **PASS**.
- Demo preflight: **PASS** (15,454 RAG documents/vectors).
- Airflow regression: covered by focused tests and the live ledger/HTTP check; no manual expensive DAG run was triggered for this acceptance.

## CLOUD COST / SNOWFLAKE COMPUTE: NOT_CONFIGURED — LIVE ACCEPTANCE PENDING

AWS and Snowflake credentials and billing-rate inputs were not available. No cloud usage, spend, or production SLO is claimed.

## Remaining limits

- GPU and VRAM require an accessible `nvidia-smi` inside the serving container; absent here, their series are omitted.
- No Alertmanager or external notification delivery is configured. A live alert firing/resolution was not tested.
- Local monetary estimates require explicit opt-in, inference device, and hourly rate. The default remains unknown.
- Prometheus counters are process-scoped and reset on serving-container restart; SQLite keeps request-level audit history.
