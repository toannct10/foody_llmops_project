"""Continuous, accessible progress around observable UI/backend boundaries."""

from html import escape
from time import perf_counter

import streamlit as st

SALES_STAGES = ("Parse question", "Build query plan", "Generate SQL or select fallback",
                "Validate query", "Execute query", "Render verified answer")
REVIEW_STAGES = ("Prepare request", "Retrieve evidence", "Generate answer from evidence",
                 "Validate grounding", "Prepare citations", "Render answer")
CLASSIFIER_STAGES = ("Check review", "Run saved classifiers", "Render predictions")


def progress_markup(title, label, fraction, elapsed, *, state="active"):
    """Render one estimated process bar without exposing internal stage names."""
    fraction = max(0.0, min(1.0, float(fraction)))
    percent = round(fraction * 100)
    state = state if state in {"active", "complete", "failed"} else "active"
    if state == "complete":
        message = "Analysis complete"
    elif state == "failed":
        message = "Analysis stopped"
    elif "review" in title.casefold():
        message = ("Preparing review intelligence" if fraction < .3 else
                   "Retrieving relevant evidence" if fraction < .6 else
                   "Generating and checking grounded response" if fraction < .9 else
                   "Preparing result")
    else:
        message = ("Preparing verified analytics" if fraction < .3 else
                   "Generating and validating analytics" if fraction < .7 else
                   "Verifying database result" if fraction < .9 else
                   "Preparing dashboard")
    return (
        f'<div class="foody-progress {escape(state)}" role="progressbar" '
        f'aria-label="{escape(title)}" aria-valuemin="0" aria-valuemax="100" '
        f'aria-valuenow="{percent}">'
        '<div class="foody-progress-header">'
        f'<span class="foody-progress-title">{escape(title)}</span>'
        f'<span class="foody-progress-percent">{percent}%</span></div>'
        '<div class="foody-progress-track"><div class="foody-progress-fill" '
        f'style="width:{percent}%"><span class="foody-progress-shimmer"></span>'
        '<span class="foody-progress-head"></span></div></div>'
        f'<div class="foody-progress-footer">{escape(message)} · '
        f'{elapsed:.1f} s elapsed</div></div>'
    )


class AIProgress:
    def __init__(self, title):
        self.title = title
        self.started = perf_counter()
        self.slot = st.empty()

    def stage(self, label, fraction):
        """Advance only when the caller reaches an actual workflow boundary."""
        self.slot.markdown(progress_markup(self.title, label, fraction,
                                          perf_counter() - self.started),
                           unsafe_allow_html=True)

    def finish(self, *, success=True):
        elapsed = perf_counter() - self.started
        self.slot.markdown(progress_markup(self.title, "Completed" if success else "Stopped",
                                          1.0 if success else 0.0, elapsed,
                                          state="complete" if success else "failed"),
                           unsafe_allow_html=True)
        return elapsed
