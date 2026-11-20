# Model gateway architecture

```text
Sales Text-to-SQL / Review RAG / Cross Analysis
                    |
                LLMGateway
             /       |       \
 Qwen [PRODUCTION] Llama [BENCHMARK] DeepSeek [BENCHMARK]

Saved benchmark artifacts -> Evaluation Summary -> System Monitor / Model Evaluation
```

`config/model_benchmark.json` is the central research registry. Each entry
contains ID, family, name, role, status, GGUF path/hash, parameter count,
quantization, backend, context, default generation settings, supported
capabilities and a benchmark-summary reference. `config/model_selection.json`
pins Qwen as the selected production model. Normal application callers retain
their existing Qwen configuration. A research caller can use
`LLMGateway(model_id="llama")` or `model_id="deepseek"` with the same
`generate` method; local files are checksum-verified before use. An explicit
URL connects to an already running model endpoint. Research models need not
remain loaded in VRAM.

The gateway sends the same JSON-schema chat request format, applies a 120 s
HTTP timeout, supports optional transport retries, returns token counts and
latency, and writes bounded model/task/status telemetry when monitoring is
enabled. Prometheus labels are restricted to model IDs, task enums and
success/failure. SQLite stores model ID, task, status, sanitized error type,
token counts, latency, and `not_at_gateway` fallback state; the application
records its later deterministic fallback separately. Benchmark runs set
`monitor=False` so research traffic does not contaminate operational counts.

The read-only summary service accepts only complete three-model runs matching
the selected frozen dataset hash. It prefers full local logs and falls back to
the hash-checked `config/model_benchmark_history.json` summary when local
`outputs/` logs are absent. It never loads model weights, executes SQL, or
displays raw prompts/SQL. The production Qwen service and its Docker port are
unchanged.
