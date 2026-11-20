"""Read-only checks for generated Vietnamese project documents."""

import json
import re

from audit_repository import QA, ROOT, snapshot
from docx import Document


def verify():
    before = json.loads((QA / "protected_before.json").read_text(encoding="utf-8"))
    after = snapshot()
    changed = sorted(
        key for key in before.keys() | after.keys() if before.get(key) != after.get(key)
    )
    assert not changed, f"Protected files changed: {changed}"

    results = {}
    for stem in ("PROJECT_MASTER_GUIDE_VI", "TASK2_REVIEW2_REPORT_VI"):
        md_path = ROOT / "docs" / f"{stem}.md"
        docx_path = md_path.with_suffix(".docx")
        md = md_path.read_text(encoding="utf-8")
        doc = Document(docx_path)
        figure_links = re.findall(r"!\[[^]]*\]\(([^)]+)\)", md)
        assert all((md_path.parent / link).is_file() for link in figure_links)
        assert len(figure_links) == len(doc.inline_shapes)
        assert "�" not in md
        assert not any(
            "![" in paragraph.text or "<!--" in paragraph.text for paragraph in doc.paragraphs
        )
        assert len(doc.element.xpath("//m:oMath")) >= 30
        assert len(doc.tables) >= 25
        results[stem] = {
            "markdown_bytes": md_path.stat().st_size,
            "docx_bytes": docx_path.stat().st_size,
            "tables": len(doc.tables),
            "figures": len(doc.inline_shapes),
            "formula_elements": len(doc.element.xpath("//m:oMath")),
            "headings": sum(p.style.name.startswith("Heading") for p in doc.paragraphs),
            "qa_questions": sum(p.text.startswith("Câu hỏi ") for p in doc.paragraphs),
        }

    master = (ROOT / "docs" / "PROJECT_MASTER_GUIDE_VI.md").read_text(encoding="utf-8")
    report = (ROOT / "docs" / "TASK2_REVIEW2_REPORT_VI.md").read_text(encoding="utf-8")
    notebook = (ROOT / "docs" / "TASK2_CALCULATION_NOTEBOOK_VI.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "DOCUMENTATION_AUDIT.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^## Chương \d+\b", master, re.M)) == 85
    assert len(re.findall(r"^### Câu hỏi \d+\b", master, re.M)) >= 50
    assert len(re.findall(r"^## \d+ ", report, re.M)) >= 30
    assert "Hit@" in audit and "8193" in audit and "8194" in audit
    assert "33938" in audit and "31694" in audit
    assert "parameter defense" in notebook.lower() or "Bảo vệ tham số" in notebook
    assert all(token in master for token in ("8193", "8194", "33938", "31694", "v1.0.1"))
    return {
        "protected_files": len(before),
        "protected_changes": changed,
        "master_chapters": 85,
        "report_numbered_sections": len(re.findall(r"^## \d+ ", report, re.M)),
        "files": results,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
