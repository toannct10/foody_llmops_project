"""Reusable, escaped presentation components; no business calculations."""

from hashlib import sha256
from html import escape

import streamlit as st

BADGE_TONES = {"good", "warn", "muted", "info", "cyan", "danger"}


def header(title, subtitle, badges=()):
    pills = "".join(f'<span class="foody-badge">{escape(str(label))}</span>' for label in badges)
    st.markdown(
        '<div class="foody-hero"><div class="foody-eyebrow">Foody Intelligence Platform</div>'
        f'<h1>{escape(title)}</h1><div class="foody-muted">{escape(subtitle)}</div>{pills}</div>',
        unsafe_allow_html=True,
    )


def badge(label, tone="default"):
    tone = tone if tone in BADGE_TONES else ""
    st.markdown(f'<span class="foody-badge {tone}">{escape(str(label))}</span>',
                unsafe_allow_html=True)


def badge_row(items):
    pills = "".join(
        f'<span class="foody-badge {tone if tone in BADGE_TONES else ""}">'
        f'{escape(str(label))}</span>' for label, tone in items
    )
    st.markdown(f"<div>{pills}</div>", unsafe_allow_html=True)


def empty_state(title, detail=""):
    st.markdown(f'<div class="foody-empty"><strong>{escape(title)}</strong>'
                f'{escape(detail)}</div>', unsafe_allow_html=True)


def kpi_card(label, value, *, kind="secondary", detail="", tall=False):
    """Show a verified value with a bounded visual priority, without recalculation."""
    kind = kind if kind in {"primary", "secondary", "status", "healthy", "warning", "danger"} else "secondary"
    description = f'<div class="foody-kpi-detail">{escape(str(detail))}</div>' if detail else ""
    height_class = " foody-kpi-tall" if tall else ""
    st.markdown(
        f'<div class="foody-kpi-card foody-kpi-{kind}{height_class}">'
        f'<div class="foody-kpi-label">{escape(str(label))}</div>'
        f'<div class="foody-kpi-value">{escape(str(value))}</div>{description}</div>',
        unsafe_allow_html=True,
    )


def answer_card(title, answer, label=None, tone="default"):
    pill = (f'<span class="foody-badge {tone if tone in BADGE_TONES else ""}">'
            f'{escape(label)}</span>') if label else ""
    st.markdown(f'<div class="foody-card foody-answer"><h3>{escape(title)}</h3>{pill}'
                f'<p>{escape(str(answer))}</p></div>', unsafe_allow_html=True)


def review_state_key(review_id, scope):
    """Use the stable review ID plus a bounded context to avoid cross-query UI state."""
    context = sha256(str(scope).encode("utf-8")).hexdigest()[:10]
    return f"review_expanded_{context}_{review_id}"


def preview_text(value, limit=230):
    value = str(value)
    if len(value) <= limit:
        return value
    cut = value[:limit].rsplit(" ", 1)[0]
    return (cut if cut else value[:limit]).rstrip() + "..."


def _toggle_review(key):
    st.session_state[key] = not st.session_state.get(key, False)


def review_text(review_id, value, *, scope, limit=230):
    """Render exactly one text version; toggling never calls retrieval or generation."""
    value = str(value)
    if len(value) <= limit:
        st.write(value)
        return
    key = review_state_key(review_id, scope)
    expanded = st.session_state.get(key, False)
    st.write(value if expanded else preview_text(value, limit))
    st.button("Less" if expanded else "More", key=f"{key}_toggle",
              on_click=_toggle_review, args=(key,))


def evidence_card(reference, text, metadata="", *, review_id=None, scope="evidence"):
    with st.container(border=True):
        st.markdown(f"**{escape(str(reference))}**")
        st.caption(str(metadata))
        review_text(review_id or reference, text, scope=scope)


def money(value):
    return f"{float(value or 0):,.0f} ₫"


def percent(value):
    return "—" if value is None else f"{float(value):.2%}"


def text_sentiment_label(prediction):
    """The explorer badge uses the saved text-model class, never the rating."""
    if prediction not in {"negative", "neutral", "positive"}:
        raise ValueError("Unsupported sentiment model class")
    return f"Text sentiment: {prediction.title()}"
