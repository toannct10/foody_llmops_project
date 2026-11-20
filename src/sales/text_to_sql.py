"""Constrained Qwen Text-to-SQL over approved PostgreSQL Sales marts."""

import json
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import requests
import sqlglot
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlglot import exp

from src.monitoring.metrics import observe_sales_sql, observe_text_to_sql
from src.rag.monitoring import record
from src.sales import queries
from src.sales.metric_ontology import STATUS_METRICS, UNITS
from src.sales.planner import SQLAnalyticalPlan, build_sql_analytical_plan
from src.sales.semantic_plan import (
    build_canonical_plan,
    month_range,
    next_month,
    verify_result_shape,
)
from src.security.audit import security_event

PROMPT = Path("prompts/sales/text_to_sql_v2.txt")
EXAMPLES = Path("prompts/sales/text_to_sql_examples.json")
MAX_ROWS = 100
TIMEOUT_MS = 5000

# Columns and meanings mirror sql/postgres/migrations/003_sales.sql, not an LLM guess.
MART_COLUMNS = {
    "restaurant_monthly_order_status_values": {
        "restaurant_id": "Sales restaurant ID", "period_start": "first day of month",
        "order_count": "all observed orders",
        "cancelled_order_count": "Cancelled orders",
        "cancelled_order_value": "sum of Cancelled order amounts in VND",
        "refunded_order_count": "Refunded orders",
        "refunded_order_value": "sum of Refunded order amounts in VND",
        "cancellation_rate": "Cancelled orders / all observed orders",
        "refund_rate": "Refunded orders / all observed orders",
    },
    "restaurant_monthly_sales": {
        "restaurant_id": "Sales restaurant ID", "period_start": "first day of month",
        "order_count": "all observed orders", "gross_sales": "all order amounts",
        "delivered_sales": "Delivered-only revenue VND",
        "delivered_count": "Delivered orders", "cancelled_count": "Cancelled orders",
        "refunded_count": "Refunded orders", "aov": "Delivered revenue / Delivered count",
        "cancellation_rate": "Cancelled / all observed orders",
        "refund_rate": "Refunded / all observed orders",
        "previous_delivered_sales": "previous-month Delivered revenue",
        "mom_growth": "month-over-month Delivered growth",
    },
    "restaurant_weekly_sales": {
        "restaurant_id": "Sales restaurant ID", "period_start": "Monday of week",
        "order_count": "all observed orders", "gross_sales": "all order amounts",
        "delivered_sales": "Delivered-only revenue VND",
        "delivered_count": "Delivered orders", "cancelled_count": "Cancelled orders",
        "refunded_count": "Refunded orders", "aov": "Delivered revenue / Delivered count",
        "cancellation_rate": "Cancelled / all observed orders",
        "refund_rate": "Refunded / all observed orders",
        "previous_delivered_sales": "previous-week Delivered revenue",
        "wow_growth": "week-over-week Delivered growth",
    },
    "restaurant_sales_summary": {
        "restaurant_id": "Sales restaurant ID", "order_count": "all observed orders",
        "gross_sales": "all order amounts", "delivered_sales": "Delivered-only revenue VND",
        "delivered_count": "Delivered orders", "cancelled_count": "Cancelled orders",
        "refunded_count": "Refunded orders", "aov": "Delivered revenue / Delivered count",
        "cancellation_rate": "Cancelled / all observed orders",
        "refund_rate": "Refunded / all observed orders",
    },
    "dim_sales_restaurant": {
        "restaurant_id": "Sales restaurant ID", "restaurant_name": "display name",
    },
}
SAFE_FUNCTIONS = {"SUM", "COUNT", "AVG", "MIN", "MAX", "ROUND", "COALESCE",
                  "NULLIF", "DATE", "DATE_TRUNC", "TIMESTAMP_TRUNC", "EXTRACT", "ABS",
                  "GREATEST", "LEAST"}
FORBIDDEN_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                   exp.Alter, exp.Command, exp.Copy, exp.Transaction,
                   exp.Grant, exp.Revoke, exp.Merge, exp.Into, exp.Lateral)
PLACEHOLDER = re.compile(r"%\(([a-z][a-z0-9_]*)\)s")


class SQLRejected(ValueError):
    """Rejected before reaching the PostgreSQL executor."""

    def __init__(self, category):
        self.category = category
        super().__init__(category)


class SQLDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=1, max_length=80)
    sql: str = Field(min_length=8, max_length=6000)
    parameters: dict[str, str | int | float | bool | None]
    tables_used: list[str]
    reasoning_summary: str = Field(max_length=200)
    answer_type: str


def select_schema(question, plan=None):
    """Select the smallest approved marts needed by the requested metric/timeframe."""
    lowered = question.casefold()
    metrics = plan.metrics if plan is not None else build_canonical_plan(question).metrics
    tables = ({"restaurant_monthly_order_status_values"} if
              set(metrics) & STATUS_METRICS else {"restaurant_monthly_sales"})
    if any(word in lowered for word in ("tuần", "weekly", "week")):
        tables = {"restaurant_weekly_sales"}
    if any(word in lowered for word in ("tổng thể", "toàn thời gian", "overall")):
        tables = {"restaurant_sales_summary"}
    if _scope_is_global(question) and not re.search(r"\b20\d{2}\b", question):
        tables = {"restaurant_sales_summary"}
    if any(word in lowered for word in ("top", "xếp hạng", "nhà hàng nào",
                                        "restaurant", "nhà hàng")):
        tables.add("dim_sales_restaurant")
    return {name: MART_COLUMNS[name] for name in sorted(tables)}


def _prompt_schema(selected_schema, plan):
    """Show Qwen only columns needed by this validated analytical plan."""
    needed = {"restaurant_id", "period_start", *plan.metrics}
    if "average_order_value" in plan.metrics:
        needed.update(("aov", "delivered_sales", "delivered_count"))
    if "cancellation_rate" in plan.metrics:
        needed.update(("cancelled_count", "order_count"))
    if "refund_rate" in plan.metrics:
        needed.update(("refunded_count", "order_count"))
    if plan.group_by == ("restaurant_id",):
        needed.add("restaurant_name")
    return "\n".join(f"{table}: " + ", ".join(
        f"{column} ({meaning})" for column, meaning in columns.items()
        if column in needed) for table, columns in selected_schema.items())


