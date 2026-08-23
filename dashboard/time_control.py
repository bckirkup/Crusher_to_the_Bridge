"""Global simulation clock — epoch scrubber and playback."""
from __future__ import annotations

import time
from typing import Any

import streamlit as st

from dashboard.session_state import (
    apply_slider_epoch,
    get_selected_epoch,
    set_selected_epoch,
    sync_epoch_slider_key,
)
from dashboard.units import time_xaxis_title

PLAYBACK_INTERVAL_SEC = 0.5


def _advance_playback(num_epochs: int) -> None:
    """Step epoch forward when playback is active; rerun when interval elapsed."""
    if not st.session_state.get("playback_active") or num_epochs <= 1:
        return
    now = time.time()
    last = float(st.session_state.get("last_playback_tick", 0.0))
    speed = max(0.25, float(st.session_state.get("playback_speed", 1.0)))
    interval = PLAYBACK_INTERVAL_SEC / speed
    if now - last < interval:
        return
    st.session_state.last_playback_tick = now
    current = get_selected_epoch()
    if current >= num_epochs - 1:
        st.session_state.playback_active = False
        return
    set_selected_epoch(current + 1, num_epochs)
    st.rerun()


def render_time_control(history: list[dict[str, Any]], *, key_suffix: str = "") -> int:
    """Sidebar time bar: slider, step buttons, playback. Returns selected epoch."""
    num_epochs = len(history)
    if num_epochs == 0:
        return 0

    _advance_playback(num_epochs)

    st.markdown("**Simulation clock**")
    x_label = time_xaxis_title(history)
    rec = history[get_selected_epoch()]
    voyage = rec.get("voyage_epoch", {})
    caption_bits = [f"Epoch {rec['epoch']}"]
    if voyage.get("voyage_day") is not None:
        caption_bits.append(f"Day {voyage['voyage_day']}")
    if voyage.get("port"):
        caption_bits.append(str(voyage["port"]))
    st.caption(" · ".join(caption_bits))

    slider_key = f"global_epoch_slider{key_suffix}"
    sync_epoch_slider_key(slider_key)
    epoch = st.slider(
        x_label,
        0,
        num_epochs - 1,
        key=slider_key,
    )
    apply_slider_epoch(epoch, num_epochs)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("◀", key=f"time_step_back{key_suffix}", help="Previous epoch"):
            set_selected_epoch(get_selected_epoch() - 1, num_epochs)
            st.rerun()
    with c2:
        playing = st.session_state.get("playback_active", False)
        label = "⏸" if playing else "▶"
        if st.button(label, key=f"time_play_pause{key_suffix}", help="Play / Pause"):
            st.session_state.playback_active = not playing
            st.session_state.last_playback_tick = time.time()
            st.rerun()
    with c3:
        if st.button("▶", key=f"time_step_fwd{key_suffix}", help="Next epoch"):
            set_selected_epoch(get_selected_epoch() + 1, num_epochs)
            st.rerun()
    with c4:
        speed = st.selectbox(
            "Speed",
            [0.5, 1.0, 2.0, 4.0],
            index=1,
            key=f"playback_speed_sel{key_suffix}",
            label_visibility="collapsed",
        )
        st.session_state.playback_speed = speed

    return get_selected_epoch()
