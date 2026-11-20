"""Operation-based, parameterized Sales fallback for a validated canonical plan."""

from decimal import Decimal

from src.sales import queries
from src.sales.metric_ontology import STATUS_METRICS, UNITS
from src.sales.semantic_plan import CanonicalPlan, validate_plan


def _number(value):
    return Decimal(str(value or 0))


def _metric(rows, name):
    sales = sum((_number(row.get("delivered_sales")) for row in rows), Decimal(0))
    orders = sum((_number(row.get("order_count")) for row in rows), Decimal(0))
    delivered = sum((_number(row.get("delivered_count")) for row in rows), Decimal(0))
    cancelled = sum((_number(row.get("cancelled_count")) for row in rows), Decimal(0))
    refunded = sum((_number(row.get("refunded_count")) for row in rows), Decimal(0))
    cancelled_orders = sum((_number(row.get("cancelled_order_count")) for row in rows),
                           Decimal(0))
    refunded_orders = sum((_number(row.get("refunded_order_count")) for row in rows),
                          Decimal(0))
    return {"delivered_sales": sales, "order_count": orders,
            "aov": sales / delivered if delivered else None,
            "average_order_value": sales / delivered if delivered else None,
            "cancelled_order_count": cancelled_orders,
            "cancelled_order_value": sum((_number(row.get("cancelled_order_value"))
                                          for row in rows), Decimal(0)),
            "refunded_order_count": refunded_orders,
            "refunded_order_value": sum((_number(row.get("refunded_order_value"))
                                         for row in rows), Decimal(0)),
            "cancellation_rate": cancelled / orders if orders else None,
            "refund_rate": refunded / orders if orders else None}[name]


def _display(value, metric):
    if value is None:
        return "không đủ dữ liệu"
    if UNITS[metric] == "%":
        return f"{value * 100:,.2f}%"
    if UNITS[metric] == "orders":
        return f"{value:,.0f} đơn"
    if UNITS[metric] == "VND/order":
        return f"{value:,.0f} ₫/đơn"
    return f"{value:,.0f} ₫"


def _label(group):
    if len(group) == 12 and group[0].endswith("-01") and group[-1].endswith("-12"):
        return group[0][:4]
    return group[0] if len(group) == 1 else f"{group[0]} – {group[-1]}"


