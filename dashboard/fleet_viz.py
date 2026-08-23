"""Fleet Operations tab — Presidio multi-cruise overview with port context."""
from __future__ import annotations

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import render_bridge_status
from dashboard.loaders import (
    detect_retention_mode,
    list_cruise_dirs,
    load_history_from,
    load_notebook_from,
    load_platform_bundle,
    load_voyage_config,
    resolve_platform_id,
    telemetry_paths,
)
from dashboard.paths import REPO_ROOT
from dashboard.retrospective import _build_voyage_strip
from dashboard.session_state import get_selected_epoch, set_selected_epoch
from dashboard.spatial_viz import render_tactical_grid
from dashboard.theme import (
    LCARS_BLUE,
    LCARS_GOLD,
    LCARS_GREEN,
    LCARS_RED,
    _lcars_alert_banner,
    _lcars_banner,
    apply_lcars_layout,
)
from dashboard.units import axis, time_x_values, time_xaxis_title
from simulation_utils.paths import resolve_child_path, resolve_repo_path, validated_open


def _trigger_status_color(status: str) -> str:
    if status in ("CONFIRMED", "LOCKDOWN"):
        return LCARS_RED
    if status in ("SUSPECTED", "ALERT"):
        return LCARS_GOLD
    return LCARS_GREEN


def _load_cruise_histories(cruise_dirs: list[str]) -> dict[str, list]:
    out: dict[str, list] = {}
    for cdir in cruise_dirs:
        hist_path, _ = telemetry_paths(cdir)
        hist = load_history_from(hist_path)
        if hist:
            out[cdir] = hist
    return out


def _fleet_metrics_matrix(cruise_dirs: list[str], histories: dict[str, list]) -> pd.DataFrame:
    rows = []
    for cdir in cruise_dirs:
        hist = histories.get(cdir, [])
        if not hist:
            continue
        last = hist[-1]
        summary = last.get("summary", {})
        peak_inf = max(
            (r.get("summary", {}).get("infected", 0) for r in hist),
            default=0,
        )
        ca = last.get("cost_accounting", {})
        rows.append({
            "Cruise": os.path.basename(cdir),
            "Peak infected": peak_inf,
            "Final infected": summary.get("infected", 0),
            "Final symptomatic": summary.get("symptomatic", 0),
            "OIS cumulative": ca.get("operational_impact_cumulative", 0),
            "Credits spent": ca.get("total_financial_usd", 0),
            "Status": last.get("trigger_status", ""),
        })
    return pd.DataFrame(rows)


def _render_fleet_comparison(
    cruise_dirs: list[str],
    histories: dict[str, list],
    *,
    selected_epoch: int,
) -> None:
    labels = []
    infected = []
    symptomatic = []
    colors = []

    for cdir in cruise_dirs:
        hist = histories.get(cdir, [])
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
        yaxis_title=axis("persons").title,
        margin={"t": 40, "b": 60},
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    sample_hist: list = []
    for cdir in cruise_dirs:
        hist = histories.get(cdir, [])
        if not hist:
            continue
        sample_hist = hist
        epochs = time_x_values(hist)
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
        for rec in hist:
            port = rec.get("voyage_epoch", {}).get("port")
            if port and rec.get("voyage_epoch", {}).get("day_type") == "port_day":
                x_val = rec.get("voyage_epoch", {}).get("voyage_day", rec["epoch"])
                fig2.add_vline(
                    x=x_val,
                    line_dash="dot",
                    line_color="rgba(255,180,0,0.35)",
                )
    if fig2.data and sample_hist:
        apply_lcars_layout(
            fig2,
            height=260,
            title=f"Infection pressure across cruises (scrubber epoch {selected_epoch})",
            xaxis_title=time_xaxis_title(sample_hist),
            yaxis_title=axis("active_cases").title,
        )
        st.plotly_chart(fig2, use_container_width=True)


