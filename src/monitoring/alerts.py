"""Bounded Prometheus alert snapshots and small SQLite transition history."""

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

LOG = Path("state/llmops.sqlite")
NAMES = {"QwenServiceDown", "RAGBackendDown", "StreamlitDown",
         "AirflowPipelineFailure", "DataQualityGateFailed", "HighLLMLatency",
         "TextToSQLValidationFailureSpike", "TextToSQLExecutionFailureSpike",
         "RAGInsufficientEvidenceSpike", "HighMemoryUsage"}
SEVERITIES = {"warning", "critical"}
COMPONENTS = {"qwen", "backend", "streamlit", "airflow", "data_quality",
              "llm", "text_to_sql", "rag", "infrastructure"}


def fetch_alerts(url=None):
    """None means Prometheus unavailable; an empty list means no active alerts."""
    base = url or os.getenv("FOODY_PROMETHEUS_URL", "http://prometheus:9090")
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(base.rstrip("/") + "/api/v1/alerts", timeout=0.8)
            response.raise_for_status()
            payload = response.json()
        if payload.get("status") != "success":
            return None
        result = []
        for item in payload.get("data", {}).get("alerts", []):
            labels = item.get("labels", {})
            name = labels.get("alertname")
            if name not in NAMES or item.get("state") != "firing":
                continue
            severity = labels.get("severity")
            component = labels.get("component")
            result.append({"name": name,
                           "severity": severity if severity in SEVERITIES else "warning",
                           "component": component if component in COMPONENTS else "unknown",
                           "status": "firing", "summary": name})
        return result
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def record_alerts(alerts, path=LOG, *, now=None):
    """Persist firing/resolved transitions, never raw Prometheus annotations."""
    if alerts is None:
        return []
    now = now or datetime.now(UTC)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sanitized = {item["name"]: item for item in alerts if item.get("name") in NAMES
                 and item.get("status") == "firing"}
    with sqlite3.connect(path, timeout=10) as db:
        db.execute("CREATE TABLE IF NOT EXISTS alert_current (name TEXT PRIMARY KEY, "
                   "severity TEXT, component TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS alert_history (id INTEGER PRIMARY KEY, "
                   "timestamp TEXT, name TEXT, severity TEXT, component TEXT, "
                   "status TEXT, summary TEXT)")
        prior = {row[0]: (row[1], row[2]) for row in
                 db.execute("SELECT name,severity,component FROM alert_current")}
        for name, item in sanitized.items():
            if name not in prior:
                severity = item["severity"] if item.get("severity") in SEVERITIES else "warning"
                component = item["component"] if item.get("component") in COMPONENTS else "unknown"
                db.execute("INSERT INTO alert_current VALUES (?,?,?)", (name, severity, component))
                db.execute("INSERT INTO alert_history (timestamp,name,severity,component,status,summary) "
                           "VALUES (?,?,?,?,?,?)",
                           (now.isoformat(), name, severity, component, "firing", name))
        for name, (severity, component) in prior.items():
            if name not in sanitized:
                db.execute("DELETE FROM alert_current WHERE name=?", (name,))
                db.execute("INSERT INTO alert_history (timestamp,name,severity,component,status,summary) "
                           "VALUES (?,?,?,?,?,?)",
                           (now.isoformat(), name, severity, component, "resolved", name))
        db.execute("DELETE FROM alert_history WHERE timestamp < ?",
                   ((now - timedelta(days=30)).isoformat(),))
        return [dict(zip(("timestamp", "name", "severity", "component", "status", "summary"),
                         row, strict=True)) for row in db.execute(
                             "SELECT timestamp,name,severity,component,status,summary "
                             "FROM alert_history ORDER BY id DESC LIMIT 20")]
