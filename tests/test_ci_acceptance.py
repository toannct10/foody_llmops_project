"""CI evidence checks stay small, deterministic, and model-free."""

import csv
import json
import shutil
from pathlib import Path

from scripts import ci_acceptance


def test_data_quality_fixture_passes_and_detects_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(ci_acceptance, "OUT", tmp_path / "artifacts")
    fixture = tmp_path / "fixture"
    shutil.copytree(Path("tests/fixtures/ci"), fixture)
    assert ci_acceptance.data_quality(fixture)
    result = json.loads((ci_acceptance.OUT / "data_quality.json").read_text())
    assert result["checks"]["row_reconciliation"]
    with (fixture / "sales.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[1]["order_id"] = rows[0]["order_id"]
    with (fixture / "sales.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    assert not ci_acceptance.data_quality(fixture)
    result = json.loads((ci_acceptance.OUT / "data_quality.json").read_text())
    assert result["status"] == "FAIL" and not result["checks"]["unique_ids"]


def test_frozen_evaluation_validates_checked_in_hashes(tmp_path, monkeypatch):
    monkeypatch.setattr(ci_acceptance, "OUT", tmp_path)
    assert ci_acceptance.frozen_evaluation()
    result = json.loads((tmp_path / "llm_evaluation.json").read_text())
    assert result["mode"] == "FROZEN_ARTIFACT_NO_INFERENCE"
    assert all(result["checks"].values())


def test_aggregate_marks_missing_evidence_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(ci_acceptance, "OUT", tmp_path)
    for name in ("quality", "pytest", "data_quality", "llm_evaluation", "rag_evaluation",
                 "text_to_sql", "dbt_static", "airflow", "security", "observability",
                 "secret_scan", "docker"):
        ci_acceptance.status(name, "PASS")
    assert ci_acceptance.aggregate()
    (tmp_path / "docker.json").unlink()
    assert not ci_acceptance.aggregate()
    result = json.loads((tmp_path / "ci_acceptance.json").read_text())
    assert result["docker"] == "MISSING" and result["overall"] == "FAIL"
