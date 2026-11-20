# CI test matrix

| Requirement | CI evidence | External dependency |
| --- | --- | --- |
| Code quality/config | Ruff, compileall, YAML/JSON parser, required path checks | None |
| Unit/integration | Full `pytest` once, JUnit XML | Mocked services/fixtures |
| Data Quality | `tests/fixtures/ci` schema, null, ID uniqueness, accepted status, restaurant reference, rating/amount, row reconciliation checks | None |
| LLM evaluation | Frozen 12-case hash, 3-model registry, selected Qwen, complete benchmark summary schema; parser/failure tests in pytest | No GGUF |
| Review RAG | `test_rag_v3` deterministic routing, evidence, citations, grounding, insufficient evidence | Fake retriever/gateway |
| Text-to-SQL | `test_text_to_sql` validator, attacks, verifier, fallback; frozen dataset hash | No database or Qwen |
| Airflow | `test_airflow_batch` and cloud foundation mocks for DAG graph, schedule, retry, quality gate | No Airflow service |
| Snowflake dbt | `dbt parse`, `dbt ls`, static project tests | Dummy profile; no Snowflake session |
| Docker | Compose syntax and base/DevOps image build | Docker daemon; no model runtime |
| Security | Tracked-file secret scan and security pytest module | None |
| Observability | Promtool ten rules, dashboard/config parse, bounded metric-label and UI import tests | No live Grafana |

The small fixture is a contract check, not a substitute for live Data Quality acceptance on the full Foody or Sales datasets. JUnit-based group summaries include the number of tests actually discovered and fail if an expected module disappears.
