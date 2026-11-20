"""Grounded SQL answers and date-aligned review cross-analysis."""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from time import perf_counter

from src.monitoring.metrics import observe_cross_analysis, observe_rag, observe_sales_sql
from src.rag.monitoring import record
from src.sales import queries
from src.sales.analysis import answer_advanced
from src.sales.comparisons import answer_comparison
from src.sales.planner import (
    build_sales_plan,
    build_sql_analytical_plan,
    sales_plan_from_canonical,
    sql_plan_from_canonical,
)
from src.sales.response import SalesAnalysisResult, render
from src.sales.response import money as display_money
from src.sales.response import percentage as display_percentage
from src.sales.router import (
    month_in_question,
    route_question,
    wants_current_month,
    wants_current_week,
)
from src.sales.semantic_fallback import answer_from_plan
from src.sales.semantic_plan import build_canonical_plan


def _money(value):
    return f"{value:,.0f} VND" if value is not None else "không có dữ liệu"


def _percent(value):
    return f"{value * 100:+.2f}%" if value is not None else "không đủ dữ liệu so sánh"


def _month_for_question(question, today):
    explicit = month_in_question(question)
    if explicit:
        return explicit
    if wants_current_month(question):
        return today.strftime("%Y-%m")
    return None


def _record(route, started, status, *, input_tokens=0, output_tokens=0,
            generation_mode="none", evidence_count=0):
    elapsed_ms = (perf_counter() - started) * 1000
    record(route, "PostgreSQL + RAG V3" if route == "cross_analysis" else "PostgreSQL",
           "003", "sales_sql_v1", elapsed_ms, status,
           input_tokens=input_tokens, output_tokens=output_tokens,
           rag_version="RAG_V3" if route == "cross_analysis" else None,
           query_route=route, generation_mode=generation_mode,
           evidence_count=evidence_count)
    if route == "sales_sql":
        observe_sales_sql(elapsed_ms / 1000, status)
    else:
        observe_cross_analysis(status)


