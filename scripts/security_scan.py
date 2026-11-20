"""Reject tracked private artifacts and high-confidence credential signatures."""

import re
import subprocess
from pathlib import Path

TEXT_SUFFIXES = {".py", ".sql", ".yaml", ".yml", ".json", ".toml", ".md",
                 ".txt", ".ps1", ".sh"}
SIGNATURES = {
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "databricks_pat": re.compile(r"\bdapi[0-9a-f]{32}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def private_path(path):
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return (name == ".env" or (name.startswith(".env.") and name != ".env.example")
            or path.suffix.lower() in {".pem", ".p8", ".key", ".gguf", ".sqlite"}
            or "vector_store" in parts or "mlruns" in parts
            or ("data" in parts and "foody" in parts))


def scan_file(path):
    if private_path(path):
        return ["private_artifact"]
    if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    return [name for name, pattern in SIGNATURES.items() if pattern.search(content)]


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    findings = [(str(path), issue) for name in tracked if name
                for path in [Path(name.decode("utf-8", errors="surrogateescape"))]
                for issue in scan_file(path)]
    for path, issue in findings:
        print(f"{path}: {issue}")
    print(f"Security scan: {'FAIL' if findings else 'PASS'}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
