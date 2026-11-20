"""Check the live Streamlit analyst presentation without rewriting old reports."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def main():
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app/app.py"),
        default_timeout=180,
    ).run()
    app.sidebar.radio[0].set_value("AI Review Analyst").run()
    app.selectbox[0].set_value(
        "Hanuri - Quán Ăn Hàn Quốc - Nguyễn Đình Chiểu"
    ).run()
    app.text_input[0].set_value("Khách nói gì về chất lượng món ăn?").run()
    app.button[0].click().run()
    headings = [item.value for item in app.subheader]
    captions = [str(item.value) for item in app.caption]
    displayed = [str(item.value) for item in app.markdown]
    result = {
        "exceptions": len(app.exception),
        "warnings": [item.message for item in app.warning],
        "analysis_heading": "AI Analysis" in headings,
        "evidence_heading": "Evidence used" in headings,
        "technical_expander": any(item.label == "Technical details" for item in app.expander),
        "synthesis_mode_visible": any("Generation mode: AI synthesis" in item
                                      for item in captions),
        "citation_visible": any("[E1]" in item for item in displayed),
        "raw_ids_hidden_from_main": not any("Evidence IDs" in item for item in displayed),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["exceptions"] or result["warnings"] or not all(
        value for key, value in result.items() if isinstance(value, bool)
    ):
        raise SystemExit("AI Review Analyst presentation check failed")


if __name__ == "__main__":
    main()