def _deterministic_sales_answer(conn, restaurant_id, question, *, today=None,
                                naturalizer=None, canonical=None):
    """Answer numeric questions from predefined SQL only."""
    started = perf_counter()
    today = today or queries.vietnam_today()
    try:
        if (canonical is not None and callable(getattr(conn, "execute", None)) and
                canonical.time_scope.periods and
                canonical.time_scope.kind != "single_month" and
                canonical.operation != "comparison" and
                not canonical.filters.get("analytical_step")):
            result = answer_from_plan(conn, restaurant_id, {}, canonical, today=today)
            _record("sales_sql", started, result["status"])
            return result
        identity = queries.restaurant(conn, restaurant_id)
        if identity is None:
            raise ValueError("Unknown sales restaurant_id")
        plan = (sales_plan_from_canonical(canonical) if canonical is not None else
                build_sales_plan(question, today=today))
        if plan is None:
            result = answer_from_plan(conn, restaurant_id, identity, canonical, today=today)
            _record("sales_sql", started, result["status"])
            return result
        if plan.kind == "COMPARE_PERIODS":
            result = answer_comparison(conn, restaurant_id, identity, plan, today=today,
                                       question=question, naturalizer=naturalizer)
            _record("sales_sql", started, result["status"])
            return result
        if plan.kind != "SINGLE_PERIOD_METRIC":
            result = answer_advanced(conn, restaurant_id, identity, plan, today=today)
            _record("sales_sql", started, result["status"])
            return result
    except ValueError as error:
        _record("sales_sql", started, "invalid_period")
        return {"route": "SALES_SQL", "source": "SQL Analytics",
                "answer": str(error), "restaurant_id": str(restaurant_id),
                "sql_facts": None, "review_evidence": [], "status": "invalid_period"}
    lowered = question.casefold()
    try:
        month = _month_for_question(question, today)
    except ValueError as error:
        _record("sales_sql", started, "invalid_period")
        return {"route": "SALES_SQL", "source": "SQL Analytics",
                "answer": str(error), "restaurant_id": str(restaurant_id),
                "sql_facts": None, "review_evidence": [], "status": "invalid_period"}
    source = "SQL Analytics"
    simple_analysis = None
    simple_trace = None
    if "cao nhất" in lowered or "highest" in lowered:
        facts = queries.highest_sales_month(conn, restaurant_id, today=today)
        answer = (f"Tháng doanh thu Delivered cao nhất của {identity['restaurant_name']} "
                  f"là {facts['period_start']:%m/%Y}: {display_money(facts['delivered_sales'])}.") if facts else \
            "Chưa có tháng hoàn chỉnh để xếp hạng doanh thu."
    elif "tuần" in lowered or "tuan" in lowered or "week" in lowered:
        week = today.fromordinal(today.toordinal() - today.weekday()) if \
            wants_current_week(question) else None
        facts = queries.weekly_sales(conn, restaurant_id, week, today=today)
        answer = (f"Doanh thu Delivered tuần bắt đầu {facts['period_start']}: "
                  f"{display_money(facts['delivered_sales'])}; {facts['order_count']} đơn, "
                  f"AOV {display_money(facts['aov'])}.") if facts else "Không có đơn trong tuần được hỏi."
    elif any(term in lowered for term in ("cancelled", "refunded", "delivered", "đơn hủy",
                                         "tỷ lệ", "aov", "order status")):
        facts = queries.sales_summary(conn, restaurant_id)
        answer = (f"{identity['restaurant_name']}: {facts['order_count']} đơn đã quan sát; "
                  f"Delivered {facts['delivered_count']}, Cancelled {facts['cancelled_count']}, "
                  f"Refunded {facts['refunded_count']}; tỷ lệ hủy "
                  f"{display_percentage(facts['cancellation_rate'] * 100)}, tỷ lệ hoàn "
                  f"{display_percentage(facts['refund_rate'] * 100)}, AOV Delivered "
                  f"{display_money(facts['aov'])}.") if facts else "Chưa có đơn đã quan sát."
    else:
        facts = queries.monthly_comparison(conn, restaurant_id, month, today=today)
        if facts:
            basis = (" So sánh với cùng số ngày của tháng trước; tháng này chưa hoàn tất."
                     if facts["comparison_basis"] == "same_day_of_month_partial" else "")
            period = facts["period_start"].strftime("%Y-%m")
            simple_analysis = SalesAnalysisResult(
                intent="SINGLE_PERIOD_METRIC", response_mode="FACTUAL",
                metric="delivered_sales", periods=[period],
                values=[Decimal(str(facts["delivered_sales"]))],
                details={"order_count": facts["order_count"], "aov": facts["aov"],
                         "comparison_growth": facts["comparison_growth"]},
            )
            answer = render(simple_analysis, identity["restaurant_name"]) + basis
            simple_trace = {"intent": "SINGLE_PERIOD_METRIC", "response_mode": "FACTUAL",
                            "metric": "delivered_sales", "periods": [period],
                            "aggregation": None, "period_selection": "EXPLICIT_SET" if month else None,
                            "sql_functions": ["monthly_comparison"],
                            "calculations": ["comparison_growth"],
                            "sql_mode": "predefined_parameterized_monthly_sales",
                            "qwen_used": False, "grounding_status": "sql_verified",
                            "fact_validation_status": "not_needed"}
        else:
            answer = (f"Kỳ dữ liệu: {month[5:7]}/{month[:4]}. " if month else "") + \
                "Không có dữ liệu đơn hàng trong tháng được hỏi."
    status = "ok" if facts else "no_data"
    _record("sales_sql", started, status)
    return {"route": "SALES_SQL", "source": source, "answer": answer,
            "restaurant_id": str(restaurant_id), "sql_facts": queries.jsonable(facts),
            "review_evidence": [], "status": status,
            "query_plan": simple_trace,
            "analysis": simple_analysis.as_dict() if simple_analysis else None}


