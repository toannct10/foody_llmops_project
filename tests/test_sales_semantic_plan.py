"""Cross-product analytical contracts, not fixtures for one demo question."""

from datetime import date

import pytest

from src.sales import service
from src.sales.planner import sql_plan_from_canonical
from src.sales.semantic_fallback import answer_from_plan
from src.sales.semantic_plan import (
    build_canonical_plan,
    parse_time_scope,
    verify_result_shape,
)

TODAY = date(2026, 11, 9)
CASES = {
    "aggregate": [
        "tổng doanh thu tháng 5 năm 2025", "doanh thu tháng 6/2025",
        "doanh thu T7/2025", "doanh thu tháng 5 và 6 năm 2025",
        "tổng doanh thu tháng 5, 6, 7 năm 2025",
        "số đơn tháng 5 năm 2025", "AOV tháng 5 năm 2025",
        "doanh thu năm 2025", "doanh thu trung bình mỗi tháng năm 2025",
        "revenue tháng 8 năm 2025",
    ],
    "range_aggregate": [
        "tổng doanh thu từ tháng 1 đến tháng 8 năm 2026",
        "tổng doanh thu 5/2025 đến 8/2025",
        "tổng doanh thu T5 đến T8/2025",
        "tổng doanh thu quý 2 năm 2025", "tổng doanh thu Q2/2025",
        "tổng doanh thu 6 tháng đầu năm 2025",
        "AOV quý 2 năm 2025", "số đơn 6 tháng cuối năm 2025",
    ],
    "comparison": [
        "so sánh doanh thu tháng 5 và tháng 6 năm 2025",
        "doanh thu tháng 2 với tháng 3 năm 2026",
        "so sánh số đơn tháng 5 và tháng 6 năm 2025",
        "so sánh AOV tháng 5 và tháng 6 năm 2025",
        "so sánh doanh thu 5/2025 và 6/2025",
        "doanh thu năm 2025 và năm 2026",
        "2025 so với 2026 doanh thu",
        "doanh thu 2025 vs 2026",
        "so sánh doanh thu 2024 với 2025",
        "chênh lệch doanh thu năm 2025 và năm 2026",
    ],
    "trend": [
        "xu hướng doanh thu từ tháng 1 đến tháng 8 năm 2026",
        "xu hướng doanh thu 5/2025 đến 8/2025",
        "trend doanh thu quý 2 năm 2025",
        "xu hướng số đơn 6 tháng đầu năm 2025",
        "xu hướng doanh thu năm 2025",
        "trend revenue năm 2026",
        "xu hướng AOV từ tháng 1 đến tháng 6 năm 2025",
        "doanh thu 6 tháng gần đây xu hướng",
    ],
    "ranking": [
        "top 5 tháng doanh thu cao nhất năm 2025",
        "top 3 tháng doanh thu thấp nhất năm 2025",
        "tháng nào doanh thu thấp nhất năm 2026",
        "tháng nào doanh thu cao nhất năm 2025",
        "top 4 tháng số đơn cao nhất năm 2025",
        "top 2 tháng AOV cao nhất năm 2025",
        "top 5 tháng doanh thu cao nhất từ tháng 1 đến tháng 8 năm 2026",
        "top 3 tháng doanh thu thấp nhất quý 2 năm 2025",
    ],
    "growth": [
        "2026 tăng bao nhiêu % so với 2025",
        "doanh thu 2025 tăng trưởng so với 2024",
        "tăng trưởng doanh thu năm 2025 với năm 2026",
        "YoY doanh thu năm 2025 và năm 2026",
        "MoM doanh thu tháng 5 và tháng 6 năm 2025",
        "số đơn 2026 tăng bao nhiêu % so với 2025",
    ],
    "rate": [
        "tỷ lệ hủy tháng 5 năm 2025", "tỉ lệ hủy tháng 6/2025",
        "tỷ lệ hoàn tháng 5 năm 2025", "refund rate tháng 5 năm 2025",
        "tỷ lệ hủy quý 2 năm 2025", "tỷ lệ hoàn Q2/2025",
        "tỷ lệ hủy 6 tháng đầu năm 2026", "cancellation năm 2025",
    ],
    "multi_metric": [
        "doanh thu và số đơn tháng 5 năm 2025",
        "doanh thu và AOV quý 2 năm 2025",
        "doanh thu và tỷ lệ hủy năm 2025",
        "so sánh doanh thu và số đơn 2025 với 2026",
        "so sánh doanh thu và AOV năm 2025 và năm 2026",
        "doanh thu và tỷ lệ hoàn tháng 5 năm 2025",
        "số đơn và AOV năm 2025",
        "doanh thu và số đơn 6 tháng đầu năm 2026",
    ],
}