def _prompt_plan(plan):
    payload = {"metric": plan.metric, "metrics": plan.metrics,
               "operation": plan.operation, "group_by": plan.group_by,
               "sort": plan.sort, "limit": plan.limit,
               "output_shape": plan.output_shape, "expected_rows": plan.expected_rows,
               "time_scope": plan.time_scope}
    if plan.filters.get("order_status"):
        payload["order_status"] = plan.filters["order_status"]
    if plan.time_scope in {"single_month", "explicit_months"}:
        payload["exact_month_dates"] = [period["start"] for period in plan.periods]
    elif plan.periods:
        payload["period_bounds"] = {"start": plan.periods[0]["start"],
                                    "end_exclusive": plan.periods[-1]["end"]}
        if len(plan.periods) > 1:
            payload["year_starts"] = [period["start"] for period in plan.periods]
    if plan.filters.get("monthly_average") == "true":
        payload["monthly_average"] = True
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def select_examples(question, selected_schema):
    """Include at most two relevant, schema-compatible frozen examples."""
    lowered = question.casefold()
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    from src.sales.planner import build_sales_plan

    try:
        period_plan = build_sales_plan(question)
    except ValueError:
        period_plan = None
    try:
        analytical = build_sql_analytical_plan(question)
    except ValueError:
        analytical = None
    if _scope_is_global(question):
        wanted = ["cancellation_ranking_monthly" if "hủy" in lowered and
                  re.search(r"\b20\d{2}\b", question) else
                  "cancellation_ranking" if "hủy" in lowered else "top_revenue"]
    elif analytical and analytical.grain == "year" and len(analytical.periods) > 1:
        wanted = ["multi_year_comparison"]
    elif analytical and analytical.operation == "ranking" and \
            analytical.group_by == ("month",):
        wanted = ["top_months"]
    elif analytical and analytical.operation == "trend":
        wanted = ["month_trend"]
    elif analytical and analytical.output_shape == "grouped_rows" and \
            analytical.time_scope == "explicit_months":
        wanted = ["month_set_values"]
    elif analytical and analytical.metric == "cancelled_order_value":
        wanted = ["cancelled_value"]
    elif analytical and analytical.metric == "cancelled_order_count":
        wanted = ["cancelled_count"]
    elif analytical and analytical.metric == "cancellation_rate" and \
            analytical.grain == "year":
        wanted = ["year_cancellation_rate"]
    elif period_plan and period_plan.kind == "RANGE_AGGREGATE" and \
            period_plan.period_selection == "EXPLICIT_SET":
        wanted = ["month_set_total"]
    elif period_plan and period_plan.kind == "YEAR_AGGREGATE" and \
            period_plan.aggregation == "sum":
        wanted = ["year_total"]
    elif any(word in lowered for word in ("so sánh", "vs", " với ")):
        wanted = ["comparison"]
    elif "aov" in lowered:
        wanted = ["aov"]
    elif "hủy" in lowered or "hoàn" in lowered:
        wanted = ["cancellation_refund"]
    elif any(word in lowered for word in ("đơn hàng", "số đơn", "orders")):
        wanted = ["orders"]
    else:
        wanted = ["revenue"]
    return "\n".join(
        f"Example question: {item['question']}\nExample JSON: "
        + json.dumps(item["output"], ensure_ascii=False, separators=(",", ":"))
        for item in examples if item["id"] in wanted
        and set(item["output"]["tables_used"]) <= set(selected_schema)
    )


def _scope_is_global(question):
    lowered = question.casefold()
    return "nhà hàng nào" in lowered or (any(term in lowered for term in
           ("top ", "xếp hạng")) and any(term in lowered for term in
           ("nhà hàng", "restaurant")))


def unsafe_request(question):
    """Refuse data destruction and credential requests before model or fallback."""
    lowered = question.casefold()
    return any(term in lowered for term in (
        "xóa ", "xoá ", "delete ", "drop ", "truncate ", "cập nhật dữ liệu",
        "mật khẩu", "password", "credential", "secret key"))


def validate_sql(draft, selected_schema, *, global_scope=False, max_rows=MAX_ROWS):
    """Validate one PostgreSQL SELECT AST, its scope, columns and parameters."""
    if not isinstance(draft, SQLDraft):
        try:
            draft = SQLDraft.model_validate(draft)
        except ValidationError as error:
            raise SQLRejected("structured_output") from error
    if draft.answer_type not in {"single_value", "table", "comparison", "trend", "ranking"}:
        raise SQLRejected("answer_type")
    if "--" in draft.sql or "/*" in draft.sql or "*/" in draft.sql:
        raise SQLRejected("sql_comments")
    if draft.sql.rstrip().endswith(";") and draft.sql.count(";") == 1:
        draft.sql = draft.sql.rstrip()[:-1].rstrip()
    if ";" in draft.sql:
        raise SQLRejected("multiple_statements")
    try:
        statements = sqlglot.parse(draft.sql, read="postgres", error_level="RAISE")
    except sqlglot.errors.SqlglotError as error:
        raise SQLRejected("sql_syntax") from error
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise SQLRejected("non_select")
    tree = statements[0]
    if any(isinstance(node, FORBIDDEN_NODES) for node in tree.walk()):
        raise SQLRejected("unsafe_operation")
    if any(isinstance(node, exp.Subquery) for node in tree.walk()):
        raise SQLRejected("unsupported_subquery")
    if any(isinstance(node, (exp.Or, exp.Not, exp.Union)) for node in tree.walk()):
        raise SQLRejected("unsafe_expression")
    if any(not isinstance(star.parent, exp.Count) for star in tree.find_all(exp.Star)):
        raise SQLRejected("wildcard_select")
    for join in tree.find_all(exp.Join):
        on = join.args.get("on")
        if join.args.get("kind") == "CROSS" or not isinstance(on, exp.EQ) or not all(
            isinstance(side, exp.Column) and side.name.lower() == "restaurant_id"
            for side in (on.left, on.right)
        ):
            raise SQLRejected("unsafe_join")
    cte_names = {cte.alias.lower() for cte in tree.find_all(exp.CTE)}
    tables = {table.name.lower() for table in tree.find_all(exp.Table)
              if table.name.lower() not in cte_names}
    if not tables or tables != set(draft.tables_used) or not tables <= set(selected_schema):
        raise SQLRejected("table_allowlist")
    if any(table.db or table.catalog for table in tree.find_all(exp.Table)):
        raise SQLRejected("cross_schema")
    allowed_columns = {column for table in tables for column in selected_schema[table]}
    table_aliases = {table.alias_or_name.lower(): table.name.lower()
                     for table in tree.find_all(exp.Table)
                     if table.name.lower() in tables}
    aliases = {alias.alias.lower() for alias in tree.find_all(exp.Alias)}
    for column in tree.find_all(exp.Column):
        if column.name.lower() not in allowed_columns | aliases:
            raise SQLRejected("column_allowlist")
        if column.table and column.table.lower() in table_aliases and \
                column.name.lower() not in selected_schema[table_aliases[column.table.lower()]]:
            raise SQLRejected("column_allowlist")
    for function in tree.find_all(exp.Func):
        if isinstance(function, (exp.Binary, exp.Unary, exp.Predicate)):
            continue
        if isinstance(function, exp.Cast):
            target = function.args.get("to")
            if not isinstance(function.this, exp.Sum) or \
                    not isinstance(target, exp.DataType) or \
                    target.this != exp.DataType.Type.DECIMAL:
                raise SQLRejected("cast_type")
            continue
        if function.sql_name().upper() not in SAFE_FUNCTIONS:
            raise SQLRejected("function_allowlist")
    limit = tree.args.get("limit")
    if limit is None:
        # A validated SELECT can safely receive a server-side cap before execution.
        draft.sql = draft.sql.rstrip() + f" LIMIT {max_rows}"
    else:
        if not isinstance(limit.expression, exp.Literal):
            raise SQLRejected("row_limit")
        try:
            row_limit = int(limit.expression.this)
        except (TypeError, ValueError) as error:
            raise SQLRejected("row_limit") from error
        if not 1 <= row_limit <= max_rows:
            raise SQLRejected("row_limit")
    names = {str(node.name) for node in tree.find_all(exp.Placeholder)}
    if names != set(draft.parameters) or names != set(PLACEHOLDER.findall(draft.sql)):
        raise SQLRejected("parameters")
    if any(not isinstance(value, (str, int, float, bool, type(None)))
           for value in draft.parameters.values()):
        raise SQLRejected("parameters")
    scoped = any(isinstance(node, exp.EQ) and
                 ((isinstance(node.left, exp.Column) and
                   node.left.name.lower() == "restaurant_id" and
                   isinstance(node.right, exp.Placeholder) and
                   str(node.right.name) == "restaurant_id") or
                  (isinstance(node.right, exp.Column) and
                   node.right.name.lower() == "restaurant_id" and
                   isinstance(node.left, exp.Placeholder) and
                   str(node.left.name) == "restaurant_id")) for node in tree.walk())
    if global_scope and ("restaurant_id" in names or scoped):
        raise SQLRejected("global_scope")
    if not global_scope and ("restaurant_id" not in names or not scoped):
        raise SQLRejected("restaurant_scope")
    if not global_scope:
        for select in tree.find_all(exp.Select):
            reads_mart = any(table.name.lower() in tables and
                             table.find_ancestor(exp.Select) is select
                             for table in select.find_all(exp.Table))
            where = select.args.get("where")
            scoped_here = where is not None and any(
                isinstance(node, exp.EQ) and
                ((isinstance(node.left, exp.Column) and
                  node.left.name.lower() == "restaurant_id" and
                  isinstance(node.right, exp.Placeholder) and
                  str(node.right.name) == "restaurant_id") or
                 (isinstance(node.right, exp.Column) and
                  node.right.name.lower() == "restaurant_id" and
                  isinstance(node.left, exp.Placeholder) and
                  str(node.left.name) == "restaurant_id"))
                for node in where.walk())
            if reads_mart and not scoped_here:
                raise SQLRejected("restaurant_scope")
    return draft


