"""Tactical Sensor Grid — architectural elevation + per-deck plan views."""
from __future__ import annotations

import base64
import os
from collections import defaultdict
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from dashboard.architectural_graphics import ordered_decks
from dashboard.deck_geometry import (
    collect_zone_metrics,
    color_scale_max,
    compute_agent_positions,
    compute_agent_trail,
    iter_compartment_rings,
    iter_hull_rings,
    iter_hvac_paths,
    metric_fraction,
    zone_metric,
)
from dashboard.loaders import PlatformBundle
from dashboard.pydeck_builder import build_pydeck_deck
from dashboard.retention import render_retention_banner
from dashboard.session_state import get_selected_agent_id, get_selected_zone_id, set_selected_zone
from dashboard.theme import (
    LCARS_GOLD,
    LCARS_PEACH,
    STOPLIGHT_COLORS,
    _lcars_alert_banner,
    _lcars_banner,
    _worst_stoplight,
    apply_lcars_layout,
)
from dashboard.units import axis

_AGENT_COLORS = {
    "susceptible": "#4a90d9",
    "infected": "#e05050",
    "recovered": "#50a050",
    "immune": "#808080",
}

_CLASS_COLOR_PALETTE = [
    "#4a90d9", "#e05050", "#50a050", "#c9a227", "#9b59b6",
    "#e67e22", "#1abc9c", "#e91e63", "#3498db", "#8e44ad",
]


def _colors_for_agents(positions: list[dict[str, Any]], color_by: str) -> list[str]:
    """Map agent markers to colors for infection state or agent class."""
    if color_by == "agent_class":
        classes = sorted({str(p.get("agent_class", "") or "unknown") for p in positions})
        class_colors = {
            cls: _CLASS_COLOR_PALETTE[i % len(_CLASS_COLOR_PALETTE)]
            for i, cls in enumerate(classes)
        }
        return [
            class_colors.get(str(p.get("agent_class", "") or "unknown"), "#333333")
            for p in positions
        ]
    return [
        _AGENT_COLORS.get(p.get("infection_state", ""), "#333333")
        for p in positions
    ]


def _add_agent_layer(
    fig: go.Figure,
    history: list[dict[str, Any]],
    record: dict[str, Any],
    bundle: PlatformBundle,
    deck_filter: str,
    *,
    show_agents: bool,
    show_trails: bool,
    color_by: str,
) -> None:
    if not show_agents and not show_trails:
        return
    positions = compute_agent_positions(record, bundle, deck_filter)
    if show_trails:
        trail_agent = get_selected_agent_id()
        if trail_agent is not None:
            trail = compute_agent_trail(
                history, trail_agent, bundle, end_epoch=record["epoch"],
            )
            if len(trail) > 1:
                fig.add_trace(go.Scatter(
                    x=[p[0] for p in trail],
                    y=[p[1] for p in trail],
                    mode="lines+markers",
                    line={"color": LCARS_GOLD, "width": 2, "dash": "dot"},
                    marker={"size": 4},
                    name=f"Trail agent {trail_agent}",
                    showlegend=True,
                ))
    if not show_agents or not positions:
        return
    color_key = color_by if color_by in ("infection_state", "agent_class") else "infection_state"
    colors = _colors_for_agents(positions, color_key)
    sel = get_selected_agent_id()
    sizes = [10 if p["agent_id"] == sel else 5 for p in positions]
    fig.add_trace(go.Scatter(
        x=[p["x"] for p in positions],
        y=[p["y"] for p in positions],
        mode="markers",
        marker={"color": colors, "size": sizes, "line": {"width": 1, "color": _INK}},
        text=[
            f"Agent {p['agent_id']}<br>{p['location']}<br>"
            f"{p['infection_state']} / {p.get('agent_class', '')}"
            for p in positions
        ],
        hoverinfo="text",
        name="Agents",
        showlegend=False,
    ))


def _add_hvac_exposure_overlay(
    fig: go.Figure,
    record: dict[str, Any],
    bundle: PlatformBundle,
    deck_filter: str,
) -> None:
    exposed_zones: set[str] = set()
    for exp in record.get("contact_tracing", {}).get("hvac_downstream_exposures", []):
        exposed_zones.add(str(exp.get("zone", "")))
    if not exposed_zones:
        return
    for path in iter_hvac_paths(bundle, deck_filter):
        fig.add_trace(go.Scatter(
            x=[c[0] for c in path],
            y=[c[1] for c in path],
            mode="lines",
            line={"color": "rgba(220,80,40,0.75)", "width": 3},
            hoverinfo="skip",
            showlegend=False,
        ))

