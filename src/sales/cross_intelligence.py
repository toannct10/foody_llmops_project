"""Period-aligned Sales and Review analysis over existing verified services."""

import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field
from requests import RequestException

from src.foody.review_runtime import new_corpus_active
from src.rag.schemas import RetrievalRequest
from src.rag_v3.routing import HYBRID_GENERAL
from src.sales import queries
from src.sales.review_aggregates import monthly_review_aggregate
from src.sales.router import route_question
from src.sales.semantic_plan import (
    build_canonical_plan,
    month_key,
    next_month,
    parse_time_scope,
    plain,
)

PROMPT = Path("prompts/cross/cross_synthesis_v1.txt")
FALLBACK_SQL = ("SELECT * FROM restaurant_monthly_sales WHERE restaurant_id=%s "
                "AND period_start >= %s AND period_start < %s "
                "ORDER BY period_start LIMIT 100")
CAUSAL = re.compile(r"nguyên nhân|dẫn đến|khiến|gây ra|caused|because|"
                    r"\bdo\b.{0,50}\bnên\b", re.IGNORECASE)
CHANGE = re.compile(r"\b(?:tang|giam|cai thien|xau di|thay doi)\b")


@dataclass(frozen=True)
class CrossPlan:
    mode: str
    restaurant_id: str
    periods: tuple[str, ...]
    sales_metrics: tuple[str, ...]
    review_metrics: tuple[str, ...]
    need_review_evidence: bool
    period_source: str
    intent: str = "PERIOD_EXPLANATION"
    operation: str = "aggregate"
    baseline_period: str | None = None
    current_period: str | None = None
    period_groups: tuple[tuple[str, ...], ...] = ()

    def as_dict(self):
        return asdict(self)


class CrossQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_quote: str = Field(max_length=160)
    evidence_ref: str


def classify_cross_intent(question):
    """Classify analytical purpose without asking a model to infer SQL or causation."""
    value = plain(question)
    if any(word in value for word in ("vi sao", "tai sao", "nguyen nhan")):
        return "WHY_CHANGE"
    if "thap nhat" in value or "hieu suat thap" in value:
        return "LOW_PERFORMANCE_REVIEW"
    if "cao nhat" in value or "hieu suat cao" in value:
        return "HIGH_PERFORMANCE_REVIEW"
    if any(word in value for word in ("khong tuong xung", "nhung sentiment",
                                      "nhung review", "nguoc chieu")):
        return "MISMATCH"
    if any(word in value for word in ("xu huong", "qua cac thang", "theo thang")):
        return "CROSS_TREND"
    if any(word in value for word in ("di kem", "tuong quan", "lien he")):
        return "CORRELATION"
    if any(word in value for word in ("service", "food", "price", "phuc vu",
                                      "mon an", "gia ca", "khong gian")):
        return "ASPECT_VS_SALES"
    if any(word in value for word in ("sentiment", "tieu cuc", "tich cuc",
                                      "trung lap")):
        return "SENTIMENT_VS_SALES"
    return "PERIOD_EXPLANATION"


def _previous_group(group):
    first = int(group[0][:4]) * 12 + int(group[0][5:]) - 1 - len(group)
    return tuple(month_key((first + index) // 12,
                           (first + index) % 12 + 1) for index in range(len(group)))


def _period_label(group, kind):
    if kind == "year":
        return group[0][:4]
    if kind == "quarter":
        return f"{group[0][:4]}-Q{(int(group[0][5:]) - 1) // 3 + 1}"
    return group[0]


