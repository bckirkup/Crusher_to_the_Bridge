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
    iter_compartment_rings,
    iter_hull_rings,
    iter_hvac_paths,
    metric_fraction,
    zone_metric,
)
from dashboard.loaders import PlatformBundle
from dashboard.pydeck_builder import build_pydeck_deck
from dashboard.theme import (
    LCARS_GOLD,
    LCARS_PEACH,
    STOPLIGHT_COLORS,
    _lcars_alert_banner,
    _lcars_banner,
    _worst_stoplight,
    apply_lcars_layout,
)

# Architectural drawing palette (light paper — distinct from LCARS bridge chrome).
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
            "title": "Ship length (m)",
            "scaleanchor": "y",
            "scaleratio": 1,
            "constrain": "domain",
            "color": _INK,
        },
        yaxis={
            "range": [ymin, ymax],
            "showgrid": True,
            "gridcolor": _GRID,
            "title": "Beam (m)",
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
            "title": "Ship length (m)",
            "color": _INK,
        },
        yaxis={
            "range": [ymin, ymax],
            "showgrid": False,
            "title": "Deck stack (keel → top)",
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

    # Attach architectural credits into caption path.
    if bundle.architectural and bundle.architectural.raw:
        bundle.manifest.setdefault(
            "architectural_graphics",
            {
                "elevation": {
                    "credit": bundle.architectural.elevation_credit,
                },
                "plan": {
                    "credit": bundle.architectural.plan_credit,
                },
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

    decks = ordered_decks(bundle.layout)
    if not decks:
        decks = ["main"]

    num_epochs = len(history)
    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        selected_epoch = st.slider(
            "Epoch", 0, num_epochs - 1, 0, key=f"deck_epoch{key_suffix}",
        )
    with c2:
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
    with c3:
        # Single-deck selection only — "All Decks" stacking removed (writes over itself).
        deck_filter = _render_deck_filter(decks, key_suffix=key_suffix)

    record = history[selected_epoch]
    st.markdown(_lcars_alert_banner(record["trigger_status"]), unsafe_allow_html=True)

    metrics = collect_zone_metrics(record, bundle, color_mode, deck_filter)
    active = sum(1 for v in metrics.values() if v > 0)
    st.caption(
        f"Plan overlay: **{len(metrics)}** compartments on **{deck_filter}** "
        f"({active} non-zero). Elevation shows per-deck totals; plan and elevation "
        f"are separate panels so drawings do not overwrite each other."
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
        plan_fig = _build_plotly_plan_map(record, bundle, color_mode, deck_filter)
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

    with st.expander(f"Crew Disposition — Epoch {selected_epoch}", expanded=False):
        agents = record.get("agents", [])
        if agents:
            import pandas as pd
            df = pd.DataFrame(agents).sort_values("agent_id")
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
