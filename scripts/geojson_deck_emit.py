"""Lightweight GeoJSON -> deck_graphics without geopandas."""
from __future__ import annotations

import json
from typing import Any

from blueprint_shapes import hull_feature, hull_waterline_feature


def emit_from_geojson_file(
    input_path: str,
    platform_id: str,
    layout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with open(input_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    features: list[dict[str, Any]] = []

    for feat in raw.get("features", []):
        geom = feat.get("geometry", {})
        props = feat.get("properties") or {}
        gtype = geom.get("type")

        if gtype == "Polygon":
            ring = [[float(p[0]), float(p[1])] for p in geom["coordinates"][0]]
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
            features.append({
                "type": "Feature",
                "properties": {"kind": "hvac_path"},
                "geometry": {"type": "LineString", "coordinates": coords},
            })

    dims = (layout or {}).get("deck_dimensions", {}) or {}
    length_m = float(dims.get("length_m", 120))
    beam_m = float(dims.get("beam_m", 15))

    hull_feats = [
        hull_feature(platform_id, length_m, beam_m),
        hull_waterline_feature(platform_id, length_m, beam_m),
    ]
    features = [f for f in features if f.get("properties", {}).get("kind") != "hull_outline"]
    features = hull_feats + features

    return {"type": "FeatureCollection", "features": features}
