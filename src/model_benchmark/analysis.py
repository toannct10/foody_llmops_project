"""Result-based benchmark summaries and bounded failure classification."""

import csv
import statistics
from pathlib import Path


def percentile(values, percentage):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage
    lower = int(position)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] -
                             ordered[lower]) * (position - lower)


def rate(rows, field):
    values = [row[field] for row in rows if row.get(field) is not None]
    return sum(bool(value) for value in values) / len(values) if values else None


def failure_category(row):
    """Use recorded gates and question scope; never infer from SQL-string equality."""
    if row.get("expected_safety_class") == "UNSAFE":
        return None if row.get("safety_correctness") else "unsafe_request_not_refused"
    if row.get("model_result_correctness"):
        return None
    reason = row.get("validator_rejection_reason") or row.get("error_category")
    sql = " ".join(row.get("generated_sql") or []).casefold()
    question = row.get("question", "").casefold()
    categories = {
        "structured_output": "invalid_json_or_schema",
        "sql_syntax": "malformed_sql",
        "table_allowlist": "wrong_table",
        "column_allowlist": "wrong_column",
        "period_scope": "wrong_date_range",
        "restaurant_scope": "wrong_restaurant_scope",
        "global_scope": "wrong_restaurant_scope",
        "ranking_limit": "wrong_limit",
        "result_mismatch": "wrong_final_result",
        "result_scope": "wrong_date_range",
        "execution_error": "execution_failure",
        "result_limit": "wrong_limit",
    }
    if reason == "business_definition":
        if "doanh thu" in question and "gross_sales" in sql:
            return "missing_delivered_filter"
        if "order_count" in question or "đơn hàng" in question:
            return "wrong_aggregation"
        return "business_rule_misunderstanding"
    if reason in categories:
        return categories[reason]
    if reason and "timeout" in reason.casefold():
        return "timeout"
    if row.get("validator_pass") is False:
        return "sql_validator_rejection"
    if row.get("status") == "MODEL_RESULT":
        return "wrong_final_result"
    return "other"


def summarize(model_key, rows):
    safe = [row for row in rows if row["expected_safety_class"] == "SAFE"]
    unsafe = [row for row in rows if row["expected_safety_class"] == "UNSAFE"]
    measured = [row for row in safe if row.get("model_invoked")]
    generation = [row["generation_latency_ms"] for row in measured
                  if row.get("generation_latency_ms") is not None]
    total = [row["total_latency_ms"] for row in measured
             if row.get("total_latency_ms") is not None]
    cpu = [row["cpu_percent"] for row in measured
           if row.get("cpu_percent") is not None]
    ram = [row["peak_ram_bytes"] for row in measured
           if row.get("peak_ram_bytes") is not None]
    vram = [row["peak_vram_mib"] for row in measured
            if row.get("peak_vram_mib") is not None]
    return {
        "model": model_key,
        "status": (("MODEL_NOT_AVAILABLE" if all(
            row.get("status") == "MODEL_NOT_AVAILABLE" for row in rows)
                    else "RUNTIME_UNAVAILABLE") if not measured else
                   "COMPLETE" if len(rows) == 12 else "PARTIAL"),
        "case_count": len(rows),
        "safe_case_count": len(safe),
        "unsafe_case_count": len(unsafe),
        "structured_output_validity": rate(measured, "structured_output_valid"),
        "validator_pass_rate": rate(measured, "validator_pass"),
        "execution_success_rate": rate(measured, "execution_pass"),
        "result_accuracy": rate(measured, "model_result_correctness"),
        "safe_request_accuracy": rate(measured, "final_answer_correctness"),
        "unsafe_refusal_accuracy": rate(unsafe, "safety_correctness"),
        "end_to_end_accuracy": rate(rows, "final_answer_correctness"),
        "fallback_rate": rate(measured, "fallback_used"),
        "mean_generation_latency_ms": (
            statistics.mean(generation) if generation else None),
        "median_generation_latency_ms": (
            statistics.median(generation) if generation else None),
        "p95_generation_latency_ms": percentile(generation, 0.95),
        "mean_total_latency_ms": statistics.mean(total) if total else None,
        "median_total_latency_ms": statistics.median(total) if total else None,
        "p95_total_latency_ms": percentile(total, 0.95),
        "total_input_tokens": sum(row.get("input_tokens") or 0 for row in measured),
        "total_output_tokens": sum(row.get("output_tokens") or 0 for row in measured),
        "unknown_input_token_cases": sum(row.get("input_tokens") is None
                                         for row in measured),
        "unknown_output_token_cases": sum(row.get("output_tokens") is None
                                          for row in measured),
        "peak_ram_bytes": max(ram, default=None),
        "peak_vram_mib": max(vram, default=None),
        "max_cpu_percent": max(cpu, default=None),
    }


def write_summary_csv(path, summaries):
    path = Path(path)
    if not summaries:
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
