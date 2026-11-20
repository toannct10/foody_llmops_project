"""Dedicated SQL-backed Sales Analytics presentation."""

from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st

from src.sales.metric_ontology import UNITS
from src.sales.response import money as vietnamese_money
from src.sales.response import percentage as vietnamese_percentage
from src.ui.components import (
    answer_card,
    badge_row,
    empty_state,
    evidence_card,
    header,
    kpi_card,
    money,
    percent,
)
from src.ui.progress import SALES_STAGES, AIProgress


@st.cache_data(ttl=300, show_spinner=False)
def sales_restaurants():
    from src.sales import queries
    from src.warehouse.loader import connection

    with connection() as conn:
        return queries.list_restaurants(conn)


@st.cache_data(ttl=120, show_spinner=False)
def sales_snapshot(restaurant_id):
    from src.sales import queries
    from src.warehouse.loader import connection

    with connection() as conn:
        return {
            "monthly": queries.monthly_trend(conn, restaurant_id, limit=36),
            "weekly": queries.weekly_trend(conn, restaurant_id, limit=52),
            "statuses": queries.order_status_summary(conn, restaurant_id),
            "summary": queries.sales_summary(conn, restaurant_id),
        }


@st.cache_data(ttl=120, show_spinner=False)
def month_snapshot(restaurant_id, month):
    from src.sales import queries
    from src.warehouse.loader import connection

    with connection() as conn:
        return queries.monthly_comparison(conn, restaurant_id, month)


@st.cache_data(ttl=300, show_spinner=False)
def review_snippets(review_ids, restaurant_key):
    """Resolve already accepted evidence IDs to local review text for display only."""
    if not review_ids or not restaurant_key:
        return {}
    from src.foody.review_runtime import ENRICHED, new_corpus_active

    if new_corpus_active():
        frame = pd.read_parquet(ENRICHED,
                                columns=["review_id", "restaurant_id", "comment", "rating",
                                         "review_time"])
        rows = frame.loc[frame.review_id.isin(review_ids) &
                         frame.restaurant_id.astype(str).eq(str(restaurant_key))]
        return {row.review_id: {"text": row.comment, "rating": row.rating,
                                "date": row.review_time} for row in rows.itertuples()}
    frame = pd.read_parquet("data/foody/enriched/reviews.parquet",
                            columns=["review_id", "restaurant_key", "text", "raw_rating",
                                     "review_timestamp"])
    return select_review_snippets(frame, review_ids, restaurant_key)


def select_review_snippets(frame, review_ids, restaurant_key):
    """Never display a review from a different restaurant for a cross result."""
    rows = frame.loc[frame.review_id.isin(review_ids) &
                     frame.restaurant_key.eq(restaurant_key)].drop_duplicates("review_id")
    return {row.review_id: {"text": row.text, "rating": row.raw_rating,
                            "date": row.review_timestamp} for row in rows.itertuples()}


def cross_evidence_metadata(item):
    """Show only metadata carried by the cited review, including missing values."""
    rating = item.get("rating")
    rating_label = f"{rating}/10" if rating is not None and pd.notna(rating) else "unavailable"
    date = item.get("date")
    date_label = str(date)[:10] if date is not None and pd.notna(date) else "unavailable"
    aspects = item.get("aspects") or []
    return (f"Date: {date_label} · Rating: {rating_label} · "
            f"Sentiment: {(item.get('sentiment') or 'unavailable').title()} · "
            f"Aspects: {', '.join(aspects) if aspects else 'unavailable'} · "
            f"Source: {item.get('source') or 'unavailable'}")


