#!/usr/bin/env python3
"""Fiction-adapted Enterprise hull + compartment polygons for dashboard precompute."""
from __future__ import annotations

from typing import Any


def _feat(kind: str, props: dict[str, Any], ring: list[list[float]]) -> dict[str, Any]:
    p = dict(props)
    p["kind"] = kind
    return {
        "type": "Feature",
        "properties": p,
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def _line(props: dict[str, Any], coords: list[list[float]]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {**props, "kind": "hvac_path"},
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def galaxy_tng_geojson() -> dict[str, Any]:
    """Galaxy-class saucer + drive section; zones match enterprise_galaxy_tng layout."""
    features: list[dict[str, Any]] = []
    hull = [
        [25, 5], [55, 2], [95, 8], [120, 25], [125, 42], [115, 48],
        [85, 50], [55, 48], [35, 42], [20, 30], [15, 15], [25, 5],
        [8, 35], [5, 45], [12, 48], [25, 5],
    ]
    features.append(_feat("hull_outline", {"platform_id": "enterprise_galaxy_tng"}, hull))

    zones = {
        "Bridge": ([118, 8], [128, 8], [128, 14], [118, 14]),
        "Ten_Forward": ([62, 4], [78, 4], [78, 12], [62, 12]),
        "Sickbay": ([82, 16], [98, 16], [98, 24], [82, 24]),
        "Main_Engineering": ([42, 40], [58, 40], [58, 50], [42, 50]),
        "Holodeck": ([68, 24], [82, 24], [82, 32], [68, 32]),
        "Crew_Quarters": ([38, 8], [52, 8], [52, 16], [38, 16]),
        "Family_Quarters": ([48, 14], [62, 14], [62, 22], [48, 22]),
        "Science_Labs": ([78, 28], [92, 28], [92, 36], [78, 36]),
        "Shuttlebay": ([32, 36], [48, 36], [48, 44], [32, 44]),
        "Cargo_Bay": ([28, 34], [40, 34], [40, 42], [28, 42]),
        "Galley": ([56, 18], [66, 18], [66, 24], [56, 24]),
        "Crew_Lounge": ([60, 10], [72, 10], [72, 18], [60, 18]),
        "Security_Office": ([74, 32], [84, 32], [84, 38], [74, 38]),
        "Arboretum": ([90, 38], [105, 38], [105, 46], [90, 46]),
        "Stellar_Cartography": ([96, 34], [108, 34], [108, 42], [96, 42]),
        "Schoolroom": ([48, 22], [58, 22], [58, 28], [48, 28]),
        "Mess_Hall": ([58, 16], [68, 16], [68, 22], [58, 22]),
    }
    for zid, ring_pts in zones.items():
        ring = list(ring_pts) + [ring_pts[0]]
        features.append(_feat("compartment", {"zone_id": zid, "deck": "saucer"}, ring))

    paths = [
        ("Bridge", "Sickbay", [[123, 11], [90, 20]]),
        ("Ten_Forward", "Crew_Lounge", [[70, 8], [66, 14]]),
        ("Main_Engineering", "Cargo_Bay", [[50, 45], [34, 38]]),
    ]
    for a, b, coords in paths:
        features.append(_line({"from": a, "to": b}, coords))

    return {"type": "FeatureCollection", "features": features}


def constitution_tos_geojson() -> dict[str, Any]:
    """Constitution-class hull; zones match enterprise_constitution_tos layout."""
    features: list[dict[str, Any]] = []
    hull = [
        [30, 6], [70, 3], [110, 10], [115, 28], [108, 40],
        [75, 45], [45, 42], [25, 32], [20, 18], [30, 6],
        [15, 38], [8, 42], [12, 44], [30, 6],
    ]
    features.append(_feat("hull_outline", {"platform_id": "enterprise_constitution_tos"}, hull))

    zones = {
        "Bridge": ([112, 6], [122, 6], [122, 12], [112, 12]),
        "Sickbay": ([88, 14], [102, 14], [102, 22], [88, 22]),
        "Engineering": ([48, 38], [62, 38], [62, 46], [48, 46]),
        "Transporter_Room": ([72, 24], [84, 24], [84, 32], [72, 32]),
        "Rec_Deck": ([58, 8], [72, 8], [72, 16], [58, 16]),
        "Galley": ([52, 14], [62, 14], [62, 20], [52, 20]),
        "Science_Lab": ([82, 28], [96, 28], [96, 36], [82, 36]),
        "Communications": ([100, 18], [110, 18], [110, 26], [100, 26]),
        "Security_Station": ([68, 32], [78, 32], [78, 38], [68, 38]),
        "Crew_Quarters": ([38, 4], [52, 4], [52, 12], [38, 12]),
        "Officer_Quarters": ([44, 18], [56, 18], [56, 26], [44, 26]),
        "Library": ([56, 34], [68, 34], [68, 42], [56, 42]),
        "Mess_Hall": ([62, 5], [72, 5], [72, 11], [62, 11]),
    }
    for zid, ring_pts in zones.items():
        ring = list(ring_pts) + [ring_pts[0]]
        features.append(_feat("compartment", {"zone_id": zid, "deck": "saucer_primary"}, ring))

    return {"type": "FeatureCollection", "features": features}