@pytest.mark.parametrize(("operation", "question"), [
    (operation, question) for operation, questions in CASES.items() for question in questions
])
def test_analytical_matrix_operation_and_scope(operation, question):
    plan = build_canonical_plan(question, today=TODAY)
    assert plan.operation == operation
    assert plan.metrics
    assert plan.time_scope.periods
    assert len(plan.time_scope.periods) == len(set(plan.time_scope.periods))
    assert len(plan.time_scope.bounds) == len(plan.time_scope.groups)
    assert plan.output_shape in {"scalar", "grouped_rows", "comparison",
                                 "time_series", "ranking", "multi_metric"}


def test_matrix_has_breadth_and_unique_questions():
    questions = [question for group in CASES.values() for question in group]
    assert len(questions) >= 60
    assert len(questions) == len(set(questions))
    assert len(CASES) == 8


@pytest.mark.parametrize(("question", "kind", "first", "last", "count"), [
    ("từ tháng 1 đến tháng 8 năm 2026", "continuous_range", "2026-01", "2026-08", 8),
    ("5/2025 đến 8/2025", "continuous_range", "2025-05", "2025-08", 4),
    ("T5 đến T8/2025", "continuous_range", "2025-05", "2025-08", 4),
    ("quý 2 năm 2025", "quarter", "2025-04", "2025-06", 3),
    ("6 tháng cuối năm 2025", "half_year", "2025-07", "2025-12", 6),
    ("năm 2025 và 2026", "multiple_years", "2025-01", "2026-12", 24),
])
def test_temporal_grammar_preserves_full_scope(question, kind, first, last, count):
    scope = parse_time_scope(question, today=TODAY)
    assert scope.kind == kind
    assert scope.periods[0] == first and scope.periods[-1] == last
    assert len(scope.periods) == count
    assert scope.bounds[0]["start"] == first + "-01"


@pytest.mark.parametrize(("question", "expected"), [
    ("doanh thu tháng 5/2026 YoY", ("2026-05", "2025-05")),
    ("doanh thu tháng 1/2026 so với tháng trước", ("2026-01", "2025-12")),
])
def test_relative_comparison_expands_both_sides(question, expected):
    plan = build_canonical_plan(question, today=TODAY)
    assert tuple(group[0] for group in plan.time_scope.groups) == expected
    assert plan.operation in {"comparison", "growth"}


def test_result_contract_rejects_collapsed_comparison_and_unordered_trend():
    comparison = build_canonical_plan("doanh thu năm 2025 và năm 2026", today=TODAY)
    with pytest.raises(ValueError, match="collapsed"):
        verify_result_shape([{"year": 2025, "delivered_sales": 1}], comparison)
    trend = build_canonical_plan("xu hướng doanh thu quý 2 năm 2025", today=TODAY)
    with pytest.raises(ValueError, match="chronological"):
        verify_result_shape([{"period_start": "2025-06-01", "delivered_sales": 1},
                             {"period_start": "2025-04-01", "delivered_sales": 2}], trend)


def test_ranking_limit_and_breakdown_reconciliation():
    ranking = build_canonical_plan("top 2 tháng doanh thu năm 2025", today=TODAY)
    with pytest.raises(ValueError, match="limit"):
        verify_result_shape([{"period_start": f"2025-0{i}-01"} for i in range(1, 4)], ranking)
    total = build_canonical_plan("tổng doanh thu quý 2 năm 2025 chi tiết từng tháng", today=TODAY)
    with pytest.raises(ValueError, match="reconcile"):
        verify_result_shape([{"delivered_sales": 10},
                             {"period": "2025-04", "delivered_sales": 3},
                             {"period": "2025-05", "delivered_sales": 4}], total)


