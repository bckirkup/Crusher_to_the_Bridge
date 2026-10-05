"""Operations console — configure and launch ship or fleet runs."""
from __future__ import annotations

import glob
import json
import os
from typing import Any

import streamlit as st

from dashboard.loaders import list_platform_ids
from dashboard.paths import REPO_ROOT
from simulation_utils.paths import (
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)


def _list_ship_presets() -> list[str]:
    pattern = os.path.join(REPO_ROOT, "picard_framework", "runs", "smoke*.json")
    return sorted(glob.glob(pattern))


def _list_fleet_presets() -> list[str]:
    cfg_dir = os.path.join(REPO_ROOT, "presidio", "data", "config")
    paths = glob.glob(os.path.join(cfg_dir, "*fleet*.json"))
    return sorted(paths)


def _load_json(path: str) -> dict[str, Any]:
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _preset_bundle_id(preset_path: str | None) -> str:
    """Pathogen bundle id the selected preset resolves (default bundle)."""
    path = preset_path
    if not path or not os.path.isfile(path):
        path = os.path.join(REPO_ROOT, "picard_framework", "runs", "smoke_2epoch.json")
    try:
        spec = _load_json(path)
    except Exception:
        return "active_profiles"
    return str((spec.get("catalog") or {}).get("pathogen_bundle_id") or "active_profiles")


def _pathogen_mechanism_rows(bundle_id: str) -> list[tuple[str, str, bool]]:
    """(pathogen_id, block, enabled) for per-pathogen mechanism blocks."""
    bundle_path = os.path.join(REPO_ROOT, "data", "pathogens", f"{bundle_id}.json")
    if not os.path.isfile(bundle_path):
        return []
    try:
        data = _load_json(bundle_path)
    except Exception:
        return []
    rows: list[tuple[str, str, bool]] = []
    for profile in data.get("pathogens", []):
        pid = profile.get("pathogen_id")
        if not pid:
            continue
        for block in ("food_contamination", "common_source_events"):
            block_data = profile.get(block)
            if isinstance(block_data, dict):
                rows.append((str(pid), block, bool(block_data.get("enabled"))))
    return rows