def build_cross_plan(question, restaurant_id, *, today=None, default_periods=(),
                     analysis_year=None):
    """Reuse the canonical Sales period parser; never infer a name-based join."""
    route = route_question(question)
    intent = classify_cross_intent(question)
    mode = {"SALES_SQL": "sales_only", "REVIEW_RAG": "review_only",
            "CROSS_ANALYSIS": "cross_analysis"}[route]
    if mode == "sales_only" and intent in {"WHY_CHANGE", "MISMATCH", "CROSS_TREND",
                                          "CORRELATION", "ASPECT_VS_SALES",
                                          "SENTIMENT_VS_SALES"}:
        mode = "cross_analysis"
    value = plain(question)
    bare_month = re.search(r"\b(?:thang|t)\s*(\d{1,2})\b", value)
    if bare_month and not re.search(r"\b20\d{2}\b", value):
        if analysis_year is None:
            raise ValueError(f"Please specify the year for month {int(bare_month.group(1))}.")
        month_key(analysis_year, bare_month.group(1))
        question = f"{question} năm {analysis_year}"
    scope = parse_time_scope(question, today=today)
    can_infer = (len(scope.groups) == 1 and
                 scope.kind in {"single_month", "quarter", "year"} and
                 bool(CHANGE.search(value)))
    try:
        canonical = build_canonical_plan(question, today=today)
    except ValueError as error:
        if not can_infer or "Comparison requires two explicit periods" not in str(error):
            raise
        neutral = re.sub(r"\b(?:so sanh|so voi|voi|vs|chenh lech)\b", " ",
                         plain(question))
        canonical = build_canonical_plan(neutral, today=today)
    periods = canonical.time_scope.periods or tuple(default_periods)
    period_source = ("explicit" if canonical.time_scope.periods else
                     "latest_common_observed_periods")
    operation = canonical.operation
    groups = ()
    baseline = current = None
    if can_infer and len(canonical.time_scope.groups) == 1:
        current_group = scope.groups[0]
        previous_group = _previous_group(current_group)
        groups = (previous_group, current_group)
        periods = previous_group + current_group
        baseline = _period_label(previous_group, scope.kind)
        current = _period_label(current_group, scope.kind)
        period_source = "inferred_previous_" + {
            "single_month": "month", "quarter": "quarter", "year": "year"}[scope.kind]
        operation = "comparison"
    elif len(periods) == 2:
        baseline, current = sorted(periods)
        groups = ((baseline,), (current,))
    if not periods:
        raise ValueError("No observed period is available for Cross Intelligence")
    return CrossPlan(mode, str(restaurant_id), tuple(periods), canonical.metrics,
                     ("review_count", "positive_count", "neutral_count",
                      "negative_count", "sentiment_rate", "aspect_frequencies",
                      "negative_review_count", "negative_review_rate"),
                     mode == "cross_analysis", period_source, intent, operation,
                     baseline, current, groups)


def _default_periods(conn, restaurant_id, today):
    """For an unspecified time, disclose the latest two months with both sources."""
    cursor = conn.execute("""SELECT s.period_start
        FROM restaurant_monthly_sales s
        JOIN dim_date d ON d.calendar_date >= s.period_start
            AND d.calendar_date < s.period_start + INTERVAL '1 month'
        JOIN fact_review_v2 r ON r.date_key=d.date_key
            AND r.restaurant_id=s.restaurant_id
        WHERE s.restaurant_id=%s AND s.period_start <= %s
        GROUP BY s.period_start ORDER BY s.period_start DESC LIMIT 2""",
        (str(restaurant_id), today.replace(day=1)))
    return tuple(sorted(row[0].strftime("%Y-%m") for row in cursor.fetchall()))


