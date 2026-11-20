# Local runbook

1. Start the existing Review2 stack with `./scripts/devops/start_review2.ps1`.
2. Verify Qwen at `http://127.0.0.1:8193/health`, Streamlit at
   `http://127.0.0.1:8501/_stcore/health`, and PostgreSQL via
   `docker compose -f docker-compose.yml -f docker-compose.devops.yml ps`.
3. Open Sales Intelligence, select a restaurant and ask a Vietnamese Sales
   question. The result table contains only SQL rows. Expand Technical details
   to inspect `QWEN_TEXT_TO_SQL` or `DETERMINISTIC_FALLBACK`, generated SQL,
   selected tables, validation status and latency.
4. In a non-Compose local run set `TEXT_TO_SQL_ENABLED=true` and
   `QWEN_BASE_URL=http://127.0.0.1:8193`. The Review2 Compose Streamlit service
   sets the feature flag itself. Use `TEXT_TO_SQL_ENABLED=false` for an immediate
   rollback to the existing deterministic Sales path.
5. Run `.venv/Scripts/python.exe -m pytest -q tests/test_text_to_sql.py` for
   model-free policy tests. For the twelve-case live evaluation, use the
   project-root PowerShell session after Qwen and PostgreSQL are healthy:

   ```powershell
   $env:QWEN_BASE_URL = 'http://127.0.0.1:8193'
   $env:FOODY_DATABASE_URL = 'postgresql://foody:foody_local_demo@127.0.0.1:5433/foody?connect_timeout=5'
   .venv\Scripts\python.exe -m scripts.evaluate_text_to_sql
   ```

   Use the local demo database credentials shown here only with the bundled
   demo database. The explicit IPv4 host avoids a Windows localhost connection
   stall observed during acceptance. The run writes each case as it finishes
   to `outputs/evaluation/text_to_sql_v1_results.json`.

If Qwen is unavailable or emits invalid SQL, the Sales result includes a bounded
fallback reason in Technical details. If PostgreSQL itself is unavailable, the
UI reports warehouse unavailability. Neither SQL drafts nor credentials are
written to Prometheus labels. The Review RAG path remains independent.
