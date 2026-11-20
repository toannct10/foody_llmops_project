"""OpenAI-compatible llama.cpp gateway; production defaults to pinned Qwen."""

import json
import os
from functools import lru_cache
from hashlib import file_digest
from pathlib import Path
from time import perf_counter

import requests
import yaml

from src.monitoring.metrics import observe_model_gateway
from src.proposed_v1.runtime import LocalQwen
from src.rag.monitoring import record
from src.security.audit import security_event

CONFIG = Path("qwen_v1.yaml")
PROVENANCE = Path("models/qwen_v1/provenance.json")


@lru_cache(maxsize=4)
def _model_digest(path, size, modified_ns):
    """Stream the frozen GGUF once per process; stat values invalidate the cache."""
    with path.open("rb") as model_file:
        return file_digest(model_file, "sha256").hexdigest()


class LLMGateway:
    def __init__(self, url=None, launch_local=True, monitor=True,
                 config_path=CONFIG, provenance_path=PROVENANCE, model_id=None):
        self.model_id = model_id or "qwen"
        if model_id is not None and config_path == CONFIG and provenance_path == PROVENANCE:
            from src.model_benchmark.registry import load_registry

            settings, specs = load_registry()
            if model_id not in specs or specs[model_id].status == "disabled":
                raise ValueError("Unknown or disabled model ID")
            spec = specs[model_id]
            if model_id == "qwen":
                config_path = Path("qwen_v3_3b.yaml")
                provenance_path = Path("models/qwen_v3/provenance.json")
                self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
                self.provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            else:
                model_file = Path(spec.file)
                self.config = {
                    "model_dir": str(model_file.parent), "model_file": model_file.name,
                    "port": spec.port, "runtime": settings["backend"],
                    "gpu_layers": settings["gpu_layers_requested"],
                    "threads": settings["threads"],
                    "context_size": settings["context_size"],
                    "temperature": settings["temperature"], "seed": settings["seed"],
                }
                self.provenance = {"model": spec.repo, "model_sha256": spec.sha256}
                self.provenance["server_executable"] = str(
                    Path(settings["server_executable"]).resolve())
        else:
            self.config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
            self.provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
        model_path = (Path(self.config["model_dir"]) /
                      self.config["model_file"]).resolve()
        model_stat = model_path.stat()
        if _model_digest(model_path, model_stat.st_size, model_stat.st_mtime_ns) != \
                self.provenance["model_sha256"]:
            raise ValueError("Model checksum differs from frozen provenance")
        self.url = (url or os.environ.get("QWEN_BASE_URL") or
                    f"http://127.0.0.1:{self.config['port']}").rstrip("/")
        self.launch_local = launch_local and not (url or os.environ.get("QWEN_BASE_URL"))
        self.monitor = monitor
        self.session = requests.Session()
        self.session.trust_env = False
        self.runtime = None

    @property
    def name(self):
        return self.provenance["model"]

    @property
    def version(self):
        return self.provenance["model_sha256"]

    def __enter__(self):
        try:
            live = self.session.get(self.url + "/health", timeout=2).status_code == 200
        except requests.RequestException:
            live = False
        if not live:
            if not self.launch_local:
                raise RuntimeError("Model endpoint is unavailable")
            self.runtime = LocalQwen(self.config, self.provenance)
            self.runtime.__enter__()
        return self

    def __exit__(self, *args):
        if self.runtime:
            self.runtime.__exit__(*args)
        self.session.close()

    def generate(self, *, system, user, response_schema, prompt_version,
                 max_new_tokens=256, component="rag_generation", audit_sink=None,
                 temperature=0, retries=0, timeout_seconds=120):
        start = perf_counter()
        usage = {}
        status = "error_or_invalid_json"
        task = ("text_to_sql" if "text_to_sql" in component else
                "cross" if "cross" in component else "review")
        error_category = None
        try:
            payload = {
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": temperature, "seed": 42, "max_tokens": max_new_tokens,
                "stream": False, "cache_prompt": False,
                "response_format": {"type": "json_schema", "schema": response_schema},
            }
            for attempt in range(retries + 1):
                try:
                    response = self.session.post(self.url + "/v1/chat/completions",
                                                 json=payload, timeout=timeout_seconds)
                    response.raise_for_status()
                    break
                except requests.RequestException:
                    if attempt == retries:
                        raise
            data = response.json()
            raw = data["choices"][0]["message"]["content"]
            if audit_sink is not None:
                audit_sink.append({"raw_output": raw})
            usage = data.get("usage", {})
            value = json.loads(raw, object_pairs_hook=_unique_keys)
            status = "valid_json"
            return value, {"input_tokens": usage.get("prompt_tokens"),
                           "output_tokens": usage.get("completion_tokens"),
                           "latency_ms": (perf_counter() - start) * 1000,
                           "status": status}
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            status = "error_or_invalid_json"
            error_category = type(error).__name__
            security_event("model_gateway", error_category, model_id=self.model_id)
            raise
        finally:
            if self.monitor:
                record(component, self.name, self.version, prompt_version,
                       (perf_counter() - start) * 1000, status,
                       input_tokens=usage.get("prompt_tokens"),
                       output_tokens=usage.get("completion_tokens"),
                       model_id=self.model_id, task_type=task,
                       fallback_status="not_at_gateway", failure_category=error_category)
                observe_model_gateway(self.model_id, task, status,
                                      perf_counter() - start,
                                      usage.get("prompt_tokens"),
                                      usage.get("completion_tokens"),
                                      error_category in {
                                          "ValueError", "KeyError", "TypeError"})

    def health(self, timeout=2):
        """Check the selected endpoint without launching or loading a model."""
        try:
            return self.session.get(self.url + "/health", timeout=timeout).status_code == 200
        except requests.RequestException:
            return False


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result
