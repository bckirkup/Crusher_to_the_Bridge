"""
dashboard.py – USS Crusher Main Bridge Display
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LCARS-inspired Streamlit command interface for the Crusher Labs
biodefense digital twin.  All readouts styled after the
Enterprise-D Bridge Operations console.

Stations:
  1. Bridge Status Display     – Ship status, biosensor telemetry, epidemic curve
  2. Tactical Sensor Grid      – Spatial deck map with contamination overlays
  3. Sickbay Diagnostic Console – Dr. Crusher's lab notebook at three fidelity tiers
  4. Standing Orders & Threat Profiles – SOP configuration and pathogen dossiers

Usage::

    python orchestrator.py        # generate simulation data
    streamlit run dashboard.py    # launch the command deck
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Paths ────────────────────────────────────────────────────────────────

_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(_DIR, "telemetry_buffer", "simulation_history.json")
NOTEBOOK_PATH = os.path.join(_DIR, "telemetry_buffer", "artificial_lab_notebook.json")
LAYOUT_PATH = os.path.join(
    _DIR, "data", "platforms", "destroyer_baseline", "spatial_layout.json",
)
AIRFLOW_PATH = os.path.join(
    _DIR, "data", "platforms", "destroyer_baseline", "air_flow_paths.json",
)
PATHOGEN_PATH = os.path.join(_DIR, "data", "pathogens", "active_profiles.json")
PROTOCOLS_PATH = os.path.join(_DIR, "data", "config", "protocols.json")

# ── LCARS Styling ────────────────────────────────────────────────────────

# TNG-era LCARS palette
LCARS_GOLD = "#FF9900"
LCARS_AMBER = "#CC7700"
LCARS_BLUE = "#9999FF"
LCARS_PURPLE = "#CC99CC"
LCARS_PEACH = "#FFCC99"
LCARS_TAN = "#CC9966"
LCARS_RED = "#CC6666"
LCARS_GREEN = "#99CC99"
LCARS_BG = "#000000"
LCARS_PANEL = "#1A1A2E"

# Alert condition colours
ALERT_COLORS = {
    "BASELINE": LCARS_GREEN,
    "SUSPECTED": LCARS_GOLD,
    "CONFIRMED": LCARS_RED,
}
ALERT_LABELS = {
    "BASELINE": "CONDITION GREEN",
    "SUSPECTED": "YELLOW ALERT",
    "CONFIRMED": "RED ALERT",
}
STOPLIGHT_COLORS = {"GREEN": LCARS_GREEN, "AMBER": LCARS_GOLD, "RED": LCARS_RED}
_STOPLIGHT_SEVERITY = {"GREEN": 0, "AMBER": 1, "RED": 2}

# Plotly template overrides for LCARS look
LCARS_PLOTLY = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(26,26,46,0.6)",
    font=dict(family="Helvetica Neue, Arial, sans-serif", color=LCARS_PEACH),
)

LCARS_CSS = """
<style>
    /* LCARS background */
    .stApp {
        background-color: #000000;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1A1A2E;
        color: #FFCC99;
        border-radius: 12px 12px 0 0;
        padding: 8px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF9900;
        color: #000000;
    }
    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: #FF9900;
    }
    [data-testid="stMetricLabel"] {
        color: #FFCC99;
    }
    /* Subheader styling */
    .stMarkdown h2, .stMarkdown h3 {
        color: #FF9900;
        border-bottom: 2px solid #CC7700;
        padding-bottom: 4px;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0D0D1A;
        border-right: 3px solid #FF9900;
    }
    /* Expander */
    .streamlit-expanderHeader {
        color: #FFCC99;
        background-color: #1A1A2E;
    }
    /* Divider */
    hr {
        border-color: #CC7700;
    }
