# CI/CD runbook

From the repository root, use a Python 3.12 environment with `requirements-ci.txt`:

```bash
python -m pip install -r requirements-ci.txt
python -m ruff check .
python -m compileall -q src app scripts dags
python -m scripts.ci_config_check
python -m scripts.ci_acceptance status quality PASS
python -m scripts.ci_acceptance data-quality
python -m scripts.ci_acceptance frozen-evaluation
python -m scripts.security_scan
python -m scripts.ci_acceptance status secret_scan PASS
python -m pytest -q --junitxml=ci-artifacts/pytest.xml
python -m scripts.ci_acceptance pytest-summary
```

For offline dbt, install `requirements-dbt.txt`, then run `dbt parse --project-dir dbt --profiles-dir dbt --no-partial-parse` and `dbt ls --project-dir dbt --profiles-dir dbt --resource-type model source test --output json --quiet > ci-artifacts/dbt_resources.jsonl`, followed by `python -m scripts.ci_dbt_summary`. These commands use dummy profile values and do not contact Snowflake.

For Docker/monitoring syntax, run the four Compose combinations in `ci.yml`, run the pinned `rhysd/actionlint:1.7.12` image, then `promtool check rules` on `devops/prometheus/alerts.yml`; build `Dockerfile.rag` and `Dockerfile.devops` without starting Qwen. Compose manages local named volumes; cloud setup uses documented AWS/Snowflake commands and `sql/snowflake/` scripts.

Inspect the GitHub Actions `ci-acceptance` artifact for `ci_acceptance.json` and `ci_acceptance.md`. An absent per-job summary means the job did not complete; `package-evidence` reports `MISSING` and fails. JUnit XML and the per-domain JSON summaries are in `ci-python-evidence`. Reproduce a failing domain with its named pytest module rather than launching live models. CI files must be committed before GitHub Actions can execute them.

Heavy evaluation remains manual on a suitable local/self-hosted machine. No self-hosted runner has been confirmed, so no automatic or manual-dispatch workflow has been created for GGUF benchmarks or cloud acceptance.
