"""
contam_hobbyist.py – Shared ContamW 3.4 hobbyist-plus fiction pack helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Loads ``data/contam_hobbyist/`` templates and optional per-platform
``contam/hobbyist_overrides.json`` for the fiction JSON→PRJ bootstrap.
"""

from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PACK_DIR = os.path.join(REPO_ROOT, "data", "contam_hobbyist")
OVERRIDES_NAME = "hobbyist_overrides.json"

_PACK_FILES = (
    "orifice_catalog.json",
    "wind_profiles.json",
    "schedule_templates.json",
    "filter_presets.json",
    "duct_defaults.json",
    "species_pack.json",
)


def _read_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


@lru_cache(maxsize=4)
def load_hobbyist_pack(pack_dir: str | None = None) -> dict[str, Any]:
    """Load the shared hobbyist pack (cached)."""
    root = pack_dir or DEFAULT_PACK_DIR
    pack: dict[str, Any] = {"_pack_dir": root}
    for name in _PACK_FILES:
        key = name.replace(".json", "")
        pack[key] = _read_json(os.path.join(root, name))
    return pack


def load_hobbyist_overrides(platform_dir: str) -> dict[str, Any]:
    """Load optional ``contam/hobbyist_overrides.json`` for a platform."""
    path = os.path.join(platform_dir, "contam", OVERRIDES_NAME)
    if not os.path.isfile(path):
        return {}
    return _read_json(path)


def orifice_params_for_area(area_m2: float) -> str:
    """Contam ``plr_orfc`` params scaled from the canonical Opening template."""
    area = max(float(area_m2), 1e-12)
    ref = 0.01
    scale = area / ref
    lam = 2.70811e-05 * scale
    turb = 0.00848528 * scale
    dia = math.sqrt(4.0 * area / math.pi)
    return f"{lam:.8g} {turb:.8g} 0.5 {area:.8g} {dia:.8g} 0.6 30 0 0"


def resolve_orifice_type(
    adj_type: str,
    pack: dict[str, Any],
    overrides: dict[str, Any],
) -> str:
    """Map adjacency ``type`` → orifice catalog key."""
    type_map = dict(overrides.get("orifice_type_map") or {})
    key = type_map.get(adj_type, adj_type)
    catalog = pack["orifice_catalog"]["types"]
    if key in catalog:
        return key
    default = pack["orifice_catalog"].get("default_type", "passageway")
    return default if default in catalog else next(iter(catalog))


def resolve_filter_preset(
    pack: dict[str, Any],
    overrides: dict[str, Any],
    *,
    hvac_id: str | None = None,
    filter_efficiency: float | None = None,
) -> str:
    """Pick a named filter preset for an AHS / platform."""
    presets = pack["filter_presets"]["presets"]
    hvac_map = dict(overrides.get("hvac_filter") or {})
    if hvac_id and hvac_id in hvac_map:
        name = str(hvac_map[hvac_id])
        if name in presets:
            return name
    if overrides.get("filter_preset") in presets:
        return str(overrides["filter_preset"])
    if filter_efficiency is not None:
        for row in pack["filter_presets"].get("efficiency_to_preset", []):
            if float(filter_efficiency) <= float(row["max_efficiency"]):
                return str(row["preset"])
    default = pack["filter_presets"].get("default_preset", "MERV13")
    return default if default in presets else next(iter(presets))


def resolve_wind_profile_key(
    pack: dict[str, Any],
    overrides: dict[str, Any],
) -> str:
    profiles = pack["wind_profiles"]["profiles"]
    key = overrides.get("wind_profile") or pack["wind_profiles"].get(
        "default_profile", "ship_hull",
    )
    if key in profiles:
        return str(key)
    return next(iter(profiles))


def deck_temp_k(
    deck: str,
    overrides: dict[str, Any],
    base_k: float = 293.15,
) -> float:
    offsets = dict(overrides.get("deck_temp_offset_K") or {})
    return float(base_k) + float(offsets.get(deck, 0.0))


def wall_azimuth_deg(
    zone_id: str,
    zone: dict[str, Any],
    overrides: dict[str, Any],
    *,
    beam_m: float = 15.0,
) -> float:
    """Invent a plausible hull-wall azimuth from overrides or display coords."""
    explicit = dict(overrides.get("wall_azimuth_deg") or {})
    if zone_id in explicit:
        return float(explicit[zone_id])
    display = zone.get("display") or {}
    x = float(display.get("x", 0) or 0)
    y = float(display.get("y", 0) or 0)
    if x >= 80:
        return 0.0
    if x <= 30:
        return 180.0
    if y >= beam_m * 0.55:
        return 90.0
    if y <= beam_m * 0.35:
        return 270.0
    return 90.0


def oa_fraction_for_hvac(
    hvac_id: str,
    overrides: dict[str, Any],
    default: float = 0.2,
) -> float:
    oa_map = dict(overrides.get("oa_fraction") or {})
    if hvac_id in oa_map:
        return float(oa_map[hvac_id])
    if "_default" in oa_map:
        return float(oa_map["_default"])
    return float(default)


def sketch_xy(zone_or_display: dict[str, Any]) -> tuple[float, float]:
    display = zone_or_display.get("display") or zone_or_display
    return (
        float(display.get("x", 0) or 0),
        float(display.get("y", 0) or 0),
    )
