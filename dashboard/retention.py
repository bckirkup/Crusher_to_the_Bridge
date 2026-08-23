"""Retention guard banners for compact telemetry."""
from __future__ import annotations

import streamlit as st

from dashboard.theme import LCARS_AMBER, _lcars_banner


def render_retention_banner(retention_mode: str, *, feature: str) -> bool:
    """Show banner when compact retention blocks a feature. Returns True if blocked."""
    if retention_mode != "compact":
        return False
    st.markdown(
        _lcars_banner(
            f"{feature} requires full telemetry retention. "
            "Set run.history_retention to \"full\" in your Picard run spec.",
            LCARS_AMBER,
        ),
        unsafe_allow_html=True,
    )
    return True
