"""Panels for recently-landed mechanisms that other tabs don't own.

Aggregators in this module are pure (no Streamlit) so tests can exercise
them against fixture records; the ``render_*`` functions are thin shells
over the aggregates.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import (
    LCARS_AMBER,
    LCARS_BLUE,
    LCARS_GOLD,
    LCARS_GREEN,
    LCARS_PEACH,
    LCARS_PURPLE,
    LCARS_RED,
    LCARS_TAN,
    apply_lcars_layout,
)
from dashboard.units import axis
from telemetry_buffer.agent_axes import (
    COMPLIANCE_ISOLATED,
    COMPLIANCE_QUARANTINED,
    INFECTION_RECOVERED,
    agent_has_symptomatic_presentation,
    agent_is_infected,
    resolve_agent_axes,
)
from telemetry_buffer.fields import (
    AGENT_AGE_BAND,
    record_agents,
    record_epoch,
)

PATHWAY_LABELS: dict[str, str] = {
    "direct_contact": "Direct Contact",
    "droplet": "Droplet",
    "hvac_airborne": "HVAC Airborne",
    "emesis_aerosol": "Emesis Aerosol",
    "flush_aerosol": "Flush Aerosol",
    "fomite": "Fomite Surface",
    "food_contamination": "Food Contamination",
    "common_source_food": "Common-Source Food",
    "environmental": "Environmental (HVAC Colonization)",
    "environmental_source": "Environmental Source",
}


def pathway_label(pathway: str) -> str:
    """Human label for a pathway id from ``pathway_breakdown`` keys."""
    return PATHWAY_LABELS.get(pathway, pathway.replace("_", " ").title())


# Contact-tracing exposure lists → pathway label, in emit order.
EXPOSURE_LISTS: tuple[tuple[str, str], ...] = (
    ("shared_room_exposures", "Direct Contact"),
    ("droplet_exposures", "Droplet"),
    ("hvac_downstream_exposures", "HVAC Airborne"),
    ("emesis_aerosol_exposures", "Emesis Aerosol"),
    ("flush_aerosol_exposures", "Flush Aerosol"),
    ("fomite_trailing_exposures", "Fomite Surface"),
    ("food_contamination_exposures", "Food Contamination"),
    ("common_source_exposures", "Common-Source Food"),
    ("environmental_exposures", "Environmental"),
)


def aggregate_exposure_counts(
    history: list[dict[str, Any]],
) -> dict[str, int]:
    """Count delivered-exposure records per pathway across all epochs."""
    counts: dict[str, int] = {}
    for rec in history:
        ct = rec.get("contact_tracing") or {}
        for key, label in EXPOSURE_LISTS:
            n = len(ct.get(key) or [])
            if n:
                counts[label] = counts.get(label, 0) + n
    return counts


def collect_common_source_events(
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten ``common_source_events`` into table rows, newest epoch last."""
    rows: list[dict[str, Any]] = []
    for rec in history:
        ct = rec.get("contact_tracing") or {}
        for ev in ct.get("common_source_events") or []:
            rows.append({
                "epoch": rec.get("epoch", record_epoch(rec)),
                "event": ev.get("event_id", ""),
                "pathogen": ev.get("pathogen_id", ""),
                "zone": ev.get("zone", ""),
                "meal": ev.get("meal", ""),
                "source": ev.get("source_kind", ""),
                "posture": ev.get("food_safety_posture"),
                "window": f"{ev.get('start_epoch')}–{ev.get('end_epoch')}",
                "cohort": ev.get("cohort_size"),
                "servings": ev.get("servings_taken"),
                "dose/serving": ev.get("per_serving_dose"),
            })
    return rows


def route_attribution(
    history: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, float]]:
    """Latest cumulative dominant-route counts and dose-share snapshot."""
    for rec in reversed(history):
        summary = rec.get("summary") or {}
        counts = summary.get("infections_by_dominant_route") or {}
        share = summary.get("infection_dose_share_by_route") or {}
        if counts or share:
            return dict(counts), dict(share)
    return {}, {}


def _pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.1f}%"