def answer_from_plan(conn, restaurant_id, identity, plan: CanonicalPlan, *, today):
    """Fetch observed mart rows once, then apply a shape-specific pure calculation."""
    validate_plan(plan)
    scope = plan.time_scope
    if not scope.periods:
        raise ValueError("An explicit time scope is required for this analytical plan")
    source = (queries.monthly_status_values_range if
              any(metric in STATUS_METRICS for metric in plan.metrics) else
              queries.monthly_sales_range)
    fetched = source(conn, restaurant_id,
                     min(item["start"] for item in scope.bounds),
                     max(item["end"] for item in scope.bounds))
    allowed = set(scope.periods)
    by_month = {str(row["period_start"])[:7]: row for row in fetched
                if str(row["period_start"])[:7] in allowed}
    observed = [period for period in scope.periods if period in by_month]
    missing = [period for period in scope.periods if period not in by_month]
    groups = [([by_month[period] for period in group if period in by_month], _label(group))
              for group in scope.groups]
    metadata = {**plan.as_dict(), "observed_periods": observed,
                "missing_periods": missing,
                "periods": list(scope.periods), "period_ranges": list(scope.bounds),
                "intent": plan.operation, "metric": plan.metrics[0],
                "sql_mode": ("predefined_parameterized_status_values" if
                             source is queries.monthly_status_values_range else
                             "predefined_parameterized_monthly_sales"),
                "result_unit": UNITS[plan.metrics[0]]}
    base = {"route": "SALES_SQL", "source": "SQL Analytics",
            "restaurant_id": str(restaurant_id), "review_evidence": [],
            "query_plan": metadata, "execution_mode": "DETERMINISTIC_FALLBACK"}
    if not observed or (plan.operation in {"comparison", "growth", "multi_metric"}
                        and any(not rows for rows, _ in groups)):
        return {**base, "status": "no_data", "sql_facts": [], "display_rows": [],
                "answer": "Không đủ dữ liệu cho các kỳ đã yêu cầu. Kỳ thiếu: " +
                          ", ".join(missing or [_label(group) for group in scope.groups
                                              if not any(period in by_month for period in group)]) + "."}

    primary = plan.metrics[0]
    rows = []
    if plan.operation == "ranking":
        rows = [{"period_start": period + "-01",
                 **{metric: _metric([by_month[period]], metric) for metric in plan.metrics}}
                for period in observed]
        rows = [row for row in rows if row[primary] is not None]
        rows.sort(key=lambda row: row[primary],
                  reverse=plan.sort == ("descending",))
        rows = rows[:plan.limit]
        answer = ("Xếp hạng tháng theo " + primary + ": " + "; ".join(
            f"{row['period_start'][:7]} {_display(row[primary], primary)}" for row in rows) + ".")
    elif plan.operation == "trend":
        rows = [{"period_start": period + "-01",
                 **{metric: _metric([by_month[period]], metric) for metric in plan.metrics}}
                for period in sorted(observed)]
        answer = ("Xu hướng " + primary + ": " + "; ".join(
            f"{row['period_start'][:7]} {_display(row[primary], primary)}" for row in rows) + ".")
    elif plan.output_shape == "grouped_rows" and plan.group_by == ("month",):
        rows = [{"period_start": period + "-01",
                 **{metric: _metric([by_month[period]], metric) for metric in plan.metrics}}
                for period in sorted(observed)]
        answer = "; ".join(f"{row['period_start'][:7]}: " + ", ".join(
            f"{metric} {_display(row[metric], metric)}" for metric in plan.metrics)
                           for row in rows) + "."
    elif plan.operation in {"comparison", "growth", "multi_metric"} and len(groups) > 1:
        rows = [{"period": label, **{metric: _metric(facts, metric)
                                      for metric in plan.metrics}}
                for facts, label in groups]
        rows.sort(key=lambda row: row["period"])
        answer = "; ".join(f"{row['period']}: " + ", ".join(
            f"{metric} {_display(row[metric], metric)}" for metric in plan.metrics)
                           for row in rows) + "."
        if plan.operation == "growth" and len(rows) == 2:
            baseline, current = rows
            if baseline[primary] is not None and current[primary] is not None:
                difference = current[primary] - baseline[primary]
                pct = difference / baseline[primary] * 100 if baseline[primary] else None
                rows.append({"period": "change", "absolute_change": difference,
                             "percentage_change": pct})
                answer += (f" Chênh lệch {_display(difference, primary)}; " +
                           (f"{pct:+.2f}%." if pct is not None else
                            "không tính được tỷ lệ phần trăm từ mốc 0."))
    else:
        facts = [by_month[period] for period in observed]
        values = {metric: _metric(facts, metric) for metric in plan.metrics}
        if plan.filters.get("monthly_average") == "true":
            values[primary] = values[primary] / len(facts) if values[primary] is not None else None
        rows = [values]
        answer = ", ".join(f"{metric} {_display(rows[0][metric], metric)}"
                           for metric in plan.metrics) + "."
        if plan.include_breakdown:
            rows.extend({"period": period, **{metric: _metric([by_month[period]], metric)
                                              for metric in plan.metrics}}
                        for period in observed)
    if missing:
        answer += " Kỳ chưa quan sát: " + ", ".join(missing) + "."
    if today.strftime("%Y-%m") in observed:
        answer += " Tháng hiện tại có thể chưa đủ dữ liệu."
    serialized = queries.jsonable(rows)
    return {**base, "status": "ok", "answer": answer,
            "sql_facts": serialized, "display_rows": serialized}
