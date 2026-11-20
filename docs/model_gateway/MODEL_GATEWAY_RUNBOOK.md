# Model gateway and evaluation runbook

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --check --all
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --model qwen
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --model llama
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --model deepseek
.\.venv\Scripts\python.exe -m scripts.benchmark_llms --all
```

The benchmark requires local PostgreSQL Sales marts, the pinned GGUFs and
llama.cpp runtime. Each run writes persistent logs under
`outputs/experiments/llm_benchmark/<run_id>/`. Normal CI tests mock model
generation and do not load the GGUFs. The dashboard reads existing logs, or
the checked-in `config/model_benchmark_history.json` summary if logs are
absent. It does not rerun benchmarks. The selected production run and dataset
are pinned in `config/model_selection.json`.

To start the existing production stack, run
`.\scripts\devops\start_review2.ps1`. Then open Streamlit on port 8501 and
choose **System Monitor**. Production Qwen health is available at
`http://127.0.0.1:8193/health`; backend and Streamlit health endpoints are
`http://127.0.0.1:8000/health` and
`http://127.0.0.1:8501/_stcore/health`. A missing benchmark mount uses the
checked-in summary and does not change production generation.
