"""One-time freeze of the existing twelve questions and independent SQL facts."""

import json
import subprocess

from src.model_benchmark.dataset import MANIFEST, freeze_manifest
from src.warehouse.loader import connection


def main():
    if MANIFEST.exists():
        raise SystemExit(f"Frozen manifest already exists: {MANIFEST}")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip()
    with connection() as conn:
        manifest = freeze_manifest(conn, restaurant_id="2751", git_commit=commit)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"Frozen {len(manifest['cases'])} cases: {manifest['dataset_sha256']}")


if __name__ == "__main__":
    main()
