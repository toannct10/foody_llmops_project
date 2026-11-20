"""Isolated model execution for the existing Analyze a Review tab."""

import logging

from src.foody.schema import normalize

LOGGER = logging.getLogger(__name__)


def analyze_models(text: str, mode: str = "Compare Models") -> dict:
    clean = normalize(text)
    if not clean:
        raise ValueError("Enter review text before analysis.")
    selected = {"Compare Models": ("tfidf", "phobert_absa"),
                "TF-IDF": ("tfidf",), "PhoBERT ABSA": ("phobert_absa",)}.get(mode)
    if selected is None:
        raise ValueError("Unknown review model view mode")
    results = {}
    for name in selected:
        try:
            if name == "tfidf":
                from src.foody.review_models.tfidf_adapter import TfidfAdapter

                model = TfidfAdapter()
            else:
                from src.foody.review_models.phobert_absa_adapter import PhoBERTABSAAdapter

                model = PhoBERTABSAAdapter()
            results[name] = {"status": "available", "result": model.predict(clean)}
        except Exception as error:
            LOGGER.exception("Review classifier %s failed", name)
            results[name] = {"status": "unavailable", "result": None,
                             "error_type": type(error).__name__}
    return results
