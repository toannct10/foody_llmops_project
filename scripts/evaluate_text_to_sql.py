"""Run the frozen Vietnamese Sales cases against live Qwen and PostgreSQL."""

import argparse
import json
import os
import statistics
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter

import requests

from src.sales.service import sales_answer
from src.sales.text_to_sql import answer_with_text_to_sql
from src.warehouse.loader import connection

CASES = Path("docs/text_to_sql/evaluation_cases.json")
OUTPUT = Path("outputs/evaluation/text_to_sql_v1_results.json")
SCALAR_COLUMNS = {
    "revenue_month": "delivered_sales", "orders_month": "order_count",
    "aov_month": "aov", "cancel_rate": "cancellation_rate",
    "refund_rate": "refund_rate",
}
INTENTS = {
    "revenue_month": "monthly_revenue", "orders_month": "monthly_orders",
    "aov_month": "monthly_aov", "cancel_rate": "monthly_cancellation_rate",
    "refund_rate": "monthly_refund_rate", "yoy": "compare_revenue",
    "trend": "monthly_revenue_trend", "range": "range_revenue",
    "ranking": "top_revenue_restaurants",
    "cancel_ranking": "top_cancellation_rate_restaurant",
    "unsafe_delete": "refuse_destructive_request",
    "unsafe_secret": "refuse_credential_request",
}


def _reference(conn, restaurant_id, case_id):
    if case_id in SCALAR_COLUMNS:
        column = SCALAR_COLUMNS[case_id]
        return conn.execute(
            f"SELECT {column} FROM restaurant_monthly_sales "
            "WHERE restaurant_id=%s AND period_start=%s",
            (restaurant_id, "2026-05-01")).fetchone()[0]
    if case_id == "yoy":
        return dict(conn.execute(
            "SELECT period_start, delivered_sales FROM restaurant_monthly_sales "
            "WHERE restaurant_id=%s AND period_start IN (%s,%s)",
            (restaurant_id, "2026-05-01", "2025-05-01")).fetchall())
    if case_id == "trend":
        return dict(conn.execute(
            "SELECT period_start, delivered_sales FROM restaurant_monthly_sales "
            "WHERE restaurant_id=%s AND period_start BETWEEN %s AND %s",
            (restaurant_id, "2026-01-01", "2026-06-01")).fetchall())
    if case_id == "range":
        return conn.execute(
            "SELECT SUM(delivered_sales) FROM restaurant_monthly_sales "
            "WHERE restaurant_id=%s AND period_start BETWEEN %s AND %s",
            (restaurant_id, "2026-01-01", "2026-06-01")).fetchone()[0]
    if case_id == "ranking":
        return conn.execute(
            "SELECT restaurant_id, delivered_sales FROM restaurant_monthly_sales "
            "WHERE period_start=%s ORDER BY delivered_sales DESC, restaurant_id "
            "LIMIT 10", ("2026-05-01",)).fetchall()
    if case_id == "cancel_ranking":
        return conn.execute(
            "SELECT MAX(cancellation_rate) FROM restaurant_sales_summary").fetchone()[0]
    return None


def _number(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _close(actual, expected):
    left, right = _number(actual), _number(expected)
    return left is not None and right is not None and abs(left - right) <= Decimal("0.01")


def _correct(case_id, facts, expected):
    if case_id.startswith("unsafe_"):
        return facts is None
    if isinstance(facts, dict):
        facts = [facts]
    if not facts:
        return False
    if case_id in SCALAR_COLUMNS:
        return _close(facts[0].get(SCALAR_COLUMNS[case_id]), expected)
    if case_id in {"yoy", "trend"}:
        observed = {str(row.get("period_start"))[:10]: row.get("delivered_sales")
                    for row in facts}
        return (len(observed) == len(expected) and
                all(period.isoformat() in observed and
                    _close(observed[period.isoformat()], value)
                    for period, value in expected.items()))
    if case_id == "range":
        return any(_close(value, expected) for value in facts[0].values())
    if case_id == "ranking":
        return (len(facts) == 10 and
                all(str(row.get("restaurant_id")) == str(ref_id) and
                    _close(row.get("delivered_sales", row.get("metric_value")), revenue)
                    for row, (ref_id, revenue) in zip(facts, expected, strict=True)))
    if case_id == "cancel_ranking":
        return len(facts) == 1 and _close(
            facts[0].get("cancellation_rate", facts[0].get("metric_value")), expected)
    return False


def _percentile(values, percentage):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage
    lower = int(position)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] -
                             ordered[lower]) * (position - lower)


def _rate(cases, key):
    values = [case[key] for case in cases if case.get(key) is not None]
    return sum(values) / len(values) if values else None


def finalize_report(report):
    safe = [case for case in report["cases"] if case["category"] != "unsafe"]
    latencies = [case["total_latency_ms"] for case in safe]
    warm_generation = [case["generation_latency_ms"] for case in safe
                       if case["generation_latency_ms"] is not None]
    report["metrics"] = {
        "safe_case_count": len(safe),
        "structured_output_validity_rate": _rate(safe, "structured_output_valid"),
        "validator_pass_rate": _rate(safe, "validator_pass"),
        "execution_success_rate": _rate(safe, "execution_pass"),
        "qwen_only_success_rate": _rate(safe, "qwen_result_correctness"),
        "fallback_rate": _rate(safe, "fallback_used"),
        "end_to_end_answer_correctness_rate": _rate(report["cases"], "answer_correctness"),
        "mean_total_latency_ms": statistics.mean(latencies) if latencies else None,
        "median_total_latency_ms": statistics.median(latencies) if latencies else None,
        "p95_total_latency_ms": _percentile(latencies, 0.95),
        "mean_warm_generation_latency_ms": (
            statistics.mean(warm_generation) if warm_generation else None),
        "median_warm_generation_latency_ms": (
            statistics.median(warm_generation) if warm_generation else None),
        "p95_warm_generation_latency_ms": _percentile(warm_generation, 0.95),
    }
    report["status"] = ("EXECUTED" if report["evaluated_case_count"] ==
                        report["dataset_case_count"] else "PARTIAL_EXECUTED")
    return report


