"""Model-free tests for the frozen Text-to-SQL benchmark protocol."""

import json
from contextlib import nullcontext
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import benchmark_llms
from src.model_benchmark import dataset
from src.model_benchmark.analysis import failure_category, summarize
from src.model_benchmark.registry import ModelSpec, load_registry, select_models


def test_registry_has_three_pinned_distinct_local_candidates():
    config, specs = load_registry()
    assert set(specs) == {"qwen", "llama", "deepseek"}
    assert {spec.quantization for spec in specs.values()} == {"Q4_K_M"}
    assert len({spec.port for spec in specs.values()}) == 3
    assert config["temperature"] == 0
    assert [spec.key for spec in select_models(specs, all_models=True)] == [
        "qwen", "llama", "deepseek"]
    assert select_models(specs, model="llama")[0].family == "Llama"
    with pytest.raises(ValueError):
        select_models(specs)


def test_prompt_hash_uses_both_frozen_prompt_files():
    expected = sha256(benchmark_llms.PROMPT.read_bytes() + b"\n" +
                      benchmark_llms.EXAMPLES.read_bytes()).hexdigest()
    assert benchmark_llms.prompt_hash() == expected


def test_frozen_manifest_hash_and_question_source_are_stable(tmp_path):
    manifest = dataset.load_manifest()
    assert len(manifest["cases"]) == 12
    assert manifest["cases"][0]["expected_reference_result"] == "3184032.00"
    assert manifest["cases"][-1]["expected_safety_class"] == "UNSAFE"
    source = tmp_path / "questions.json"
    source.write_bytes(dataset.SOURCE.read_bytes())
    copy = tmp_path / "manifest.json"
    copy.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    assert dataset.load_manifest(copy, source=source)["dataset_sha256"] == (
        manifest["dataset_sha256"])
    altered = json.loads(copy.read_text(encoding="utf-8"))
    altered["cases"][0]["question"] = "changed"
    copy.write_text(json.dumps(altered, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        dataset.load_manifest(copy, source=source)


def test_manifest_freeze_is_deterministic_for_fixed_inputs(monkeypatch):
    def reference(conn, restaurant_id, case_id):
        if case_id in {"yoy", "trend"}:
            return {datetime(2026, 5, 1, tzinfo=UTC): 7}
        if case_id == "ranking":
            return [("9", 7)]
        return 7

    monkeypatch.setattr(dataset, "_reference", reference)
    monkeypatch.setattr(dataset.queries, "rank_sales_restaurants",
                        lambda *args, **kwargs: [
                            {"restaurant_id": "9", "metric_value": 0.25}])
    timestamp = datetime(2026, 11, 7, tzinfo=UTC)
    first = dataset.freeze_manifest(
        object(), restaurant_id="2751", git_commit="abc", created_at=timestamp)
    second = dataset.freeze_manifest(
        object(), restaurant_id="2751", git_commit="abc", created_at=timestamp)
    assert first == second
    assert first["dataset_sha256"] == dataset.canonical_hash({
        key: value for key, value in first.items() if key != "dataset_sha256"})


def test_frozen_reference_comparison_checks_values_and_restaurant():
    assert dataset.result_correct(
        "orders_month", [{"order_count": 11}], "11")
    assert not dataset.result_correct(
        "orders_month", [{"order_count": 1}], "11")
    assert dataset.result_correct(
        "cancel_ranking", [{"restaurant_id": "1310",
                            "cancellation_rate": 0.1739}],
        {"restaurant_id": "1310", "cancellation_rate": "0.1739"})
    assert not dataset.result_correct(
        "cancel_ranking", [{"restaurant_id": "2751",
                            "cancellation_rate": 0.1739}],
        {"restaurant_id": "1310", "cancellation_rate": "0.1739"})
    monthly = {"2026-01": {"period_start": "2026-01-01",
                           "delivered_sales": 10},
               "2026-02": {"period_start": "2026-02-01",
                           "delivered_sales": 20}}
    assert dataset.result_correct(
        "trend", monthly, {"2026-01-01": "10", "2026-02-01": "20"})
    assert dataset.result_correct("range", monthly, "30")
    assert not dataset.result_correct("range", monthly, "31")


def test_summary_and_failure_classification():
    rows = [
        {"expected_safety_class": "SAFE", "status": "MODEL_RESULT",
         "model_invoked": True, "structured_output_valid": True,
         "validator_pass": True, "execution_pass": True,
         "model_result_correctness": True, "final_answer_correctness": True,
         "fallback_used": False, "generation_latency_ms": 10,
         "total_latency_ms": 20, "input_tokens": 50, "output_tokens": 10,
         "peak_ram_bytes": 100, "peak_vram_mib": 200},
        {"expected_safety_class": "SAFE", "status": "FALLBACK",
         "model_invoked": True, "structured_output_valid": True,
         "validator_pass": False, "execution_pass": False,
         "model_result_correctness": False, "final_answer_correctness": True,
         "fallback_used": True, "generation_latency_ms": 20,
         "total_latency_ms": 30, "input_tokens": 60, "output_tokens": 11,
         "validator_rejection_reason": "ranking_limit",
         "peak_ram_bytes": 120, "peak_vram_mib": 210,
         "generated_sql": ["SELECT ... LIMIT 100"]},
        {"expected_safety_class": "UNSAFE", "status": "POLICY_REFUSAL",
         "safety_correctness": True, "final_answer_correctness": True},
    ]
    summary = summarize("llama", rows)
    assert summary["result_accuracy"] == 0.5
    assert summary["fallback_rate"] == 0.5
    assert summary["end_to_end_accuracy"] == 1
    assert summary["p95_total_latency_ms"] == 29.5
    assert summary["total_input_tokens"] == 110
    assert failure_category(rows[1]) == "wrong_limit"
    assert failure_category(rows[2]) is None
    assert failure_category({**rows[0], "model_result_correctness": False}) == (
        "wrong_final_result")


def test_experiment_logger_and_run_manifest_without_model(tmp_path, monkeypatch):
    spec = ModelSpec(
        "qwen", "Qwen", "missing-test-model", "repo", "revision",
        str(tmp_path / "missing.gguf"), "0" * 64, 3_000_000_000,
        "Q4_K_M", 8194)
    config = {
        "version": "test", "backend": "llama.cpp",
        "server_executable": str(tmp_path / "missing-server.exe"),
        "temperature": 0, "seed": 42, "max_output_tokens": 256,
        "context_size": 2048, "threads": 8, "gpu_layers_requested": 99,
    }
    monkeypatch.setattr(benchmark_llms, "load_registry",
                        lambda: (config, {"qwen": spec}))
    monkeypatch.setattr(benchmark_llms, "git_snapshot",
                        lambda: ("abc123", " M local.txt"))
    monkeypatch.setattr(benchmark_llms, "_port_free", lambda port: True)
    monkeypatch.setattr(benchmark_llms, "environment_snapshot",
                        lambda conn, conf: {"python_version": "test"})
    monkeypatch.setattr(benchmark_llms, "connection",
                        lambda: nullcontext(object()))
    run_dir, summaries = benchmark_llms.benchmark(
        model="qwen", root=tmp_path / "runs", limit=1)
    expected = {
        "run_manifest.json", "results.jsonl", "summary.json",
        "summary.csv", "environment.json", "model_configs.json",
        "git_state.txt", "README.md", "failure_analysis_qwen.json",
    }
    assert expected <= {path.name for path in run_dir.iterdir()}
    assert summaries[0]["status"] == "MODEL_NOT_AVAILABLE"
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
    assert result["status"] == "MODEL_NOT_AVAILABLE"
    assert result["question_id"] == "revenue_month"
    assert json.loads((run_dir / "run_manifest.json").read_text(
        encoding="utf-8"))["git_dirty"] is True


def test_results_jsonl_serializes_unicode_and_sql(tmp_path):
    path = Path(tmp_path / "results.jsonl")
    benchmark_llms._append_result(
        path, {"question": "Tỷ lệ hủy?", "generated_sql": ["SELECT 1"]})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "question": "Tỷ lệ hủy?", "generated_sql": ["SELECT 1"]}


def test_research_result_labels_actual_model_not_production_qwen(monkeypatch):
    spec = ModelSpec("llama", "Llama", "Llama-3.2-3B-Instruct", "repo",
                     "revision", "model.gguf", "a" * 64, 3_210_000_000,
                     "Q4_K_M", 8195)
    case = dataset.load_manifest()["cases"][0]

    def generated(conn, restaurant_id, question, *, gateway_factory, audit_sink):
        audit_sink.append({"structured_output_valid": True,
                           "validator": "PASS", "execution": "PASS",
                           "generation_latency_ms": 1,
                           "raw": [{"raw_output": '{"intent":"monthly_revenue"}'}]})
        return {"execution_mode": "QWEN_TEXT_TO_SQL",
                "sql_facts": [{"delivered_sales": 3184032}],
                "sql_details": {"execution_latency_ms": 2},
                "answer": "verified"}

    monkeypatch.setattr(benchmark_llms.text_to_sql,
                        "answer_with_text_to_sql", generated)
    context = {"backend": "llama.cpp", "run_id": "test", "git_commit": "abc",
               "git_dirty": True, "dataset_version": "v1",
               "dataset_sha256": "b" * 64, "prompt_version": "v1",
               "prompt_sha256": "c" * 64, "schema_version": "003",
               "schema_sha256": "d" * 64}
    row = benchmark_llms.run_case(object(), object(), spec, case, context)
    assert row["execution_mode"] == "LLAMA_TEXT_TO_SQL"
    assert row["status"] == "MODEL_RESULT"
    assert row["model_result_correctness"] is True
