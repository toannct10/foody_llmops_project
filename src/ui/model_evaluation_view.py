"""Saved three-model benchmark in the existing System Monitor workspace."""

import pandas as pd
import streamlit as st

from src.model_benchmark.service import available_runs, get_run, model_status, selection


def comparison_rows(run):
    """Whitelisted display fields; raw questions, SQL and secrets stay in logs."""
    rows = []
    for key in ("qwen", "llama", "deepseek"):
        metric = run["summaries"][key]
        rows.append({
            "Model": metric["model_name"],
            "Correct model SQL": f"{round(metric['result_accuracy'] * 10)}/10",
            "End-to-end correct": f"{round(metric['end_to_end_accuracy'] * 12)}/12",
            "Structured JSON": f"{metric['structured_output_validity']:.0%}",
            "Mean generation (ms)": round(metric["mean_generation_latency_ms"]),
            "Peak VRAM (MiB)": metric["peak_vram_mib"],
        })
    return rows


def render_model_evaluation():
    st.subheader("Model Evaluation")
    st.caption("Benchmark results are based on a 12-case project-specific evaluation set "
               "and are not a general model ranking.")
    try:
        selected = selection()
        runs = available_runs(selected=selected)
    except (OSError, ValueError, KeyError) as error:
        st.info(f"Model evaluation configuration unavailable: {type(error).__name__}")
        return
    st.metric("Production model", "Qwen2.5-3B-Instruct")
    st.caption("Production · Q4_K_M · llama.cpp · "
               f"{selected['dataset_version']} · run {selected['benchmark_run']}")
    if not runs:
        st.info("No complete three-model benchmark is available in this deployment.")
        return
    ids = [item["run_id"] for item in runs]
    default = ids.index(selected["benchmark_run"]) if selected["benchmark_run"] in ids else 0
    run_id = st.selectbox("Saved benchmark run", ids, index=default)
    run = get_run(run_id, selected=selected)
    st.dataframe(pd.DataFrame(comparison_rows(run)), hide_index=True, width="stretch")
    st.caption("Qwen was selected for its 10/10 correct model results, 100% structured "
               "output validity, and the lowest measured mean generation latency. "
               "The production model has not changed.")
    with st.expander("Failure analysis"):
        for key, failures in run["failure_categories"].items():
            st.write(f"{key.title()}: " +
                     (", ".join(f"{name} ({count})" for name, count in failures.items())
                      if failures else "no observed model-result failures"))
        st.caption("Llama's YoY SQL returned one of two requested periods. "
                   "DeepSeek produced invalid structured output on all ten safe cases.")
    with st.expander("Benchmark metadata and model status"):
        manifest = run["manifest"]
        st.json({"run_id": run_id,
                 "dataset_version": manifest["dataset_version"],
                 "dataset_sha256": manifest["dataset_sha256"],
                 "git_commit": manifest["git_commit"],
                 "backend": manifest["backend"],
                 "quantization": "Q4_K_M",
                 "generation_settings": manifest["generation_settings"]})
        st.dataframe(pd.DataFrame.from_dict(model_status(), orient="index"),
                     width="stretch")
