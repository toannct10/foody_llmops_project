# Observability architecture

Backend `/metrics` and Streamlit port 8002 are scraped every 15 seconds by the existing Prometheus. Backend scrape refreshes bounded service probes, host/process resource gauges and the most recent **non-fixture** local Airflow ledger. This lets a one-shot pipeline be observed without a Pushgateway. Grafana provisions its dashboard and Prometheus loads alert rules from repository files. The existing System Monitor reads Prometheus, SQLite, the Airflow ledger and short health probes; it remains the third workspace.

SQLite LLMOps is the detailed request audit. Generation-call resource totals use only `*_generation` rows so request-level records do not double-count tokens. Prometheus is aggregate time series; SQLite alert history stores only transitions for ten known alert names and deletes history older than 30 days. Alertmanager is not part of the default demo stack.

The backend resource probe reports memory visible inside its container and backend resident memory; neither is a complete host or Qwen GPU process profile. `nvidia-smi` is sampled only when present. Optional cost rates are local assumptions, never cloud spend. AWS/Snowflake remain pending.
