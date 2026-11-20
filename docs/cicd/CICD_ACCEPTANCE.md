# CI/CD acceptance

## AUTOMATED GITHUB CI

**PENDING GITHUB RUN.** The workflow and evidence scripts are implemented locally. GitHub Actions status cannot be claimed before the changed files are committed, pushed, and the workflow completes on GitHub-hosted runners. Several already-accepted prerequisite paths, including `dbt/`, Airflow files, the frozen benchmark configuration/manifest, and the observability alert rules, are currently untracked in this checkout; they must be committed with the CI files before a clean checkout can pass. The final report requires `quality`, `pytest`, `data_quality`, `llm_evaluation`, `rag_evaluation`, `text_to_sql`, `dbt_static`, `airflow`, `security`, `secret_scan`, `observability`, `docker` to be `PASS`. Missing artifacts or failed jobs make overall acceptance `FAIL`.

## LOCAL WORKFLOW VALIDATION: PASS

The local acceptance run validated the new CI code from a dirty working tree based on Git commit `65eadd4`; it is not a GitHub Actions run. The machine-readable `ci-artifacts/ci_acceptance.json` recorded all locally checked domains as PASS and `working_tree_dirty: true`. Generated local artifacts are ignored by Git.

| Check | Local result |
| --- | --- |
| New CI evidence tests | 3 passed |
| Full pytest with JUnit | 500 passed; one upstream Starlette deprecation warning |
| JUnit RAG / Text-to-SQL / Airflow groups | 35 / 50 / 15 passed |
| Data Quality fixture | PASS: 3 Sales rows, 2 Review rows, seven checks |
| Frozen LLM evidence | PASS: 12-case dataset hash, Qwen selection, three complete summaries |
| Ruff / compileall / config parser | PASS / PASS / PASS (9 YAML, 5 JSON) |
| Tracked-file secret scan | PASS |
| Offline dbt parse and graph | PASS: 10 models, 3 sources, 65 tests |
| Four Compose combinations | PASS |
| GitHub Actions actionlint 1.7.12 | PASS |
| Promtool alert rules | PASS: 10 rules |
| Dockerfile.rag and Dockerfile.devops builds | PASS / PASS |
| Retired Terraform check | Historical run only; removed from the current workflow |
| Demo preflight | PASS; 15,454 review vectors/documents |

The dbt parse used the already-built `foody-airflow-cloud:local` image with dbt 1.11.11 and Snowflake adapter 1.11.6. The Docker build used cached layers; GitHub-hosted cold-build time is not yet measured.

## MANUAL HEAVY EVALUATION

Live three-model GGUF benchmarking, live RAG generation, and cloud acceptance require explicit manual execution on suitable hardware and credentials. No self-hosted runner is configured for these tasks. CI reads frozen evidence only.

## LIVE CLOUD ACCEPTANCE PENDING

dbt parse and cloud Compose syntax do not establish Snowflake/AWS connectivity, Data Quality on cloud tables, deployment, or cost. These remain unverified until live credentials and infrastructure are available.
