"""Research-only, sequential three-family Text-to-SQL benchmark."""

import argparse
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
from contextlib import nullcontext
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import psutil

from src.llm.gateway import LLMGateway
from src.model_benchmark.analysis import (
    failure_category,
    summarize,
    write_summary_csv,
)
from src.model_benchmark.dataset import load_manifest, result_correct
from src.model_benchmark.registry import load_registry, select_models
from src.sales import text_to_sql
from src.utils.hashing import file_checksum
from src.warehouse.loader import connection

ROOT = Path("outputs/experiments/llm_benchmark")
PROMPT = Path("prompts/sales/text_to_sql_v1.txt")
EXAMPLES = Path("prompts/sales/text_to_sql_examples.json")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                     default=str) + "\n", encoding="utf-8")


def git_snapshot():
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1"], text=True).strip()
    return commit, status


def prompt_hash():
    return sha256(PROMPT.read_bytes() + b"\n" + EXAMPLES.read_bytes()).hexdigest()


def _command_output(command):
    try:
        process = subprocess.run(command, capture_output=True, text=True,
                                 timeout=8, check=False)
        return process.stdout.strip() if process.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def environment_snapshot(conn, config):
    packages = {}
    for name in ("sqlglot", "psycopg", "pydantic", "requests", "psutil"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    gpu = _command_output(["nvidia-smi", "--query-gpu=name,memory.total,"
                           "driver_version", "--format=csv,noheader"])
    cuda = _command_output(["nvidia-smi"]) or ""
    server = Path(config["server_executable"])
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "python_version": sys.version,
        "os": platform.platform(),
        "cpu": platform.processor() or platform.uname().processor or None,
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "total_ram_bytes": psutil.virtual_memory().total,
        "gpu": gpu,
        "cuda_version_reported_by_driver": (
            cuda.split("CUDA Version:")[-1].split("|")[0].strip()
            if "CUDA Version:" in cuda else None),
        "llama_cpp_backend": config["backend"],
        "llama_server_executable": str(server),
        "llama_server_sha256": file_checksum(server) if server.is_file() else None,
        "postgresql_version": conn.execute("SHOW server_version").fetchone()[0],
        "package_versions": packages,
    }


def _port_free(port):
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _model_runtime_files(spec, config, run_dir):
    model_path = Path(spec.file)
    runtime_config = {
        "model_repo": spec.repo, "model_revision": spec.revision,
        "model_file": model_path.name, "model_dir": str(model_path.parent),
        "quantization": spec.quantization, "runtime": config["backend"],
        "port": spec.port, "gpu_layers": config["gpu_layers_requested"],
        "threads": config["threads"], "context_size": config["context_size"],
        "temperature": config["temperature"], "seed": config["seed"],
        "max_new_tokens": config["max_output_tokens"],
        "server_log_path": str(run_dir / f"{spec.key}_server.log"),
        "resource_samples_path": str(run_dir / f"{spec.key}_resources.jsonl"),
    }
    provenance = {
        "model": spec.repo, "model_sha256": spec.sha256,
        "server_executable": str(Path(config["server_executable"]).resolve()),
    }
    config_path = run_dir / f"{spec.key}_runtime_config.json"
    provenance_path = run_dir / f"{spec.key}_runtime_provenance.json"
    write_json(config_path, runtime_config)
    write_json(provenance_path, provenance)
    return config_path, provenance_path


def _attempt_details(attempts):
    raw = [entry["raw_output"] for item in attempts
           for entry in item.get("raw", []) if "raw_output" in entry]
    parsed = None
    for item in reversed(raw):
        try:
            parsed = json.loads(item)
            break
        except (ValueError, TypeError):
            continue
    return raw, parsed if isinstance(parsed, dict) else {}


def _resource_window(runtime, cpu_start, gpu_start):
    if runtime is None:
        return {"cpu_percent": None, "peak_ram_bytes": None,
                "gpu_percent": None, "peak_vram_mib": None}
    cpu = runtime.cpu_samples[cpu_start:]
    gpu = runtime.gpu_samples[gpu_start:]
    return {
        "cpu_percent": max(cpu, default=None),
        "peak_ram_bytes": runtime.peak_rss or None,
        "gpu_percent": max((value[0] for value in gpu), default=None),
        "peak_vram_mib": max((value[1] for value in gpu), default=None),
    }


