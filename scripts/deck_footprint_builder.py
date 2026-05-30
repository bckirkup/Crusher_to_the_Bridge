#!/usr/bin/env python3
"""Build class-representative deck_graphics.geojson from platform spatial_layout + airflow."""
from __future__ import annotations

import json
import math
import os
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HULL_FAMILY = {
    "destroyer_baseline": "naval_surface_combatant",
    "fletcher_class_destroyer": "naval_surface_combatant",
    "legend_class_nsc": "coast_guard",
    "san_antonio_class_lpd": "naval_amphib",
    "expedition_cruise_300": "cruise_small",
    "mega_cruise_5000": "cruise_large",
    "enterprise_constitution_tos": "starship_constitution",
    "enterprise_galaxy_tng": "starship_galaxy",
}


def _rect_polygon(cx: float, cy: float, w: float, h: float) -> list[list[float]]:
    hw, hh = w / 2, h / 2
    return [
        [cx - hw, cy - hh],
        [cx + hw, cy - hh],
        [cx + hw, cy + hh],
        [cx - hw, cy + hh],
        [cx - hw, cy - hh],
    ]


def _zone_size(volume_m3: float, zone_type: str) -> tuple[float, float]:
    side = max(4.0, math.sqrt(volume_m3) * 0.35)
    if zone_type == "Dining":
        return side * 1.4, side * 0.9
    if zone_type == "Room":
        return side * 1.1, side * 1.1
    if zone_type == "Engineering" or zone_type == "Room":
        return side * 1.2, side * 1.0
    return side, side * 0.85


def _hull_outline(family: str, length_m: float, beam_m: float) -> list[list[float]]:
    L, B = length_m, beam_m
    if family == "cruise_large":
        return [
            [L * 0.02, B * 0.35],
            [L * 0.15, B * 0.08],
            [L * 0.55, B * 0.05],
            [L * 0.88, B * 0.12],
            [L * 0.98, B * 0.35],
            [L * 0.95, B * 0.65],
            [L * 0.75, B * 0.92],
            [L * 0.35, B * 0.95],
            [L * 0.08, B * 0.85],
            [L * 0.02, B * 0.35],
        ]
    if family == "cruise_small":
        return [
            [L * 0.05, B * 0.4],
            [L * 0.2, B * 0.1],
            [L * 0.75, B * 0.08],
            [L * 0.95, B * 0.35],
            [L * 0.9, B * 0.7],
            [L * 0.5, B * 0.92],
            [L * 0.1, B * 0.8],
            [L * 0.05, B * 0.4],
        ]
    if family == "naval_amphib":
        return [
            [L * 0.05, B * 0.25],
            [L * 0.35, B * 0.05],
            [L * 0.75, B * 0.08],
            [L * 0.95, B * 0.3],
            [L * 0.92, B * 0.75],
            [L * 0.55, B * 0.95],
            [L * 0.15, B * 0.88],
            [L * 0.05, B * 0.25],
        ]
    if family == "coast_guard":
        return [
            [L * 0.08, B * 0.3],
            [L * 0.25, B * 0.08],
            [L * 0.8, B * 0.1],
            [L * 0.95, B * 0.4],
            [L * 0.88, B * 0.78],
            [L * 0.4, B * 0.92],
            [L * 0.08, B * 0.3],
        ]
    if family == "starship_galaxy":
        return [
            [L * 0.35, B * 0.02],
            [L * 0.75, B * 0.05],
            [L * 0.95, B * 0.25],
            [L * 0.92, B * 0.55],
            [L * 0.7, B * 0.75],
            [L * 0.45, B * 0.82],
            [L * 0.15, B * 0.7],
            [L * 0.05, B * 0.45],
            [L * 0.08, B * 0.2],
            [L * 0.2, B * 0.05],
            [L * 0.35, B * 0.02],
            [L * 0.12, B * 0.55],
            [L * 0.08, B * 0.75],
            [L * 0.02, B * 0.5],
            [L * 0.05, B * 0.35],
            [L * 0.35, B * 0.02],
        ]
    if family == "starship_constitution":
        return [
            [L * 0.4, B * 0.05],
            [L * 0.85, B * 0.12],
            [L * 0.95, B * 0.35],
            [L * 0.88, B * 0.65],
            [L * 0.55, B * 0.88],
            [L * 0.2, B * 0.82],
            [L * 0.05, B * 0.5],
            [L * 0.15, B * 0.15],
            [L * 0.4, B * 0.05],
            [L * 0.25, B * 0.55],
            [L * 0.08, B * 0.7],
            [L * 0.02, B * 0.45],
            [L * 0.4, B * 0.05],
        ]
    # naval_surface_combatant default
    return [
        [L * 0.05, B * 0.45],
        [L * 0.2, B * 0.12],
        [L * 0.75, B * 0.08],
        [L * 0.95, B * 0.35],
        [L * 0.92, B * 0.7],
        [L * 0.6, B * 0.88],
        [L * 0.2, B * 0.85],
        [L * 0.05, B * 0.45],
    ]


