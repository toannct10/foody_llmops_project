"""Reproducible, model-free structural evaluation of the Cross question matrix."""

import json
from collections import Counter
from datetime import date
from pathlib import Path

from src.sales.cross_intelligence import build_cross_plan

MATRIX = Path("data/evaluation/cross_intelligence_cases.json")
OUTPUT = Path("reports/cross/CROSS_EVALUATION.json")


def evaluate(matrix=MATRIX):
    cases = json.loads(Path(matrix).read_text(encoding="utf-8"))["cases"]
    results = []
    for case in cases:
        try:
            plan = build_cross_plan(
                case["question"], case["restaurant_id"],
                today=date(2026, 11, 15), default_periods=("2025-05", "2025-06"))
            checks = {
                "intent": plan.intent == case["category"],
                "cross_route": plan.mode == "cross_analysis",
                "exact_entity": plan.restaurant_id == case["restaurant_id"],
                "periods_present": bool(plan.periods),
                "no_duplicate_periods": len(plan.periods) == len(set(plan.periods)),
                "review_evidence_required": plan.need_review_evidence,
            }
            result = {"id": case["id"], "category": case["category"],
                      "scenario": case["scenario"], "status": "PASS" if all(
                          checks.values()) else "FAIL", "checks": checks,
                      "periods": list(plan.periods), "period_source": plan.period_source}
        except (ValueError, KeyError, TypeError) as error:
            result = {"id": case["id"], "category": case["category"],
                      "scenario": case["scenario"], "status": "FAIL",
                      "error": type(error).__name__}
        results.append(result)
    categories = sorted({case["category"] for case in cases})
    passed = Counter(item["category"] for item in results if item["status"] == "PASS")
    totals = Counter(item["category"] for item in results)
    return {"version": "cross_general_v1", "scope": "structural_planning_invariants",
            "matrix_size": len(results), "passed": sum(item["status"] == "PASS"
                                                  for item in results),
            "categories": {category: {"passed": passed[category],
                                      "total": totals[category]}
                           for category in categories},
            "results": results}


if __name__ == "__main__":
    report = evaluate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"Cross planning matrix: {report['passed']}/{report['matrix_size']} PASS")
    raise SystemExit(0 if report["passed"] == report["matrix_size"] else 1)
