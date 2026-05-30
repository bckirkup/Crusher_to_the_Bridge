#!/usr/bin/env python3
"""Build class-representative deck_graphics.geojson from platform spatial_layout + airflow."""
from __future__ import annotations

import json
import os
from typing import Any

from blueprint_shapes import (
    HULL_FAMILY,
    blueprint_compartment,
    hull_feature,
    hull_waterline_feature,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_representative_geojson(
    platform_id: str,
    layout: dict[str, Any],
    airflow: dict[str, Any],
) -> dict[str, Any]:
    """Build FeatureCollection for deck_graphics.geojson."""
    dims = layout.get("deck_dimensions", {}) or {}
    length_m = float(dims.get("length_m", 120))
    beam_m = float(dims.get("beam_m", 15))

    features: list[dict[str, Any]] = [
        hull_feature(platform_id, length_m, beam_m),
        hull_waterline_feature(platform_id, length_m, beam_m),
    ]

    for zone in layout.get("zones", []):
        zid = zone["id"]
        display = zone.get("display", {})
        cx = float(display.get("x", 0))
        cy = float(display.get("y", 0))
        vol = float(zone.get("volume_m3", 100))
        ztype = zone.get("type", "Free")
        ring = blueprint_compartment(cx, cy, vol, ztype)
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

    zmap = {z["id"]: z for z in layout.get("zones", [])}
    for link in airflow.get("adjacency", []):
        fz, tz = link.get("from"), link.get("to")
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