_PAPER = "#f4f7fb"
_INK = "#1a2a3a"
_GRID = "rgba(40, 80, 120, 0.12)"
_HULL_LINE = "#2a4a6a"
_COMP_EDGE = "#3d6a8a"


def footprint_caption(manifest: dict[str, Any]) -> str:
    tier = manifest.get("footprint_tier", "unknown")
    label = manifest.get("ship_class_label", "Vessel")
    arch = manifest.get("architectural_graphics") or {}
    credit_bits = []
    elev = arch.get("elevation") or {}
    plan = arch.get("plan") or {}
    if elev.get("credit"):
        credit_bits.append(f"elevation: {elev['credit']}")
    if plan.get("credit"):
        credit_bits.append(f"plan: {plan['credit']}")
    photo_note = (" " + "; ".join(credit_bits) + ".") if credit_bits else ""
    if tier == "representative":
        return (
            f"*Architectural class-representative plate for **{label}** — "
            f"simulation zones overlaid; not a surveyed vessel drawing.{photo_note}*"
        )
    if tier == "fiction_adapted":
        return (
            f"*Fiction-adapted architectural layout for **{label}** — "
            f"demonstration only; simplified silhouette, not show artwork.{photo_note}*"
        )
    if tier == "gis_traced":
        return f"*GIS-traced compartments for **{label}**.{photo_note}*"
    return f"*{label}*{photo_note}"


def _image_uri(path: str) -> str | None:
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        data = base64.b64encode(fh.read()).decode("ascii")
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{data}"


def _add_underlay(
    fig: go.Figure,
    path: str | None,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    *,
    opacity: float = 0.88,
) -> None:
    uri = _image_uri(path) if path else None
    if not uri:
        return
    fig.add_layout_image(
        {
            "source": uri,
            "xref": "x",
            "yref": "y",
            "x": xmin,
            "y": ymin,
            "yanchor": "bottom",
            "sizex": xmax - xmin,
            "sizey": ymax - ymin,
            "sizing": "stretch",
            "opacity": opacity,
            "layer": "below",
        },
    )


def _plotly_rgba(fraction: float) -> str:
    if fraction <= 0.01:
        return "rgba(230, 236, 242, 0.55)"
    if fraction < 0.33:
        return f"rgba(120, 180, 140,{0.35 + 0.35 * fraction})"
    if fraction < 0.66:
        return f"rgba(230, 160, 60,{0.4 + 0.3 * fraction})"
    return f"rgba(190, 80, 80,{0.45 + 0.35 * fraction})"


def _plan_bounds(bundle: PlatformBundle) -> tuple[float, float, float, float]:
    dims = bundle.layout.get("deck_dimensions", {}) or {}
    length_m = float(dims.get("length_m", 120))
    beam_m = float(dims.get("beam_m", 15))
    bounds = bundle.manifest.get("view_bounds") or {}
    xmin = float(bounds.get("xmin", -2))
    xmax = float(bounds.get("xmax", length_m + 2))
    ymin = float(bounds.get("ymin", -2))
    ymax = float(bounds.get("ymax", beam_m + 2))
    # Prefer hull-native bounds so the plan underlay maps cleanly.
    return (
        min(xmin, -2.0),
        max(xmax, length_m + 2.0),
        min(ymin, -2.0),
        max(ymax, beam_m + 2.0),
    )