def _explicit_month_filter(tree, parameters, expected):
    """Accept equivalent exact IN or contiguous half-open range predicates."""
    requested = {period + "-01" for period in expected}
    for node in tree.find_all(exp.In):
        if not isinstance(node.this, exp.Column) or node.this.name.lower() != "period_start":
            continue
        values = {str(parameters.get(str(item.name))) if isinstance(item, exp.Placeholder)
                  else str(item.this) for item in node.expressions}
        if values == requested:
            return True
    if len(requested) == 1:
        for node in tree.find_all(exp.EQ):
            if isinstance(node.left, exp.Column) and node.left.name.lower() == "period_start":
                value = (parameters.get(str(node.right.name)) if isinstance(
                    node.right, exp.Placeholder) else getattr(node.right, "this", None))
                if str(value) in requested:
                    return True
    if tuple(sorted(expected)) != month_range(min(expected), max(expected)):
        return False
    lower, upper = min(requested), max(expected)
    upper = next_month(upper) + "-01"
    comparisons = tuple(tree.find_all(exp.GTE, exp.GT, exp.LT, exp.LTE))
    def matching(kind, target):
        return any(isinstance(node, kind) and isinstance(node.left, exp.Column) and
                   node.left.name.lower() == "period_start" and
                   str(parameters.get(str(node.right.name)) if isinstance(
                       node.right, exp.Placeholder) else getattr(node.right, "this", None))
                   == target for node in comparisons)
    return matching(exp.GTE, lower) and matching(exp.LT, upper)


def verify_question_scope(draft, question):
    """Reject common semantic drift before showing a numerically grounded answer."""
    from src.sales.planner import extract_requested_periods

    lowered = question.casefold()
    tree = sqlglot.parse_one(draft.sql, read="postgres")
    columns = {column.name.lower() for column in tree.find_all(exp.Column)}
    if _scope_is_global(question):
        top = re.search(r"\btop\s+(\d{1,3})\b", lowered)
        requested_rows = min(int(top.group(1)), 100) if top else 1
        if int(tree.args["limit"].expression.this) != requested_rows:
            raise SQLRejected("ranking_limit")
    canonical = build_canonical_plan(question)
    metrics = set(canonical.metrics)
    if "delivered_sales" in metrics and \
            "gross_sales" in columns:
        raise SQLRejected("business_definition")
    if "delivered_sales" in metrics and \
            "delivered_sales" not in columns:
        raise SQLRejected("business_definition")
    if "order_count" in metrics and \
            "order_count" not in columns:
        raise SQLRejected("business_definition")
    if "average_order_value" in metrics and \
            not ("aov" in columns or {"delivered_sales", "delivered_count"} <= columns):
        raise SQLRejected("business_definition")
    if any(term in lowered for term in ("tỷ lệ hủy", "tỉ lệ hủy", "cancellation")) and \
            not ("cancellation_rate" in columns or
                 {"cancelled_count", "order_count"} <= columns):
        raise SQLRejected("business_definition")
    if any(term in lowered for term in ("tỷ lệ hoàn", "tỉ lệ hoàn", "refund")) and \
            not ("refund_rate" in columns or
                 {"refunded_count", "order_count"} <= columns):
        raise SQLRejected("business_definition")
    for aggregate in tree.find_all(exp.Sum, exp.Avg):
        if any(column.name.lower() in {"aov", "cancellation_rate", "refund_rate"}
               for column in aggregate.find_all(exp.Column)):
            raise SQLRejected("business_definition")
    try:
        periods = extract_requested_periods(question)
    except ValueError:
        periods = canonical.time_scope.periods
    analytical = build_sql_analytical_plan(question)
    if canonical.time_scope.kind in {"single_month", "explicit_months"} or \
            len(analytical.periods) > 2 or (len(analytical.periods) > 1 and
                                      re.search(r"\b(?:đến|den)\b", lowered)):
        # The plan verifier checks the complete bounded interval; endpoint-only
        # string matching would reject a valid range query.
        periods = ()
    parameter_text = " ".join(str(value) for value in draft.parameters.values())
    literal_dates = set()
    for comparison in tree.find_all(exp.EQ, exp.GT, exp.GTE, exp.LT, exp.LTE):
        sides = (comparison.left, comparison.right)
        if any(isinstance(side, exp.Column) and side.name.lower() == "period_start"
               for side in sides):
            literal_dates.update(str(side.this) for side in sides
                                 if isinstance(side, exp.Literal) and side.is_string)
    period_values = parameter_text + " " + " ".join(literal_dates)
    if periods and ("period_start" not in columns or
                    any(period not in period_values for period in periods)):
        raise SQLRejected("period_scope")
    years = set(re.findall(r"\b20\d{2}\b", question))
    if len(years) <= 1 and years and ("period_start" not in columns or
                  any(year not in period_values and year not in draft.sql
                      for year in years)):
        raise SQLRejected("period_scope")
    if canonical.time_scope.kind in {"single_month", "explicit_months"} and not \
            _explicit_month_filter(tree, draft.parameters, canonical.time_scope.periods):
        raise SQLRejected("period_scope")


