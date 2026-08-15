"""LCARS Streamlit command deck package (import as ``dashboard``)."""
from __future__ import annotations

import streamlit as st

from dashboard.app import main
from dashboard.charts import aggregate_transmission_pathway_totals
from dashboard.loaders import load_history_from, load_notebook_from
from dashboard.paths import HISTORY_PATH, NOTEBOOK_PATH
from dashboard.theme import LCARS_GOLD


@st.cache_data
def load_history() -> list:
    return load_history_from(HISTORY_PATH)


@st.cache_data
def load_notebook() -> dict:
    return load_notebook_from(NOTEBOOK_PATH)


__all__ = [
    "main",
    "LCARS_GOLD",
    "HISTORY_PATH",
    "NOTEBOOK_PATH",
    "aggregate_transmission_pathway_totals",
    "load_history",
    "load_notebook",
]
