"""Model selection, saved evaluation, routing and bounded telemetry tests."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.llm import gateway as gateway_module
from src.model_benchmark import registry as registry_module
from src.model_benchmark import service as benchmark_service
from src.model_benchmark.registry import load_registry
from src.model_benchmark.service import (
    available_runs,
    latest_valid_run,
    load_history,
    load_run,
    selection,
)
from src.monitoring import metrics
from src.rag.monitoring import record
from src.ui.model_evaluation_view import comparison_rows


def test_registry_and_production_selection_are_explicit():
    _, specs = load_registry()
    selected = selection()
    assert {key for key, spec in specs.items() if spec.status == "production"} == {"qwen"}
    assert selected["selected_model"] == "qwen"
    assert selected["benchmark_run"] == "20261107T022914Z-bccf46ea"
    assert all(spec.benchmark_summary_ref for spec in specs.values())
    assert "review_generation" in specs["qwen"].capabilities
    assert "review_generation" not in specs["llama"].capabilities


@pytest.mark.parametrize("model_id", ["llama", "deepseek"])
def test_gateway_routes_by_model_id_without_loading_weights(monkeypatch, model_id,
                                                              tmp_path):
    settings, specs = load_registry()
    fake_file = tmp_path / "candidate.gguf"
    fake_file.write_bytes(b"mock")
    spec = replace(specs[model_id], file=str(fake_file))
    monkeypatch.setattr(registry_module, "load_registry",
                        lambda: (settings, {model_id: spec}))
    monkeypatch.setattr(gateway_module, "_model_digest",
                        lambda path, size, modified: spec.sha256)
    routed = gateway_module.LLMGateway(
        model_id=model_id, url=f"http://127.0.0.1:{spec.port}",
        launch_local=False, monitor=False)
    assert routed.model_id == model_id
    assert routed.name == spec.repo
    assert routed.config["model_file"] == Path(spec.file).name
    routed.session.close()
    with pytest.raises(ValueError, match="Unknown or disabled"):
        gateway_module.LLMGateway(model_id="unknown")


def test_saved_summary_excludes_incomplete_runs(tmp_path):
    selected = selection()
    run_id = "20261107T022914Z-bccf46ea"
    folder = tmp_path / run_id
    folder.mkdir()
    (folder / "run_manifest.json").write_text(json.dumps({
        "run_id": run_id, "status": "COMPLETE",
        "dataset_sha256": selected["dataset_sha256"],
        "dataset_version": selected["dataset_version"],
        "generation_settings": {}, "git_commit": "abc", "backend": "llama.cpp",
    }), encoding="utf-8")
    summaries = [{"model": key, "model_name": key, "status": "COMPLETE",
                  "case_count": 12, "result_accuracy": 1,
                  "end_to_end_accuracy": 1, "structured_output_validity": 1,
                  "mean_generation_latency_ms": 10, "peak_vram_mib": 20}
                 for key in ("qwen", "llama", "deepseek")]
    (folder / "summary.json").write_text(json.dumps(summaries), encoding="utf-8")
    for key in ("qwen", "llama", "deepseek"):
        (folder / f"failure_analysis_{key}.json").write_text(
            json.dumps([{"failure_classification": "wrong_date_range"}]),
            encoding="utf-8")
    assert available_runs(tmp_path, selected=selected)[0]["run_id"] == run_id
    run = latest_valid_run(tmp_path, selected=selected)
    assert run["failure_categories"]["llama"] == {"wrong_date_range": 1}
    assert comparison_rows(run)[0]["Correct model SQL"] == "10/10"
    (folder / "run_manifest.json").write_text(json.dumps({
        "run_id": run_id, "status": "PARTIAL"}), encoding="utf-8")
    assert available_runs(tmp_path, selected=selected) == []
    with pytest.raises(ValueError):
        load_run(folder, selected=selected)


def test_checked_in_history_survives_missing_local_logs(tmp_path, monkeypatch):
    selected = selection()
    monkeypatch.setattr(benchmark_service, "RUNS", tmp_path)
    run = benchmark_service.get_run(selected["benchmark_run"], root=tmp_path,
                                    selected=selected)
    assert run["summaries"]["qwen"]["result_accuracy"] == 1
    assert run["summaries"]["llama"]["result_accuracy"] == 0.5
    assert benchmark_service.available_runs(tmp_path, selected=selected)
    history = json.loads(benchmark_service.HISTORY.read_text(encoding="utf-8"))
    history["runs"][0]["summaries"]["qwen"]["result_accuracy"] = 0
    damaged = tmp_path / "history.json"
    damaged.write_text(json.dumps(history), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_history(damaged)


def test_gateway_telemetry_has_bounded_labels_and_sqlite_fields(tmp_path, monkeypatch):
    seen = []
    path = tmp_path / "llmops.sqlite"
    monkeypatch.setattr(gateway_module, "record",
                        lambda *args, **kwargs: record(*args, **kwargs, path=path))
    monkeypatch.setattr(gateway_module, "observe_model_gateway",
                        lambda *args: seen.append(args))

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"value":1}'}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3}}

    class Session:
        def post(self, *args, **kwargs):
            return Response()

    gateway = gateway_module.LLMGateway.__new__(gateway_module.LLMGateway)
    gateway.url = "http://local"
    gateway.session = Session()
    gateway.monitor = True
    gateway.model_id = "qwen"
    gateway.provenance = {"model": "Qwen", "model_sha256": "hash"}
    gateway.generate(system="private", user="private SQL", response_schema={},
                     prompt_version="v1", component="sales_text_to_sql_generation")
    assert seen[0][:3] == ("qwen", "text_to_sql", "valid_json")
    import sqlite3

    with sqlite3.connect(path) as conn:
        value = conn.execute("SELECT model_id, task_type, input_tokens, "
                             "output_tokens, fallback_status, filters_json "
                             "FROM events").fetchone()
    assert value[:5] == ("qwen", "text_to_sql", 7, 3, "not_at_gateway")
    assert "private" not in value[5]
    metrics.observe_model_gateway("raw-query", "restaurant-id", "valid_json", 0.1)
    samples = list(metrics.MODEL_GATEWAY_REQUESTS.collect()[0].samples)
    assert any(sample.labels == {"model": "other", "task": "other",
                                 "status": "success"} for sample in samples)