def _sales_facts(conn, restaurant_id, periods, question, today):
    """Run the existing Sales semantic path, then independently verify monthly rows."""
    from src.sales.service import sales_answer

    ordered = sorted(set(periods))
    rows = queries.monthly_sales_range(conn, restaurant_id, ordered[0] + "-01",
                                      next_month(ordered[-1]) + "-01")
    by_period = {row["period_start"].strftime("%Y-%m"): row for row in rows}
    status_rows = (queries.monthly_status_values_range(
        conn, restaurant_id, ordered[0] + "-01", next_month(ordered[-1]) + "-01")
        if conn is not None else [])
    status_by_period = {str(row["period_start"])[:7]: row for row in status_rows}
    facts = [{"period": month, "delivered_sales": float(by_period[month]["delivered_sales"]),
              "order_count": int(by_period[month]["order_count"]),
              "delivered_count": int(by_period[month].get("delivered_count") or 0),
              "aov": float(by_period[month]["aov"]) if by_period[month].get("aov")
              is not None else None,
              "cancelled_order_count": int(by_period[month].get("cancelled_count") or 0),
              "cancelled_order_value": float(status_by_period[month]["cancelled_order_value"])
              if month in status_by_period else None,
              "cancellation_rate": float(by_period[month]["cancellation_rate"])
              if by_period[month].get("cancellation_rate") is not None else None,
              "refunded_order_count": int(by_period[month].get("refunded_count") or 0),
              "refunded_order_value": float(status_by_period[month]["refunded_order_value"])
              if month in status_by_period else None,
              "refund_rate": float(by_period[month]["refund_rate"])
              if by_period[month].get("refund_rate") is not None else None}
             for month in ordered if month in by_period]
    sales_question = "so sánh doanh thu " + " và ".join(
        f"tháng {month[5:7]}/{month[:4]}" for month in ordered)
    if len(ordered) == 1:
        sales_question = f"doanh thu tháng {ordered[0][5:7]}/{ordered[0][:4]}"
    result = (sales_answer(conn, restaurant_id, sales_question, today=today)
              if facts and len(ordered) <= 2 else {})
    details = result.get("sql_details") or {}
    qwen_rows = result.get("sql_facts") or []
    if isinstance(qwen_rows, dict):
        qwen_rows = [qwen_rows]
    verified_qwen = (result.get("execution_mode") == "QWEN_TEXT_TO_SQL" and
                     details.get("semantic_verification") == "PASS" and
                     len(qwen_rows) == len(facts) == len(ordered))
    if verified_qwen:
        expected = {row["period"]: Decimal(str(row["delivered_sales"])) for row in facts}
        try:
            observed = {str(row["period_start"])[:7]: Decimal(str(row["delivered_sales"]))
                        for row in qwen_rows}
            verified_qwen = observed == expected
        except (KeyError, TypeError, ValueError):
            verified_qwen = False
    return facts, {"mode": "QWEN_TEXT_TO_SQL" if verified_qwen else
                   "PREDEFINED_PARAMETERIZED_SQL",
                   "sql": details.get("sql") if verified_qwen else FALLBACK_SQL,
                   "semantic_verification": "PASS" if verified_qwen or facts else "NO_DATA",
                   "generation_attempt_count": details.get("generation_attempt_count", 0),
                   "missing_periods": [month for month in ordered if month not in by_period]}


DRIVER_UNITS = {"delivered_sales": "VND", "order_count": "orders",
                "delivered_count": "orders", "aov": "VND/order",
                "cancelled_order_count": "orders", "cancelled_order_value": "VND",
                "cancellation_rate": "fraction", "refunded_order_count": "orders",
                "refunded_order_value": "VND", "refund_rate": "fraction"}


def calculate_sales_drivers(facts):
    """Compare measured monthly components without assigning causal credit."""
    if len(facts) < 2:
        return []
    first, last = facts[0], facts[-1]
    drivers = []
    for metric, unit in DRIVER_UNITS.items():
        if first.get(metric) is None or last.get(metric) is None:
            continue
        baseline = Decimal(str(first[metric]))
        current = Decimal(str(last[metric]))
        change = current - baseline
        drivers.append({"metric": metric, "unit": unit,
                        "baseline_period": first["period"], "current_period": last["period"],
                        "baseline": float(baseline), "current": float(current),
                        "absolute_change": float(change),
                        "percentage_change": float(change / baseline * 100)
                        if baseline else None,
                        "percentage_point_change": float(change * 100)
                        if unit == "fraction" else None})
    return drivers


