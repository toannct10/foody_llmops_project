# Evaluation in CI

**CI LLM EVALUATION** reads the checked-in 12-case Text-to-SQL manifest, verifies its canonical hash and source-question hash, checks the three pinned model registry entries, validates the `qwen` production selection against the hashed completed benchmark history, and checks summary shape and model hashes. Full pytest runs structured-output parsing, failure categories, SQL guardrails, result verification, unsafe-request refusal, and deterministic fallback tests. The script records `FROZEN_ARTIFACT_NO_INFERENCE` in its summary.

**CI RAG EVALUATION** extracts the deterministic `test_rag_v3` result from the full JUnit file. Its fake retriever and gateway exercise route selection, known evidence, citation shape, grounding, and insufficient-evidence behavior without Qwen generation or a live Chroma index.

**CI TEXT-TO-SQL EVALUATION** extracts the validator/security/fallback tests from the same full JUnit file and records the frozen dataset hash in the LLM summary. It checks answer safety and verification, not live model accuracy.

**LIVE MODEL BENCHMARK** is separate research work. Qwen/Llama/DeepSeek model weights, llama.cpp servers, PostgreSQL reference data, and substantial compute are required. It must not run in normal GitHub Actions. Live RAG generation and cloud acceptance also remain explicit manual work; frozen CI results must not be described as new live benchmark measurements.
