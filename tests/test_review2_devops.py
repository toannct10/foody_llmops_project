"""Fast contract checks; no Docker, model weights, or live data needed in CI."""

import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import api
from src.foody import review_runtime
from src.foody.review_paths import DATA_VERSION
from src.monitoring import metrics as rag_metrics
from src.warehouse.loader import _date_key, _number


def test_warehouse_mapping_uses_existing_calendar_keys():
    assert _date_key(datetime(2024, 2, 3)) == 20240203
    assert _number("8.5") == 8.5
    assert _number("bad") is None
    assert _number(float("nan")) is None


def test_api_exposes_bounded_metrics_and_versions():
    client = TestClient(api)
    assert client.get("/health").status_code == 200
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "foody_api_requests_total" in response.text
    assert "foody_api_request_duration_seconds" in response.text
    version = client.get("/version")
    assert version.status_code == 200
    assert version.json()["warehouse_schema_version"] == "004"
    assert "qwen_model" in version.json()


def test_active_manifest_reads_real_file(monkeypatch, tmp_path):
    manifest = {"data_version": DATA_VERSION, "row_count": 7, "restaurant_count": 2}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(review_runtime, "MANIFEST", path)
    monkeypatch.setattr(review_runtime, "new_corpus_active", lambda: True)

    assert review_runtime.active_manifest() == manifest


def test_active_manifest_missing_has_unknown_counts(monkeypatch, tmp_path):
    monkeypatch.setattr(review_runtime, "MANIFEST", tmp_path / "missing.json")
    monkeypatch.setattr(review_runtime, "new_corpus_active", lambda: True)

    assert review_runtime.active_manifest() == {
        "data_version": DATA_VERSION, "status": "artifact_unavailable",
        "row_count": None, "document_count": None, "restaurant_count": None,
        "date_min": None, "date_max": None,
    }


def test_version_without_runtime_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(review_runtime, "MANIFEST", tmp_path / "missing.json")
    monkeypatch.setattr(review_runtime, "new_corpus_active", lambda: True)

    response = TestClient(api).get("/version")

    assert response.status_code == 200
    assert response.json()["review_data_version"] == DATA_VERSION
    assert response.json()["review_count"] is None


def test_devops_configs_keep_batch_services_and_dashboard():
    dashboard = json.loads(Path("devops/grafana/dashboards/foody-devops.json").read_text())
    assert dashboard["title"] == "Foody DevOps & LLMOps"
    assert len(dashboard["panels"]) >= 11
    assert [panel["id"] for panel in dashboard["panels"][:8]] == list(range(1, 9))
    assert {panel["title"] for panel in dashboard["panels"][8:11]} == {
        "Sales SQL requests", "Cross-analysis requests", "Sales SQL latency P95",
    }
    compose = Path("docker-compose.devops.yml").read_text()
    assert "kafka" not in compose.lower()
    assert "terraform" not in compose.lower()
    assert Path("sql/postgres/migrations/001_init.sql").exists()
    prometheus = Path("devops/prometheus/prometheus.yml").read_text()
    assert 'targets: ["streamlit:8002"]' in prometheus
    assert 'FOODY_STREAMLIT_METRICS_PORT: "8002"' in compose


def test_shared_rag_metrics_count_once_and_bound_labels():
    before = rag_metrics.RAG_REQUESTS.labels(status="grounded")._value.get()
    rag_metrics.observe_rag({
        "status": "grounded", "generation_mode": "qwen",
        "query_route": "SERVICE_COMPLAINT", "evidence_count": 2,
        "llm_latency_ms": 300, "input_tokens": 12, "output_tokens": 5,
    })
    assert rag_metrics.RAG_REQUESTS.labels(status="grounded")._value.get() == before + 1
    assert rag_metrics.GENERATION.labels(generation_mode="qwen")._value.get() >= 1
    assert rag_metrics.RETRIEVAL.labels(route="SERVICE_COMPLAINT")._value.get() >= 1

    rag_metrics.observe_rag({
        "status": "raw user query", "generation_mode": "restaurant name",
        "query_route": "review_id", "evidence_count": 0,
    })
    assert rag_metrics.RAG_REQUESTS.labels(status="other")._value.get() >= 1
    assert rag_metrics.GENERATION.labels(generation_mode="other")._value.get() >= 1
    assert rag_metrics.RETRIEVAL.labels(route="other")._value.get() >= 1
    assert "raw user query" not in rag_metrics.RAG_REQUESTS.collect()[0].samples[0].labels.values()


def test_streamlit_metrics_server_starts_only_once(monkeypatch):
    calls = []
    monkeypatch.setattr(rag_metrics, "_SERVER_STARTED", False)
    monkeypatch.setattr(rag_metrics, "start_http_server", lambda *args, **kwargs:
                        calls.append((args, kwargs)))
    rag_metrics.start_streamlit_metrics("8002")
    rag_metrics.start_streamlit_metrics("8002")
    assert calls == [((8002,), {"addr": "0.0.0.0"})]
