"""Transmission channel explorer — per-epoch pathways and event drill-down."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import aggregate_transmission_pathway_totals
from dashboard.retention import render_retention_banner
from dashboard.session_state import set_selected_agent, set_selected_epoch
from dashboard.theme import (
    LCARS_BLUE,
    LCARS_GOLD,
    LCARS_GREEN,
    LCARS_PEACH,
    LCARS_PURPLE,
    LCARS_RED,
    LCARS_TAN,
    apply_lcars_layout,
)
from dashboard.units import axis, time_x_values

PATHWAY_LABELS = {
    "direct_contact": "Direct Contact",
    "droplet": "Droplet",
    "hvac_airborne": "HVAC Airborne",
    "fomite": "Fomite Surface",
    "food_contamination": "Food Contamination",
    "environmental": "Environmental (HVAC Colonization)",
}

PATHWAY_COLORS = [
    LCARS_BLUE, LCARS_PURPLE, LCARS_GOLD, LCARS_PEACH, LCARS_GREEN, LCARS_RED, LCARS_TAN,
]


def _pathway_from_breakdown_key(key: str) -> str:
    return key.split(":", 1)[0] if ":" in key else key


def aggregate_pathway_time_series(
    history: list[dict[str, Any]],
) -> tuple[list[Any], dict[str, list[float]]]:
    """Per-epoch pathway dose totals."""
    epochs = time_x_values(history)
    series: dict[str, list[float]] = defaultdict(lambda: [0.0] * len(history))
    for i, rec in enumerate(history):
        ct = rec.get("contact_tracing", {})
        epoch_totals: dict[str, float] = defaultdict(float)
        for ev in ct.get("transmission_events", []):
            breakdown = ev.get("pathway_breakdown")
            if breakdown:
                for pk, dose in breakdown.items():
                    pw = _pathway_from_breakdown_key(pk)
                    if pw != "none":
                        epoch_totals[pw] += float(dose)
            else:
                pw = ev.get("dominant_pathway") or ev.get("pathway", "unknown")
                if pw != "none":
                    epoch_totals[pw] += float(ev.get("total_dose", 1.0))
        for pw, dose in epoch_totals.items():
            if pw not in series:
                series[pw] = [0.0] * len(history)
            series[pw][i] = dose
    return epochs, dict(series)


def _build_pathway_stacked_area(history: list[dict[str, Any]]) -> go.Figure | None:
    epochs, series = aggregate_pathway_time_series(history)
    if not series:
        return None
    fig = go.Figure()
    for i, (pw, values) in enumerate(sorted(series.items())):
        fig.add_trace(go.Scatter(
            x=epochs,
            y=values,
            mode="lines",
            stackgroup="pathways",
            name=PATHWAY_LABELS.get(pw, pw.replace("_", " ").title()),
            line={"width": 0.5, "color": PATHWAY_COLORS[i % len(PATHWAY_COLORS)]},
        ))
    apply_lcars_layout(
        fig,
        height=320,
        title="Transmission pathways by epoch",
        xaxis_title=axis("time_epoch").title,
        yaxis_title=axis("dose").title,
        margin={"t": 50, "b": 40, "l": 60, "r": 20},
        legend={"orientation": "h", "y": -0.25, "x": 0.5, "xanchor": "center"},
    )
    return fig


def _collect_events(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in history:
        epoch = rec["epoch"]
        for ev in rec.get("contact_tracing", {}).get("transmission_events", []):
            rows.append({
                "epoch": epoch,
                "target_id": ev.get("target_id"),
                "zone": ev.get("zone", ""),
                "pathogen_id": ev.get("pathogen_id", ""),
                "dominant_pathway": ev.get("dominant_pathway", ""),
                "total_dose": ev.get("total_dose", 0),
                "source_ids": ev.get("source_ids", []),
            })
    return rows


def _zone_pathway_matrix(history: list[dict[str, Any]], epoch: int) -> pd.DataFrame:
    matrix: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rec = next((r for r in history if r["epoch"] == epoch), None)
    if not rec:
        return pd.DataFrame()
    for ev in rec.get("contact_tracing", {}).get("transmission_events", []):
        zone = ev.get("zone", "unknown")
        breakdown = ev.get("pathway_breakdown") or {}
        if breakdown:
            for pk, dose in breakdown.items():
                pw = _pathway_from_breakdown_key(pk)
                matrix[zone][pw] += float(dose)
        else:
            pw = ev.get("dominant_pathway", "unknown")
            matrix[zone][pw] += float(ev.get("total_dose", 1.0))
    if not matrix:
        return pd.DataFrame()
    return pd.DataFrame(matrix).fillna(0)


def render_transmission_explorer(
    history: list[dict[str, Any]],
    *,
    retention_mode: str,
    selected_epoch: int,
) -> None:
    st.subheader("Transmission Channel Explorer")
    if render_retention_banner(retention_mode, feature="Transmission explorer"):
        return

    totals = aggregate_transmission_pathway_totals(history)
    if not totals:
        st.info("No transmission events recorded in telemetry.")
        return

    area_fig = _build_pathway_stacked_area(history)
    if area_fig:
        st.plotly_chart(area_fig, use_container_width=True)

    events = _collect_events(history)
    if events:
        st.markdown("**Transmission events**")
        df = pd.DataFrame(events)
        st.dataframe(
            df.sort_values("epoch"),
            use_container_width=True,
            hide_index=True,
        )
        event_epochs = sorted({e["epoch"] for e in events})
        default_idx = 0
        for i, ep in enumerate(event_epochs):
            if ep == selected_epoch:
                default_idx = i
                break
        pick = st.selectbox(
            "Jump to event epoch",
            event_epochs,
            index=default_idx,
            key="trans_event_epoch_pick",
        )
        if st.button("Go to epoch", key="trans_go_epoch"):
            set_selected_epoch(int(pick), len(history))
            st.rerun()

        targets = df["target_id"].dropna().unique().tolist()
        if targets:
            agent_pick = st.selectbox("Inspect target agent", targets, key="trans_agent_pick")
            if st.button("Select agent", key="trans_select_agent"):
                set_selected_agent(int(agent_pick))
                st.rerun()

    matrix = _zone_pathway_matrix(history, selected_epoch)
    if not matrix.empty:
        st.markdown(f"**Zone × pathway matrix — epoch {selected_epoch}**")
        st.dataframe(matrix, use_container_width=True)
