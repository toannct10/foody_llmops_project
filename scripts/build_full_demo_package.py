"""Stage the current full offline Docker demo and build its ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "Foody_Intelligence_Full_Demo_With_Models"
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache", ".locks", "logs", "node_modules", "tmp", "temp"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log", ".sqlite-wal", ".sqlite-shm"}
SOURCE_DIRS = ("src", "app", "scripts", "tests", "dags", "dbt", "sql", "prompts", "config", "docs", "devops", "reports")
SOURCE_FILES = ("pyproject.toml", "README.md", ".dockerignore", ".env.example", "setup_demo.ps1", "start_demo.ps1", "stop_demo.ps1", "reset_demo.ps1")
DATA_FILES = (
    "data/foody/source/order_cleaning.csv",
    "data/foody/source/data_2025_2026.csv",
    "data/foody/processed/reviews_2025_2026_enriched.parquet",
    "data/foody/processed/reviews_2025_2026.parquet",
    "data/foody/processed/reviews_2025_2026_manifest.json",
    "data/foody/rag/reviews_2025_2026.jsonl",
    "data/foody/enriched/reviews.parquet",
    "database/foody.dump",
)
DATA_DIRS = ("data/foody/vector_store_review_2025_2026", "data/foody/lexical_index_review_2025_2026", "data/foody/mart")
MODEL_FILES = ("models/tfidf_logreg.joblib", "models/aspect_tfidf.joblib", "models/qwen_v3/qwen2.5-3b-instruct-q4_k_m.gguf", "models/qwen_v3/provenance.json")
MODEL_DIRS = ("models/phobert_absa", "models/embeddings")


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def copy_tree(relative: str, stage: Path) -> None:
    source = ROOT / relative
    if not source.is_dir():
        raise FileNotFoundError(source)
    for file in source.rglob("*"):
        if not file.is_file() or any(part in EXCLUDE_DIRS for part in file.relative_to(source).parts):
            continue
        if file.suffix in EXCLUDE_SUFFIXES or file.name.startswith(".env"):
            continue
        copy_file(file, stage / file.relative_to(ROOT))


def size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    stage = output_dir / NAME
    archive = output_dir / f"{NAME}.zip"
    if stage.exists() or archive.exists():
        raise FileExistsError("Stage or ZIP exists; inspect it before replacing")
    stage.mkdir(parents=True)
    try:
        for relative in SOURCE_DIRS:
            copy_tree(relative, stage)
        for pattern in ("Dockerfile*", "docker-compose*.yml", "requirements*.txt", "qwen_*.yaml"):
            for file in ROOT.glob(pattern):
                copy_file(file, stage / file.name)
        for relative in SOURCE_FILES + DATA_FILES + MODEL_FILES:
            copy_file(ROOT / relative, stage / relative)
        for relative in DATA_DIRS + MODEL_DIRS:
            copy_tree(relative, stage)
        provenance = stage / "models/qwen_v3/provenance.json"
        metadata = json.loads(provenance.read_text(encoding="utf-8"))
        metadata["server_executable"] = "docker:qwen"
        provenance.unlink()  # break hard link; do not modify the source provenance
        provenance.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lexical_manifest = stage / "data/foody/lexical_index_review_2025_2026/index_manifest.json"
        lexical_metadata = json.loads(lexical_manifest.read_text(encoding="utf-8"))
        lexical_metadata["path"] = "data/foody/lexical_index_review_2025_2026/reviews.sqlite"
        lexical_manifest.unlink()  # break hard link; preserve source index metadata
        lexical_manifest.write_text(json.dumps(lexical_metadata, ensure_ascii=False,
                                               indent=2) + "\n", encoding="utf-8")
        (stage / "DEMO_README.md").write_text(
            "# Foody Intelligence full local demo\n\n"
            "Requires Docker Desktop with Compose, PowerShell 7, at least 16 GB RAM and 10 GB free disk space. "
            "The first setup builds CPU images and restores PostgreSQL from the included dump; it needs no model download.\n\n"
            "From this extracted folder in PowerShell:\n\n"
            "```powershell\nSet-ExecutionPolicy -Scope Process Bypass\n.\\setup_demo.ps1\n```\n\n"
            "Open http://localhost:8501. API: http://localhost:8000; Grafana: http://localhost:3000; "
            "Prometheus: http://localhost:9090. Local credentials are generated in .env.demo during setup.\n\n"
            "Later: `.\\start_demo.ps1`; stop: `.\\stop_demo.ps1`; reset isolated demo volumes: "
            "`.\\reset_demo.ps1 -ConfirmReset`. Optional Airflow: `.\\setup_demo.ps1 -WithAirflow`.\n\n"
            "Cross Intelligence supports an inferred previous month for a dated change question. "
            "For example, a June 2025 revenue and negative-review comparison uses May 2025 "
            "as its baseline; a month without a year requires clarification.\n",
            encoding="utf-8",
        )
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                check=True, capture_output=True, text=True).stdout.strip()
        cross_sha = hashlib.sha256(
            (stage / "src/sales/cross_intelligence.py").read_bytes()).hexdigest()
        stage_bytes = size(stage)
        file_count = sum(1 for p in stage.rglob("*") if p.is_file()) + 1
        manifest = stage / "PACKAGE_MANIFEST.txt"
        manifest.write_text(
            f"Package: {NAME}\nFiles: {file_count}\nStage bytes: {stage_bytes}\n"
            f"Source HEAD: {commit}\n"
            f"Packaged Cross source SHA256: {cross_sha}\n"
            "Source state: current working tree, including uncommitted files.\n"
            f"PhoBERT bytes: {size(stage / 'models/phobert_absa')}\n"
            f"Qwen bytes: {(stage / MODEL_FILES[2]).stat().st_size}\n"
            "Models: Qwen2.5-3B GGUF; TF-IDF sentiment/aspect; PhoBERT ABSA; MiniLM ONNX.\n"
            "Data: 400,000-order Sales source; 15,456 Review source/enriched parquet.\n"
            "Database: PostgreSQL custom-format dump with migration 005, views and marts.\n"
            "RAG: accepted 15,454-document Chroma and BM25 indexes.\n"
            "Source: src, app, scripts, tests, dags, dbt, sql, prompts, config, docs, devops.\n"
            "ZIP bytes: see adjacent ZIP file size after creation.\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as out:
            for file in sorted(stage.rglob("*")):
                if file.is_file():
                    out.write(file, Path(NAME) / file.relative_to(stage))
        with zipfile.ZipFile(archive) as check:
            bad = check.testzip()
            if bad:
                raise ValueError(f"ZIP corrupt: {bad}")
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        print(f"stage={stage}\nzip={archive}\nfiles={file_count}\nzip_bytes={archive.stat().st_size}\nsha256={digest.hexdigest()}")
    except Exception:
        if archive.exists():
            archive.unlink()
        raise


if __name__ == "__main__":
    main()
