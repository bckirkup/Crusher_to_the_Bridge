#!/usr/bin/env python3
"""Build class-representative deck_graphics.geojson from platform spatial_layout + airflow."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from blueprint_shapes import (
    hull_feature,
    hull_waterline_feature,
)
from compartment_packer import pack_deck_compartments

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_representative_geojson(
    platform_id: str,
    layout: dict[str, Any],
    airflow: dict[str, Any],
) -> dict[str, Any]:
    """Build FeatureCollection for deck_graphics.geojson.

    Compartments are packed **per deck** into the hull plan (length × beam)
    so footprints on the same deck do not overwrite each other. Cross-deck
    stacking is a dashboard concern (elevation + single-deck plan), not GeoJSON.
    """
    dims = layout.get("deck_dimensions", {}) or {}
    length_m = float(dims.get("length_m", 120))
    beam_m = float(dims.get("beam_m", 15))

    features: list[dict[str, Any]] = [
        hull_feature(platform_id, length_m, beam_m),
        hull_waterline_feature(platform_id, length_m, beam_m),
    ]

    by_deck: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for zone in layout.get("zones", []):
        by_deck[str(zone.get("deck", "main"))].append(zone)

    packed_centers: dict[str, tuple[float, float]] = {}
    for deck, zones in by_deck.items():
        rings = pack_deck_compartments(zones, length_m, beam_m)
        for zone in zones:
            zid = zone["id"]
            ring = rings.get(zid)
            if not ring:
                continue
            xs = [p[0] for p in ring[:-1]]
            ys = [p[1] for p in ring[:-1]]
            packed_centers[zid] = (sum(xs) / len(xs), sum(ys) / len(ys))
            features.append({
                "type": "Feature",
                "properties": {
                    "kind": "compartment",
                    "zone_id": zid,
                    "deck": deck,
                    "room_type": zone.get("type", "Free"),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            })

    zmap = {z["id"]: z for z in layout.get("zones", [])}
    for link in airflow.get("adjacency", []):
        fz, tz = link.get("from"), link.get("to")
        if fz not in zmap or tz not in zmap:
            continue
        # Only draw HVAC links when both ends share a deck (plan-view readable).
        if zmap[fz].get("deck", "main") != zmap[tz].get("deck", "main"):
            continue
        fxy = packed_centers.get(fz)
        txy = packed_centers.get(tz)
        if not fxy or not txy:
            continue
        features.append({
            "type": "Feature",
            "properties": {"kind": "hvac_path", "from": fz, "to": tz},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [float(fxy[0]), float(fxy[1])],
                    [float(txy[0]), float(txy[1])],
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


def _footprint_disclaimer(tier: str) -> str:
    if tier == "representative":
        return (
            "Footprints are class-representative for simulation zones, "
            "not a surveyed deck plan of one vessel."
        )
    if tier == "fiction_adapted":
        return "Fiction-adapted layout for demonstration; not an official starship blueprint."
    return "Derived from GIS-traced compartment polygons."


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
        "messy_cruise_500": "Mega cruise — legacy well-mixed berthing",
        "expedition_cruise_300": "Expedition cruise — legacy well-mixed berthing",
        "expedition_cruise_450": "Expedition cruise (cabin-corridor)",
        "classic_cruise_1900": "Classic cruise (cabin-corridor)",
        "spirit_cruise_3000": "Spirit cruise (cabin-corridor)",
        "fletcher_class_destroyer": "Fletcher-class DD (representative)",
        "legend_class_nsc": "Legend-class NSC (representative)",
        "san_antonio_class_lpd": "San Antonio-class LPD (representative)",
        "destroyer_baseline": "Destroyer baseline",
    }
    tier = footprint_tier
    disclaimer = _footprint_disclaimer(tier)
    decks = sorted({str(z.get("deck", "main")) for z in layout.get("zones", [])})
    return {
        "platform_id": platform_id,
        "ship_class_label": labels.get(platform_id, platform_id.replace("_", " ").title()),
        "footprint_tier": tier,
        "representative_of": desc[:200],
        "provenance": [
            "spatial_layout.json description and deck_dimensions",
            f"zone count: {len(zone_ids)}",
            "per-deck non-overlapping compartment packing",
        ],
        "disclaimer": disclaimer,
        "zone_ids": zone_ids,
        "decks": decks,
        "view_bounds": view_bounds,
        "assets": {
            "deck_graphics": "deck_graphics.geojson",
            "deck_hull": "deck_hull.png",
            "deck_blueprint_bg": "deck_blueprint_bg.png",
            "architectural_graphics": "graphics/graphics.json",
        },
    }