def verify_sql_plan(draft, plan: SQLAnalyticalPlan):
    """Check SQL shape and bound temporal scope against the validated plan."""
    tree = sqlglot.parse_one(draft.sql, read="postgres")
    columns = {column.name.lower() for column in tree.find_all(exp.Column)}
    output_names = {item.alias_or_name.lower() for item in tree.expressions}
    if not set(plan.metrics) <= columns | output_names:
        # Ratio metrics may be derived from numerator and denominator.
        derived = {"aov": {"delivered_sales", "delivered_count"},
                   "average_order_value": {"delivered_sales", "delivered_count"},
                   "cancellation_rate": {"cancelled_count", "order_count"},
                   "refund_rate": {"refunded_count", "order_count"}}
        if any(metric not in columns | output_names and
               (metric not in derived or not derived[metric] <= columns)
               for metric in plan.metrics):
            raise SQLRejected("plan_metric")
    multiple_months = len(plan.periods) > 1 or plan.time_scope in {
        "year", "quarter", "half_year", "continuous_range", "multiple_years"}
    summed = {column.name.lower() for node in tree.find_all(exp.Sum)
              for column in node.find_all(exp.Column)}
    for metric in plan.metrics:
        if metric in STATUS_METRICS:
            if metric not in columns or (multiple_months and metric not in summed):
                raise SQLRejected("metric_type")
        if metric in {"order_count", "cancelled_order_count", "refunded_order_count"} \
                and any(isinstance(node, exp.Count) for node in tree.walk()):
            raise SQLRejected("metric_type")
        if metric in {"cancellation_rate", "refund_rate"} and multiple_months:
            numerator = ("cancelled_count" if metric == "cancellation_rate" else
                         "refunded_count")
            if {numerator, "order_count"} - summed:
                raise SQLRejected("plan_aggregation")
        if metric == "average_order_value" and multiple_months and \
                {"delivered_sales", "delivered_count"} - summed:
            raise SQLRejected("metric_type")
    if plan.periods:
        if "period_start" not in columns:
            raise SQLRejected("plan_periods")
        dates = {str(value) for value in draft.parameters.values()
                 if isinstance(value, str) and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value)}
        dates.update(str(node.this) for node in tree.find_all(exp.Literal)
                     if node.is_string and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(node.this)))
        starts = {period["start"] for period in plan.periods}
        if (plan.grain == "year" or
                (plan.operation == "ranking" and len(plan.periods) == 1 and
                 plan.periods[0]["start"][:4] != plan.periods[0]["end"][:4])) and \
                max(period["end"] for period in plan.periods) not in dates:
            raise SQLRejected("plan_periods")
        if not starts <= dates:
            first = min(period["start"] for period in plan.periods)
            last = max(period["end"] for period in plan.periods)
            if first not in dates or last not in dates:
                raise SQLRejected("plan_periods")
            if not any(isinstance(node, (exp.GT, exp.GTE)) for node in tree.walk()) or \
                    not any(isinstance(node, (exp.LT, exp.LTE)) for node in tree.walk()):
                raise SQLRejected("plan_periods")
    if plan.group_by and plan.grain in {"year", "month"} and \
            plan.group_by != ("restaurant_id",):
        grouped = tree.args.get("group") is not None
        output_period = ("period_start" in output_names or "year" in output_names or
                         "month" in output_names)
        preaggregated_months = plan.grain == "month" and \
            not any(isinstance(node, (exp.Sum, exp.Avg, exp.Count)) for node in tree.walk())
        if (not grouped and not preaggregated_months) or not output_period:
            raise SQLRejected("plan_grouping")
        if plan.grain == "year" and not any(isinstance(node, exp.Extract)
                                             for node in tree.walk()):
            raise SQLRejected("plan_grouping")
    if plan.operation == "ranking":
        limit = tree.args.get("limit")
        if tree.args.get("order") is None or limit is None or \
                int(limit.expression.this) != plan.limit:
            raise SQLRejected("plan_ranking")
        order_sql = tree.args["order"].sql().upper()
        if plan.sort == "descending" and "DESC" not in order_sql:
            raise SQLRejected("plan_ranking")
        if plan.sort == "ascending" and "DESC" in order_sql:
            raise SQLRejected("plan_ranking")
    if plan.operation == "trend":
        order = tree.args.get("order")
        if order is None or "PERIOD_START" not in order.sql().upper():
            raise SQLRejected("plan_trend")
    if plan.output_shape == "scalar" and not plan.include_breakdown:
        if tree.args.get("group") is not None or draft.answer_type != "single_value":
            raise SQLRejected("plan_result_shape")
        if plan.time_scope in {"continuous_range", "quarter", "half_year", "year"} and \
                not any(isinstance(node, (exp.Sum, exp.Avg)) for node in tree.walk()):
            raise SQLRejected("plan_aggregation")
    if plan.output_shape == "grouped_rows" and (
            draft.answer_type != "table" or "period_start" not in output_names):
        raise SQLRejected("plan_result_shape")
    if plan.output_shape == "time_series" and draft.answer_type != "trend":
        raise SQLRejected("plan_result_shape")
    if plan.output_shape == "ranking" and draft.answer_type != "ranking":
        raise SQLRejected("plan_result_shape")
    if multiple_months and plan.output_shape == "scalar":
        required = {"aov": {"delivered_sales", "delivered_count"},
                    "average_order_value": {"delivered_sales", "delivered_count"},
                    "cancellation_rate": {"cancelled_count", "order_count"},
                    "refund_rate": {"refunded_count", "order_count"},
                    "delivered_sales": {"delivered_sales"},
                    "order_count": {"order_count"},
                    "cancelled_order_count": {"cancelled_order_count"},
                    "cancelled_order_value": {"cancelled_order_value"},
                    "refunded_order_count": {"refunded_order_count"},
                    "refunded_order_value": {"refunded_order_value"}}
        if not all((required[metric] <= summed or
                    metric == "delivered_sales" and
                    plan.filters.get("monthly_average") == "true" and
                    any(isinstance(node, exp.Avg) and any(
                        column.name.lower() == "delivered_sales"
                        for column in node.find_all(exp.Column))
                        for node in tree.walk())) for metric in plan.metrics):
            raise SQLRejected("plan_aggregation")
    if plan.operation in {"compare_periods", "growth", "multi_metric"} and \
            len(plan.periods) > 1 and draft.answer_type == "single_value":
        raise SQLRejected("plan_result_shape")
    if plan.filters.get("monthly_average") == "true" and not any(
            isinstance(node, exp.Avg) and any(
                column.name.lower() == "delivered_sales"
                for column in node.find_all(exp.Column))
            for node in tree.walk()):
        raise SQLRejected("plan_aggregation")
    if plan.operation == "rate" and plan.grain == "year" and not (
            {"order_count", "cancelled_count" if plan.metric == "cancellation_rate"
             else "refunded_count"} <= summed):
        raise SQLRejected("plan_aggregation")


