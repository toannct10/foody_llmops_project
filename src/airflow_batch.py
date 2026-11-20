"""Reusable local Foody batch stages called by the Airflow DAG.

The active Review corpus and indexes are immutable: unchanged batches verify
and reuse them; changed active index content fails closed before publication.
"""

import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pandas as pd

from src.foody.review_paths import CANONICAL, DOCUMENTS, ENRICHED, MANIFEST, SOURCE
from src.foody.schema import digest
from src.sales.audit import SOURCE as SALES_SOURCE

RUNS = Path("outputs/airflow/runs")
READY = Path("outputs/airflow/ready.json")
BAD_FIXTURE = Path("tests/fixtures/airflow/invalid_review_schema.csv")
STAGES = (
    "detect_source_data", "validate_source", "prepare_or_load_data",
    "transform_data", "data_quality_gate", "update_marts",
    "review_enrichment", "update_rag_indexes", "run_evaluation", "publish_ready",
)


def _now():
    return datetime.now(UTC).isoformat()


def _git_commit():
    if configured := os.getenv("GIT_SHA"):
        return configured
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL, timeout=3).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def summary_path(run_id):
    key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:20]
    return RUNS / f"{key}.json"


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def read_summary(run_id):
    return json.loads(summary_path(run_id).read_text(encoding="utf-8"))


def review_source(quality_fixture=None):
    if quality_fixture is None:
        return SOURCE
    if quality_fixture != "invalid_review_schema":
        raise ValueError("Unknown quality fixture")
    return BAD_FIXTURE


def detect_source_data(summary, *, quality_fixture=None):
    source = review_source(quality_fixture)
    review_hash, sales_hash = digest(source), digest(SALES_SOURCE)
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    unchanged = (existing.get("source_sha256") == review_hash and ENRICHED.exists()
                 and DOCUMENTS.exists())
    batch_id = hashlib.sha256(f"{review_hash}:{sales_hash}".encode()).hexdigest()[:20]
    summary.update({"batch_id": batch_id, "source_hashes": {
        "review": review_hash, "sales": sales_hash},
        "source_version": existing.get("data_version"),
        "quality_fixture": quality_fixture})
    return {"status": "SKIPPED_DUPLICATE" if unchanged else "NEW",
            "batch_id": batch_id, "review_source": str(source),
            "review_source_sha256": review_hash, "sales_source_sha256": sales_hash}


def validate_source(summary, *, quality_fixture=None):
    from src.foody.review_migration import (
        align_ids,
        audit_source,
        read_source,
        require_accepted,
    )
    from src.sales.audit import audit_orders, read_orders, require_loadable

    source = review_source(quality_fixture)
    reviews = read_source(source)
    orders = read_orders(SALES_SOURCE)
    review_audit = audit_source(reviews)
    sales_audit = audit_orders(SALES_SOURCE)
    alignment = align_ids(reviews, orders)
    require_loadable(sales_audit)
    require_accepted(review_audit, alignment)
    if not reviews.Comment.fillna("").map(lambda value: bool(value.strip())).any():
        raise ValueError("Review source contains no non-empty comments")
    return {"status": "SUCCESS", "sales_rows": sales_audit["rows"],
            "review_rows": review_audit["rows"],
            "review_exact_duplicates": review_audit["exact_duplicate_rows"],
            "review_restaurants": review_audit["unique_restaurant_ids"],
            "review_date_max": review_audit["date_max"],
            "id_alignment": alignment["direct_join_accepted"],
            "failed_rows": 0}


def prepare_or_load_data(summary, *, quality_fixture=None):
    from src.foody.review_migration import prepare
    from src.foody.review_runtime import LEXICAL, VECTOR

    source = review_source(quality_fixture)
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    if (old.get("source_sha256") == summary["source_hashes"]["review"]
            and CANONICAL.exists() and ENRICHED.exists() and DOCUMENTS.exists()
            and old.get("documents", {}).get("sha256") == digest(DOCUMENTS)):
        return {"status": "SKIPPED_DUPLICATE", "review_rows": old["row_count"],
                "documents": old["documents"]["document_count"]}
    if ((VECTOR / "index_manifest.json").exists() or
            (LEXICAL / "index_manifest.json").exists()):
        raise ValueError("Changed Review source requires a versioned index rollout before preparation")
    manifest = prepare(source)
    return {"status": "REPROCESSED", "review_rows": manifest["row_count"],
            "documents": manifest["documents"]["document_count"]}