def _deterministic_analytical_answer(conn, restaurant_id, question, *, today=None,
                                     plan=None):
    """Cover new complex shapes with the existing parameterized monthly mart query."""
    from src.sales.text_to_sql import _render_result

    plan = plan or build_sql_analytical_plan(question, today=today)
    year_groups = (plan.operation == "compare_periods" and
                   plan.grain == "year" and len(plan.periods) > 1)
    month_ranking = (plan.operation == "ranking" and plan.group_by == ("month",)
                     and re.search(r"\btop\s+\d+", question.casefold()))
    long_trend = plan.operation == "trend" and len(plan.periods) > 12
    if not (year_groups or month_ranking or long_trend):
        return None
    today = today or queries.vietnam_today()
    current_month = today.replace(day=1)
    months = []
    for interval in plan.periods:
        current = datetime.fromisoformat(interval["start"]).date()
        end = datetime.fromisoformat(interval["end"]).date()
        while current < end:
            months.append(current.strftime("%Y-%m"))
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    available = {fact["period_start"].strftime("%Y-%m"): fact for fact in
                 queries.monthly_sales_range(conn, restaurant_id,
                                             min(item["start"] for item in plan.periods),
                                             max(item["end"] for item in plan.periods))}
    observed, unavailable = [], []
    for month in months:
        if datetime.fromisoformat(month + "-01").date() > current_month:
            unavailable.append(month)
            continue
        fact = available.get(month)
        if fact is None:
            unavailable.append(month)
        else:
            observed.append(fact)
    if not observed:
        return {"route": "SALES_SQL", "source": "SQL Analytics",
                "answer": "Không đủ dữ liệu Sales cho toàn bộ kỳ đã yêu cầu: " +
                          ", ".join(unavailable) + ".",
                "restaurant_id": str(restaurant_id), "sql_facts": [],
                "display_rows": [], "review_evidence": [], "status": "no_data",
                "query_plan": {"intent": plan.operation, "metric": plan.metric,
                               "periods": months, "missing_periods": unavailable,
                               "sql_mode": "predefined_parameterized_monthly_sales"}}
    if year_groups:
        rows = []
        for interval in plan.periods:
            year = interval["start"][:4]
            facts = [fact for fact in observed if fact["period_start"].year == int(year)]
            if not facts:
                unavailable.append(year)
                continue
            sales = sum(Decimal(str(fact["delivered_sales"])) for fact in facts)
            orders = sum(int(fact["order_count"]) for fact in facts)
            cancelled = sum(int(fact["cancelled_count"]) for fact in facts)
            delivered = sum(int(fact["delivered_count"]) for fact in facts)
            row = {"year": int(year), "delivered_sales": sales}
            if "order_count" in plan.metrics:
                row["order_count"] = orders
            if "cancellation_rate" in plan.metrics:
                row["cancellation_rate"] = Decimal(cancelled) / orders if orders else None
            if "aov" in plan.metrics:
                row["aov"] = sales / delivered if delivered else None
            rows.append(row)
        rows.sort(key=lambda item: item["year"])
        if len(rows) != len(plan.periods):
            unavailable.extend(interval["start"][:4] for interval in plan.periods
                               if all(row["year"] != int(interval["start"][:4])
                                      for row in rows))
            return {"route": "SALES_SQL", "source": "SQL Analytics",
                    "answer": "Không đủ dữ liệu để so sánh tất cả các năm đã yêu cầu.",
                    "restaurant_id": str(restaurant_id), "sql_facts": [],
                    "display_rows": [], "review_evidence": [], "status": "no_data",
                    "query_plan": {"intent": plan.operation, "metric": plan.metric,
                                   "periods": months, "missing_periods": unavailable,
                                   "sql_mode": "predefined_parameterized_monthly_sales"}}
        answer_type = "comparison"
    else:
        rows = [{"period_start": fact["period_start"],
                 "delivered_sales": fact["delivered_sales"]} for fact in observed]
        if month_ranking:
            rows.sort(key=lambda item: item["delivered_sales"],
                      reverse=plan.sort == "descending")
            rows = rows[:plan.limit]
        else:
            rows.sort(key=lambda item: item["period_start"])
        answer_type = "ranking" if month_ranking else "trend"
    answer = _render_result(queries.jsonable(rows), answer_type, question)
    if unavailable:
        answer += (" Kết quả không bao gồm các tháng chưa có hàng dữ liệu: " +
                   ", ".join(unavailable) + ".")
    if any(fact["period_start"] == current_month for fact in observed):
        answer += (f" Tháng {current_month:%Y-%m} đang diễn ra; số liệu quan sát "
                   "có thể chưa đủ tháng.")
    return {"route": "SALES_SQL", "source": "SQL Analytics", "answer": answer,
            "restaurant_id": str(restaurant_id), "sql_facts": queries.jsonable(rows),
            "display_rows": queries.jsonable(rows), "review_evidence": [],
            "status": "ok", "query_plan": {
                "intent": plan.operation, "metric": plan.metric,
                "metrics": list(plan.metrics),
                "periods": ([interval["start"][:4] for interval in plan.periods]
                            if year_groups else months),
                "period_ranges": list(plan.periods), "group_by": list(plan.group_by),
                "aggregation": None, "sort": plan.sort, "limit": plan.limit,
                "missing_periods": unavailable,
                "sql_mode": "predefined_parameterized_monthly_sales"}}


