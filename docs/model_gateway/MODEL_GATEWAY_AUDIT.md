# Model gateway audit

Audited the current Foody checkout after the complete three-model Text-to-SQL
benchmark. Production serving uses `docker-compose.yml` Qwen on port 8193;
`src/rag_v3/cli.py` selects the pinned Qwen V3 config and provenance. The
existing `src/llm/gateway.py` already provided one OpenAI-compatible JSON
generation path, timeout, token usage and SQLite LLMOps logging. The Phase-1
`config/model_benchmark.json` registry pinned Qwen, Llama and DeepSeek GGUFs,
hashes, runtime settings and research ports. Phase-1 artifacts live under
`outputs/experiments/llm_benchmark/20261107T022914Z-bccf46ea/`.

The existing System Monitor showed live Prometheus/SQLite telemetry and
VN-MSASar research metrics, but had no Text-to-SQL model comparison. The
existing Prometheus counters covered Qwen Text-to-SQL and RAG, but had no
bounded model/task/status gateway counter. Llama and DeepSeek were available
as local research files and were not production Docker services.

This phase extends the same registry with role/status/capabilities, adds an
explicit model-selection artifact, a read-only benchmark summary service,
gateway model-ID routing and bounded telemetry, and a Model Evaluation
section inside System Monitor. Streamlit mounts only the saved benchmark
directory read-only. No GGUF is copied or duplicated. No benchmark inference
is run by the dashboard. Production Qwen remains selected.