def _render_port_voyage_strips(cruise_dirs: list[str], histories: dict[str, list]) -> None:
    for cdir in cruise_dirs:
        hist = histories.get(cdir, [])
        if not hist or not hist[0].get("voyage_epoch"):
            continue
        platform_id, _ = resolve_platform_id(hist)
        itinerary = (load_voyage_config(platform_id).get("voyage") or {}).get("itinerary") or []
        label = os.path.basename(cdir)
        st.markdown(f"**{label}** voyage timeline")
        st.plotly_chart(_build_voyage_strip(hist, itinerary), use_container_width=True)


def render_fleet_operations(
    default_fleet_root: str,
    *,
    selected_epoch: int = 0,
) -> None:
    st.subheader("Fleet Operations")

    fleet_root_input = st.text_input(
        "Presidio output root",
        value=st.session_state.get("fleet_root") or default_fleet_root or os.path.join(
            REPO_ROOT, "presidio", "data", "experiences", "smoke_runs",
        ),
        key="fleet_root",
    )
    try:
        fleet_root = resolve_repo_path(REPO_ROOT, fleet_root_input)
    except ValueError:
        st.error("Fleet output root must be inside the repository.")
        return
    st.session_state.fleet_root = fleet_root

    summary_path = resolve_child_path(fleet_root, "fleet_summary.json")
    fleet_summary: dict = {}
    try:
        with validated_open(
            summary_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            fleet_summary = json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        fleet_summary = {}
    if fleet_summary:
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
                    "Seed": rec.get("metadata", {}).get("seed", ""),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    cruises = list_cruise_dirs(fleet_root)
    if not cruises:
        st.info("No cruise_NNN directories found under output root.")
        return

    histories = _load_cruise_histories(cruises)
    matrix = _fleet_metrics_matrix(cruises, histories)
    if not matrix.empty:
        st.markdown("**Fleet overview matrix**")
        st.dataframe(matrix, use_container_width=True, hide_index=True)

    _render_fleet_comparison(cruises, histories, selected_epoch=selected_epoch)

    with st.expander("Port-linked voyage timelines", expanded=False):
        _render_port_voyage_strips(cruises, histories)

    cruise_labels = [os.path.basename(c) for c in cruises]
    selected = st.selectbox(
        "Select cruise (detail only — use button below to load globally)",
        cruise_labels,
        key="fleet_cruise",
    )
    cruise_dir = resolve_child_path(fleet_root, selected)
    st.session_state.selected_cruise_dir = cruise_dir

    hist_path, nb_path = telemetry_paths(cruise_dir)
    history = load_history_from(hist_path)
    notebook = load_notebook_from(nb_path)

    if not history:
        st.warning(f"No telemetry in {cruise_dir}")
        return

    retention_mode = detect_retention_mode(history)
    platform_id, _ = resolve_platform_id(history)
    bundle = load_platform_bundle(platform_id)

    c1, c2 = st.columns([1, 3])
    with c1:
        if bundle.hull_png_path:
            st.image(bundle.hull_png_path, width=180)
        st.caption(bundle.manifest.get("ship_class_label", platform_id))

    with c2:
        epoch_idx = min(get_selected_epoch(), len(history) - 1)
        rec = history[epoch_idx]
        st.markdown(_lcars_alert_banner(rec.get("trigger_status", "BASELINE")), unsafe_allow_html=True)
        s = rec.get("summary", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Infected", s.get("infected", 0))
        m2.metric("Symptomatic", s.get("symptomatic", 0))
        m3.metric(
            "Credits spent",
            f"${rec.get('cost_accounting', {}).get('total_financial_usd', 0):,.0f}",
        )

    st.divider()
    st.markdown(_lcars_banner(f"Cruise detail — {selected}", LCARS_BLUE), unsafe_allow_html=True)
    render_tactical_grid(
        history, bundle,
        key_suffix="_fleet",
        selected_epoch=epoch_idx,
        retention_mode=retention_mode,
    )

    with st.expander("Bridge metrics (this cruise)", expanded=False):
        render_bridge_status(history, notebook)

    if st.button("Use this cruise in all tabs", key="fleet_activate_cruise"):
        st.session_state.telemetry_dir = cruise_dir
        st.session_state.active_history_source = "fleet"
        set_selected_epoch(0, len(history))
        st.cache_data.clear()
        st.rerun()
