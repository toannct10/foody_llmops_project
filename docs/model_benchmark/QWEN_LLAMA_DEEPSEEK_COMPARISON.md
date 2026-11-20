# Qwen, Llama, DeepSeek: frozen Text-to-SQL benchmark

## Protocol and provenance

The dataset is `foody_text_to_sql_12_v1`, SHA256
`3b995a92f053366898e65cb5eb3f7e01597ce6f6da18adf3a65e021586c69cfc`.
Its twelve questions and independent parameterized PostgreSQL reference
results were frozen in `data/evaluation/text_to_sql/manifest_v1.json` before
running candidates. Ten cases are safe and two are unsafe. The complete live
run is `outputs/experiments/llm_benchmark/20261107T022914Z-bccf46ea/`,
based on Git commit `65eadd438885bf0ca0732431c2f661e49a116d2d`
with a dirty worktree recorded in `git_state.txt`.

Each model used llama.cpp b11429, Q4_K_M, 2,048-token context, 8 CPU threads,
GPU offload request of 99 layers, temperature 0, seed 42, and 256 maximum
output tokens. Models ran sequentially on separate research ports. Each
received the same question, selected Sales schema, prompt, examples, JSON
contract, SQL validator, read-only executor, and frozen result reference.
The production Qwen service was not repointed. Actual GPU memory use was
recorded for all three candidates.

| Candidate | Parameters | Exact GGUF SHA256 | Backend |
|---|---:|---|---|
| Qwen2.5-3B-Instruct | 3.09B | `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d` | llama.cpp b11429, Q4_K_M |
| Llama-3.2-3B-Instruct | 3.21B | `6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff` | same |
| DeepSeek-R1-Distill-Qwen-1.5B | ~1.5B | `1741e5b2d062b07acf048bf0d2c514dadf2a48f94e2b4aa0cfe069af3838ee2f` | same |

## Observed results

Percentages for structured output, validator, execution, model-result
correctness, and fallback use the ten safe model attempts. End-to-end uses
all twelve cases. Latency is measured on the ten safe questions.

| Metric | Qwen | Llama | DeepSeek |
|---|---:|---:|---:|
| Structured JSON valid | 100% | 100% | 0% |
| SQL validator pass | 100% | 60% | 0% |
| SQL execution success | 100% | 60% | 0% |
| **Model result correct** | **10/10** | **5/10** | **0/10** |
| Safe final answer correct, including fallback | 10/10 | 9/10 | 7/10 |
| Unsafe application-policy refusal | 2/2 | 2/2 | 2/2 |
| End-to-end correct | 12/12 | 11/12 | 9/12 |
| Fallback rate | 0% | 40% | 100% |
| Mean generation latency | 1,086 ms | 1,532 ms | 3,067 ms |
| P95 generation latency | 1,246 ms | 2,342 ms | 3,293 ms |
| Mean total latency | 2,583 ms | 4,089 ms | 5,044 ms |
| P95 total latency | 3,112 ms | 8,770 ms | 9,880 ms |
| Input tokens, total over safe cases | 6,627 | 10,103 | unknown (10/10) |
| Output tokens, total over safe cases | 1,006 | 1,367 | unknown (10/10) |
| Peak process RAM | 2,419 MB | 2,642 MB | 1,466 MB |
| Peak GPU VRAM | 2,085 MiB | 2,313 MiB | 1,159 MiB |

The DeepSeek token counter returned no values. Its aggregate fields in the
machine summary are zero because unavailable samples cannot be summed; they
must **not** be interpreted as zero tokens used. The original benchmark
scores are retained in `initial_scoring/`; the current summary was rescored
from the same saved live facts after correcting nested fallback comparison.

## Recommendation

**Qwen2.5-3B-Instruct is the preferred research base for the next phase** on
this task: it achieved 10/10 correct model SQL results, zero fallback, full
structured-output validity, and the lowest measured generation latency.
This is evidence for selecting a future fine-tuning candidate, not a claim
that fine-tuning has occurred. Production selection is unchanged.

The comparison is limited by twelve cases, one restaurant scope for most
questions, and a single run per model. DeepSeek is smaller and Qwen-derived,
so this is not a matched-parameter architecture experiment. The two unsafe
refusals were handled before any model call. See
`MODEL_BENCHMARK_FAILURE_ANALYSIS.md` for the observed errors, including the
Llama YoY result that passed execution but was factually wrong.

## Reproduce and inspect

From the repository root with PostgreSQL Sales marts available and the local
GGUF files present:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --check --all
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --model qwen
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --model llama
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --model deepseek
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --all
```

Every command creates a separate unique directory under
`outputs/experiments/llm_benchmark/`. Each contains `run_manifest.json`,
`results.jsonl`, `summary.json`, `summary.csv`, `environment.json`,
`model_configs.json`, `git_state.txt`, and per-model failure and resource logs.
To rescore a completed run from already saved facts without new inference:

```powershell
.\.venv\Scripts\python.exe -m scripts.rescore_text_to_sql_benchmark outputs/experiments/llm_benchmark/<run_id>
```

Rescoring can be done once per run and preserves the original files under
`initial_scoring/`.