def _build_plotly_plan_map(
    record: dict[str, Any],
    bundle: PlatformBundle,
    color_mode: str,
    deck_filter: str,
    *,
    history: list[dict[str, Any]] | None = None,
    show_agents: bool = False,
    show_trails: bool = False,
    agent_color_by: str = "infection_state",
    hvac_exposure: bool = False,
) -> go.Figure:
    """Top-down architectural plan for a single deck (never stacks all decks)."""
    fig = go.Figure()
    xmin, xmax, ymin, ymax = _plan_bounds(bundle)

    metrics = collect_zone_metrics(record, bundle, color_mode, deck_filter)
    scale_max = color_scale_max(metrics)

    arch = bundle.architectural
    plan_path = arch.plan_for_deck(deck_filter) if arch else None
    if not plan_path:
        plan_path = bundle.blueprint_bg_path or bundle.hull_png_path
    _add_underlay(fig, plan_path, xmin, xmax, ymin, ymax, opacity=0.9)

    for kind, ring in iter_hull_rings(bundle):
        xs = [p[0] for p in ring] + [ring[0][0]]
        ys = [p[1] for p in ring] + [ring[0][1]]
        if kind == "hull_waterline":
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                line={"color": "rgba(80,120,160,0.45)", "width": 1, "dash": "dot"},
                hoverinfo="skip",
                showlegend=False,
            ))
            continue
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line={"color": _HULL_LINE, "width": 2},
            fill="toself",
            fillcolor="rgba(0,0,0,0)",
            hoverinfo="skip",
            showlegend=False,
            name="hull",
        ))

    for path in iter_hvac_paths(bundle, deck_filter):
        fig.add_trace(go.Scatter(
            x=[c[0] for c in path],
            y=[c[1] for c in path],
            mode="lines",
            line={"color": "rgba(180,120,40,0.35)", "width": 1},
            hoverinfo="skip",
            showlegend=False,
        ))

    sorted_zones = sorted(
        iter_compartment_rings(bundle, deck_filter),
        key=lambda t: metrics.get(t[0], 0.0),
    )
    for zid, ring, _deck in sorted_zones:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        val = metrics.get(zid, 0.0)
        frac = metric_fraction(val, scale_max)
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            fill="toself",
            fillcolor=_plotly_rgba(frac),
            line={"color": _COMP_EDGE, "width": 1.25},
            hovertext=f"<b>{zid}</b><br>{color_mode}: {val:.3g}",
            hoverinfo="text",
            showlegend=False,
        ))

    if history is not None:
        _add_agent_layer(
            fig, history, record, bundle, deck_filter,
            show_agents=show_agents,
            show_trails=show_trails,
            color_by=agent_color_by,
        )
    if hvac_exposure:
        _add_hvac_exposure_overlay(fig, record, bundle, deck_filter)

    label = bundle.manifest.get("ship_class_label", bundle.platform_id)
    apply_lcars_layout(
        fig,
        title=f"Plan — {label} — Deck {deck_filter} — Epoch {record['epoch']}",
        plot_bgcolor=_PAPER,
        paper_bgcolor=_PAPER,
        height=480,
        font={"color": _INK},
        xaxis={
            "range": [xmin, xmax],
            "showgrid": True,
            "gridcolor": _GRID,
            "title": axis("length_m").title,
            "scaleanchor": "y",
            "scaleratio": 1,
            "constrain": "domain",
            "color": _INK,
        },
        yaxis={
            "range": [ymin, ymax],
            "showgrid": True,
            "gridcolor": _GRID,
            "title": axis("beam_m").title,
            "constrain": "domain",
            "color": _INK,
        },
        margin={"t": 55, "b": 50, "l": 55, "r": 30},
    )
    return fig


