"""Overlay the PhoBERT ABSA runtime into an existing portable-demo staging tree.

Run before creating the ZIP. This only copies the new model/runtime files and
does not remove or rebuild any other packaged artifact.
"""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHOBERT_FILES = (
    "models/phobert_absa/absa.pt",
    "models/phobert_absa/absa_config.json",
    "models/phobert_absa/absa_test_metrics.json",
    "models/phobert_absa/history.csv",
    "models/phobert_absa/relevance.joblib",
    "models/phobert_absa/relevance_config.json",
    "models/phobert_absa/relevance_proxy_metrics.json",
)
RUNTIME_FILES = (
    "Dockerfile.rag",
    "requirements-phobert-absa.txt",
    "src/ui/review_analysis_view.py",
    "src/foody/review_models/__init__.py",
    "src/foody/review_models/base.py",
    "src/foody/review_models/registry.py",
    "src/foody/review_models/tfidf_adapter.py",
    "src/foody/review_models/phobert_absa_adapter.py",
)


def stage_phobert_bundle(stage_root: Path) -> dict:
    target = stage_root.resolve()
    if target == ROOT:
        raise ValueError("Use a separate portable-demo staging directory")
    files = (*PHOBERT_FILES,
             *(str(path.relative_to(ROOT)).replace("\\", "/") for directory in
               (ROOT / "models/phobert_absa/tokenizer",
                ROOT / "models/phobert_absa/backbone_config")
               for path in directory.rglob("*") if path.is_file()),
             *RUNTIME_FILES)
    for name in files:
        source = ROOT / name
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(f"Missing or unsafe bundle file: {name}")
    total_bytes = 0
    for name in files:
        source = ROOT / name
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        total_bytes += source.stat().st_size
    return {"files": len(files), "uncompressed_bytes": total_bytes,
            "checkpoint_bytes": (ROOT / PHOBERT_FILES[0]).stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage_root", type=Path)
    result = stage_phobert_bundle(parser.parse_args().stage_root)
    print(f"Staged {result['files']} PhoBERT runtime files; "
          f"{result['uncompressed_bytes']:,} bytes uncompressed")


if __name__ == "__main__":
    main()