def _fallback(conn, restaurant_id, question):
    old = os.environ.get("TEXT_TO_SQL_ENABLED")
    os.environ["TEXT_TO_SQL_ENABLED"] = "false"
    try:
        return sales_answer(conn, restaurant_id, question)
    finally:
        if old is None:
            os.environ.pop("TEXT_TO_SQL_ENABLED", None)
        else:
            os.environ["TEXT_TO_SQL_ENABLED"] = old


def _run_case(conn, restaurant_id, case):
    start = perf_counter()
    attempts = []
    outcome = {
        "id": case["id"], "category": case["category"],
        "question": case["question"], "expected_intent": INTENTS[case["id"]],
        "attempts": attempts, "generated_sql": None,
        "structured_output_valid": None, "validator_pass": None,
        "execution_pass": None, "result_correctness": None,
        "qwen_result_correctness": False, "answer_correctness": False,
        "fallback_used": False, "execution_mode": None,
    }
    expected = _reference(conn, restaurant_id, case["id"])
    try:
        result = answer_with_text_to_sql(
            conn, restaurant_id, case["question"], audit_sink=attempts)
        outcome.update({"qwen_result_correctness": _correct(
            case["id"], result["sql_facts"], expected),
                        "result_correctness": _correct(
                            case["id"], result["sql_facts"], expected),
                        "answer_correctness": _correct(
                            case["id"], result["sql_facts"], expected),
                        "execution_mode": "QWEN_TEXT_TO_SQL",
                        "answer": result["answer"],
                        "sql_facts": result["sql_facts"]})
    except Exception as error:
        outcome["failure_category"] = getattr(error, "category", type(error).__name__)
        fallback = _fallback(conn, restaurant_id, case["question"])
        outcome.update({"execution_mode": fallback.get("execution_mode"),
                        "fallback_used": case["category"] != "unsafe",
                        "answer": fallback["answer"],
                        "fallback_status": fallback["status"],
                        "answer_correctness": (
                            fallback["status"] == "refused_unsafe_request"
                            if case["category"] == "unsafe" else
                            _correct(case["id"], fallback.get("sql_facts"), expected))})
        if outcome["failure_category"] == "result_mismatch":
            outcome["result_correctness"] = False
    for attempt in attempts:
        raw = attempt.pop("raw", [])
        if raw and not attempt.get("generated_sql"):
            attempt["invalid_raw_excerpt"] = raw[-1].get("raw_output", "")[:500]
    outcome["generated_sql"] = [item["generated_sql"] for item in attempts
                                if item.get("generated_sql")]
    outcome["structured_output_valid"] = (
        any(item.get("structured_output_valid") for item in attempts)
        if attempts else None)
    outcome["validator_pass"] = (
        any(item.get("validator") == "PASS" for item in attempts)
        if attempts else None)
    outcome["execution_pass"] = (
        any(item.get("execution") == "PASS" for item in attempts)
        if attempts else None)
    outcome["generation_latency_ms"] = (
        sum(item.get("generation_latency_ms") or 0 for item in attempts)
        if attempts else None)
    outcome["input_tokens"] = sum(item.get("input_tokens") or 0 for item in attempts)
    outcome["output_tokens"] = sum(item.get("output_tokens") or 0 for item in attempts)
    outcome["total_latency_ms"] = (perf_counter() - start) * 1000
    return outcome


def evaluate(limit=None):
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if limit is not None:
        cases = cases[:limit]
    endpoint = os.environ.get("QWEN_BASE_URL", "http://127.0.0.1:8193")
    response = requests.get(endpoint.rstrip("/") + "/health", timeout=5)
    response.raise_for_status()
    os.environ["QWEN_BASE_URL"] = endpoint
    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "model": "Qwen2.5-3B-Instruct-GGUF", "runtime": "llama.cpp CPU; PostgreSQL",
        "prompt_version": "text_to_sql_v1", "dataset_case_count": len(json.loads(
            CASES.read_text(encoding="utf-8"))),
        "evaluated_case_count": 0, "status": "RUNNING", "cases": [],
        "cold_start_seconds": (float(os.environ["QWEN_COLD_START_SECONDS"])
                               if os.environ.get("QWEN_COLD_START_SECONDS") else None),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        row = conn.execute(
            "SELECT restaurant_id FROM restaurant_monthly_sales "
            "WHERE period_start=%s ORDER BY delivered_sales DESC LIMIT 1",
            ("2026-05-01",)).fetchone()
        if row is None:
            raise RuntimeError("No May 2026 Sales mart rows")
        restaurant_id = str(row[0])
        report["restaurant_id"] = restaurant_id
        for case in cases:
            outcome = _run_case(conn, restaurant_id, case)
            report["cases"].append(outcome)
            report["evaluated_case_count"] = len(report["cases"])
            finalize_report(report)
            if report["evaluated_case_count"] < report["dataset_case_count"]:
                report["status"] = "PARTIAL_EXECUTED"
            OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                         default=str), encoding="utf-8")
            print(f"{case['id']}: {outcome['execution_mode']} "
                  f"{outcome['failure_category'] if 'failure_category' in outcome else 'ok'} "
                  f"{outcome['total_latency_ms'] / 1000:.1f}s", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    evaluate(args.limit)
