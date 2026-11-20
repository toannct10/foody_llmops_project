# CI/CD audit

> Historical audit of the earlier workflow. Terraform validation was retired
> with the streaming demo; see `CICD_ARCHITECTURE.md` for current CI jobs.

The existing `ci.yml` ran on `main`/`develop` pushes, `main` pull requests, and manual dispatch. It had a Python lint/full-pytest job, a base Compose and Dockerfile.rag build job, and Terraform offline validation. It uploaded only JUnit XML. `release.yml` published a versioned GHCR image on `v*` tags or manual dispatch. Neither workflow deployed to a remote environment.

Existing tests already cover Sales, Review RAG V3, Cross Analysis, Text-to-SQL validation and attack cases, model gateway, local/cloud Airflow contracts, Snowflake dbt project structure, PostgreSQL/Snowflake security boundaries, and observability. The suite uses mocks and small fixtures; it does not need GGUF inference. The repo has frozen 12-case Text-to-SQL questions, a hashed manifest, model selection, and a hashed summary of the completed Qwen/Llama/DeepSeek benchmark. Full live benchmark outputs and model weights are local research artifacts, not CI inputs.

Gaps before this change: no Data Quality result artifact, no frozen benchmark integrity job, no named RAG/Text-to-SQL/Airflow summaries, no dbt parse, no Airflow/cloud Compose overlay checks, no promtool rule check, no consolidated CI acceptance JSON or GitHub summary. The release workflow did not validate Compose or label images by source SHA.

Automatic CI is intentionally limited to checked-in code, fixtures, and frozen artifacts. Live Qwen/Llama/DeepSeek inference, full Foody/Sales ingestion, index rebuilds, S3/Snowflake runs, and cloud deployment remain manual. Cloud credentials and billing evidence are unavailable; no cloud success can be inferred from offline checks.
