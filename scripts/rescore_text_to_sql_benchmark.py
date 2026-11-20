"""Recalculate benchmark scores from saved live facts without model inference."""

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from src.model_benchmark.analysis import failure_category, summarize, write_summary_csv
from src.model_benchmark.dataset import load_manifest, result_correct


def rescore(run_dir):
    run_dir = Path(run_dir)
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset = load_manifest()
    if manifest["status"] != "COMPLETE" or manifest["dataset_sha256"] != dataset["dataset_sha256"]:
        raise ValueError("Only a complete run on the current frozen dataset can be rescored")
    results_path = run_dir / "results.jsonl"
    rows = [json.loads(line) for line in results_path.read_text(
        encoding="utf-8").splitlines()]
    expected = {(model, case["id"]) for model in manifest["selected_models"]
                for case in dataset["cases"]}
    actual = {(row["model_family"].casefold(), row["question_id"]) for row in rows}
    if len(rows) != len(expected) or actual != expected:
        raise ValueError("Saved model/question records are incomplete or duplicated")
    original = run_dir / "initial_scoring"
    if original.exists():
        raise FileExistsError("Run has already been rescored")
    original.mkdir()
    for name in ("results.jsonl", "summary.json", "summary.csv", "run_manifest.json"):
        shutil.copy2(run_dir / name, original / name)
    for model in manifest["selected_models"]:
        failure = run_dir / f"failure_analysis_{model}.json"
        shutil.copy2(failure, original / failure.name)
    cases = {case["id"]: case for case in dataset["cases"]}
    for row in rows:
        if row["expected_safety_class"] == "SAFE":
            correct = result_correct(row["question_id"], row["result_rows"],
                                     cases[row["question_id"]]["expected_reference_result"])
            row["final_answer_correctness"] = correct
            if row["status"] == "MODEL_RESULT":
                row["model_result_correctness"] = correct
                row["result_correctness"] = correct
        row["failure_classification"] = failure_category(row)
    results_path.write_text("".join(
        json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows),
        encoding="utf-8")
    old = json.loads((original / "summary.json").read_text(encoding="utf-8"))
    summaries = []
    for model in manifest["selected_models"]:
        summary = summarize(model, [row for row in rows if row["model_family"].casefold() == model])
        previous = next(item for item in old if item["model"] == model)
        for key in ("model_name", "model_sha256", "availability"):
            summary[key] = previous[key]
        summaries.append(summary)
        failures = [row for row in rows if row["model_family"].casefold() == model
                    and row.get("failure_classification")]
        (run_dir / f"failure_analysis_{model}.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_summary_csv(run_dir / "summary.csv", summaries)
    manifest["rescored_at_utc"] = datetime.now(UTC).isoformat()
    manifest["scoring_revision"] = "nested deterministic fallback facts v2"
    manifest["original_scoring_directory"] = "initial_scoring/"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    arguments = parser.parse_args()
    for item in rescore(arguments.run_dir):
        print(f"{item['model']}: model={item['result_accuracy']} "
              f"end_to_end={item['end_to_end_accuracy']}")
