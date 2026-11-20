"""Cross Intelligence inside the existing Review workspace."""

import pandas as pd
import streamlit as st

from src.ui.components import answer_card, badge_row, empty_state, evidence_card, kpi_card, money


def _restaurants():
    from src.ui.sales_view import sales_restaurants

    return {str(row["restaurant_id"]): row for row in sales_restaurants()
            if str(row.get("review_restaurant_id")) == str(row["restaurant_id"])}


def render_cross_intelligence():
    st.subheader("Cross Intelligence")
    st.caption("Compare verified Sales facts with customer signals from the same restaurant and months.")
    try:
        restaurants = _restaurants()
    except Exception:
        st.error("Sales warehouse is unavailable.")
        return
    if not restaurants:
        empty_state("No exact restaurant ID matches are available")
        return
    restaurant_id = st.selectbox(
        "Cross restaurant", list(restaurants),
        format_func=lambda value: f"{restaurants[value]['restaurant_name']} · ID {value}",
        key="cross_intelligence_restaurant")
    question = st.text_input(
        "Ask about Sales and Reviews", key="cross_intelligence_question",
        placeholder="Doanh thu tháng 6/2025 thay đổi thế nào so với tháng 5/2025 và khách hàng đang phản hồi gì?")
    if st.button("Analyze Cross Intelligence", type="primary", key="run_cross_intelligence"):
        st.session_state.pop("_cross_intelligence_result", None)
        if not question.strip():
            st.info("Enter a Sales and Review question to begin.")
            return
        try:
            from src.sales.cross_intelligence import analyze_cross
            from src.warehouse.loader import connection

            with st.spinner("Aligning verified Sales and Review evidence..."):
                with connection() as conn:
                    result = analyze_cross(conn, restaurant_id, question)
            st.session_state["_cross_intelligence_result"] = {
                "scope": (restaurant_id, question), "result": result}
        except ValueError as error:
            st.warning(str(error))
            return
        except Exception:
            st.error("Cross Intelligence is temporarily unavailable.")
            return
    saved = st.session_state.get("_cross_intelligence_result")
    if not saved or saved["scope"] != (restaurant_id, question):
        return
    result = saved["result"]
    if result["status"] in {"unmatched_restaurant", "unsupported_corpus"}:
        st.warning(result["answer"])
        return
    facts = result["sales_facts"]
    reviews = result["review_aggregates"]
    st.subheader("Sales Performance")
    st.caption("FACT · Verified monthly PostgreSQL Sales values")
    if facts:
        first, last = facts[0], facts[-1]
        cards = st.columns(3)
        with cards[0]:
            kpi_card(f"Delivered · {first['period']}", money(first["delivered_sales"]),
                     kind="primary")
        with cards[1]:
            kpi_card(f"Delivered · {last['period']}", money(last["delivered_sales"]),
                     kind="primary")
        with cards[2]:
            delta = last["delivered_sales"] - first["delivered_sales"]
            kpi_card("Change", money(delta), kind="status")
        st.dataframe(pd.DataFrame(facts), hide_index=True, use_container_width=True)
    else:
        st.warning("No Sales rows exist for the requested periods.")
    st.subheader("Quantitative Drivers")
    st.caption("FACT · Measured component changes; these do not establish causation")
    drivers = result.get("sales_drivers") or []
    if drivers:
        st.dataframe(pd.DataFrame(drivers), hide_index=True, use_container_width=True)
    else:
        st.info("Two observed Sales periods are needed to calculate changes.")
    st.subheader("Customer Signals")
    st.caption("SIGNAL · Model-predicted sentiment and aspect counts in the same months")
    if any(item["review_count"] for item in reviews):
        rows = [{"Month": item["period"], "Reviews": item["review_count"],
                 "Positive": item["positive_count"], "Neutral": item["neutral_count"],
                 "Negative": item["negative_count"],
                 "Negative rate": item["sentiment_rate"]["negative"],
                 "Top aspects": ", ".join(list(item["aspect_frequencies"])[:3])}
                for item in reviews]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        badge_row([(f"{item['period']}: {item['review_count']} reviews", "info")
                   for item in reviews])
    else:
        st.warning("No Review rows exist for this restaurant in the requested periods.")
    st.subheader("AI Synthesis")
    st.caption("INTERPRETATION · Associations are observational, not proven causes")
    tone = "good" if result["status"] == "grounded" else "warn"
    answer_card("Sales + Review", result["answer"],
                "Grounded association" if tone == "good" else "Limited evidence", tone)
    st.subheader("Evidence")
    st.caption("EVIDENCE · Retrieved reviews verified by restaurant ID and date")
    for item in result["review_evidence"]:
        evidence_card(item["ref"], item["text"],
                      f"{item['period']} · {item['date']} · "
                      f"{item.get('sentiment') or 'unknown'} · ID {item['restaurant_id']} · "
                      f"Aspects: {', '.join(item.get('aspects') or []) or 'unavailable'}",
                      review_id=item["review_id"],
                      scope=f"cross-intelligence:{restaurant_id}:{question}")
    if not result["review_evidence"]:
        empty_state("No aligned Review evidence accepted")
    if result.get("missing_data"):
        st.info("Limitations: " + "; ".join(result["missing_data"]))
    with st.expander("Technical Details"):
        st.json({"plan": result["plan"], **result["technical"]})
