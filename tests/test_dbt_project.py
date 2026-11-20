"""Offline dbt project and cloud quality-gate contract checks."""

import json
from pathlib import Path

import pytest
import yaml

from src import cloud_dbt

ROOT = Path(__file__).resolve().parents[1] / "dbt"


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_dbt_project_and_source_contract():
    project = yaml.safe_load(read("dbt_project.yml"))
    assert project["name"] == "foody_cloud_analytics"
    assert project["profile"] == "foody_cloud_analytics"
    assert project["models"]["foody_cloud_analytics"]["staging"]["+schema"] == "STAGING"
    assert project["models"]["foody_cloud_analytics"]["marts"]["+schema"] == "MART"
    sources = yaml.safe_load(read("models/staging/sources.yml"))["sources"][0]
    assert {table["name"] for table in sources["tables"]} == {
        "SALES_SOURCE", "REVIEWS_SOURCE", "LOAD_AUDIT"}
    assert sources["config"]["loaded_at_field"] == "LOADED_AT"
    assert sources["config"]["freshness"]["warn_after"]["count"] == 30
    assert "UNCONFIGURED" in read("profiles.yml")
    assert "generate_schema_name" in read("macros/generate_schema_name.sql")


def test_required_models_and_incremental_keys():
    models = {path.stem for path in (ROOT / "models").rglob("*.sql")}
    assert models == {"stg_sales", "stg_reviews", "dim_restaurant", "fact_order",
                      "fact_review", "restaurant_daily_sales", "restaurant_weekly_sales",
                      "restaurant_monthly_sales", "restaurant_sales_summary",
                      "restaurant_monthly_reviews"}
    for name, key in (("stg_sales", "order_id"), ("stg_reviews", "review_id"),
                      ("fact_order", "order_id"), ("fact_review", "review_id")):
        matches = list((ROOT / "models").rglob(f"{name}.sql"))
        assert len(matches) == 1
        sql = matches[0].read_text(encoding="utf-8").lower()
        assert "materialized='incremental'" in sql
        assert f"unique_key='{key}'" in sql
        assert "is_incremental()" in sql
        assert "source_loaded_at" in sql


def test_business_rules_and_custom_tests_present():
    daily = read("models/marts/restaurant_daily_sales.sql").lower()
    metrics = read("macros/sales_metrics.sql")
    assert "'delivered'" in metrics.lower()
    assert "nullif" in metrics.lower()
    assert "cancellation_rate('cancelled_count', 'order_count')" in daily
    assert "refund_rate('refunded_count', 'order_count')" in daily
    assert "asia/ho_chi_minh" in daily
    assert "dayofweekiso" in read("models/marts/restaurant_weekly_sales.sql").lower()
    tests = {path.stem for path in (ROOT / "tests").glob("*.sql")}
    assert {"assert_raw_sales_unique_per_batch", "assert_raw_batch_audit_counts",
            "assert_valid_sales_amounts", "assert_valid_ratings",
            "assert_delivered_only_revenue", "assert_mart_row_consistency",
            "assert_unique_mart_periods"}.issubset(tests)
    stage_schema = read("models/staging/schema.yml")
    mart_schema = read("models/marts/schema.yml")
    assert "accepted_values" in stage_schema and "relationships" in mart_schema
    assert "unique" in stage_schema and "not_null" in mart_schema


def test_cloud_dbt_opt_in_and_quality_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("FOODY_CLOUD_DBT_ENABLED", raising=False)
    with pytest.raises(ValueError, match="disabled"):
        cloud_dbt.require_enabled()
    monkeypatch.setenv("FOODY_CLOUD_DBT_ENABLED", "true")
    cloud_dbt.require_enabled()
    project = tmp_path / "dbt"
    (project / "target").mkdir(parents=True)
    monkeypatch.setattr(cloud_dbt, "PROJECT", project)
    artifact = project / "target/run_results.json"
    artifact.write_text(json.dumps({"results": [{"status": "pass"}, {"status": "pass"}]}))
    assert cloud_dbt.quality_gate() == {"status": "PASS", "tests_passed": 2}
    artifact.write_text(json.dumps({"results": [{"status": "fail"}]}))
    with pytest.raises(ValueError, match="quality gate"):
        cloud_dbt.quality_gate()


def test_publish_requires_matching_batches_and_passing_tests(tmp_path, monkeypatch):
    monkeypatch.setattr(cloud_dbt, "READY", tmp_path / "ready.json")
    sources = {name: {"batch_id": "same", "sha256": name} for name in ("sales", "reviews")}
    loads = {name: {"batch_id": "same"} for name in sources}
    published = cloud_dbt.publish_ready(dag_run_id="manual__test", sources=sources,
                                        loads=loads, gate={"status": "PASS", "tests_passed": 4})
    assert published["status"] == "READY"
    assert json.loads(cloud_dbt.READY.read_text())["dbt_test_count"] == 4
    with pytest.raises(ValueError, match="reconcile"):
        cloud_dbt.publish_ready(dag_run_id="manual__bad", sources=sources,
                                loads={"sales": loads["sales"],
                                       "reviews": {"batch_id": "wrong"}},
                                gate={"status": "PASS", "tests_passed": 4})
