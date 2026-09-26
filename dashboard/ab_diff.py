"""A/B Run Diff — side-by-side comparison of two simulation_history.json runs.

Compares a baseline run against a variant arm (e.g. paired-seed protocol
A/B, arm-vs-baseline sweep readouts). Pure helpers return DataFrames so
they are unit-testable without a Streamlit server.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.loaders import load_history_from, telemetry_paths
from dashboard.paths import REPO_ROOT
from dashboard.theme import LCARS_BLUE, LCARS_RED, apply_lcars_layout
from dashboard.units import axis, time_x_values, time_xaxis_title
from simulation_utils.paths import resolve_repo_path

SUMMARY_METRICS = (
    "infected",
    "symptomatic",
    "isolated",
    "recovered",
    "sick_call_count",
    "quarantine_refusers",
)


def summarize_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    """One-row run summary used for the A/B delta table."""
    if not history:
        return {}
    summary_of = [rec.get("summary", {}) for rec in history]
    active = [s.get("infected", 0) + s.get("symptomatic", 0) for s in summary_of]
    infected = [s.get("infected", 0) for s in summary_of]
    peak_idx = max(range(len(history)), key=lambda i: active[i])
    first_trigger = next(
        (rec.get("epoch", i) for i, rec in enumerate(history)
         if rec.get("trigger_status") not in (None, "BASELINE")),
        None,
    )
    cost = history[-1].get("cost_accounting", {}) or {}
    last = summary_of[-1]
    return {
        "epochs": len(history),
        "peak_active_cases": active[peak_idx],
        "peak_active_epoch": history[peak_idx].get("epoch", peak_idx),
        "peak_infected": max(infected),
        "final_infected": last.get("infected", 0),
        "final_symptomatic": last.get("symptomatic", 0),
        "final_recovered": last.get("recovered", 0),
        "final_sick_calls": last.get("sick_call_count", 0),
        "first_non_baseline_epoch": first_trigger,
        "final_trigger_status": history[-1].get("trigger_status", "BASELINE"),
        "ois_cumulative": cost.get("operational_impact_cumulative", 0.0),
        "credits_spent_usd": cost.get("total_financial_usd", 0.0),
        "labor_hours": cost.get("total_labor_hours", 0.0),
    }


def delta_summary_frame(
    hist_a: list[dict[str, Any]], hist_b: list[dict[str, Any]],
) -> pd.DataFrame:
    """Metric | Run A | Run B | Delta (B - A) table of run-level summaries."""
    a, b = summarize_history(hist_a), summarize_history(hist_b)
    rows = []
    for key in a.keys() | b.keys():
        va, vb = a.get(key), b.get(key)
        delta = vb - va if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None
        rows.append({"Metric": key, "Run A": va, "Run B": vb, "Delta (B-A)": delta})
    return pd.DataFrame(rows)


def per_epoch_delta_frame(
    hist_a: list[dict[str, Any]], hist_b: list[dict[str, Any]],
) -> pd.DataFrame:
    """Per-epoch metric deltas over the shared epoch prefix (long format)."""
    rows = []
    for rec_a, rec_b in zip(hist_a, hist_b):
        epoch = rec_a.get("epoch", len(rows))
        sa, sb = rec_a.get("summary", {}), rec_b.get("summary", {})
        for metric in SUMMARY_METRICS:
            va, vb = sa.get(metric, 0), sb.get(metric, 0)
            rows.append({
                "epoch": epoch, "metric": metric,
                "run_a": va, "run_b": vb, "delta": vb - va,
            })
    return pd.DataFrame(rows)


def active_cases_series(history: list[dict[str, Any]]) -> list[int]:
    """Infected + symptomatic per epoch — the paired-seed readout curve."""
    return [
        rec.get("summary", {}).get("infected", 0)
        + rec.get("summary", {}).get("symptomatic", 0)
        for rec in history
    ]


def _render_overlay_chart(
    hist_a: list[dict[str, Any]], hist_b: list[dict[str, Any]],
    label_a: str, label_b: str,
) -> None:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_x_values(hist_a), y=active_cases_series(hist_a),
        mode="lines", name=label_a, line={"color": LCARS_BLUE, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=time_x_values(hist_b), y=active_cases_series(hist_b),
        mode="lines", name=label_b, line={"color": LCARS_RED, "width": 2},
    ))
    apply_lcars_layout(
        fig, height=280, title="Active cases (infected + symptomatic)",
        xaxis_title=time_xaxis_title(hist_a), yaxis_title=axis("active_cases").title,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_delta_chart(
    delta_df: pd.DataFrame, hist_a: list[dict[str, Any]],
) -> None:
    fig = go.Figure()
    for metric in ("infected", "symptomatic", "isolated"):
        sub = delta_df[delta_df["metric"] == metric]
        if not sub.empty:
            fig.add_trace(go.Scatter(
                x=sub["epoch"], y=sub["delta"], mode="lines", name=f"{metric} Δ",
            ))
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,180,0,0.35)")
    apply_lcars_layout(
        fig, height=260, title="Per-epoch delta (Run B − Run A)",
        xaxis_title=time_xaxis_title(hist_a), yaxis_title=axis("persons").title,
    )
    st.plotly_chart(fig, use_container_width=True)


def _load_history_for_dir(telemetry_dir: str) -> list[dict[str, Any]]:
    hist_path, _ = telemetry_paths(telemetry_dir)
    return load_history_from(hist_path)


def render_ab_diff(default_dir: str) -> None:
    """A/B run diff tab: two telemetry dirs → overlay + delta summaries."""
    st.subheader("A/B Run Diff")
    st.caption(
        "Compare two `simulation_history.json` runs — e.g. protocol arm vs "
        "baseline. Point each input at a telemetry directory or a Presidio "
        "cruise folder."
    )
    c1, c2 = st.columns(2)
    with c1:
        dir_a = st.text_input("Run A (baseline) telemetry dir", value=default_dir, key="ab_dir_a")
    with c2:
        dir_b = st.text_input("Run B (arm) telemetry dir", value=default_dir, key="ab_dir_b")

    try:
        dir_a = resolve_repo_path(REPO_ROOT, dir_a)
        dir_b = resolve_repo_path(REPO_ROOT, dir_b)
    except ValueError:
        st.error("Telemetry directories must be inside the repository.")
        return

    hist_a = _load_history_for_dir(dir_a)
    hist_b = _load_history_for_dir(dir_b)
    if not hist_a or not hist_b:
        missing = dir_a if not hist_a else dir_b
        st.warning(f"No simulation_history.json found in {missing}")
        return

    label_a, label_b = os.path.basename(dir_a.rstrip("/")) or "A", os.path.basename(dir_b.rstrip("/")) or "B"
    st.markdown(f"**Run A:** `{dir_a}` — **Run B:** `{dir_b}`")

    _render_overlay_chart(hist_a, hist_b, label_a, label_b)

    delta_df = per_epoch_delta_frame(hist_a, hist_b)
    _render_delta_chart(delta_df, hist_a)
    if len(hist_a) != len(hist_b):
        st.info(
            f"Epoch counts differ (A={len(hist_a)}, B={len(hist_b)}); "
            "per-epoch deltas cover the shared prefix."
        )

    st.markdown("**Run-level delta summary**")
    st.dataframe(delta_summary_frame(hist_a, hist_b), use_container_width=True, hide_index=True)

    with st.expander("Per-epoch deltas", expanded=False):
        st.dataframe(
            delta_df.pivot(index="epoch", columns="metric", values="delta"),
            use_container_width=True,
        )
