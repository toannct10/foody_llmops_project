"""Read-only local health and Airflow ledger snapshots; no cloud assumptions."""

import json
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

import psutil
import requests

from src.monitoring import metrics

RUNS = Path("outputs/airflow/runs")
READY = Path("outputs/airflow/ready.json")
URLS = {
    "qwen": "http://qwen:8193/health",
    "backend": "http://rag-backend:8000/health",
    "streamlit": "http://streamlit:8501/_stcore/health",
    "prometheus": "http://prometheus:9090/-/healthy",
    "grafana": "http://grafana:3000/api/health",
    "airflow": "http://airflow:8080/health",
}


def pipeline_snapshot(runs=RUNS, ready=READY):
    """Use completed non-fixture runs; controlled failure tests are not incidents."""
    recent = None
    if Path(runs).exists():
        for path in sorted(Path(runs).glob("*.json"), key=lambda item: item.stat().st_mtime,
                           reverse=True):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if value.get("quality_fixture") or value.get("status") not in {"SUCCESS", "FAILED"}:
                continue
            recent = value
            break
    published = None
    if Path(ready).exists():
        try:
            published = json.loads(Path(ready).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    gate = (recent or {}).get("tasks", {}).get("data_quality_gate", {})
    return {
        "status": (recent or {}).get("status", "NOT_CONFIGURED"),
        "run_id": (recent or {}).get("dag_run_id"),
        "duration_seconds": (recent or {}).get("duration_seconds"),
        "processed_rows": (recent or {}).get("processed_rows"),
        "failed_rows": (recent or {}).get("failed_rows"),
        "duplicate_rows": (recent or {}).get("duplicate_rows"),
        "quality_gate": gate.get("status", "NOT_CONFIGURED"),
        "last_success_utc": (published or {}).get("published_at_utc"),
    }


def resource_snapshot():
    """Best-effort process/host counters; GPU is unknown without nvidia-smi."""
    result = {"host_memory_ratio": psutil.virtual_memory().percent / 100,
              "process_rss_bytes": psutil.Process().memory_info().rss,
              "cpu_percent": psutil.cpu_percent(interval=None),
              "gpu_percent": None, "vram_used_mb": None}
    if shutil.which("nvidia-smi"):
        try:
            output = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                 "--format=csv,noheader,nounits"], capture_output=True, text=True,
                timeout=1, check=True).stdout.splitlines()[0]
            gpu, vram = output.split(",", 1)
            result.update(gpu_percent=float(gpu.strip()), vram_used_mb=float(vram.strip()))
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            pass
    return result


def _probe_http(url):
    try:
        with requests.Session() as session:
            session.trust_env = False
            return session.get(url, timeout=0.7).status_code == 200
    except requests.RequestException:
        return False


def health_summary(*, probe=_probe_http):
    """Bounded service names; optional Airflow/cloud are never assumed healthy."""
    status = {}
    for name, default_url in URLS.items():
        if name == "airflow" and os.getenv("FOODY_AIRFLOW_MONITOR_ENABLED") != "true":
            status[name] = "NOT_CONFIGURED"
            continue
        url = os.getenv(f"FOODY_HEALTH_{name.upper()}_URL", default_url)
        status[name] = "HEALTHY" if probe(url) else "DOWN"
    try:
        import psycopg

        dsn = os.getenv("FOODY_DATABASE_URL")
        if not dsn:
            status["postgres"] = "NOT_CONFIGURED"
        else:
            with psycopg.connect(dsn, connect_timeout=1) as conn:
                conn.execute("SELECT 1")
            status["postgres"] = "HEALTHY"
    except Exception:
        status["postgres"] = "DOWN"
    status["alertmanager"] = "NOT_CONFIGURED"
    status["aws"] = "LIVE_ACCEPTANCE_PENDING"
    status["snowflake"] = "LIVE_ACCEPTANCE_PENDING"
    return status


def refresh_prometheus():
    """Refresh gauges on backend scrape; one-shot Airflow need not stay alive."""
    pipeline = pipeline_snapshot()
    if pipeline["status"] != "NOT_CONFIGURED":
        metrics.PIPELINE_LAST_FAILURE.labels(source="local_airflow").set(
            int(pipeline["status"] == "FAILED"))
        metrics.PIPELINE_QUALITY_FAILED.labels(source="local_airflow").set(
            int(pipeline["quality_gate"] == "FAILED"))
        metrics.PIPELINE_DURATION.labels(source="local_airflow").set(
            pipeline["duration_seconds"] or 0)
        for key in ("processed_rows", "failed_rows", "duplicate_rows"):
            metrics.PIPELINE_ROWS.labels(kind=key).set(pipeline[key] or 0)
    if pipeline["last_success_utc"]:
        metrics.PIPELINE_LAST_SUCCESS.labels(source="local_airflow").set(
            datetime.fromisoformat(pipeline["last_success_utc"]).timestamp())
    resources = resource_snapshot()
    metrics.HOST_MEMORY_RATIO.set(resources["host_memory_ratio"])
    metrics.VISIBLE_CPU_PERCENT.set(resources["cpu_percent"])
    if resources["gpu_percent"] is not None:
        metrics.VISIBLE_GPU_PERCENT.labels(device="gpu0").set(resources["gpu_percent"])
    if resources["vram_used_mb"] is not None:
        metrics.VISIBLE_VRAM_BYTES.labels(device="gpu0").set(
            resources["vram_used_mb"] * 1024 * 1024)
    metrics.PROCESS_RSS.set(resources["process_rss_bytes"])
    from src.monitoring.cost import resource_summary

    try:
        estimate = resource_summary()["total"]["estimated_local_cost"]
    except sqlite3.Error:
        estimate = None
    if estimate is not None:
        from src.monitoring.cost import cost_config

        metrics.LOCAL_ESTIMATED_COST.labels(device=cost_config()["device"]).set(estimate)
    for name, status in health_summary().items():
        if name not in {"aws", "snowflake", "alertmanager"} and status != "NOT_CONFIGURED":
            metrics.SERVICE_HEALTH.labels(service=name).set(int(status == "HEALTHY"))
