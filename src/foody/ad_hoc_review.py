"""Read-only, single-review inference through the current production classifiers."""

from functools import lru_cache
from time import perf_counter

import joblib
import pandas as pd

from src.foody.aspect import MODEL as ASPECT_MODEL
from src.foody.enrichment import SENTIMENT_MODEL
from src.foody.review_migration import enrich
from src.foody.schema import normalize


@lru_cache(maxsize=1)
def production_models():
    """Load the same artifacts used for Review corpus enrichment once per process."""
    return joblib.load(SENTIMENT_MODEL), joblib.load(ASPECT_MODEL)


def analyze_review(text):
    """Classify one text in memory; never write a corpus, index, or database."""
    clean = normalize(text)
    if not clean:
        raise ValueError("Enter review text before analysis.")
    started = perf_counter()
    sentiment_model, aspect_bundle = production_models()
    result = enrich(pd.DataFrame({"comment": [clean]}), sentiment_model, aspect_bundle).iloc[0]
    return {
        "sentiment": result.predicted_sentiment,
        "sentiment_confidence": float(result.sentiment_confidence),
        "aspects": list(result.predicted_aspects),
        "aspect_scores": {str(label): float(score) for label, score in result.aspect_scores.items()},
        "aspect_threshold": float(aspect_bundle["threshold"]),
        "latency_ms": (perf_counter() - started) * 1000,
        "sentiment_model": SENTIMENT_MODEL.name,
        "aspect_model": ASPECT_MODEL.name,
        "preprocessing": "Unicode NFC normalization and whitespace collapse; saved TF-IDF pipelines",
    }