def sales_result_table(result):
    """Present verified monthly facts without changing their values."""
    rows = result.get("display_rows") or []
    metric = (result.get("analysis") or {}).get("metric", "delivered_sales")
    title = {"delivered_sales": "Revenue", "aov": "AOV",
             "cancellation_rate": "Cancellation rate"}.get(metric, "Value")
    formatter = vietnamese_percentage if metric == "cancellation_rate" else vietnamese_money
    return pd.DataFrame([{"Period": f"{row['period'][5:7]}/{row['period'][:4]}",
                          title: formatter(row["value"] * 100 if metric ==
                                           "cancellation_rate" else row["value"])}
                         for row in rows])


@dataclass(frozen=True)
class SalesRenderModel:
    """One final response snapshot for every visible Sales section."""

    answer: str
    status: str
    mode: str
    answer_badge: str
    sql: str | None
    sql_note: str | None
    sql_badges: tuple[tuple[str, str], ...]
    kpis: tuple[tuple[str, str], ...]
    preview_title: str
    preview_rows: tuple[dict, ...]
    preview_kind: str
    chart_points: tuple[tuple[str, float], ...]
    technical: dict


def _fact_count(facts):
    if isinstance(facts, (list, dict)):
        return len(facts)
    return int(facts is not None)


def _period_label(periods):
    if not periods:
        return "—"
    if len(periods) == 1:
        return str(periods[0])
    return f"{periods[0]} – {periods[-1]}"


