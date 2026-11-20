# Foody Intelligence full local demo

Requires Docker Desktop with Compose, PowerShell 7, at least 16 GB RAM and 10 GB free disk space. The first setup builds CPU images and restores PostgreSQL from the included dump; it needs no model download.

From this extracted folder in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_demo.ps1
```

Open http://localhost:8501. API: http://localhost:8000; Grafana: http://localhost:3000; Prometheus: http://localhost:9090. Local credentials are generated in .env.demo during setup.

Later: `.\start_demo.ps1`; stop: `.\stop_demo.ps1`; reset isolated demo volumes: `.\reset_demo.ps1 -ConfirmReset`. Optional Airflow: `.\setup_demo.ps1 -WithAirflow`.

Cross Intelligence supports an inferred previous month for a dated change question. For example, a June 2025 revenue and negative-review comparison uses May 2025 as its baseline; a month without a year requires clarification.
