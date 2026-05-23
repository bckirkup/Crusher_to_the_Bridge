"""
dashboard.py – Crusher-to-the-Bridge Interactive Dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Streamlit app visualizing the infection-dynamics simulation:

1. **Epidemic Timeline Chart** – S/I/Q curves with epoch slider
2. **Spatial Deck Map** – Plotly scatter of room nodes colored by
   pathogen concentration, sized by occupant count
3. **Crusher Surveillance Log** – sidebar showing trigger tier,
   surface wipe deployments, and isolation orders

Usage::

    # First run the simulation to generate history:
    python orchestrator.py

    # Then launch the dashboard:
    streamlit run dashboard.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import plotly.graph_objects as go
import streamlit as st

# ── Paths ────────────────────────────────────────────────────────────────

_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(_DIR, "telemetry_buffer", "simulation_history.json")
LAYOUT_PATH = os.path.join(
    _DIR, "data", "platforms", "destroyer_baseline", "spatial_layout.json",
)
AIRFLOW_PATH = os.path.join(
    _DIR, "data", "platforms", "destroyer_baseline", "air_flow_paths.json",
)

# ── Trigger status styling ───────────────────────────────────────────────

STATUS_COLORS = {
    "BASELINE":  "#2ecc71",
    "SUSPECTED": "#f39c12",
    "CONFIRMED": "#e74c3c",
}
STATUS_ICONS = {
    "BASELINE":  "●",
    "SUSPECTED": "▲",
    "CONFIRMED": "■",
}


# ── Data loading ─────────────────────────────────────────────────────────

@st.cache_data
def load_history() -> list[dict[str, Any]]:
    if not os.path.isfile(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
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


def get_zone_coords(layout: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Extract zone name → {x, y} mapping from spatial layout."""
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


# ── Charts ───────────────────────────────────────────────────────────────

def build_epidemic_timeline(history: list[dict[str, Any]]) -> go.Figure:
    """Build the S/I/Q epidemic curve chart."""
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
        marker={"size": 6},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=infected, mode="lines+markers",
        name="Infected (I)", line={"color": "#e74c3c", "width": 2},
        marker={"size": 6},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=isolated, mode="lines+markers",
        name="Quarantined (Q)", line={"color": "#f39c12", "width": 2, "dash": "dash"},
        marker={"size": 6},
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=recovered, mode="lines+markers",
        name="Recovered (R)", line={"color": "#2ecc71", "width": 2, "dash": "dot"},
        marker={"size": 6},
    ))

    # Add escalation transition markers
    for record in history:
        epoch = record["epoch"]
        status = record["trigger_status"]
        if epoch > 0:
            prev_status = history[epoch - 1]["trigger_status"]
            if status != prev_status:
                fig.add_vline(
                    x=epoch, line_dash="dash",
                    line_color=STATUS_COLORS.get(status, "gray"),
                    annotation_text=f"→ {status}",
                    annotation_position="top",
                )

    fig.update_layout(
        title="Epidemic Timeline (S / I / Q / R)",
        xaxis_title="Epoch (hours)",
        yaxis_title="Agent Count",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.5, "xanchor": "center"},
        template="plotly_dark",
        height=350,
        margin={"t": 60, "b": 40, "l": 50, "r": 20},
    )

    return fig


def build_deck_map(
    record: dict[str, Any],
    zone_coords: dict[str, dict[str, float]],
    adjacency: list[dict[str, str]],
) -> go.Figure:
    """Build the spatial deck map for a single epoch."""
    fig = go.Figure()

    # Draw adjacency edges
    for link in adjacency:
        from_zone = link.get("from", "")
        to_zone = link.get("to", "")
        if from_zone in zone_coords and to_zone in zone_coords:
            x0, y0 = zone_coords[from_zone]["x"], zone_coords[from_zone]["y"]
            x1, y1 = zone_coords[to_zone]["x"], zone_coords[to_zone]["y"]
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1],
                mode="lines",
                line={"color": "rgba(150,150,150,0.4)", "width": 1.5},
                hoverinfo="skip",
                showlegend=False,
            ))

    # Count agents per zone
    agent_locations: dict[str, int] = {}
    for agent in record.get("agents", []):
        loc = agent.get("location", "unknown")
        agent_locations[loc] = agent_locations.get(loc, 0) + 1

    # Zone pathogen mass
    spaces = record.get("spaces", {})

    zone_names: list[str] = []
    xs: list[float] = []
    ys: list[float] = []
    sizes: list[float] = []
    colors: list[float] = []
    hover_texts: list[str] = []

    max_mass = max(
        (spaces.get(zn, {}).get("pathogen_mass", 0.0) for zn in zone_coords),
        default=1.0,
    )
    if max_mass <= 0:
        max_mass = 1.0

    for zname, zinfo in zone_coords.items():
        zone_names.append(zname)
        xs.append(zinfo["x"])
        ys.append(zinfo["y"])

        occupants = agent_locations.get(zname, 0)
        sizes.append(max(20, 15 + occupants * 8))

        mass = spaces.get(zname, {}).get("pathogen_mass", 0.0)
        colors.append(mass)

        hover_texts.append(
            f"<b>{zname}</b><br>"
            f"Type: {zinfo['type']}<br>"
            f"Deck: {zinfo['deck']}<br>"
            f"Occupants: {occupants}<br>"
            f"Pathogen mass: {mass:.2f}<br>"
            f"Volume: {zinfo['volume_m3']} m³"
        )

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
                [0.0, "#2ecc71"],
                [0.3, "#f1c40f"],
                [0.6, "#e67e22"],
                [1.0, "#e74c3c"],
            ],
            "cmin": 0,
            "cmax": max(max_mass, 0.01),
            "colorbar": {
                "title": "Pathogen<br>Mass",
                "thickness": 15,
                "len": 0.6,
            },
            "line": {"width": 2, "color": "white"},
        },
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        title=f"Spatial Deck Map — Epoch {record['epoch']}",
        template="plotly_dark",
        height=400,
        xaxis={
            "title": "Ship Length (m)",
            "range": [0, 120],
            "showgrid": False,
        },
        yaxis={
            "title": "Beam (m)",
            "range": [0, 15],
            "showgrid": False,
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        margin={"t": 60, "b": 40, "l": 50, "r": 80},
    )

    return fig


