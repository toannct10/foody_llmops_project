# System Monitor: Model Evaluation

Open **System Monitor** and scroll to **Model Evaluation**. It displays the
selected Qwen production model, Q4_K_M/llama.cpp configuration, frozen dataset
and run ID; a Qwen/Llama/DeepSeek table of correct model SQL, end-to-end
answers, structured-output validity, mean generation latency and peak VRAM;
selection rationale; bounded failure categories; metadata and model status.

The run picker lists only complete, valid three-model runs matching the
selected dataset hash. It reads `summary.json`, `run_manifest.json` and
per-model failure files, with a checked-in compact history snapshot for
deployments without local experiment logs. It does not display raw model output,
user questions, SQL, restaurant IDs or secrets, and it performs no inference. Llama and
DeepSeek normally display `AVAILABLE_OFFLINE`; Qwen health is probed from the
existing endpoint. If both local artifacts and the snapshot are absent, the
section explains that no complete run is available while System Monitor
remains usable.

The dashboard explicitly states: “Benchmark results are based on a 12-case
project-specific evaluation set and are not a general model ranking.”