def build_representative_geojson(
    platform_id: str,
    layout: dict[str, Any],
    airflow: dict[str, Any],
) -> dict[str, Any]:
    """Build FeatureCollection for deck_graphics.geojson."""
    dims = layout.get("deck_dimensions", {}) or {}
    length_m = float(dims.get("length_m", 120))
    beam_m = float(dims.get("beam_m", 15))
    family = HULL_FAMILY.get(platform_id, "naval_surface_combatant")

    features: list[dict[str, Any]] = []

    hull_ring = _hull_outline(family, length_m, beam_m)
    features.append({
        "type": "Feature",
        "properties": {"kind": "hull_outline", "platform_id": platform_id},
        "geometry": {"type": "Polygon", "coordinates": [hull_ring]},
    })

    for zone in layout.get("zones", []):
        zid = zone["id"]
        display = zone.get("display", {})
        cx = float(display.get("x", 0))
        cy = float(display.get("y", 0))
        vol = float(zone.get("volume_m3", 100))
        ztype = zone.get("type", "Free")
        w, h = _zone_size(vol, ztype)
        ring = _rect_polygon(cx, cy, w, h)
        features.append({
            "type": "Feature",
            "properties": {
                "kind": "compartment",
                "zone_id": zid,
                "deck": zone.get("deck", "main"),
                "room_type": ztype,
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })

    for link in airflow.get("adjacency", []):
        fz, tz = link.get("from"), link.get("to")
        zmap = {z["id"]: z for z in layout.get("zones", [])}
        if fz not in zmap or tz not in zmap:
            continue
        fxy = zmap[fz].get("display", {})
        txy = zmap[tz].get("display", {})
        features.append({
            "type": "Feature",
            "properties": {"kind": "hvac_path", "from": fz, "to": tz},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [float(fxy.get("x", 0)), float(fxy.get("y", 0))],
                    [float(txy.get("x", 0)), float(txy.get("y", 0))],
                ],
            },
        })

    return {"type": "FeatureCollection", "features": features}


def compute_view_bounds(geojson: dict[str, Any], padding: float = 5.0) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    for feat in geojson.get("features", []):
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom.get("type") == "Polygon" and coords:
            for pt in coords[0]:
                xs.append(pt[0])
                ys.append(pt[1])
        elif geom.get("type") == "LineString":
            for pt in coords:
                xs.append(pt[0])
                ys.append(pt[1])
    if not xs:
        return {"xmin": 0, "xmax": 120, "ymin": 0, "ymax": 15}
    return {
        "xmin": min(xs) - padding,
        "xmax": max(xs) + padding,
        "ymin": min(ys) - padding,
        "ymax": max(ys) + padding,
    }


def build_manifest(
    platform_id: str,
    layout: dict[str, Any],
    footprint_tier: str,
    view_bounds: dict[str, float],
) -> dict[str, Any]:
    desc = layout.get("description", platform_id)
    zone_ids = [z["id"] for z in layout.get("zones", [])]
    labels = {
        "enterprise_galaxy_tng": "Galaxy-class (fiction-adapted)",
        "enterprise_constitution_tos": "Constitution-class (fiction-adapted)",
        "mega_cruise_5000": "Mega cruise (representative)",
        "expedition_cruise_300": "Expedition cruise (representative)",
        "fletcher_class_destroyer": "Fletcher-class DD (representative)",
        "legend_class_nsc": "Legend-class NSC (representative)",
        "san_antonio_class_lpd": "San Antonio-class LPD (representative)",
        "destroyer_baseline": "Destroyer baseline",
    }
    tier = footprint_tier
    disclaimer = (
        "Footprints are class-representative for simulation zones, not a surveyed deck plan of one vessel."
        if tier == "representative"
        else (
            "Fiction-adapted layout for demonstration; not an official starship blueprint."
            if tier == "fiction_adapted"
            else "Derived from GIS-traced compartment polygons."
        )
    )
    return {
        "platform_id": platform_id,
        "ship_class_label": labels.get(platform_id, platform_id.replace("_", " ").title()),
        "footprint_tier": tier,
        "representative_of": desc[:200],
        "provenance": [
            "spatial_layout.json description and deck_dimensions",
            f"zone count: {len(zone_ids)}",
        ],
        "disclaimer": disclaimer,
        "zone_ids": zone_ids,
        "view_bounds": view_bounds,
        "assets": {
            "deck_graphics": "deck_graphics.geojson",
            "deck_hull": "deck_hull.png",
        },
    }
