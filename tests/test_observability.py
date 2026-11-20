"""Offline operational metrics, cost and alert contracts."""

import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from prometheus_client import REGISTRY

from src.monitoring import metrics
from src.monitoring.alerts import record_alerts
from src.monitoring.cost import resource_summary
from src.monitoring.operations import health_summary, pipeline_snapshot
from src.rag.monitoring import record

ROOT = Path(__file__).resolve().parents[1]


def test_metric_registration_and_bounded_labels():
    metrics.observe_model_gateway("/private/model.gguf", "raw question", "valid_json", 1,
                                  structured_failure=True)
    metrics.observe_rag({"status": "secret", "generation_mode": "prompt text",
                         "query_route": "restaurant_123", "evidence_count": 0})
    samples = list(REGISTRY.collect())
    names = {family.name for family in samples}
    assert {"foody_pipeline_last_run_failed", "foody_service_health",
            "foody_rag_retrieval_latency_seconds",
            "foody_llm_structured_output_failures"} <= names
    labels = [sample.labels for family in samples for sample in family.samples]
    assert {"model": "other", "task": "other", "status": "success"} in labels
    assert {"route": "other"} in labels
    assert not any("restaurant_123" in str(item) or "private/model" in str(item)
                   for item in labels)


def test_cost_defaults_and_configured_estimate(tmp_path, monkeypatch):
    path = tmp_path / "llmops.sqlite"
    record("rag_v3_generation", "Qwen", "hash", "prompt", 3_600_000, "success",
           input_tokens=100, output_tokens=20, model_id="qwen", task_type="review",
           path=path)
    record("rag_v3_request", "Qwen", "hash", "prompt", 3_600_000, "success",
           input_tokens=100, output_tokens=20, path=path)
    for name in ("COST_TRACKING_ENABLED", "LOCAL_INFERENCE_DEVICE",
                 "LOCAL_GPU_COST_PER_HOUR", "LOCAL_CPU_COST_PER_HOUR"):
        monkeypatch.delenv(name, raising=False)
    default = resource_summary(path)
    assert default["total"]["request_count"] == 1
    assert default["total"]["total_tokens"] == 120
    assert default["total"]["estimated_local_cost"] is None
    assert default["cloud"]["status"] == "NOT_CONFIGURED"
    assert default["model"]["qwen"]["request_count"] == 1
    assert default["task"]["review"]["request_count"] == 1
    monkeypatch.setenv("COST_TRACKING_ENABLED", "true")
    monkeypatch.setenv("LOCAL_INFERENCE_DEVICE", "gpu")
    monkeypatch.setenv("LOCAL_GPU_COST_PER_HOUR", "2")
    estimated = resource_summary(path)["total"]
    assert estimated["estimated_gpu_seconds"] == 3600
    assert estimated["estimated_local_cost"] == 2.0
    assert estimated["cost_status"] == "ESTIMATE"


def test_pipeline_ignores_controlled_fixture_and_keeps_last_success(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    success = runs / "success.json"
    success.write_text(json.dumps({"dag_run_id": "real", "status": "SUCCESS",
                                   "duration_seconds": 12, "processed_rows": 10,
                                   "failed_rows": 0, "duplicate_rows": 2,
                                   "tasks": {"data_quality_gate": {"status": "PASS"}}}))
    failed_fixture = runs / "fixture.json"
    failed_fixture.write_text(json.dumps({"status": "FAILED", "quality_fixture": "bad",
                                          "tasks": {"data_quality_gate": {"status": "FAILED"}}}))
    os.utime(failed_fixture, (success.stat().st_mtime + 10, success.stat().st_mtime + 10))
    ready = tmp_path / "ready.json"
    ready.write_text(json.dumps({"published_at_utc": "2026-11-07T00:00:00+00:00"}))
    value = pipeline_snapshot(runs, ready)
    assert value["run_id"] == "real" and value["quality_gate"] == "PASS"
    assert value["processed_rows"] == 10 and value["last_success_utc"]


def test_health_summary_never_marks_cloud_healthy_without_acceptance(monkeypatch):
    monkeypatch.delenv("FOODY_DATABASE_URL", raising=False)
    monkeypatch.delenv("FOODY_AIRFLOW_MONITOR_ENABLED", raising=False)
    value = health_summary(probe=lambda url: True)
    assert value["qwen"] == "HEALTHY"
    assert value["airflow"] == "NOT_CONFIGURED"
    assert value["postgres"] == "NOT_CONFIGURED"
    assert value["aws"] == "LIVE_ACCEPTANCE_PENDING"
    assert value["snowflake"] == "LIVE_ACCEPTANCE_PENDING"


def test_alert_history_redacts_annotations_and_records_resolution(tmp_path):
    path = tmp_path / "events.sqlite"
    when = datetime(2026, 11, 7, tzinfo=UTC)
    alert = {"name": "QwenServiceDown", "severity": "critical", "component": "qwen",
             "status": "firing", "summary": "password=private"}
    first = record_alerts([alert], path, now=when)
    assert len(first) == 1 and first[0]["summary"] == "QwenServiceDown"
    assert len(record_alerts([alert], path, now=when + timedelta(minutes=1))) == 1
    second = record_alerts([], path, now=when + timedelta(minutes=2))
    assert len(second) == 2 and second[0]["status"] == "resolved"
    assert record_alerts(None, path) == []
    with sqlite3.connect(path) as db:
        serialized = str(db.execute("SELECT * FROM alert_history").fetchall())
    assert "password=private" not in serialized


def test_alert_rules_and_grafana_are_provisioned():
    alerts = yaml.safe_load((ROOT / "devops/prometheus/alerts.yml").read_text())
    names = {rule["alert"] for group in alerts["groups"] for rule in group["rules"]}
    assert len(names) == 10
    assert {"QwenServiceDown", "AirflowPipelineFailure", "DataQualityGateFailed",
            "TextToSQLExecutionFailureSpike", "HighMemoryUsage"} <= names
    prometheus = yaml.safe_load((ROOT / "devops/prometheus/prometheus.yml").read_text())
    assert "/etc/prometheus/alerts.yml" in prometheus["rule_files"]
    dashboard = json.loads((ROOT / "devops/grafana/dashboards/foody-devops.json").read_text())
    titles = {panel["title"] for panel in dashboard["panels"]}
    assert {"Service health", "Text-to-SQL validation/execution failures",
            "Local Airflow run and quality gate", "Configured local compute cost estimate"} <= titles
    assert (ROOT / "devops/grafana/provisioning/dashboards/foody.yaml").exists()


def test_system_monitor_imports_without_live_services():
    from app.app import monitor_page

    assert callable(monitor_page)
