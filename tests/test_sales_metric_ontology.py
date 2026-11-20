"""Sales metric, period, SQL and fallback contracts for observed orders."""

from datetime import date
from decimal import Decimal

import pytest

from src.sales import queries, service, text_to_sql
from src.sales.metric_ontology import UNITS
from src.sales.planner import build_sql_analytical_plan
from src.sales.semantic_fallback import answer_from_plan
from src.sales.semantic_plan import build_canonical_plan
from src.sales.text_to_sql import SQLRejected, validate_sql, verify_sql_plan
from src.ui.sales_view import normalize_sales_result


@pytest.mark.parametrize(("question", "metric", "unit"), [
    ("số đơn hàng năm 2026", "order_count", "orders"),
    ("số đơn hàng bị hủy trong năm 2026", "cancelled_order_count", "orders"),
    ("số tiền đơn hàng bị hủy trong năm 2026", "cancelled_order_value", "VND"),
    ("tỷ lệ hủy trong năm 2026", "cancellation_rate", "%"),
    ("số đơn hoàn tiền năm 2026", "refunded_order_count", "orders"),
    ("số tiền hoàn năm 2026", "refunded_order_value", "VND"),
    ("tỷ lệ hoàn tiền năm 2026", "refund_rate", "%"),
    ("doanh thu năm 2026", "delivered_sales", "VND"),
    ("AOV tháng 5 năm 2026", "average_order_value", "VND/order"),
    ("giá trị trung bình đơn hàng năm 2026", "average_order_value", "VND/order"),
])
def test_metric_ontology_preserves_quantity(question, metric, unit):
    plan = build_canonical_plan(question, today=date(2026, 11, 13))
    assert plan.metrics == (metric,)
    assert UNITS[metric] == unit


@pytest.mark.parametrize(("question", "periods", "shape"), [
    ("doanh thu tháng 6 năm 2025", ("2025-06",), "scalar"),
    ("doanh thu tháng 6 và 7 năm 2025", ("2025-06", "2025-07"), "grouped_rows"),
    ("tổng doanh thu tháng 5 và 6 năm 2025", ("2025-05", "2025-06"), "scalar"),
    ("doanh thu tháng 6 và tháng 7", ("2026-06", "2026-07"), "grouped_rows"),
    ("tổng doanh thu từ tháng 1 đến tháng 8 năm 2026",
     tuple(f"2026-{month:02d}" for month in range(1, 9)), "scalar"),
])
def test_revenue_periods_and_shape(question, periods, shape):
    plan = build_canonical_plan(question, today=date(2026, 11, 13))
    assert plan.time_scope.periods == periods
    assert plan.output_shape == shape


def _draft(sql, parameters, question, answer_type="single_value"):
    return validate_sql({"intent": "sales_metric", "sql": sql,
                         "parameters": parameters,
                         "tables_used": ["restaurant_monthly_order_status_values" if
                                         "order_status_values" in sql else
                                         "restaurant_monthly_sales"],
                         "reasoning_summary": "Read approved monthly measures",
                         "answer_type": answer_type}, text_to_sql.select_schema(question))


def test_status_view_is_narrow_and_prompt_has_scalar_shape():
    question = "số tiền đơn hàng bị hủy trong năm 2026"
    plan = build_sql_analytical_plan(question)
    schema = text_to_sql.select_schema(question)
    assert set(schema) == {"restaurant_monthly_order_status_values"}
    prompt_schema = text_to_sql._prompt_schema(schema, plan)
    assert "cancelled_order_value" in prompt_schema
    assert "sales_amount" not in prompt_schema
    assert '"output_shape":"scalar"' in text_to_sql._prompt_plan(plan)
    assert "year_total" not in text_to_sql.select_examples(question, schema)


