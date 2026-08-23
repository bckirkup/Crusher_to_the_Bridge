"""Shared Streamlit session state for dashboard views."""
from __future__ import annotations

import streamlit as st

SESSION_DEFAULTS: dict[str, object] = {
    "selected_epoch": 0,
    "playback_active": False,
    "playback_speed": 1.0,
    "selected_agent_id": None,
    "selected_zone_id": None,
    "selected_cruise_dir": None,
    "telemetry_dir": "",
    "fleet_root": "",
    "last_playback_tick": 0.0,
    "active_history_source": "ship",
}


def init_session_state(*, history_len: int = 0) -> None:
    """Ensure session keys exist and clamp epoch to valid range."""
    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default

    max_epoch = max(0, history_len - 1)
    current = int(st.session_state.get("selected_epoch", 0))
    if current > max_epoch:
        st.session_state.selected_epoch = max_epoch


def get_selected_epoch() -> int:
    return int(st.session_state.get("selected_epoch", 0))


def set_selected_epoch(epoch: int, history_len: int) -> None:
    max_epoch = max(0, history_len - 1)
    st.session_state.selected_epoch = max(0, min(int(epoch), max_epoch))


def set_selected_agent(agent_id: int | None) -> None:
    st.session_state.selected_agent_id = agent_id


def set_selected_zone(zone_id: str | None) -> None:
    st.session_state.selected_zone_id = zone_id


def get_selected_agent_id() -> int | None:
    val = st.session_state.get("selected_agent_id")
    return int(val) if val is not None else None


def get_selected_zone_id() -> str | None:
    val = st.session_state.get("selected_zone_id")
    return str(val) if val else None
