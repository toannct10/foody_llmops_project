"""CI-safe DAG and quality-gate tests without Airflow or model weights."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from src import airflow_batch as batch


def test_dag_import_schedule_dependencies_and_retry_policy(monkeypatch):
    created = {}
    dependencies = []

    class FakeDag:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeOperator:
        def __init__(self, **kwargs):
            self.task_id = kwargs["task_id"]
            created.setdefault("tasks", {})[self.task_id] = kwargs

        def __rshift__(self, other):
            dependencies.append((self.task_id, other.task_id))
            return other

    airflow = ModuleType("airflow")
    airflow.DAG = FakeDag
    operators = ModuleType("airflow.operators")
    python = ModuleType("airflow.operators.python")
    python.PythonOperator = FakeOperator
    pendulum = ModuleType("pendulum")
    pendulum.datetime = lambda *args, **kwargs: (args, kwargs)
    for name, module in (("airflow", airflow), ("airflow.operators", operators),
                         ("airflow.operators.python", python), ("pendulum", pendulum)):
        monkeypatch.setitem(sys.modules, name, module)
    path = Path(__file__).resolve().parents[1] / "dags/foody_daily_batch.py"
    spec = importlib.util.spec_from_file_location("test_foody_dag", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert created["dag_id"] == "foody_daily_batch"
    assert created["schedule"] == "0 2 * * *"
    assert created["catchup"] is False and created["max_active_runs"] == 1
    assert created["start_date"][1]["tz"] == "Asia/Ho_Chi_Minh"
    assert list(created["tasks"]) == list(batch.STAGES)
    assert dependencies == list(zip(batch.STAGES, batch.STAGES[1:], strict=False))
    assert created["tasks"]["validate_source"]["retries"] == 0
    assert created["tasks"]["data_quality_gate"]["retries"] == 0
    assert created["tasks"]["update_rag_indexes"]["retries"] == 1
    assert all(created["tasks"][name]["python_callable"] is batch.execute_stage
               for name in batch.STAGES)


def test_detect_identical_source_is_idempotent(tmp_path, monkeypatch):
    source = tmp_path / "review.csv"
    sales = tmp_path / "sales.csv"
    enriched = tmp_path / "enriched.parquet"
    documents = tmp_path / "documents.jsonl"
    manifest = tmp_path / "manifest.json"
    for path in (source, sales, enriched, documents):
        path.write_bytes(b"stable")
    manifest.write_text(json.dumps({"source_sha256": "stablehash",
                                    "data_version": "v1"}), encoding="utf-8")
    monkeypatch.setattr(batch, "SOURCE", source)
    monkeypatch.setattr(batch, "SALES_SOURCE", sales)
    monkeypatch.setattr(batch, "ENRICHED", enriched)
    monkeypatch.setattr(batch, "DOCUMENTS", documents)
    monkeypatch.setattr(batch, "MANIFEST", manifest)
    monkeypatch.setattr(batch, "digest", lambda path: "stablehash")
    first = batch.detect_source_data({})
    second = batch.detect_source_data({})
    assert first == second
    assert first["status"] == "SKIPPED_DUPLICATE"
    manifest.write_text(json.dumps({"source_sha256": "oldhash"}), encoding="utf-8")
    assert batch.detect_source_data({})["status"] == "NEW"


def test_bad_review_fixture_fails_and_blocks_ai_index_publish(tmp_path, monkeypatch):
    from src.foody import review_migration

    monkeypatch.setattr(batch, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(batch, "digest", lambda path: "fixturehash")
    monkeypatch.setattr(review_migration, "read_source",
                        lambda path: (_ for _ in ()).throw(
                            ValueError("Review source columns differ from contract")))
    run_id = "manual__quality_fixture"
    batch.execute_stage("detect_source_data", run_id=run_id,
                        logical_date="2026-11-07T00:00:00+07:00",
                        quality_fixture="invalid_review_schema")
    with pytest.raises(ValueError, match="columns differ"):
        batch.execute_stage("validate_source", run_id=run_id,
                            logical_date="2026-11-07T00:00:00+07:00",
                            quality_fixture="invalid_review_schema")
    summary = batch.read_summary(run_id)
    assert summary["status"] == "FAILED"
    assert summary["failed_rows"] == 1
    assert summary["duration_seconds"] >= 0
    assert summary["tasks"]["validate_source"]["status"] == "FAILED"
    for name in ("review_enrichment", "update_rag_indexes", "publish_ready"):
        assert summary["tasks"][name]["status"] == "BLOCKED_UPSTREAM"


def test_changed_review_source_fails_before_touching_active_index(tmp_path, monkeypatch):
    from src.foody import review_migration, review_runtime

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_sha256": "old"}), encoding="utf-8")
    vector = tmp_path / "vector"
    vector.mkdir()
    (vector / "index_manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(batch, "MANIFEST", manifest)
    monkeypatch.setattr(review_runtime, "VECTOR", vector)
    monkeypatch.setattr(review_runtime, "LEXICAL", tmp_path / "lexical")
    monkeypatch.setattr(review_migration, "prepare",
                        lambda source: pytest.fail("active artifacts were rewritten"))
    with pytest.raises(ValueError, match="versioned index rollout"):
        batch.prepare_or_load_data({"source_hashes": {"review": "new"}})


def test_critical_quality_gate_failure_blocks_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(batch, "digest", lambda path: "stable")
    run_id = "manual__bad_quality"
    batch.execute_stage("detect_source_data", run_id=run_id,
                        logical_date="2026-11-07T00:00:00+07:00")
    monkeypatch.setitem(batch.ACTIONS, "data_quality_gate",
                        lambda summary, **kwargs: (_ for _ in ()).throw(
                            ValueError("critical null rule failed")))
    with pytest.raises(ValueError, match="critical null"):
        batch.execute_stage("data_quality_gate", run_id=run_id,
                            logical_date="2026-11-07T00:00:00+07:00")
    summary = batch.read_summary(run_id)
    assert summary["status"] == "FAILED"
    assert summary["tasks"]["update_marts"]["status"] == "BLOCKED_UPSTREAM"
    assert summary["tasks"]["publish_ready"]["status"] == "BLOCKED_UPSTREAM"
