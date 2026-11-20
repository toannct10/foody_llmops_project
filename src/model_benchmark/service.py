"""Read-only model selection and saved benchmark summaries for the dashboard."""

import json
import os
from collections import Counter
from hashlib import sha256
from pathlib import Path

import requests

from src.model_benchmark.registry import load_registry

RUNS = Path("outputs/experiments/llm_benchmark")
SELECTION = Path("config/model_selection.json")
HISTORY = Path("config/model_benchmark_history.json")
MODELS = ("qwen", "llama", "deepseek")


def selection(path=SELECTION):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("selected_model") != "qwen" or value.get("production_change") is not False:
        raise ValueError("Production model selection must remain Qwen")
    return value


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def load_history(path=HISTORY, *, selected=None):
    history = _json(Path(path))
    digest = history.pop("history_sha256")
    if _canonical_hash(history) != digest:
        raise ValueError("Benchmark history hash mismatch")
    history["history_sha256"] = digest
    runs = history.get("runs", [])
    if selected:
        runs = [run for run in runs if
                run["manifest"]["dataset_sha256"] == selected["dataset_sha256"] and
                run["manifest"]["dataset_version"] == selected["dataset_version"]]
    return runs


def get_run(run_id, *, root=RUNS, selected=None):
    """Prefer full local artifacts; use the checked-in summary if absent."""
    if Path(run_id).name != run_id:
        raise ValueError("Invalid benchmark run ID")
    directory = Path(root) / run_id
    if directory.is_dir():
        return load_run(directory, selected=selected)
    if Path(root) == RUNS:
        return next((run for run in load_history(selected=selected)
                     if run["run_id"] == run_id), None)
    return None


def load_run(directory, *, selected=None):
    """Reject incomplete runs and expose bounded summaries, never raw prompts/SQL."""
    directory = Path(directory)
    manifest = _json(directory / "run_manifest.json")
    if manifest.get("status") != "COMPLETE" or manifest.get("valid_for_comparison") is False:
        raise ValueError("Benchmark run is incomplete or invalid")
    summaries = _json(directory / "summary.json")
    if len(summaries) != 3 or {row.get("model") for row in summaries} != set(MODELS):
        raise ValueError("Benchmark requires all three model summaries")
    if any(row.get("status") != "COMPLETE" or row.get("case_count") != 12
           for row in summaries):
        raise ValueError("Benchmark summaries are incomplete")
    if selected and (manifest.get("dataset_sha256") != selected["dataset_sha256"]
                     or manifest.get("dataset_version") != selected["dataset_version"]):
        raise ValueError("Benchmark dataset differs from selected evidence")
    failures = {}
    for model in MODELS:
        rows = _json(directory / f"failure_analysis_{model}.json")
        failures[model] = dict(Counter(
            row["failure_classification"] for row in rows
            if row.get("failure_classification")))
    return {"run_id": manifest["run_id"], "manifest": manifest,
            "summaries": {row["model"]: row for row in summaries},
            "failure_categories": failures}


def available_runs(root=RUNS, *, selected=None):
    root = Path(root)
    valid = []
    for directory in sorted(root.iterdir(), reverse=True) if root.is_dir() else []:
        if not directory.is_dir():
            continue
        try:
            run = load_run(directory, selected=selected)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        valid.append({"run_id": run["run_id"],
                      "finished_at_utc": run["manifest"].get("finished_at_utc")})
    if root == RUNS:
        for run in load_history(selected=selected):
            if run["run_id"] not in {item["run_id"] for item in valid}:
                valid.append({"run_id": run["run_id"],
                              "finished_at_utc": run["manifest"].get("finished_at_utc")})
        valid.sort(key=lambda item: item["run_id"], reverse=True)
    return valid


def latest_valid_run(root=RUNS, *, selected=None):
    runs = available_runs(root, selected=selected)
    return get_run(runs[0]["run_id"], root=root, selected=selected) if runs else None


def model_status(*, registry_path=None, health_url=None):
    """Stat offline GGUF files; probe only the existing production endpoint."""
    _, specs = load_registry(registry_path) if registry_path else load_registry()
    base = health_url or os.getenv("QWEN_BASE_URL", "http://127.0.0.1:8193")
    try:
        with requests.Session() as session:
            session.trust_env = False
            active = session.get(base.rstrip("/") + "/health", timeout=0.8).status_code == 200
    except requests.RequestException:
        active = False
    return {key: {"model_file": "AVAILABLE" if Path(spec.file).is_file() else "MISSING",
                  "gateway": "ACTIVE" if key == "qwen" and active else
                  "AVAILABLE_OFFLINE" if Path(spec.file).is_file() else "UNAVAILABLE",
                  "role": spec.role, "status": spec.status}
            for key, spec in specs.items()}
