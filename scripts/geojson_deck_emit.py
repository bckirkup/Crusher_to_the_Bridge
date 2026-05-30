"""Lightweight GeoJSON -> deck_graphics without geopandas."""
from __future__ import annotations

import json
from typing import Any


def emit_from_geojson_file(input_path: str, platform_id: str) -> dict[str, Any]:
    with open(input_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    features: list[dict[str, Any]] = []
    xs: list[float] = []
    ys: list[float] = []

    for feat in raw.get("features", []):
        geom = feat.get("geometry", {})
        props = feat.get("properties") or {}
        gtype = geom.get("type")

        if gtype == "Polygon":
            ring = [[float(p[0]), float(p[1])] for p in geom["coordinates"][0]]
            for pt in ring:
                xs.append(pt[0])
                ys.append(pt[1])
            zid = props.get("ROOM_NAME", props.get("NAME", "zone")).replace(" ", "_")
            features.append({
                "type": "Feature",
                "properties": {
                    "kind": "compartment",
                    "zone_id": zid,
                    "deck": str(props.get("DECK", "main")).lower(),
                    "room_type": props.get("ROOM_TYPE", "Free"),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            })
        elif gtype == "LineString":
            coords = [[float(p[0]), float(p[1])] for p in geom["coordinates"]]
            for pt in coords:
                xs.append(pt[0])
                ys.append(pt[1])
            features.append({
                "type": "Feature",
                "properties": {"kind": "hvac_path"},
                "geometry": {"type": "LineString", "coordinates": coords},
            })

    if xs and ys:
        pad = 3.0
        hull = [
            [min(xs) - pad, min(ys) - pad],
            [max(xs) + pad, min(ys) - pad],
            [max(xs) + pad, max(ys) + pad],
            [min(xs) - pad, max(ys) + pad],
            [min(xs) - pad, min(ys) - pad],
        ]
        features.insert(0, {
            "type": "Feature",
            "properties": {"kind": "hull_outline", "platform_id": platform_id},
            "geometry": {"type": "Polygon", "coordinates": [hull]},
        })

    return {"type": "FeatureCollection", "features": features}