def normalize_sales_result(result):
    """Discard superseded SQL artifacts and derive one consistent display payload."""
    status = result.get("status") or "ok"
    mode = result.get("execution_mode") or "DETERMINISTIC_FALLBACK"
    details = result.get("sql_details") or {}
    analysis = result.get("analysis") or {}
    plan = result.get("query_plan") or {}
    output_shape = plan.get("output_shape")
    sql, _, badges, note = sql_presentation(result)
    accepted = status in {"ok", "no_data"}
    badge = ("Blocked" if status == "refused_unsafe_request" else
             "Validation failed" if status in {"unsupported_sql", "invalid_period"} else
             "No matching data" if status == "no_data" else
             "Deterministic fallback" if mode == "DETERMINISTIC_FALLBACK" else
             "Verified by SQL")
    source_rows = result.get("display_rows") or []
    intent = analysis.get("intent") or plan.get("intent")
    metric = analysis.get("metric") or plan.get("metric")
    unit = plan.get("result_unit") or UNITS.get(metric)
    def format_value(value):
        if unit == "%":
            return vietnamese_percentage(float(value) * 100)
        if unit == "orders":
            return f"{float(value):,.0f} orders"
        if unit == "VND/order":
            return vietnamese_money(value) + "/order"
        return vietnamese_money(value)

    aggregate = (analysis.get("details") or {}).get("aggregate_value")
    if aggregate is None and mode == "QWEN_TEXT_TO_SQL" and \
            (output_shape == "scalar" or intent in
             {"YEAR_AGGREGATE", "RANGE_AGGREGATE"}) and len(source_rows) == 1:
        aggregate = source_rows[0].get(metric)
    preview_kind = "none"
    preview_title = "Result Preview"
    rows = []
    chart_points = []
    if accepted and status == "ok":
        if (output_shape == "scalar" or
                intent in {"YEAR_AGGREGATE", "RANGE_AGGREGATE"} or
                (intent == "aggregate" and len(plan.get("periods") or []) > 1)) and \
                aggregate is not None:
            periods = analysis.get("periods") or plan.get("periods") or []
            rows = [{"Aggregate": "Monthly average" if analysis.get("aggregation") ==
                     "monthly_average" else "Total revenue" if metric ==
                     "delivered_sales" else str(metric).replace("_", " ").title(),
                     "Period": _period_label(periods), "Value": format_value(aggregate)}]
            preview_kind, preview_title = "aggregate", "Aggregate Result"
        elif mode == "DETERMINISTIC_FALLBACK" and source_rows and all(
                isinstance(row, dict) and {"period", "value"} <= row.keys()
                for row in source_rows):
            rows = sales_result_table(result).to_dict("records")
            preview_kind = ("trend" if analysis.get("response_mode") == "TREND" else
                            "comparison" if analysis.get("response_mode") == "COMPARISON" else
                            "table")
            preview_title = ("Period Comparison" if preview_kind == "comparison" else
                             "Verified Monthly Breakdown")
            if preview_kind == "trend":
                chart_points = [(row["period"], float(row["value"])) for row in source_rows]
        elif isinstance(source_rows, list) and source_rows:
            rows = [dict(row) for row in source_rows]
            preview_kind = (output_shape if output_shape in
                            {"comparison", "time_series", "ranking", "multi_metric"} else
                            "comparison" if plan.get("intent") in
                            {"compare_periods", "growth", "multi_metric"} else
                            "trend" if details.get("answer_type") == "trend" else "table")
            preview_title = ("Ranked Months" if preview_kind == "ranking" else
                             "Monthly Trend" if preview_kind == "time_series" else
                             "Period Comparison" if preview_kind == "comparison" else
                             "Supporting SQL Rows" if details.get("answer_type") ==
                             "aggregate" and len(rows) > 1 else "Verified SQL Result")
            if preview_kind in {"trend", "time_series"}:
                chart_points = [(str(row["period_start"]), float(row["delivered_sales"]))
                                for row in source_rows if "period_start" in row and
                                "delivered_sales" in row]
        elif isinstance(result.get("sql_facts"), dict) and result["sql_facts"]:
            rows = [dict(result["sql_facts"])]
            preview_kind, preview_title = "single", "Verified SQL Result"
    periods = analysis.get("periods") or plan.get("periods") or []
    if len(source_rows) == 2 and all(isinstance(row, dict) and "year" in row
                                     for row in source_rows):
        periods = sorted(str(row["year"]) for row in source_rows)
    kpis = []
    if accepted and status == "ok":
        metric = metric or details.get("answer_type")
        if metric:
            kpis.append(("Metric", str(metric).replace("_", " ").title()))
        if periods:
            kpis.append(("Period", _period_label(periods)))
        if len(source_rows) == 2 and all(isinstance(row, dict) and
                                         {"year", "delivered_sales"} <= row.keys()
                                         for row in source_rows):
            ordered = sorted(source_rows, key=lambda row: str(row["year"]))
            first, second = ordered
            kpis.extend((str(row["year"]), vietnamese_money(row["delivered_sales"]))
                        for row in ordered)
            delta = float(second["delivered_sales"]) - float(first["delivered_sales"])
            kpis.append(("Difference", vietnamese_money(delta)))
            if float(first["delivered_sales"]):
                kpis.append(("Growth", vietnamese_percentage(
                    delta / float(first["delivered_sales"]) * 100)))
        value = aggregate if aggregate is not None else (
            (analysis.get("details") or {}).get("selected_value"))
        if value is None and len(source_rows) == 1 and isinstance(source_rows[0], dict):
            value = next((source_rows[0][key] for key in
                          ("value", metric, "delivered_sales", "aov", "metric_value")
                          if key in source_rows[0]), None)
        if value is not None:
            kpis.append(("Value", format_value(value)))
        change = analysis.get("percent_change")
        if change is not None:
            kpis.append(("Change", vietnamese_percentage(change)))
        if output_shape == "multi_metric" and source_rows:
            for row in source_rows:
                for name in plan.get("metrics") or []:
                    if name in row:
                        raw = row[name]
                        shown = (vietnamese_percentage(float(raw) * 100) if
                                 name.endswith("_rate") else f"{float(raw):,.0f}" if
                                 name == "order_count" else vietnamese_money(raw))
                        kpis.append((f"{row.get('period', '')} {name}".strip()
                                     .replace("_", " ").title(), shown))
        kpis.append(("Execution", "Qwen SQL" if mode == "QWEN_TEXT_TO_SQL" else "Predefined SQL"))
    final_qwen = mode == "QWEN_TEXT_TO_SQL"
    technical = {
        "mode": mode, "model": "Qwen2.5-3B-Instruct" if mode == "QWEN_TEXT_TO_SQL" else "Not used for final SQL",
        "prompt": "text_to_sql_v2" if mode == "QWEN_TEXT_TO_SQL" else "Not used for final SQL",
        "validation": (details.get("validation_status") or status) if final_qwen else
        "Qwen SQL not executed",
        "intent": intent or "—", "tables": (details.get("tables_used") or []) if final_qwen else [],
        "displayed_rows": len(rows), "source_fact_rows": _fact_count(result.get("sql_facts")),
        "generation_ms": details.get("generation_latency_ms") if final_qwen else None,
        "execution_ms": details.get("execution_latency_ms") if final_qwen else None,
        "total_ms": details.get("total_latency_ms") if final_qwen else None,
        "input_tokens": details.get("input_tokens") if final_qwen else None,
        "output_tokens": details.get("output_tokens") if final_qwen else None,
        "status": status, "fallback_reason": details.get("fallback_reason"),
        "check": plan.get("grounding_status") or ("verified SQL result" if accepted else "not executed"),
        "query_plan": plan, "semantic_verification": details.get("semantic_verification"),
        "generation_attempt_count": details.get("generation_attempt_count"),
    }
    return SalesRenderModel(str(result.get("answer") or ""), status, mode, badge, sql, note,
                            tuple(badges), tuple(kpis), preview_title, tuple(rows),
                            preview_kind, tuple(chart_points), technical)


