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
    "_epoch_slider_needs_sync": False,
}


def init_session_state(*, history_len: int = 0) -> None:
    """Ensure session keys exist and clamp epoch to valid range."""
    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default

    max_epoch = max(0, history_len - 1)
    current = int(st.session_state.get("selected_epoch", 0))
    if current > max_epoch:
        set_selected_epoch(max_epoch, history_len)


def get_selected_epoch() -> int:
    return int(st.session_state.get("selected_epoch", 0))


def set_selected_epoch(epoch: int, history_len: int) -> None:
    """Set the shared clock; mark epoch sliders to resync on the next render."""
    max_epoch = max(0, history_len - 1)
    clamped = max(0, min(int(epoch), max_epoch))
    st.session_state.selected_epoch = clamped
    # Streamlit ignores slider ``value=`` once the widget key exists, and forbids
    # mutating that key after the widget is instantiated in the same run. Flag a
    # sync so render_time_control can write the key *before* creating the slider.
    st.session_state._epoch_slider_needs_sync = True


def sync_epoch_slider_key(slider_key: str) -> None:
    """Apply pending programmatic epoch updates to a slider widget key."""
    desired = get_selected_epoch()
    needs_sync = bool(st.session_state.pop("_epoch_slider_needs_sync", False))
    if needs_sync or slider_key not in st.session_state:
        st.session_state[slider_key] = desired


def apply_slider_epoch(epoch: int, history_len: int) -> None:
    """Record a user slider change without requesting a slider resync."""
    max_epoch = max(0, history_len - 1)
    st.session_state.selected_epoch = max(0, min(int(epoch), max_epoch))
    st.session_state._epoch_slider_needs_sync = False


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