def verify_plan_rows(rows, plan: SQLAnalyticalPlan):
    """Never present a partial comparison as a complete analytical answer."""
    if not rows:
        return
    if plan.grain == "year" and plan.group_by and plan.periods and \
            plan.operation != "ranking":
        expected = {period["start"][:4] if plan.grain == "year" else
                    period["start"][:7] for period in plan.periods}
        observed = {str(row.get("year", row.get("period_start", "")))[:4 if
                    plan.grain == "year" else 7] for row in rows}
        if not expected <= observed:
            raise SQLRejected("result_scope")
    if plan.operation == "ranking" and len(rows) > (plan.limit or MAX_ROWS):
        raise SQLRejected("result_scope")


def verify_plan_against_mart(conn, restaurant_id, rows, plan):
    """Independently check yearly groups using fixed parameterized mart SQL."""
    if plan.grain == "year" and len(plan.periods) == 1 and \
            plan.group_by != ("restaurant_id",) and rows:
        period = plan.periods[0]
        source = (queries.monthly_status_values_range if
                  plan.metric in STATUS_METRICS else queries.monthly_sales_range)
        reference = source(conn, restaurant_id, period["start"], period["end"])
        if not reference:
            if rows and rows[0].get(plan.metric) is not None:
                raise SQLRejected("result_mismatch")
            return
        sums = {key: sum((Decimal(str(item.get(key) or 0)) for item in reference),
                         Decimal(0)) for key in {
                             "delivered_sales", "delivered_count", "order_count",
                             "cancelled_count", "refunded_count", *STATUS_METRICS}}
        if plan.filters.get("monthly_average") == "true":
            target = sums["delivered_sales"] / len(reference)
        elif plan.metric in {"cancellation_rate", "refund_rate"}:
            numerator = "cancelled_count" if plan.metric == "cancellation_rate" else \
                "refunded_count"
            target = (sums[numerator] / sums["order_count"] if
                      sums["order_count"] else None)
        elif plan.metric == "average_order_value":
            target = (sums["delivered_sales"] / sums["delivered_count"] if
                      sums["delivered_count"] else None)
        else:
            target = sums[plan.metric]
        if target is not None and (len(rows) != 1 or
                rows[0].get(plan.metric) is None or abs(
                    Decimal(str(rows[0][plan.metric])) - Decimal(str(target))) >
                Decimal("0.01")):
            raise SQLRejected("result_mismatch")
        return
    if plan.grain == "month" and plan.group_by == ("month",) and plan.periods:
        reference = queries.monthly_sales_range(
            conn, restaurant_id, min(item["start"] for item in plan.periods),
            max(item["end"] for item in plan.periods))
        if plan.operation == "ranking":
            expected = sorted(reference, key=lambda item: item[plan.metric],
                              reverse=plan.sort == "descending")[:plan.limit]
        else:
            allowed = {item["start"] for item in plan.periods}
            expected = [item for item in reference if item["period_start"].isoformat()
                        in allowed]
        if len(rows) != len(expected):
            raise SQLRejected("result_scope")
        for row, fact in zip(rows, expected, strict=True):
            if str(row.get("period_start"))[:10] != fact["period_start"].isoformat():
                raise SQLRejected("result_scope")
            for metric in plan.metrics:
                if metric in fact and metric in row and abs(
                        Decimal(str(row[metric])) - Decimal(str(fact[metric]))) > \
                        Decimal("0.01"):
                    raise SQLRejected("result_mismatch")
        return
    if plan.grain != "year" or len(plan.periods) < 2 or \
            plan.group_by == ("restaurant_id",):
        return
    for period in plan.periods:
        year = period["start"][:4]
        actual = next((row for row in rows if str(row.get("year")) == year), None)
        expected = conn.execute(
            "SELECT SUM(delivered_sales), SUM(order_count), SUM(cancelled_count), "
            "SUM(delivered_count) FROM restaurant_monthly_sales "
            "WHERE restaurant_id = %s AND period_start >= %s AND period_start < %s",
            (str(restaurant_id), period["start"], period["end"])).fetchone()
        if expected[0] is None:
            if actual is not None:
                raise SQLRejected("result_mismatch")
            continue
        if actual is None:
            raise SQLRejected("result_scope")
        checks = {"delivered_sales": expected[0], "order_count": expected[1]}
        for metric in plan.metrics:
            if metric in checks:
                target = checks[metric]
            elif metric == "cancellation_rate":
                target = (Decimal(str(expected[2])) / Decimal(str(expected[1]))
                          if expected[1] else None)
            elif metric == "aov":
                target = (Decimal(str(expected[0])) / Decimal(str(expected[3]))
                          if expected[3] else None)
            else:
                continue
            value = actual.get(metric)
            if target is None or value is None or abs(
                    Decimal(str(value)) - Decimal(str(target))) > Decimal("0.01"):
                raise SQLRejected("result_mismatch")


def _repair_message(error, plan):
    if plan.metric in {"cancellation_rate", "refund_rate"} and \
            error.category in {"business_definition", "function_allowlist",
                               "plan_aggregation"}:
        numerator = ("cancelled_count" if plan.metric == "cancellation_rate" else
                     "refunded_count")
        return ("Annual rate must be SUM(" + numerator + ")::numeric / "
                "NULLIF(SUM(order_count), 0). Apply the period filter in WHERE "
                "only. Do not SUM or AVG monthly rates; do not use FILTER. "
                "Return one scalar row with answer_type=single_value.")
    if error.category in {"plan_periods", "plan_grouping", "plan_result_shape",
                          "result_scope"}:
        scope = ", ".join(period["start"] for period in plan.periods)
        if plan.output_shape == "scalar":
            return ("Previous SQL returned groups or dropped a requested period. "
                    "Return exactly one aggregate row, answer_type=single_value, "
                    "without GROUP BY. Preserve the exact period set " + scope + ".")
        if plan.grain == "year":
            return ("Previous SQL grouped by month or omitted a year. Use "
                    "EXTRACT(YEAR FROM period_start) AS year, SUM(delivered_sales) "
                    "AS delivered_sales, GROUP BY EXTRACT(YEAR FROM period_start), "
                    "ORDER BY year. Bind start to the earliest year January 1 and "
                    "end EXCLUSIVE to January 1 after the latest year. "
                    "Also include every metric listed in the plan. "
                    f"The requested year starts are {scope}.")
        return ("Previous SQL omitted requested periods or groups. Return separate "
                f"{plan.grain or 'period'} rows for {scope}; preserve every requested "
                "period and metric. Include GROUP BY and the period column.")
    if error.category == "period_scope" and plan.time_scope == "single_month":
        return ("Previous SQL used the wrong month filter. Use period_start = "
                "%(period)s with parameters.period=" + plan.periods[0]["start"] +
                "; one row, no GROUP BY, answer_type=single_value.")
    if error.category == "plan_ranking":
        return f"Previous SQL did not rank correctly. Add ORDER BY and LIMIT {plan.limit}."
    if error.category == "plan_trend":
        return "Previous SQL did not order the trend. Include period_start and ORDER BY period_start."
    return f"Previous rejection: {error.category}. Return safe SQL matching the validated plan."


