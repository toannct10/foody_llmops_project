"""Read-only documentation inventory; never imports project runtime modules."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "scripts" / "documentation" / ".qa"
TEXT = {".py", ".md", ".json", ".csv", ".yaml", ".yml", ".toml", ".txt", ".cmd", ".ps1"}


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def snapshot():
    paths = set()
    for folder in (
        "src",
        "app",
        "scripts",
        "tests",
        "databricks",
        ".github",
        "config",
        "prompts",
        "reports",
        "docs/experiments",
        "data",
        "models",
    ):
        paths.update(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and "documentation" not in p.parts
        )
    paths.update(
        p
        for p in ROOT.iterdir()
        if p.is_file() and p.name != ".env" and p.suffix not in {".sqlite", ".log"}
    )
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


def audit():
    inventory = []
    folders = (
        "src",
        "app",
        "scripts",
        "tests",
        "databricks",
        ".github",
        "config",
        "prompts",
        "reports",
        "docs/experiments",
    )
    paths = {
        p
        for folder in folders
        for p in (ROOT / folder).rglob("*")
        if p.is_file()
        and p.suffix in TEXT
        and "__pycache__" not in p.parts
        and "documentation" not in p.parts
    }
    paths.update(
        p
        for p in ROOT.iterdir()
        if p.is_file()
        and (p.suffix in TEXT or p.name.startswith("Dockerfile") or p.name == ".gitignore")
        and not p.name.startswith(".env")
    )
    for path in sorted(paths):
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        row = {
            "file": path.relative_to(ROOT).as_posix(),
            "sha256": digest(path),
            "lines": len(text.splitlines()),
            "characters": len(text),
            "symbols": [],
            "imports": [],
        }
        if path.suffix == ".py":
            tree = ast.parse(text)
            row["docstring"] = ast.get_docstring(tree) or ""
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    row["imports"].append(node.module or "")
                elif isinstance(node, ast.Import):
                    row["imports"].extend(n.name for n in node.names)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    row["symbols"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "kind": type(node).__name__,
                            "doc": ast.get_docstring(node) or "",
                            "parameters": ast.unparse(node.args) if hasattr(node, "args") else "",
                            "calls": sorted(
                                {
                                    ast.unparse(n.func)
                                    for n in ast.walk(node)
                                    if isinstance(n, ast.Call)
                                }
                            ),
                        }
                    )
        else:
            row["headings"] = [line for line in text.splitlines() if line.startswith("#")][:30]
        inventory.append(row)
    for row in inventory:
        module = row["file"].removesuffix(".py").replace("/", ".")
        row["called_by_modules"] = [r["file"] for r in inventory if module in r["imports"]]
    QA.mkdir(exist_ok=True)
    (QA / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    before = snapshot()
    (QA / "protected_before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "audited_text_files": len(inventory),
                "source_modules": sum(bool(r["symbols"]) for r in inventory),
                "protected_files_hashed": len(before),
                "qa_dir": str(QA),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    audit()