def sales_answer(conn, restaurant_id, question, *, today=None, naturalizer=None):
    """Try validated Qwen SQL, then preserve the original deterministic path."""
    from src.sales.text_to_sql import (
        _scope_is_global,
        answer_with_text_to_sql,
        enabled,
        unsafe_request,
    )

    if unsafe_request(question):
        return {"route": "SALES_SQL", "source": "SQL Analytics",
                "answer": "Không thể thực hiện yêu cầu thay đổi dữ liệu hoặc tiết lộ thông tin bảo mật.",
                "restaurant_id": str(restaurant_id), "sql_facts": None,
                "review_evidence": [], "status": "refused_unsafe_request",
                "execution_mode": "DETERMINISTIC_FALLBACK",
                "sql_details": {"sql": None, "tables_used": [],
                                "validation_status": "Request rejected before execution",
                                "fallback_reason": "unsafe_request"}}

    started = perf_counter()
    fallback_reason = None
    generation_attempts = []
    try:
        canonical = build_canonical_plan(question, today=today or queries.vietnam_today())
    except ValueError as error:
        return {"route": "SALES_SQL", "source": "SQL Analytics",
                "answer": str(error), "restaurant_id": str(restaurant_id),
                "sql_facts": None, "review_evidence": [], "status": "invalid_period"}
    if enabled() and conn is not None and not canonical.filters.get("analytical_step"):
        try:
            return answer_with_text_to_sql(conn, restaurant_id, question,
                                           audit_sink=generation_attempts,
                                           canonical_plan=canonical)
        except Exception as error:
            fallback_reason = (getattr(error, "category", None) or
                               "qwen_unavailable_or_invalid")
    elif canonical.filters.get("analytical_step"):
        fallback_reason = "multi_step_predefined"
    if _scope_is_global(question):
        lowered = question.casefold()
        if any(term in lowered for term in ("doanh thu", "revenue", "tỷ lệ hủy",
                                           "tỉ lệ hủy", "aov")):
            metric = ("cancellation_rate" if "hủy" in lowered else
                      "aov" if "aov" in lowered else "delivered_sales")
            try:
                month = month_in_question(question)
                top = re.search(r"\btop\s+(\d{1,3})\b", lowered)
                limit = min(int(top.group(1)), 100) if top else 1
                rows = queries.rank_sales_restaurants(
                    conn, metric=metric, month=month,
                    highest=not any(term in lowered for term in ("thấp nhất", "ít nhất")),
                    limit=limit)
                label = {"delivered_sales": "doanh thu Delivered",
                         "cancellation_rate": "tỷ lệ hủy", "aov": "AOV"}[metric]
                def display(value):
                    return (f"{float(value) * 100:.2f}%" if metric == "cancellation_rate"
                            else _money(value))

                answer = (f"Xếp hạng {label}" + (f" tháng {month}" if month else "") +
                          ": " + "; ".join(f"{row['restaurant_name']} "
                          f"({display(row['metric_value'])})" for row in rows) + ".") if rows else \
                    "Không có dữ liệu Sales cho kỳ xếp hạng này."
                _record("sales_sql", started, "ok" if rows else "no_data")
                return {"route": "SALES_SQL", "source": "SQL Analytics",
                        "answer": answer, "restaurant_id": str(restaurant_id),
                        "sql_facts": queries.jsonable(rows), "display_rows": queries.jsonable(rows),
                        "review_evidence": [], "status": "ok" if rows else "no_data",
                        "execution_mode": "DETERMINISTIC_FALLBACK",
                        "sql_details": {"sql": None, "tables_used": [],
                                        "validation_status": "Qwen SQL not executed",
                                        "generation_attempt_count": len(generation_attempts),
                                        "semantic_verification": "Qwen SQL rejected; predefined SQL used",
                                        "fallback_reason": fallback_reason or "local_mode"}}
            except ValueError:
                pass
        return {"route": "SALES_SQL", "source": "SQL Analytics",
                "answer": "Không thể xác minh xếp hạng nhà hàng từ truy vấn hiện tại. "
                          "Vui lòng thử lại khi Text-to-SQL khả dụng.",
                "restaurant_id": str(restaurant_id), "sql_facts": None,
                "review_evidence": [], "status": "unsupported_sql",
                "execution_mode": "DETERMINISTIC_FALLBACK",
                "sql_details": {"sql": None, "tables_used": [],
                                "validation_status": "Qwen SQL not executed",
                                "fallback_reason": fallback_reason or "ranking_requires_validated_sql"}}
    result = None
    if not callable(getattr(conn, "execute", None)) or \
            canonical.filters.get("analytical_step") or \
            canonical.operation == "comparison":
        try:
            result = _deterministic_analytical_answer(
                conn, restaurant_id, question, today=today,
                plan=sql_plan_from_canonical(canonical))
        except ValueError:
            result = None
    if result is None:
        result = _deterministic_sales_answer(conn, restaurant_id, question,
                                             today=today, naturalizer=naturalizer,
                                             canonical=canonical)
    trace = result.get("query_plan")
    if trace is None:
        trace = result["query_plan"] = {}
    if isinstance(trace, dict):
        trace.setdefault("canonical_plan", canonical.as_dict())
        trace.setdefault("output_shape", canonical.output_shape)
        missing = trace.setdefault("missing_periods", [])
        if result.get("status") == "no_data" and not missing:
            missing = trace["missing_periods"] = list(canonical.time_scope.periods)
        trace.setdefault("observed_periods", [period for period in
                                              canonical.time_scope.periods if period not in missing])
    if enabled():
        result["execution_mode"] = "DETERMINISTIC_FALLBACK"
        result["sql_details"] = {
            "sql": None, "tables_used": [], "validation_status": "Qwen SQL not executed",
            "generation_attempt_count": len(generation_attempts),
            "semantic_verification": "Qwen SQL rejected; predefined SQL used",
            "fallback_reason": fallback_reason or "local_mode",
        }
    return result