def test_metric_type_rejects_count_value_swaps():
    params = {"restaurant_id": "2751", "start": "2026-01-01", "end": "2027-01-01"}
    prefix = (" FROM restaurant_monthly_order_status_values WHERE restaurant_id "
              "= %(restaurant_id)s AND period_start >= %(start)s "
              "AND period_start < %(end)s LIMIT 1")
    for question, expression in (
        ("số tiền đơn hàng bị hủy trong năm 2026",
         "SUM(cancelled_order_count) AS cancelled_order_value"),
        ("số đơn hàng bị hủy trong năm 2026",
         "SUM(cancelled_order_value) AS cancelled_order_count"),
    ):
        draft = _draft("SELECT " + expression + prefix, params, question)
        with pytest.raises(SQLRejected, match="metric_type"):
            verify_sql_plan(draft, build_sql_analytical_plan(question))


def test_rate_and_aov_reject_monthly_average_shortcuts():
    params = {"restaurant_id": "2751", "start": "2026-01-01", "end": "2027-01-01"}
    suffix = (" FROM restaurant_monthly_sales WHERE restaurant_id = "
              "%(restaurant_id)s AND period_start >= %(start)s AND "
              "period_start < %(end)s LIMIT 1")
    for question, expression in (
        ("tỷ lệ hủy trong năm 2026", "AVG(cancellation_rate) AS cancellation_rate"),
        ("AOV năm 2026", "AVG(aov) AS average_order_value"),
    ):
        draft = _draft("SELECT " + expression + suffix, params, question)
        with pytest.raises(SQLRejected, match="plan_aggregation|metric_type"):
            verify_sql_plan(draft, build_sql_analytical_plan(question))


def test_annual_rate_prompt_and_retry_keep_weighted_semantics():
    question = "tỷ lệ hủy trong năm 2026"
    plan = build_sql_analytical_plan(question)
    schema = text_to_sql.select_schema(question)
    example = text_to_sql.select_examples(question, schema)
    assert "SUM(cancelled_count)::numeric / NULLIF(SUM(order_count), 0)" in example
    assert "FILTER" not in example
    feedback = text_to_sql._repair_message(SQLRejected("function_allowlist"), plan)
    assert "SUM(cancelled_count)::numeric / NULLIF(SUM(order_count), 0)" in feedback
    assert "do not use FILTER" in feedback
    sql = ("SELECT SUM(cancelled_count)::numeric / NULLIF(SUM(order_count), 0) "
           "AS cancellation_rate FROM restaurant_monthly_sales WHERE "
           "restaurant_id = %(restaurant_id)s AND "
           "period_start >= %(start)s AND period_start < %(end)s LIMIT 1")
    draft = _draft(sql, {"restaurant_id": "2751", "start": "2026-01-01",
                         "end": "2027-01-01"}, question)
    verify_sql_plan(draft, plan)


def test_only_numeric_sum_cast_is_allowed():
    question = "tỷ lệ hủy trong năm 2026"
    params = {"restaurant_id": "2751", "start": "2026-01-01",
              "end": "2027-01-01"}
    sql = ("SELECT SUM(cancelled_count)::text AS cancellation_rate "
           "FROM restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s "
           "AND period_start >= %(start)s AND period_start < %(end)s LIMIT 1")
    with pytest.raises(SQLRejected, match="cast_type"):
        _draft(sql, params, question)


def test_equivalent_exact_month_filters_and_broader_range():
    question = "tổng doanh thu tháng 5 và 6 năm 2025"
    base = ("SELECT SUM(delivered_sales) AS delivered_sales FROM "
            "restaurant_monthly_sales WHERE restaurant_id = %(restaurant_id)s ")
    for end, accepted in (("2025-07-01", True), ("2025-08-01", False)):
        draft = _draft(base + "AND period_start >= %(start)s AND period_start < "
                       "%(end)s LIMIT 1",
                       {"restaurant_id": "2751", "start": "2025-05-01", "end": end},
                       question)
        if accepted:
            text_to_sql.verify_question_scope(draft, question)
            verify_sql_plan(draft, build_sql_analytical_plan(question))
        else:
            with pytest.raises(SQLRejected, match="period_scope"):
                text_to_sql.verify_question_scope(draft, question)