def execute_read_only(conn, draft, *, max_rows=MAX_ROWS, timeout_ms=TIMEOUT_MS):
    """Execute in a rollback-only, read-only transaction with a database timeout."""
    # The caller validates first; this recheck prevents direct write calls.
    validate_sql(draft, {name: MART_COLUMNS[name] for name in MART_COLUMNS},
                 global_scope="restaurant_id" not in draft.parameters,
                 max_rows=max_rows)
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SELECT set_config('statement_timeout', %s, true)",
                         (str(int(timeout_ms)),))
            parameters = {key: (str(value) if key == "restaurant_id" else
                                date.fromisoformat(value) if isinstance(value, str) and
                                re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value) else value)
                          for key, value in draft.parameters.items()}
            cursor = conn.execute(draft.sql, parameters)
            columns = [item.name for item in cursor.description]
            rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchmany(max_rows + 1)]
            if len(rows) > max_rows:
                raise SQLRejected("result_limit")
            return queries.jsonable(rows)
    except SQLRejected:
        raise
    except Exception as error:
        raise SQLRejected("execution_error") from error


def _runtime_limits():
    try:
        rows = int(os.environ.get("TEXT_TO_SQL_MAX_ROWS", str(MAX_ROWS)))
        seconds = float(os.environ.get("TEXT_TO_SQL_TIMEOUT_SECONDS", "5"))
    except ValueError as error:
        raise SQLRejected("runtime_config") from error
    if not 1 <= rows <= MAX_ROWS or not 0.1 <= seconds <= 10:
        raise SQLRejected("runtime_config")
    return rows, int(seconds * 1000)


def _render_result(rows, answer_type, question=""):
    if not rows:
        return "Không có dữ liệu Sales cho câu hỏi này."
    labels = {"delivered_sales": "doanh thu Delivered", "order_count": "số đơn",
              "delivered_count": "số đơn Delivered", "aov": "AOV",
              "cancellation_rate": "tỷ lệ hủy", "refund_rate": "tỷ lệ hoàn",
              "average_order_value": "AOV",
              "cancelled_order_count": "số đơn bị hủy",
              "cancelled_order_value": "giá trị đơn bị hủy",
              "refunded_order_count": "số đơn hoàn tiền",
              "refunded_order_value": "giá trị đơn hoàn tiền",
              "restaurant_name": "nhà hàng", "period_start": "kỳ"}

    def format_item(key, value):
        label = labels.get(key, key.replace("_", " "))
        if value is not None and UNITS.get(key) == "VND":
            return f"{label}: {float(value):,.0f} ₫".replace(",", ".")
        if value is not None and UNITS.get(key) == "VND/order":
            return f"{label}: {float(value):,.0f} ₫/đơn".replace(",", ".")
        if value is not None and UNITS.get(key) == "%":
            return f"{label}: {float(value) * 100:.2f}%"
        if value is not None and UNITS.get(key) == "orders":
            return f"{label}: {float(value):,.0f} đơn".replace(",", ".")
        return f"{label}: {value}"

    if len(rows) == 2 and all("year" in row and "delivered_sales" in row for row in rows):
        ordered = sorted(rows, key=lambda row: str(row["year"]))
        first, second = ordered
        earlier = Decimal(str(first["delivered_sales"]))
        later = Decimal(str(second["delivered_sales"]))
        difference = later - earlier
        growth = (difference / earlier * 100) if earlier else None
        text = (f"Doanh thu Delivered {first['year']}: {earlier:,.0f} ₫; "
                f"{second['year']}: {later:,.0f} ₫; chênh lệch {difference:,.0f} ₫")
        for key in ("order_count", "aov", "cancellation_rate"):
            if key in first and key in second:
                text += (f"; {key.replace('_', ' ')} {first['year']}: "
                         f"{format_item(key, first[key])}; {second['year']}: "
                         f"{format_item(key, second[key])}")
        return (text + (f"; tăng trưởng {growth:+.2f}%." if growth is not None
                        else "; không thể tính tỷ lệ tăng trưởng vì năm gốc bằng 0.")).replace(",", ".")

    if len(rows) == 1 and "delivered_sales" in rows[0]:
        from src.sales.planner import build_sales_plan

        try:
            plan = build_sales_plan(question)
        except ValueError:
            plan = None
        if plan and plan.kind in {"RANGE_AGGREGATE", "YEAR_AGGREGATE"} and \
                plan.aggregation == "sum":
            value = rows[0]["delivered_sales"]
            if value is None:
                return "Không có dữ liệu Sales cho câu hỏi này."
            period = (" và ".join(plan.periods) if plan.period_selection ==
                      "EXPLICIT_SET" else f"{plan.periods[0]} đến {plan.periods[-1]}")
            return (f"Tổng doanh thu Delivered {period}: "
                    f"{Decimal(str(value)):,.0f} ₫.").replace(",", ".")
    if len(rows) == 1:
        values = ", ".join(format_item(key, value) for key, value in rows[0].items())
        return f"Kết quả Sales đã xác minh: {values}."
    if answer_type == "comparison" and all(
        "period_start" in row and "delivered_sales" in row for row in rows
    ):
        from src.sales.planner import extract_requested_periods

        by_period = {str(row["period_start"])[:7]: Decimal(str(row["delivered_sales"]))
                     for row in rows}
        requested = extract_requested_periods(question)
        if len(requested) == 2 and all(period in by_period for period in requested):
            current, prior = (by_period[period] for period in requested)
            difference = current - prior
            relation = "cao hơn" if difference > 0 else "thấp hơn" if difference < 0 else "bằng"
            return (f"Doanh thu Delivered {requested[0]} là {current:,.0f} ₫; "
                    f"{relation} {requested[1]} ({prior:,.0f} ₫) "
                    f"{abs(difference):,.0f} ₫.").replace(",", ".")
    preview = "; ".join(", ".join(format_item(key, value) for key, value in row.items())
                        for row in rows[:5])
    kind = "xếp hạng" if answer_type == "ranking" else "phân tích"
    return f"Kết quả {kind} Sales đã xác minh, {len(rows)} hàng: {preview}."


def verify_result_rows(rows, draft, question):
    """Require both observed periods before rendering a two-month comparison."""
    if draft.answer_type != "comparison" or not rows:
        return
    from src.sales.planner import extract_requested_periods

    try:
        periods = extract_requested_periods(question)
    except ValueError:
        periods = build_canonical_plan(question).time_scope.periods
    if len(periods) == 2:
        observed = {str(row.get("period_start", ""))[:7] for row in rows}
        if not set(periods) <= observed:
            raise SQLRejected("result_scope")


