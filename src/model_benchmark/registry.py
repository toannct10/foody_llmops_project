"""Pinned local candidate registry; no network or model downloads."""

import json
from dataclasses import dataclass
from pathlib import Path

from src.utils.hashing import file_checksum

REGISTRY = Path("config/model_benchmark.json")


@dataclass(frozen=True)
class ModelSpec:
    key: str
    family: str
    name: str
    repo: str
    revision: str
    file: str
    sha256: str
    parameter_count: int
    quantization: str
    port: int
    role: str = "research_evaluation"
    status: str = "benchmark"
    capabilities: tuple[str, ...] = ("text_to_sql", "structured_output")
    benchmark_summary_ref: str | None = None

    def availability(self, *, verify_hash=False):
        path = Path(self.file)
        if not path.is_file():
            return "MODEL_NOT_AVAILABLE"
        if verify_hash and file_checksum(path) != self.sha256:
            return "MODEL_HASH_MISMATCH"
        return "AVAILABLE"


def load_registry(path=REGISTRY):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"qwen", "llama", "deepseek"}
    if set(data["models"]) != required:
        raise ValueError("Expected exactly Qwen, Llama and DeepSeek candidates")
    specs = {}
    for key, value in data["models"].items():
        specs[key] = ModelSpec(
            key=key, family=value["family"], name=value["name"],
            repo=value["repo"], revision=value["revision"],
            file=value["file"], sha256=value["sha256"],
            parameter_count=value["parameter_count"],
            quantization=value["quantization"], port=value["port"],
            role=value.get("role", "research_evaluation"),
            status=value.get("status", "benchmark"),
            capabilities=tuple(value.get("capabilities", ("text_to_sql",))),
            benchmark_summary_ref=value.get("benchmark_summary_ref"))
    if len({spec.port for spec in specs.values()}) != len(specs):
        raise ValueError("Benchmark model ports must be unique")
    if {key for key, spec in specs.items() if spec.status == "production"} != {"qwen"}:
        raise ValueError("Qwen must remain the only production model")
    if any(spec.status not in {"production", "benchmark", "disabled"} for spec in specs.values()):
        raise ValueError("Invalid model status")
    return data, specs


def select_models(specs, *, model=None, all_models=False):
    if bool(model) == bool(all_models):
        raise ValueError("Choose exactly one --model or --all")
    if all_models:
        return [specs[key] for key in ("qwen", "llama", "deepseek")]
    if model not in specs:
        raise ValueError(f"Unknown benchmark model: {model}")
    return [specs[model]]