def test_fallback_keeps_exact_months_and_cancelled_value(monkeypatch):
    months = {"2025-06": Decimal("40"), "2025-07": Decimal("60")}
    monkeypatch.setattr(queries, "monthly_sales_range", lambda *_: [
        {"period_start": date.fromisoformat(month + "-01"),
         "delivered_sales": value, "order_count": 1, "delivered_count": 1}
        for month, value in months.items()])
    grouped = answer_from_plan(None, "2751", {}, build_canonical_plan(
        "doanh thu tháng 6 và 7 năm 2025"), today=date(2026, 11, 13))
    assert [row["delivered_sales"] for row in grouped["display_rows"]] == [40, 60]
    monkeypatch.setattr(queries, "monthly_status_values_range", lambda *_: [
        {"period_start": date(2026, 5, 1), "cancelled_order_count": 2,
         "cancelled_order_value": Decimal("70000"), "order_count": 10},
        {"period_start": date(2026, 6, 1), "cancelled_order_count": 1,
         "cancelled_order_value": Decimal("30000"), "order_count": 5}])
    value = answer_from_plan(None, "2751", {}, build_canonical_plan(
        "số tiền đơn hàng bị hủy trong năm 2026"), today=date(2026, 11, 13))
    assert value["display_rows"][0]["cancelled_order_value"] == 100000
    assert value["query_plan"]["result_unit"] == "VND"
    assert "100,000 ₫" in value["answer"]
    view = normalize_sales_result(value)
    assert ("Value", "100.000 ₫") in view.kpis


def test_forced_qwen_rejection_keeps_same_plan_and_units(monkeypatch):
    monkeypatch.setattr(text_to_sql, "enabled", lambda: True)
    monkeypatch.setattr(text_to_sql, "answer_with_text_to_sql",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            SQLRejected("forced_rejection")))
    monkeypatch.setattr(service, "_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(queries, "monthly_sales_range", lambda *_args: [
        {"period_start": date(2025, 6, 1), "delivered_sales": 40,
         "order_count": 1, "delivered_count": 1},
        {"period_start": date(2025, 7, 1), "delivered_sales": 60,
         "order_count": 1, "delivered_count": 1}])
    monkeypatch.setattr(queries, "monthly_status_values_range", lambda *_args: [
        {"period_start": date(2026, 5, 1), "cancelled_order_count": 2,
         "cancelled_order_value": Decimal("70000"), "order_count": 10},
        {"period_start": date(2026, 6, 1), "cancelled_order_count": 1,
         "cancelled_order_value": Decimal("30000"), "order_count": 5}])

    class Connection:
        def execute(self, *_args):
            raise AssertionError("Only approved query functions should run")

    grouped = service.sales_answer(Connection(), "2751",
                                   "doanh thu tháng 6 và 7 năm 2025",
                                   today=date(2026, 11, 13))
    value = service.sales_answer(Connection(), "2751",
                                 "số tiền đơn hàng bị hủy trong năm 2026",
                                 today=date(2026, 11, 13))
    assert grouped["execution_mode"] == value["execution_mode"] == \
        "DETERMINISTIC_FALLBACK"
    assert [item["delivered_sales"] for item in grouped["display_rows"]] == [40, 60]
    assert value["display_rows"][0]["cancelled_order_value"] == 100000
    assert value["query_plan"]["result_unit"] == "VND"
    assert value["sql_details"]["fallback_reason"] == "forced_rejection"


@pytest.mark.parametrize(("metric", "unit", "value", "fragment"), [
    ("cancelled_order_value", "VND", 148512, "₫"),
    ("cancelled_order_count", "orders", 1, "orders"),
    ("cancellation_rate", "%", 0.0208, "%"),
])
def test_ui_value_unit_tracks_metric(metric, unit, value, fragment):
    result = {"status": "ok", "execution_mode": "QWEN_TEXT_TO_SQL",
              "answer": "Verified result", "display_rows": [{metric: value}],
              "query_plan": {"intent": "aggregate", "metric": metric,
                             "result_unit": unit, "output_shape": "scalar",
                             "periods": ["2026"]},
              "sql_details": {"answer_type": "single_value"}}
    view = normalize_sales_result(result)
    assert any(name == "Value" and fragment in shown for name, shown in view.kpis)
