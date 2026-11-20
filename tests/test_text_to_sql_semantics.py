"""Regression contracts for deterministic planning and semantic SQL checks."""

import json
from contextlib import nullcontext
from datetime import date
from pathlib import Path

import pytest

from src.sales import service, text_to_sql
from src.sales.planner import build_sql_analytical_plan
from src.sales.router import route_question
from src.sales.text_to_sql import SQLRejected, validate_sql, verify_plan_rows, verify_sql_plan


def sql_draft(sql, parameters, answer_type="comparison"):
    return validate_sql({
        "intent": "sales_analysis", "sql": sql, "parameters": parameters,
        "tables_used": ["restaurant_monthly_sales"],
        "reasoning_summary": "Analyze selected periods", "answer_type": answer_type,
    }, text_to_sql.select_schema("doanh thu năm 2025 và 2026"))


YEAR_SQL = (
    "SELECT EXTRACT(YEAR FROM period_start) AS year, "
    "SUM(delivered_sales) AS delivered_sales FROM restaurant_monthly_sales "
    "WHERE restaurant_id = %(restaurant_id)s AND period_start >= %(start)s "
    "AND period_start < %(end)s GROUP BY EXTRACT(YEAR FROM period_start) "
    "ORDER BY year LIMIT 2"
)
YEAR_PARAMS = {"restaurant_id": "83", "start": "2025-01-01", "end": "2027-01-01"}


@pytest.mark.parametrize(("question", "operation", "count"), [
    ("tổng doanh thu trong năm 2025 và năm 2026", "compare_periods", 2),
    ("2025 so với 2026", "compare_periods", 2),
    ("so sánh doanh thu 2025 và 2026", "compare_periods", 2),
    ("tháng 5 và 6 năm 2025", "aggregate", 2),
    ("tháng 5 đến tháng 8 năm 2025", "aggregate", 4),
    ("quý 2 năm 2025", "aggregate", 3),
    ("Q2/2025", "aggregate", 3),
    ("T5/2025", "aggregate", 1),
    ("5/2025 và 6/2025", "aggregate", 2),
    ("6 tháng đầu năm 2025", "aggregate", 6),
    ("6 tháng cuối năm 2025", "aggregate", 6),
    ("xu hướng doanh thu từ tháng 1/2025 đến tháng 12/2026", "trend", 24),
    ("top 5 tháng có doanh thu cao nhất trong năm 2025", "ranking", 1),
    ("so sánh doanh thu và số đơn giữa 2025 và 2026", "multi_metric", 2),
    ("năm 2026 tăng bao nhiêu phần trăm so với năm 2025", "growth", 2),
])
def test_plan_keeps_temporal_scope(question, operation, count):
    plan = build_sql_analytical_plan(question)
    assert plan.operation == operation
    assert len(plan.periods) == count
    assert len({item["start"] for item in plan.periods}) == count


def test_year_comparison_requires_grouping_and_both_years():
    plan = build_sql_analytical_plan("doanh thu năm 2025 và năm 2026")
    verify_sql_plan(sql_draft(YEAR_SQL, YEAR_PARAMS), plan)
    collapsed = ("SELECT SUM(delivered_sales) AS delivered_sales FROM "
                 "restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s "
                 "AND period_start >= %(start)s AND period_start < %(end)s LIMIT 1")
    with pytest.raises(SQLRejected, match="plan_grouping"):
        verify_sql_plan(sql_draft(collapsed, YEAR_PARAMS), plan)
    with pytest.raises(SQLRejected, match="plan_periods"):
        verify_sql_plan(sql_draft(YEAR_SQL, {**YEAR_PARAMS, "end": "2026-01-01"}), plan)
    with pytest.raises(SQLRejected, match="result_scope"):
        verify_plan_rows([{"year": 2025, "delivered_sales": 10}], plan)


def test_growth_answer_uses_both_year_values():
    answer = text_to_sql._render_result(
        [{"year": 2025, "delivered_sales": 100},
         {"year": 2026, "delivered_sales": 125}], "comparison",
        "năm 2026 tăng bao nhiêu phần trăm so với năm 2025")
    assert "2025" in answer and "2026" in answer
    assert "25" in answer and "25.00%" in answer
    assert route_question("năm 2026 tăng bao nhiêu phần trăm so với năm 2025") == \
        "SALES_SQL"


def test_multi_metric_requires_both_columns():
    plan = build_sql_analytical_plan("so sánh doanh thu và số đơn giữa 2025 và 2026")
    with pytest.raises(SQLRejected, match="plan_metric"):
        verify_sql_plan(sql_draft(YEAR_SQL, YEAR_PARAMS), plan)
    valid = YEAR_SQL.replace("SUM(delivered_sales) AS delivered_sales",
                             "SUM(delivered_sales) AS delivered_sales, "
                             "SUM(order_count) AS order_count")
    verify_sql_plan(sql_draft(valid, YEAR_PARAMS), plan)