def show_sales_result(result):
    view = result if isinstance(result, SalesRenderModel) else normalize_sales_result(result)
    tone = "warn" if view.status not in {"ok", "no_data"} else "info"
    answer_card("Verified Analysis", view.answer, view.answer_badge, tone)
    if view.kpis:
        primary = [(label, value) for label, value in view.kpis
                   if label == "Value" or label.isdigit() and len(label) == 4]
        secondary = [(label, value) for label, value in view.kpis
                     if (label, value) not in primary]
        for offset in range(0, len(primary), 2):
            group = primary[offset:offset + 2]
            for column, (label, value) in zip(st.columns(len(group)), group, strict=True):
                with column:
                    kpi_card(label, value, kind="primary")
        for offset in range(0, len(secondary), 4):
            group = secondary[offset:offset + 4]
            for column, (label, value) in zip(st.columns(len(group)), group, strict=True):
                with column:
                    kpi_card(label, value, kind="status" if label == "Execution" else "secondary")
    with st.container(border=True):
        st.markdown(f"#### {view.preview_title}")
        if view.preview_rows:
            frame = pd.DataFrame(view.preview_rows)
            if view.preview_kind == "comparison" and len(view.preview_rows) == 2:
                cards = st.columns(2)
                for card, row in zip(cards, view.preview_rows, strict=True):
                    metric_name = (view.technical.get("query_plan") or {}).get(
                        "metric", "delivered_sales")
                    card.metric(str(row.get("year", row.get("period_start",
                                   row.get("period", row.get("Period", "Period"))))),
                                (vietnamese_money(row["delivered_sales"]) if
                                 "delivered_sales" in row else
                                 str(row.get(metric_name, row.get("Revenue",
                                     row.get("Value", "—"))))))
            if view.chart_points and len(view.chart_points) > 1:
                chart = pd.DataFrame(view.chart_points, columns=["Period", "Value"])
                st.line_chart(chart.set_index("Period")["Value"], color="#6366F1", height=220)
            st.dataframe(frame, hide_index=True, width="stretch")
        else:
            empty_state("No result rows to preview", "The final response contains no displayed rows.")
    render_sales_sql(view)
    missing = (view.technical.get("query_plan") or {}).get("missing_periods") or []
    if missing:
        st.caption("Unobserved periods: " + ", ".join(map(str, missing)) +
                   ". No zero values were fabricated.")
    show_sales_technical_details(view)


