"""
dashboard.py – Crusher-to-the-Bridge Tactical Command Deck
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-tab Streamlit app for the Crusher Labs biodefense digital twin.

Tabs:
  1. Mission Summary & Ledger
  2. Spatial Outbreak Deck
  3. Crusher Labs Portal
  4. Protocol & Configuration Profile

Usage::

    python orchestrator.py        # generate simulation data
    streamlit run dashboard.py    # launch the dashboard
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

# ── Styling ──────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "BASELINE": "#2ecc71",
    "SUSPECTED": "#f39c12",
    "CONFIRMED": "#e74c3c",
}
STATUS_ICONS = {
    "BASELINE": "●",
    "SUSPECTED": "▲",
    "CONFIRMED": "■",
}
STOPLIGHT_COLORS = {"GREEN": "#2ecc71", "AMBER": "#f39c12", "RED": "#e74c3c"}
_STOPLIGHT_SEVERITY = {"GREEN": 0, "AMBER": 1, "RED": 2}


def _worst_stoplight(level: Any) -> str:
    """Return the worst stoplight string when level may be a per-zone dict."""
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


# ── Tab 1: Mission Summary & Ledger ─────────────────────────────────────

def render_mission_summary(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
) -> None:
    """Key operational metrics, financial balance sheet, SOP log."""

    if not history:
        st.warning("No simulation history loaded.")
        return

    last = history[-1]
    first = history[0]
    summary = last["summary"]
    num_epochs = len(history)

    # ── Row 1: Key operational metrics ────────────────────────────
    st.subheader("Operational Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    total_infected = (
        summary.get("infected", 0)
        + summary.get("recovered", 0)
        + summary.get("isolated", 0)
    )
    with col1:
        st.metric("Total Crew", summary.get("susceptible", 0) + total_infected + summary.get("immune", 0))
    with col2:
        st.metric("Total Infected", total_infected)
    with col3:
        st.metric("Isolated", summary.get("isolated", 0))
    with col4:
        multi_path = last.get("multi_pathogen", {})
        co_inf = 0
        for pid, pdata in multi_path.items():
            co_inf += pdata.get("infected", 0)
        st.metric("Active Infections", co_inf)
    with col5:
        ca = last.get("cost_accounting", {})
        st.metric("Person-hrs Left", f"{ca.get('labor_hours_remaining', 0):.1f}")

    # Trigger status banner
    status = last["trigger_status"]
    st.markdown(
        f"<div style='background-color:{STATUS_COLORS.get(status, 'gray')}; "
        f"padding:8px; border-radius:6px; text-align:center; "
        f"font-size:16px; font-weight:bold; color:white; margin:8px 0;'>"
        f"{STATUS_ICONS.get(status, '?')} Final Status: {status}</div>",
        unsafe_allow_html=True,
    )

    # ── Infection Counters ─────────────────────────────────────────
    counters = last.get("infection_counters", {})
    if counters:
        st.subheader("Infection Counters (VSP Reporting)")
        counter_cols = st.columns(min(len(counters), 5))
        for idx, (cid, cdata) in enumerate(counters.items()):
            col = counter_cols[idx % len(counter_cols)]
            label = cdata.get("label", cid)
            value = cdata.get("value", 0)
            threshold = cdata.get("threshold")
            exceeded = cdata.get("exceeded", False)
            if "attack_rate" in cid:
                display_val = f"{value:.1%}"
            else:
                display_val = f"{value:.0f}"
            suffix = ""
            if threshold is not None:
                if "attack_rate" in cid:
                    suffix = f" (thr: {threshold:.1%})"
                else:
                    suffix = f" (thr: {threshold})"
            with col:
                if exceeded:
                    st.metric(f"🔴 {label}", display_val + suffix)
                else:
                    st.metric(label, display_val + suffix)

    # ── Epidemic curve ────────────────────────────────────────────
    st.subheader("Epidemic Timeline")
    fig = _build_epidemic_curve(history)
    st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Financial Balance Sheet ────────────────────────────
    st.subheader("Financial Balance Sheet")

    audit = notebook.get("FINANCIAL_AUDIT", {})
    fin_summary = audit.get("summary", {})

    if fin_summary:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "Starting Budget",
                f"${fin_summary.get('starting_financial_budget_usd', 0):,.0f}",
            )
            st.metric(
                "Remaining",
                f"${fin_summary.get('remaining_balance_usd', 0):,.0f}",
            )
        with c2:
            st.metric(
                "Surveillance Cost",
                f"${fin_summary.get('surveillance_cost_usd', 0):,.0f}",
            )
            st.metric(
                "Surv. Labor",
                f"{fin_summary.get('surveillance_labor_hours', 0):.1f} hrs",
            )
        with c3:
            st.metric(
                "Intervention Cost",
                f"${fin_summary.get('intervention_cost_usd', 0):,.0f}",
            )
            st.metric(
                "Intv. Labor",
                f"{fin_summary.get('intervention_labor_hours', 0):.1f} hrs",
            )

        # Cost over time chart
        cost_by_epoch = audit.get("cost_by_epoch", [])
        if cost_by_epoch:
            st.markdown("**Cumulative Expenditure by Epoch**")
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
                line={"color": "#3498db"},
            ))
            cost_fig.add_trace(go.Scatter(
                x=epochs_x, y=intv_cum, mode="lines+markers",
                name="Intervention", fill="tozeroy",
                line={"color": "#e74c3c"},
            ))
            cost_fig.update_layout(
                template="plotly_dark", height=280,
                xaxis_title="Epoch", yaxis_title="Cumulative USD",
                margin={"t": 30, "b": 40, "l": 50, "r": 20},
                legend={"orientation": "h", "y": 1.1, "x": 0.5, "xanchor": "center"},
            )
            st.plotly_chart(cost_fig, use_container_width=True)

        # Material supply status
        mat_inv = audit.get("material_inventory", {})
        if mat_inv:
            st.markdown("**Material Supply Consumption**")
            mat_rows = []
            for item, data in mat_inv.items():
                remaining = data.get("remaining", 0)
                starting = data.get("starting", 0)
                consumed = data.get("consumed", 0)
                pct = (remaining / starting * 100) if starting > 0 else 0
                warn = " !! DEPLETED" if remaining == 0 and consumed > 0 else ""
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
        st.info("No financial audit data available.")

    # ── Row 3: SOP Activation History ─────────────────────────────
    st.subheader("SOP Activation History")

    proto_summary = notebook.get("PROTOCOL_SUMMARY", {})
    event_log = proto_summary.get("event_log", [])
    if event_log:
        sop_rows = []
        for ev in event_log:
            sop_rows.append({
                "Epoch": ev.get("epoch", ""),
                "Event": ev.get("event", ""),
                "Protocol": ev.get("protocol_id", ""),
                "Name": ev.get("name", ""),
            })
        st.dataframe(pd.DataFrame(sop_rows), use_container_width=True, hide_index=True)

        still_active = proto_summary.get("protocols_still_active", [])
        if still_active:
            st.info(f"Still active at simulation end: **{', '.join(still_active)}**")
    else:
        st.info("No protocol activation events recorded.")


def _build_epidemic_curve(history: list[dict[str, Any]]) -> go.Figure:
    epochs = []
    susceptible = []
    infected = []
    isolated = []
    recovered = []
    for record in history:
        epochs.append(record["epoch"])
        s = record["summary"]
        susceptible.append(s.get("susceptible", 0))
        infected.append(s.get("infected", 0) + s.get("symptomatic", 0))
        isolated.append(s.get("isolated", 0))
        recovered.append(s.get("recovered", 0))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs, y=susceptible, mode="lines+markers",
        name="Susceptible (S)", line={"color": "#3498db", "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=infected, mode="lines+markers",
        name="Infected (I)", line={"color": "#e74c3c", "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=isolated, mode="lines+markers",
        name="Quarantined (Q)", line={"color": "#f39c12", "width": 2, "dash": "dash"},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=recovered, mode="lines+markers",
        name="Recovered (R)", line={"color": "#2ecc71", "width": 2, "dash": "dot"},
    ))

    for record in history:
        epoch = record["epoch"]
        status = record["trigger_status"]
        if epoch > 0:
            prev_status = history[epoch - 1]["trigger_status"]
            if status != prev_status:
                fig.add_vline(
                    x=epoch, line_dash="dash",
                    line_color=STATUS_COLORS.get(status, "gray"),
                    annotation_text=f"-> {status}",
                    annotation_position="top",
                )

    fig.update_layout(
        template="plotly_dark", height=320,
        xaxis_title="Epoch (hours)", yaxis_title="Agent Count",
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
    )
    return fig


# ── Tab 2: Spatial Outbreak Deck ─────────────────────────────────────────

def render_spatial_deck(
    history: list[dict[str, Any]],
    zone_coords: dict[str, dict[str, float]],
    adjacency: list[dict[str, str]],
) -> None:
    """Spatial deck map with toggleable colour mode and epoch slider."""

    if not history:
        st.warning("No simulation data.")
        return

    num_epochs = len(history)

    col_ctrl1, col_ctrl2 = st.columns([2, 3])
    with col_ctrl1:
        selected_epoch = st.slider(
            "Epoch (Hour)", min_value=0, max_value=num_epochs - 1,
            value=0, key="deck_epoch",
        )
    with col_ctrl2:
        color_mode = st.radio(
            "Node Colour",
            ["Airborne Aerosol Mass", "Surface Fomite Contamination", "Symptomatic Agent Count"],
            horizontal=True,
            key="deck_color",
        )

    record = history[selected_epoch]
    status = record["trigger_status"]

    # Status banner
    st.markdown(
        f"<div style='background-color:{STATUS_COLORS.get(status, 'gray')}; "
        f"padding:6px; border-radius:4px; text-align:center; "
        f"font-size:14px; font-weight:bold; color:white;'>"
        f"{STATUS_ICONS.get(status, '?')} Epoch {selected_epoch} — {status}</div>",
        unsafe_allow_html=True,
    )

    # Build the map
    fig = _build_deck_map(record, zone_coords, adjacency, color_mode)
    st.plotly_chart(fig, use_container_width=True)

    # Stoplights row
    stoplights = record.get("reactive_protocols", {}).get("stoplights", {})
    if stoplights:
        st.markdown("**Instrument Stoplights**")
        cols = st.columns(len(stoplights))
        for i, (inst, level) in enumerate(stoplights.items()):
            resolved = _worst_stoplight(level)
            color = STOPLIGHT_COLORS.get(resolved, "gray")
            short = inst.replace("_", " ").title()[:20]
            with cols[i]:
                st.markdown(
                    f"<div style='background:{color}; padding:4px; "
                    f"border-radius:4px; text-align:center; color:white; "
                    f"font-size:11px; font-weight:bold;'>"
                    f"{short}<br>{resolved}</div>",
                    unsafe_allow_html=True,
                )

    # Active protocols for this epoch
    active = record.get("reactive_protocols", {}).get("active_protocols", [])
    if active:
        names = [p.get("name", p.get("protocol_id", "?")) for p in active]
        st.info(f"Active SOPs: **{', '.join(names)}**")

    # Agent location table
    with st.expander(f"Agent Details — Epoch {selected_epoch}", expanded=False):
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
                line={"color": "rgba(150,150,150,0.4)", "width": 1.5},
                hoverinfo="skip", showlegend=False,
            ))

    # Agent locations
    agent_locations: dict[str, int] = {}
    symptomatic_per_zone: dict[str, int] = {}
    for agent in record.get("agents", []):
        loc = agent.get("location", "unknown")
        agent_locations[loc] = agent_locations.get(loc, 0) + 1
        if agent.get("status") in ("symptomatic", "infected"):
            symptomatic_per_zone[loc] = symptomatic_per_zone.get(loc, 0) + 1

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
            f"Symptomatic: {symp_count}"
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
        textfont={"size": 11, "color": "white"},
        marker={
            "size": sizes,
            "color": colors,
            "colorscale": [
                [0.0, "#2ecc71"], [0.3, "#f1c40f"],
                [0.6, "#e67e22"], [1.0, "#e74c3c"],
            ],
            "cmin": 0,
            "cmax": max(max_val, 0.01),
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.6},
            "line": {"width": 2, "color": "white"},
        },
        hovertext=hover_texts, hoverinfo="text", showlegend=False,
    ))

    fig.update_layout(
        title=f"Spatial Deck Map — Epoch {record['epoch']} ({color_mode})",
        template="plotly_dark", height=420,
        xaxis={"title": "Ship Length (m)", "range": [0, 120], "showgrid": False},
        yaxis={
            "title": "Beam (m)", "range": [0, 15], "showgrid": False,
            "scaleanchor": "x", "scaleratio": 1,
        },
        margin={"t": 60, "b": 40, "l": 50, "r": 80},
    )
    return fig


# ── Tab 3: Crusher Labs Portal ──────────────────────────────────────────

def render_crusher_portal(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
) -> None:
    """Lab notebook explorer with fidelity toggle and interactive charts."""

    if not notebook:
        st.warning("No lab notebook data found.")
        return

    records = notebook.get("records", [])
    fidelity_defs = notebook.get("fidelity_tier_definitions", {})
    run_meta = notebook.get("run_metadata", {})

    st.markdown(
        f"**Notebook v{notebook.get('version', '?')}** — "
        f"{notebook.get('total_records', 0)} records — "
        f"Fidelity: {records[0].get('fidelity_tier', '?') if records else '?'}"
    )

    # Fidelity selector
    fidelity = st.radio(
        "Display Fidelity",
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
        st.info("No records match the current filters.")
        return

    # ── Render based on fidelity ──────────────────────────────────
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

    st.subheader("Strategic Stoplight View")

    # Build stoplight grid from simulation history
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
                    raw = sl.get(inst, "—")
                    row[inst.replace("_", " ").title()[:22]] = _worst_stoplight(raw) if isinstance(raw, dict) else raw
                rows.append(row)

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Summary counts
    detected = sum(1 for r in records if r.get("binary_result") == "DETECTED")
    not_det = sum(1 for r in records if r.get("binary_result") == "NOT DETECTED")
    st.markdown(f"**Total:** {len(records)} records — {detected} DETECTED, {not_det} NOT DETECTED")


def _render_mid_fidelity(records: list[dict[str, Any]]) -> None:
    """CAP-certified clinical reports table."""

    st.subheader("Certified Clinical Reports")

    rows = []
    for r in records:
        row = {
            "Epoch": r.get("timestamp_epoch", ""),
            "Zone": r.get("collection_zone", ""),
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

    st.subheader("Raw Instrument Telemetry")

    tab_amp, tab_kingdom, tab_raw = st.tabs([
        "qPCR Amplification Curves",
        "GRUMB Kingdom Reads",
        "Raw Records Table",
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

    # Group by assay type
    by_assay: dict[str, list[dict[str, Any]]] = {}
    for r in curve_records:
        at = r.get("assay_type", "unknown")
        by_assay.setdefault(at, []).append(r)

    for assay_type, recs in by_assay.items():
        st.markdown(f"**{assay_type.replace('_', ' ').title()}** — {len(recs)} curves")

        fig = go.Figure()
        for r in recs[:12]:  # limit to prevent overload
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
            template="plotly_dark", height=350,
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
        st.info("No wastewater kingdom read data in current selection.")
        return

    kingdoms = ["Bacteria", "Archaea", "Fungi", "Virus"]
    kingdom_colors = {
        "Bacteria": "#3498db",
        "Archaea": "#9b59b6",
        "Fungi": "#2ecc71",
        "Virus": "#e74c3c",
    }

    # Stacked bar chart over epochs
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
        template="plotly_dark", height=380,
        xaxis_title="Sample", yaxis_title="Read Counts",
        title="Multi-Kingdom Relative Abundance (Wastewater Sequencing)",
        margin={"t": 50, "b": 60, "l": 50, "r": 20},
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)

    # CLR delta table
    clr_records = [r for r in ww_records if r.get("kingdom_clr_deltas")]
    if clr_records:
        st.markdown("**CLR-Space Anomaly Deltas**")
        clr_rows = []
        for r in clr_records:
            deltas = r["kingdom_clr_deltas"]
            clr_rows.append({
                "Epoch": r.get("timestamp_epoch", ""),
                "Zone": r.get("collection_zone", ""),
                "Bacteria": f"{deltas.get('Bacteria', 0):+.3f}",
                "Archaea": f"{deltas.get('Archaea', 0):+.3f}",
                "Fungi": f"{deltas.get('Fungi', 0):+.3f}",
                "Virus": f"{deltas.get('Virus', 0):+.3f}",
                "Anomaly": f"{r.get('inferred_anomaly_score', 0):.3f}",
            })
        st.dataframe(pd.DataFrame(clr_rows), use_container_width=True, hide_index=True)


# ── Tab 4: Protocol & Configuration Profile ─────────────────────────────

def render_protocol_config(
    pathogen_data: dict[str, Any],
    protocol_data: dict[str, Any],
) -> None:
    """Display pathogen profiles and standing protocol configurations."""

    # ── Pathogen Profiles ─────────────────────────────────────────
    st.subheader("Active Pathogen Profiles")

    pathogens = pathogen_data.get("pathogens", [])
    if isinstance(pathogens, list):
        for p in pathogens:
            with st.expander(f"{p.get('pathogen_id', '?')} — {p.get('name', '?')}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Category:** {p.get('category', '?')}")
                    st.markdown(f"**Introduction Epoch:** {p.get('introduction_epoch', 0)}")
                    routes = p.get("transmission_routes", [])
                    st.markdown(f"**Transmission Routes:** {', '.join(routes)}")
                with c2:
                    shed = p.get("shedding_profile", {})
                    if shed:
                        st.markdown(f"**Peak Shedding:** {shed.get('peak_log10', '?')} log10")
                        st.markdown(f"**Duration:** {shed.get('duration_days', '?')} days")
                    fc = p.get("food_contamination", {})
                    if fc.get("enabled"):
                        st.markdown(f"**Food Contamination:** growth={fc.get('growth_rate_per_epoch', 0)}/epoch, "
                                    f"decay={fc.get('decay_rate_per_epoch', 0)}/epoch")
                    ecc = p.get("environmental_contamination", {})
                    if ecc.get("enabled"):
                        st.markdown(f"**Env Contamination:** {ecc.get('source_type', '?')} "
                                    f"(load={ecc.get('baseline_environmental_load', 0)}, "
                                    f"p2p={'yes' if ecc.get('person_to_person', True) else 'no'})")
                    disrupt = p.get("microflora_disruption", {})
                    if disrupt:
                        st.markdown(f"**Microflora Target:** {disrupt.get('target_system', '?')}")
                        st.markdown(f"**Disruption Magnitude:** {disrupt.get('magnitude', '?')}")
    elif isinstance(pathogens, dict):
        for pid, p in pathogens.items():
            with st.expander(f"{pid} — {p.get('name', '?')}", expanded=True):
                st.json(p)
    else:
        st.info("No pathogen profiles loaded.")

    st.divider()

    # ── Standing Protocols ────────────────────────────────────────
    st.subheader("Standing Operating Protocols")

    protocols = protocol_data.get("protocols", [])
    if protocols:
        for p in protocols:
            trigger = p.get("trigger", {})
            inst = trigger.get("instrument_class", "?")
            level = trigger.get("stoplight_level", "?")
            color = STOPLIGHT_COLORS.get(level, "gray")

            st.markdown(
                f"<div style='border-left:4px solid {color}; padding:8px 12px; "
                f"margin:4px 0; background:rgba(255,255,255,0.03); "
                f"border-radius:0 4px 4px 0;'>"
                f"<b>{p.get('protocol_id', '?')}</b> — {p.get('name', '?')}<br>"
                f"<span style='color:{color};'>Trigger: {inst} >= {level}</span><br>"
                f"Modifiers: {', '.join(p.get('modifiers', {}).keys())}"
                f"</div>",
                unsafe_allow_html=True,
            )

            costs = p.get("cost_footprint", {})
            act_cost = costs.get("activation_costs", {}).get("financial_usd", 0)
            epoch_cost = costs.get("costs_per_epoch", {}).get("financial_usd", 0)
            if act_cost or epoch_cost:
                st.caption(f"  Activation: ${act_cost:,.0f} | Per-epoch: ${epoch_cost:,.0f}")
    else:
        st.info("No standing protocols configured.")


# ── Main App ─────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Crusher to the Bridge — Tactical Command Deck",
        page_icon="🔬",
        layout="wide",
    )

    st.title("Crusher to the Bridge")
    st.caption("Biodefense Digital Twin — Tactical Command Deck")

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
            "No simulation history found. "
            "Run `python orchestrator.py` first to generate "
            "`telemetry_buffer/simulation_history.json`."
        )
        return

    # ── Sidebar: Quick Status ─────────────────────────────────────
    with st.sidebar:
        st.header("Quick Status")
        last = history[-1]
        status = last["trigger_status"]
        st.markdown(
            f"<div style='background-color:{STATUS_COLORS.get(status, 'gray')}; "
            f"padding:10px; border-radius:6px; text-align:center; "
            f"font-size:18px; font-weight:bold; color:white;'>"
            f"{STATUS_ICONS.get(status, '?')} {status}</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        summary = last["summary"]
        st.metric("Epochs Run", len(history))
        st.metric("Total Crew", summary.get("susceptible", 0) + summary.get("infected", 0) + summary.get("recovered", 0) + summary.get("immune", 0) + summary.get("isolated", 0))
        st.metric("Currently Isolated", summary.get("isolated", 0))

        ca = last.get("cost_accounting", {})
        st.metric("Budget Remaining", f"${ca.get('financial_balance_remaining', 0):,.0f}")
        st.metric("Labor Remaining", f"{ca.get('labor_hours_remaining', 0):.1f} hrs")

        active_sops = last.get("reactive_protocols", {}).get("active_protocols", [])
        if active_sops:
            st.divider()
            st.markdown("**Active SOPs**")
            for sop in active_sops:
                st.markdown(f"- {sop.get('name', sop.get('protocol_id', '?'))}")

        st.divider()
        hvac = last.get("hvac", {})
        if hvac.get("transport_active"):
            st.markdown(
                f"**HVAC:** {hvac.get('filter_type', '?')} "
                f"({hvac.get('filter_efficiency', 0):.0%})"
            )

    # ── Tabs ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Mission Summary & Ledger",
        "Spatial Outbreak Deck",
        "Crusher Labs Portal",
        "Protocol & Configuration",
    ])

    with tab1:
        render_mission_summary(history, notebook)

    with tab2:
        render_spatial_deck(history, zone_coords, adjacency)

    with tab3:
        render_crusher_portal(history, notebook)

    with tab4:
        render_protocol_config(pathogen_data, protocol_data)


if __name__ == "__main__":
    main()