def transform_data(summary, **_):
    """Verify the canonical/JSONL products of the existing preparation call."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if len(pd.read_parquet(CANONICAL, columns=["review_id"])) != manifest["row_count"]:
        raise ValueError("Canonical Review row count differs from manifest")
    with DOCUMENTS.open(encoding="utf-8") as stream:
        document_count = sum(1 for _ in stream)
    if document_count != manifest["documents"]["document_count"]:
        raise ValueError("RAG document count differs from manifest")
    return {"status": "SUCCESS", "canonical_rows": manifest["row_count"],
            "document_count": document_count}


def data_quality_gate(summary, **_):
    from src.foody.review_migration import DATA_VERSION

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    frame = pd.read_parquet(ENRICHED)
    required = {"review_id", "restaurant_id", "review_time", "rating", "comment",
                "predicted_sentiment", "predicted_aspects"}
    if not required.issubset(frame.columns):
        raise ValueError("Enriched Review schema is missing required columns")
    if (manifest["data_version"] != DATA_VERSION or
            manifest["source_sha256"] != summary["source_hashes"]["review"] or
            manifest["row_count"] != len(frame) or frame.review_id.isna().any() or
            frame.review_id.duplicated().any() or frame.restaurant_id.isna().any() or
            frame.review_time.isna().any() or frame.rating.isna().any() or
            frame.comment.isna().any() or frame.predicted_aspects.isna().any() or
            frame.rating.lt(0).any() or frame.rating.gt(10).any() or
            frame.predicted_sentiment.isna().any() or
            not frame.predicted_sentiment.isin({"negative", "neutral", "positive"}).all() or
            manifest["documents"]["sha256"] != digest(DOCUMENTS)):
        raise ValueError("Critical Review quality, source freshness or business rule failed")
    if not pd.api.types.is_datetime64_any_dtype(frame.review_time):
        raise ValueError("Review date type is invalid")
    for key, path in (("sentiment_model_sha256", "models/tfidf_logreg.joblib"),
                      ("aspect_model_sha256", "models/aspect_tfidf.joblib")):
        if manifest[key] != digest(path):
            raise ValueError("Frozen classifier artifact changed")
    return {"status": "PASS", "review_rows": len(frame),
            "duplicates": 0, "failed_rows": 0,
            "source_current": True, "model_hashes_match": True}


def update_marts(summary, **_):
    from src.sales.loader import load_sales
    from src.warehouse.loader import connection, migrate
    from src.warehouse.review_loader import load as load_reviews

    sales = load_sales()
    with connection() as conn:
        migrate(conn)
        review = load_reviews(conn)
        counts = {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for name in ("fact_order", "fact_review_v2", "restaurant_monthly_sales")}
    if counts["fact_order"] != sales["orders"] or counts["fact_review_v2"] != review["reviews"]:
        raise ValueError("Warehouse fact counts do not reconcile")
    return {"status": "SKIPPED_DUPLICATE" if
            sales["status"] == review["status"] == "unchanged" else "REPROCESSED",
            "sales": sales, "reviews": review, "mart_counts": counts}


def review_enrichment(summary, **_):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (manifest["sentiment_enrichment_count"] != manifest["row_count"] or
            manifest["aspect_enrichment_count"] != manifest["row_count"]):
        raise ValueError("Review enrichment count is incomplete")
    prepared = summary["tasks"]["prepare_or_load_data"]["result"]["status"]
    return {"status": "SKIPPED_DUPLICATE" if prepared == "SKIPPED_DUPLICATE"
            else "REPROCESSED", "sentiment_rows": manifest["sentiment_enrichment_count"],
            "aspect_rows": manifest["aspect_enrichment_count"], "qwen_loaded": False}


def update_rag_indexes(summary, **_):
    from src.foody.review_runtime import LEXICAL, VECTOR
    from src.rag.vector_store import open_collection

    source_hash = digest(DOCUMENTS)
    vector_manifest = VECTOR / "index_manifest.json"
    lexical_manifest = LEXICAL / "index_manifest.json"
    built = False
    if not vector_manifest.exists() and not lexical_manifest.exists():
        from scripts.build_review_2025_2026_index import main as build_indexes

        build_indexes()
        built = True
    if not vector_manifest.exists() or not lexical_manifest.exists():
        raise ValueError("Only one RAG index exists")
    vector = json.loads(vector_manifest.read_text(encoding="utf-8"))
    lexical = json.loads(lexical_manifest.read_text(encoding="utf-8"))
    if (vector["documents_sha256"] != source_hash or
            lexical["source_sha256"] != source_hash):
        raise ValueError("Active RAG index source changed; versioned index switch required")
    collection, _ = open_collection(vector_manifest, VECTOR)
    with sqlite3.connect(LEXICAL / "reviews.sqlite") as db:
        lexical_count = db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    count = vector["document_count"]
    if collection.count() != lexical_count or count != lexical_count:
        raise ValueError("Chroma and BM25 counts differ")
    return {"status": "REPROCESSED" if built else "SKIPPED_DUPLICATE",
            "vector_count": count,
            "bm25_count": lexical_count, "documents_sha256": source_hash}


def run_evaluation(summary, **_):
    from src.warehouse.loader import connection

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    index = summary["tasks"]["update_rag_indexes"]["result"]
    with connection() as conn:
        orders = conn.execute("SELECT COUNT(*) FROM fact_order").fetchone()[0]
        reviews = conn.execute("SELECT COUNT(*) FROM fact_review_v2").fetchone()[0]
        monthly = conn.execute("SELECT COUNT(*) FROM restaurant_monthly_sales").fetchone()[0]
    checks = {
        "sales_mart": orders == summary["tasks"]["update_marts"]["result"]["sales"]["orders"],
        "review_mart": reviews == manifest["row_count"],
        "rag_documents": index["vector_count"] == index["bm25_count"] ==
                         manifest["documents"]["document_count"],
        "monthly_mart": monthly > 0,
    }
    if not all(checks.values()):
        raise ValueError("Lightweight warehouse/RAG evaluation failed")
    return {"status": "PASS", "checks": checks, "sales_rows": orders,
            "review_rows": reviews, "monthly_mart_rows": monthly,
            "model_benchmark_rerun": False, "qwen_generation_run": False}


def publish_ready(summary, **_):
    critical = ("validate_source", "data_quality_gate", "update_marts",
                "review_enrichment", "update_rag_indexes", "run_evaluation")
    if any(summary["tasks"].get(name, {}).get("status") not in {
            "SUCCESS", "PASS", "SKIPPED_DUPLICATE", "REPROCESSED"}
           for name in critical):
        raise ValueError("Critical stage did not pass; ready state withheld")
    ready = {"dag_run_id": summary["dag_run_id"], "batch_id": summary["batch_id"],
             "source_hashes": summary["source_hashes"], "published_at_utc": _now(),
             "data_quality_status": "PASS", "evaluation_status": "PASS"}
    _write(READY, ready)
    return {"status": "SUCCESS", "ready_path": str(READY)}


ACTIONS = {name: globals()[name] for name in STAGES}


def execute_stage(stage, *, run_id, logical_date, quality_fixture=None):
    """Run one Airflow stage and atomically persist a content-free run ledger."""
    if stage not in ACTIONS:
        raise ValueError("Unknown batch stage")
    path = summary_path(run_id)
    if stage == STAGES[0]:
        summary = {"dag_run_id": run_id, "logical_date": logical_date,
                   "started_at_utc": _now(), "ended_at_utc": None,
                   "status": "RUNNING", "git_commit": _git_commit(),
                   "tasks": {}, "source_hashes": {}, "batch_id": None,
                   "processed_rows": 0, "failed_rows": 0, "duplicate_rows": 0}
    else:
        summary = read_summary(run_id)
    started = perf_counter()
    try:
        result = ACTIONS[stage](summary, quality_fixture=quality_fixture)
        summary["tasks"][stage] = {"status": result["status"],
                                   "duration_seconds": round(perf_counter() - started, 3),
                                   "result": result}
        if stage == "validate_source":
            summary["processed_rows"] = result["sales_rows"] + result["review_rows"]
            summary["duplicate_rows"] = result["review_exact_duplicates"]
        if stage == "data_quality_gate":
            summary["data_quality_status"] = "PASS"
        if stage == "update_marts":
            summary["mart_update_status"] = result["status"]
        if stage == "update_rag_indexes":
            summary["rag_index_update_status"] = result["status"]
        if stage == "run_evaluation":
            summary["evaluation_status"] = "PASS"
        if stage == "publish_ready":
            summary["status"] = "SUCCESS"
            summary["ended_at_utc"] = _now()
            summary["duration_seconds"] = round((datetime.fromisoformat(
                summary["ended_at_utc"]) - datetime.fromisoformat(
                summary["started_at_utc"])).total_seconds(), 3)
    except Exception as error:
        if stage == "data_quality_gate":
            from src.security.audit import security_event

            security_event("airflow_quality_gate", type(error).__name__,
                           status="blocked", request_id=run_id)
        summary["tasks"][stage] = {"status": "FAILED",
                                   "duration_seconds": round(perf_counter() - started, 3),
                                   "error_category": type(error).__name__,
                                   "reason": type(error).__name__}
        for later in STAGES[STAGES.index(stage) + 1:]:
            summary["tasks"].setdefault(later, {"status": "BLOCKED_UPSTREAM"})
        summary["status"] = "FAILED"
        summary["failed_stage"] = stage
        summary["ended_at_utc"] = _now()
        summary["duration_seconds"] = round((datetime.fromisoformat(
            summary["ended_at_utc"]) - datetime.fromisoformat(
            summary["started_at_utc"])).total_seconds(), 3)
        if stage == "validate_source" and quality_fixture == "invalid_review_schema":
            summary["failed_rows"] = max(
                sum(1 for _ in BAD_FIXTURE.open(encoding="utf-8")) - 1, 0)
        _write(path, summary)
        raise
    _write(path, summary)
    return result