def sql_presentation(result):
    """Describe only execution facts the accepted service actually returned."""
    details = result.get("sql_details") or {}
    sql = details.get("sql")
    mode = result.get("execution_mode") or "DETERMINISTIC_FALLBACK"
    status = result.get("status")
    if status == "refused_unsafe_request":
        return None, mode, [("Blocked by policy", "warn")], (
            "No SQL generated — request blocked by policy.")
    if status in {"invalid_period", "unsupported_sql"}:
        return None, mode, [("Not executed", "warn")], "No SQL generated or executed."
    if mode == "QWEN_TEXT_TO_SQL" and sql:
        return sql, mode, [("Generated", "info"), ("Validated", "cyan"),
                           ("Read-only", "muted"), ("Executed", "info"),
                           ("Verified", "good")], None
    if mode == "DETERMINISTIC_FALLBACK":
        chips = [("Predefined query", "muted")]
        if status in {"ok", "no_data"}:
            chips.extend([("Executed", "good"), ("Verified", "good")])
        return None, mode, chips, (
            "A safe predefined parameterized query was used because the generated "
            "SQL path could not be accepted. Its SQL text is not exposed by this route.")
    return None, mode, [("SQL unavailable", "warn")], "No SQL text was returned."


def render_sales_sql(result):
    view = result if isinstance(result, SalesRenderModel) else normalize_sales_result(result)
    st.markdown("#### Generated SQL" if view.mode == "QWEN_TEXT_TO_SQL" else
                "#### Fallback Query")
    with st.container(border=True):
        badge_row([(view.mode, "" if view.mode == "QWEN_TEXT_TO_SQL" else "muted"),
                   *view.sql_badges])
        if view.sql:
            st.code(view.sql, language="sql")
        else:
            st.caption(view.sql_note)


def show_sales_technical_details(result):
    view = result if isinstance(result, SalesRenderModel) else normalize_sales_result(result)
    details = view.technical
    with st.expander("Technical Details"):
        left, right = st.columns(2)
        with left:
            st.markdown("**Execution**")
            st.write("Mode:", details["mode"])
            st.write("Model:", details["model"])
            st.write("Prompt version:", details["prompt"])
            st.write("Planner intent:", details["intent"])
            st.write("Query plan:", details.get("query_plan") or "—")
            st.write("Generation attempts:", details.get("generation_attempt_count") or "—")
            st.markdown("**Validation**")
            st.write("Validation:", details["validation"])
            st.write("Safety:", "Validated SELECT" if view.sql else "Predefined query")
            st.write("Read-only enforcement:", "Enabled" if view.sql else "Predefined")
            st.write("Verification:", details["check"])
            st.write("Semantic verification:", details.get("semantic_verification") or "—")
            st.markdown("**Database**")
            st.write("Tables:", ", ".join(details["tables"]) or "Predefined marts")
            st.write("Query scope:", "Selected restaurant")
            st.write("Preview rows:", details["displayed_rows"])
            st.write("Source fact rows:", details["source_fact_rows"])
            st.write("Parameters:", "Bound at execution; values not displayed")
        with right:
            st.markdown("**Performance**")
            for label, key in (("Generation", "generation_ms"),
                               ("SQL execution", "execution_ms"),
                               ("Total", "total_ms")):
                value = details.get(key)
                st.write(f"{label} latency:", f"{value:.1f} ms" if value is not None else "—")
            st.write("Input tokens:", details["input_tokens"] if details["input_tokens"] is not None else "—")
            st.write("Output tokens:", details["output_tokens"] if details["output_tokens"] is not None else "—")
            st.write("Status:", details["status"])
            if details.get("fallback_reason"):
                st.write("Fallback reason:", details["fallback_reason"])


def _delta(value):
    if value is None:
        return None
    return f"{float(value):+.2%}"


