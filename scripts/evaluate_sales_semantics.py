"""Read-only live acceptance for the canonical Sales planner and fallback."""

import json
import os
import runpy
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.sales.semantic_plan import build_canonical_plan, verify_result_shape
from src.sales.service import sales_answer
from src.warehouse.loader import connection

QUESTIONS = (
    "tổng doanh thu tháng 5 năm 2025",
    "tổng doanh thu tháng 5, 6, 7 năm 2025",
    "tổng doanh thu từ tháng 1 đến tháng 8 năm 2026",
    "xu hướng doanh thu từ tháng 1 đến tháng 8 năm 2026",
    "doanh thu năm 2025 và năm 2026",
    "2026 tăng bao nhiêu % so với 2025",
    "top 5 tháng doanh thu cao nhất năm 2025",
    "tháng nào doanh thu thấp nhất năm 2025",
    "doanh thu và số đơn tháng 5 năm 2025",
    "tỷ lệ hủy quý 2 năm 2025",
)


def _money(value):
    return Decimal(str(value))


def _check(result, plan, raw):
    """Compare response facts to an independent, fixed PostgreSQL mart read."""
    rows = result.get("display_rows") or []
    scope = plan.time_scope
    observed = [month for month in scope.periods if month in raw]
    missing = [month for month in scope.periods if month not in raw]
    assert result["status"] == "ok"
    assert result["query_plan"]["missing_periods"] == missing
    if rows:
        verify_result_shape(rows, plan)
    if plan.operation in {"aggregate", "range_aggregate"}:
        expected = sum((_money(raw[month]["delivered_sales"]) for month in observed),
                       Decimal(0))
        actual = (result["sql_facts"]["delivered_sales"] if not rows else
                  rows[0]["delivered_sales"])
        assert _money(actual) == expected
    elif plan.operation == "trend":
        assert [str(row["period_start"])[:7] for row in rows] == sorted(observed)
        assert all(_money(row["delivered_sales"]) ==
                   _money(raw[str(row["period_start"])[:7]]["delivered_sales"])
                   for row in rows)
    elif plan.operation in {"comparison", "growth"}:
        for group in scope.groups:
            year = group[0][:4]
            expected = sum((_money(raw[month]["delivered_sales"]) for month in group
                            if month in raw), Decimal(0))
            matched = next(row for row in rows if str(row.get("year",
                           row.get("period"))) == year)
            assert _money(matched["delivered_sales"]) == expected
        if plan.operation == "growth":
            assert _money(rows[-1]["absolute_change"]) == (
                _money(rows[1]["delivered_sales"]) -
                _money(rows[0]["delivered_sales"]))
    elif plan.operation == "ranking":
        expected = sorted(observed, key=lambda month:
                          _money(raw[month]["delivered_sales"]),
                          reverse=plan.sort == ("descending",))[:plan.limit]
        assert [str(row["period_start"])[:7] for row in rows] == expected
    elif plan.operation == "multi_metric":
        assert _money(rows[0]["delivered_sales"]) == sum(
            (_money(raw[month]["delivered_sales"]) for month in observed), Decimal(0))
        assert _money(rows[0]["order_count"]) == sum(
            (_money(raw[month]["order_count"]) for month in observed), Decimal(0))
    elif plan.operation == "rate":
        numerator = sum(raw[month]["cancelled_count"] for month in observed)
        denominator = sum(raw[month]["order_count"] for month in observed)
        assert abs(_money(rows[0]["cancellation_rate"]) -
                   Decimal(numerator) / Decimal(denominator)) < Decimal("0.000001")
    return {"question": plan.operation, "status": result["status"],
            "output_shape": plan.output_shape, "observed_months": len(observed),
            "missing_months": missing, "returned_rows": len(rows)}


def main():
    if os.getenv("TEXT_TO_SQL_ENABLED", "").lower() != "false":
        raise SystemExit("Set TEXT_TO_SQL_ENABLED=false for bounded fallback evaluation")
    matrix = runpy.run_path("tests/test_sales_semantic_plan.py")["CASES"]
    matrix_errors = {}
    matrix_counts = {}
    for expected, questions in matrix.items():
        matrix_counts[expected] = len(questions)
        for question in questions:
            try:
                actual = build_canonical_plan(question, today=date(2026, 11, 9)).operation
                if actual != expected:
                    matrix_errors[question] = {"expected": expected, "actual": actual}
            except ValueError as error:
                matrix_errors[question] = {"expected": expected, "error": str(error)}
    matrix_size = sum(matrix_counts.values())
    with connection() as conn:
        raw_rows = conn.execute(
            "SELECT period_start, delivered_sales, order_count, cancelled_count "
            "FROM restaurant_monthly_sales WHERE restaurant_id=%s",
            ("2751",),
        ).fetchall()
        raw = {str(row[0])[:7]: {"delivered_sales": row[1], "order_count": row[2],
                               "cancelled_count": row[3]} for row in raw_rows}
        checks = []
        for question in QUESTIONS:
            plan = build_canonical_plan(question, today=date(2026, 11, 9))
            result = sales_answer(conn, "2751", question, today=date(2026, 11, 9))
            checks.append({"question_text": question, **_check(result, plan, raw)})
    report = {
        "restaurant_id": "2751",
        "matrix_size": matrix_size,
        "matrix_operation_accuracy": {"correct": matrix_size - len(matrix_errors),
                                      "total": matrix_size},
        "matrix_categories": matrix_counts,
        "matrix_category_accuracy": {
            category: {"correct": count - sum(
                question in matrix_errors for question in matrix[category]),
                "total": count}
            for category, count in matrix_counts.items()
        },
        "matrix_errors": matrix_errors,
        "qwen_sql_semantic_accuracy_on_matrix": None,
        "live_fallback_execution_correctness": {"correct": len(checks), "total": len(QUESTIONS)},
        "live_result_shape_correctness": {"correct": len(checks), "total": len(QUESTIONS)},
        "live_categories": dict(Counter(check["question"] for check in checks)),
        "live_checks": checks,
        "qwen_range_trial": {"attempts": 2, "semantic_sql_acceptance": False,
                             "rejection": "plan_periods", "fallback_status": "ok"},
        "measurement_limitations": [
            "The 66-question matrix measures planner operation classification; it does "
            "not measure Qwen SQL execution on all 66 questions.",
            "One live Qwen range trial was rejected by the semantic verifier; "
            "no general Qwen SQL accuracy estimate follows from one trial.",
        ],
    }
    path = Path("reports/sales/SEMANTIC_FRAMEWORK_EVALUATION.json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(json.dumps({"matrix": f"{matrix_size - len(matrix_errors)}/{matrix_size}",
                      "live": f"{len(checks)}/{len(QUESTIONS)}",
                      "report": str(path)}))


if __name__ == "__main__":
    main()