def _aligned_review_count(conn, restaurant_key, start, end):
    from src.foody.review_runtime import new_corpus_active

    if new_corpus_active():
        return conn.execute("""SELECT COUNT(*) FROM fact_review_v2 r
            JOIN dim_date d ON d.date_key=r.date_key
            WHERE r.restaurant_id=%s AND d.calendar_date BETWEEN %s AND %s""",
            (str(restaurant_key), start, end)).fetchone()[0]
    return conn.execute("""SELECT COUNT(*) FROM fact_review r
        JOIN dim_date d ON d.date_key=r.date_key
        WHERE r.restaurant_key=%s AND d.calendar_date BETWEEN %s AND %s""",
        (restaurant_key, start, end)).fetchone()[0]


def _review_trend(conn, restaurant_key, start, end):
    return conn.execute("""SELECT COUNT(*), COUNT(*) FILTER
        (WHERE r.predicted_sentiment='negative') FROM fact_review r
        JOIN dim_date d ON d.date_key=r.date_key
        WHERE r.restaurant_key=%s AND d.calendar_date BETWEEN %s AND %s""",
        (restaurant_key, start, end)).fetchone()


def _cross_sql_details(conn, restaurant_id, metric):
    """Accept Qwen Sales evidence only if it matches the existing verified mart."""
    from src.sales.text_to_sql import answer_with_text_to_sql, enabled

    if not enabled():
        return None
    period = metric["period_start"].strftime("%m/%Y")
    try:
        result = answer_with_text_to_sql(
            conn, restaurant_id,
            f"Doanh thu Delivered, số đơn và kỳ tháng {period} của nhà hàng này là gì?")
        rows = result.get("sql_facts") or []
        if len(rows) != 1:
            return None
        row = rows[0]
        if (str(row.get("period_start"))[:10] != str(metric["period_start"]) or
                Decimal(str(row.get("delivered_sales"))) !=
                Decimal(str(metric["delivered_sales"])) or
                int(row.get("order_count")) != int(metric["order_count"])):
            return None
        return result["sql_details"]
    except (ValueError, TypeError, KeyError, OverflowError):
        return None
    except Exception:
        return None