def _group_sales_facts(monthly_facts, plan):
    """Sum observed months within inferred quarters/years, never invent missing rows."""
    if not plan.period_groups or all(len(group) == 1 for group in plan.period_groups):
        return monthly_facts
    by_month = {item["period"]: item for item in monthly_facts}
    grouped = []
    for label, months in zip((plan.baseline_period, plan.current_period),
                             plan.period_groups, strict=True):
        rows = [by_month[month] for month in months if month in by_month]
        if not rows:
            continue
        def total(key, current_rows=rows):
            return sum(item[key] for item in current_rows
                       if item.get(key) is not None)
        delivered = total("delivered_sales")
        orders = total("order_count")
        delivered_count = total("delivered_count")
        cancelled = total("cancelled_order_count")
        refunded = total("refunded_order_count")
        grouped.append({"period": label, "delivered_sales": delivered,
                        "order_count": orders, "delivered_count": delivered_count,
                        "aov": delivered / delivered_count if delivered_count else None,
                        "cancelled_order_count": cancelled,
                        "cancelled_order_value": total("cancelled_order_value")
                        if all(item.get("cancelled_order_value") is not None
                               for item in rows) else None,
                        "cancellation_rate": cancelled / orders if orders else None,
                        "refunded_order_count": refunded,
                        "refunded_order_value": total("refunded_order_value")
                        if all(item.get("refunded_order_value") is not None
                               for item in rows) else None,
                        "refund_rate": refunded / orders if orders else None})
    return grouped


def _group_review_signals(monthly, plan):
    if not plan.period_groups or all(len(group) == 1 for group in plan.period_groups):
        return monthly
    by_month = {item["period"]: item for item in monthly}
    grouped = []
    for label, months in zip((plan.baseline_period, plan.current_period),
                             plan.period_groups, strict=True):
        rows = [by_month[month] for month in months if month in by_month]
        counts = {key: sum(item[key] for item in rows) for key in
                  ("review_count", "positive_count", "neutral_count", "negative_count")}
        aspects = {}
        for item in rows:
            for aspect, count in item["aspect_frequencies"].items():
                aspects[aspect] = aspects.get(aspect, 0) + count
        total = counts["review_count"]
        grouped.append({"period": label, **counts,
                        "sentiment_rate": {name: counts[name + "_count"] / total
                                           if total else None for name in
                                           ("positive", "neutral", "negative")},
                        "aspect_frequencies": aspects,
                        "label_source": "production_sentiment_and_aspect_predictions"})
    return grouped


def _review_evidence(retriever, restaurant_id, aggregates, question):
    normalized = plain(question)
    negative = any(word in normalized for word in
                   ("tieu cuc", "phan nan", "khieu nai"))
    aspect = next((label for words, label in (
        (("service", "phuc vu"), "phục vụ"),
        (("food", "mon an"), "món ăn"),
        (("price", "gia ca"), "giá"),
        (("space", "khong gian", "ambiance"), "không gian"))
        if any(word in normalized for word in words)), None)
    query = ("đánh giá tiêu cực phàn nàn về " if negative else "phản hồi về ") + \
        (aspect or "món ăn phục vụ giá và chất lượng")
    policy = (retriever.policies[HYBRID_GENERAL.name] if hasattr(retriever, "policies")
              else retriever)
    evidence, methods, searched = [], [], []
    for aggregate in [item for item in aggregates if item["review_count"]][-6:]:
        period = aggregate["period"]
        start = date.fromisoformat(period + "-01")
        end = date.fromisoformat(next_month(period) + "-01")
        request = RetrievalRequest(
            query=query, restaurant_id=str(restaurant_id),
            date_from=datetime.combine(start, time.min),
            date_to=datetime.combine(end, time.min) - timedelta(microseconds=1),
            sentiment="negative" if negative else None, top_k=3)
        hits, _, debug = policy.search_debug(request)
        searched.append(period)
        methods.append(debug.get("retrieval_method", HYBRID_GENERAL.name))
        for hit in hits:
            metadata = hit.metadata
            stamp = str(metadata.get("review_timestamp", ""))[:10]
            try:
                observed_date = date.fromisoformat(stamp)
            except ValueError:
                continue
            if (str(metadata.get("restaurant_id")) != str(restaurant_id) or
                    not start <= observed_date < end or
                    any(item["review_id"] == hit.review_id for item in evidence)):
                continue
            aspects = metadata.get("predicted_aspects") or []
            if isinstance(aspects, str):
                try:
                    aspects = json.loads(aspects)
                except (TypeError, ValueError):
                    aspects = []
            evidence.append({"ref": f"E{len(evidence) + 1}", "review_id": hit.review_id,
                             "restaurant_id": str(restaurant_id), "period": period,
                             "date": stamp, "text": hit.text[:350],
                             "sentiment": metadata.get("predicted_sentiment"),
                             "aspects": aspects,
                             "source": metadata.get("source")})
    return evidence, {"method": HYBRID_GENERAL.name,
                      "observed_methods": methods, "searched_periods": searched,
                      "filters": {"restaurant_id": str(restaurant_id),
                                  "periods": searched,
                                  "sentiment": "negative" if negative else None}}


