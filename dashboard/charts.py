"""Bridge, sickbay, and standing orders chart stations."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import (
    ALERT_COLORS,
    ALERT_LABELS,
    LCARS_AMBER,
    LCARS_BLUE,
    LCARS_GOLD,
    LCARS_GREEN,
    LCARS_PANEL,
    LCARS_PEACH,
    LCARS_PURPLE,
    LCARS_RED,
    LCARS_TAN,
    STOPLIGHT_COLORS,
    _lcars_alert_banner,
    _lcars_banner,
    _worst_stoplight,
    apply_lcars_layout,
)
from dashboard.units import axis, time_x_values, time_xaxis_title
from telemetry_buffer.agent_axes import (
    COMPLIANCE_QUARANTINED,
    INFECTION_RECOVERED,
    agent_has_symptomatic_presentation,
    agent_is_infected,
    resolve_agent_axes,
)

PLOT_MODE_LINES_MARKERS = "lines+markers"

# ══════════════════════════════════════════════════════════════════════════
# Station 1: Bridge Status Display
# ══════════════════════════════════════════════════════════════════════════

def _render_bridge_ship_status(summary: dict[str, Any], trigger_status: str) -> None:
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

    sick_call = summary.get("sick_call_count")
    microflora = summary.get("disrupted_microflora_count")
    if sick_call is not None or microflora is not None:
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("Sick Call", sick_call if sick_call is not None else 0)
        with sc2:
            st.metric("Microflora Disrupted", microflora if microflora is not None else 0)
        with sc3:
            st.metric("Recovered", summary.get("recovered", 0))
        with sc4:
            st.metric("Immune", summary.get("immune", 0))

    st.markdown(_lcars_alert_banner(trigger_status), unsafe_allow_html=True)


def _render_bridge_biosensor_telemetry(
    history: list[dict[str, Any]],
    counters: dict[str, Any],
) -> None:
    if not counters:
        return
    st.subheader("Biosensor Telemetry")
    counter_cols = st.columns(min(len(counters), 5))
    for idx, (cid, cdata) in enumerate(counters.items()):
        col = counter_cols[idx % len(counter_cols)]
        label = cdata.get("label", cid)
        value = cdata.get("value", 0)
        threshold = cdata.get("threshold")
        exceeded = cdata.get("exceeded", False)
        display_val = f"{value:.1%}" if "rate" in cid else f"{value:.0f}"
        suffix = ""
        if threshold is not None:
            suffix = (
                f" (thr: {threshold:.1%})" if "rate" in cid else f" (thr: {threshold})"
            )
        with col:
            if exceeded:
                st.metric(f"ALERT: {label}", display_val + suffix)
            else:
                st.metric(label, display_val + suffix)
    _render_counter_time_series(history)


def _render_bridge_resource_allocation(notebook: dict[str, Any]) -> None:
    st.subheader("Resource Allocation")
    audit = notebook.get("FINANCIAL_AUDIT", {})
    fin_summary = audit.get("summary", {})
    if not fin_summary:
        st.info("Awaiting financial audit data from the quartermaster.")
        return

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
            x=epochs_x, y=surv_cum, mode=PLOT_MODE_LINES_MARKERS,
            name="Surveillance", fill="tozeroy",
            line={"color": LCARS_BLUE},
        ))
        cost_fig.add_trace(go.Scatter(
            x=epochs_x, y=intv_cum, mode=PLOT_MODE_LINES_MARKERS,
            name="Intervention", fill="tozeroy",
            line={"color": LCARS_RED},
        ))
        apply_lcars_layout(
            cost_fig,
            height=280,
            xaxis_title=axis("time_epoch").title, yaxis_title=axis("usd").title,
            margin={"t": 30, "b": 40, "l": 50, "r": 20},
            legend={"orientation": "h", "y": 1.1, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(cost_fig, use_container_width=True)

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


def _render_bridge_sop_log(notebook: dict[str, Any]) -> None:
    st.subheader("Standing Orders Log")
    proto_summary = notebook.get("PROTOCOL_SUMMARY", {})
    event_log = proto_summary.get("event_log", [])
    if not event_log:
        st.info("No protocol activation events recorded.")
        return

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

    _render_bridge_ship_status(summary, last["trigger_status"])
    _render_bridge_biosensor_telemetry(history, last.get("infection_counters", {}))
    _render_class_breakdown(last)

    # ── Contagion Progression ─────────────────────────────────────
    st.subheader("Contagion Progression")
    fig = _build_epidemic_curve(history)
    st.plotly_chart(fig, use_container_width=True)

    # ── Multi-Pathogen Breakdown ──────────────────────────────────
    multi_path = last.get("multi_pathogen", {})
    if multi_path:
        _render_pathogen_curves(history)

    # ── Wearable Physiological Monitoring ─────────────────────────
    _render_wearable_monitoring(history)

    # ── Diagnostic Cascade ────────────────────────────────────────
    _render_diagnostic_cascade(history)

    # ── Transmission Pathway Analysis ─────────────────────────────
    _render_transmission_pathways(history)

    # ── Operational Impact Score ──────────────────────────────────
    _render_operational_impact(history)

    # ── Crusher Lab Operations ────────────────────────────────────
    _render_crusher_ops(last)

    _render_bridge_resource_allocation(notebook)
    _render_bridge_sop_log(notebook)


def _collect_counter_ids(history: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    all_cids: list[str] = []
    cid_labels: dict[str, str] = {}
    for rec in history:
        for cid, cdata in rec.get("infection_counters", {}).items():
            if cid not in cid_labels:
                all_cids.append(cid)
                cid_labels[cid] = cdata.get("label", cid)
    return all_cids, cid_labels


def _render_rate_counter_chart(
    history: list[dict[str, Any]],
    rate_cids: list[str],
    cid_labels: dict[str, str],
) -> None:
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
            x=epochs, y=values, mode=PLOT_MODE_LINES_MARKERS,
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

    apply_lcars_layout(
        fig,
        height=300,
        title="Attack Rate Tracking",
        xaxis_title=time_xaxis_title(history), yaxis_title=axis("attack_rate").title,
        yaxis_tickformat=axis("attack_rate").tickformat,
        margin={"t": 50, "b": 40, "l": 60, "r": 20},
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_count_counter_chart(
    history: list[dict[str, Any]],
    count_cids: list[str],
    cid_labels: dict[str, str],
) -> None:
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
    apply_lcars_layout(
        fig,
        height=280,
        title="Infection Count Tracking",
        xaxis_title=time_xaxis_title(history), yaxis_title=axis("persons").title,
        barmode="group",
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_counter_time_series(history: list[dict[str, Any]]) -> None:
    """Line chart of infection counter values across all epochs."""
    all_cids, cid_labels = _collect_counter_ids(history)
    if not all_cids:
        return

    rate_cids = [c for c in all_cids if "rate" in c]
    count_cids = [c for c in all_cids if "rate" not in c]

    if rate_cids:
        _render_rate_counter_chart(history, rate_cids, cid_labels)
    if count_cids:
        _render_count_counter_chart(history, count_cids, cid_labels)


def aggregate_class_stats(agents: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Infection distribution by agent class using orthogonal telemetry axes."""
    class_stats: dict[str, dict[str, int]] = {}
    for agent in agents:
        cls = agent.get("agent_class", "unknown")
        if cls not in class_stats:
            class_stats[cls] = {
                "total": 0, "infected": 0, "symptomatic": 0,
                "recovered": 0, "quarantined": 0,
            }
        class_stats[cls]["total"] += 1
        infection_state, _, compliance_status = resolve_agent_axes(agent)
        if agent_is_infected(agent):
            class_stats[cls]["infected"] += 1
        if agent_has_symptomatic_presentation(agent):
            class_stats[cls]["symptomatic"] += 1
        if infection_state == INFECTION_RECOVERED:
            class_stats[cls]["recovered"] += 1
        if compliance_status == COMPLIANCE_QUARANTINED:
            class_stats[cls]["quarantined"] += 1
    return class_stats