def _charts(snapshot):
    monthly = pd.DataFrame(snapshot["monthly"])
    weekly = pd.DataFrame(snapshot["weekly"])
    statuses = pd.DataFrame(snapshot["statuses"])
    for frame in (monthly, weekly):
        if not frame.empty:
            frame["delivered_sales"] = pd.to_numeric(frame["delivered_sales"], errors="coerce")
    if not monthly.empty:
        monthly["mom_growth"] = pd.to_numeric(monthly["mom_growth"], errors="coerce")
    axis = {"labelColor": "#94A3B8", "titleColor": "#94A3B8", "gridColor": "#273244"}
    with st.container(border=True):
        st.subheader("Monthly Revenue")
        st.caption("Delivered revenue by month")
        if monthly.empty:
            empty_state("No monthly sales yet", "Choose another restaurant.")
        else:
            base = alt.Chart(monthly).encode(
                x=alt.X("period_start:T", title="Month", axis=alt.Axis(**axis)),
                y=alt.Y("delivered_sales:Q", title="Delivered revenue (₫)",
                        axis=alt.Axis(format="~s", **axis)),
                tooltip=[alt.Tooltip("period_start:T", title="Month", format="%b %Y"),
                         alt.Tooltip("delivered_sales:Q", title="Revenue (₫)", format=",.0f")],
            )
            chart = base.mark_area(color="#6366F1", opacity=.1) + base.mark_line(
                color="#818CF8", strokeWidth=3, point=True)
            st.altair_chart(chart.properties(height=290), width="stretch")
    left, right = st.columns(2)
    with right, st.container(border=True):
        st.subheader("Month-over-Month Growth")
        st.caption("Monthly growth rate")
        growth = monthly.dropna(subset=["mom_growth"]) if not monthly.empty else monthly
        if growth.empty:
            empty_state("No prior month for comparison")
        else:
            chart = alt.Chart(growth).mark_bar().encode(
                x=alt.X("period_start:T", title="Month", axis=alt.Axis(**axis)),
                y=alt.Y("mom_growth:Q", title="Month-over-month", axis=alt.Axis(format=".0%", **axis)),
                color=alt.condition("datum.mom_growth < 0", alt.value("#FF6B7A"),
                                    alt.value("#22D3EE")),
                tooltip=[alt.Tooltip("period_start:T", title="Month", format="%b %Y"),
                         alt.Tooltip("mom_growth:Q", title="Growth", format="+.1%")],
            )
            st.altair_chart(chart.properties(height=220), width="stretch")
    with left, st.container(border=True):
        st.subheader("Weekly Revenue")
        st.caption("Delivered revenue by week")
        if weekly.empty:
            empty_state("No weekly sales yet")
        else:
            chart = alt.Chart(weekly).mark_line(color="#22D3EE", strokeWidth=2.5,
                                               point=True).encode(
                x=alt.X("period_start:T", title="Week", axis=alt.Axis(**axis)),
                y=alt.Y("delivered_sales:Q", title="Delivered revenue (₫)",
                        axis=alt.Axis(format="~s", **axis)),
                tooltip=[alt.Tooltip("period_start:T", title="Week", format="%d %b %Y"),
                         alt.Tooltip("delivered_sales:Q", title="Revenue (₫)", format=",.0f")],
            )
            st.altair_chart(chart.properties(height=220), width="stretch")
    with st.container(border=True):
        st.subheader("Order Status")
        st.caption("Distribution across observed orders")
        if statuses.empty:
            empty_state("No orders available")
        else:
            counts = statuses.set_index("order_status")["order_count"]
            counts = counts.reindex(["Delivered", "Cancelled", "Refunded"], fill_value=0)
            st.bar_chart(counts, color="#6366F1", height=180)