def _verify_evidence_in_warehouse(conn, restaurant_id, periods, evidence):
    """Keep only retrieved IDs whose warehouse entity and date agree with the plan."""
    if not evidence or conn is None:
        return evidence
    ids = [item["review_id"] for item in evidence]
    cursor = conn.execute("""SELECT r.review_id, r.restaurant_id, d.calendar_date
        FROM fact_review_v2 r JOIN dim_date d ON d.date_key=r.date_key
        WHERE r.restaurant_id=%s AND r.review_id = ANY(%s)""",
        (str(restaurant_id), ids))
    approved = {str(review_id): (str(entity), str(stamp)[:10])
                for review_id, entity, stamp in cursor.fetchall()}
    kept = []
    for item in evidence:
        matched = approved.get(str(item["review_id"]))
        if matched == (str(restaurant_id), item["date"]) and \
                item["period"] in periods and item["date"].startswith(item["period"]):
            kept.append({**item, "ref": f"E{len(kept) + 1}"})
    return kept


def validate_cross_quote(raw, evidence):
    """Reject unsupported causation, unknown refs, and invented review wording."""
    quote = CrossQuote.model_validate(raw)
    by_ref = {item["ref"]: item for item in evidence}
    source = by_ref.get(quote.evidence_ref)
    normalized = " ".join(quote.review_quote.casefold().split())
    if not source or len(normalized) < 12 or CAUSAL.search(normalized):
        raise ValueError("Cross quote is missing, causal, or cites unknown evidence")
    if normalized not in " ".join(source["text"].casefold().split()):
        raise ValueError("Cross quote is not an exact review excerpt")
    return quote


def _verified_fallback_quote(evidence):
    """Cite an exact aligned excerpt when Qwen cannot select one safely."""
    ordered = sorted(evidence, key=lambda item: item.get("sentiment") != "negative")
    for item in ordered:
        raw = {"review_quote": item["text"].strip()[:160],
               "evidence_ref": item["ref"]}
        try:
            return validate_cross_quote(raw, evidence)
        except (ValueError, TypeError, KeyError):
            continue
    return None


