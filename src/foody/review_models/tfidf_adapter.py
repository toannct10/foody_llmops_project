"""Normalize the existing production classifier output without changing inference."""

from src.foody.ad_hoc_review import analyze_review


class TfidfAdapter:
    model_id = "tfidf"

    def predict(self, text: str) -> dict:
        raw = analyze_review(text)
        return {
            "model_id": self.model_id,
            "model_name": "TF-IDF + Logistic Regression",
            "sentiment": raw["sentiment"],
            "sentiment_score": raw["sentiment_confidence"],
            "aspects": [{"label": label, "sentiment": None,
                         "score": raw["aspect_scores"].get(label)}
                        for label in raw["aspects"]],
            "supported_tasks": ["review_sentiment", "multi_label_aspect_detection"],
            "latency_ms": raw["latency_ms"],
            "raw_output": raw,
            "metadata": {"framework": "scikit-learn", "backbone": "TF-IDF",
                         "training_dataset": "VN-MSASar v3",
                         "version": "saved production artifacts",
                         "preprocessing": raw["preprocessing"],
                         "artifact_paths": ["models/tfidf_logreg.joblib",
                                            "models/aspect_tfidf.joblib"]},
        }