def test_qwen_and_fallback_receive_one_canonical_plan(monkeypatch):
    from src.sales import text_to_sql

    captured = {}
    monkeypatch.setattr(text_to_sql, "enabled", lambda: True)

    def reject(*_, canonical_plan, **__):
        captured["qwen"] = canonical_plan
        raise RuntimeError("offline")

    def fallback(*_, canonical, **__):
        captured["fallback"] = canonical
        return {"route": "SALES_SQL", "status": "no_data", "answer": "No rows",
                "sql_facts": [], "query_plan": {}}

    monkeypatch.setattr(text_to_sql, "answer_with_text_to_sql", reject)
    monkeypatch.setattr(service, "_deterministic_sales_answer", fallback)
    monkeypatch.setattr(service, "_deterministic_analytical_answer", lambda *_, **__: None)
    service.sales_answer(object(), "2751", "tổng doanh thu tháng 5 năm 2025", today=TODAY)
    assert captured["qwen"] is captured["fallback"]


def _mart(monkeypatch, values):
    from src.sales import queries

    def rows(_conn, _id, start, end):
        return [{"period_start": date.fromisoformat(month + "-01"), **facts}
                for month, facts in values.items() if start <= month + "-01" < end]

    monkeypatch.setattr(queries, "monthly_sales_range", rows)


def test_fallback_range_sum_and_missing_periods(monkeypatch):
    _mart(monkeypatch, {"2025-04": {"delivered_sales": 100},
                        "2025-06": {"delivered_sales": 200}})
    plan = build_canonical_plan("tổng doanh thu quý 2 năm 2025", today=TODAY)
    result = answer_from_plan(None, "2751", {}, plan, today=TODAY)
    assert result["status"] == "ok"
    assert result["display_rows"][0]["delivered_sales"] == 300
    assert result["query_plan"]["observed_periods"] == ["2025-04", "2025-06"]
    assert result["query_plan"]["missing_periods"] == ["2025-05"]
    assert "2025-05" in result["answer"]


def test_fallback_trend_and_ranking_use_observed_rows(monkeypatch):
    _mart(monkeypatch, {"2025-04": {"delivered_sales": 100},
                        "2025-05": {"delivered_sales": 300},
                        "2025-06": {"delivered_sales": 200}})
    trend = build_canonical_plan("xu hướng doanh thu quý 2 năm 2025", today=TODAY)
    ranked = build_canonical_plan("top 2 tháng doanh thu cao nhất quý 2 năm 2025", today=TODAY)
    trend_rows = answer_from_plan(None, "2751", {}, trend, today=TODAY)["display_rows"]
    rank_rows = answer_from_plan(None, "2751", {}, ranked, today=TODAY)["display_rows"]
    assert [row["delivered_sales"] for row in trend_rows] == [100, 300, 200]
    assert [row["delivered_sales"] for row in rank_rows] == [300, 200]
    assert len(rank_rows) <= ranked.limit


def test_fallback_weighted_rate_and_multi_metric(monkeypatch):
    _mart(monkeypatch, {"2025-04": {"delivered_sales": 100, "order_count": 10,
                                    "delivered_count": 5, "cancelled_count": 2},
                        "2025-05": {"delivered_sales": 300, "order_count": 30,
                                    "delivered_count": 10, "cancelled_count": 3}})
    rate = build_canonical_plan("tỷ lệ hủy quý 2 năm 2025", today=TODAY)
    multiple = build_canonical_plan("doanh thu và số đơn quý 2 năm 2025", today=TODAY)
    rate_result = answer_from_plan(None, "2751", {}, rate, today=TODAY)
    multi_result = answer_from_plan(None, "2751", {}, multiple, today=TODAY)
    assert rate_result["display_rows"][0]["cancellation_rate"] == .125
    assert multi_result["display_rows"][0] == {"delivered_sales": 400.0,
                                                "order_count": 40.0}