def cross_answer(conn, restaurant_id, question, *, today=None,
                 retriever_factory=None, gateway_factory=None):
    """Combine SQL facts with separately grounded, same-period review evidence."""
    started = perf_counter()
    today = today or queries.vietnam_today()
    identity = queries.restaurant(conn, restaurant_id)
    from src.foody.review_runtime import new_corpus_active

    direct_id = new_corpus_active()
    review_identity = (identity.get("review_restaurant_id") if direct_id else
                       identity.get("restaurant_key")) if identity else None
    if identity is None:
        raise ValueError("Unknown sales restaurant_id")
    if review_identity is None:
        answer = ("Không có ánh xạ ID nhà hàng được xác minh giữa đơn hàng và đánh giá; "
                  "không thể tổng hợp hai nguồn cho nhà hàng này.")
        _record("cross_analysis", started, "unmatched_restaurant")
        return {"route": "CROSS_ANALYSIS", "source": "Hybrid SQL + RAG",
                "answer": answer, "sql_facts": None, "review_evidence": [],
                "restaurant_id": str(restaurant_id), "status": "unmatched_restaurant"}
    try:
        month = _month_for_question(question, today)
    except ValueError as error:
        _record("cross_analysis", started, "invalid_period")
        return {"route": "CROSS_ANALYSIS", "source": "Hybrid SQL + RAG",
                "answer": str(error), "sql_facts": None, "review_evidence": [],
                "restaurant_id": str(restaurant_id), "status": "invalid_period"}
    lowered = question.casefold()
    if "giảm mạnh nhất" in lowered or "largest decline" in lowered:
        metric = queries.lowest_growth_month(conn, restaurant_id, today=today)
        month = metric["period_start"].strftime("%Y-%m") if metric else None
    else:
        metric = queries.monthly_comparison(conn, restaurant_id, month, today=today)
    if metric is None:
        _record("cross_analysis", started, "no_sales_data")
        return {"route": "CROSS_ANALYSIS", "source": "Hybrid SQL + RAG",
                "answer": "Không có dữ liệu doanh thu cho kỳ được hỏi.",
                "sql_facts": None, "review_evidence": [],
                "restaurant_id": str(restaurant_id), "status": "no_sales_data"}
    cross_sql_details = _cross_sql_details(conn, restaurant_id, metric)
    start = metric["period_start"]
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = min(next_month - timedelta(days=1), today)
    growth = metric.get("comparison_growth", metric.get("mom_growth"))
    sales_text = (f"Theo SQL, doanh thu Delivered {start:%Y-%m} là "
                  f"{_money(metric['delivered_sales'])}, {metric['order_count']} đơn; "
                  f"thay đổi {_percent(growth)} so với kỳ trước.")
    count = _aligned_review_count(conn, review_identity, start, end)
    if count == 0:
        answer = (sales_text + " Không có đánh giá cùng kỳ cho đúng nhà hàng; "
                  "không đủ bằng chứng để liên hệ biến động doanh thu với phản hồi khách hàng.")
        _record("cross_analysis", started, "no_aligned_reviews")
        return {"route": "CROSS_ANALYSIS", "source": "Hybrid SQL + RAG",
                "answer": answer, "sql_facts": queries.jsonable(metric),
                "review_evidence": [], "restaurant_id": str(restaurant_id),
                "aligned_review_count": 0, "status": "no_aligned_reviews"}

    from src.rag.schemas import RetrievalRequest
    from src.rag_v3.cli import selected_v3_gateway
    from src.rag_v3.retriever import cached_retriever
    from src.rag_v3.service import answer_question_v3

    retriever_factory = retriever_factory or cached_retriever
    gateway_factory = gateway_factory or selected_v3_gateway
    request = RetrievalRequest(
        query="Khách phàn nàn gì về món ăn, phục vụ hoặc giá?",
        **({"restaurant_id": str(review_identity)} if direct_id else
           {"restaurant_key": review_identity}),
        date_from=datetime.combine(start, datetime.min.time()),
        date_to=datetime.combine(end, datetime.min.time()), top_k=5,
    )
    with gateway_factory() as gateway:
        review_answer, _, telemetry, _, packet = answer_question_v3(
            retriever_factory(), gateway, request,
        )
    observe_rag(telemetry)
    by_id = {item["review_id"]: item for item in packet.evidence}
    evidence = [{**item.model_dump(), **{
        key: by_id[item.review_id].get(key)
        for key in ("ref", "date", "rating", "sentiment", "aspects", "text", "source")
    }} for item in review_answer.evidence if item.review_id in by_id]
    if evidence:
        answer = (sales_text + " Phản hồi cùng kỳ: " + review_answer.answer
                  + " Đây là sự trùng thời gian, không chứng minh quan hệ nhân quả.")
        status = "grounded"
    else:
        answer = (sales_text + " Có đánh giá cùng kỳ nhưng RAG V3 không xác nhận "
                  "được bằng chứng phù hợp; không thể quy nguyên nhân cho phản hồi.")
        status = "insufficient_review_evidence"
    _record("cross_analysis", started, status,
            input_tokens=telemetry.get("input_tokens") or 0,
            output_tokens=telemetry.get("output_tokens") or 0,
            generation_mode=telemetry.get("generation_mode") or "none",
            evidence_count=len(evidence))
    return {"route": "CROSS_ANALYSIS", "source": "Hybrid SQL + RAG",
            "answer": answer, "sql_facts": queries.jsonable(metric),
            "review_evidence": evidence, "restaurant_id": str(restaurant_id),
            "aligned_review_count": count, "status": status,
            "review_generation_mode": telemetry.get("generation_mode"),
            "sales_execution_mode": ("QWEN_TEXT_TO_SQL" if cross_sql_details else
                                     "DETERMINISTIC_FALLBACK"),
            "sales_sql_details": cross_sql_details}


def answer_question(conn, restaurant_id, question, **kwargs):
    route = route_question(question)
    if route == "SALES_SQL":
        return sales_answer(conn, restaurant_id, question, today=kwargs.get("today"),
                            naturalizer=kwargs.get("naturalizer"))
    if route == "CROSS_ANALYSIS":
        return cross_answer(conn, restaurant_id, question, **kwargs)
    raise ValueError("Review-only questions must use the unchanged RAG V3 path")
