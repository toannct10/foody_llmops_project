"""Ad-hoc model comparison must preserve each model's task contract and isolation."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.foody.review_models import analyze_models
from src.foody.review_models.phobert_absa_adapter import (
    PHOBERT_ROOT,
    PhoBERTABSAAdapter,
    load_phobert_resources,
)

EXAMPLE = "Đồ ăn ngon nhưng phục vụ hơi chậm và giá khá cao."
HAS_PHOBERT_WEIGHTS = (PHOBERT_ROOT / "absa.pt").exists()
HAS_TFIDF_WEIGHTS = Path("models/tfidf_logreg.joblib").exists()


@pytest.mark.skipif(not HAS_PHOBERT_WEIGHTS, reason="PhoBERT checkpoint is local-only")
def test_phobert_bundle_layout_and_native_labels():
    expected = {"backbone_config", "tokenizer", "absa.pt", "absa_config.json",
                "absa_test_metrics.json", "history.csv", "relevance.joblib",
                "relevance_config.json", "relevance_proxy_metrics.json"}
    assert {item.name for item in PHOBERT_ROOT.iterdir()} == expected
    spec = json.loads((PHOBERT_ROOT / "absa_config.json").read_text(encoding="utf-8"))
    assert spec["labels"] == ["not_mentioned", "positive", "negative", "neutral"]
    assert len(spec["aspects"]) == 12


@pytest.mark.skipif(not HAS_TFIDF_WEIGHTS, reason="Production classifier is local-only")
def test_tfidf_only_keeps_production_predictions(monkeypatch):
    from src.foody.review_models import phobert_absa_adapter

    monkeypatch.setattr(phobert_absa_adapter.PhoBERTABSAAdapter, "predict",
                        lambda *_: pytest.fail("PhoBERT ABSA model loaded in TF-IDF view"))
    output = analyze_models(EXAMPLE, "TF-IDF")
    assert set(output) == {"tfidf"}
    result = output["tfidf"]["result"]
    assert result["sentiment"] in {"positive", "neutral", "negative"}
    assert all(item["sentiment"] is None for item in result["aspects"])


@pytest.mark.skipif(not HAS_PHOBERT_WEIGHTS, reason="PhoBERT checkpoint is local-only")
def test_phobert_cpu_inference_uses_native_aspect_sentiment_and_cached_weights():
    first = load_phobert_resources(PHOBERT_ROOT)
    assert load_phobert_resources(PHOBERT_ROOT) is first
    assert all(parameter.device.type == "cpu" for parameter in first[0].parameters())
    output = analyze_models(EXAMPLE, "PhoBERT ABSA")
    assert set(output) == {"phobert_absa"}
    result = output["phobert_absa"]["result"]
    assert result["sentiment"] is None
    assert result["sentiment_score"] is None
    assert result["supported_tasks"] == ["aspect_sentiment"]
    assert all(item["label"] in first[3]["aspects"] for item in result["aspects"])
    assert all(item["sentiment"] in first[3]["labels"][1:]
               for item in result["aspects"])
    assert "unmapped_relevance_proxy_scores" in result["raw_output"]


def test_compare_isolates_phobert_failure(monkeypatch):
    from src.foody.review_models.tfidf_adapter import TfidfAdapter

    monkeypatch.setattr(TfidfAdapter, "predict", lambda *_: {"model_id": "tfidf"})
    monkeypatch.setattr(PhoBERTABSAAdapter, "predict",
                        lambda *_: (_ for _ in ()).throw(RuntimeError("private path")))
    output = analyze_models(EXAMPLE)
    assert output["tfidf"]["status"] == "available"
    assert output["phobert_absa"] == {"status": "unavailable", "result": None,
                                "error_type": "RuntimeError"}
    assert "private path" not in str(output)


def test_compare_isolates_tfidf_failure(monkeypatch):
    from src.foody.review_models.tfidf_adapter import TfidfAdapter

    monkeypatch.setattr(TfidfAdapter, "predict",
                        lambda *_: (_ for _ in ()).throw(RuntimeError("private path")))
    monkeypatch.setattr(PhoBERTABSAAdapter, "predict", lambda *_: {"model_id": "phobert_absa"})
    output = analyze_models(EXAMPLE)
    assert output["tfidf"]["status"] == "unavailable"
    assert output["phobert_absa"]["status"] == "available"


def test_empty_review_and_unknown_view_do_not_load_models(monkeypatch):
    monkeypatch.setattr(PhoBERTABSAAdapter, "predict",
                        lambda *_: pytest.fail("Loaded PhoBERT ABSA model"))
    with pytest.raises(ValueError, match="Enter review text"):
        analyze_models("   ")
    with pytest.raises(ValueError, match="Unknown review model"):
        analyze_models(EXAMPLE, "Unknown")


@pytest.mark.skipif(not HAS_PHOBERT_WEIGHTS or not HAS_TFIDF_WEIGHTS,
                    reason="Live artifacts are local-only")
def test_inference_does_not_call_rag_or_mutate_database_or_indexes(monkeypatch):
    import psycopg
    import requests

    def forbidden(*_args, **_kwargs):
        pytest.fail("Ad-hoc comparison reached a remote service or writer")

    monkeypatch.setattr(psycopg, "connect", forbidden)
    monkeypatch.setattr(requests, "post", forbidden)
    monkeypatch.setattr("src.rag.vector_store.build_index", forbidden)
    monkeypatch.setattr("src.rag_v2.lexical.build_index", forbidden)
    result = analyze_models(EXAMPLE)
    assert result["tfidf"]["status"] == "available"
    assert result["phobert_absa"]["status"] == "available"


def test_docker_mount_is_relative_and_dependencies_are_pinned():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = Path("Dockerfile.rag").read_text(encoding="utf-8")
    requirements = Path("requirements-phobert-absa.txt").read_text(encoding="utf-8")
    assert "./models:/app/models:ro" in compose
    assert "requirements-phobert-absa.txt" in dockerfile
    assert "download.pytorch.org/whl/cpu" in dockerfile
    assert all(name + "==" in requirements for name in
               ("torch", "transformers", "sentencepiece"))


def test_review_ui_has_three_view_modes_and_empty_button():
    app = AppTest.from_string(
        "from src.ui.review_analysis_view import render_review_analysis\n"
        "render_review_analysis()\n"
    ).run()
    assert not app.exception
    assert app.radio[0].options == ["Compare Models", "TF-IDF", "PhoBERT ABSA"]
    assert app.button[0].disabled
