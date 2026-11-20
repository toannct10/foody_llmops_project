"""Small, model-free CI evidence checks and machine-readable summaries."""

import argparse
import csv
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

OUT = Path("ci-artifacts")
TEST_GROUPS = {
    "rag_evaluation": ("test_rag_v3",),
    "text_to_sql": ("test_text_to_sql",),
    "airflow": ("test_airflow_batch", "test_cloud_foundation"),
    "observability": ("test_observability", "test_review2_devops"),
    "security": ("test_security",),
}


def write(name, value):
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def data_quality(root=Path("tests/fixtures/ci")):
    """Check a tiny stable relational fixture without reading local Foody data."""
    with (root / "sales.csv").open(encoding="utf-8", newline="") as stream:
        sales = list(csv.DictReader(stream))
    with (root / "reviews.csv").open(encoding="utf-8", newline="") as stream:
        reviews = list(csv.DictReader(stream))
    checks = {}
    checks["schema"] = all(set(row) == {"order_id", "restaurant_id", "status", "total_amount"}
                           for row in sales) and all(
        set(row) == {"review_id", "restaurant_id", "rating", "comment"}
        for row in reviews)
    checks["required_non_null"] = all(
        row["order_id"] and row["restaurant_id"] and row["status"] and row["total_amount"]
        for row in sales) and all(
            row["review_id"] and row["restaurant_id"] and row["rating"] and
            row["comment"].strip() for row in reviews)
    checks["unique_ids"] = (len({row["order_id"] for row in sales}) == len(sales) and
                            len({row["review_id"] for row in reviews}) == len(reviews))
    checks["accepted_values"] = all(
        row["status"] in {"Delivered", "Cancelled", "Refunded"} for row in sales)
    checks["referential_integrity"] = {row["restaurant_id"] for row in reviews} <= {
        row["restaurant_id"] for row in sales}
    try:
        amounts = [Decimal(row["total_amount"]) for row in sales]
        ratings = [Decimal(row["rating"]) for row in reviews]
        checks["business_rules"] = all(value >= 0 for value in amounts) and all(
            0 <= value <= 10 for value in ratings)
        delivered = sum((amount for row, amount in zip(sales, amounts, strict=True)
                         if row["status"] == "Delivered"), Decimal(0))
        checks["row_reconciliation"] = (sum(Counter(row["status"] for row in sales).values())
                                         == len(sales) and delivered == Decimal(175000))
    except InvalidOperation:
        checks["business_rules"] = False
        checks["row_reconciliation"] = False
    result = {"status": "PASS" if all(checks.values()) else "FAIL",
              "sales_rows": len(sales), "review_rows": len(reviews), "checks": checks,
              "fixture_only": True}
    write("data_quality", result)
    return result["status"] == "PASS"


def frozen_evaluation():
    """Validate checked-in benchmark evidence, never load a GGUF model."""
    from src.model_benchmark.dataset import load_manifest
    from src.model_benchmark.registry import load_registry
    from src.model_benchmark.service import load_history, selection

    manifest = load_manifest()
    registry, models = load_registry()
    selected = selection()
    runs = load_history(selected=selected)
    run = next((item for item in runs if item["run_id"] == selected["benchmark_run"]), None)
    summaries = run["summaries"] if run else {}
    checks = {
        "dataset_hash": selected["dataset_sha256"] == manifest["dataset_sha256"],
        "dataset_cases": len(manifest["cases"]) == 12,
        "unsafe_cases": sum(case["expected_safety_class"] == "UNSAFE"
                            for case in manifest["cases"]) == 2,
        "production_selection": selected["selected_model"] == "qwen" and
        models["qwen"].status == "production" and
        selected["production_change"] is False,
        "registry_candidates": set(models) == {"qwen", "llama", "deepseek"},
        "benchmark_run": run is not None and run["manifest"]["status"] == "COMPLETE",
        "summary_schema": set(summaries) == set(models) and all(
            item.get("status") == "COMPLETE" and item.get("case_count") == 12 and
            item.get("model_sha256") == models[key].sha256 and
            isinstance(item.get("structured_output_validity"), (int, float)) and
            isinstance(item.get("result_accuracy"), (int, float))
            for key, item in summaries.items()),
        "deterministic_generation": registry["temperature"] == 0,
    }
    result = {"status": "PASS" if all(checks.values()) else "FAIL",
              "mode": "FROZEN_ARTIFACT_NO_INFERENCE", "dataset_sha256": manifest["dataset_sha256"],
              "selected_model": selected["selected_model"], "benchmark_run": selected["benchmark_run"],
              "checks": checks}
    write("llm_evaluation", result)
    return result["status"] == "PASS"


