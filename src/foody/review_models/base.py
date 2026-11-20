"""Shared response contract; absent model tasks remain null rather than inferred."""

from typing import Protocol


class ReviewModel(Protocol):
    model_id: str

    def predict(self, text: str) -> dict: ...