def _mechanism_override_form(
    preset_path: str | None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Mechanism toggles → (config_overrides, pathogen_overrides, retention)."""
    cfg: dict[str, Any] = {}
    path_over: dict[str, Any] = {}
    with st.expander("Mechanism overrides", expanded=False):
        st.caption(
            "'default' leaves the preset/config.yaml value untouched; "
            "anything else is pinned as a config override for this run."
        )
        mc1, mc2, mc3 = st.columns(3)
        rhythm = mc1.selectbox(
            "Ship rhythm (watches, dining)",
            ["default", "on", "off"], key="ship_mech_rhythm",
        )
        sanitary = mc1.selectbox(
            "Sanitary visit mode",
            ["default", "none", "dwell_weighted"], key="ship_mech_sanitary",
        )
        cabin_air = mc1.selectbox(
            "Cabin air",
            ["default", "cabin_compartment", "zone_pool"],
            key="ship_mech_cabin_air",
        )
        common_src = mc2.selectbox(
            "Common-source meals",
            ["default", "on", "off"], key="ship_mech_common_source",
        )
        droplet = mc2.selectbox(
            "Droplet field split",
            ["default", "partition", "off"], key="ship_mech_droplet",
        )
        near_field = mc2.selectbox(
            "Near-field air",
            ["default", "two_box", "off"], key="ship_mech_nearfield",
        )
        hand = mc3.selectbox(
            "Hand reservoir",
            ["default", "hygiene_cycle", "wash_reuptake", "spike_decay"],
            key="ship_mech_hand",
        )
        info = mc3.selectbox(
            "Info suppression",
            ["default", "on", "off"], key="ship_mech_info_suppression",
        )
        retention = mc3.selectbox(
            "History retention",
            ["full", "compact"], key="ship_mech_retention",
        )

        tx = cfg.setdefault("transmission", {})
        if rhythm != "default":
            cfg.setdefault("rhythm", {})["enabled"] = rhythm == "on"
        if sanitary != "default":
            tx["sanitary_visit_mode"] = sanitary
        if cabin_air != "default":
            tx["cabin_air_mode"] = cabin_air
        if common_src != "default":
            tx.setdefault("common_source", {})["mode"] = common_src
        if droplet != "default":
            tx.setdefault("droplet_field_split", {})["mode"] = droplet
        if near_field != "default":
            tx.setdefault("near_field_air", {})["mode"] = near_field
        if hand != "default":
            tx["hand_reservoir_mode"] = hand
        if info != "default":
            cfg.setdefault("info_suppression", {})["enabled"] = info == "on"
        if not tx:
            cfg.pop("transmission", None)

        rows = _pathogen_mechanism_rows(_preset_bundle_id(preset_path))
        if rows:
            st.markdown("**Pathogen mechanisms**")
            for pid, block, enabled in rows:
                label = block.replace("_", " ")
                val = st.checkbox(
                    f"{label} — {pid}",
                    value=enabled,
                    key=f"ship_pathogen_{block}_{pid}",
                )
                if val != enabled:
                    path_over.setdefault(pid, {})[block] = {"enabled": val}
    return cfg, path_over, retention


def _build_ship_spec(
    *,
    platform_id: str,
    num_epochs: int,
    seed: int,
    cascade: bool,
    voyage_effects: bool,
    preset_path: str | None,
    config_overrides: dict[str, Any] | None = None,
    pathogen_overrides: dict[str, Any] | None = None,
    history_retention: str = "full",
) -> dict[str, Any]:
    from picard_framework.pathogen_overrides import deep_merge_dict

    if preset_path and os.path.isfile(preset_path):
        spec = _load_json(preset_path)
    else:
        default = os.path.join(REPO_ROOT, "picard_framework", "runs", "smoke_2epoch.json")
        spec = _load_json(default)

    spec.setdefault("catalog", {})["platform_id"] = platform_id
    spec.setdefault("run", {})["num_epochs"] = num_epochs
    spec.setdefault("run", {})["random_seed"] = seed
    spec.setdefault("run", {})["history_retention"] = history_retention

    overrides = spec.setdefault("config_overrides", {})
    if config_overrides:
        spec["config_overrides"] = deep_merge_dict(overrides, config_overrides)
        overrides = spec["config_overrides"]
    if cascade:
        overrides.setdefault("diagnostic_cascade", {})["enabled"] = True
    if voyage_effects:
        overrides.setdefault("voyage", {})["effects_enabled"] = True
    if pathogen_overrides:
        spec["pathogen_overrides"] = deep_merge_dict(
            spec.get("pathogen_overrides") or {}, pathogen_overrides,
        )
    return spec


def _safe_telemetry_dir(telemetry_dir: str) -> str:
    """Resolve UI telemetry path under the repo root; fall back to telemetry_buffer."""
    try:
        return resolve_repo_path(REPO_ROOT, telemetry_dir)
    except ValueError:
        return resolve_repo_path(REPO_ROOT, "telemetry_buffer")


def _launch_ship(spec_dict: dict[str, Any], telemetry_dir: str) -> str:
    from picard_framework import PicardRunSpec, ShipSimulation

    abs_dir = _safe_telemetry_dir(telemetry_dir)
    prepare_output_directory(abs_dir, allowed_roots=(REPO_ROOT,))
    rel_dir = os.path.relpath(abs_dir, REPO_ROOT).replace("\\", "/")

    run_block = spec_dict.setdefault("run", {})
    run_block["simulation_history"] = f"{rel_dir}/simulation_history.json"
    run_block["lab_notebook"] = f"{rel_dir}/artificial_lab_notebook.json"
    run_block["ground_truth"] = f"{rel_dir}/ground_truth.json"
    run_block.setdefault("history_retention", "full")

    spec = PicardRunSpec.from_picard_dict(REPO_ROOT, spec_dict)
    sim = ShipSimulation(spec, display=False)
    sim.run()
    sim.finalize(display=False)
    out = spec.telemetry.simulation_history if spec.telemetry else run_block["simulation_history"]
    return out if os.path.isabs(out) else os.path.join(REPO_ROOT, out)


def _launch_fleet(fleet_config: str, num_cruises: int) -> str:
    from presidio.run_spec import PresidioRunSpec
    from presidio_runner import run

    safe_config = resolve_repo_path(REPO_ROOT, fleet_config)
    fleet_spec = PresidioRunSpec.from_fleet_json(REPO_ROOT, safe_config)
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
    cfg_overrides, pathogen_overrides, retention = _mechanism_override_form(preset_path)
    telemetry_dir = st.text_input(
        "Output telemetry directory (under repo root)",
        value=os.path.join(REPO_ROOT, "telemetry_buffer"),
        key="ship_telemetry_dir",
    )

    confirm = False
    if num_epochs > 24:
        confirm = st.checkbox("Confirm long run (>24 epochs)", value=False, key="ship_confirm_long")

    if st.button("Launch ship run", type="primary", key="launch_ship"):
        if num_epochs > 24 and not confirm:
            st.error("Confirm long run before launching.")
            return
        if not _path_under_repo(telemetry_dir):
            st.warning("Path outside repo — using telemetry_buffer/.")
        safe_dir = _safe_telemetry_dir(telemetry_dir)
        spec = _build_ship_spec(
            platform_id=platform_id,
            num_epochs=int(num_epochs),
            seed=int(seed),
            cascade=cascade,
            voyage_effects=voyage,
            preset_path=preset_path,
            config_overrides=cfg_overrides,
            pathogen_overrides=pathogen_overrides,
            history_retention=retention,
        )
        with st.spinner(f"Running {num_epochs}-epoch simulation…"):
            try:
                hist_path = _launch_ship(spec, safe_dir)
            except Exception as exc:
                st.error(f"Run failed: {exc}")
                return
        st.success(f"Run complete. History: {hist_path}")
        st.session_state.telemetry_dir = safe_dir
        st.session_state.active_history_source = "ship"
        st.cache_data.clear()
        st.rerun()


def _path_under_repo(path: str) -> bool:
    try:
        resolve_repo_path(REPO_ROOT, path)
        return True
    except ValueError:
        return False


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
