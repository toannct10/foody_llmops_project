"""Read-only comparison of production classifiers and the PhoBERT ABSA bundle."""

import streamlit as st

from src.foody.review_models.registry import analyze_models
from src.ui.components import badge_row, kpi_card
from src.ui.progress import CLASSIFIER_STAGES, AIProgress


def _render_model_card(title, outcome):
    with st.container(border=True):
        st.markdown(f"#### {title}")
        if outcome["status"] != "available":
            st.warning("Model unavailable")
            with st.expander("Technical Details"):
                st.write("Inference could not complete.")
                st.write("Error type:", outcome.get("error_type", "Unknown"))
            return
        result = outcome["result"]
        sentiment = result["sentiment"]
        kpi_card("Overall sentiment", sentiment.title() if sentiment else
                 "Not supported by this model", kind="primary")
        if result["sentiment_score"] is not None:
            st.caption(f"Model score: {result['sentiment_score']:.1%} (uncalibrated)")
        st.caption(f"Inference latency: {result['latency_ms']:.1f} ms")
        if result["aspects"]:
            if result["model_id"] == "tfidf":
                badge_row([(item["label"].replace("_", " ").title(), "info")
                           for item in result["aspects"]])
                st.caption("Detected aspect model scores: " + " · ".join(
                    f"{item['label'].title()} {item['score']:.1%}"
                    for item in result["aspects"] if item["score"] is not None))
            else:
                for item in result["aspects"]:
                    st.write(f"{item['label']} → {item['sentiment'].title()}"
                             f" · Model score {item['score']:.1%}")
        else:
            st.info("No aspect was detected by this model.")
        with st.expander("Technical Details"):
            st.json({"model_name": result["model_name"],
                     "supported_tasks": result["supported_tasks"],
                     "latency_ms": result["latency_ms"],
                     **result["metadata"], "raw_output": result["raw_output"]})


def render_review_analysis():
    with st.container(border=True):
        st.subheader("Analyze Customer Review")
        st.caption("Compare saved models on one Vietnamese review. The submitted text "
                   "is not added to the Review corpus or indexes.")
        mode = st.radio("View Mode", ("Compare Models", "TF-IDF", "PhoBERT ABSA"),
                        horizontal=True, key="review_model_view_mode")
        review = st.text_area("Review text", key="adhoc_review_text", height=150,
                              placeholder="Đồ ăn ngon nhưng phục vụ hơi chậm và giá cao.")
        submitted = st.button("Analyze Review", type="primary", key="analyze_review",
                              disabled=not review.strip())
    if submitted:
        st.session_state.pop("_adhoc_review_result", None)
        progress = AIProgress("Analyzing review")
        try:
            progress.stage(CLASSIFIER_STAGES[0], 0.1)
            progress.stage(CLASSIFIER_STAGES[1], 0.5)
            results = analyze_models(review, mode)
            progress.stage(CLASSIFIER_STAGES[2], 0.95)
            st.session_state["_adhoc_review_result"] = {
                "scope": (review, mode), "results": results}
            progress.finish()
        except Exception:
            progress.finish(success=False)
            st.error("Review analysis is temporarily unavailable. Please try again later.")
            return
    saved = st.session_state.get("_adhoc_review_result")
    if not saved or saved["scope"] != (review, mode):
        return
    results = saved["results"]
    if mode == "Compare Models":
        left, right = st.columns(2)
        with left:
            _render_model_card("TF-IDF + Logistic Regression", results["tfidf"])
        with right:
            _render_model_card("PhoBERT ABSA Model", results["phobert_absa"])
        st.caption("These models were trained on different datasets. Ad-hoc predictions "
                   "do not establish comparative accuracy.")
    elif mode == "TF-IDF":
        _render_model_card("TF-IDF + Logistic Regression", results["tfidf"])
    else:
        _render_model_card("PhoBERT ABSA Model", results["phobert_absa"])
