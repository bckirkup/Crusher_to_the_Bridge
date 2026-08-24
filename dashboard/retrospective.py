"""Voyage retrospective summary — run header, epidemic arc, port timeline."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.loaders import extract_run_metadata, load_voyage_config
from dashboard.session_state import set_selected_agent, set_selected_epoch
from dashboard.theme import LCARS_BLUE, LCARS_GOLD, _lcars_banner, apply_lcars_layout
from dashboard.units import axis, time_x_values


def _peak_attack_rate(history: list[dict[str, Any]]) -> tuple[float, int]:
    best_val = -1.0
    best_epoch = 0
    for rec in history:
        for cdata in rec.get("infection_counters", {}).values():
            if cdata.get("metric_type") == "rate":
                val = float(cdata.get("value", 0))
                if val > best_val:
                    best_val = val
                    best_epoch = rec["epoch"]
    return best_val, best_epoch


def _cumulative_infected(history: list[dict[str, Any]]) -> int:
    total = 0
    for rec in history:
        ct = rec.get("contact_tracing", {})
        total += len(ct.get("transmission_events", []))
    if total:
        return total
    return max((r.get("summary", {}).get("infected", 0) for r in history), default=0)


def _find_epoch_by_status(history: list[dict[str, Any]], status: str) -> int | None:
    for rec in history:
        if rec.get("trigger_status") == status:
            return rec["epoch"]
    return None


def _first_infection_epoch(history: list[dict[str, Any]]) -> int | None:
    for rec in history:
        ct = rec.get("contact_tracing", {})
        if ct.get("transmission_events"):
            return rec["epoch"]
        if rec.get("summary", {}).get("infected", 0) > 0:
            return rec["epoch"]
    return None


def _top_transmission_agent(history: list[dict[str, Any]]) -> int | None:
    counts: dict[int, int] = {}
    for rec in history:
        for ev in rec.get("contact_tracing", {}).get("transmission_events", []):
            for sid in ev.get("source_ids", []):
                counts[int(sid)] = counts.get(int(sid), 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _build_voyage_strip(history: list[dict[str, Any]], itinerary: list[dict[str, Any]]) -> go.Figure:
    epochs = time_x_values(history)
    ports: list[str] = []
    onboard: list[float] = []
    day_types: list[str] = []
    for rec in history:
        ve = rec.get("voyage_epoch", {})
        ports.append(str(ve.get("port") or ""))
        onboard.append(float(ve.get("onboard_fraction", 1.0)))
        day_types.append(str(ve.get("day_type") or "sea_day"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs,
        y=onboard,
        mode="lines+markers",
        name="Onboard fraction",
        line={"color": LCARS_BLUE, "width": 2},
        text=ports,
        hovertemplate="Epoch %{x}<br>Port: %{text}<br>Onboard: %{y:.0%}<extra></extra>",
    ))
    for item in itinerary:
        day = item.get("voyage_day")
        if day is None:
            continue
        fig.add_vline(
            x=day,
            line_dash="dot",
            line_color=LCARS_GOLD,
            annotation_text=str(item.get("port", ""))[:18],
            annotation_position="top",
        )
    apply_lcars_layout(
        fig,
        height=220,
        title="Voyage timeline — port calls and onboard fraction",
        xaxis_title=axis("time_voyage_day").title if any(ports) else axis("time_epoch").title,
        yaxis_title="Onboard fraction",
        yaxis_tickformat=".0%",
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
    )
    return fig


def render_voyage_retrospective(
    history: list[dict[str, Any]],
    notebook: dict[str, Any],
    *,
    platform_id: str,
    ship_label: str,
    run_metadata: dict[str, Any] | None = None,
) -> None:
    """Opening retrospective: what happened on this voyage."""
    if not history:
        st.warning("No telemetry for retrospective.")
        return

    meta = run_metadata or extract_run_metadata(notebook)
    last = history[-1]
    summary = last.get("summary", {})

    st.subheader("Voyage Retrospective")
    st.markdown(
        _lcars_banner(
            f"{ship_label} · {len(history)} epochs · "
            f"Status: {last.get('trigger_status', 'BASELINE')}",
            LCARS_GOLD,
        ),
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    pop = (
        summary.get("susceptible", 0)
        + summary.get("infected", 0)
        + summary.get("recovered", 0)
        + summary.get("immune", 0)
        + summary.get("isolated", 0)
    )
    m1.metric("Population", pop)
    m2.metric("Final infected", summary.get("infected", 0))
    m3.metric("Final symptomatic", summary.get("symptomatic", 0))
    seed = meta.get("seed", meta.get("random_seed", "—"))
    m4.metric("Seed", seed)
    m5.metric("Platform", platform_id)

    peak_rate, peak_epoch = _peak_attack_rate(history)
    cum_inf = _cumulative_infected(history)
    ca = last.get("cost_accounting", {})
    dc = last.get("diagnostic_cascade", {})

    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Peak attack rate", f"{peak_rate:.1%}" if peak_rate >= 0 else "—")
    o2.metric("Peak epoch", peak_epoch if peak_rate >= 0 else "—")
    o3.metric("Transmission events", cum_inf)
    o4.metric("OIS cumulative", f"{ca.get('operational_impact_cumulative', 0):,.1f}")

    q_peak = max((r.get("summary", {}).get("quarantined", 0) for r in history), default=0)
    iso_peak = max((r.get("summary", {}).get("isolated", 0) for r in history), default=0)
    st.caption(
        f"Peak quarantined: {q_peak} · Peak isolated: {iso_peak} · "
        f"Credits spent: ${ca.get('total_financial_usd', 0):,.0f} · "
        f"Cascade tier-0 entries: {dc.get('tier0_entries_total', dc.get('new_tier0_agents', 0))}"
    )

    voyage_cfg = load_voyage_config(platform_id)
    itinerary = (voyage_cfg.get("voyage") or {}).get("itinerary") or []
    if history[0].get("voyage_epoch") or itinerary:
        st.plotly_chart(_build_voyage_strip(history, itinerary), use_container_width=True)

    st.markdown("**Quick navigation**")
    c1, c2, c3 = st.columns(3)
    first_inf = _first_infection_epoch(history)
    confirmed = _find_epoch_by_status(history, "CONFIRMED")
    top_agent = _top_transmission_agent(history)

    with c1:
        if first_inf is not None and st.button("Jump to first infection", key="retro_first_inf"):
            set_selected_epoch(first_inf, len(history))
            st.rerun()
    with c2:
        if confirmed is not None and st.button("Jump to CONFIRMED", key="retro_confirmed"):
            set_selected_epoch(confirmed, len(history))
            st.rerun()
    with c3:
        if top_agent is not None and st.button(
            f"Open top transmitter (agent {top_agent})",
            key="retro_top_agent",
        ):
            set_selected_agent(top_agent)
            st.rerun()

    with st.expander("Run metadata", expanded=False):
        if meta:
            st.dataframe(pd.DataFrame([meta]), use_container_width=True, hide_index=True)
        else:
            st.caption("No run metadata in lab notebook.")