def passenger_crew_rates(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Passenger/crew split table from one epoch summary block."""
    rows: list[dict[str, Any]] = []
    for label, prefix in (("Passengers", "passenger"), ("Crew", "crew")):
        complement = summary.get(f"{prefix}_complement")
        if complement is None:
            continue
        rows.append({
            "Group": label,
            "Complement": complement,
            "Ever infected": summary.get(f"cumulative_ever_infected_{prefix}"),
            "Ever ill": summary.get(f"cumulative_ever_ill_{prefix}"),
            "Reported": summary.get(f"cumulative_reported_cases_{prefix}"),
            "Attack rate": _pct(summary.get(f"infection_attack_rate_{prefix}")),
            "Illness rate": _pct(summary.get(f"ever_ill_rate_{prefix}")),
            "Reported rate": _pct(summary.get(f"reported_case_rate_{prefix}")),
        })
    return rows


def sanitary_activity_totals(
    history: list[dict[str, Any]],
) -> dict[str, float]:
    """Latest cumulative sanitary-activity block, when it did any work."""
    for rec in reversed(history):
        activity = (rec.get("summary") or {}).get("sanitary_activity") or {}
        if any(
            isinstance(v, (int, float)) and v
            for v in activity.values()
        ):
            return dict(activity)
    return {}


def aggregate_age_band_stats(
    agents: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Infection distribution by HOST-AGE age band; skips unbanded agents."""
    stats: dict[str, dict[str, int]] = {}
    for agent in agents:
        band = agent.get(AGENT_AGE_BAND)
        if not band:
            continue
        s = stats.setdefault(str(band), {
            "total": 0, "infected": 0, "symptomatic": 0,
            "recovered": 0, "confined": 0,
        })
        s["total"] += 1
        infection, _, compliance = resolve_agent_axes(agent)
        if agent_is_infected(agent):
            s["infected"] += 1
        if agent_has_symptomatic_presentation(agent):
            s["symptomatic"] += 1
        if infection == INFECTION_RECOVERED:
            s["recovered"] += 1
        if compliance in (COMPLIANCE_QUARANTINED, COMPLIANCE_ISOLATED):
            s["confined"] += 1
    return stats


def information_series(history: list[dict[str, Any]]) -> pd.DataFrame:
    """Per-epoch trust/reputation/rumor aggregates from information_state."""
    rows: list[dict[str, Any]] = []
    for rec in history:
        ist = rec.get("information_state") or {}
        if not ist:
            continue
        reputation = ist.get("reputation") or {}
        agents = ist.get("agents") or {}
        rumor = [
            float(a.get("rumor_exposure") or 0.0)
            for a in agents.values()
            if isinstance(a, dict)
        ]
        beliefs = [
            float(a["severity_belief"])
            for a in agents.values()
            if isinstance(a, dict) and a.get("severity_belief") is not None
        ]
        rows.append({
            "epoch": record_epoch(rec),
            "trust_command": reputation.get("trust_command"),
            "trust_medical": reputation.get("trust_medical"),
            "corporate_reputation_risk": reputation.get(
                "corporate_reputation_risk",
            ),
            "mean_rumor_exposure": sum(rumor) / len(rumor) if rumor else None,
            "max_rumor_exposure": max(rumor) if rumor else None,
            "mean_severity_belief": (
                sum(beliefs) / len(beliefs) if beliefs else None
            ),
        })
    return pd.DataFrame(rows)


def collect_decision_rows(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten applied decision-engine actions into a log table."""
    rows: list[dict[str, Any]] = []
    for rec in history:
        decisions = rec.get("decisions") or {}
        by_actor = decisions.get("by_actor") or {}
        for actor, actions in sorted(by_actor.items()):
            for action in actions or []:
                if isinstance(action, str):
                    label = action
                else:
                    label = str(action)
                if label == "noop":
                    continue
                rows.append({
                    "epoch": record_epoch(rec),
                    "actor": actor,
                    "action": label,
                })
    return rows


def collect_sop_events(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten reactive-protocol SOP events into a log table."""
    rows: list[dict[str, Any]] = []
    for rec in history:
        rp = rec.get("reactive_protocols") or {}
        for ev in rp.get("sop_events") or []:
            modifiers = ev.get("modifiers") or {}
            rows.append({
                "epoch": ev.get("epoch", record_epoch(rec)),
                "protocol": ev.get("protocol_id", ""),
                "name": ev.get("name", ""),
                "event": ev.get("event", ""),
                "forced": bool(ev.get("forced")),
                "modifiers": ", ".join(sorted(modifiers)) if modifiers else "",
            })
    return rows


def render_route_attribution(history: list[dict[str, Any]]) -> None:
    """Infection counts and dose share by dominant route."""
    counts, share = route_attribution(history)
    if not counts and not share:
        return

    st.subheader("Route Attribution")
    c1, c2 = st.columns(2)
    colors = [LCARS_BLUE, LCARS_PURPLE, LCARS_GOLD, LCARS_PEACH,
              LCARS_GREEN, LCARS_RED, LCARS_TAN, LCARS_AMBER]
    with c1:
        if counts:
            labels = [pathway_label(r) for r in sorted(counts)]
            values = [counts[r] for r in sorted(counts)]
            fig = go.Figure(data=[go.Bar(
                x=labels, y=values, marker_color=colors[: len(labels)],
            )])
            apply_lcars_layout(
                fig, height=300,
                title="Infections by dominant route",
                yaxis_title=axis("persons").title,
                margin={"t": 50, "b": 80, "l": 50, "r": 20},
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if share:
            labels = [pathway_label(r) for r in sorted(share)]
            values = [float(share[r]) for r in sorted(share)]
            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values, hole=0.4,
                marker={"colors": colors[: len(labels)]},
                textinfo="label+percent",
                textfont={"color": "white"},
            )])
            apply_lcars_layout(
                fig, height=300,
                title="Delivered dose share by route",
                margin={"t": 50, "b": 20, "l": 20, "r": 20},
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


def render_passenger_crew_rates(summary: dict[str, Any]) -> None:
    """Passenger vs crew attack/report rates, when role splits are emitted."""
    rows = passenger_crew_rates(summary)
    if not rows:
        return
    st.subheader("Passenger / Crew Rates")
    noise = summary.get("cumulative_reported_noise_cases")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if noise:
        st.caption(
            f"Reported-case rates include {noise} background noise "
            "presentation(s) (non-infectious sick-call traffic)."
        )


def render_sanitary_activity(history: list[dict[str, Any]]) -> None:
    """Sanitary-visit block: head traffic + flush aerosol bookkeeping."""
    activity = sanitary_activity_totals(history)
    if not activity:
        return
    st.subheader("Sanitary Activity")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sanitary visits", int(activity.get("visits", 0)))
    c2.metric("Stool events", int(activity.get("stool_visits", 0)))
    c3.metric(
        "Dwell time",
        f"{activity.get('person_seconds', 0.0):,.0f} person-s",
    )
    c4.metric("Unresolved queue", int(activity.get("unresolved", 0)))
    flush_events = int(activity.get("flush_events", 0))
    flush_recipients = int(activity.get("flush_recipients", 0))
    if flush_events or flush_recipients:
        st.caption(
            f"Flush aerosol: {flush_events} event(s), "
            f"{flush_recipients} recipient(s), "
            f"delivered {activity.get('flush_dose_delivered', 0.0):.3g} / "
            f"emitted {activity.get('flush_aerosol_emitted', 0.0):.3g}."
        )


def render_age_band_breakdown(last: dict[str, Any]) -> None:
    """Per-age-band infection table (HOST-AGE axes) for the final epoch."""
    stats = aggregate_age_band_stats(record_agents(last))
    if len(stats) < 2:
        return
    st.subheader("Age-Band Breakdown")
    rows = []
    for band, s in sorted(stats.items()):
        rate = (s["infected"] / s["total"] * 100) if s["total"] else 0.0
        rows.append({
            "Age band": band.replace("_", " ").title(),
            "Complement": s["total"],
            "Infected": s["infected"],
            "Symptomatic": s["symptomatic"],
            "Recovered": s["recovered"],
            "Confined": s["confined"],
            "Attack rate": f"{rate:.1f}%",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_exposure_totals(history: list[dict[str, Any]]) -> None:
    """Delivered-exposure records per pathway (contact-tracing feed)."""
    counts = aggregate_exposure_counts(history)
    if not counts:
        return
    st.markdown("**Delivered exposures by pathway**")
    labels = sorted(counts)
    fig = go.Figure(data=[go.Bar(
        x=labels,
        y=[counts[l] for l in labels],
        marker_color=LCARS_PEACH,
    )])
    apply_lcars_layout(
        fig, height=280,
        title="Exposure records delivered per pathway",
        yaxis_title="exposure records",
        margin={"t": 50, "b": 80, "l": 60, "r": 20},
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_common_source_log(history: list[dict[str, Any]]) -> None:
    """Common-source meal events provisioned during the voyage."""
    rows = collect_common_source_events(history)
    if not rows:
        return
    st.markdown("**Common-source event log**")
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def render_information_environment(history: list[dict[str, Any]]) -> None:
    """Trust / rumor / reputation dynamics plus the decision log."""
    df = information_series(history)
    sop_rows = collect_sop_events(history)
    decision_rows = collect_decision_rows(history)
    if df.empty and not sop_rows and not decision_rows:
        return

    st.subheader("Information Environment")

    if not df.empty:
        latest = df.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        if pd.notna(latest.get("trust_command")):
            c1.metric("Trust — command", f"{latest['trust_command']:.2f}")
        if pd.notna(latest.get("trust_medical")):
            c2.metric("Trust — medical", f"{latest['trust_medical']:.2f}")
        if pd.notna(latest.get("corporate_reputation_risk")):
            c3.metric(
                "Reputation risk",
                f"{latest['corporate_reputation_risk']:.2f}",
            )
        if pd.notna(latest.get("mean_rumor_exposure")):
            c4.metric(
                "Mean rumor exposure",
                f"{latest['mean_rumor_exposure']:.2f}",
            )

        fig = go.Figure()
        series = [
            ("trust_command", "Trust — command", LCARS_GOLD),
            ("trust_medical", "Trust — medical", LCARS_BLUE),
            ("corporate_reputation_risk", "Reputation risk", LCARS_RED),
            ("mean_rumor_exposure", "Mean rumor exposure", LCARS_PURPLE),
            ("mean_severity_belief", "Mean severity belief", LCARS_PEACH),
        ]
        for col, name, color in series:
            if col in df.columns and df[col].notna().any():
                fig.add_trace(go.Scatter(
                    x=df["epoch"], y=df[col],
                    mode="lines+markers", name=name,
                    line={"color": color, "width": 2},
                ))
        if fig.data:
            apply_lcars_layout(
                fig, height=300,
                title="Trust, reputation, and rumor over time",
                xaxis_title=axis("time_epoch").title,
                yaxis_title="level (0–1)",
                yaxis_range=[0, 1],
                margin={"t": 50, "b": 40, "l": 50, "r": 20},
                legend={
                    "orientation": "h", "y": -0.2,
                    "x": 0.5, "xanchor": "center",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

        messages = []
        for rec in history:
            ist = rec.get("information_state") or {}
            for msg in ist.get("public_messages") or []:
                if isinstance(msg, dict):
                    messages.append({
                        "epoch": msg.get("epoch", record_epoch(rec)),
                        **{k: v for k, v in msg.items() if k != "epoch"},
                    })
                else:
                    messages.append({
                        "epoch": record_epoch(rec), "message": str(msg),
                    })
        if messages:
            with st.expander("Public messages", expanded=False):
                st.dataframe(
                    pd.DataFrame(messages).tail(50),
                    use_container_width=True, hide_index=True,
                )

    if decision_rows:
        st.markdown("**Command / medical decisions applied**")
        st.dataframe(
            pd.DataFrame(decision_rows),
            use_container_width=True, hide_index=True,
        )
    if sop_rows:
        st.markdown("**SOP activations**")
        st.dataframe(
            pd.DataFrame(sop_rows),
            use_container_width=True, hide_index=True,
        )
