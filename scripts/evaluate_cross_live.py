"""Four bounded live Cross acceptance cases against the existing local warehouse."""

import json
import os
from pathlib import Path

from src.sales.cross_intelligence import analyze_cross, validate_cross_answer
from src.warehouse.loader import connection

RESTAURANT_ID = "1062"
QUESTIONS = (
    "Vì sao doanh thu tháng 6/2025 giảm so với tháng 5/2025?",
    "Doanh thu giảm có đi kèm review tiêu cực tăng không?",
    "Tháng doanh thu thấp nhất năm 2025 khách hàng phàn nàn gì?",
    "So sánh doanh thu, số đơn và phản hồi khách hàng giữa tháng 5 và 6 năm 2025.",
)
OUTPUT = Path(os.environ.get("CROSS_EVALUATION_OUTPUT",
                             "reports/cross/CROSS_LIVE_ACCEPTANCE.json"))


def check_result(conn, result):
    periods = set(result["plan"]["periods"])
    checks = {"exact_restaurant": result["restaurant_id"] == RESTAURANT_ID,
              "sales_verified": True, "review_counts_verified": True,
              "evidence_scope_verified": True, "deltas_verified": True,
              "causation_guard": True, "missing_data_explicit": True}
    for item in result["sales_facts"]:
        row = conn.execute("""SELECT delivered_sales FROM restaurant_monthly_sales
            WHERE restaurant_id=%s AND period_start=%s""",
            (RESTAURANT_ID, item["period"] + "-01")).fetchone()
        checks["sales_verified"] &= (row is not None and
                                      float(row[0]) == item["delivered_sales"])
    for item in result["review_signals"]:
        count = conn.execute("""SELECT COUNT(*) FROM fact_review_v2 r
            JOIN dim_date d ON d.date_key=r.date_key WHERE r.restaurant_id=%s
            AND d.calendar_date >= %s AND d.calendar_date <
            (%s::date + INTERVAL '1 month')""",
            (RESTAURANT_ID, item["period"] + "-01",
             item["period"] + "-01")).fetchone()[0]
        checks["review_counts_verified"] &= count == item["review_count"]
    for item in result["review_evidence"]:
        row = conn.execute("""SELECT d.calendar_date FROM fact_review_v2 r
            JOIN dim_date d ON d.date_key=r.date_key WHERE r.review_id=%s
            AND r.restaurant_id=%s""",
            (item["review_id"], RESTAURANT_ID)).fetchone()
        checks["evidence_scope_verified"] &= (row is not None and
            str(row[0]) == item["date"] and item["period"] in periods and
            item["date"].startswith(item["period"]))
    by_metric = {item["metric"]: item for item in result["sales_drivers"]}
    if len(result["sales_facts"]) >= 2:
        first, last = result["sales_facts"][0], result["sales_facts"][-1]
        revenue = by_metric.get("delivered_sales")
        checks["deltas_verified"] = bool(revenue and
            abs(revenue["absolute_change"] -
                (last["delivered_sales"] - first["delivered_sales"])) < 0.01)
    try:
        validate_cross_answer(result["answer"], result["review_evidence"])
    except ValueError:
        checks["causation_guard"] = False
    if result["status"] in {"no_sales_data", "no_review_data",
                            "insufficient_review_evidence"}:
        checks["missing_data_explicit"] = bool(result["missing_data"])
    return checks


def main():
    records = []
    with connection() as conn:
        for index, question in enumerate(QUESTIONS, 1):
            try:
                result = analyze_cross(conn, RESTAURANT_ID, question)
                checks = check_result(conn, result)
                record = {"case": index, "question": question,
                          "status": "PASS" if all(checks.values()) else "FAIL",
                          "checks": checks, "plan": result["plan"],
                          "sales_facts": result["sales_facts"],
                          "sales_drivers": result["sales_drivers"],
                          "review_signals": result["review_signals"],
                          "evidence_ids": [item["review_id"] for item in
                                           result["review_evidence"]],
                          "answer": result["answer"],
                          "missing_data": result["missing_data"],
                          "causation_guard": result["technical"][
                              "causation_guard_status"],
                          "retrieval_mode": result["technical"]["retrieval_mode"],
                          "generation_mode": result["technical"]["generation_mode"],
                          "latency_ms": result["technical"]["latency_ms"]}
            except Exception as error:
                record = {"case": index, "question": question, "status": "FAIL",
                          "error": f"{type(error).__name__}: {str(error)[:200]}"}
            records.append(record)
            print(json.dumps({key: record.get(key) for key in
                              ("case", "status", "evidence_ids", "missing_data",
                               "causation_guard", "latency_ms", "error")},
                             ensure_ascii=False, default=str), flush=True)
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(json.dumps({"version": "cross_general_v1",
                                          "restaurant_id": RESTAURANT_ID,
                                          "results": records}, ensure_ascii=False,
                                         indent=2, default=str) + "\n", encoding="utf-8")
    return all(item["status"] == "PASS" for item in records)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