def _performance_table(rows):
    if not rows:
        return
    st.subheader("Monthly performance")
    with st.expander("View monthly details"):
        display = pd.DataFrame([
            {"Month": row["period_start"].strftime("%Y-%m"),
             "Revenue": money(row["delivered_sales"]),
             "Orders": f"{row['order_count']:,}",
             "AOV": money(row["aov"]),
             "Cancellation rate": percent(row["cancellation_rate"]),
             "MoM growth": percent(row["mom_growth"])}
            for row in reversed(rows)
        ])
        st.dataframe(display, hide_index=True, width="stretch")


def _ask_sql(restaurant_id):
    from src.sales.router import route_question
    from src.sales.service import answer_question
    from src.warehouse.loader import connection

    st.subheader("Ask AI Sales")
    with st.container(border=True):
        st.caption("Ask about verified revenue, orders, AOV, cancellation, refunds or trends.")
        question = st.text_input("Ask AI Sales", key="sales_question",
                                 placeholder="Ví dụ: Doanh thu tháng 5/2026 của nhà hàng 2751 là bao nhiêu?")
        submitted = st.button("✨ Analyze", type="primary", key="ask_sales")
    if submitted:
        st.session_state.pop("_sales_result", None)
        if not question.strip():
            empty_state("Enter a sales question to continue")
        elif route_question(question) != "SALES_SQL":
            st.info("Ask about revenue or orders here. Customer feedback belongs in Review Intelligence.")
        else:
            progress = AIProgress("Analyzing sales data")
            try:
                progress.stage(SALES_STAGES[0], 0.12)
                progress.stage("Connecting to the warehouse", 0.38)
                with connection() as conn:
                    progress.stage("Build plan · generate or select SQL · validate and execute", 0.61)
                    result = answer_question(conn, restaurant_id, question)
                progress.stage(SALES_STAGES[5], 0.92)
                st.session_state["_sales_result"] = {
                    "scope": (str(restaurant_id), question),
                    "view": normalize_sales_result(result),
                    "elapsed": progress.finish(),
                }
            except Exception as error:
                progress.finish(success=False)
                st.error("Unable to query the sales warehouse.")
                with st.expander("Technical Details"):
                    st.code(type(error).__name__)
    saved = st.session_state.get("_sales_result")
    if saved and saved["scope"] == (str(restaurant_id), question):
        show_sales_result(saved["view"])
        st.caption(f"Completed in {saved['elapsed']:.1f} s")


def _cross(restaurant):
    from src.sales.router import route_question
    from src.sales.service import answer_question
    from src.warehouse.loader import connection

    st.subheader("Sales + Customer Feedback")
    st.caption("Combine verified sales metrics with customer review evidence.")
    from src.foody.review_runtime import new_corpus_active

    review_id = restaurant.get("review_restaurant_id") if new_corpus_active() else \
        restaurant.get("restaurant_key")
    if not review_id:
        empty_state("Customer feedback is not linked to this sales restaurant.")
        return
    question = st.text_input("Ask about sales and reviews", key="cross_question",
                             placeholder="Doanh thu giảm thì khách phàn nàn gì?")
    if st.button("✨ Analyze together", key="ask_cross"):
        st.session_state.pop("_cross_result", None)
        if route_question(question) != "CROSS_ANALYSIS":
            empty_state("Ask about both sales and reviews",
                        "Include a sales metric and customer feedback in the question.")
            return
        try:
            with st.spinner("Analyzing verified evidence..."):
                with connection() as conn:
                    result = answer_question(conn, restaurant["restaurant_id"], question)
            st.session_state["_cross_result"] = {
                "scope": (str(restaurant["restaurant_id"]), question), "result": result,
            }
        except Exception as error:
            st.error("Unable to complete cross-analysis.")
            with st.expander("Technical details"):
                st.code(type(error).__name__)
    saved = st.session_state.get("_cross_result")
    if not saved or saved["scope"] != (str(restaurant["restaurant_id"]), question):
        return
    result = saved["result"]
    if result["status"] == "invalid_period":
        st.warning(result["answer"])
        return
    tone = "good" if result["status"] == "grounded" else "warn"
    answer_card("Cross-analysis", result["answer"],
                "Grounded" if tone == "good" else "Limited evidence", tone)
    ids = tuple(item["review_id"] for item in result.get("review_evidence") or [])
    snippets = review_snippets(ids, review_id)
    for index, item in enumerate(result.get("review_evidence") or [], 1):
        snippet = snippets.get(item["review_id"], {})
        evidence_card(item.get("ref") or f"E{index}",
                      snippet.get("text", item.get("text") or "Review source text unavailable"),
                      cross_evidence_metadata(item), review_id=item["review_id"],
                      scope=f"cross:{restaurant['restaurant_id']}:{question}")
    with st.expander("Technical Details"):
        st.json({key: result.get(key) for key in
                 ("route", "status", "sql_facts", "aligned_review_count",
                  "sales_execution_mode", "sales_sql_details")})


