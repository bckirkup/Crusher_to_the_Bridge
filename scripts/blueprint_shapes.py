#!/usr/bin/env python3
"""Blueprint-style hull outlines and compartment footprints for deck graphics."""
from __future__ import annotations

import math
from typing import Any

HULL_FAMILY: dict[str, str] = {
    "destroyer_baseline": "naval_surface_combatant",
    "fletcher_class_destroyer": "naval_surface_combatant",
    "legend_class_nsc": "coast_guard",
    "san_antonio_class_lpd": "naval_amphib",
    "expedition_cruise_300": "cruise_small",
    "expedition_cruise_450": "cruise_small",
    "classic_cruise_1900": "cruise_large",
    "spirit_cruise_3000": "cruise_large",
    "mega_cruise_5000": "cruise_large",
    "messy_cruise_500": "cruise_large",
    "enterprise_constitution_tos": "starship_constitution",
    "enterprise_galaxy_tng": "starship_galaxy",
}


def _close(ring: list[list[float]]) -> list[list[float]]:
    if ring and ring[0] != ring[-1]:
        return ring + [ring[0]]
    return ring


def hull_outline(family: str, length_m: float, beam_m: float) -> list[list[float]]:
    """Plan-view hull in ship coordinates (bow typically high x)."""
    L, B = length_m, beam_m
    mid = B * 0.5

    if family == "naval_surface_combatant":
        return _close([
            [L * 0.04, mid],
            [L * 0.12, B * 0.22],
            [L * 0.28, B * 0.12],
            [L * 0.72, B * 0.08],
            [L * 0.92, B * 0.22],
            [L * 0.98, mid],
            [L * 0.92, B * 0.78],
            [L * 0.72, B * 0.92],
            [L * 0.28, B * 0.88],
            [L * 0.12, B * 0.78],
            [L * 0.04, mid],
        ])

    if family == "cruise_large":
        return _close([
            [L * 0.02, mid],
            [L * 0.08, B * 0.18],
            [L * 0.22, B * 0.06],
            [L * 0.55, B * 0.04],
            [L * 0.82, B * 0.08],
            [L * 0.96, B * 0.22],
            [L * 0.99, mid],
            [L * 0.96, B * 0.78],
            [L * 0.82, B * 0.92],
            [L * 0.55, B * 0.96],
            [L * 0.22, B * 0.94],
            [L * 0.08, B * 0.82],
            [L * 0.02, mid],
        ])

    if family == "cruise_small":
        return _close([
            [L * 0.05, mid],
            [L * 0.14, B * 0.2],
            [L * 0.35, B * 0.08],
            [L * 0.78, B * 0.06],
            [L * 0.94, B * 0.25],
            [L * 0.97, mid],
            [L * 0.94, B * 0.75],
            [L * 0.78, B * 0.94],
            [L * 0.35, B * 0.92],
            [L * 0.14, B * 0.8],
            [L * 0.05, mid],
        ])

    if family == "naval_amphib":
        return _close([
            [L * 0.06, mid],
            [L * 0.2, B * 0.15],
            [L * 0.45, B * 0.05],
            [L * 0.7, B * 0.06],
            [L * 0.88, B * 0.2],
            [L * 0.96, mid],
            [L * 0.9, B * 0.82],
            [L * 0.65, B * 0.94],
            [L * 0.35, B * 0.92],
            [L * 0.15, B * 0.85],
            [L * 0.06, mid],
        ])

    if family == "coast_guard":
        return _close([
            [L * 0.08, mid],
            [L * 0.2, B * 0.18],
            [L * 0.55, B * 0.1],
            [L * 0.88, B * 0.2],
            [L * 0.96, mid],
            [L * 0.88, B * 0.8],
            [L * 0.55, B * 0.9],
            [L * 0.2, B * 0.82],
            [L * 0.08, mid],
        ])

    if family == "starship_galaxy":
        return _close([
            [L * 0.22, B * 0.12],
            [L * 0.38, B * 0.05],
            [L * 0.62, B * 0.04],
            [L * 0.78, B * 0.12],
            [L * 0.88, B * 0.28],
            [L * 0.9, B * 0.5],
            [L * 0.82, B * 0.68],
            [L * 0.62, B * 0.78],
            [L * 0.38, B * 0.76],
            [L * 0.22, B * 0.62],
            [L * 0.14, B * 0.4],
            [L * 0.22, B * 0.12],
            [L * 0.08, B * 0.45],
            [L * 0.05, B * 0.62],
            [L * 0.1, B * 0.72],
            [L * 0.22, B * 0.12],
        ])

    if family == "starship_constitution":
        return _close([
            [L * 0.25, B * 0.15],
            [L * 0.45, B * 0.08],
            [L * 0.72, B * 0.1],
            [L * 0.88, B * 0.25],
            [L * 0.92, B * 0.5],
            [L * 0.85, B * 0.72],
            [L * 0.6, B * 0.85],
            [L * 0.35, B * 0.82],
            [L * 0.18, B * 0.65],
            [L * 0.12, B * 0.4],
            [L * 0.25, B * 0.15],
            [L * 0.06, B * 0.55],
            [L * 0.04, B * 0.7],
            [L * 0.12, B * 0.78],
            [L * 0.25, B * 0.15],
        ])

    return _close([
        [L * 0.05, mid],
        [L * 0.15, B * 0.2],
        [L * 0.5, B * 0.1],
        [L * 0.9, B * 0.2],
        [L * 0.97, mid],
        [L * 0.9, B * 0.8],
        [L * 0.5, B * 0.9],
        [L * 0.15, B * 0.8],
        [L * 0.05, mid],
    ])