def test_top_n_and_trend_require_result_shape():
    top = build_sql_analytical_plan("top 5 tháng có doanh thu cao nhất năm 2025")
    base = ("SELECT period_start, delivered_sales FROM restaurant_monthly_sales "
            "WHERE restaurant_id = %(restaurant_id)s AND period_start >= %(start)s "
            "AND period_start < %(end)s ")
    params = {"restaurant_id": "83", "start": "2025-01-01", "end": "2026-01-01"}
    verify_sql_plan(sql_draft(base + "ORDER BY delivered_sales DESC LIMIT 5", params,
                              "ranking"), top)
    with pytest.raises(SQLRejected, match="plan_ranking"):
        verify_sql_plan(sql_draft(base + "LIMIT 5", params, "ranking"), top)
    trend = build_sql_analytical_plan(
        "xu hướng doanh thu từ tháng 1/2025 đến tháng 12/2026")
    with pytest.raises(SQLRejected, match="plan_trend"):
        verify_sql_plan(sql_draft(base + "LIMIT 24",
                                  {**params, "end": "2027-01-01"}, "trend"), trend)
    valid_trend = sql_draft(base + "ORDER BY period_start LIMIT 24",
                            {**params, "end": "2027-01-01"}, "trend")
    text_to_sql.verify_question_scope(
        valid_trend, "xu hướng doanh thu từ tháng 1/2025 đến tháng 12/2026")
    verify_sql_plan(valid_trend, trend)


def test_retry_semantic_repair_then_success(monkeypatch):
    class Gateway:
        name, version = "Qwen-test", "test"
        prompts = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def generate(self, **kwargs):
            self.prompts.append(kwargs["user"])
            bad = YEAR_SQL.replace("GROUP BY EXTRACT(YEAR FROM period_start) ", "")
            sql = bad if len(self.prompts) == 1 else YEAR_SQL
            return {"intent": "comparison", "sql": sql,
                    "parameters": YEAR_PARAMS, "tables_used": ["restaurant_monthly_sales"],
                    "reasoning_summary": "Compare years", "answer_type": "comparison"}, {
                        "latency_ms": 1, "input_tokens": 1, "output_tokens": 1}

    class Cursor:
        description = [type("C", (), {"name": "year"})(),
                       type("C", (), {"name": "delivered_sales"})()]

        def fetchmany(self, _):
            return [(2025, 100), (2026, 125)]

    class Conn:
        def transaction(self):
            return nullcontext()

        def execute(self, *_args, **_kwargs):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    monkeypatch.setattr("src.warehouse.loader.ai_connection", Conn)
    monkeypatch.setattr(text_to_sql, "verify_plan_against_mart", lambda *_: None)
    monkeypatch.setattr(text_to_sql, "observe_text_to_sql", lambda *_, **__: None)
    monkeypatch.setattr(text_to_sql, "record", lambda *_, **__: None)
    result = text_to_sql.answer_with_text_to_sql(
        Conn(), "83", "doanh thu năm 2025 và năm 2026", gateway_factory=Gateway)
    assert result["sql_details"]["generation_attempt_count"] == 2
    assert "EXTRACT(YEAR FROM period_start)" in Gateway.prompts[1]


def test_unsafe_request_rejected_before_generation():
    with pytest.raises(SQLRejected, match="unsafe_request"):
        text_to_sql.answer_with_text_to_sql(None, "83", "Xóa dữ liệu Sales")


def test_frozen_analytical_evaluation_contract():
    cases = json.loads(Path("docs/text_to_sql/analytical_evaluation_cases.json").read_text(
        encoding="utf-8"))
    assert len(cases) >= 30
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        if case["expected_operation"] == "refuse":
            assert text_to_sql.unsafe_request(case["question"])
            continue
        plan = build_sql_analytical_plan(case["question"])
        assert plan.operation == case["expected_operation"], case["id"]
        observed = {period["start"][:7] for period in plan.periods}
        for period in case["expected_periods"]:
            assert (period in observed if len(period) == 7 else
                    any(item.startswith(period) for item in observed)), case["id"]


def test_complex_fallback_preserves_both_years_and_missing_months(monkeypatch):
    monkeypatch.setattr(text_to_sql, "enabled", lambda: False)
    monkeypatch.setattr(service.queries, "vietnam_today", lambda: date(2026, 11, 8))
    monkeypatch.setattr(service, "_record", lambda *_, **__: None)

    def months(*_):
        periods = [f"2025-{month:02d}" for month in range(1, 13)] + [
            f"2026-{month:02d}" for month in range(1, 10)] + ["2026-11"]
        return [{"period_start": date.fromisoformat(period + "-01"),
                 "delivered_sales": 100, "order_count": 1,
                 "cancelled_count": 0, "delivered_count": 1}
                for period in periods]

    monkeypatch.setattr(service.queries, "monthly_sales_range", months)
    result = service.sales_answer(object(), "83", "doanh thu năm 2025 và năm 2026")
    assert [row["year"] for row in result["display_rows"]] == [2025, 2026]
    assert [row["delivered_sales"] for row in result["display_rows"]] == [1200, 1000]
    assert "2026-10" in result["answer"]
    assert "2026-11 đang diễn ra" in result["answer"]