def _safe_fallback(conn, restaurant_id, question):
    from src.sales.service import sales_answer

    old = os.environ.get("TEXT_TO_SQL_ENABLED")
    os.environ["TEXT_TO_SQL_ENABLED"] = "false"
    try:
        return sales_answer(conn, restaurant_id, question)
    finally:
        if old is None:
            os.environ.pop("TEXT_TO_SQL_ENABLED", None)
        else:
            os.environ["TEXT_TO_SQL_ENABLED"] = old


def run_case(conn, gateway, spec, case, context, runtime=None):
    """Reuse the production SQL gates but isolate benchmark logs and model."""
    started = perf_counter()
    attempts = []
    cpu_start = len(runtime.cpu_samples) if runtime else 0
    gpu_start = len(runtime.gpu_samples) if runtime else 0
    record = {
        **context,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "model_family": spec.family,
        "model_name": spec.name,
        "model_file": spec.file,
        "model_sha256": spec.sha256,
        "parameter_count": spec.parameter_count,
        "quantization": spec.quantization,
        "backend": context["backend"],
        "question_id": case["id"],
        "question": case["question"],
        "expected_intent": case["expected_intent"],
        "expected_safety_class": case["expected_safety_class"],
        "restaurant_scope": case["restaurant_scope"],
        "date_scope": case["date_scope"],
        "selected_schema": sorted(text_to_sql.select_schema(case["question"])),
        "selected_schema_sha256": (
            text_to_sql_schema_hash(case["question"])),
    }
    try:
        result = text_to_sql.answer_with_text_to_sql(
            conn, case["selected_restaurant_id"], case["question"],
            gateway_factory=lambda: nullcontext(gateway), audit_sink=attempts)
        record["model_result_correctness"] = result_correct(
            case["id"], result["sql_facts"], case["expected_reference_result"])
        record["result_correctness"] = record["model_result_correctness"]
        record["final_answer_correctness"] = record["model_result_correctness"]
        record["execution_mode"] = f"{spec.key.upper()}_TEXT_TO_SQL"
        record["fallback_used"] = False
        record["answer"] = result["answer"]
        record["result_rows"] = result["sql_facts"]
        record["status"] = "MODEL_RESULT"
        record["execution_latency_ms"] = result["sql_details"].get(
            "execution_latency_ms")
    except Exception as error:
        category = getattr(error, "category", type(error).__name__)
        record["error_category"] = category
        record["error_message_sanitized"] = category
        record["model_result_correctness"] = False if (
            case["expected_safety_class"] == "SAFE") else None
        record["result_correctness"] = (
            False if category in {"result_mismatch", "result_scope"} else None)
        fallback = _safe_fallback(
            conn, case["selected_restaurant_id"], case["question"])
        record["execution_mode"] = fallback.get("execution_mode")
        record["fallback_used"] = case["expected_safety_class"] == "SAFE"
        record["answer"] = fallback.get("answer")
        record["fallback_status"] = fallback.get("status")
        record["result_rows"] = fallback.get("sql_facts")
        record["safety_correctness"] = (
            fallback.get("status") == "refused_unsafe_request"
            and fallback.get("sql_facts") is None
            and not attempts) if case["expected_safety_class"] == "UNSAFE" else None
        record["final_answer_correctness"] = (
            record["safety_correctness"]
            if case["expected_safety_class"] == "UNSAFE" else result_correct(
                case["id"], fallback.get("sql_facts"),
                case["expected_reference_result"]))
        record["status"] = ("POLICY_REFUSAL" if case["expected_safety_class"] ==
                            "UNSAFE" else "FALLBACK")
    raw, parsed = _attempt_details(attempts)
    record.update({
        "model_invoked": bool(attempts),
        "raw_structured_output": raw,
        "parsed_output_status": ("VALID" if any(
            item.get("structured_output_valid") for item in attempts)
            else "INVALID" if attempts else "NOT_APPLICABLE"),
        "predicted_intent": parsed.get("intent"),
        "generated_sql": [item["generated_sql"] for item in attempts
                          if item.get("generated_sql")],
        "parameters": parsed.get("parameters"),
        "tables_used": parsed.get("tables_used"),
        "structured_output_valid": (any(
            item.get("structured_output_valid") for item in attempts)
            if attempts else None),
        "validator_pass": (any(item.get("validator") == "PASS" for item in attempts)
                           if attempts else None),
        "validator_rejection_reason": next((
            item["rejection"] for item in reversed(attempts)
            if item.get("validator") == "FAIL"), None),
        "execution_pass": (any(item.get("execution") == "PASS" for item in attempts)
                           if attempts else None),
        "generation_latency_ms": (sum(
            item.get("generation_latency_ms") or 0 for item in attempts)
            if attempts else None),
        "execution_latency_ms": record.get("execution_latency_ms") or (
            sum(item.get("execution_latency_ms") or 0 for item in attempts)
            if attempts else None),
        "total_latency_ms": (perf_counter() - started) * 1000,
        "input_tokens": (sum(item.get("input_tokens") or 0 for item in attempts)
                         if any(item.get("input_tokens") is not None
                                for item in attempts) else None),
        "output_tokens": (sum(item.get("output_tokens") or 0 for item in attempts)
                          if any(item.get("output_tokens") is not None
                                 for item in attempts) else None),
        "attempts": attempts,
        **_resource_window(runtime, cpu_start, gpu_start),
    })
    record["failure_classification"] = failure_category(record)
    return record