def verify_result_against_mart(conn, restaurant_id, question, rows, *, global_scope=False):
    """Cross-check one-month scalar answers against the frozen deterministic mart."""
    if global_scope:
        return
    from src.sales.planner import extract_requested_periods

    canonical = build_canonical_plan(question)
    if canonical.time_scope.kind == "explicit_months" and \
            len(canonical.time_scope.periods) > 1 and \
            canonical.operation == "aggregate":
        metric = canonical.metrics[0]
        periods = canonical.time_scope.periods
        if metric in STATUS_METRICS:
            found = queries.monthly_status_values_range(
                conn, restaurant_id, periods[0] + "-01",
                next_month(periods[-1]) + "-01")
            by_period = {str(item["period_start"])[:7]: item for item in found}
            references = [by_period.get(period) for period in periods]
        else:
            references = [queries.monthly_sales(conn, restaurant_id, period)
                          for period in periods]
        if any(item is None or item.get(metric) is None for item in references):
            if rows and any(row.get(metric) is not None for row in rows):
                raise SQLRejected("result_mismatch")
            return
        if canonical.output_shape == "grouped_rows":
            if len(rows) != len(periods) or any(
                    str(row.get("period_start"))[:7] != period or
                    row.get(metric) is None or reference is None or
                    abs(Decimal(str(row[metric])) - Decimal(str(reference[metric]))) >
                    Decimal("0.01") for row, period, reference in
                    zip(rows, periods, references, strict=True)):
                raise SQLRejected("result_mismatch")
        else:
            expected = sum((Decimal(str(item[metric])) for item in references), Decimal(0))
            if len(rows) != 1 or rows[0].get(metric) is None or abs(
                    Decimal(str(rows[0][metric])) - expected) > Decimal("0.01"):
                raise SQLRejected("result_mismatch")
        return

    try:
        periods = extract_requested_periods(question)
    except ValueError:
        periods = canonical.time_scope.periods
    if len(periods) != 1:
        return
    metric = canonical.metrics[0]
    if metric is None:
        return
    if metric in STATUS_METRICS:
        matches = queries.monthly_status_values_range(
            conn, restaurant_id, periods[0] + "-01", next_month(periods[0]) + "-01")
        reference = matches[0] if matches else None
    else:
        reference = queries.monthly_sales(conn, restaurant_id, periods[0])
    source_metric = "aov" if metric == "average_order_value" else metric
    if reference is None:
        if rows:
            raise SQLRejected("result_mismatch")
        return
    if len(rows) != 1 or metric not in rows[0] or rows[0][metric] is None:
        raise SQLRejected("result_mismatch")
    try:
        difference = abs(Decimal(str(rows[0][metric])) -
                         Decimal(str(reference[source_metric])))
    except (ValueError, TypeError, ArithmeticError) as error:
        raise SQLRejected("result_mismatch") from error
    if difference > Decimal("0.01"):
        raise SQLRejected("result_mismatch")


def verify_global_ranking(conn, question, rows):
    """Cross-check global ranking against the existing fixed, parameterized mart query."""
    from src.sales.planner import extract_requested_periods

    lowered = question.casefold()
    metric = ("cancellation_rate" if "hủy" in lowered else
              "aov" if "aov" in lowered else "delivered_sales")
    periods = extract_requested_periods(question)
    month = periods[0] if periods else None
    top = re.search(r"\btop\s+(\d{1,3})\b", lowered)
    limit = min(int(top.group(1)), 100) if top else 1
    expected = queries.rank_sales_restaurants(
        conn, metric=metric, month=month,
        highest=not any(term in lowered for term in ("thấp nhất", "ít nhất")),
        limit=limit)
    if len(rows) != len(expected):
        raise SQLRejected("result_mismatch")
    for actual, reference in zip(rows, expected, strict=True):
        value = actual.get(metric, actual.get("metric_value"))
        if (str(actual.get("restaurant_id")) != str(reference["restaurant_id"]) or
                value is None or
                abs(Decimal(str(value)) - Decimal(str(reference["metric_value"]))) >
                Decimal("0.01")):
            raise SQLRejected("result_mismatch")