def _render_class_breakdown(last: dict[str, Any]) -> None:
    """Agent class breakdown showing infection distribution across classes."""
    agents = last.get("agents", [])
    if not agents:
        return

    class_stats = aggregate_class_stats(agents)

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

    if len(all_pids) < 1:
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
            x=epochs, y=infected, mode=PLOT_MODE_LINES_MARKERS,
            name=pid.replace("_", " ").title(),
            line={"color": colors[i % len(colors)], "width": 2},
        ))

    apply_lcars_layout(
        fig,
        height=300,
        title="Per-Pathogen Active Infections",
        xaxis_title=time_xaxis_title(history), yaxis_title=axis("active_infections").title,
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_wearable_summary_metrics(wm: dict[str, Any]) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Monitored Crew", wm.get("total_monitored", 0))
    with c2:
        staff_vis = wm.get("total_staff_visible")
        if staff_vis is not None:
            st.metric("Staff-Visible", staff_vis)
        else:
            st.metric("Fever Detected", wm.get("fever_count", 0))
    with c3:
        st.metric("Fever Rate", f"{wm.get('fever_rate', 0):.1%}")
    with c4:
        st.metric("Anomaly Rate", f"{wm.get('anomaly_rate', 0):.1%}")
    with c5:
        st.metric("Anomalies", wm.get("anomaly_count", 0))


def _render_wearable_breakdown_metrics(wm: dict[str, Any]) -> None:
    visibility = wm.get("visibility_breakdown", {})
    if visibility:
        vis_cols = st.columns(len(visibility))
        for i, (tier, cnt) in enumerate(sorted(visibility.items())):
            with vis_cols[i]:
                st.metric(tier.replace("_", " ").title(), cnt)

    wearer_only = wm.get("wearer_only_agents", [])
    if wearer_only:
        st.caption(
            f"{len(wearer_only)} agent(s) with wearer-only device visibility "
            "(alerts may not reach medical staff)."
        )

    device_counts = wm.get("device_deployment_counts", {})
    if device_counts:
        dev_cols = st.columns(min(len(device_counts), 4))
        for i, (dev_id, cnt) in enumerate(sorted(device_counts.items())):
            with dev_cols[i % len(dev_cols)]:
                st.metric(dev_id.replace("_", " ").title(), cnt)

    channel_counts = wm.get("channel_anomaly_counts", {})
    if channel_counts:
        cols = st.columns(len(channel_counts))
        for i, (ch, cnt) in enumerate(channel_counts.items()):
            with cols[i]:
                st.metric(ch.replace("_", " ").title(), cnt)


def _render_wearable_trends(history: list[dict[str, Any]]) -> None:
    epochs = []
    fever_rates = []
    anomaly_rates = []
    for rec in history:
        wm_rec = rec.get("wearable_monitoring", {})
        if wm_rec:
            epochs.append(rec["epoch"])
            fever_rates.append(wm_rec.get("fever_rate", 0))
            anomaly_rates.append(wm_rec.get("anomaly_rate", 0))

    if not epochs:
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs, y=fever_rates, mode=PLOT_MODE_LINES_MARKERS,
        name="Fever Rate", line={"color": LCARS_RED, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=anomaly_rates, mode=PLOT_MODE_LINES_MARKERS,
        name="Anomaly Rate", line={"color": LCARS_GOLD, "width": 2},
    ))
    apply_lcars_layout(
        fig,
        height=260,
        title="Wearable Monitoring Trends",
        xaxis_title=time_xaxis_title(history), yaxis_title=axis("attack_rate").title,
        yaxis_tickformat=axis("attack_rate").tickformat,
        margin={"t": 50, "b": 40, "l": 60, "r": 20},
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
    _render_wearable_summary_metrics(wm)
    _render_wearable_breakdown_metrics(wm)
    _render_wearable_trends(history)


def _render_diagnostic_cascade(history: list[dict[str, Any]]) -> None:
    """Tier-0/1 cascade entries and advancement log."""
    if not any(rec.get("diagnostic_cascade") for rec in history):
        return

    st.subheader("Diagnostic Cascade")

    last_dc = history[-1].get("diagnostic_cascade", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Tier-0 Entries (epoch)", len(last_dc.get("new_tier0_agents", [])))
    with c2:
        st.metric("Tier-1 Entries (epoch)", len(last_dc.get("new_tier1_agents", [])))
    with c3:
        st.metric("Confinements Ordered", len(last_dc.get("confinements_ordered", [])))
    with c4:
        st.metric("Wearable Offers", len(last_dc.get("wearable_offers", [])))

    unlocked = last_dc.get("fleet_sops_unlocked", [])
    if unlocked:
        st.caption(f"Fleet SOPs unlocked this epoch: {', '.join(unlocked)}")

    epochs: list[int] = []
    tier0_counts: list[int] = []
    tier1_counts: list[int] = []
    for rec in history:
        dc = rec.get("diagnostic_cascade", {})
        if not dc:
            continue
        epochs.append(rec["epoch"])
        tier0_counts.append(len(dc.get("new_tier0_agents", [])))
        tier1_counts.append(len(dc.get("new_tier1_agents", [])))

    if epochs:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=epochs, y=tier0_counts, name="Tier-0",
            marker_color=LCARS_GOLD,
        ))
        fig.add_trace(go.Bar(
            x=epochs, y=tier1_counts, name="Tier-1",
            marker_color=LCARS_BLUE,
        ))
        apply_lcars_layout(
            fig,
            height=260,
            barmode="group",
            title="Cascade Entries by Epoch",
            xaxis_title=time_xaxis_title(history), yaxis_title=axis("new_agents").title,
            margin={"t": 50, "b": 40, "l": 50, "r": 20},
            legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(fig, use_container_width=True)

    advancements: list[dict[str, Any]] = []
    for rec in history:
        dc = rec.get("diagnostic_cascade", {})
        for adv in dc.get("tier_advancements", []):
            row = dict(adv)
            row["epoch"] = rec["epoch"]
            advancements.append(row)
    if advancements:
        st.dataframe(
            pd.DataFrame(advancements),
            use_container_width=True,
            hide_index=True,
        )


def _render_operational_impact(history: list[dict[str, Any]]) -> None:
    """Operational Impact Score (fourth ledger dimension)."""
    if not any(
        rec.get("cost_accounting", {}).get("operational_impact_cumulative") is not None
        for rec in history
    ):
        return

    st.subheader("Operational Impact Score")

    last_ca = history[-1].get("cost_accounting", {})
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("OIS (epoch)", f"{last_ca.get('operational_impact_epoch', 0):,.1f}")
    with c2:
        st.metric("OIS (cumulative)", f"{last_ca.get('operational_impact_cumulative', 0):,.1f}")
    with c3:
        st.metric("Credits Remaining", f"${last_ca.get('financial_balance_remaining', 0):,.0f}")

    breakdown = last_ca.get("operational_impact_breakdown", {})
    if breakdown:
        bd_rows = [
            {"Driver": key.replace("_", " ").title(), "Contribution": f"{val:,.2f}"}
            for key, val in sorted(breakdown.items(), key=lambda item: -abs(item[1]))
        ]
        st.dataframe(pd.DataFrame(bd_rows), use_container_width=True, hide_index=True)

    epochs: list[int] = []
    epoch_ois: list[float] = []
    cum_ois: list[float] = []
    for rec in history:
        ca = rec.get("cost_accounting", {})
        if ca.get("operational_impact_cumulative") is None:
            continue
        epochs.append(rec["epoch"])
        epoch_ois.append(float(ca.get("operational_impact_epoch", 0)))
        cum_ois.append(float(ca.get("operational_impact_cumulative", 0)))

    if epochs:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=epochs, y=cum_ois, mode=PLOT_MODE_LINES_MARKERS,
            name="Cumulative OIS", line={"color": LCARS_PURPLE, "width": 2},
        ))
        fig.add_trace(go.Bar(
            x=epochs, y=epoch_ois, name="Epoch OIS",
            marker_color=LCARS_AMBER, opacity=0.65,
        ))
        apply_lcars_layout(
            fig,
            height=280,
            title="Operational Impact Over Time",
            xaxis_title=time_xaxis_title(history), yaxis_title=axis("ois").title,
            margin={"t": 50, "b": 40, "l": 50, "r": 20},
            legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_crusher_ops(record: dict[str, Any]) -> None:
    """Shipboard lab ops: RDT/PCR summary from epoch telemetry."""
    ops = record.get("crusher_ops", {})
    if not ops:
        return

    rdt_tested = ops.get("rdt_tested_count", 0)
    rdt_pos = ops.get("rdt_positive_count", 0)
    pcr_zones = ops.get("pcr_results", {})
    if rdt_tested == 0 and not pcr_zones:
        return

    st.subheader("Crusher Lab Operations")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("RDT Tests", rdt_tested)
    with c2:
        st.metric("RDT Positive", rdt_pos)
    with c3:
        st.metric("Surface PCR Zones", len(pcr_zones))

    if pcr_zones:
        pcr_rows = [
            {
                "Zone": zone,
                "Detected": data.get("detected", False),
                "Ct": data.get("ct_value"),
            }
            for zone, data in sorted(pcr_zones.items())
        ]
        st.dataframe(pd.DataFrame(pcr_rows), use_container_width=True, hide_index=True)


def _accumulate_event_pathways(
    ev: dict[str, Any],
    pathway_totals: dict[str, float],
) -> None:
    breakdown = ev.get("pathway_breakdown", {})
    if breakdown:
        for key, dose in breakdown.items():
            pw = key.split(":")[0] if ":" in key else key
            pathway_totals[pw] = pathway_totals.get(pw, 0) + dose
    else:
        pw = ev.get("dominant_pathway", ev.get("pathway", "unknown"))
        pathway_totals[pw] = pathway_totals.get(pw, 0) + ev.get("total_dose", 1)


def aggregate_transmission_pathway_totals(
    history: list[dict[str, Any]],
) -> dict[str, float]:
    """Sum transmission doses by pathway across epoch records.

    Uses ``pathway_breakdown`` keys (``pathway:pathogen_id``) when present;
    otherwise falls back to ``dominant_pathway`` / legacy ``pathway`` fields.
    """
    pathway_totals: dict[str, float] = {}
    for rec in history:
        ct = rec.get("contact_tracing", {})
        events = ct.get("transmission_events", [])
        for ev in events:
            _accumulate_event_pathways(ev, pathway_totals)
    pathway_totals.pop("none", None)
    return pathway_totals


def _render_transmission_pathways(history: list[dict[str, Any]]) -> None:
    """Transmission pathway breakdown from contact tracing data."""
    pathway_totals = aggregate_transmission_pathway_totals(history)
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
        marker={"colors": colors[:len(labels)]},
        textinfo="label+percent",
        textfont={"color": "white"},
        hole=0.4,
    )])
    apply_lcars_layout(
        fig,
        height=350,
        title="Transmission Pathway Distribution",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Pathway dose table
    pw_rows = [{"Pathway": l, "Total Dose": f"{v:,.1f}"} for l, v in zip(labels, values)]
    st.dataframe(pd.DataFrame(pw_rows), use_container_width=True, hide_index=True)


def _build_epidemic_curve(history: list[dict[str, Any]]) -> go.Figure:
    epochs = time_x_values(history)
    susceptible: list[int] = []
    infected: list[int] = []
    quarantined: list[int] = []
    isolated: list[int] = []
    recovered: list[int] = []
    for record in history:
        s = record["summary"]
        susceptible.append(s.get("susceptible", 0))
        infected.append(s.get("infected", 0) + s.get("symptomatic", 0))
        quarantined.append(s.get("quarantined", 0))
        isolated.append(s.get("isolated", 0))
        recovered.append(s.get("recovered", 0))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs, y=susceptible, mode=PLOT_MODE_LINES_MARKERS,
        name="Susceptible (S)", line={"color": LCARS_BLUE, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=infected, mode=PLOT_MODE_LINES_MARKERS,
        name="Infected (I)", line={"color": LCARS_RED, "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=quarantined, mode=PLOT_MODE_LINES_MARKERS,
        name="Confined to Quarters (Q)", line={"color": LCARS_GOLD, "width": 2, "dash": "dash"},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=isolated, mode=PLOT_MODE_LINES_MARKERS,
        name="Isolation Ward", line={"color": LCARS_PURPLE, "width": 2, "dash": "dashdot"},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=recovered, mode=PLOT_MODE_LINES_MARKERS,
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

    apply_lcars_layout(
        fig,
        height=350,
        xaxis_title=time_xaxis_title(history), yaxis_title=axis("persons").title,
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════
# Station 3: Sickbay Diagnostic Console
# ══════════════════════════════════════════════════════════════════════════

def _render_sickbay_fidelity_view(
    fidelity: str,
    filtered: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> None:
    if fidelity == "LOW_FIDELITY":
        _render_low_fidelity(filtered, history)
    elif fidelity == "MID_FIDELITY":
        _render_mid_fidelity(filtered)
    else:
        _render_high_fidelity(filtered)


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

    _render_sickbay_fidelity_view(fidelity, filtered, history)


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

        apply_lcars_layout(
            fig,
            height=350,
            xaxis_title=axis("cycle").title, yaxis_title=axis("fluorescence").title,
            margin={"t": 30, "b": 40, "l": 50, "r": 20},
            legend={"font": {"size": 9}},
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_kingdom_clr_deltas(ww_records: list[dict[str, Any]]) -> None:
    clr_records = [r for r in ww_records if r.get("kingdom_clr_deltas")]
    if not clr_records:
        return
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

    apply_lcars_layout(
        fig,
        barmode="stack",
        height=380,
        xaxis_title=axis("sample").title, yaxis_title=axis("read_counts").title,
        title="Multi-Kingdom Metagenomic Analysis",
        margin={"t": 50, "b": 60, "l": 50, "r": 20},
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
    )
    st.plotly_chart(fig, use_container_width=True)
    _render_kingdom_clr_deltas(ww_records)


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
            category = p.get("category", "intervention")
            cat_color = LCARS_BLUE if category == "surveillance" else LCARS_AMBER

            st.markdown(
                f"<div style='border-left:6px solid {color}; padding:10px 14px; "
                f"margin:6px 0; background:{LCARS_PANEL}; "
                f"border-radius:0 8px 8px 0;'>"
                f"<b style='color:{LCARS_GOLD};'>{p.get('protocol_id', '?')}</b> "
                f"<span style='color:{LCARS_PEACH};'>— {p.get('name', '?')}</span> "
                f"<span style='color:{cat_color};font-size:11px;'>[{category}]</span><br>"
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