def hull_waterline(family: str, length_m: float, beam_m: float, inset: float = 0.92) -> list[list[float]]:
    """Inner construction line for blueprint aesthetic."""
    outer = hull_outline(family, length_m, beam_m)
    cx = sum(p[0] for p in outer[:-1]) / max(len(outer) - 1, 1)
    cy = sum(p[1] for p in outer[:-1]) / max(len(outer) - 1, 1)
    return _close([
        [cx + (p[0] - cx) * inset, cy + (p[1] - cy) * inset]
        for p in outer[:-1]
    ])


def zone_size(volume_m3: float, zone_type: str) -> tuple[float, float]:
    side = max(4.0, math.sqrt(volume_m3) * 0.38)
    if zone_type == "Dining":
        return side * 1.45, side * 0.88
    if zone_type == "Room":
        return side * 1.15, side * 1.05
    return side * 1.05, side * 0.82


def blueprint_compartment(
    cx: float,
    cy: float,
    volume_m3: float,
    zone_type: str,
    *,
    aspect_alongship: float = 1.0,
) -> list[list[float]]:
    """Chamfered octagon footprint (blueprint bay), not a plain rectangle."""
    w, h = zone_size(volume_m3, zone_type)
    w *= aspect_alongship
    c = min(w, h) * 0.22
    hw, hh = w / 2, h / 2
    return _close([
        [cx - hw + c, cy - hh],
        [cx + hw - c, cy - hh],
        [cx + hw, cy - hh + c],
        [cx + hw, cy + hh - c],
        [cx + hw - c, cy + hh],
        [cx - hw + c, cy + hh],
        [cx - hw, cy + hh - c],
        [cx - hw, cy - hh + c],
    ])


def hull_feature(platform_id: str, length_m: float, beam_m: float) -> dict[str, Any]:
    family = HULL_FAMILY.get(platform_id, "naval_surface_combatant")
    ring = hull_outline(family, length_m, beam_m)
    return {
        "type": "Feature",
        "properties": {"kind": "hull_outline", "platform_id": platform_id},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def hull_waterline_feature(platform_id: str, length_m: float, beam_m: float) -> dict[str, Any]:
    family = HULL_FAMILY.get(platform_id, "naval_surface_combatant")
    ring = hull_waterline(family, length_m, beam_m)
    return {
        "type": "Feature",
        "properties": {"kind": "hull_waterline", "platform_id": platform_id},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }
