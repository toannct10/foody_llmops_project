"""General Cross taxonomy and evidence invariants, independent of Qwen output."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.sales import cross_intelligence as cross

MATRIX = json.loads(Path("data/evaluation/cross_intelligence_cases.json").read_text(
    encoding="utf-8"))["cases"]


@pytest.mark.parametrize("item", MATRIX, ids=lambda item: item["id"])
def test_general_cross_matrix_preserves_taxonomy_and_entity(item):
    plan = cross.build_cross_plan(item["question"], item["restaurant_id"],
                                  today=date(2026, 11, 15),
                                  default_periods=("2025-05", "2025-06"))
    assert plan.intent == item["category"]
    assert plan.mode == "cross_analysis"
    assert plan.restaurant_id == item["restaurant_id"]
    assert plan.periods and len(plan.periods) == len(set(plan.periods))
    assert plan.need_review_evidence


def test_matrix_covers_all_requested_categories_and_missing_data():
    assert len(MATRIX) >= 30
    assert {item["category"] for item in MATRIX} == {
        "WHY_CHANGE", "CORRELATION", "PERIOD_EXPLANATION",
        "LOW_PERFORMANCE_REVIEW", "HIGH_PERFORMANCE_REVIEW", "ASPECT_VS_SALES",
        "SENTIMENT_VS_SALES", "MISMATCH", "CROSS_TREND"}
    assert {item["scenario"] for item in MATRIX} >= {
        "NO_SALES", "NO_REVIEW_EVIDENCE", "PARTIAL_YEAR",
        "SALES_NO_REVIEWS", "REVIEWS_NO_SALES", "PARTIAL_MONTH"}


def test_why_one_month_discloses_inferred_comparison_month():
    plan = cross.build_cross_plan("Vì sao doanh thu tháng 6/2025 giảm?", "1062")
    assert plan.periods == ("2025-05", "2025-06")
    assert plan.period_source == "inferred_previous_month"


def test_quantitative_drivers_keep_count_value_rate_and_zero_baseline_distinct():
    facts = [
        {"period": "2025-05", "delivered_sales": 100, "order_count": 5,
         "delivered_count": 4, "aov": 25, "cancelled_order_count": 0,
         "cancelled_order_value": 0, "cancellation_rate": 0,
         "refunded_order_count": 1, "refunded_order_value": 10,
         "refund_rate": 0.2},
        {"period": "2025-06", "delivered_sales": 80, "order_count": 4,
         "delivered_count": 2, "aov": 40, "cancelled_order_count": 1,
         "cancelled_order_value": 30, "cancellation_rate": 0.25,
         "refunded_order_count": 1, "refunded_order_value": 10,
         "refund_rate": 0.25},
    ]
    drivers = {item["metric"]: item for item in cross.calculate_sales_drivers(facts)}
    assert drivers["delivered_sales"]["absolute_change"] == -20
    assert drivers["delivered_sales"]["percentage_change"] == -20
    assert drivers["delivered_count"]["absolute_change"] == -2
    assert drivers["aov"]["percentage_change"] == 60
    assert drivers["cancelled_order_value"]["current"] == 30
    assert drivers["cancelled_order_count"]["percentage_change"] is None
    assert drivers["cancellation_rate"]["percentage_point_change"] == 25


def test_warehouse_evidence_check_drops_unknown_id_other_entity_and_date():
    class Connection:
        def execute(self, sql, params):
            assert "r.restaurant_id=%s" in sql
            assert params[0] == "1062"
            return SimpleNamespace(fetchall=lambda: [
                ("right", "1062", date(2025, 6, 15)),
                ("other-date", "1062", date(2025, 7, 1))])

    evidence = [
        {"ref": "E1", "review_id": "right", "period": "2025-06",
         "date": "2025-06-15"},
        {"ref": "E2", "review_id": "missing", "period": "2025-06",
         "date": "2025-06-20"},
        {"ref": "E3", "review_id": "other-date", "period": "2025-06",
         "date": "2025-06-30"},
    ]
    accepted = cross._verify_evidence_in_warehouse(
        Connection(), "1062", ["2025-06"], evidence)
    assert [item["review_id"] for item in accepted] == ["right"]


def test_ranked_low_month_restricts_review_scope(monkeypatch):
    monkeypatch.setattr(cross, "new_corpus_active", lambda: True)
    monkeypatch.setattr(cross.queries, "restaurant", lambda *_: {
        "restaurant_name": "A", "review_restaurant_id": "1062"})
    monkeypatch.setattr(cross, "_sales_facts", lambda *_: (
        [{"period": "2025-05", "delivered_sales": 100},
         {"period": "2025-06", "delivered_sales": 80}],
        {"mode": "PREDEFINED_PARAMETERIZED_SQL", "sql": "SELECT ...",
         "semantic_verification": "PASS", "missing_periods": []}))
    requested = []

    def review(_conn, _id, period):
        requested.append(period)
        return {"period": period, "review_count": 0, "positive_count": 0,
                "neutral_count": 0, "negative_count": 0,
                "aspect_frequencies": {}, "sentiment_rate": {}}

    monkeypatch.setattr(cross, "monthly_review_aggregate", review)
    from src.sales import service

    monkeypatch.setattr(service, "_record", lambda *_args, **_kwargs: None)
    result = cross.analyze_cross(None, "1062",
                                 "Tháng doanh thu thấp nhất năm 2025 khách hàng phàn nàn gì?",
                                 today=date(2026, 11, 15))
    assert result["plan"]["intent"] == "LOW_PERFORMANCE_REVIEW"
    assert result["plan"]["periods"] == ("2025-06",)
    assert requested == ["2025-06"]
    assert "Thiếu Review: 2025-06" in result["missing_data"]