def answer_with_text_to_sql(conn, restaurant_id, question, *, gateway_factory=None,
                            audit_sink=None, canonical_plan=None):
    """Return a verified Sales result or raise for deterministic fallback."""
    started = perf_counter()
    request_id = uuid4().hex
    if unsafe_request(question):
        security_event("text_to_sql", "unsafe_request", status="rejected",
                       request_id=request_id)
        raise SQLRejected("unsafe_request")
    schema = select_schema(question, canonical_plan)
    try:
        analytical_plan = build_sql_analytical_plan(question, canonical=canonical_plan)
    except ValueError as error:
        raise SQLRejected("plan_periods") from error
    global_scope = _scope_is_global(question)
    template = PROMPT.read_text(encoding="utf-8")
    schema_text = _prompt_schema(schema, analytical_plan)
    system = template.replace("{schema}", schema_text).replace(
        "{examples}", select_examples(question, schema))
    plan_text = _prompt_plan(analytical_plan)
    user = (f"question={question}\nscope=global ranking across all restaurants"
            if global_scope else
            f"restaurant_id={restaurant_id}\nquestion={question}\nscope=one restaurant")
    user += ("\nvalidated_analytical_plan=" + plan_text +
             "\nGenerate SQL from this plan. Preserve every period and every metric. "
             "For comparisons return a row per period and intermediate values; "
             "for ranking include ORDER BY and LIMIT; for trends order chronologically.")
    if gateway_factory is None:
        from src.rag_v3.cli import selected_v3_gateway

        gateway_factory = selected_v3_gateway
    last_error = None
    generation_ms = 0.0
    input_tokens = 0
    output_tokens = 0
    try:
        max_rows, timeout_ms = _runtime_limits()
        with gateway_factory() as gateway:
            for _attempt in range(2):
                attempt = {"number": _attempt + 1}
                call_started = perf_counter()
                if audit_sink is not None:
                    audit_sink.append(attempt)
                try:
                    try:
                        repair = ""
                        if last_error:
                            if global_scope:
                                top = re.search(r"\btop\s+(\d{1,3})\b", question.casefold())
                                requested_rows = min(int(top.group(1)), 100) if top else 1
                                repair = ("\nPrevious rejection: " + last_error.category +
                                          f". Return exactly LIMIT {requested_rows}; "
                                          "no restaurant_id filter or parameter; "
                                          "parameters must match SQL placeholders exactly.")
                            else:
                                repair = "\n" + _repair_message(last_error, analytical_plan)
                        generated, telemetry = gateway.generate(
                            system=system, user=user + repair,
                            response_schema=SQLDraft.model_json_schema(),
                            prompt_version="text_to_sql_v2", max_new_tokens=256,
                            timeout_seconds=150,
                            component="sales_text_to_sql_generation",
                            audit_sink=attempt.setdefault("raw", []))
                    except (ValueError, KeyError, TypeError, requests.RequestException) as error:
                        raise SQLRejected("structured_output") from error
                    generation_ms += telemetry.get("latency_ms") or 0
                    input_tokens += telemetry.get("input_tokens") or 0
                    output_tokens += telemetry.get("output_tokens") or 0
                    attempt.update({"structured_output_valid": True,
                                    "generated_sql": generated.get("sql"),
                                    "input_tokens": telemetry.get("input_tokens"),
                                    "output_tokens": telemetry.get("output_tokens"),
                                    "generation_latency_ms": telemetry.get("latency_ms")})
                    draft = validate_sql(generated, schema, global_scope=global_scope,
                                         max_rows=max_rows)
                    if not global_scope and str(draft.parameters["restaurant_id"]) != str(restaurant_id):
                        raise SQLRejected("restaurant_scope")
                    verify_question_scope(draft, question)
                    verify_sql_plan(draft, analytical_plan)
                    execution_start = perf_counter()
                    from src.warehouse.loader import ai_connection

                    with ai_connection() as read_conn:
                        rows = execute_read_only(read_conn, draft, max_rows=max_rows,
                                                 timeout_ms=timeout_ms)
                    attempt["execution_latency_ms"] = (perf_counter() -
                                                       execution_start) * 1000
                    verify_result_rows(rows, draft, question)
                    verify_plan_rows(rows, analytical_plan)
                    if canonical_plan is not None:
                        try:
                            result_metadata = verify_result_shape(rows, canonical_plan)
                        except ValueError as error:
                            raise SQLRejected("result_shape") from error
                        scope = canonical_plan.time_scope
                        if scope.periods and not global_scope:
                            mart_rows = queries.monthly_sales_range(
                                conn, restaurant_id, min(item["start"] for item in scope.bounds),
                                max(item["end"] for item in scope.bounds))
                            observed_months = {str(row["period_start"])[:7]
                                               for row in mart_rows}
                            result_metadata = {
                                "observed_periods": [month for month in scope.periods
                                                     if month in observed_months],
                                "missing_periods": [month for month in scope.periods
                                                    if month not in observed_months],
                            }
                    else:
                        result_metadata = {"observed_periods": [], "missing_periods": []}
                    verify_result_against_mart(conn, restaurant_id, question, rows,
                                               global_scope=global_scope)
                    if not global_scope:
                        verify_plan_against_mart(conn, restaurant_id, rows,
                                                 analytical_plan)
                    if global_scope:
                        verify_global_ranking(conn, question, rows)
                    attempt.update({"validator": "PASS", "execution": "PASS",
                                    "result_correctness": True})
                    execution_ms = (perf_counter() - execution_start) * 1000
                    observe_text_to_sql("success", generation_ms, execution_ms,
                                        (perf_counter() - started) * 1000,
                                        input_tokens=input_tokens, output_tokens=output_tokens,
                                        tables=draft.tables_used)
                    observe_sales_sql((perf_counter() - started),
                                      "ok" if rows else "no_data")
                    record("sales_text_to_sql", gateway.name, gateway.version,
                           "text_to_sql_v2", (perf_counter() - started) * 1000, "success",
                           input_tokens=telemetry.get("input_tokens"),
                           output_tokens=telemetry.get("output_tokens"),
                           generation_mode="QWEN_TEXT_TO_SQL")
                    answer = _render_result(rows, draft.answer_type, question)
                    missing_periods = result_metadata["missing_periods"]
                    if analytical_plan.operation == "trend":
                        observed_periods = {str(row.get("period_start", ""))[:7]
                                            for row in rows}
                        if canonical_plan is None:
                            missing_periods = [period["start"][:7]
                                               for period in analytical_plan.periods
                                               if period["start"][:7] not in observed_periods]
                        if missing_periods:
                            answer += (" Các tháng chưa có hàng dữ liệu trong kỳ đã yêu cầu: " +
                                       ", ".join(missing_periods) + ".")
                        current_month = queries.vietnam_today().strftime("%Y-%m")
                        if current_month in observed_periods:
                            answer += f" Tháng {current_month} đang diễn ra; số liệu có thể chưa đủ tháng."
                    elif missing_periods:
                        answer += (" Các tháng chưa có hàng dữ liệu trong kỳ đã yêu cầu: " +
                                   ", ".join(missing_periods) + ".")
                    if analytical_plan.grain == "year" and any(
                            period["end"] > date.today().isoformat()
                            for period in analytical_plan.periods):
                        answer += " Năm hiện tại chỉ gồm dữ liệu tháng đã quan sát."
                    return {"route": "SALES_SQL", "source": "SQL Analytics",
                            "answer": answer,
                            "restaurant_id": str(restaurant_id), "sql_facts": rows,
                            "review_evidence": [], "status": "ok" if rows else "no_data",
                            "display_rows": rows, "execution_mode": "QWEN_TEXT_TO_SQL",
                            "query_plan": {"intent": analytical_plan.operation,
                                           "canonical_plan": (canonical_plan.as_dict()
                                                              if canonical_plan else None),
                                           "output_shape": analytical_plan.output_shape,
                                           "metric": analytical_plan.metric,
                                           "metrics": list(analytical_plan.metrics),
                                           "result_unit": UNITS[analytical_plan.metric],
                                           "periods": [period["start"][:4 if
                                                       analytical_plan.grain == "year" else 7]
                                                       for period in analytical_plan.periods],
                                           "period_ranges": list(analytical_plan.periods),
                                           "missing_periods": missing_periods,
                                           "observed_periods": result_metadata["observed_periods"],
                                           "group_by": list(analytical_plan.group_by),
                                           "aggregation": ("monthly_average" if
                                                           analytical_plan.filters.get(
                                                               "monthly_average") == "true"
                                                           else "sum" if
                                                           analytical_plan.operation == "aggregate"
                                                           else None),
                                           "sort": analytical_plan.sort,
                                           "limit": analytical_plan.limit},
                            "sql_details": {"sql": draft.sql, "tables_used": draft.tables_used,
                                            "validation_status": "SQL validated before execution",
                                            "semantic_verification": "PASS",
                                            "generation_attempt_count": _attempt + 1,
                                            "generation_latency_ms": generation_ms,
                                            "execution_latency_ms": execution_ms,
                                            "total_latency_ms": (perf_counter() - started) * 1000,
                                            "input_tokens": input_tokens,
                                            "output_tokens": output_tokens,
                                            "answer_type": draft.answer_type}}
                except SQLRejected as error:
                    security_event("text_to_sql", error.category, status="rejected",
                                   request_id=request_id)
                    last_error = error
                    attempt.setdefault("generation_latency_ms", (perf_counter() -
                                                                 call_started) * 1000)
                    attempt["rejection"] = error.category
                    if error.category in {"execution_error", "result_limit",
                                          "result_mismatch", "result_scope"}:
                        attempt["validator"] = "PASS"
                        attempt["execution"] = ("FAIL" if error.category ==
                                                "execution_error" else "PASS")
                    else:
                        attempt["validator"] = "FAIL"
                    if error.category == "execution_error":
                        observe_text_to_sql("execution_failure", generation_ms, 0,
                                            (perf_counter() - started) * 1000)
                    observe_text_to_sql("validation_failure", generation_ms, 0,
                                        (perf_counter() - started) * 1000,
                                        reason=error.category)
                except Exception as error:
                    security_event("text_to_sql", type(error).__name__,
                                   request_id=request_id)
                    attempt.update({"rejection": type(error).__name__,
                                    "generation_latency_ms": (perf_counter() -
                                                              call_started) * 1000})
                    raise
        raise last_error or SQLRejected("generation_error")
    except Exception:
        observe_text_to_sql("fallback", generation_ms, 0,
                            (perf_counter() - started) * 1000,
                            input_tokens=input_tokens, output_tokens=output_tokens)
        raise


def enabled():
    return os.environ.get("TEXT_TO_SQL_ENABLED", "false").casefold() == "true"