def sales_page():
    header("Sales Intelligence", "Verified revenue, order, AOV and trend analytics powered by secure Text-to-SQL.",
           ("PostgreSQL", "Verified Analytics"))
    try:
        restaurants = sales_restaurants()
    except Exception as error:
        st.error("Unable to connect to the sales warehouse.")
        with st.expander("Technical details"):
            st.code(type(error).__name__)
        return
    if not restaurants:
        empty_state("No sales restaurants available", "Load the sales warehouse to begin.")
        return
    by_id = {str(item["restaurant_id"]): item for item in restaurants}
    badge_row([("PostgreSQL connected", "good")])
    st.caption(f"{len(restaurants):,} sales restaurants available")
    selected_id = st.selectbox("Restaurant", list(by_id),
                               format_func=lambda value: f"{by_id[value]['restaurant_name']} · ID {value}",
                               key="sales_restaurant")
    restaurant = by_id[selected_id]
    try:
        snapshot = sales_snapshot(selected_id)
        months = [row["period_start"].strftime("%Y-%m") for row in snapshot["monthly"]]
        if not months:
            empty_state("No observed sales periods for this restaurant")
            return
        from src.sales.queries import vietnam_today

        completed = [month for month in months if month < vietnam_today().strftime("%Y-%m")]
        if (st.session_state.get("_sales_period_restaurant") != selected_id or
                st.session_state.get("sales_period") not in months):
            st.session_state["sales_period"] = completed[-1] if completed else months[-1]
            st.session_state["_sales_period_restaurant"] = selected_id
        period = st.selectbox("Month", list(reversed(months)), key="sales_period")
        metric = month_snapshot(selected_id, period)
    except Exception as error:
        st.error("Unable to load sales analytics.")
        with st.expander("Technical details"):
            st.code(type(error).__name__)
        return
    if metric is None:
        empty_state("No data available for the selected month")
        return
    st.caption(f"Selected period: {period} · completed months use full prior-month comparison")
    cards = st.columns([1.5, 1, 1])
    with cards[0]:
        kpi_card("Delivered Revenue", money(metric["delivered_sales"]), kind="primary",
                 detail=f"{period} · {_delta(metric.get('comparison_growth')) or 'No prior-month change'}")
    with cards[1]:
        kpi_card("Total Orders", f"{metric['order_count']:,}")
    with cards[2]:
        kpi_card("Average Order Value", money(metric["aov"]))
    summary = snapshot["summary"] or {}
    rates = st.columns(2)
    with rates[0]:
        kpi_card("Cancellation Rate", percent(summary.get("cancellation_rate")),
                 detail="All observed orders for this restaurant")
    with rates[1]:
        kpi_card("Refund Rate", percent(summary.get("refund_rate")),
                 detail="All observed orders for this restaurant")
    st.caption("Revenue, orders and AOV use the selected month. Cancellation and refund rates "
               "cover all observed orders for this restaurant.")
    _charts(snapshot)
    _performance_table(snapshot["monthly"])
    _ask_sql(selected_id)
    _cross(restaurant)
