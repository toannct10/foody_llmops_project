# Model benchmark audit — Text-to-SQL Phase 1

Audit completed before benchmark implementation or model downloads on
2026-11-07. The repository is at commit
`65eadd438885bf0ca0732431c2f661e49a116d2d` with uncommitted
Text-to-SQL work and unrelated local drafts. No existing model or data file
will be replaced.

## Existing system reused

| Concern | Existing implementation |
|---|---|
| Production Qwen service | `docker-compose.yml` service `qwen`, llama.cpp OpenAI-compatible server at port 8193, Qwen2.5-3B-Instruct Q4_K_M |
| Frozen active Qwen config and provenance | `qwen_v3_3b.yaml`, `models/qwen_v3/provenance.json`, active GGUF under `models/qwen_v3/` |
| Gateway | `src/llm/gateway.py` `LLMGateway`, supports alternate config and provenance paths; `src/proposed_v1/runtime.py` can launch one local llama-server |
| Text-to-SQL and security gates | `src/sales/text_to_sql.py`, including relevant-schema selector, JSON schema, SQL AST validator, read-only executor, mart checks, deterministic fallback |
| Frozen questions and accepted Qwen evidence | `docs/text_to_sql/evaluation_cases.json`, `scripts/evaluate_text_to_sql.py`, `outputs/evaluation/text_to_sql_v1_results.json` (12/12 acceptance) |
| Prompt | `prompts/sales/text_to_sql_v1.txt` plus selected examples JSON |
| Operational telemetry | `src/rag/monitoring.py` SQLite LLMOps events, `src/monitoring/metrics.py` Prometheus counters and histograms |
| Existing research precedent | `scripts/task2_llm_benchmark.py` benchmarks the same three local model families on frozen RAG packets, with pinned repositories/revisions; it is a different task and its scores are not Text-to-SQL scores |
| Evaluation storage | `outputs/evaluation/` currently contains local Text-to-SQL evidence; the new research logs will be under `outputs/experiments/llm_benchmark/` |
| SQL warehouse | `src/warehouse/loader.py` PostgreSQL connection; approved Sales marts defined in `sql/postgres/migrations/003_sales.sql` |

## Local candidate inventory

All three candidate files exist locally; no download is needed. The SHA256
values for Llama and DeepSeek are recorded in existing Hugging Face download
metadata and the prior RAG benchmark. The new runner must rehash each file
before live use.

| Family | Exact local candidate | Quantization | Bytes | Recorded SHA256 | Source revision |
|---|---|---|---:|---|---|
| Qwen | `models/qwen_v3/qwen2.5-3b-instruct-q4_k_m.gguf` | Q4_K_M | 2,104,932,768 | `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d` | `Qwen/Qwen2.5-3B-Instruct-GGUF@cc1e68eea5f05f88f41a6de1fc73110178f23715` |
| Llama | `models/task2_llm/llama/Llama-3.2-3B-Instruct-Q4_K_M.gguf` | Q4_K_M | 2,019,377,696 | `6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff` | `bartowski/Llama-3.2-3B-Instruct-GGUF@5ab33fa94d1d04e903623ae72c95d1696f09f9e8` |
| DeepSeek | `models/task2_llm/deepseek/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` | Q4_K_M | 1,117,320,800 | `1741e5b2d062b07acf048bf0d2c514dadf2a48f94e2b4aa0cfe069af3838ee2f` | `bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF@9cc28b17e86fa2415fcb070f8ee5ec27c965aa61` |

Official model cards: [Qwen GGUF](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF),
[Meta Llama 3.2 3B](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct),
[DeepSeek R1 Distill Qwen 1.5B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B).
The local Llama and DeepSeek quantizations come from the pinned
[Llama GGUF](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF)
and [DeepSeek GGUF](https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF)
repositories.

## Runtime and protocol

The machine reports Windows 11, Python 3.12.14, 16 logical CPUs, 15.26 GiB
RAM and an NVIDIA RTX 3060 Laptop GPU with 6 GiB VRAM. The accepted local
research runtime is `.qwen-runtime/b11429/llama-server.exe`. The prior RAG
benchmark launched models sequentially on ports 8194–8196 with 8 threads,
2,048-token context and Q4_K_M. The production Docker Qwen service uses port
8193 and must not be stopped or repointed.

Freeze the existing twelve questions, their independently queried Sales mart
references, prompt and schema hashes before generating new model responses.
Run one model at a time through the same `LLMGateway` response schema, fixed
temperature 0, seed 42, max output 256, same selected schema and
`answer_with_text_to_sql` validation/execution/result gates. The only planned
model-specific inputs are local GGUF path, pinned provenance, launch port and
the model's native chat template handled by llama.cpp. Do not change the
production Qwen configuration or prompt.

The new runner will log each attempt to a unique local run directory, retain
raw structured output for audit, sanitize errors, record environment and Git
state, and calculate result-based metrics. Research telemetry will remain in
the experiment directory rather than altering accepted operational LLMOps
events or Prometheus counters.

## Risks and interpretation

- The DeepSeek candidate is a 1.5B distilled **Qwen-based** model, whereas
  Qwen and Llama are approximately 3B. The family comparison is therefore
  not architecture- or size-controlled. Report this explicitly.
- Llama 3.2's official language list is limited and does not list Vietnamese;
  the benchmark's Vietnamese cases test transfer to this task rather than a
  guaranteed supported language.
- A twelve-question acceptance set is too small for a general superiority or
  production-readiness claim. Unsafe refusals must be measured separately.
- Windows localhost port forwarding stalled in prior Text-to-SQL acceptance;
  use explicit `127.0.0.1` for local PostgreSQL. At audit time Docker Desktop
  is not running, so live benchmark readiness still needs verification.
- GPU offload and actual VRAM usage must be measured for every candidate.
  If one model falls back to CPU, report the deployment difference.
- Never use generated SQL as the reference answer. The reference is frozen
  from predefined parameterized SQL against the existing PostgreSQL Sales marts.