</style>
"""


def _lcars_banner(text: str, color: str = LCARS_GOLD, bg: str = LCARS_PANEL) -> str:
    return (
        f"<div style='background:{bg}; border-left:6px solid {color}; "
        f"padding:10px 16px; border-radius:0 8px 8px 0; margin:6px 0; "
        f"font-size:14px; font-weight:bold; color:{color};'>"
        f"{text}</div>"
    )


def _lcars_alert_banner(status: str) -> str:
    color = ALERT_COLORS.get(status, "gray")
    label = ALERT_LABELS.get(status, status)
    return (
        f"<div style='background:linear-gradient(90deg, {color}22, {color}44); "
        f"border:2px solid {color}; border-radius:8px; padding:12px; "
        f"text-align:center; font-size:20px; font-weight:bold; "
        f"color:{color}; letter-spacing:3px; margin:8px 0;'>"
        f"{label}</div>"
    )


def _worst_stoplight(level: Any) -> str:
    if isinstance(level, dict):
        worst = "GREEN"
        for v in level.values():
            s = str(v)
            if _STOPLIGHT_SEVERITY.get(s, 0) > _STOPLIGHT_SEVERITY.get(worst, 0):
                worst = s
        return worst
    return str(level)


# ── Data loading ─────────────────────────────────────────────────────────

@st.cache_data
def load_history() -> list[dict[str, Any]]:
    if not os.path.isfile(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_notebook() -> dict[str, Any]:
    if not os.path.isfile(NOTEBOOK_PATH):
        return {}
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_spatial_layout() -> dict[str, Any]:
    if not os.path.isfile(LAYOUT_PATH):
        return {}
    with open(LAYOUT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_airflow() -> dict[str, Any]:
    if not os.path.isfile(AIRFLOW_PATH):
        return {}
    with open(AIRFLOW_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_pathogen_profiles() -> dict[str, Any]:
    if not os.path.isfile(PATHOGEN_PATH):
        return {}
    with open(PATHOGEN_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_protocols() -> dict[str, Any]:
    if not os.path.isfile(PROTOCOLS_PATH):
        return {}
    with open(PROTOCOLS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_zone_coords(layout: dict[str, Any]) -> dict[str, dict[str, float]]:
    coords: dict[str, dict[str, float]] = {}
    for zone in layout.get("zones", []):
        display = zone.get("display", {})
        coords[zone["id"]] = {
            "x": display.get("x", 0),
            "y": display.get("y", 0),
            "type": zone.get("type", "Free"),
            "deck": zone.get("deck", "main"),
            "volume_m3": zone.get("volume_m3", 100),
        }
    return coords


# ══════════════════════════════════════════════════════════════════════════
# Station 1: Bridge Status Display
# ══════════════════════════════════════════════════════════════════════════

def render_bridge_status(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
) -> None:
    """Ship status, biosensor telemetry, contagion progression, resource allocation."""

    if not history:
        st.warning("No telemetry data loaded. Awaiting sensor input.")
        return

    last = history[-1]
    summary = last["summary"]
    num_epochs = len(history)

    # ── Ship Status ───────────────────────────────────────────────
    st.subheader("Ship Status")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    total_pop = (
        summary.get("susceptible", 0)
        + summary.get("infected", 0)
        + summary.get("recovered", 0)
        + summary.get("immune", 0)
        + summary.get("isolated", 0)
    )
    with col1:
        st.metric("Crew Complement", total_pop)
    with col2:
        st.metric("Infected", summary.get("infected", 0))
    with col3:
        st.metric("Symptomatic", summary.get("symptomatic", 0))
    with col4:
        st.metric("Confined to Quarters", summary.get("quarantined", 0))
    with col5:
        st.metric("Isolation Ward", summary.get("isolated", 0))
    with col6:
        st.metric("Non-Compliant", summary.get("quarantine_refusers", 0))

    # Alert condition banner
    status = last["trigger_status"]
    st.markdown(_lcars_alert_banner(status), unsafe_allow_html=True)

    # ── Biosensor Telemetry (Infection Counters) ──────────────────
    counters = last.get("infection_counters", {})
    if counters:
        st.subheader("Biosensor Telemetry")
        counter_cols = st.columns(min(len(counters), 5))
        for idx, (cid, cdata) in enumerate(counters.items()):
            col = counter_cols[idx % len(counter_cols)]
            label = cdata.get("label", cid)
            value = cdata.get("value", 0)
            threshold = cdata.get("threshold")
            exceeded = cdata.get("exceeded", False)
            if "rate" in cid:
                display_val = f"{value:.1%}"
            else:
                display_val = f"{value:.0f}"
            suffix = ""
            if threshold is not None:
                if "rate" in cid:
                    suffix = f" (thr: {threshold:.1%})"
                else:
                    suffix = f" (thr: {threshold})"
            with col:
                if exceeded:
                    st.metric(f"ALERT: {label}", display_val + suffix)
                else:
                    st.metric(label, display_val + suffix)

        # Infection counter time series
        _render_counter_time_series(history)

    # ── Agent Class Breakdown ─────────────────────────────────────
    _render_class_breakdown(last)

    # ── Contagion Progression ─────────────────────────────────────
    st.subheader("Contagion Progression")
    fig = _build_epidemic_curve(history)
    st.plotly_chart(fig, use_container_width=True)

    # ── Multi-Pathogen Breakdown ──────────────────────────────────
    multi_path = last.get("multi_pathogen", {})
    if multi_path and len(multi_path) > 1:
        _render_pathogen_curves(history)

    # ── Wearable Physiological Monitoring ─────────────────────────
    _render_wearable_monitoring(history)

    # ── Transmission Pathway Analysis ─────────────────────────────
    _render_transmission_pathways(history)

    # ── Resource Allocation ───────────────────────────────────────
    st.subheader("Resource Allocation")

    audit = notebook.get("FINANCIAL_AUDIT", {})
    fin_summary = audit.get("summary", {})

    if fin_summary:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "Starting Allocation",
                f"${fin_summary.get('starting_financial_budget_usd', 0):,.0f}",
            )
            st.metric(
                "Remaining Balance",
                f"${fin_summary.get('remaining_balance_usd', 0):,.0f}",
            )
        with c2:
            st.metric(
                "Surveillance Expenditure",
                f"${fin_summary.get('surveillance_cost_usd', 0):,.0f}",
            )
            st.metric(
                "Surveillance Labour",
                f"{fin_summary.get('surveillance_labor_hours', 0):.1f} hrs",
            )
        with c3:
            st.metric(
                "Intervention Expenditure",
                f"${fin_summary.get('intervention_cost_usd', 0):,.0f}",
            )
            st.metric(
                "Intervention Labour",
                f"{fin_summary.get('intervention_labor_hours', 0):.1f} hrs",
            )

        # Expenditure over time
        cost_by_epoch = audit.get("cost_by_epoch", [])
        if cost_by_epoch:
            st.markdown(
                _lcars_banner("Cumulative Expenditure by Epoch"),
                unsafe_allow_html=True,
            )
            epochs_x = []
            surv_cum: list[float] = []
            intv_cum: list[float] = []
            running_surv = 0.0
            running_intv = 0.0
            for entry in cost_by_epoch:
                epochs_x.append(entry.get("epoch", 0))
                running_surv += entry.get("surveillance_usd", 0)
                running_intv += entry.get("intervention_usd", 0)
                surv_cum.append(running_surv)
                intv_cum.append(running_intv)

            cost_fig = go.Figure()
            cost_fig.add_trace(go.Scatter(
                x=epochs_x, y=surv_cum, mode="lines+markers",
                name="Surveillance", fill="tozeroy",
                line={"color": LCARS_BLUE},
            ))
            cost_fig.add_trace(go.Scatter(
                x=epochs_x, y=intv_cum, mode="lines+markers",
                name="Intervention", fill="tozeroy",
                line={"color": LCARS_RED},
            ))
            cost_fig.update_layout(
                **LCARS_PLOTLY, height=280,
                xaxis_title="Epoch (Stardate)", yaxis_title="Cumulative Credits (USD)",
                margin={"t": 30, "b": 40, "l": 50, "r": 20},
                legend={"orientation": "h", "y": 1.1, "x": 0.5, "xanchor": "center"},
            )
            st.plotly_chart(cost_fig, use_container_width=True)

        # Material supply status
        mat_inv = audit.get("material_inventory", {})
        if mat_inv:
            st.markdown(
                _lcars_banner("Supply Manifest", LCARS_PEACH),
                unsafe_allow_html=True,
            )
            mat_rows = []
            for item, data in mat_inv.items():
                remaining = data.get("remaining", 0)
                starting = data.get("starting", 0)
                consumed = data.get("consumed", 0)
                pct = (remaining / starting * 100) if starting > 0 else 0
                warn = " DEPLETED" if remaining == 0 and consumed > 0 else ""
                mat_rows.append({
                    "Item": item,
                    "Starting": starting,
                    "Consumed": consumed,
                    "Remaining": remaining,
                    "% Left": f"{pct:.0f}%{warn}",
                    "Cost USD": f"${data.get('total_cost_usd', 0):,.2f}",
                })
            st.dataframe(pd.DataFrame(mat_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Awaiting financial audit data from the quartermaster.")

    # ── SOP Activation Log ────────────────────────────────────────
    st.subheader("Standing Orders Log")

    proto_summary = notebook.get("PROTOCOL_SUMMARY", {})
    event_log = proto_summary.get("event_log", [])
    if event_log:
        sop_rows = []
        for ev in event_log:
            sop_rows.append({
                "Epoch": ev.get("epoch", ""),
                "Event": ev.get("event", ""),
                "Protocol": ev.get("protocol_id", ""),
                "Designation": ev.get("name", ""),
            })
        st.dataframe(pd.DataFrame(sop_rows), use_container_width=True, hide_index=True)

        still_active = proto_summary.get("protocols_still_active", [])
        if still_active:
            st.markdown(
                _lcars_banner(
                    f"Protocols still active: {', '.join(still_active)}",
                    LCARS_GOLD,
                ),
                unsafe_allow_html=True,
            )
    else:
        st.info("No protocol activation events recorded.")


def _render_counter_time_series(history: list[dict[str, Any]]) -> None:
    """Line chart of infection counter values across all epochs."""
    all_cids: list[str] = []
    cid_labels: dict[str, str] = {}
    for rec in history:
        for cid, cdata in rec.get("infection_counters", {}).items():
            if cid not in cid_labels:
                all_cids.append(cid)
                cid_labels[cid] = cdata.get("label", cid)

    if not all_cids:
        return

    # Only chart rate-type counters (most useful over time)
    rate_cids = [c for c in all_cids if "rate" in c]
    count_cids = [c for c in all_cids if "rate" not in c]

    if rate_cids:
        fig = go.Figure()
        colors = [LCARS_GOLD, LCARS_BLUE, LCARS_PURPLE, LCARS_GREEN, LCARS_RED]
        for i, cid in enumerate(rate_cids):
            epochs = []
            values = []
            threshold = None
            for rec in history:
                cdata = rec.get("infection_counters", {}).get(cid, {})
                epochs.append(rec["epoch"])
                values.append(cdata.get("value", 0))
                if threshold is None:
                    threshold = cdata.get("threshold")
            fig.add_trace(go.Scatter(
                x=epochs, y=values, mode="lines+markers",
                name=cid_labels.get(cid, cid),
                line={"color": colors[i % len(colors)], "width": 2},
            ))
            if threshold is not None:
                fig.add_hline(
                    y=threshold, line_dash="dash",
                    line_color=LCARS_RED,
                    annotation_text=f"Threshold ({threshold:.1%})",
                    annotation_position="top right",
                    annotation_font_color=LCARS_RED,
                )

        fig.update_layout(
            **LCARS_PLOTLY, height=300,
            title="Attack Rate Tracking",
            xaxis_title="Epoch", yaxis_title="Rate",
            yaxis_tickformat=".1%",
            margin={"t": 50, "b": 40, "l": 60, "r": 20},
            legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(fig, use_container_width=True)

    if count_cids:
        fig = go.Figure()
        colors = [LCARS_PEACH, LCARS_TAN, LCARS_AMBER, LCARS_PURPLE]
        for i, cid in enumerate(count_cids):
            epochs = []
            values = []
            for rec in history:
                cdata = rec.get("infection_counters", {}).get(cid, {})
                epochs.append(rec["epoch"])
                values.append(cdata.get("value", 0))
            fig.add_trace(go.Bar(
                x=epochs, y=values,
                name=cid_labels.get(cid, cid),
                marker_color=colors[i % len(colors)],
            ))
        fig.update_layout(
            **LCARS_PLOTLY, height=280,
            title="Infection Count Tracking",
            xaxis_title="Epoch", yaxis_title="Count",
            barmode="group",
            margin={"t": 50, "b": 40, "l": 50, "r": 20},
            legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_class_breakdown(last: dict[str, Any]) -> None:
    """Agent class breakdown showing infection distribution across classes."""
    agents = last.get("agents", [])
    if not agents:
        return

    class_stats: dict[str, dict[str, int]] = {}
    for a in agents:
        cls = a.get("agent_class", "unknown")
        if cls not in class_stats:
            class_stats[cls] = {
                "total": 0, "infected": 0, "symptomatic": 0,
                "recovered": 0, "quarantined": 0,
            }
        class_stats[cls]["total"] += 1
        status = a.get("status", "")
        if status in ("symptomatic", "non_compliant", "asymptomatic_shedding"):
            class_stats[cls]["infected"] += 1
        if status == "symptomatic":
            class_stats[cls]["symptomatic"] += 1
        if status == "recovered":
            class_stats[cls]["recovered"] += 1
        if status == "quarantined":
            class_stats[cls]["quarantined"] += 1

    if len(class_stats) <= 1:
        return

    st.subheader("Crew Manifest by Division")
    rows = []
    for cls, stats in sorted(class_stats.items()):
        role = "Command" if cls.startswith("crew") else "Civilian"
        attack_rate = (stats["symptomatic"] / stats["total"] * 100) if stats["total"] > 0 else 0
        rows.append({
            "Division": cls.replace("_", " ").title(),
            "Role": role,
            "Complement": stats["total"],
            "Infected": stats["infected"],
            "Symptomatic": stats["symptomatic"],
            "Recovered": stats["recovered"],
            "Confined": stats["quarantined"],
            "Attack Rate": f"{attack_rate:.1f}%",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_pathogen_curves(history: list[dict[str, Any]]) -> None:
    """Per-pathogen epidemic curves when multiple pathogens are active."""
    st.subheader("Multi-Threat Analysis")

    all_pids: set[str] = set()
    for rec in history:
        all_pids.update(rec.get("multi_pathogen", {}).keys())

    if len(all_pids) < 2:
        return

    colors = [LCARS_RED, LCARS_BLUE, LCARS_GOLD, LCARS_PURPLE, LCARS_GREEN,
              LCARS_PEACH, LCARS_TAN, LCARS_AMBER]

    fig = go.Figure()
    for i, pid in enumerate(sorted(all_pids)):
        epochs = []
        infected = []
        for rec in history:
            epochs.append(rec["epoch"])
            pdata = rec.get("multi_pathogen", {}).get(pid, {})
            infected.append(pdata.get("infected", 0) + pdata.get("symptomatic", 0))
        fig.add_trace(go.Scatter(
            x=epochs, y=infected, mode="lines+markers",
            name=pid.replace("_", " ").title(),
            line={"color": colors[i % len(colors)], "width": 2},
        ))

    fig.update_layout(
        **LCARS_PLOTLY, height=300,
        title="Per-Pathogen Active Infections",
        xaxis_title="Epoch", yaxis_title="Active Infections",
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_wearable_monitoring(history: list[dict[str, Any]]) -> None:
    """Wearable physiological monitoring readout."""
    has_wearable = any(rec.get("wearable_monitoring") for rec in history)
    if not has_wearable:
        return

    st.subheader("Physiological Monitoring Array")

    last = history[-1]
    wm = last.get("wearable_monitoring", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Monitored Crew", wm.get("total_monitored", 0))
    with c2:
        st.metric("Fever Detected", wm.get("fever_count", 0))
    with c3:
        st.metric("Fever Rate", f"{wm.get('fever_rate', 0):.1%}")
    with c4:
        st.metric("Anomalies", wm.get("anomaly_count", 0))

    # Channel anomaly breakdown
    channel_counts = wm.get("channel_anomaly_counts", {})
    if channel_counts:
        cols = st.columns(len(channel_counts))
        for i, (ch, cnt) in enumerate(channel_counts.items()):
            with cols[i]:
                st.metric(ch.replace("_", " ").title(), cnt)

    # Time series
    epochs = []
    fever_rates = []
    anomaly_rates = []
    for rec in history:
        wm_rec = rec.get("wearable_monitoring", {})
        if wm_rec:
            epochs.append(rec["epoch"])
            fever_rates.append(wm_rec.get("fever_rate", 0))
            anomaly_rates.append(wm_rec.get("anomaly_rate", 0))

    if epochs:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=epochs, y=fever_rates, mode="lines+markers",
            name="Fever Rate", line={"color": LCARS_RED, "width": 2},
        ))
        fig.add_trace(go.Scatter(
            x=epochs, y=anomaly_rates, mode="lines+markers",
            name="Anomaly Rate", line={"color": LCARS_GOLD, "width": 2},
        ))
        fig.update_layout(
            **LCARS_PLOTLY, height=260,
            title="Wearable Monitoring Trends",
            xaxis_title="Epoch", yaxis_title="Rate",
            yaxis_tickformat=".1%",
            margin={"t": 50, "b": 40, "l": 60, "r": 20},
            legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_transmission_pathways(history: list[dict[str, Any]]) -> None:
    """Transmission pathway breakdown from contact tracing data."""
    pathway_totals: dict[str, float] = {}
    for rec in history:
        ct = rec.get("contact_tracing", {})
        events = ct.get("transmission_events", [])
        for ev in events:
            breakdown = ev.get("pathway_breakdown", {})
            if breakdown:
                for key, dose in breakdown.items():
                    pw = key.split(":")[0] if ":" in key else key
                    pathway_totals[pw] = pathway_totals.get(pw, 0) + dose
            else:
                pw = ev.get("dominant_pathway", ev.get("pathway", "unknown"))
                pathway_totals[pw] = pathway_totals.get(pw, 0) + ev.get("total_dose", 1)

    pathway_totals.pop("none", None)
    if not pathway_totals:
        return

    st.subheader("Transmission Vector Analysis")

    pathway_labels = {
        "direct_contact": "Direct Contact",
        "droplet": "Droplet",
        "hvac_airborne": "HVAC Airborne",
        "fomite": "Fomite Surface",
        "food_contamination": "Food Contamination",
        "environmental": "Environmental (HVAC Colonization)",
    }

    labels = []
    values = []
    colors = [LCARS_BLUE, LCARS_PURPLE, LCARS_GOLD, LCARS_PEACH, LCARS_GREEN, LCARS_RED,
              LCARS_TAN, LCARS_AMBER]
    for pw, count in sorted(pathway_totals.items(), key=lambda x: -x[1]):
        labels.append(pathway_labels.get(pw, pw.replace("_", " ").title()))
        values.append(count)

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors[:len(labels)]),
        textinfo="label+percent",
        textfont=dict(color="white"),
        hole=0.4,
    )])
    fig.update_layout(
        **LCARS_PLOTLY, height=350,
        title="Transmission Pathway Distribution",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Pathway dose table
    pw_rows = [{"Pathway": l, "Total Dose": f"{v:,.1f}"} for l, v in zip(labels, values)]
    st.dataframe(pd.DataFrame(pw_rows), use_container_width=True, hide_index=True)


def _build_epidemic_curve(history: list[dict[str, Any]]) -> go.Figure:
    epochs = []
    susceptible = []
    infected = []
    quarantined = []
    isolated = []
    recovered = []
    for record in history:
        epochs.append(record["epoch"])
        s = record["summary"]
        susceptible.append(s.get("susceptible", 0))
        infected.append(s.get("infected", 0) + s.get("symptomatic", 0))
        quarantined.append(s.get("quarantined", 0))
        isolated.append(s.get("isolated", 0))
        recovered.append(s.get("recovered", 0))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs, y=susceptible, mode="lines+markers",
        name="Susceptible (S)", line={"color": LCARS_BLUE, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=infected, mode="lines+markers",
        name="Infected (I)", line={"color": LCARS_RED, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=quarantined, mode="lines+markers",
        name="Confined to Quarters (Q)", line={"color": LCARS_GOLD, "width": 2, "dash": "dash"},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=isolated, mode="lines+markers",
        name="Isolation Ward", line={"color": LCARS_PURPLE, "width": 2, "dash": "dashdot"},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=recovered, mode="lines+markers",
        name="Recovered (R)", line={"color": LCARS_GREEN, "width": 2, "dash": "dot"},
    ))

    for record in history:
        epoch = record["epoch"]
        status = record["trigger_status"]
        if epoch > 0:
            prev_status = history[epoch - 1]["trigger_status"]
            if status != prev_status:
                fig.add_vline(
                    x=epoch, line_dash="dash",
                    line_color=ALERT_COLORS.get(status, "gray"),
                    annotation_text=f"{ALERT_LABELS.get(status, status)}",
                    annotation_position="top",
                    annotation_font_color=ALERT_COLORS.get(status, "gray"),
                )

    fig.update_layout(
        **LCARS_PLOTLY, height=350,
        xaxis_title="Epoch (Stardate)", yaxis_title="Personnel Count",
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════
# Station 2: Tactical Sensor Grid
# ══════════════════════════════════════════════════════════════════════════

def render_tactical_grid(
    history: list[dict[str, Any]],
    zone_coords: dict[str, dict[str, float]],
    adjacency: list[dict[str, str]],
) -> None:
    """Spatial deck map with toggleable colour mode and epoch slider."""

    if not history:
        st.warning("Sensors offline. No telemetry data.")
        return

    num_epochs = len(history)

    col_ctrl1, col_ctrl2 = st.columns([2, 3])
    with col_ctrl1:
        selected_epoch = st.slider(
            "Epoch", min_value=0, max_value=num_epochs - 1,
            value=0, key="deck_epoch",
        )
    with col_ctrl2:
        color_mode = st.radio(
            "Sensor Overlay",
            ["Airborne Aerosol Mass", "Surface Fomite Contamination", "Symptomatic Agent Count"],
            horizontal=True,
            key="deck_color",
        )

    record = history[selected_epoch]
    status = record["trigger_status"]

    st.markdown(_lcars_alert_banner(status), unsafe_allow_html=True)

    # Build the map
    fig = _build_deck_map(record, zone_coords, adjacency, color_mode)
    st.plotly_chart(fig, use_container_width=True)

    # Stoplights row
    stoplights = record.get("reactive_protocols", {}).get("stoplights", {})
    if stoplights:
        st.markdown(
            _lcars_banner("Instrument Sensor Array", LCARS_BLUE),
            unsafe_allow_html=True,
        )
        cols = st.columns(len(stoplights))
        for i, (inst, level) in enumerate(stoplights.items()):
            resolved = _worst_stoplight(level)
            color = STOPLIGHT_COLORS.get(resolved, "gray")
            short = inst.replace("_", " ").title()[:20]
            with cols[i]:
                st.markdown(
                    f"<div style='background:{color}22; border:2px solid {color}; "
                    f"padding:6px; border-radius:6px; text-align:center; "
                    f"color:{color}; font-size:11px; font-weight:bold;'>"
                    f"{short}<br>{resolved}</div>",
                    unsafe_allow_html=True,
                )

    # Active protocols for this epoch
    active = record.get("reactive_protocols", {}).get("active_protocols", [])
    if active:
        names = [p.get("name", p.get("protocol_id", "?")) for p in active]
        st.markdown(
            _lcars_banner(f"Active Standing Orders: {', '.join(names)}", LCARS_GOLD),
            unsafe_allow_html=True,
        )

    # Agent location table
    with st.expander(f"Crew Disposition — Epoch {selected_epoch}", expanded=False):
        agents = record.get("agents", [])
        if agents:
            df = pd.DataFrame(agents).sort_values("agent_id")
            st.dataframe(df, use_container_width=True, hide_index=True)


def _build_deck_map(
    record: dict[str, Any],
    zone_coords: dict[str, dict[str, float]],
    adjacency: list[dict[str, str]],
    color_mode: str,
) -> go.Figure:
    fig = go.Figure()

    # Adjacency edges
    for link in adjacency:
        fz = link.get("from", "")
        tz = link.get("to", "")
        if fz in zone_coords and tz in zone_coords:
            fig.add_trace(go.Scatter(
                x=[zone_coords[fz]["x"], zone_coords[tz]["x"]],
                y=[zone_coords[fz]["y"], zone_coords[tz]["y"]],
                mode="lines",
                line={"color": "rgba(255,153,0,0.25)", "width": 1.5},
                hoverinfo="skip", showlegend=False,
            ))

    # Agent locations
    agent_locations: dict[str, int] = {}
    symptomatic_per_zone: dict[str, int] = {}
    quarantined_per_zone: dict[str, int] = {}
    for agent in record.get("agents", []):
        loc = agent.get("location", "unknown")
        agent_locations[loc] = agent_locations.get(loc, 0) + 1
        if agent.get("status") in ("symptomatic", "infected"):
            symptomatic_per_zone[loc] = symptomatic_per_zone.get(loc, 0) + 1
        if agent.get("status") == "quarantined":
            quarantined_per_zone[loc] = quarantined_per_zone.get(loc, 0) + 1

    spaces = record.get("spaces", {})
    obs = record.get("observation_engine", {})

    zone_names: list[str] = []
    xs: list[float] = []
    ys: list[float] = []
    sizes: list[float] = []
    colors: list[float] = []
    hover_texts: list[str] = []

    for zname, zinfo in zone_coords.items():
        zone_names.append(zname)
        xs.append(zinfo["x"])
        ys.append(zinfo["y"])

        occupants = agent_locations.get(zname, 0)
        sizes.append(max(20, 15 + occupants * 8))

        mass = spaces.get(zname, {}).get("pathogen_mass", 0.0)
        surface_mass = obs.get("surface_swab", {}).get(zname, {}).get("surface_mass", 0.0)
        symp_count = symptomatic_per_zone.get(zname, 0)
        quar_count = quarantined_per_zone.get(zname, 0)

        if color_mode == "Airborne Aerosol Mass":
            colors.append(mass)
        elif color_mode == "Surface Fomite Contamination":
            colors.append(surface_mass)
        else:
            colors.append(float(symp_count))

        hover_texts.append(
            f"<b>{zname}</b><br>"
            f"Type: {zinfo['type']}<br>"
            f"Occupants: {occupants}<br>"
            f"Aerosol mass: {mass:.2f}<br>"
            f"Surface mass: {surface_mass:.2f}<br>"
            f"Symptomatic: {symp_count}<br>"
            f"Confined: {quar_count}"
        )

    max_val = max(colors) if colors and max(colors) > 0 else 1.0

    colorbar_title = {
        "Airborne Aerosol Mass": "Aerosol<br>Mass",
        "Surface Fomite Contamination": "Surface<br>Mass",
        "Symptomatic Agent Count": "Sympto-<br>matic",
    }.get(color_mode, "Value")

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        text=zone_names,
        textposition="top center",
        textfont={"size": 11, "color": LCARS_PEACH},
        marker={
            "size": sizes,
            "color": colors,
            "colorscale": [
                [0.0, LCARS_GREEN], [0.3, LCARS_GOLD],
                [0.6, LCARS_AMBER], [1.0, LCARS_RED],
            ],
            "cmin": 0,
            "cmax": max(max_val, 0.01),
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.6},
            "line": {"width": 2, "color": LCARS_PEACH},
        },
        hovertext=hover_texts, hoverinfo="text", showlegend=False,
    ))

    fig.update_layout(
        title=f"Tactical Deck Scan — Epoch {record['epoch']} ({color_mode})",
        **LCARS_PLOTLY, height=420,
        xaxis={"title": "Ship Length (m)", "range": [0, 120], "showgrid": False},
        yaxis={
            "title": "Beam (m)", "range": [0, 15], "showgrid": False,
            "scaleanchor": "x", "scaleratio": 1,
        },
        margin={"t": 60, "b": 40, "l": 50, "r": 80},
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════
# Station 3: Sickbay Diagnostic Console
# ══════════════════════════════════════════════════════════════════════════

def render_sickbay_console(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
) -> None:
    """Dr. Crusher's lab notebook at three fidelity tiers."""

    if not notebook:
        st.warning("Sickbay offline. No diagnostic data available.")
        return

    records = notebook.get("records", [])
    fidelity_defs = notebook.get("fidelity_tier_definitions", {})

    st.markdown(
        _lcars_banner(
            f"Medical Log v{notebook.get('version', '?')} — "
            f"{notebook.get('total_records', 0)} records — "
            f"Fidelity: {records[0].get('fidelity_tier', '?') if records else '?'}",
            LCARS_BLUE,
        ),
        unsafe_allow_html=True,
    )

    # Fidelity selector
    fidelity = st.radio(
        "Diagnostic Resolution",
        ["LOW_FIDELITY", "MID_FIDELITY", "HIGH_FIDELITY"],
        index=2,
        horizontal=True,
        key="fidelity_select",
    )

    if fidelity_defs.get(fidelity):
        st.caption(fidelity_defs[fidelity])

    # Assay type filter
    assay_types = sorted({r.get("assay_type", "") for r in records})
    selected_assays = st.multiselect(
        "Filter by Assay Type", assay_types, default=assay_types,
        key="assay_filter",
    )

    filtered = [r for r in records if r.get("assay_type") in selected_assays]

    if not filtered:
        st.info("No records match the current diagnostic filters.")
        return

    if fidelity == "LOW_FIDELITY":
        _render_low_fidelity(filtered, history)
    elif fidelity == "MID_FIDELITY":
        _render_mid_fidelity(filtered)
    else:
        _render_high_fidelity(filtered)


