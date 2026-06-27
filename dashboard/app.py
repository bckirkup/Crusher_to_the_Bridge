"""Main Streamlit LCARS command deck."""
from __future__ import annotations

import json
import os

import streamlit as st

from dashboard.charts import (
    render_bridge_status,
    render_sickbay_console,
    render_standing_orders,
)
from dashboard.fleet_viz import render_fleet_operations
from dashboard.loaders import (
    default_telemetry_dir,
    load_history_from,
    load_notebook_from,
    load_platform_bundle,
    parse_fleet_output_root,
    resolve_platform_id,
    telemetry_paths,
)
from dashboard.paths import (
    DEFAULT_FLEET_OUTPUT,
    PATHOGEN_PATH,
    PROTOCOLS_PATH,
    REPO_ROOT,
)
from dashboard.spatial_viz import render_tactical_grid
from dashboard.theme import (
    LCARS_AMBER,
    LCARS_BG,
    LCARS_CSS,
    LCARS_GOLD,
    LCARS_PEACH,
    _lcars_alert_banner,
    _lcars_banner,
)


@st.cache_data
def _load_pathogen_profiles() -> dict:
    if not os.path.isfile(PATHOGEN_PATH):
        return {}
    with open(PATHOGEN_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def _load_protocols() -> dict:
    if not os.path.isfile(PROTOCOLS_PATH):
        return {}
    with open(PROTOCOLS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _detection_label(method: str) -> str:
    return {
        "exact": "matched simulation zones",
        "subset": "matched simulation zones",
        "fingerprint": "matched telemetry zones",
        "config": "crusher_labs/config.yaml",
        "picard_spec": "Picard run spec",
        "manual": "environment override",
        "default": "catalog default",
    }.get(method, method)


def _locked_platform_id(history: list) -> tuple[str, str]:
    """Single source of truth for vessel class — no UI picker."""
    env_override = os.environ.get("CTTB_PLATFORM_OVERRIDE", "").strip()
    if env_override:
        return env_override, "manual"
    return resolve_platform_id(history)


def main() -> None:
    st.set_page_config(
        page_title="USS Crusher — Main Bridge Display",
        page_icon="🖖",
        layout="wide",
    )
    st.markdown(LCARS_CSS, unsafe_allow_html=True)

    tel_dir = default_telemetry_dir()
    hist_path, nb_path = telemetry_paths(tel_dir)
    history = load_history_from(hist_path)
    notebook = load_notebook_from(nb_path)

    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:8px;'>"
            f"<span style='color:{LCARS_GOLD};font-size:16px;font-weight:bold;"
            f"letter-spacing:2px;'>SHIP STATUS</span></div>",
            unsafe_allow_html=True,
        )

        tel_dir_input = st.text_input(
            "Telemetry directory",
            value=tel_dir,
            key="telemetry_dir",
        )
        if tel_dir_input != tel_dir:
            hist_path, nb_path = telemetry_paths(tel_dir_input)
            history = load_history_from(hist_path)
            notebook = load_notebook_from(nb_path)
            tel_dir = tel_dir_input

        active_pid, detect_method = _locked_platform_id(history)
        bundle = load_platform_bundle(active_pid)
        ship_label = bundle.manifest.get("ship_class_label", active_pid)

        st.markdown(
            _lcars_banner(f"LOCKED VESSEL CLASS<br>{ship_label}", LCARS_GOLD),
            unsafe_allow_html=True,
        )
        st.caption(
            f"**{active_pid}** — {_detection_label(detect_method)}. "
            "Deck plan and tactical map follow this class automatically."
        )

        if bundle.blueprint_bg_path:
            plate_kind = bundle.manifest.get("background_plate", "deck_plate")
            cap = (
                "Class reference photo plate"
                if plate_kind == "reference_photo_composite"
                else "Class blueprint plate"
            )
            st.image(
                bundle.blueprint_bg_path,
                caption=cap,
                use_container_width=True,
            )
        elif bundle.hull_png_path:
            st.image(bundle.hull_png_path, use_container_width=True)

        if history:
            last = history[-1]
            st.markdown(_lcars_alert_banner(last["trigger_status"]), unsafe_allow_html=True)
            st.divider()
            summary = last["summary"]
            st.metric("Epochs Elapsed", len(history))
            total_pop = (
                summary.get("susceptible", 0)
                + summary.get("infected", 0)
                + summary.get("recovered", 0)
                + summary.get("immune", 0)
                + summary.get("isolated", 0)
            )
            st.metric("Crew Complement", total_pop)
            st.metric("Confined to Quarters", summary.get("quarantined", 0))
            st.metric("Isolation Ward", summary.get("isolated", 0))
            ca = last.get("cost_accounting", {})
            st.metric(
                "Credits Remaining",
                f"${ca.get('financial_balance_remaining', 0):,.0f}",
            )
            if ca.get("operational_impact_cumulative") is not None:
                st.metric(
                    "Operational Impact",
                    f"{ca.get('operational_impact_cumulative', 0):,.1f}",
                )

    if not history:
        st.error(
            "No sensor telemetry found. Run `python orchestrator.py` "
            "or point Telemetry directory at a Presidio cruise folder."
        )
        return

    ship_label = bundle.manifest.get("ship_class_label", bundle.platform_id)
    desc = (bundle.layout.get("description") or "")[:120]

    st.markdown(
        f"<div style='background:linear-gradient(90deg,{LCARS_GOLD},{LCARS_AMBER});"
        f"padding:12px 20px;border-radius:20px 20px 0 0;margin-bottom:4px;'>"
        f"<span style='color:{LCARS_BG};font-size:28px;font-weight:bold;"
        f"letter-spacing:2px;'>CRUSHER TO THE BRIDGE</span>"
        f"<span style='color:{LCARS_BG};font-size:14px;float:right;margin-top:8px;'>"
        f"{ship_label}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='color:{LCARS_PEACH};font-size:13px;'>"
        f"Locked deck plan: **{bundle.platform_id}** — {desc}</span>",
        unsafe_allow_html=True,
    )

    pathogen_data = _load_pathogen_profiles()
    protocol_data = _load_protocols()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Bridge Status Display",
        "Tactical Sensor Grid",
        "Sickbay Diagnostic Console",
        "Standing Orders & Threat Profiles",
        "Fleet Operations",
    ])

    with tab1:
        render_bridge_status(history, notebook)
    with tab2:
        render_tactical_grid(history, bundle)
    with tab3:
        render_sickbay_console(history, notebook)
    with tab4:
        render_standing_orders(pathogen_data, protocol_data)
    with tab5:
        fleet_cfg = os.path.join(
            REPO_ROOT, "presidio", "data", "config", "smoke_fleet.json",
        )
        fleet_root = parse_fleet_output_root(fleet_cfg) or DEFAULT_FLEET_OUTPUT
        render_fleet_operations(fleet_root)


if __name__ == "__main__":
    main()