def _synthesis(facts, aggregates, evidence, quote, drivers=(), missing_data=()):
    by_period = {item["period"]: item for item in aggregates}
    parts = []
    if facts:
        parts.append("FACT: " + "; ".join(
            f"{item['period']} Delivered {item['delivered_sales']:,.0f} VND"
            for item in facts) + ".")
    else:
        parts.append("FACT: Không có dữ liệu Sales cho kỳ được hỏi.")
    if len(facts) >= 2:
        first, last = facts[0], facts[-1]
        delta = last["delivered_sales"] - first["delivered_sales"]
        percent = (delta / first["delivered_sales"] * 100
                   if first["delivered_sales"] else None)
        parts.append(f"FACT: Chênh lệch Delivered {delta:+,.0f} VND" +
                     (f" ({percent:+.2f}%)." if percent is not None else
                      "; không tính phần trăm vì kỳ gốc bằng 0."))
        driver_map = {item["metric"]: item for item in drivers}
        if "delivered_count" in driver_map and "aov" in driver_map:
            count = driver_map["delivered_count"]
            aov = driver_map["aov"]
            parts.append("QUANTITATIVE DRIVER: Số đơn Delivered "
                         f"{count['baseline']:,.0f} → {count['current']:,.0f}; "
                         f"AOV {aov['baseline']:,.0f} → {aov['current']:,.0f} VND/đơn. "
                         "Đây là các thành phần đo được, không xác định nguyên nhân.")
        change = "giảm" if last["delivered_sales"] < first["delivered_sales"] else \
            "tăng" if last["delivered_sales"] > first["delivered_sales"] else "không đổi"
        first_review = by_period[first["period"]]
        last_review = by_period[last["period"]]
        if first_review["review_count"] and last_review["review_count"]:
            negative_first = first_review["negative_count"]
            negative_last = last_review["negative_count"]
            rate_first = first_review["sentiment_rate"]["negative"]
            rate_last = last_review["sentiment_rate"]["negative"]
            review_change = "tăng" if negative_last > negative_first else \
                "giảm" if negative_last < negative_first else "không đổi"
            rate_change = "tăng" if rate_last > rate_first else \
                "giảm" if rate_last < rate_first else "không đổi"
            parts.append(f"OBSERVED ASSOCIATION: Doanh thu {change}; số review tiêu cực "
                         f"{review_change} ({negative_first} → {negative_last}); tỷ lệ "
                         f"review tiêu cực {rate_change} ({rate_first:.1%} → "
                         f"{rate_last:.1%}) trong các kỳ tương ứng. "
                         "Sự trùng thời gian không chứng minh nhân quả.")
        else:
            parts.append("OBSERVED ASSOCIATION: Không đủ Review ở cả hai kỳ để "
                         "đánh giá sự thay đổi phản hồi khách hàng.")
    elif aggregates:
        parts.append("OBSERVED ASSOCIATION: Chưa đủ hai kỳ Sales để hoàn tất so sánh.")
    if aggregates:
        parts.append("REVIEW SIGNAL: " + "; ".join(
            f"{item['period']} có {item['review_count']} review "
            f"(tích cực {item['positive_count']}, trung lập {item['neutral_count']}, "
            f"tiêu cực {item['negative_count']}, tỷ lệ tiêu cực " +
            (f"{item['sentiment_rate']['negative']:.1%}" if
             item["sentiment_rate"].get("negative") is not None else
             "chưa đủ dữ liệu") +
            "), khía cạnh " +
            (", ".join(f"{name} {count}" for name, count in
                       list(item["aspect_frequencies"].items())[:3]) or "chưa quan sát")
            for item in aggregates) + ".")
    if quote:
        parts.append(f"REVIEW EVIDENCE: Review cùng kỳ ghi “{quote.review_quote}” "
                     f"[{quote.evidence_ref}].")
        parts.append("POSSIBLE EXPLANATION: Chưa xác lập được mối liên hệ giữa phản hồi "
                     "này và biến động doanh thu.")
    elif not any(item["review_count"] for item in aggregates):
        parts.append("POSSIBLE EXPLANATION: Không có review cùng kỳ cho nhà hàng này.")
    else:
        parts.append("POSSIBLE EXPLANATION: Có review cùng kỳ, nhưng chưa có trích dẫn "
                     "được xác minh để diễn giải thêm.")
    if missing_data:
        parts.append("LIMITATION: " + "; ".join(missing_data) + ".")
    return " ".join(parts)


