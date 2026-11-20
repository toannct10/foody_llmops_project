"""Transparent, offline resource summaries from existing LLMOps generation events."""

import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LOG = Path("state/llmops.sqlite")
MODELS = {"qwen", "llama", "deepseek"}
TASKS = {"text_to_sql", "review", "cross", "benchmark"}


def _rate(name):
    try:
        value = float(os.getenv(name, ""))
        return value if 0 <= value < 1_000_000 else None
    except ValueError:
        return None


def cost_config():
    device = os.getenv("LOCAL_INFERENCE_DEVICE", "").lower()
    return {"enabled": os.getenv("COST_TRACKING_ENABLED", "false").lower() == "true",
            "device": device if device in {"cpu", "gpu"} else None,
            "cpu_rate_per_hour": _rate("LOCAL_CPU_COST_PER_HOUR"),
            "gpu_rate_per_hour": _rate("LOCAL_GPU_COST_PER_HOUR"),
            "snowflake_credit_price": _rate("SNOWFLAKE_CREDIT_PRICE"),
            "aws_estimate_mode": os.getenv("AWS_ESTIMATE_MODE", "disabled")}


def _model(row):
    if row["model_id"] in MODELS:
        return row["model_id"]
    name = (row["model_name"] or "").casefold()
    return next((model for model in MODELS if model in name), "other")


def _task(row):
    if row["task_type"] in TASKS:
        return row["task_type"]
    component = row["component"].casefold()
    if "text_to_sql" in component:
        return "text_to_sql"
    if "cross" in component:
        return "cross"
    if "benchmark" in component:
        return "benchmark"
    return "review"


def _blank():
    return {"request_count": 0, "input_tokens": 0, "output_tokens": 0,
            "generation_seconds": 0.0}


def _add(target, row):
    target["request_count"] += 1
    target["input_tokens"] += max(int(row["input_tokens"] or 0), 0)
    target["output_tokens"] += max(int(row["output_tokens"] or 0), 0)
    target["generation_seconds"] += max(float(row["latency_ms"] or 0), 0) / 1000


def _finish(value, config):
    count = value["request_count"]
    result = {**value, "total_tokens": value["input_tokens"] + value["output_tokens"],
              "avg_tokens_per_request": (value["input_tokens"] + value["output_tokens"]) /
              count if count else None,
              "estimated_cpu_seconds": None, "estimated_gpu_seconds": None,
              "estimated_local_cost": None, "cost_status": "NOT_CONFIGURED"}
    if config["device"]:
        result[f"estimated_{config['device']}_seconds"] = value["generation_seconds"]
    rate = config[f"{config['device']}_rate_per_hour"] if config["device"] else None
    if config["enabled"] and rate is not None:
        result["estimated_local_cost"] = round(value["generation_seconds"] * rate / 3600, 6)
        result["cost_status"] = "ESTIMATE"
    return result


def resource_summary(path=LOG):
    """Count generation calls once; exclude request-level rows that duplicate tokens."""
    config = cost_config()
    totals = _blank()
    groups = {name: defaultdict(_blank) for name in ("daily", "weekly", "model", "task")}
    if Path(path).exists():
        with sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            columns = {row[1] for row in db.execute("PRAGMA table_info(events)")}
            if not columns:
                return {"total": _finish(totals, config), "daily": {}, "weekly": {},
                        "model": {}, "task": {},
                        "cloud": {"aws_actual_cost": None, "snowflake_actual_cost": None,
                                  "status": "NOT_CONFIGURED"},
                        "assumption": "No generation events recorded"}
            model_id = "model_id" if "model_id" in columns else "NULL AS model_id"
            task_type = "task_type" if "task_type" in columns else "NULL AS task_type"
            rows = db.execute(f"SELECT timestamp,component,model_name,{model_id},{task_type},"
                              "latency_ms,input_tokens,output_tokens FROM events "
                              "WHERE component LIKE '%_generation' ORDER BY id")
            for row in rows:
                _add(totals, row)
                when = datetime.fromisoformat(row["timestamp"])
                week = when.isocalendar()
                for name, key in (("daily", when.date().isoformat()),
                                  ("weekly", f"{week.year}-W{week.week:02d}"),
                                  ("model", _model(row)), ("task", _task(row))):
                    _add(groups[name][key], row)
    return {"total": _finish(totals, config),
            **{name: {key: _finish(value, config) for key, value in sorted(group.items())}
               for name, group in groups.items()},
            "cloud": {"aws_actual_cost": None, "snowflake_actual_cost": None,
                      "status": "NOT_CONFIGURED"},
            "assumption": ("Generation wall time is a device-runtime proxy only when "
                           "LOCAL_INFERENCE_DEVICE is explicitly set. Monetary values "
                           "are estimates only when enabled with a rate.")}