def test_sql_verifier_checks_shape_and_weighted_rate():
    from types import SimpleNamespace

    from src.sales.text_to_sql import SQLRejected, verify_sql_plan

    total = sql_plan_from_canonical(build_canonical_plan(
        "tổng doanh thu quý 2 năm 2025", today=TODAY))
    parameters = {"start": "2025-04-01", "end": "2025-07-01"}
    monthly = SimpleNamespace(
        sql="SELECT period_start, delivered_sales FROM restaurant_monthly_sales "
            "WHERE period_start >= %(start)s AND period_start < %(end)s",
        parameters=parameters, answer_type="trend")
    with pytest.raises(SQLRejected, match="plan_result_shape"):
        verify_sql_plan(monthly, total)
    rate = sql_plan_from_canonical(build_canonical_plan(
        "tỷ lệ hủy quý 2 năm 2025", today=TODAY))
    bad_rate = SimpleNamespace(
        sql="SELECT AVG(cancellation_rate) AS cancellation_rate "
            "FROM restaurant_monthly_sales WHERE period_start >= %(start)s "
            "AND period_start < %(end)s", parameters=parameters,
        answer_type="single_value")
    with pytest.raises(SQLRejected, match="plan_aggregation"):
        verify_sql_plan(bad_rate, rate)


@pytest.mark.parametrize(("shape", "rows", "expected"), [
    ("comparison", [{"period": "2025", "delivered_sales": 100},
                    {"period": "2026", "delivered_sales": 90}], "comparison"),
    ("time_series", [{"period_start": "2025-04-01", "delivered_sales": 100},
                     {"period_start": "2025-05-01", "delivered_sales": 90}], "time_series"),
    ("ranking", [{"period_start": "2025-04-01", "delivered_sales": 100}], "ranking"),
    ("multi_metric", [{"delivered_sales": 100, "order_count": 2}], "multi_metric"),
])
def test_ui_uses_declared_output_shape(shape, rows, expected):
    from src.ui.sales_view import normalize_sales_result

    result = {"status": "ok", "answer": "Verified", "display_rows": rows,
              "execution_mode": "DETERMINISTIC_FALLBACK",
              "query_plan": {"output_shape": shape, "metric": "delivered_sales",
                             "metrics": ["delivered_sales", "order_count"]}}
    view = normalize_sales_result(result)
    assert view.preview_kind == expected
    if shape == "multi_metric":
        assert any("Order Count" in label for label, _ in view.kpis)


@pytest.mark.parametrize(("question", "shape", "row_count"), [
    ("tổng doanh thu từ tháng 1 đến tháng 8 năm 2026", "scalar", 1),
    ("xu hướng doanh thu từ tháng 1 đến tháng 8 năm 2026", "time_series", 2),
    ("tháng nào doanh thu thấp nhất năm 2026", "ranking", 1),
])
def test_live_service_fallback_uses_canonical_operation(
        monkeypatch, question, shape, row_count):
    from src.sales import queries

    _mart(monkeypatch, {"2026-01": {"delivered_sales": 100},
                        "2026-02": {"delivered_sales": 200}})
    monkeypatch.setattr(queries, "restaurant", lambda *_: {"restaurant_name": "Example"})
    monkeypatch.setattr(service, "_record", lambda *_, **__: None)
    monkeypatch.setenv("TEXT_TO_SQL_ENABLED", "false")
    class Connection:
        def execute(self, *_):
            raise AssertionError("The mocked monthly mart must handle this read")

    result = service.sales_answer(Connection(), "2751", question, today=TODAY)
    assert result["status"] == "ok"
    assert result["query_plan"]["output_shape"] == shape
    assert len(result["display_rows"]) == row_count
    assert "2026-03" in result["query_plan"]["missing_periods"]


def test_result_contract_rejects_wrong_comparison_side_and_ranking_order():
    comparison = build_canonical_plan("doanh thu năm 2025 và 2026", today=TODAY)
    with pytest.raises(ValueError, match="dropped"):
        verify_result_shape([{"year": 2025, "delivered_sales": 1},
                             {"year": 2027, "delivered_sales": 2}], comparison)
    ranking = build_canonical_plan("top 2 tháng doanh thu cao nhất năm 2025", today=TODAY)
    with pytest.raises(ValueError, match="sorted"):
        verify_result_shape([{"period_start": "2025-01-01", "delivered_sales": 1},
                             {"period_start": "2025-02-01", "delivered_sales": 2}], ranking)


def test_plan_validator_rejects_dropped_month():
    from dataclasses import replace

    from src.sales.semantic_plan import validate_plan

    plan = build_canonical_plan("tổng doanh thu quý 2 năm 2025", today=TODAY)
    broken_scope = replace(plan.time_scope, periods=("2025-04", "2025-06"))
    with pytest.raises(ValueError, match="dropped"):
        validate_plan(replace(plan, time_scope=broken_scope))
