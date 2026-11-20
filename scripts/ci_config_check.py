"""Parse CI-relevant repository configuration without credentials or services."""

import json
from pathlib import Path

import yaml


def main():
    yaml_files = [
        *Path(".github/workflows").glob("*.yml"),
        Path("devops/prometheus/prometheus.yml"),
        Path("devops/prometheus/alerts.yml"),
        Path("dbt/dbt_project.yml"),
        Path("dbt/profiles.yml"),
        *Path("dbt/models").rglob("*.yml"),
    ]
    json_files = [
        Path("devops/grafana/dashboards/foody-devops.json"),
        Path("config/model_benchmark.json"),
        Path("config/model_benchmark_history.json"),
        Path("config/model_selection.json"),
        Path("data/evaluation/text_to_sql/manifest_v1.json"),
    ]
    for path in yaml_files:
        if not isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict):
            raise ValueError(f"Expected YAML mapping: {path}")
    for path in json_files:
        if not isinstance(json.loads(path.read_text(encoding="utf-8")), dict):
            raise ValueError(f"Expected JSON object: {path}")
    for path in (Path("Dockerfile.rag"), Path("Dockerfile.devops"),
                 Path("Dockerfile.airflow"), Path("docker-compose.airflow.yml"),
                 Path("docker-compose.cloud.yml"), Path("requirements-dbt.txt"),
                 Path("dags/foody_daily_batch.py"), Path("sql/postgres/migrations/003_sales.sql")):
        if not path.is_file():
            raise FileNotFoundError(path)
    print(f"Config parse PASS: {len(yaml_files)} YAML, {len(json_files)} JSON")


if __name__ == "__main__":
    main()