def text_to_sql_schema_hash(question):
    from src.model_benchmark.dataset import canonical_hash

    return canonical_hash(text_to_sql.select_schema(question))


def _unavailable_case(spec, case, context, status):
    return {
        **context,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "model_family": spec.family, "model_name": spec.name,
        "model_file": spec.file, "model_sha256": spec.sha256,
        "parameter_count": spec.parameter_count,
        "quantization": spec.quantization, "backend": context["backend"],
        "question_id": case["id"], "question": case["question"],
        "expected_intent": case["expected_intent"],
        "expected_safety_class": case["expected_safety_class"],
        "status": status, "model_invoked": False,
        "structured_output_valid": None, "validator_pass": None,
        "execution_pass": None, "model_result_correctness": None,
        "final_answer_correctness": None, "safety_correctness": None,
        "fallback_used": None, "generation_latency_ms": None,
        "execution_latency_ms": None, "total_latency_ms": None,
        "input_tokens": None, "output_tokens": None,
        "peak_ram_bytes": None, "peak_vram_mib": None,
        "failure_classification": status,
    }


def _append_result(path, row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        stream.flush()


def _write_readme(path, manifest):
    path.write_text(
        "# Text-to-SQL model benchmark\n\n"
        f"Run ID: {manifest['run_id']}\n\n"
        "This is research output. The production Qwen service was not repointed.\n"
        "results.jsonl contains one record per model and frozen question; "
        "summary.json/csv aggregate measured outcomes. "
        "failure_analysis_<model>.json lists failed cases. "
        "environment.json and model_configs.json record reproducibility details.\n"
        "Unsafe refusals are application-policy outcomes before any model call, "
        "not evidence of model-native refusal.\n",
        encoding="utf-8")


def benchmark(*, model=None, all_models=False, root=ROOT, limit=None):
    config, specs = load_registry()
    selected = select_models(specs, model=model, all_models=all_models)
    dataset = load_manifest()
    cases = dataset["cases"][:limit] if limit else dataset["cases"]
    commit, state = git_snapshot()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    run_dir = Path(root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    prompt_digest = prompt_hash()
    from src.model_benchmark.dataset import canonical_hash

    context = {
        "run_id": run_id, "git_commit": commit, "git_dirty": bool(state),
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": dataset["dataset_sha256"],
        "prompt_version": "text_to_sql_v1", "prompt_sha256": prompt_digest,
        "schema_version": "sql/postgres/migrations/003_sales.sql",
        "schema_sha256": canonical_hash(text_to_sql.MART_COLUMNS),
        "backend": config["backend"],
    }
    manifest = {
        **context, "started_at_utc": datetime.now(UTC).isoformat(),
        "selected_models": [spec.key for spec in selected],
        "case_count_per_model": len(cases),
        "generation_settings": {key: config[key] for key in (
            "temperature", "seed", "max_output_tokens", "context_size",
            "threads", "gpu_layers_requested")},
        "production_qwen_service_modified": False,
    }
    write_json(run_dir / "run_manifest.json", manifest)
    (run_dir / "git_state.txt").write_text(
        f"commit: {commit}\ndirty: {bool(state)}\n\n{state}\n", encoding="utf-8")
    _write_readme(run_dir / "README.md", manifest)
    results_path = run_dir / "results.jsonl"
    if not _port_free(8194) or not _port_free(8195) or not _port_free(8196):
        raise RuntimeError("A research model port is already in use; no model launched")
    if Path(config["server_executable"]).is_file():
        backend_status = "AVAILABLE"
    else:
        backend_status = "RUNTIME_NOT_AVAILABLE"
    model_configs = {spec.key: {**asdict(spec),
                     "availability": spec.availability(verify_hash=True)}
                     for spec in selected}
    write_json(run_dir / "model_configs.json", {
        "registry_version": config["version"],
        "backend_status": backend_status,
        "settings": {key: config[key] for key in (
            "backend", "server_executable", "context_size", "threads",
            "gpu_layers_requested", "temperature", "seed", "max_output_tokens")},
        "models": model_configs,
    })
    summaries = []
    old_url = os.environ.pop("QWEN_BASE_URL", None)
    try:
        with connection() as conn:
            write_json(run_dir / "environment.json",
                       environment_snapshot(conn, config))
            # Keep research telemetry in run files rather than accepted LLMOps state.
            text_to_sql.record = lambda *args, **kwargs: None
            text_to_sql.observe_text_to_sql = lambda *args, **kwargs: None
            text_to_sql.observe_sales_sql = lambda *args, **kwargs: None
            for spec in selected:
                availability = model_configs[spec.key]["availability"]
                if availability == "AVAILABLE" and backend_status != "AVAILABLE":
                    availability = backend_status
                rows = []
                if availability == "AVAILABLE":
                    config_path, provenance_path = _model_runtime_files(
                        spec, config, run_dir)
                    try:
                        with LLMGateway(
                            config_path=config_path, provenance_path=provenance_path,
                            monitor=False) as gateway:
                            for case in cases:
                                row = run_case(conn, gateway, spec, case, context,
                                               runtime=gateway.runtime)
                                rows.append(row)
                                _append_result(results_path, row)
                                print(f"{spec.key} {case['id']}: {row['status']} "
                                      f"correct={row['final_answer_correctness']}",
                                      flush=True)
                    except Exception as error:
                        availability = "RUNTIME_UNAVAILABLE_" + type(error).__name__
                for case in cases[len(rows):]:
                    row = _unavailable_case(spec, case, context, availability)
                    rows.append(row)
                    _append_result(results_path, row)
                summary = summarize(spec.key, rows)
                summary["model_name"] = spec.name
                summary["model_sha256"] = spec.sha256
                summary["availability"] = availability
                summaries.append(summary)
                failures = [row for row in rows if row.get("failure_classification")]
                write_json(run_dir / f"failure_analysis_{spec.key}.json", failures)
                write_json(run_dir / "summary.json", summaries)
                write_summary_csv(run_dir / "summary.csv", summaries)
    finally:
        if old_url is not None:
            os.environ["QWEN_BASE_URL"] = old_url
    manifest["finished_at_utc"] = datetime.now(UTC).isoformat()
    manifest["status"] = "COMPLETE" if all(
        row["status"] == "COMPLETE" for row in summaries) else "PARTIAL"
    write_json(run_dir / "run_manifest.json", manifest)
    return run_dir, summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--model", choices=("qwen", "llama", "deepseek"))
    choice.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, choices=range(1, 13))
    parser.add_argument("--check", action="store_true",
                        help="Inspect local model files without running inference")
    args = parser.parse_args()
    config, specs = load_registry()
    selected = select_models(specs, model=args.model, all_models=args.all)
    if args.check:
        for spec in selected:
            print(f"{spec.key}: {spec.availability()}")
        print(f"server: {'AVAILABLE' if Path(config['server_executable']).is_file() else 'RUNTIME_NOT_AVAILABLE'}")
        return
    run_dir, summaries = benchmark(
        model=args.model, all_models=args.all, limit=args.limit)
    print(f"Run: {run_dir}")
    for row in summaries:
        print(f"{row['model']}: {row['status']} "
              f"result_accuracy={row['result_accuracy']}")


if __name__ == "__main__":
    main()
