"""Persist bounded security categories in the existing LLMOps SQLite ledger."""

import re
import sqlite3

from src.rag.monitoring import record

SAFE_TOKEN = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}\Z")


def _safe(value):
    normalized = str(value).lower()
    return normalized if SAFE_TOKEN.fullmatch(normalized) else "unspecified"


def _safe_id(value):
    normalized = str(value).lower()
    return normalized if SAFE_ID.fullmatch(normalized) else "unspecified"


def security_event(component, category, *, status="failed", request_id=None, model_id=None):
    """Never accept free-form errors, questions, SQL, paths or credentials as audit fields."""
    component = _safe(component)
    category = _safe(category)
    status = _safe(status)
    request_id = _safe_id(request_id) if request_id is not None else None
    model_id = _safe(model_id) if model_id is not None else None
    try:
        record(component, None, None, None, 0, status,
               failure_category=category, request_id=request_id,
               model_id=model_id, task_type="security")
    except (OSError, sqlite3.Error):
        # Audit storage must not replace the original security failure.
        pass
