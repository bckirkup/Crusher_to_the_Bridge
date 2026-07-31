"""Fleet Operations tab — Presidio multi-cruise overview."""
from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import render_bridge_status
from dashboard.loaders import (
    load_history_from,
    load_notebook_from,
    load_platform_bundle,
    list_cruise_dirs,
    resolve_platform_id,
    telemetry_paths,
)
from dashboard.paths import REPO_ROOT
from dashboard.spatial_viz import render_tactical_grid
from dashboard.theme import (
    LCARS_BLUE,
    LCARS_GOLD,
    LCARS_GREEN,
    apply_lcars_layout,
    LCARS_RED,
    _lcars_alert_banner,
    _lcars_banner,
)


def render_fleet_operations(default_fleet_root: str) -> None:
    st.subheader("Fleet Operations")

    fleet_root = st.text_input(
        "Presidio output root",
        value=default_fleet_root or os.path.join(
            REPO_ROOT, "presidio", "data", "experiences", "smoke_runs",
        ),
        key="fleet_root",
    )

    summary_path = os.path.join(fleet_root, "fleet_summary.json")
    if os.path.isfile(summary_path):
        with open(summary_path, encoding="utf-8") as fh:
            fleet_summary = json.load(fh)
        st.markdown(
            _lcars_banner(
                f"Fleet summary — {fleet_summary.get('num_cruises', '?')} cruises",
                LCARS_GOLD,
            ),
            unsafe_allow_html=True,
        )
        records = fleet_summary.get("records", [])
        if records:
            rows = []
            for rec in records:
                rewards = rec.get("rewards", {})
                rows.append({
                    "Cruise": rec.get("cruise_id", "?"),
                    "Fleet reward": rewards.get("fleet", 0),
                    "CO reward": rewards.get("commanding_officer", 0),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    cruises = list_cruise_dirs(fleet_root)
    if not cruises:
        st.info("No cruise_NNN directories found under output root.")
        return

    cruise_labels = [os.path.basename(c) for c in cruises]
    selected = st.selectbox("Select cruise", cruise_labels, key="fleet_cruise")
    cruise_dir = os.path.join(fleet_root, selected)

    hist_path, nb_path = telemetry_paths(cruise_dir)
    history = load_history_from(hist_path)
    notebook = load_notebook_from(nb_path)

    if not history:
        st.warning(f"No telemetry in {cruise_dir}")
        return

    platform_id, _ = resolve_platform_id(history)
    bundle = load_platform_bundle(platform_id)

    c1, c2 = st.columns([1, 3])
    with c1:
        if bundle.hull_png_path:
            st.image(bundle.hull_png_path, width=180)
        st.caption(bundle.manifest.get("ship_class_label", platform_id))

    with c2:
        last = history[-1]
        status = last.get("trigger_status", "BASELINE")
        st.markdown(_lcars_alert_banner(status), unsafe_allow_html=True)
        s = last.get("summary", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Infected", s.get("infected", 0))
        m2.metric("Symptomatic", s.get("symptomatic", 0))
        m3.metric(
            "Credits spent",
            f"${last.get('cost_accounting', {}).get('total_financial_usd', 0):,.0f}",
        )

    _render_fleet_comparison(cruises)

    st.divider()
    st.markdown(_lcars_banner(f"Cruise detail — {selected}", LCARS_BLUE), unsafe_allow_html=True)
    render_tactical_grid(history, bundle, key_suffix="_fleet")

    with st.expander("Bridge metrics (this cruise)", expanded=False):
        render_bridge_status(history, notebook)


def _trigger_status_color(status: str) -> str:
    if status in ("CONFIRMED", "LOCKDOWN"):
        return LCARS_RED
    if status in ("SUSPECTED", "ALERT"):
        return LCARS_GOLD
    return LCARS_GREEN


def _render_fleet_comparison(cruise_dirs: list[str]) -> None:
    labels = []
    infected = []
    symptomatic = []
    colors = []

    for cdir in cruise_dirs:
        hist_path, _ = telemetry_paths(cdir)
        if not os.path.isfile(hist_path):
            continue
        with open(hist_path, encoding="utf-8") as fh:
            hist = json.load(fh)
        if not hist:
            continue
        last = hist[-1]
        summary = last.get("summary", {})
        labels.append(os.path.basename(cdir))
        infected.append(summary.get("infected", 0))
        symptomatic.append(summary.get("symptomatic", 0))
        status = last.get("trigger_status", "BASELINE")
        colors.append(_trigger_status_color(status))

    if not labels:
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Infected", x=labels, y=infected, marker_color=LCARS_RED))
    fig.add_trace(go.Bar(name="Symptomatic", x=labels, y=symptomatic, marker_color=LCARS_GOLD))
    apply_lcars_layout(
        fig,
        height=280,
        barmode="group",
        title="Final epoch — fleet cruise comparison",
        margin={"t": 40, "b": 60},
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    for i, cdir in enumerate(cruise_dirs):
        hist_path, _ = telemetry_paths(cdir)
        if not os.path.isfile(hist_path):
            continue
        with open(hist_path, encoding="utf-8") as fh:
            hist = json.load(fh)
        epochs = [r["epoch"] for r in hist]
        inf = [
            r.get("summary", {}).get("infected", 0)
            + r.get("summary", {}).get("symptomatic", 0)
            for r in hist
        ]
        fig2.add_trace(go.Scatter(
            x=epochs, y=inf, mode="lines",
            name=os.path.basename(cdir),
            line={"width": 2},
        ))
    apply_lcars_layout(
        fig2,
        height=240,
        title="Infection pressure across cruises",
        xaxis_title="Epoch", yaxis_title="Active cases",
    )
    st.plotly_chart(fig2, use_container_width=True)