# ── Main App ─────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Crusher to the Bridge — Biodefense Dashboard",
        page_icon="🔬",
        layout="wide",
    )

    st.title("Crusher to the Bridge")
    st.caption("Biodefense Digital Twin — Interactive Simulation Dashboard")

    # Load data
    history = load_history()
    layout = load_spatial_layout()
    airflow = load_airflow()
    zone_coords = get_zone_coords(layout)
    adjacency = airflow.get("adjacency", [])

    if not history:
        st.error(
            "No simulation history found. "
            "Run `python orchestrator.py` first to generate "
            "`telemetry_buffer/simulation_history.json`."
        )
        return

    num_epochs = len(history)

    # ── Sidebar: Crusher Surveillance Log ────────────────────────────
    with st.sidebar:
        st.header("Dr. Crusher's Surveillance Log")
        st.divider()

        # Epoch slider (in sidebar for mobile-friendly layout)
        selected_epoch = st.slider(
            "Epoch (Hour)",
            min_value=0,
            max_value=num_epochs - 1,
            value=0,
            key="epoch_slider",
        )

        record = history[selected_epoch]
        status = record["trigger_status"]
        status_color = STATUS_COLORS.get(status, "gray")
        status_icon = STATUS_ICONS.get(status, "?")

        st.divider()

        # Trigger tier
        st.subheader("Trigger Status")
        st.markdown(
            f"<div style='background-color:{status_color}; "
            f"padding:12px; border-radius:8px; text-align:center; "
            f"font-size:20px; font-weight:bold; color:white;'>"
            f"{status_icon} {status}</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # Summary stats
        summary = record["summary"]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Susceptible", summary.get("susceptible", 0))
            st.metric("Infected", summary.get("infected", 0))
        with col2:
            st.metric("Isolated", summary.get("isolated", 0))
            st.metric("Recovered", summary.get("recovered", 0))

        st.divider()

        # Crusher operations
        crusher = record.get("crusher_ops", {})

        st.subheader("Active Operations")

        wipe_zones = crusher.get("surface_wipe_zones", [])
        if wipe_zones:
            st.markdown("**Surface Wipes Deployed:**")
            for zone in wipe_zones:
                pcr_data = crusher.get("pcr_results", {}).get(zone, {})
                ct = pcr_data.get("ct_value")
                detected = pcr_data.get("detected", False)
                ct_str = f"Ct={ct:.1f}" if ct is not None else "Ct=n/a"
                det_icon = "🔴" if detected else "⚪"
                st.markdown(f"  {det_icon} **{zone}** — {ct_str}")
        else:
            st.markdown("*No surface wipes this epoch*")

        rdt_pos = crusher.get("rdt_positive_count", 0)
        rdt_total = crusher.get("rdt_tested_count", 0)
        st.markdown(f"**RDT Results:** {rdt_pos}/{rdt_total} positive")
        st.markdown(f"**Sick-call Count:** {summary.get('sick_call_count', 0)}")

        st.divider()

        # HVAC transport status
        hvac = record.get("hvac", {})
        if hvac.get("transport_active"):
            st.subheader("HVAC Transport")
            filter_type = hvac.get("filter_type", "Unknown")
            filter_eff = hvac.get("filter_efficiency", 0.0)
            st.markdown(
                f"**Filter:** {filter_type} ({filter_eff:.0%} efficiency)"
            )

            st.divider()

        # Isolated agents
        isolated_agents = crusher.get("isolated_agents", [])
        st.subheader(f"Isolated Agents ({len(isolated_agents)})")
        if isolated_agents:
            agent_str = ", ".join(f"#{a}" for a in isolated_agents)
            st.markdown(f"`{agent_str}`")
        else:
            st.markdown("*None isolated*")

    # ── Main content ─────────────────────────────────────────────────

    # Epidemic timeline
    st.plotly_chart(
        build_epidemic_timeline(history),
        use_container_width=True,
    )

    # Epoch slider indicator line on timeline
    st.markdown(
        f"**Selected Epoch: {selected_epoch}** — "
        f"Status: **{record['trigger_status']}** — "
        f"Sick-call: {record['summary'].get('sick_call_count', 0)} — "
        f"Infected: {record['summary'].get('infected', 0)} — "
        f"Isolated: {record['summary'].get('isolated', 0)}"
    )

    # Spatial deck map
    st.plotly_chart(
        build_deck_map(record, zone_coords, adjacency),
        use_container_width=True,
    )

    # Agent location table
    with st.expander(f"Agent Details — Epoch {selected_epoch}", expanded=False):
        agents = record.get("agents", [])
        if agents:
            import pandas as pd
            df = pd.DataFrame(agents)
            df = df.sort_values("agent_id")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "agent_id": st.column_config.NumberColumn("ID", width="small"),
                    "status": st.column_config.TextColumn("Status"),
                    "shedding_rate": st.column_config.NumberColumn(
                        "Shedding Rate", format="%.1f",
                    ),
                    "location": st.column_config.TextColumn("Location"),
                },
            )


if __name__ == "__main__":
    main()
