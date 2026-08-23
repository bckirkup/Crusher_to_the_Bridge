"""Operations console — configure and launch ship or fleet runs."""
from __future__ import annotations

import glob
import json
import os
from typing import Any

import streamlit as st

from dashboard.loaders import list_platform_ids
from dashboard.paths import REPO_ROOT


def _list_ship_presets() -> list[str]:
    pattern = os.path.join(REPO_ROOT, "picard_framework", "runs", "smoke*.json")
    return sorted(glob.glob(pattern))


def _list_fleet_presets() -> list[str]:
    cfg_dir = os.path.join(REPO_ROOT, "presidio", "data", "config")
    paths = glob.glob(os.path.join(cfg_dir, "*fleet*.json"))
    return sorted(paths)


def _load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _build_ship_spec(
    *,
    platform_id: str,
    num_epochs: int,
    seed: int,
    cascade: bool,
    voyage_effects: bool,
    preset_path: str | None,
) -> dict[str, Any]:
    if preset_path and os.path.isfile(preset_path):
        spec = _load_json(preset_path)
    else:
        spec = _load_json(os.path.join(REPO_ROOT, "picard_framework", "runs", "smoke_2epoch.json"))

    spec.setdefault("catalog", {})["platform_id"] = platform_id
    spec.setdefault("run", {})["num_epochs"] = num_epochs
    spec.setdefault("run", {})["random_seed"] = seed
    spec.setdefault("run", {})["history_retention"] = "full"

    overrides = spec.setdefault("config_overrides", {})
    if cascade:
        overrides.setdefault("diagnostic_cascade", {})["enabled"] = True
    if voyage_effects:
        overrides.setdefault("voyage", {})["effects_enabled"] = True
    return spec


def _repo_relative_dir(path: str) -> str:
    """Return a repo-relative directory for Picard telemetry paths."""
    abs_path = os.path.abspath(path)
    repo = os.path.abspath(REPO_ROOT)
    if abs_path.startswith(repo + os.sep) or abs_path == repo:
        rel = os.path.relpath(abs_path, repo)
        return rel.replace("\\", "/")
    return "telemetry_buffer"


def _launch_ship(spec_dict: dict[str, Any], telemetry_dir: str) -> str:
    from picard_framework import PicardRunSpec, ShipSimulation

    rel_dir = _repo_relative_dir(telemetry_dir)
    os.makedirs(os.path.join(REPO_ROOT, rel_dir), exist_ok=True)
    run_block = spec_dict.setdefault("run", {})
    run_block["simulation_history"] = f"{rel_dir}/simulation_history.json"
    run_block["lab_notebook"] = f"{rel_dir}/artificial_lab_notebook.json"
    run_block["ground_truth"] = f"{rel_dir}/ground_truth.json"
    run_block["history_retention"] = "full"

    spec = PicardRunSpec.from_picard_dict(REPO_ROOT, spec_dict)
    sim = ShipSimulation(spec, display=False)
    sim.run()
    sim.finalize(display=False)
    out = spec.telemetry.simulation_history if spec.telemetry else run_block["simulation_history"]
    return os.path.join(REPO_ROOT, out) if not os.path.isabs(out) else out


def _launch_fleet(fleet_config: str, num_cruises: int) -> str:
    from presidio.run_spec import PresidioRunSpec
    from presidio_runner import run

    fleet_spec = PresidioRunSpec.from_fleet_json(REPO_ROOT, fleet_config)
    fleet_spec.num_cruises = num_cruises
    run(fleet_spec, display=False)
    return fleet_spec.output_root


def render_run_console() -> None:
    st.subheader("Operations Console")
    st.caption(
        "Configure and launch a ship voyage or Presidio fleet run. "
        "Long runs block this page until complete — prefer smoke presets for testing."
    )

    mode = st.radio("Run mode", ["Single ship", "Fleet"], horizontal=True, key="run_console_mode")

    if mode == "Single ship":
        _render_ship_console()
    else:
        _render_fleet_console()


def _render_ship_console() -> None:
    presets = _list_ship_presets()
    preset_labels = [os.path.basename(p) for p in presets]
    preset_pick = st.selectbox(
        "Preset template",
        preset_labels,
        key="ship_preset",
    )
    preset_path = presets[preset_labels.index(preset_pick)] if preset_labels else None

    platforms = list_platform_ids()
    platform_id = st.selectbox("Platform", platforms or ["mega_cruise_5000"], key="ship_platform")
    num_epochs = st.number_input("Epochs", min_value=1, max_value=365, value=2, key="ship_epochs")
    seed = st.number_input("Random seed", min_value=0, value=42, key="ship_seed")
    cascade = st.checkbox("Enable diagnostic cascade", value=False, key="ship_cascade")
    voyage = st.checkbox("Enable voyage port effects", value=False, key="ship_voyage")
    telemetry_dir = st.text_input(
        "Output telemetry directory (under repo root)",
        value=os.path.join(REPO_ROOT, "telemetry_buffer"),
        key="ship_telemetry_dir",
    )
    if not os.path.abspath(telemetry_dir).startswith(os.path.abspath(REPO_ROOT)):
        st.warning("Telemetry directory must be inside the repository. Runs will use telemetry_buffer/.")

    confirm = False
    if num_epochs > 24:
        confirm = st.checkbox("Confirm long run (>24 epochs)", value=False, key="ship_confirm_long")

    if st.button("Launch ship run", type="primary", key="launch_ship"):
        if num_epochs > 24 and not confirm:
            st.error("Confirm long run before launching.")
            return
        os.makedirs(telemetry_dir, exist_ok=True)
        spec = _build_ship_spec(
            platform_id=platform_id,
            num_epochs=int(num_epochs),
            seed=int(seed),
            cascade=cascade,
            voyage_effects=voyage,
            preset_path=preset_path,
        )
        with st.spinner(f"Running {num_epochs}-epoch simulation…"):
            try:
                hist_path = _launch_ship(spec, telemetry_dir)
            except Exception as exc:
                st.error(f"Run failed: {exc}")
                return
        st.success(f"Run complete. History: {hist_path}")
        st.session_state.telemetry_dir = telemetry_dir
        st.session_state.active_history_source = "ship"
        st.cache_data.clear()
        st.rerun()


def _render_fleet_console() -> None:
    presets = _list_fleet_presets()
    preset_labels = [os.path.basename(p) for p in presets]
    preset_pick = st.selectbox("Fleet config", preset_labels, key="fleet_preset")
    preset_path = presets[preset_labels.index(preset_pick)] if preset_labels else ""

    num_cruises = st.number_input("Cruises", min_value=1, max_value=20, value=1, key="fleet_cruises")
    confirm = False
    if num_cruises > 1:
        confirm = st.checkbox("Confirm multi-cruise fleet run", value=False, key="fleet_confirm")

    if st.button("Launch fleet run", type="primary", key="launch_fleet"):
        if num_cruises > 1 and not confirm:
            st.error("Confirm multi-cruise run before launching.")
            return
        with st.spinner(f"Running {num_cruises} cruise(s)…"):
            try:
                output_root = _launch_fleet(preset_path, int(num_cruises))
            except Exception as exc:
                st.error(f"Fleet run failed: {exc}")
                return
        st.success(f"Fleet run complete. Output: {output_root}")
        st.session_state.fleet_root = output_root
        st.session_state.telemetry_dir = os.path.join(output_root, "cruise_000")
        st.session_state.active_history_source = "fleet"
        st.cache_data.clear()
        st.rerun()
