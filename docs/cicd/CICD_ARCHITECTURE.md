# CI/CD architecture

`ci.yml` runs on pull requests to `main`/`develop`, pushes to those branches, and manual dispatch. Concurrency cancels obsolete runs for the same ref. Three independent validation jobs run on GitHub-hosted Ubuntu:

1. `python-validation`: one cached CI dependency install; Ruff, compileall, config parse, Data Quality fixture, frozen LLM evidence, tracked-file secret scan, and full pytest once. JUnit is split into machine-readable RAG, Text-to-SQL, Airflow, security, and observability summaries.
2. `dbt-static`: separate dbt adapter install; `dbt parse` and resource discovery with dummy offline Snowflake profile values. No connection or `dbt run/test`.
3. `docker-validation`: actionlint, base/DevOps/Airflow/cloud-overlay Compose syntax, promtool, and artifact-free base and DevOps application image builds. It does not start Qwen or pull GGUF weights.


`package-evidence` waits for all three jobs, runs even when one fails, merges their small artifacts, and writes `ci_acceptance.json` plus a readable GitHub job summary. Missing evidence is a failure. Each job uploads its evidence independently so failures remain inspectable. The final artifact excludes datasets, model weights, indexes, and secrets.

`release.yml` is separate. A `v*` tag or explicit manual dispatch validates source/Compose, builds `Dockerfile.rag`, and publishes version and source-SHA tags to GHCR using the repository's `GITHUB_TOKEN` package permission. Publication is an image release, not production deployment.
