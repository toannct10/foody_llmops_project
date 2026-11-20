"""CPU adapter reconstructed from the supplied PhoBERT state_dict and configs.

The bundle has no training forward-pass source. Its 12 heads each have four
outputs. CLS yields focused output on the live example; the original training
word segmentation and forward pass remain unverified limitations.
"""

import json
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from src.foody.schema import normalize

PHOBERT_ROOT = Path("models/phobert_absa")


@lru_cache(maxsize=2)
def load_phobert_resources(root: Path):
    """Load each local checkpoint/tokenizer/proxy once per process, on CPU."""
    import joblib
    import torch
    from transformers import PhobertTokenizer, RobertaConfig, RobertaModel

    root = Path(root)
    spec = json.loads((root / "absa_config.json").read_text(encoding="utf-8"))
    labels = spec["labels"]
    aspects = spec["aspects"]
    if labels != ["not_mentioned", "positive", "negative", "neutral"] or len(aspects) != 12:
        raise ValueError("Unexpected PhoBERT ABSA label layout")
    backbone = RobertaConfig.from_pretrained(root / "backbone_config",
                                              local_files_only=True)
    tokenizer = PhobertTokenizer.from_pretrained(root / "tokenizer",
                                                  local_files_only=True)

    class Network(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = RobertaModel(backbone, add_pooling_layer=True)
            self.heads = torch.nn.ModuleList([
                torch.nn.Linear(backbone.hidden_size, len(labels)) for _ in aspects
            ])

        def forward(self, **tokens):
            cls = self.encoder(**tokens).last_hidden_state[:, 0]
            return torch.stack([head(cls) for head in self.heads], dim=1)

    model = Network()
    state = torch.load(root / "absa.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    del state
    model.eval()
    relevance = joblib.load(root / "relevance.joblib")
    return model, tokenizer, relevance, spec


class PhoBERTABSAAdapter:
    model_id = "phobert_absa"

    def __init__(self, root: Path = PHOBERT_ROOT):
        self.root = Path(root)

    def predict(self, text: str) -> dict:
        import torch

        clean = normalize(text)
        if not clean:
            raise ValueError("Enter review text before analysis.")
        started = perf_counter()
        model, tokenizer, relevance, spec = load_phobert_resources(self.root)
        tokens = tokenizer(clean, return_tensors="pt", truncation=True,
                           max_length=int(spec["max_length"]))
        with torch.inference_mode():
            probabilities = model(**tokens).softmax(dim=-1)[0].tolist()
        native = []
        detected = []
        for aspect, scores in zip(spec["aspects"], probabilities, strict=True):
            index = max(range(len(scores)), key=scores.__getitem__)
            entry = {"label": aspect, "sentiment": spec["labels"][index],
                     "score": float(scores[index])}
            native.append({**entry, "label_scores": dict(zip(spec["labels"], scores,
                                                            strict=True))})
            if index != 0:
                detected.append(entry)
        proxy = relevance.predict_proba([clean])[0]
        proxy_scores = {str(label): float(score) for label, score in zip(
            relevance.classes_, proxy, strict=True)}
        return {
            "model_id": self.model_id,
            "model_name": "PhoBERT ABSA",
            "sentiment": None,
            "sentiment_score": None,
            "aspects": detected,
            "supported_tasks": ["aspect_sentiment"],
            "latency_ms": (perf_counter() - started) * 1000,
            "raw_output": {"native_aspect_predictions": native,
                           "unmapped_relevance_proxy_scores": proxy_scores},
            "metadata": {"framework": "PyTorch / Transformers",
                         "backbone": "PhoBERT / RoBERTa, 12 layers, hidden size 768",
                         "training_dataset": "Not specified",
                         "version": spec.get("source_commit", "Not specified"),
                         "tokenizer": "bundled PhobertTokenizer",
                         "label_space": {"aspects": spec["aspects"],
                                         "sentiments": spec["labels"]},
                         "preprocessing": "Unicode NFC, whitespace collapse, bundled tokenizer; "
                         "training word segmentation unverified",
                         "relevance_model_usage": "Binary weak-label proxy, class meanings "
                         "unverified; reported only, not used as a gate",
                         "pooling_assumption": "CLS token; selected from artifact head "
                         "shape and live output checks; training forward pass unavailable",
                         "artifact_paths": [str(self.root / name) for name in
                                            ("absa.pt", "absa_config.json", "tokenizer",
                                             "backbone_config", "relevance.joblib")]},
        }