def _deck_aggregate_metrics(
    record: dict[str, Any],
    bundle: PlatformBundle,
    color_mode: str,
    decks: list[str],
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for zid, zinfo in bundle.zone_coords.items():
        deck = str(zinfo.get("deck", "main"))
        if deck not in decks:
            continue
        totals[deck] += zone_metric(record, zid, color_mode)
    return dict(totals)


def _build_plotly_elevation(
    record: dict[str, Any],
    bundle: PlatformBundle,
    color_mode: str,
    decks: list[str],
    highlight_deck: str | None,
) -> go.Figure:
    """Side elevation: one horizontal band per deck — never overdraws the plan."""
    fig = go.Figure()
    dims = bundle.layout.get("deck_dimensions", {}) or {}
    length_m = float(dims.get("length_m", 120))
    n = max(len(decks), 1)
    band_h = 1.0
    gap = 0.15
    total_h = n * band_h + (n - 1) * gap
    xmin, xmax = -length_m * 0.02, length_m * 1.02
    ymin, ymax = -0.4, total_h + 0.4

    arch = bundle.architectural
    elev_path = arch.elevation_path if arch and arch.has_elevation else None
    _add_underlay(fig, elev_path, xmin, xmax, ymin, ymax, opacity=0.82)

    deck_vals = _deck_aggregate_metrics(record, bundle, color_mode, decks)
    scale_max = color_scale_max(deck_vals)

    # Low decks at bottom (keel), high decks at top — architectural elevation convention.
    for i, deck in enumerate(decks):
        y0 = i * (band_h + gap)
        y1 = y0 + band_h
        val = deck_vals.get(deck, 0.0)
        frac = metric_fraction(val, scale_max)
        edge = LCARS_GOLD if deck == highlight_deck else _COMP_EDGE
        width = 2.5 if deck == highlight_deck else 1.0
        fig.add_trace(go.Scatter(
            x=[0, length_m, length_m, 0, 0],
            y=[y0, y0, y1, y1, y0],
            mode="lines",
            fill="toself",
            fillcolor=_plotly_rgba(frac),
            line={"color": edge, "width": width},
            hovertext=f"<b>{deck}</b><br>{color_mode} (deck sum): {val:.3g}",
            hoverinfo="text",
            showlegend=False,
        ))
        fig.add_annotation(
            x=length_m * 0.02,
            y=(y0 + y1) / 2,
            text=deck,
            showarrow=False,
            xanchor="left",
            font={"size": 10, "color": _INK},
        )

    label = bundle.manifest.get("ship_class_label", bundle.platform_id)
    apply_lcars_layout(
        fig,
        title=f"Elevation — {label} — Epoch {record['epoch']}",
        plot_bgcolor=_PAPER,
        paper_bgcolor=_PAPER,
        height=480,
        font={"color": _INK},
        xaxis={
            "range": [xmin, xmax],
            "showgrid": True,
            "gridcolor": _GRID,
            "title": axis("length_m").title,
            "color": _INK,
        },
        yaxis={
            "range": [ymin, ymax],
            "showgrid": False,
            "title": axis("deck_stack").title,
            "color": _INK,
            "tickvals": [],
        },
        margin={"t": 55, "b": 50, "l": 55, "r": 20},
    )
    return fig


def _render_deck_filter(deck_options: list[str], *, key_suffix: str = "") -> str:
    st.caption("Deck level (plan view — one deck at a time)")
    if len(deck_options) <= 10:
        return st.radio(
            "Deck level",
            deck_options,
            horizontal=True,
            key=f"deck_filter{key_suffix}",
            label_visibility="collapsed",
        )
    return st.selectbox(
        "Deck level",
        deck_options,
        key=f"deck_filter{key_suffix}",
        label_visibility="collapsed",
    )


def _render_stoplight_panel(stoplights: dict[str, Any]) -> None:
    st.markdown(
        _lcars_banner("Instrument Sensor Array", "#9999FF"),
        unsafe_allow_html=True,
    )
    cols = st.columns(len(stoplights))
    for i, (inst, level) in enumerate(stoplights.items()):
        resolved = _worst_stoplight(level)
        color = STOPLIGHT_COLORS.get(resolved, "gray")
        pulse = (
            "box-shadow:0 0 12px " + color + ";"
            if resolved == "RED" else ""
        )
        short = inst.replace("_", " ").title()[:20]
        with cols[i]:
            st.markdown(
                f"<div style='background:{color}22; border:2px solid {color}; "
                f"padding:6px; border-radius:6px; text-align:center; "
                f"color:{color}; font-size:11px; font-weight:bold;{pulse}'>"
                f"{short}<br>{resolved}</div>",
                unsafe_allow_html=True,
            )


def render_tactical_grid(
    history: list[dict[str, Any]],
    bundle: PlatformBundle,
    *,
    key_suffix: str = "",
    selected_epoch: int | None = None,
    retention_mode: str = "full",
) -> None:
    if not history:
        st.warning("Sensors offline. No telemetry data.")
        return

    if not bundle.deck_graphics.get("features") and not bundle.zone_coords:
        st.error(
            f"No deck graphics for **{bundle.platform_id}**. "
            "Run `python3 scripts/precompute_deck_assets.py`."
        )
        return

    if bundle.architectural and bundle.architectural.raw:
        bundle.manifest.setdefault(
            "architectural_graphics",
            {
                "elevation": {"credit": bundle.architectural.elevation_credit},
                "plan": {"credit": bundle.architectural.plan_credit},
            },
        )

    st.caption(footprint_caption(bundle.manifest))
    arch = bundle.architectural
    if arch and not arch.has_plan and not arch.has_elevation:
        st.info(
            "No user architectural plates in `graphics/`. "
            "Add `elevation.jpg` and `plan_overview.jpg` (see `graphics/graphics.json`), "
            "then re-run precompute if needed."
        )

    decks = ordered_decks(bundle.layout) or ["main"]
    epoch_idx = selected_epoch if selected_epoch is not None else 0
    epoch_idx = max(0, min(epoch_idx, len(history) - 1))

    c1, c2 = st.columns([3, 2])
    with c1:
        color_mode = st.radio(
            "Sensor Overlay",
            [
                "Airborne Aerosol Mass",
                "Surface Fomite Contamination",
                "Symptomatic Agent Count",
            ],
            horizontal=True,
            key=f"deck_color{key_suffix}",
        )
    with c2:
        deck_filter = _render_deck_filter(decks, key_suffix=key_suffix)

    has_agents = retention_mode == "full" and bool(history[0].get("agents"))
    show_agents = False
    show_trails = False
    agent_color_by = "infection_state"
    hvac_exposure = False
    if has_agents:
        show_agents = st.checkbox("Show agents on plan", value=False, key=f"show_agents{key_suffix}")
        show_trails = st.checkbox("Show selected agent trail", value=False, key=f"show_trails{key_suffix}")
        agent_color_by = st.selectbox(
            "Agent color by",
            ["infection_state", "agent_class"],
            key=f"agent_color{key_suffix}",
        )
        hvac_exposure = st.checkbox("Highlight HVAC exposures", value=False, key=f"hvac_exp{key_suffix}")
    elif retention_mode == "compact":
        render_retention_banner(retention_mode, feature="Agent movement layer")

    record = history[epoch_idx]
    st.markdown(_lcars_alert_banner(record["trigger_status"]), unsafe_allow_html=True)

    sel_zone = get_selected_zone_id()
    if sel_zone:
        st.caption(f"Selected zone: **{sel_zone}**")
        zone_pick = st.selectbox(
            "Filter by zone",
            ["(all)"] + sorted(record.get("spaces", {}).keys()),
            index=0,
            key=f"zone_filter{key_suffix}",
        )
        if zone_pick != "(all)":
            set_selected_zone(zone_pick)

    metrics = collect_zone_metrics(record, bundle, color_mode, deck_filter)
    active = sum(1 for v in metrics.values() if v > 0)
    st.caption(
        f"Epoch **{record['epoch']}** · **{len(metrics)}** compartments on **{deck_filter}** "
        f"({active} non-zero)."
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            _lcars_banner("Ship Elevation (profile)", LCARS_GOLD),
            unsafe_allow_html=True,
        )
        elev_fig = _build_plotly_elevation(
            record, bundle, color_mode, decks, highlight_deck=deck_filter,
        )
        st.plotly_chart(elev_fig, use_container_width=True)
        if arch and arch.elevation_credit:
            st.caption(arch.elevation_credit)

    with right:
        st.markdown(
            _lcars_banner(f"Deck Plan — {deck_filter}", LCARS_PEACH),
            unsafe_allow_html=True,
        )
        plan_fig = _build_plotly_plan_map(
            record, bundle, color_mode, deck_filter,
            history=history,
            show_agents=show_agents,
            show_trails=show_trails,
            agent_color_by=agent_color_by,
            hvac_exposure=hvac_exposure,
        )
        st.plotly_chart(plan_fig, use_container_width=True)
        if arch and arch.plan_credit:
            st.caption(arch.plan_credit)

    with st.expander("Advanced tactical display", expanded=False):
        if st.checkbox(
            "Use pydeck renderer (experimental, plan only)",
            value=False,
            key=f"deck_pydeck{key_suffix}",
        ):
            deck_obj = build_pydeck_deck(
                bundle, record, bundle.manifest, color_mode, deck_filter,
            )
            if deck_obj is not None:
                st.pydeck_chart(deck_obj, use_container_width=True, height=520)

    stoplights = record.get("reactive_protocols", {}).get("stoplights", {})
    if stoplights:
        _render_stoplight_panel(stoplights)

    active_sops = record.get("reactive_protocols", {}).get("active_protocols", [])
    if active_sops:
        names = [p.get("name", p.get("protocol_id", "?")) for p in active_sops]
        st.markdown(
            _lcars_banner(f"Active Standing Orders: {', '.join(names)}", LCARS_GOLD),
            unsafe_allow_html=True,
        )

    with st.expander(f"Crew Disposition — Epoch {epoch_idx}", expanded=False):
        agents = record.get("agents", [])
        if agents:
            import pandas as pd
            df = pd.DataFrame(agents).sort_values("agent_id")
            if sel_zone:
                df = df[df["location"] == sel_zone]
            preferred = [
                "agent_id", "agent_class", "location",
                "infection_state", "symptom_presentation", "compliance_status",
                "shedding_rate", "gender",
            ]
            cols = [c for c in preferred if c in df.columns]
            extra = [c for c in df.columns if c not in cols]
            st.dataframe(
                df[cols + extra],
                use_container_width=True,
                hide_index=True,
            )
        elif retention_mode == "compact":
            st.info("Per-agent disposition requires full telemetry retention.")
