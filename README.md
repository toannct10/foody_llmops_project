# Food Review Intelligence Platform

[![CI](https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/workflows/ci.yml/badge.svg)](https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/workflows/ci.yml)

A local Vietnamese restaurant-review demo and a separate, frozen sentiment research benchmark. VN-MSASar v3 supplies research training, validation, and test data. First-party Foody reviews supply real-world inference, restaurant analytics, and retrieval documents; they are not treated as gold sentiment labels.

The active demo uses text-only TF-IDF sentiment, a separate aspect classifier, Foody marts, Chroma and BM25 retrieval, RAG V3 evidence checks, a local Qwen 2.5 3B model, Streamlit, and SQLite LLMOps telemetry. [The final architecture](reports/final/FINAL_ARCHITECTURE.md) describes the data and answer path. Local model weights, review data, indexes, and operational state are intentionally excluded from Git and container images.

## Run the accepted local demo

From the project directory on Windows, with the existing `.venv` and frozen local artifacts:

```powershell
.\scripts\start_demo.cmd
```

The launcher runs the read-only `python -m src.cli demo-preflight`, starts the pinned local Qwen server if needed, and opens Streamlit at `http://localhost:8501`. It does not crawl, download, train, or rebuild indexes. For a CPU-only fallback, use `.\scripts\start_demo.cmd -CpuOnly`. Active artifact paths and versions are pinned in [`config/demo.yaml`](config/demo.yaml). The [demo acceptance report](reports/final/FINAL_DEMO_ACCEPTANCE.md), [script](reports/final/DEMO_SCRIPT_VI.md), and [backup plan](reports/final/DEMO_BACKUP_PLAN.md) record the verified local presentation path.

Foody predictions have no measured Foody accuracy. RAG V3 answers use cited synthesis, a labeled extractive fallback, or an explicit insufficient-evidence result. The six-query retrieval development set is small and incomplete; see the [RAG V3 acceptance report](reports/final/RAG_V3_ACCEPTANCE_REPORT.md) for measured limits.

### Optional PhoBERT ABSA comparison

Review Intelligence → Analyze a Review offers Compare Models, TF-IDF, and PhoBERT ABSA views. Install the declared demo and PhoBERT dependencies into the **project virtual environment**, then launch Streamlit with that same Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt -r requirements-phobert-absa.txt
.\.venv\Scripts\python.exe -m streamlit run app/app.py
```

The `streamlit` command on `PATH` may use a different Python without Transformers. The accepted `scripts/start_demo.cmd` launcher also uses the project `.venv`. Place the supplied bundle at `models/phobert_absa/`. The PhoBERT ABSA model runs on CPU, predicts native aspect-level sentiment, and does not provide an overall review sentiment. Its binary relevance artifact has weak labels without a documented class mapping, so its raw class scores are shown in Technical Details and never gate inference. The original training forward pass and word segmentation were not supplied; this adapter uses the bundled PhoBERT tokenizer and CLS token with the saved heads. Ad-hoc predictions do not establish which model is more accurate.

The Docker image installs CPU PyTorch, Transformers, and SentencePiece; Compose already mounts `./models` read-only. Before zipping an existing portable-demo staging tree, run `python -m scripts.stage_phobert_absa <staging-directory>` to copy the PhoBERT bundle and changed runtime files into it. This preserves the other staged artifacts. Existing release ZIPs predate this addition and must be rebuilt from the updated staging tree to include it. `absa.pt` adds 540,216,658 uncompressed bytes; final ZIP growth depends on compression. The checkpoint remains outside Git.

## Research and data

- [Data preparation and frozen split](docs/experiments/PHASE2.md)
- [Rule-based and TF-IDF baselines](docs/experiments/BASELINES.md)
- [Qwen Proposed V1](docs/experiments/PROPOSED_V1.md)
- [Proposed V2](docs/experiments/PROPOSED_V2.md)
- [Aspect-conditioned research](docs/experiments/ASPECT_CONDITIONED.md)
- [Final experiment story](reports/final/TASK2_EXPERIMENT_STORY.md)

The VN-MSASar split, labels, and completed model results are frozen. Foody processing and enrichment preserve raw lineage; ratings are never substituted for sentiment labels. Dataset and local model artifacts are not shipped in the repository. `dvc.yaml`, `dvc.lock`, and `params.yaml` retain the reproducible research protocol without requiring CI to download the dataset or retrain models.

The repository retains historical Shopee/Databricks source and bundle files because current tests and the Proposed V2 frozen-input audit reference them. They are outside the active Foody demo. Local-only Shopee live diagnostics and acceptance evidence are excluded from Git tracking; no local historical file is deleted by this cleanup.

## Checks

Use Python 3.12 in the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q src app scripts
.\.venv\Scripts\python.exe -m src.cli demo-preflight
```

The final preflight requires the local data, models, indexes, and state files. CI uses synthetic fixtures and skips that real-artifact check when they are absent.

## CI/CD and containers

[CI](.github/workflows/ci.yml) runs on `main` and `develop` pushes, pull requests to `main`, and manual dispatch. It checks Ruff, source compilation, pytest, application imports, Docker Compose syntax, and the Streamlit image build without downloading Qwen weights or rebuilding the Foody index. The [release workflow](.github/workflows/release.yml) publishes a versioned image to GHCR on `v*` tags or manual dispatch. It delivers an image; no remote production deployment is configured. See the [CI/CD acceptance report](reports/final/CICD_ACCEPTANCE.md).

`Dockerfile.rag` builds the application image. Docker Compose mounts local `data/`, `models/`, `state/`, and `reports/` at runtime; these assets are not baked into the image. `docker compose config --quiet` validates its configuration. The accepted presentation path is the local launcher above.

For the local batch and observability demo, install Docker Desktop, keep the existing frozen local artifacts, then run `.\scripts\devops\start_review2.ps1`. Compose reuses or creates the named PostgreSQL, Prometheus, and Grafana volumes and starts the database, Qwen, backend, Streamlit, and monitoring services. Stop monitoring and PostgreSQL with `.\scripts\devops\stop_review2.ps1`. The older [Review-2 report](reports/devops/REVIEW2_DEVOPS_REPORT.md) and [acceptance JSON](reports/devops/DEVOPS_ACCEPTANCE.json) are retained as historical evidence of the retired streaming demo; they do not describe the current stack. No remote production deployment is claimed.

The current data path is scheduled batch source → validation → PostgreSQL local demo or S3 and Snowflake cloud → dbt → Airflow → AI/LLMOps → Streamlit. Real-time streaming was removed because it is outside the proposal scope. Terraform was removed because infrastructure as code was not a proposal requirement. Cloud setup remains documented through AWS/Snowflake configuration, IAM guidance, and the SQL in `sql/snowflake/`.

## Optional sales extension

If the local `data/foody/source/order_cleaning.csv` is present, Review-2 startup loads it idempotently into the same PostgreSQL warehouse. To reload explicitly, run `python -m src.cli sales-load` with `FOODY_DATABASE_URL` pointing to that warehouse. Streamlit then routes numerical sales questions to verified SQL and combines SQL facts with date-aligned review evidence only for one-to-one restaurant matches. The source CSV remains outside Git. See the [sales and RAG architecture](docs/RAG_SALES_ARCHITECTURE.md) and [measured acceptance](reports/sales/SALES_RAG_REPORT.md).
