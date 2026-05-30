"""Tactical Sensor Grid — ship-local deck plan (Plotly default; optional pydeck)."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from dashboard.deck_geometry import (
    collect_zone_metrics,
    color_scale_max,
    iter_compartment_rings,
    iter_hull_rings,
    iter_hvac_paths,
    metric_fraction,
)
from dashboard.loaders import PlatformBundle
from dashboard.pydeck_builder import build_pydeck_deck
from dashboard.theme import (
    LCARS_GOLD,
    LCARS_PEACH,
    LCARS_PLOTLY,
    STOPLIGHT_COLORS,
    _lcars_alert_banner,
    _lcars_banner,
    _worst_stoplight,
)


def footprint_caption(manifest: dict[str, Any]) -> str:
    tier = manifest.get("footprint_tier", "unknown")
    label = manifest.get("ship_class_label", "Vessel")
    if tier == "representative":
        return (
            f"*Class-representative deck plan for **{label}** — simulation zones shown; "
            f"not a specific vessel survey.*"
        )
    if tier == "fiction_adapted":
        return f"*Fiction-adapted layout for **{label}** — demonstration only.*"
    if tier == "gis_traced":
        return f"*GIS-traced compartments for **{label}**.*"
    return f"*{label}*"


def _plotly_rgba(fraction: float) -> str:
    if fraction <= 0.01:
        return "rgba(26,26,46,0.75)"
    if fraction < 0.33:
        return f"rgba(153,204,153,{0.45 + 0.35 * fraction})"
    if fraction < 0.66:
        return f"rgba(255,153,0,{0.5 + 0.3 * fraction})"
    return f"rgba(204,102,102,{0.55 + 0.35 * fraction})"


def _build_plotly_deck_map(
    record: dict[str, Any],
    bundle: PlatformBundle,
    color_mode: str,
    deck_filter: str | None,
) -> go.Figure:
    fig = go.Figure()
    bounds = bundle.manifest.get("view_bounds", {})
    xmin = float(bounds.get("xmin", 0))
    xmax = float(bounds.get("xmax", 120))
    ymin = float(bounds.get("ymin", 0))
    ymax = float(bounds.get("ymax", 15))

    metrics = collect_zone_metrics(record, bundle, color_mode, deck_filter)
    scale_max = color_scale_max(metrics)

    for ring in iter_hull_rings(bundle):
        xs = [p[0] for p in ring] + [ring[0][0]]
        ys = [p[1] for p in ring] + [ring[0][1]]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line={"color": LCARS_GOLD, "width": 5},
            fill="toself",
            fillcolor="rgba(0,0,0,0)",
            hoverinfo="skip",
            showlegend=False,
            name="hull",
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line={"color": "rgba(255,153,0,0.35)", "width": 10},
            hoverinfo="skip",
            showlegend=False,
        ))

    for path in iter_hvac_paths(bundle, deck_filter):
        fig.add_trace(go.Scatter(
            x=[c[0] for c in path],
            y=[c[1] for c in path],
            mode="lines",
            line={"color": "rgba(255,153,0,0.3)", "width": 1},
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
            line={"color": LCARS_PEACH, "width": 1.5},
            hovertext=f"<b>{zid}</b><br>{color_mode}: {val:.3g}",
            hoverinfo="text",
            showlegend=False,
        ))

    label = bundle.manifest.get("ship_class_label", bundle.platform_id)
    n_zones = len(metrics)
    fig.update_layout(
        title=(
            f"Tactical Deck Scan — {label} — Epoch {record['epoch']} "
            f"({color_mode}, {n_zones} zones)"
        ),
        **LCARS_PLOTLY,
        height=520,
        xaxis={
            "range": [xmin, xmax],
            "showgrid": True,
            "gridcolor": "rgba(255,153,0,0.08)",
            "title": "Ship length (m)",
            "scaleanchor": "y",
            "scaleratio": 1,
            "constrain": "domain",
        },
        yaxis={
            "range": [ymin, ymax],
            "showgrid": True,
            "gridcolor": "rgba(255,153,0,0.08)",
            "title": "Beam (m)",
            "constrain": "domain",
        },
        margin={"t": 60, "b": 50, "l": 55, "r": 30},
        plot_bgcolor="rgba(0,0,0,0.85)",
    )
    return fig


def render_tactical_grid(
    history: list[dict[str, Any]],
    bundle: PlatformBundle,
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

    st.caption(footprint_caption(bundle.manifest))

    decks = sorted({z.get("deck", "main") for z in bundle.layout.get("zones", [])})
    deck_options = ["All Decks"] + decks

    num_epochs = len(history)
    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        selected_epoch = st.slider(
            "Epoch", 0, num_epochs - 1, 0, key="deck_epoch",
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
            key="deck_color",
        )
    with c3:
        deck_filter = st.selectbox("Deck", deck_options, key="deck_filter")
        renderer = st.radio(
            "Tactical renderer",
            ["plotly", "pydeck"],
            index=0,
            horizontal=True,
            key="deck_renderer",
            help="Plotly uses ship meters (recommended). Pydeck uses orthographic local coords.",
        )

    record = history[selected_epoch]
    st.markdown(_lcars_alert_banner(record["trigger_status"]), unsafe_allow_html=True)

    metrics = collect_zone_metrics(record, bundle, color_mode, deck_filter)
    active = sum(1 for v in metrics.values() if v > 0)
    st.caption(
        f"Contamination overlay on **{len(metrics)}** compartments "
        f"({active} non-zero readings). Colors use 90th-percentile scaling so the "
        f"full hull stays readable."
    )

    if bundle.hull_png_path:
        st.image(
            bundle.hull_png_path,
            caption=f"{bundle.manifest.get('ship_class_label', '')} — class silhouette",
            use_container_width=True,
        )

    fig = _build_plotly_deck_map(record, bundle, color_mode, deck_filter)

    if renderer == "pydeck":
        deck_obj = build_pydeck_deck(
            bundle, record, bundle.manifest, color_mode, deck_filter,
        )
        if deck_obj is not None:
            st.pydeck_chart(
                deck_obj,
                use_container_width=True,
                height=520,
            )
            with st.expander("Plotly deck plan (same data)", expanded=False):
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.plotly_chart(fig, use_container_width=True)

    stoplights = record.get("reactive_protocols", {}).get("stoplights", {})
    if stoplights:
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
            st.dataframe(
                pd.DataFrame(agents).sort_values("agent_id"),
                use_container_width=True,
                hide_index=True,
            )
