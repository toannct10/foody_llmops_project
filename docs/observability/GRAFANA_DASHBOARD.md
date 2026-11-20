# Provisioned Grafana dashboard

`devops/grafana/provisioning/dashboards/foody.yaml` loads `devops/grafana/dashboards/foody-devops.json` into the Foody folder. Existing panels 1–13 remain. Added panels show service health, gateway calls by model/task, RAG retrieval latency and grounding/fallback, Text-to-SQL mode and failures, local Airflow/quality gate and row counts, last accepted run, visible memory, backend RSS, opt-in local cost estimate and firing alert count.

Prometheus and Grafana may show `No data` before the first scrape or when the optional source is not configured. In particular, local cost has no series by default, and Airflow gauges require a non-fixture completed ledger. This is intentional. No manual dashboard edits are needed; restart/reload the provisioned Grafana service after changing JSON.