def pytest_summary():
    root = ET.parse(OUT / "pytest.xml").getroot()
    cases = root.findall(".//testcase")
    failures = sum(bool(case.findall("failure") or case.findall("error")) for case in cases)
    skipped = sum(bool(case.findall("skipped")) for case in cases)
    result = {"status": "PASS" if cases and not failures else "FAIL",
              "tests": len(cases), "failed_or_errored": failures, "skipped": skipped}
    write("pytest", result)
    ok = result["status"] == "PASS"
    for group, files in TEST_GROUPS.items():
        selected = [case for case in cases if any(
            case.get("classname", "").endswith(filename) for filename in files)]
        count_failed = sum(bool(case.findall("failure") or case.findall("error"))
                           for case in selected)
        summary = {"status": "PASS" if selected and not count_failed else "FAIL",
                   "mode": "MOCKED_OR_DETERMINISTIC", "tests": len(selected),
                   "failed_or_errored": count_failed, "test_modules": list(files)}
        write(group, summary)
        ok &= summary["status"] == "PASS"
    return ok


def status(name, value):
    write(name, {"status": value})
    return value == "PASS"


def aggregate():
    names = ("quality", "pytest", "data_quality", "llm_evaluation", "rag_evaluation",
             "text_to_sql", "dbt_static", "airflow", "security", "observability",
             "secret_scan", "docker")
    results = {}
    for name in names:
        path = OUT / f"{name}.json"
        results[name] = json.loads(path.read_text(encoding="utf-8")).get("status", "FAIL") if (
            path.exists()) else "MISSING"
    commit = os.getenv("GITHUB_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
        check=False).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, check=False).stdout.strip())
    summary = {"git_commit": commit, "generated_at_utc": datetime.now(UTC).isoformat(),
               "working_tree_dirty": dirty, **results}
    jobs = {name: os.getenv(f"CI_{name.upper()}_JOB_RESULT") for name in
            ("python", "dbt", "docker")}
    summary["jobs"] = {name: value for name, value in jobs.items() if value is not None}
    summary["overall"] = "PASS" if (
        all(value == "PASS" for value in results.values()) and
        all(value == "success" for value in summary["jobs"].values())) else "FAIL"
    write("ci_acceptance", summary)
    lines = ["## Foody CI acceptance", "", f"Commit: `{commit}`", "",
             "| Check | Status |", "| --- | --- |"]
    lines += [f"| {name} | {value} |" for name, value in results.items()]
    lines += ["", f"Overall: **{summary['overall']}**", "",
              "GGUF inference and live AWS/Snowflake acceptance are outside automatic CI."]
    report = OUT / "ci_acceptance.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(report.read_text(encoding="utf-8"))
    return summary["overall"] == "PASS"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("data-quality", "frozen-evaluation", "pytest-summary",
                                           "status", "aggregate"))
    parser.add_argument("name", nargs="?")
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    actions = {"data-quality": data_quality, "frozen-evaluation": frozen_evaluation,
               "pytest-summary": pytest_summary, "aggregate": aggregate}
    if args.action == "status":
        if args.name not in {"quality", "dbt_static", "docker",
                              "secret_scan"} or (
                args.value not in {"PASS", "FAIL"}):
            parser.error("status requires a known check and PASS or FAIL")
        ok = status(args.name, args.value)
    else:
        ok = actions[args.action]()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
