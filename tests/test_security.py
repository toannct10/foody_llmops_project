"""Security boundaries that can be verified without cloud credentials."""

from pathlib import Path

import pytest

from scripts.security_scan import private_path, scan_file
from src.security import audit
from src.warehouse import loader

ROOT = Path(__file__).resolve().parents[1]


def test_postgres_ai_role_exposes_only_approved_views():
    sql = (ROOT / "sql/postgres/readonly.sql").read_text().lower()
    assert "create role foody_ai_readonly login nosuperuser nocreatedb nocreaterole" in sql
    assert "revoke all on schema ai_sales from public" in sql
    assert "grant usage on schema ai_sales to foody_ai_readonly" in sql
    grants = sql.split("grant select on ai_sales.", 1)[1].split("to foody_ai_readonly", 1)[0]
    assert all(name in grants for name in ("restaurant_monthly_sales",
                                             "restaurant_weekly_sales",
                                             "restaurant_sales_summary",
                                             "dim_sales_restaurant"))
    assert "fact_order" not in grants and "fact_review" not in grants
    assert "grant insert" not in sql and "grant update" not in sql
    assert "grant delete" not in sql and "grant create" not in sql


def test_ai_connection_uses_optional_dsn_and_compatible_fallback(monkeypatch):
    sentinel = object()
    monkeypatch.delenv("FOODY_AI_DATABASE_URL", raising=False)
    monkeypatch.setattr(loader, "connection", lambda: sentinel)
    assert loader.ai_connection() is sentinel
    import psycopg

    seen = []
    monkeypatch.setattr(psycopg, "connect", lambda dsn: seen.append(dsn) or sentinel)
    monkeypatch.setenv("FOODY_AI_DATABASE_URL", "postgresql://readonly:private@host/db")
    assert loader.ai_connection() is sentinel
    assert seen == ["postgresql://readonly:private@host/db"]


def test_snowflake_ai_role_has_explicit_mart_allowlist():
    bootstrap = (ROOT / "sql/snowflake/bootstrap.sql").read_text().upper()
    grants = (ROOT / "sql/snowflake/grant_ai_readonly.sql").read_text().upper()
    assert "GRANT SELECT ON FUTURE TABLES" not in bootstrap
    assert "GRANT SELECT ON FUTURE VIEWS" not in bootstrap
    assert "GRANT SELECT ON VIEW FOODY.MART.RESTAURANT_MONTHLY_SALES" in grants
    assert "GRANT SELECT ON TABLE FOODY.MART.DIM_RESTAURANT" in grants
    assert "FACT_REVIEW" not in grants and "FOODY.RAW." not in grants
    assert "GRANT INSERT" not in grants and "GRANT CREATE" not in grants


def test_iam_policy_has_prefix_and_no_delete_or_admin():
    text = (ROOT / "docs/cloud/AWS_IAM_POLICY.md").read_text()
    assert "arn:aws:s3:::YOUR_BUCKET/foody/raw/*" in text
    assert '"s3:PutObject"' in text and '"s3:GetObject"' in text
    assert '"s3:DeleteObject"' not in text
    assert '"Action": "*"' not in text


def test_secret_scan_reports_category_without_secret_value(tmp_path):
    key = "AKIA" + "A" * 16  # synthetic signature, never a usable credential
    sample = tmp_path / "sample.py"
    sample.write_text(f"KEY = '{key}'")
    assert scan_file(sample) == ["aws_access_key"]
    assert private_path(Path(".env.cloud"))
    assert private_path(Path("models/private.gguf"))
    assert not private_path(Path(".env.example"))


def test_security_audit_discards_unbounded_reason_and_request_id(monkeypatch):
    captured = []
    monkeypatch.setattr(audit, "record", lambda *args, **kwargs:
                        captured.append((args, kwargs)))
    secret = "postgresql://user:password@host/db"
    audit.security_event("text_to_sql", secret, request_id=secret)
    args, kwargs = captured[0]
    assert args[0] == "text_to_sql"
    assert kwargs["failure_category"] == "unspecified"
    assert kwargs["request_id"] == "unspecified"
    assert secret not in str(captured)


def test_review_api_does_not_expose_internal_error(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import api
    from src.foody import review_runtime

    secret = "postgresql://user:password@host/db"
    monkeypatch.setattr(review_runtime, "new_corpus_active",
                        lambda: (_ for _ in ()).throw(ValueError(secret)))
    response = TestClient(api).post("/ask-v3", json={"question": "review", "restaurant": "x"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Review service unavailable"}
    assert secret not in response.text


@pytest.mark.parametrize("status", ["rejected", "failed", "blocked"])
def test_security_audit_sqlite_has_run_id(tmp_path, monkeypatch, status):
    from src.rag.monitoring import record

    path = tmp_path / "llmops.sqlite"
    monkeypatch.setattr(audit, "record", lambda *args, **kwargs:
                        record(*args, **kwargs, path=path))
    audit.security_event("cloud_dbt", "quality_gate_failed", status=status,
                         request_id="run_123")
    import sqlite3

    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT component, failure_category, status, request_id "
                           "FROM events").fetchone()
    assert row == ("cloud_dbt", "quality_gate_failed", status, "run_123")


def test_security_audit_preserves_generated_numeric_batch_id(monkeypatch):
    observed = []
    monkeypatch.setattr(audit, "record", lambda *args, **kwargs: observed.append(kwargs))
    audit.security_event("cloud_ingestion", "valueerror", request_id="0123abcdef")
    assert observed[0]["request_id"] == "0123abcdef"
