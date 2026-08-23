"""Agent illness, duration, and care timeline explorer."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.retention import render_retention_banner
from dashboard.session_state import get_selected_agent_id, set_selected_agent
from dashboard.theme import LCARS_GOLD, LCARS_PURPLE, LCARS_RED, apply_lcars_layout
from dashboard.units import axis, time_x_values


def _agent_ids(history: list[dict[str, Any]]) -> list[int]:
    ids: set[int] = set()
    for rec in history:
        for ag in rec.get("agents", []):
            ids.add(int(ag["agent_id"]))
    return sorted(ids)


def _agent_record_at(history: list[dict[str, Any]], agent_id: int, epoch: int) -> dict[str, Any] | None:
    rec = next((r for r in history if r["epoch"] == epoch), None)
    if not rec:
        return None
    for ag in rec.get("agents", []):
        if int(ag["agent_id"]) == agent_id:
            return ag
    return None


def _build_agent_timeline(history: list[dict[str, Any]], agent_id: int) -> go.Figure | None:
    epochs = time_x_values(history)
    infection_y: list[int] = []
    symptom_y: list[int] = []
    compliance_y: list[int] = []
    state_map = {"susceptible": 0, "infected": 1, "recovered": 2, "immune": 3}
    symptom_map = {"asymptomatic": 0, "mild": 1, "symptomatic": 2, "severe": 3}
    compliance_map = {"compliant": 0, "non_compliant": 1, "isolated": 2, "quarantined": 3}

    for rec in history:
        ag = next((a for a in rec.get("agents", []) if int(a["agent_id"]) == agent_id), None)
        if not ag:
            infection_y.append(0)
            symptom_y.append(0)
            compliance_y.append(0)
            continue
        infection_y.append(state_map.get(ag.get("infection_state", "susceptible"), 0))
        symptom_y.append(symptom_map.get(ag.get("symptom_presentation", "asymptomatic"), 0))
        compliance_y.append(compliance_map.get(ag.get("compliance_status", "compliant"), 0))

    if not any(infection_y):
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs, y=infection_y, mode="lines+markers", name="Infection state",
        line={"color": LCARS_RED, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=symptom_y, mode="lines+markers", name="Symptom level",
        line={"color": LCARS_GOLD, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=compliance_y, mode="lines+markers", name="Compliance / isolation",
        line={"color": LCARS_PURPLE, "width": 2},
    ))
    apply_lcars_layout(
        fig,
        height=320,
        title=f"Agent {agent_id} — illness and compliance tracks",
        xaxis_title=axis("time_epoch").title,
        yaxis_title="Ordinal track level",
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
    )
    return fig


def _location_track(history: list[dict[str, Any]], agent_id: int) -> pd.DataFrame:
    rows = []
    for rec in history:
        ag = next((a for a in rec.get("agents", []) if int(a["agent_id"]) == agent_id), None)
        if ag:
            rows.append({
                "epoch": rec["epoch"],
                "location": ag.get("location", ""),
                "voyage_day": rec.get("voyage_epoch", {}).get("voyage_day"),
                "port": rec.get("voyage_epoch", {}).get("port", ""),
            })
    return pd.DataFrame(rows)


def _care_events(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
    agent_id: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rec in history:
        epoch = rec["epoch"]
        cascade = rec.get("diagnostic_cascade", {})
        for test in cascade.get("tests_ordered", []):
            if test.get("agent_id") == agent_id:
                rows.append({
                    "epoch": epoch,
                    "kind": "cascade_test",
                    "detail": test.get("test_type", test.get("tier", "")),
                })
        obs = rec.get("observation_engine", {})
        for inst, data in obs.items():
            if not isinstance(data, dict):
                continue
            for _zone, entry in data.items():
                if isinstance(entry, dict) and entry.get("agent_id") == agent_id:
                    rows.append({
                        "epoch": epoch,
                        "kind": inst,
                        "detail": entry.get("status", "ordered"),
                        "available_epoch": entry.get("available_epoch"),
                    })
    for rec in notebook.get("records", []):
        pid = rec.get("patient_id")
        if pid is not None and int(pid) == agent_id:
            rows.append({
                "epoch": rec.get("timestamp_epoch"),
                "kind": "lab_notebook",
                "detail": rec.get("assay_type", ""),
                "result": rec.get("binary_result", ""),
            })
    return pd.DataFrame(rows)


def _transmission_role(history: list[dict[str, Any]], agent_id: int) -> pd.DataFrame:
    rows = []
    for rec in history:
        for ev in rec.get("contact_tracing", {}).get("transmission_events", []):
            if int(ev.get("target_id", -1)) == agent_id:
                rows.append({
                    "epoch": rec["epoch"],
                    "role": "target",
                    "zone": ev.get("zone"),
                    "pathway": ev.get("dominant_pathway"),
                    "dose": ev.get("total_dose"),
                })
            elif agent_id in [int(s) for s in ev.get("source_ids", [])]:
                rows.append({
                    "epoch": rec["epoch"],
                    "role": "source",
                    "zone": ev.get("zone"),
                    "pathway": ev.get("dominant_pathway"),
                    "dose": ev.get("total_dose"),
                })
    return pd.DataFrame(rows)


def render_agent_explorer(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
    *,
    retention_mode: str,
) -> None:
    st.subheader("Agent Illness & Care Explorer")
    if render_retention_banner(retention_mode, feature="Agent explorer"):
        return

    agent_ids = _agent_ids(history)
    if not agent_ids:
        st.info("No per-agent records in telemetry.")
        return

    preselect = get_selected_agent_id()
    default_idx = agent_ids.index(preselect) if preselect in agent_ids else 0
    agent_id = st.selectbox(
        "Select agent",
        agent_ids,
        index=default_idx,
        key="agent_explorer_pick",
    )
    set_selected_agent(int(agent_id))

    ag0 = _agent_record_at(history, int(agent_id), history[0]["epoch"])
    if ag0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Class", ag0.get("agent_class", "—"))
        c2.metric("Gender", ag0.get("gender", "—"))
        c3.metric("Cabin mates", ", ".join(map(str, ag0.get("cabin_mate_ids", []))) or "—")
        path_inf = ag0.get("pathogen_infections") or {}
        c4.metric("Pathogens tracked", len(path_inf) if path_inf else 0)

    fig = _build_agent_timeline(history, int(agent_id))
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Location track", expanded=False):
        loc_df = _location_track(history, int(agent_id))
        if not loc_df.empty:
            st.dataframe(loc_df, use_container_width=True, hide_index=True)

    with st.expander("Care & diagnostics", expanded=True):
        care_df = _care_events(history, notebook, int(agent_id))
        if not care_df.empty:
            st.dataframe(care_df.sort_values("epoch"), use_container_width=True, hide_index=True)
        else:
            st.caption("No care or diagnostic events linked to this agent.")

    with st.expander("Transmission role", expanded=False):
        tx_df = _transmission_role(history, int(agent_id))
        if not tx_df.empty:
            st.dataframe(tx_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No transmission events involving this agent.")
