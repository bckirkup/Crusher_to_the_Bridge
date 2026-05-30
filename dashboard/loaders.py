"""Telemetry and platform bundle loaders with ship-class resolution."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import streamlit as st
import yaml

from dashboard.paths import (
    CONFIG_YAML,
    DEFAULT_PICARD_SPEC,
    NOTEBOOK_PATH,
    PLATFORMS_DIR,
    REPO_ROOT,
)


@dataclass
class PlatformBundle:
    platform_id: str
    layout: dict[str, Any]
    airflow: dict[str, Any]
    manifest: dict[str, Any]
    deck_graphics: dict[str, Any]
    hull_png_path: str | None
    blueprint_bg_path: str | None
    zone_coords: dict[str, dict[str, Any]]


def list_platform_ids() -> list[str]:
    if not os.path.isdir(PLATFORMS_DIR):
        return []
    ids = []
    for name in sorted(os.listdir(PLATFORMS_DIR)):
        pdir = os.path.join(PLATFORMS_DIR, name)
        if os.path.isfile(os.path.join(pdir, "spatial_layout.json")):
            ids.append(name)
    return ids


def _load_json(path: str) -> dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def platform_dir(platform_id: str) -> str:
    return os.path.join(PLATFORMS_DIR, platform_id)


def get_zone_coords(layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    coords: dict[str, dict[str, Any]] = {}
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


def _platform_from_config() -> str | None:
    if not os.path.isfile(CONFIG_YAML):
        return None
    with open(CONFIG_YAML, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    layout_rel = (cfg.get("ship_graph") or {}).get("spatial_layout", "")
    if not layout_rel:
        return None
    parts = layout_rel.replace("\\", "/").split("/")
    if "platforms" in parts:
        idx = parts.index("platforms")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def _platform_from_picard_spec(spec_path: str) -> str | None:
    if not os.path.isfile(spec_path):
        return None
    data = _load_json(spec_path)
    pid = (data.get("catalog") or {}).get("platform_id")
    return str(pid) if pid else None


def _zone_ids_for_platform(pid: str) -> set[str]:
    mpath = os.path.join(platform_dir(pid), "deck_manifest.json")
    manifest = _load_json(mpath)
    zone_ids = set(manifest.get("zone_ids") or [])
    if not zone_ids:
        layout = _load_json(os.path.join(platform_dir(pid), "spatial_layout.json"))
        zone_ids = {z["id"] for z in layout.get("zones", [])}
    return zone_ids


def fingerprint_platform(space_keys: set[str]) -> tuple[str | None, str]:
    """Return (platform_id, method) — exact zone match preferred over Jaccard."""
    if not space_keys:
        return None, "none"

    best_id: str | None = None
    best_jaccard = -1.0

    for pid in list_platform_ids():
        zone_ids = _zone_ids_for_platform(pid)
        if not zone_ids:
            continue
        if space_keys == zone_ids:
            return pid, "exact"
        if space_keys <= zone_ids and len(space_keys) >= max(3, len(zone_ids) // 2):
            return pid, "subset"
        union = len(space_keys | zone_ids)
        if union == 0:
            continue
        jaccard = len(space_keys & zone_ids) / union
        if jaccard > best_jaccard:
            best_jaccard = jaccard
            best_id = pid

    if best_id and best_jaccard >= 0.45:
        return best_id, "fingerprint"
    return None, "none"


def resolve_platform_id(
    history: list[dict[str, Any]],
    override: str | None = None,
    picard_spec_path: str | None = None,
) -> tuple[str, str]:
    """Return (platform_id, detection_method)."""
    if override:
        return override, "manual"
    if history:
        spaces = history[-1].get("spaces", {})
        pid, method = fingerprint_platform(set(spaces.keys()))
        if pid:
            return pid, method
    cfg_pid = _platform_from_config()
    if cfg_pid:
        return cfg_pid, "config"
    spec = picard_spec_path or os.environ.get("CTTB_PICARD_SPEC", DEFAULT_PICARD_SPEC)
    pic_pid = _platform_from_picard_spec(spec)
    if pic_pid:
        return pic_pid, "picard_spec"
    return "destroyer_baseline", "default"


def resolve_platform_id_simple(
    history: list[dict[str, Any]],
    override: str | None = None,
    picard_spec_path: str | None = None,
) -> str:
    pid, _ = resolve_platform_id(history, override, picard_spec_path)
    return pid


def load_platform_bundle(platform_id: str) -> PlatformBundle:
    pdir = platform_dir(platform_id)
    layout = _load_json(os.path.join(pdir, "spatial_layout.json"))
    airflow = _load_json(os.path.join(pdir, "air_flow_paths.json"))
    manifest = _load_json(os.path.join(pdir, "deck_manifest.json"))
    if not manifest:
        manifest = {
            "platform_id": platform_id,
            "ship_class_label": platform_id.replace("_", " ").title(),
            "footprint_tier": "unknown",
            "zone_ids": [z["id"] for z in layout.get("zones", [])],
            "view_bounds": layout.get("deck_dimensions", {}),
        }
    gfx = _load_json(os.path.join(pdir, "deck_graphics.geojson"))
    hull_path = os.path.join(pdir, "deck_hull.png")
    bg_path = os.path.join(pdir, "deck_blueprint_bg.png")
    return PlatformBundle(
        platform_id=platform_id,
        layout=layout,
        airflow=airflow,
        manifest=manifest,
        deck_graphics=gfx,
        hull_png_path=hull_path if os.path.isfile(hull_path) else None,
        blueprint_bg_path=bg_path if os.path.isfile(bg_path) else None,
        zone_coords=get_zone_coords(layout),
    )


def telemetry_paths(telemetry_dir: str) -> tuple[str, str]:
    return (
        os.path.join(telemetry_dir, "simulation_history.json"),
        os.path.join(telemetry_dir, "artificial_lab_notebook.json"),
    )


@st.cache_data
def load_history_from(path: str) -> list[dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_notebook_from(path: str) -> dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def default_telemetry_dir() -> str:
    env = os.environ.get("CTTB_TELEMETRY_DIR")
    if env:
        return env
    return os.path.join(REPO_ROOT, "telemetry_buffer")


def parse_fleet_output_root(fleet_config_path: str) -> str:
    if not os.path.isfile(fleet_config_path):
        return ""
    with open(fleet_config_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return (raw.get("run") or {}).get("output_root", "")


def list_cruise_dirs(fleet_root: str) -> list[str]:
    if not os.path.isdir(fleet_root):
        return []
    cruises = []
    for name in sorted(os.listdir(fleet_root)):
        if re.match(r"cruise_\d+", name):
            cruises.append(os.path.join(fleet_root, name))
    return cruises
