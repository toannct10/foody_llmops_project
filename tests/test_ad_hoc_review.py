"""Saved-model, ad-hoc review inference and UI boundaries."""

import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

from src.foody.ad_hoc_review import analyze_review


@pytest.mark.parametrize(("text", "sentiment"), [
    ("Đồ ăn rất ngon, phục vụ chu đáo, tôi rất hài lòng.", "positive"),
    ("Đồ ăn dở, nhân viên thô lỗ, phục vụ quá chậm, giá đắt.", "negative"),
    ("Quán nằm trên đường Nguyễn Trãi và mở cửa lúc 8 giờ sáng.", "neutral"),
])
def test_real_production_sentiment_models(text, sentiment):
    result = analyze_review(text)
    assert result["sentiment"] == sentiment
    assert 0 <= result["sentiment_confidence"] <= 1
    assert result["sentiment_model"] == "tfidf_logreg.joblib"
    assert result["aspect_model"] == "aspect_tfidf.joblib"


def test_real_multi_aspect_review_uses_saved_threshold():
    result = analyze_review("Món ăn ngon, nhân viên nhiệt tình, giá hợp lý, không gian thoáng mát.")
    assert set(result["aspects"]) == {"ambiance", "food", "price", "service"}
    assert all(result["aspect_scores"][name] >= result["aspect_threshold"]
               for name in result["aspects"])


def test_empty_input_is_rejected_before_model_loading(monkeypatch):
    from src.foody import ad_hoc_review

    monkeypatch.setattr(ad_hoc_review, "production_models", lambda: pytest.fail("models loaded"))
    with pytest.raises(ValueError, match="Enter review text"):
        analyze_review("  \n  ")


def test_model_failure_is_not_persisted_and_ui_error_is_sanitized(monkeypatch):
    from src.foody import ad_hoc_review

    def fail():
        raise RuntimeError("secret model path")

    monkeypatch.setattr(ad_hoc_review, "production_models", fail)
    with pytest.raises(RuntimeError, match="secret model path"):
        analyze_review("Đồ ăn ngon")

    app = AppTest.from_string(
        "import streamlit as st\n"
        "from src.ui import review_analysis_view as view\n"
        "view.analyze_models = lambda text, mode: (_ for _ in ()).throw(RuntimeError('secret model path'))\n"
        "view.render_review_analysis()\n"
    ).run()
    app.text_area[0].set_value("Đồ ăn ngon").run()
    app.button[0].click().run()
    assert not app.exception
    assert any("temporarily unavailable" in item.value for item in app.error)
    assert all("secret model path" not in item.value for item in app.error)


def test_inference_never_calls_qwen_database_or_index_writers(monkeypatch):
    import psycopg
    import requests

    def forbidden(*_args, **_kwargs):
        pytest.fail("Ad-hoc inference reached an external service or writer")

    monkeypatch.setattr(requests, "post", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(psycopg, "connect", forbidden)
    monkeypatch.setattr("pandas.DataFrame.to_parquet", forbidden)
    monkeypatch.setattr("src.foody.schema.save_parquet", forbidden)
    monkeypatch.setattr("src.rag.vector_store.build_index", forbidden)
    monkeypatch.setattr("src.rag_v2.lexical.build_index", forbidden)
    result = analyze_review("Đồ ăn rất ngon, phục vụ chu đáo, tôi rất hài lòng.")
    assert result["sentiment"] == "positive"


def test_review_analysis_tab_and_empty_button():
    app = AppTest.from_string(
        "from src.ui.review_analysis_view import render_review_analysis\n"
        "render_review_analysis()\n"
    ).run()
    assert not app.exception
    assert app.button[0].disabled
