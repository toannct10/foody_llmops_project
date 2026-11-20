"""Canonical, deterministic Sales semantics shared by generation and fallback."""

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date

from src.sales.metric_ontology import UNITS, detect_metrics

OPERATIONS = {"aggregate", "range_aggregate", "comparison", "trend", "ranking",
              "growth", "rate", "multi_metric"}
SHAPES = {"scalar", "grouped_rows", "comparison", "time_series", "ranking",
          "multi_metric"}
TIME_KINDS = {"single_month", "explicit_months", "continuous_range", "quarter",
              "half_year", "year", "multiple_years", "all_observed"}
METRICS = set(UNITS)


def plain(value):
    value = unicodedata.normalize("NFD", value.casefold()).replace("đ", "d")
    return "".join(char for char in value if unicodedata.category(char) != "Mn")


def month_key(year, month):
    year, month = int(year), int(month)
    if not 1 <= month <= 12 or not 2000 <= year <= 2099:
        raise ValueError("Tháng không hợp lệ hoặc năm ngoài phạm vi hỗ trợ")
    return f"{year:04d}-{month:02d}"


def next_month(month):
    year, number = map(int, month.split("-"))
    return month_key(year + (number == 12), number % 12 + 1)


def month_range(start, end):
    first = int(start[:4]) * 12 + int(start[5:]) - 1
    last = int(end[:4]) * 12 + int(end[5:]) - 1
    count = last - first + 1
    if not 1 <= count <= 100:
        raise ValueError("Sales range must contain 1 to 100 ordered months")
    return tuple(month_key((first + index) // 12, (first + index) % 12 + 1)
                 for index in range(count))


@dataclass(frozen=True)
class TimeScope:
    kind: str
    periods: tuple[str, ...]
    bounds: tuple[dict[str, str], ...]
    groups: tuple[tuple[str, ...], ...]

    def as_dict(self):
        return asdict(self)


def _scope(kind, groups):
    groups = tuple(tuple(group) for group in groups)
    periods = tuple(dict.fromkeys(month for group in groups for month in group))
    return TimeScope(kind, periods,
                     tuple({"start": group[0] + "-01",
                            "end": next_month(group[-1]) + "-01"} for group in groups),
                     groups)


def parse_time_scope(question, *, today=None):
    """Parse temporal grammar independently of Sales operation words."""
    value = plain(question)
    today = today or date.today()
    recent = re.search(r"\b(\d{1,2})\s+thang\s+gan\s+day\b", value)
    if recent:
        last = today.replace(day=1).fromordinal(today.replace(day=1).toordinal() - 1)
        end = last.strftime("%Y-%m")
        last_index = last.year * 12 + last.month - 1
        count = int(recent.group(1))
        if not 1 <= count <= 100:
            raise ValueError("Invalid recent month count")
        start_index = last_index - count + 1
        start = month_key(start_index // 12, start_index % 12 + 1)
        return _scope("continuous_range", (month_range(start, end),))

    quarter = re.search(r"\b(?:quy\s*|q)([1-4])\s*(?:nam\s*|/)(20\d{2})\b", value)
    if quarter:
        number, year = map(int, quarter.groups())
        return _scope("quarter", (month_range(month_key(year, 3 * number - 2),
                                               month_key(year, 3 * number)),))
    half = re.search(r"\b6\s+thang\s+(dau|cuoi)\s+nam\s+(20\d{2})\b", value)
    if half:
        first = 1 if half.group(1) == "dau" else 7
        year = int(half.group(2))
        return _scope("half_year", (month_range(month_key(year, first),
                                                 month_key(year, first + 5)),))

    endpoint = r"(?:(?:thang|t)\s*)?(\d{1,2})(?:\s*/\s*(20\d{2}))?"
    span = re.search(r"\b(?:tu\s+)?" + endpoint + r"\s+den\s+" + endpoint +
                     r"(?:\s+nam\s+(20\d{2}))?\b", value)
    if span:
        first, first_year, last, last_year, shared_year = span.groups()
        year1 = first_year or shared_year or last_year
        year2 = last_year or shared_year or first_year
        if not year1 or not year2:
            raise ValueError("A Sales month range needs a year")
        return _scope("continuous_range", (month_range(month_key(year1, first),
                                                       month_key(year2, last)),))

    shared = re.search(r"\b(?:thang|t)\s*\d{1,2}"
                       r"(?:\s*(?:,|va|voi|so voi)\s*(?:(?:thang|t)\s*)?\d{1,2})+"
                       r"\s+nam\s+(20\d{2})\b", value)
    if shared:
        numbers = re.findall(r"\d{1,2}", shared.group()[:shared.group().rfind("nam")])
        months = tuple(month_key(shared.group(1), number) for number in numbers)
        if len(set(months)) != len(months):
            raise ValueError("Duplicate Sales month")
        return _scope("explicit_months", tuple((month,) for month in months))

    iso_months = re.findall(r"\b(20\d{2})-(\d{1,2})\b", value)
    if iso_months:
        months = tuple(month_key(year, month) for year, month in iso_months)
        return _scope("single_month" if len(months) == 1 else "explicit_months",
                      tuple((month,) for month in months))

    dated = list(re.finditer(r"\b(?:thang\s*|t)?(\d{1,2})\s*/\s*(20\d{2})\b|"
                             r"\b(?:thang|t)\s*(\d{1,2})\s+nam\s+(20\d{2})\b",
                             value))
    if dated:
        found = [(match.start(), month_key(match.group(2) or match.group(4),
                                          match.group(1) or match.group(3)))
                 for match in dated]
        years = set(re.findall(r"\b20\d{2}\b", value))
        if len(years) == 1:
            remainder = value
            for match in reversed(dated):
                remainder = (remainder[:match.start()] +
                             " " * (match.end() - match.start()) +
                             remainder[match.end():])
            found.extend((match.start(), month_key(next(iter(years)), match.group(1)))
                         for match in re.finditer(r"\b(?:thang|t)\s*(\d{1,2})\b",
                                                  remainder))
        months = tuple(dict.fromkeys(month for _, month in sorted(found)))
        return _scope("single_month" if len(months) == 1 else "explicit_months",
                      tuple((month,) for month in months))

    years = tuple(dict.fromkeys(re.findall(r"\b20\d{2}\b", value)))
    bare_months = re.findall(r"\b(?:thang|t)\s*(\d{1,2})\b", value)
    if bare_months:
        if len(years) > 1:
            raise ValueError("A Sales month needs one unambiguous year")
        year = years[0] if years else str(today.year)
        months = tuple(month_key(year, month) for month in bare_months)
        return _scope("single_month" if len(months) == 1 else "explicit_months",
                      tuple((month,) for month in months))
    if years:
        return _scope("year" if len(years) == 1 else "multiple_years",
                      tuple(month_range(month_key(year, 1), month_key(year, 12))
                            for year in years))
    return TimeScope("all_observed", (), (), ())


@dataclass(frozen=True)
class CanonicalPlan:
    operation: str
    metrics: tuple[str, ...]
    time_scope: TimeScope
    group_by: tuple[str, ...]
    filters: dict[str, str]
    sort: tuple[str, ...]
    limit: int | None
    output_shape: str
    include_breakdown: bool = False

    def as_dict(self):
        return asdict(self)


def build_canonical_plan(question, *, today=None):
    value = plain(question)
    scope = parse_time_scope(question, today=today)
    if len(scope.groups) == 1 and scope.kind == "single_month":
        current = scope.periods[0]
        year, month = map(int, current.split("-"))
        if re.search(r"cung ky nam truoc|cung thang nam truoc|cung ky nam ngoai|\byoy\b",
                     value):
            scope = _scope("explicit_months", ((current,), (month_key(year - 1, month),)))
        elif re.search(r"so voi thang truoc|\bmom\b", value):
            previous = month_key(year - (month == 1), (month - 2) % 12 + 1)
            scope = _scope("explicit_months", ((current,), (previous,)))
    metrics = detect_metrics(value)
    top = re.search(r"\btop\s+(\d{1,3})\b", value)
    ranking = bool(top or "cao nhat" in value or "thap nhat" in value)
    growth = bool(re.search(r"tang bao nhieu\s*(?:%|phan tram)|tang truong|\byoy\b|\bmom\b", value))
    comparison = bool(re.search(r"\bso sanh\b|\bso voi\b|\bvoi\b|\bvs\b|chenh lech", value))
    trend = bool(re.search(r"xu huong|\btrend\b", value) or
                 ("gan day" in value and "tong" not in value))
    breakdown = bool(re.search(r"chi tiet|tung thang|phan ra", value))
    filters = {"monthly_average": "true"} if "trung binh moi thang" in value else {}
    if any(metric.startswith("cancelled_") or metric == "cancellation_rate"
           for metric in metrics):
        filters["order_status"] = "Cancelled"
    elif any(metric.startswith("refunded_") or metric == "refund_rate"
             for metric in metrics):
        filters["order_status"] = "Refunded"
    if scope.kind in {"single_month", "explicit_months"} and not re.search(
            r"\b20\d{2}\b", value):
        filters["inferred_year"] = str((today or date.today()).year)
    limit = int(top.group(1)) if top else 1 if ranking else None
    if ranking:
        operation, shape = "ranking", "ranking"
        group_by = ("restaurant_id",) if any(word in value for word in
                                            ("nha hang", "restaurant")) else ("month",)
        sort = ("ascending" if "thap nhat" in value else "descending",)
    elif trend:
        operation, shape, group_by, sort = "trend", "time_series", ("month",), ("chronological",)
    elif growth:
        operation, shape, group_by, sort = "growth", "comparison", ("period",), ("chronological",)
    elif len(metrics) > 1:
        operation, shape = "multi_metric", "multi_metric"
        group_by = ("period",) if len(scope.groups) > 1 else ()
        sort = ("chronological",) if group_by else ()
    elif comparison or scope.kind == "multiple_years":
        operation, shape, group_by, sort = "comparison", "comparison", ("period",), ("chronological",)
    elif any(metric.endswith("_rate") for metric in metrics):
        operation, shape, group_by, sort = "rate", "scalar", (), ()
    elif scope.kind in {"continuous_range", "quarter", "half_year"}:
        operation, shape, group_by, sort = "range_aggregate", "scalar", (), ()
    elif scope.kind == "explicit_months" and len(scope.periods) > 1 and not re.search(
            r"\btong\b|\btotal\b|\bsum\b", value):
        operation, shape, group_by, sort = "aggregate", "grouped_rows", ("month",), \
            ("chronological",)
    else:
        operation, shape, group_by, sort = "aggregate", "scalar", (), ()
    if "giam manh nhat" in value and "thang truoc" in value:
        operation, shape, group_by, sort = "growth", "comparison", ("month",), ("chronological",)
        filters["analytical_step"] = "largest_mom_decline"
    elif "cao nhat" in value and "thap nhat" in value:
        operation, shape, group_by, sort, limit = (
            "ranking", "comparison", ("month",), ("descending",), 2)
        filters["analytical_step"] = "max_min_spread"
    plan = CanonicalPlan(operation, metrics, scope, group_by, filters, sort, limit, shape,
                         breakdown)
    validate_plan(plan)
    return plan


def validate_plan(plan):
    if plan.operation not in OPERATIONS or plan.output_shape not in SHAPES:
        raise ValueError("Unsupported analytical operation or output shape")
    if plan.time_scope.kind not in TIME_KINDS:
        raise ValueError("Unsupported Sales time scope")
    flattened = tuple(dict.fromkeys(month for group in plan.time_scope.groups
                                    for month in group))
    if plan.time_scope.periods != flattened:
        raise ValueError("Sales plan dropped or added requested periods")
    if not plan.metrics or not set(plan.metrics) <= METRICS:
        raise ValueError("Unsupported or missing Sales metric")
    if plan.limit is not None and not 1 <= plan.limit <= 100:
        raise ValueError("Ranking limit must be 1 to 100")
    if plan.operation == "ranking" and not plan.limit:
        raise ValueError("Ranking requires a limit")
    if plan.operation == "trend" and "month" not in plan.group_by:
        raise ValueError("Trend requires monthly grouping")
    if plan.operation in {"comparison", "growth"} and len(plan.time_scope.groups) < 2 and \
            not plan.filters.get("analytical_step"):
        raise ValueError("Comparison requires two explicit periods")
    if plan.operation in {"aggregate", "range_aggregate", "rate"} and \
            plan.output_shape == "scalar" and plan.group_by:
        raise ValueError("Scalar aggregation cannot group its final value")
    if plan.operation == "multi_metric" and len(plan.metrics) < 2:
        raise ValueError("Multi-metric analysis requires two metrics")
    for group, bounds in zip(plan.time_scope.groups, plan.time_scope.bounds, strict=True):
        if not group or bounds["start"] != group[0] + "-01" or \
                bounds["end"] != next_month(group[-1]) + "-01":
            raise ValueError("Invalid Sales time bounds")
        if tuple(sorted(group)) != group:
            raise ValueError("A period group must be chronological")
    if len(plan.time_scope.periods) != len(set(plan.time_scope.periods)):
        raise ValueError("Overlapping Sales periods")


def verify_result_shape(rows, plan):
    """Verify final row shape and report unobserved months without inventing zeros."""
    validate_plan(plan)
    if plan.output_shape == "scalar" and len(rows) > 1 and not plan.include_breakdown:
        raise ValueError("Scalar Sales result has more than one row")
    if plan.operation == "ranking" and len(rows) > plan.limit:
        raise ValueError("Ranking exceeds requested limit")
    if rows and plan.operation in {"comparison", "growth"} and len(rows) < 2:
        raise ValueError("Comparison collapsed a requested side")
    if rows and plan.operation in {"comparison", "growth"}:
        expected = {_label_scope_group(group) for group in plan.time_scope.groups}
        actual = {str(row.get("year", row.get("period", row.get("period_start", ""))))
                  for row in rows}
        if not all(any(value == label or value.startswith(label + "-01")
                       for value in actual) for label in expected):
            raise ValueError("Comparison dropped a requested side")
    if rows and plan.operation == "multi_metric" and any(
            not set(plan.metrics) <= set(row) for row in rows):
        raise ValueError("Multi-metric result dropped a metric")
    periods = [str(row.get("period_start", row.get("period", row.get("year", ""))))
               for row in rows]
    if plan.operation == "trend" and periods != sorted(periods):
        raise ValueError("Trend rows are not chronological")
    if plan.operation == "ranking" and rows and all(
            row.get(plan.metrics[0]) is not None for row in rows):
        values = [float(row[plan.metrics[0]]) for row in rows]
        if values != sorted(values, reverse=plan.sort == ("descending",)):
            raise ValueError("Ranking rows are not sorted")
    requested = set(plan.time_scope.periods)
    observed = {period[:7] for period in periods if re.fullmatch(r"20\d{2}-\d{2}.*", period)}
    if observed - requested:
        raise ValueError("Result contains months outside requested scope")
    if plan.operation in {"trend", "ranking"}:
        missing = sorted(requested - observed)
    else:
        missing = []  # Aggregate rows do not expose the contributing months.
    if plan.include_breakdown and len(rows) > 1 and plan.output_shape == "scalar":
        primary = plan.metrics[0]
        total = rows[0].get(primary)
        breakdown = [row.get(primary) for row in rows[1:]]
        if total is None or any(value is None for value in breakdown) or abs(
                sum(float(value) for value in breakdown) - float(total)) > .01:
            raise ValueError("Breakdown does not reconcile to the total")
    return {"observed_periods": sorted(observed), "missing_periods": missing}


def _label_scope_group(group):
    if len(group) == 12 and group[0].endswith("-01") and group[-1].endswith("-12"):
        return group[0][:4]
    return group[0] if len(group) == 1 else f"{group[0]} – {group[-1]}"
