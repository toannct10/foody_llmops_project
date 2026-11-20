"""Presentation contracts for the three-workspace Streamlit demo."""

from streamlit.testing.v1 import AppTest

from src.ui.components import preview_text, review_state_key
from src.ui.progress import REVIEW_STAGES, SALES_STAGES, AIProgress
from src.ui.sales_view import sql_presentation


def test_sales_sql_is_outside_technical_details():
    result = {"status": "ok", "answer": "Verified revenue", "execution_mode": "QWEN_TEXT_TO_SQL",
              "sql_details": {"sql": "SELECT delivered_sales FROM restaurant_monthly_sales",
                              "validation_status": "SQL validated before execution"}}
    app = AppTest.from_string("from src.ui.sales_view import show_sales_result\n"
                              f"show_sales_result({result!r})\n").run()
    assert not app.exception
    assert len(app.code) == 1
    assert "SELECT delivered_sales" in app.code[0].value
    assert any("QWEN_TEXT_TO_SQL" in item.value for item in app.markdown)
    assert sql_presentation(result)[2] == [
        ("Generated", "info"), ("Validated", "cyan"), ("Read-only", "muted"),
        ("Executed", "info"), ("Verified", "good")]


def test_fallback_and_blocked_sql_are_truthfully_labeled():
    fallback = {"status": "ok", "answer": "Verified", "execution_mode": "DETERMINISTIC_FALLBACK",
                "sql_details": {"sql": None}}
    blocked = {"status": "refused_unsafe_request", "answer": "Blocked",
               "execution_mode": "DETERMINISTIC_FALLBACK", "sql_details": {"sql": None}}
    assert "predefined parameterized query" in sql_presentation(fallback)[3]
    assert "blocked by policy" in sql_presentation(blocked)[3]
    for result in (fallback, blocked):
        app = AppTest.from_string("from src.ui.sales_view import show_sales_result\n"
                                  f"show_sales_result({result!r})\n").run()
        assert not app.exception
        assert len(app.code) == 0


def test_review_text_replaces_preview_in_place_without_backend_calls():
    long_text = "Món ăn ngon nhưng thời gian chờ khá lâu. " * 12
    app = AppTest.from_string("from src.ui.components import review_text\n"
                              f"review_text('stable-review-42', {long_text!r}, "
                              "scope='restaurant-2751', limit=90)\n").run()
    assert not app.exception
    assert len(app.button) == 1
    assert app.button[0].label == "More"
    assert preview_text(long_text, 90) in [item.value for item in app.markdown]
    assert long_text not in [item.value for item in app.markdown]
    app.button[0].click().run()
    assert app.button[0].label == "Less"
    assert [item.value for item in app.markdown].count(long_text.strip()) == 1
    assert preview_text(long_text, 90) not in [item.value for item in app.markdown]
    app.button[0].click().run()
    assert app.button[0].label == "More"
    assert long_text not in [item.value for item in app.markdown]
    assert review_state_key("stable-review-42", "restaurant-2751") == review_state_key(
        "stable-review-42", "restaurant-2751")
    assert review_state_key("stable-review-42", "other") != review_state_key(
        "stable-review-42", "restaurant-2751")
    assert preview_text("short", 90) == "short"


def test_loading_component_and_stage_contracts():
    assert AIProgress
    assert len(SALES_STAGES) >= 3
    assert len(REVIEW_STAGES) >= 3
    assert "SQL" in SALES_STAGES[2]
    assert "evidence" in REVIEW_STAGES[2]
