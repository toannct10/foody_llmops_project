"""Validate dbt parse discovery JSON without contacting Snowflake."""

import json
from collections import Counter
from pathlib import Path

from scripts.ci_acceptance import write


def main(path=Path("ci-artifacts/dbt_resources.jsonl")):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    counts = Counter(row["resource_type"] for row in rows)
    models = {row["name"]: row for row in rows if row["resource_type"] == "model"}
    custom = {row["name"] for row in rows if row["resource_type"] == "test"}
    checks = {
        "models": counts["model"] >= 10,
        "sources": counts["source"] >= 3,
        "tests": counts["test"] >= 7,
        "marts_depend_on_staging": any("stg_sales" in str(row.get("depends_on", {}))
                                       for name, row in models.items() if name == "fact_order"),
        "custom_tests": {"assert_delivered_only_revenue", "assert_mart_row_consistency",
                         "assert_raw_batch_audit_counts"} <= custom,
    }
    result = {"status": "PASS" if all(checks.values()) else "FAIL",
              "mode": "OFFLINE_PARSE_NO_SNOWFLAKE", "counts": dict(counts), "checks": checks}
    write("dbt_static", result)
    if result["status"] != "PASS":
        raise SystemExit("dbt static graph validation failed")
    print(f"dbt static PASS: {dict(counts)}")


if __name__ == "__main__":
    main()