def validate_cross_answer(answer, evidence):
    """Check the assembled answer for known citations and causal assertions."""
    refs = {item["ref"] for item in evidence}
    cited = set(re.findall(r"\[([A-Z]\d+)\]", answer))
    if not cited.issubset(refs):
        raise ValueError("Cross answer cites evidence outside the aligned result")
    safe_text = answer.replace("Sự trùng thời gian không chứng minh nhân quả.", "")
    safe_text = safe_text.replace(
        "Đây là các thành phần đo được, không xác định nguyên nhân.", "")
    safe_text = re.sub(r"Review cùng kỳ ghi “[^”]*”", "Review cùng kỳ ghi", safe_text)
    if CAUSAL.search(safe_text):
        raise ValueError("Cross answer contains an unsupported causal assertion")
    return answer


def analyze_cross(conn, restaurant_id, question, *, today=None,
                  retriever_factory=None, gateway_factory=None):
    """Execute a CrossPlan without fuzzy joins or model-generated business facts."""
    from src.sales.service import _record

    started = perf_counter()
    today = today or queries.vietnam_today()
    if not new_corpus_active():
        return {"status": "unsupported_corpus", "answer":
                "Cross Intelligence cần corpus Review có restaurant_id trực tiếp."}
    identity = queries.restaurant(conn, restaurant_id)
    if identity is None:
        raise ValueError("Unknown sales restaurant_id")
    if str(identity.get("review_restaurant_id")) != str(restaurant_id):
        return {"status": "unmatched_restaurant", "restaurant_id": str(restaurant_id),
                "answer": "Không có restaurant_id Review trùng chính xác; không thể ghép nguồn."}
    initial_scope = parse_time_scope(question, today=today)
    ranking = classify_cross_intent(question) in {
        "LOW_PERFORMANCE_REVIEW", "HIGH_PERFORMANCE_REVIEW"}
    if initial_scope.periods:
        defaults = ()
    elif ranking:
        defaults = tuple(str(row["period_start"])[:7] for row in
                         queries.monthly_trend(conn, restaurant_id, limit=36))
    else:
        defaults = _default_periods(conn, restaurant_id, today)
    plan = build_cross_plan(question, restaurant_id, today=today,
                            default_periods=defaults)
    if plan.mode != "cross_analysis":
        raise ValueError("Cross Intelligence requires Sales and Review in the question")
    ordered = sorted(set(plan.periods))
    facts, sales_sql = _sales_facts(conn, restaurant_id, ordered, question, today)
    candidate_periods = list(ordered)
    if ranking and facts:
        lowest = plan.intent == "LOW_PERFORMANCE_REVIEW"
        chosen = sorted(facts, key=lambda item: (
            item["delivered_sales"] if lowest else -item["delivered_sales"],
            item["period"]))[0]
        ordered = [chosen["period"]]
        facts = [chosen]
        plan = replace(plan, periods=tuple(ordered),
                       period_source="ranked_observed_month")
    facts = _group_sales_facts(facts, plan)
    drivers = calculate_sales_drivers(facts)
    monthly_aggregates = [monthly_review_aggregate(conn, restaurant_id, period)
                          for period in ordered]
    aggregates = _group_review_signals(monthly_aggregates, plan)
    evidence, retrieval = [], {"method": HYBRID_GENERAL.name,
                               "searched_periods": [], "filters": {}}
    if any(item["review_count"] for item in monthly_aggregates):
        from src.rag_v3.retriever import cached_retriever

        retriever = (retriever_factory or cached_retriever)()
        evidence_months = monthly_aggregates
        if plan.period_groups and any(len(group) > 1 for group in plan.period_groups):
            by_month = {item["period"]: item for item in monthly_aggregates}
            evidence_months = [item for group in plan.period_groups
                               for item in [by_month[month] for month in group
                                            if month in by_month and
                                            by_month[month]["review_count"]][-3:]]
        evidence, retrieval = _review_evidence(retriever, restaurant_id,
                                               evidence_months, question)
        evidence = _verify_evidence_in_warehouse(conn, restaurant_id, ordered, evidence)
    missing_data = []
    if sales_sql["missing_periods"]:
        missing_data.append("Thiếu Sales: " + ", ".join(sales_sql["missing_periods"]))
    absent_reviews = [item["period"] for item in monthly_aggregates
                      if not item["review_count"]]
    if absent_reviews:
        missing_data.append("Thiếu Review: " + ", ".join(absent_reviews))
    if any(item["review_count"] for item in aggregates) and not evidence:
        missing_data.append("Không có trích dẫn Review đúng nhà hàng và đúng kỳ")
    current_month = today.strftime("%Y-%m")
    if current_month in ordered:
        missing_data.append("Tháng hiện tại chưa hoàn tất")
    quote, generation = None, "deterministic_evidence_fallback"
    guard = "PASS"
    if evidence and facts:
        from src.rag_v3.cli import selected_v3_gateway

        prompt = PROMPT.read_text(encoding="utf-8")
        payload = {"sales_facts": facts, "sales_drivers": drivers,
                   "review_signals": aggregates, "missing_data": missing_data,
                   "review_evidence": [{key: item[key] for key in
                                        ("ref", "review_id", "restaurant_id", "period",
                                         "date", "text", "sentiment", "aspects")}
                                       for item in evidence]}
        try:
            with (gateway_factory or selected_v3_gateway)() as gateway:
                raw, _ = gateway.generate(system=prompt,
                                          user=json.dumps(payload, ensure_ascii=False),
                                          response_schema=CrossQuote.model_json_schema(),
                                          prompt_version="cross_synthesis_v1",
                                          max_new_tokens=96,
                                          component="cross_intelligence_generation")
            quote = validate_cross_quote(raw, evidence)
            generation = "qwen_verified_extract"
        except (ValueError, TypeError, KeyError, OSError, RuntimeError, RequestException):
            guard = "REJECTED_QWEN_FALLBACK"
            quote = _verified_fallback_quote(evidence)
            if quote:
                generation = "deterministic_verified_quote"
    answer = _synthesis(facts, aggregates, evidence, quote, drivers, missing_data)
    try:
        validate_cross_answer(answer, evidence)
    except ValueError:
        guard = "REJECTED_FINAL_ANSWER"
        quote = None
        answer = validate_cross_answer(
            _synthesis(facts, aggregates, [], None, drivers, missing_data), [])
    status = ("no_sales_data" if not facts else
              "insufficient_sales_comparison" if plan.operation == "comparison"
              and len(facts) < 2 else
              "no_review_data" if not any(item["review_count"] for item in aggregates) else
              "insufficient_review_comparison" if plan.operation == "comparison"
              and any(not item["review_count"] for item in aggregates) else
              "insufficient_review_evidence" if not evidence else
              "limited_synthesis" if quote is None else "grounded")
    elapsed_ms = (perf_counter() - started) * 1000
    _record("cross_analysis", started, status, generation_mode=generation,
            evidence_count=len(evidence))
    return {"status": status, "restaurant_id": str(restaurant_id),
            "restaurant_name": identity["restaurant_name"], "plan": plan.as_dict(),
            "sales_facts": facts, "sales_drivers": drivers,
            "review_aggregates": aggregates, "review_signals": aggregates,
            "missing_data": missing_data,
            "review_evidence": evidence, "answer": answer,
            "technical": {"restaurant_id": str(restaurant_id),
                          "requested_periods": list(plan.periods),
                          "candidate_periods": candidate_periods,
                          "sales_query_mode": sales_sql["mode"],
                          "sales_sql": sales_sql["sql"],
                          "sales_semantic_verification": sales_sql["semantic_verification"],
                          "missing_sales_periods": sales_sql["missing_periods"],
                          "review_filters": retrieval["filters"],
                          "evidence_count": len(evidence),
                          "retrieval_mode": retrieval["method"],
                          "model": "Qwen/Qwen2.5-3B-Instruct-GGUF",
                          "prompt_version": "cross_synthesis_v1",
                          "generation_mode": generation,
                          "grounding_status": "verified" if quote else "limited",
                          "causation_guard_status": guard,
                          "latency_ms": elapsed_ms}}
