"""Optional dbt execution and quality gates for the cloud Airflow DAG."""

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.security.audit import security_event

PROJECT = Path(__file__).resolve().parents[1] / "dbt"
READY = Path("outputs/cloud/dbt_ready.json")


def require_enabled():
    if os.getenv("FOODY_CLOUD_DBT_ENABLED", "false").lower() != "true":
        security_event("cloud_dbt", "disabled", status="blocked")
        raise ValueError("Cloud dbt DAG is disabled; set FOODY_CLOUD_DBT_ENABLED=true")


def _command(action, *, project=PROJECT):
    command = ["dbt", action, "--project-dir", str(project),
               "--profiles-dir", str(project), "--target", "prod"]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False, timeout=3600)
    except (OSError, subprocess.TimeoutExpired) as error:
        security_event("cloud_dbt", type(error).__name__)
        raise RuntimeError(f"dbt {action} could not complete: {type(error).__name__}") from error
    if result.returncode:
        security_event("cloud_dbt", "command_failed")
        # dbt may echo connection details; keep its stdout/stderr in local dbt logs.
        raise RuntimeError(f"dbt {action} failed with exit code {result.returncode}")
    return {"command": action, "exit_code": result.returncode}


def dbt_run():
    require_enabled()
    result = _command("run")
    artifact = PROJECT / "target/run_results.json"
    results = json.loads(artifact.read_text(encoding="utf-8"))["results"]
    if not results or any(row["status"] != "success" for row in results):
        security_event("cloud_dbt", "model_run_incomplete")
        raise ValueError("dbt run results contain incomplete models")
    return {**result, "models_successful": len(results)}


def dbt_test():
    require_enabled()
    # Source freshness is an explicit separate dbt CLI command.
    _source_freshness()
    result = _command("test")
    return result


def _source_freshness():
    command = ["dbt", "source", "freshness", "--project-dir", str(PROJECT),
               "--profiles-dir", str(PROJECT), "--target", "prod"]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as error:
        security_event("cloud_dbt", type(error).__name__)
        raise RuntimeError(f"dbt source freshness could not complete: {type(error).__name__}") from error
    if result.returncode:
        security_event("cloud_dbt", "source_freshness_failed")
        raise RuntimeError(f"dbt source freshness failed with exit code {result.returncode}")


def quality_gate():
    require_enabled()
    artifact = PROJECT / "target/run_results.json"
    results = json.loads(artifact.read_text(encoding="utf-8"))["results"]
    if not results or any(row["status"] != "pass" for row in results):
        security_event("cloud_dbt", "quality_gate_failed", status="blocked")
        raise ValueError("dbt test quality gate failed or did not execute")
    return {"status": "PASS", "tests_passed": len(results)}


def publish_ready(*, dag_run_id, sources, loads, gate):
    if gate["status"] != "PASS" or set(loads) != {"sales", "reviews"}:
        raise ValueError("Cloud dbt publication requires RAW loads and passing tests")
    batch_ids = {source["batch_id"] for source in sources.values()}
    if len(batch_ids) != 1 or any(loads[name]["batch_id"] not in batch_ids
                                  for name in ("sales", "reviews")):
        raise ValueError("Cloud dbt batch IDs do not reconcile")
    record = {"dag_run_id": dag_run_id, "batch_id": next(iter(batch_ids)),
              "source_hashes": {name: source["sha256"] for name, source in sources.items()},
              "dbt_test_count": gate["tests_passed"], "status": "READY",
              "published_at_utc": datetime.now(UTC).isoformat()}
    READY.parent.mkdir(parents=True, exist_ok=True)
    temporary = READY.with_name(READY.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(READY)
    return record
