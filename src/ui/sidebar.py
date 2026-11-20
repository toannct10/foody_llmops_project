"""Compact sidebar context sourced from the existing local pipeline ledger."""

from html import escape

import streamlit as st


@st.cache_data(ttl=30, show_spinner=False)
def _pipeline_status():
    from src.monitoring.operations import pipeline_snapshot

    return pipeline_snapshot()


def render_sidebar_details():
    st.sidebar.markdown("<div class='foody-eyebrow'>System status</div>",
                        unsafe_allow_html=True)
    try:
        pipeline = _pipeline_status()
    except OSError:
        pipeline = {"status": "NOT_CONFIGURED", "last_success_utc": None}
    status = pipeline.get("status") or "NOT_CONFIGURED"
    label = ("DEGRADED" if status == "FAILED" else
             "NOT CONFIGURED" if status == "NOT_CONFIGURED" else status)
    tone = ("good" if label == "SUCCESS" else "warn" if label in
            {"DEGRADED", "NOT CONFIGURED"} else "danger")
    stamp = pipeline.get("last_success_utc")
    updated = escape(str(stamp)[:16].replace("T", " ")) if stamp else "Unavailable"
    st.sidebar.markdown(
        '<div class="foody-sidebar-card"><strong>Runtime</strong><br>'
        'Database · PostgreSQL<br>Sales AI · Text-to-SQL<br>'
        'Review AI · RAG V3<br>Model · Qwen2.5-3B<br>'
        f'Pipeline · <span class="foody-badge {tone}">{escape(label)}</span><br>'
        f'<span class="foody-sidebar-muted">Last successful update: {updated} UTC</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div class='foody-eyebrow'>Current stack</div>",
                        unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="foody-sidebar-card">PostgreSQL · Qwen2.5-3B<br>'
        'RAG V3 · Text-to-SQL + fallback<br>Airflow</div>', unsafe_allow_html=True,
    )
