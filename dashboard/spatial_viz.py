"""Tactical Sensor Grid — pydeck primary, Plotly fallback."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from dashboard.loaders import PlatformBundle
from dashboard.pydeck_builder import build_pydeck_deck
from dashboard.theme import (
    LCARS_AMBER,
    LCARS_GOLD,
    LCARS_GREEN,
    LCARS_PEACH,
    LCARS_PLOTLY,
    LCARS_RED,
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


def _metric_value(record: dict[str, Any], zone_id: str, color_mode: str) -> float:
    spaces = record.get("spaces", {})
    obs = record.get("observation_engine", {})
    if color_mode == "Airborne Aerosol Mass":
        return float(spaces.get(zone_id, {}).get("pathogen_mass", 0.0))
    if color_mode == "Surface Fomite Contamination":
        return float(obs.get("surface_swab", {}).get(zone_id, {}).get("surface_mass", 0.0))
    n = 0
    for agent in record.get("agents", []):
        if agent.get("location") == zone_id and agent.get("status") in (
            "symptomatic", "infected",
        ):
            n += 1
    return float(n)


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

    max_val = 0.0
    zone_metrics: dict[str, float] = {}
    for zid in bundle.zone_coords:
        if deck_filter and deck_filter != "All Decks":
            if bundle.zone_coords[zid].get("deck") != deck_filter:
                continue
        v = _metric_value(record, zid, color_mode)
        zone_metrics[zid] = v
        max_val = max(max_val, v)

    for feat in bundle.deck_graphics.get("features", []):
        props = feat.get("properties", {})
        kind = props.get("kind", "")
        geom = feat.get("geometry", {})
        if kind == "hull_outline" and geom.get("type") == "Polygon":
            ring = geom["coordinates"][0]
            xs = [p[0] for p in ring] + [ring[0][0]]
            ys = [p[1] for p in ring] + [ring[0][1]]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                line={"color": LCARS_GOLD, "width": 3},
                hoverinfo="skip", showlegend=False,
            ))
        elif kind == "hvac_path" and geom.get("type") == "LineString":
            coords = geom["coordinates"]
            fig.add_trace(go.Scatter(
                x=[c[0] for c in coords], y=[c[1] for c in coords],
                mode="lines",
                line={"color": "rgba(255,153,0,0.35)", "width": 1.5},
                hoverinfo="skip", showlegend=False,
            ))

    for feat in bundle.deck_graphics.get("features", []):
        props = feat.get("properties", {})
        if props.get("kind") != "compartment":
            continue
        zid = props.get("zone_id", "")
        if deck_filter and deck_filter != "All Decks":
            if props.get("deck") != deck_filter:
                continue
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        ring = geom["coordinates"][0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        val = zone_metrics.get(zid, 0.0)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself",
            fillcolor=_plotly_fill_color(val, max_val),
            line={"color": LCARS_PEACH, "width": 1},
            name=zid, showlegend=False,
            hovertext=f"{zid}: {val:.2f}", hoverinfo="text",
        ))

    for link in bundle.airflow.get("adjacency", []):
        fz, tz = link.get("from", ""), link.get("to", "")
        if fz in bundle.zone_coords and tz in bundle.zone_coords:
            fig.add_trace(go.Scatter(
                x=[
                    bundle.zone_coords[fz]["x"],
                    bundle.zone_coords[tz]["x"],
                ],
                y=[
                    bundle.zone_coords[fz]["y"],
                    bundle.zone_coords[tz]["y"],
                ],
                mode="lines",
                line={"color": "rgba(255,153,0,0.2)", "width": 1},
                hoverinfo="skip", showlegend=False,
            ))

    agent_locs: dict[str, int] = {}
    for agent in record.get("agents", []):
        loc = agent.get("location", "unknown")
        agent_locs[loc] = agent_locs.get(loc, 0) + 1

    xs, ys, sizes, texts = [], [], [], []
    for zname, zinfo in bundle.zone_coords.items():
        if deck_filter and deck_filter != "All Decks":
            if zinfo.get("deck") != deck_filter:
                continue
        xs.append(zinfo["x"])
        ys.append(zinfo["y"])
        occ = agent_locs.get(zname, 0)
        sizes.append(max(12, 8 + occ * 4))
        texts.append(zname)

    if xs:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            text=texts, textposition="top center",
            textfont={"size": 9, "color": LCARS_PEACH},
            marker={"size": sizes, "color": LCARS_GOLD, "line": {"width": 1, "color": "#fff"}},
            showlegend=False,
        ))

    label = bundle.manifest.get("ship_class_label", bundle.platform_id)
    fig.update_layout(
        title=f"Tactical Deck Scan — {label} — Epoch {record['epoch']} ({color_mode})",
        **LCARS_PLOTLY,
        height=480,
        xaxis={"range": [xmin, xmax], "showgrid": False, "title": "Ship Length (m)"},
        yaxis={
            "range": [ymin, ymax], "showgrid": False, "title": "Beam (m)",
            "scaleanchor": "x", "scaleratio": 1,
        },
        margin={"t": 60, "b": 40, "l": 50, "r": 80},
    )
    return fig


def _plotly_fill_color(val: float, max_val: float) -> str:
    if max_val <= 0:
        return "rgba(153,204,153,0.55)"
    t = min(1.0, val / max_val)
    if t < 0.33:
        return "rgba(153,204,153,0.55)"
    if t < 0.66:
        return "rgba(255,153,0,0.55)"
    return "rgba(204,102,102,0.65)"


def render_tactical_grid(
    history: list[dict[str, Any]],
    bundle: PlatformBundle,
) -> None:
    if not history:
        st.warning("Sensors offline. No telemetry data.")
        return

    if not bundle.deck_graphics.get("features"):
        st.error(
            f"No deck graphics for **{bundle.platform_id}**. "
            "Run `python3 scripts/precompute_deck_assets.py`."
        )
        return

    st.caption(footprint_caption(bundle.manifest))

    decks = sorted({
        z.get("deck", "main")
        for z in bundle.layout.get("zones", [])
    })
    deck_options = ["All Decks"] + decks

    num_epochs = len(history)
    c1, c2, c3 = st.columns([2, 2, 2])
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
            ["pydeck", "plotly"],
            horizontal=True,
            key="deck_renderer",
        )

    record = history[selected_epoch]
    st.markdown(_lcars_alert_banner(record["trigger_status"]), unsafe_allow_html=True)

    col_map, col_hull = st.columns([4, 1])
    with col_hull:
        if bundle.hull_png_path:
            st.image(bundle.hull_png_path, caption=bundle.manifest.get("ship_class_label", ""))

    with col_map:
        if renderer == "pydeck":
            deck_obj = build_pydeck_deck(
                bundle.deck_graphics,
                record,
                bundle.manifest,
                color_mode,
                deck_filter,
            )
            if deck_obj is not None:
                st.pydeck_chart(deck_obj, use_container_width=True)
            else:
                st.plotly_chart(
                    _build_plotly_deck_map(record, bundle, color_mode, deck_filter),
                    use_container_width=True,
                )
        else:
            st.plotly_chart(
                _build_plotly_deck_map(record, bundle, color_mode, deck_filter),
                use_container_width=True,
            )

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

    active = record.get("reactive_protocols", {}).get("active_protocols", [])
    if active:
        names = [p.get("name", p.get("protocol_id", "?")) for p in active]
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