def _render_low_fidelity(
    records: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> None:
    """Stoplight-only strategic view."""

    st.subheader("Strategic Sensor Overview")

    if history:
        instruments = set()
        for rec in history:
            sl = rec.get("reactive_protocols", {}).get("stoplights", {})
            instruments.update(sl.keys())
        instruments_sorted = sorted(instruments)

        if instruments_sorted:
            rows = []
            for rec in history:
                sl = rec.get("reactive_protocols", {}).get("stoplights", {})
                row: dict[str, Any] = {"Epoch": rec["epoch"]}
                for inst in instruments_sorted:
                    raw = sl.get(inst, "--")
                    row[inst.replace("_", " ").title()[:22]] = _worst_stoplight(raw) if isinstance(raw, dict) else raw
                rows.append(row)

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

    detected = sum(1 for r in records if r.get("binary_result") == "DETECTED")
    not_det = sum(1 for r in records if r.get("binary_result") == "NOT DETECTED")
    st.markdown(
        _lcars_banner(
            f"Total: {len(records)} records | {detected} DETECTED | {not_det} NOT DETECTED",
            LCARS_PEACH,
        ),
        unsafe_allow_html=True,
    )


def _render_mid_fidelity(records: list[dict[str, Any]]) -> None:
    """CAP-certified clinical reports table."""

    st.subheader("Certified Diagnostic Reports")

    rows = []
    for r in records:
        row = {
            "Epoch": r.get("timestamp_epoch", ""),
            "Compartment": r.get("collection_zone", ""),
            "Assay": r.get("assay_type", ""),
            "Result": r.get("binary_result", ""),
            "Ct": r.get("ct_value"),
            "Anomaly": r.get("inferred_anomaly_score"),
            "QC": r.get("qc_status", ""),
        }
        if r.get("patient_id") is not None:
            row["Patient"] = r["patient_id"]
        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_high_fidelity(records: list[dict[str, Any]]) -> None:
    """Raw instrument telemetry with interactive charts."""

    st.subheader("Raw Sensor Telemetry")

    tab_amp, tab_kingdom, tab_raw = st.tabs([
        "qPCR Amplification Curves",
        "GRUMB Kingdom Reads",
        "Raw Data Stream",
    ])

    with tab_amp:
        _render_amplification_curves(records)

    with tab_kingdom:
        _render_kingdom_charts(records)

    with tab_raw:
        df = pd.DataFrame(records)
        cols_to_drop = [c for c in df.columns if c == "raw_amplification_curve"]
        display_df = df.drop(columns=cols_to_drop, errors="ignore")
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_amplification_curves(records: list[dict[str, Any]]) -> None:
    """Interactive line charts for qPCR 40-cycle amplification curves."""

    curve_records = [
        r for r in records
        if r.get("raw_amplification_curve") and len(r["raw_amplification_curve"]) > 0
    ]

    if not curve_records:
        st.info("No amplification curve data in current selection.")
        return

    by_assay: dict[str, list[dict[str, Any]]] = {}
    for r in curve_records:
        at = r.get("assay_type", "unknown")
        by_assay.setdefault(at, []).append(r)

    for assay_type, recs in by_assay.items():
        st.markdown(
            _lcars_banner(
                f"{assay_type.replace('_', ' ').title()} — {len(recs)} curves",
                LCARS_PURPLE,
            ),
            unsafe_allow_html=True,
        )

        fig = go.Figure()
        for r in recs[:12]:
            curve = r["raw_amplification_curve"]
            cycles = list(range(1, len(curve) + 1))
            label = f"E{r.get('timestamp_epoch', '?')}-{r.get('collection_zone', '?')[:8]}"
            ct = r.get("ct_value")
            if ct is not None:
                label += f" Ct={ct:.1f}"
            fig.add_trace(go.Scatter(
                x=cycles, y=curve, mode="lines", name=label,
                line={"width": 1.5},
            ))

        fig.update_layout(
            **LCARS_PLOTLY, height=350,
            xaxis_title="Cycle", yaxis_title="Fluorescence (RFU)",
            margin={"t": 30, "b": 40, "l": 50, "r": 20},
            legend={"font": {"size": 9}},
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_kingdom_charts(records: list[dict[str, Any]]) -> None:
    """Stacked bar charts for GRUMB multi-kingdom relative abundance reads."""

    ww_records = [
        r for r in records
        if r.get("assay_type") == "metagenomic_sequencing"
        and r.get("kingdom_reads")
    ]

    if not ww_records:
        st.info("No metagenomic data in current selection.")
        return

    kingdoms = ["Bacteria", "Archaea", "Fungi", "Virus"]
    kingdom_colors = {
        "Bacteria": LCARS_BLUE,
        "Archaea": LCARS_PURPLE,
        "Fungi": LCARS_GREEN,
        "Virus": LCARS_RED,
    }

    epochs = [r.get("timestamp_epoch", 0) for r in ww_records]
    labels = [
        f"E{r.get('timestamp_epoch', '?')}-{r.get('collection_zone', '?')[:6]}"
        for r in ww_records
    ]

    fig = go.Figure()
    for kingdom in kingdoms:
        values = [r.get("kingdom_reads", {}).get(kingdom, 0) for r in ww_records]
        fig.add_trace(go.Bar(
            x=labels, y=values, name=kingdom,
            marker_color=kingdom_colors.get(kingdom, "gray"),
        ))

    fig.update_layout(
        barmode="stack",
        **LCARS_PLOTLY, height=380,
        xaxis_title="Sample", yaxis_title="Read Counts",
        title="Multi-Kingdom Metagenomic Analysis",
        margin={"t": 50, "b": 60, "l": 50, "r": 20},
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)

    clr_records = [r for r in ww_records if r.get("kingdom_clr_deltas")]
    if clr_records:
        st.markdown(
            _lcars_banner("CLR-Space Anomaly Deltas", LCARS_PURPLE),
            unsafe_allow_html=True,
        )
        clr_rows = []
        for r in clr_records:
            deltas = r["kingdom_clr_deltas"]
            clr_rows.append({
                "Epoch": r.get("timestamp_epoch", ""),
                "Compartment": r.get("collection_zone", ""),
                "Bacteria": f"{deltas.get('Bacteria', 0):+.3f}",
                "Archaea": f"{deltas.get('Archaea', 0):+.3f}",
                "Fungi": f"{deltas.get('Fungi', 0):+.3f}",
                "Virus": f"{deltas.get('Virus', 0):+.3f}",
                "Anomaly": f"{r.get('inferred_anomaly_score', 0):.3f}",
            })
        st.dataframe(pd.DataFrame(clr_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# Station 4: Standing Orders & Threat Profiles
# ══════════════════════════════════════════════════════════════════════════

def render_standing_orders(
    pathogen_data: dict[str, Any],
    protocol_data: dict[str, Any],
) -> None:
    """Display pathogen threat profiles and standing order configurations."""

    # ── Threat Profiles ───────────────────────────────────────────
    st.subheader("Active Threat Profiles")

    pathogens = pathogen_data.get("pathogens", [])
    if isinstance(pathogens, list):
        for p in pathogens:
            with st.expander(
                f"{p.get('pathogen_id', '?')} — {p.get('name', '?')}",
                expanded=True,
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Classification:** {p.get('category', '?')}")
                    st.markdown(f"**Introduction Epoch:** {p.get('introduction_epoch', 0)}")
                    routes = p.get("transmission_routes", [])
                    st.markdown(f"**Transmission Vectors:** {', '.join(routes)}")
                    dr = p.get("dose_response", {})
                    if dr:
                        st.markdown(f"**Dose-Response Model:** {dr.get('model', '?')}")
                with c2:
                    shed = p.get("shedding_profile", {})
                    if shed:
                        st.markdown(f"**Peak Shedding:** {shed.get('peak_log10', '?')} log10")
                        st.markdown(f"**Duration:** {shed.get('duration_days', '?')} days")
                    fc = p.get("food_contamination", {})
                    if fc.get("enabled"):
                        st.markdown(
                            f"**Food Contamination:** growth={fc.get('growth_rate_per_epoch', 0)}/epoch, "
                            f"decay={fc.get('decay_rate_per_epoch', 0)}/epoch"
                        )
                    ecc = p.get("environmental_contamination", {})
                    if ecc.get("enabled"):
                        p2p = "yes" if ecc.get("person_to_person", True) else "no"
                        st.markdown(
                            f"**Environmental Contamination:** {ecc.get('source_type', '?')} "
                            f"(load={ecc.get('baseline_environmental_load', 0)}, "
                            f"person-to-person: {p2p})"
                        )
                    disrupt = p.get("microflora_disruption", {})
                    if disrupt:
                        st.markdown(f"**Microflora Target:** {disrupt.get('target_system', '?')}")
                        st.markdown(f"**Disruption Magnitude:** {disrupt.get('magnitude', '?')}")
    elif isinstance(pathogens, dict):
        for pid, p in pathogens.items():
            with st.expander(f"{pid} — {p.get('name', '?')}", expanded=True):
                st.json(p)
    else:
        st.info("No threat profiles loaded.")

    st.divider()

    # ── Standing Orders (SOPs) ────────────────────────────────────
    st.subheader("Standing Orders")

    protocols = protocol_data.get("protocols", [])
    if protocols:
        for p in protocols:
            trigger = p.get("trigger", {})
            inst = trigger.get("instrument_class", "?")
            level = trigger.get("stoplight_level", "?")
            color = STOPLIGHT_COLORS.get(level, "gray")
            modifiers = p.get("modifiers", {})
            exempt = modifiers.get("exempt_classes", [])

            exempt_html = ""
            if exempt:
                exempt_str = ", ".join(c.replace("_", " ").title() for c in exempt)
                exempt_html = (
                    f"<br><span style='color:{LCARS_PURPLE};'>"
                    f"Exempt Divisions: {exempt_str}</span>"
                )

            mod_keys = [k for k in modifiers.keys() if k != "exempt_classes"]

            st.markdown(
                f"<div style='border-left:6px solid {color}; padding:10px 14px; "
                f"margin:6px 0; background:{LCARS_PANEL}; "
                f"border-radius:0 8px 8px 0;'>"
                f"<b style='color:{LCARS_GOLD};'>{p.get('protocol_id', '?')}</b> "
                f"<span style='color:{LCARS_PEACH};'>— {p.get('name', '?')}</span><br>"
                f"<span style='color:{color};'>Trigger: {inst} >= {level}</span><br>"
                f"<span style='color:{LCARS_BLUE};'>Modifiers: {', '.join(mod_keys)}</span>"
                f"{exempt_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

            costs = p.get("costs_per_epoch", {})
            act_costs = p.get("activation_costs", {})
            act_cost = act_costs.get("financial_usd", 0) if act_costs else 0
            epoch_cost = costs.get("financial_usd", 0) if costs else 0
            if act_cost or epoch_cost:
                st.caption(
                    f"  Activation: ${act_cost:,.0f} | Per-epoch: ${epoch_cost:,.0f}"
                )
    else:
        st.info("No standing orders configured.")


# ══════════════════════════════════════════════════════════════════════════
# Main Bridge Interface
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="USS Crusher — Main Bridge Display",
        page_icon="🖖",
        layout="wide",
    )

    st.markdown(LCARS_CSS, unsafe_allow_html=True)

    # Title bar
    st.markdown(
        f"<div style='background:linear-gradient(90deg, {LCARS_GOLD}, {LCARS_AMBER}); "
        f"padding:12px 20px; border-radius:20px 20px 0 0; margin-bottom:4px;'>"
        f"<span style='color:{LCARS_BG}; font-size:28px; font-weight:bold; "
        f"letter-spacing:2px;'>CRUSHER TO THE BRIDGE</span>"
        f"<span style='color:{LCARS_BG}; font-size:14px; float:right; "
        f"margin-top:8px;'>NCC-1701-D  |  Biodefense Digital Twin</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    history = load_history()
    notebook = load_notebook()
    layout = load_spatial_layout()
    airflow = load_airflow()
    pathogen_data = load_pathogen_profiles()
    protocol_data = load_protocols()
    zone_coords = get_zone_coords(layout)
    adjacency = airflow.get("adjacency", [])

    if not history:
        st.error(
            "No sensor telemetry found. "
            "Run `python orchestrator.py` to initialize simulation data."
        )
        return

    # ── Sidebar: Command Summary ──────────────────────────────────
    with st.sidebar:
        last = history[-1]
        status = last["trigger_status"]

        st.markdown(
            f"<div style='text-align:center; padding:8px;'>"
            f"<span style='color:{LCARS_GOLD}; font-size:16px; "
            f"font-weight:bold; letter-spacing:2px;'>SHIP STATUS</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown(_lcars_alert_banner(status), unsafe_allow_html=True)
        st.divider()

        summary = last["summary"]
        st.metric("Epochs Elapsed", len(history))

        total_pop = (
            summary.get("susceptible", 0)
            + summary.get("infected", 0)
            + summary.get("recovered", 0)
            + summary.get("immune", 0)
            + summary.get("isolated", 0)
        )
        st.metric("Crew Complement", total_pop)
        st.metric("Confined to Quarters", summary.get("quarantined", 0))
        st.metric("Isolation Ward", summary.get("isolated", 0))
        st.metric("Non-Compliant", summary.get("quarantine_refusers", 0))

        st.divider()
        ca = last.get("cost_accounting", {})
        st.metric("Credits Remaining", f"${ca.get('financial_balance_remaining', 0):,.0f}")
        st.metric("Labour Remaining", f"{ca.get('labor_hours_remaining', 0):.1f} hrs")

        # Infection counter summary in sidebar
        counters = last.get("infection_counters", {})
        if counters:
            st.divider()
            st.markdown(
                f"<span style='color:{LCARS_GOLD}; font-size:13px; "
                f"font-weight:bold;'>BIOSENSOR READINGS</span>",
                unsafe_allow_html=True,
            )
            for cid, cdata in counters.items():
                label = cdata.get("label", cid)
                value = cdata.get("value", 0)
                exceeded = cdata.get("exceeded", False)
                if "rate" in cid:
                    val_str = f"{value:.1%}"
                else:
                    val_str = f"{value:.0f}"
                color = LCARS_RED if exceeded else LCARS_PEACH
                st.markdown(
                    f"<span style='color:{color}; font-size:12px;'>"
                    f"{'!! ' if exceeded else ''}{label}: {val_str}</span>",
                    unsafe_allow_html=True,
                )

        active_sops = last.get("reactive_protocols", {}).get("active_protocols", [])
        if active_sops:
            st.divider()
            st.markdown(
                f"<span style='color:{LCARS_GOLD}; font-size:13px; "
                f"font-weight:bold;'>ACTIVE ORDERS</span>",
                unsafe_allow_html=True,
            )
            for sop in active_sops:
                st.markdown(
                    f"<span style='color:{LCARS_PEACH}; font-size:12px;'>"
                    f"- {sop.get('name', sop.get('protocol_id', '?'))}</span>",
                    unsafe_allow_html=True,
                )

        st.divider()
        hvac = last.get("hvac", {})
        if hvac.get("transport_active"):
            st.markdown(
                f"<span style='color:{LCARS_BLUE}; font-size:12px;'>"
                f"HVAC: {hvac.get('filter_type', '?')} "
                f"({hvac.get('filter_efficiency', 0):.0%})</span>",
                unsafe_allow_html=True,
            )

    # ── Stations (Tabs) ───────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Bridge Status Display",
        "Tactical Sensor Grid",
        "Sickbay Diagnostic Console",
        "Standing Orders & Threat Profiles",
    ])

    with tab1:
        render_bridge_status(history, notebook)

    with tab2:
        render_tactical_grid(history, zone_coords, adjacency)

    with tab3:
        render_sickbay_console(history, notebook)

    with tab4:
        render_standing_orders(pathogen_data, protocol_data)


if __name__ == "__main__":
    main()
