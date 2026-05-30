#!/usr/bin/env python3
"""
gis_spatial_bridge.py – GIS-to-Crusher Layout Converter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reads GIS vector files (Shapefile or GeoJSON) containing polygon layers
(compartments/rooms) and optional line layers (HVAC ducts/corridors) and
converts them into the project's native JSON layout specs:

  - ``spatial_layout.json``
  - ``air_flow_paths.json``

Polygon centroids become the dashboard display coordinates.  Line layers
that intersect two compartment polygons generate directed adjacency and
HVAC cross-zone edges via a NetworkX digraph.

Usage::

    python tools/gis_spatial_bridge.py \\
        --input data/shp/destroyer_deck1.shp \\
        --output data/platforms/my_ship/

    # With separate HVAC duct layer:
    python tools/gis_spatial_bridge.py \\
        --input data/shp/compartments.geojson \\
        --hvac data/shp/hvac_ducts.geojson \\
        --output data/platforms/my_ship/

    # With explicit column mapping:
    python tools/gis_spatial_bridge.py \\
        --input data/shp/deck.shp \\
        --col-id ROOM_NAME \\
        --col-type ROOM_TYPE \\
        --col-volume VOLUME_M3 \\
        --col-ach BASE_ACH \\
        --col-deck DECK \\
        --col-traffic TRAFFIC
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon


# ── Defaults & column name resolution ────────────────────────────────────

_ID_CANDIDATES = ["ROOM_NAME", "NAME", "ID", "ROOM_ID", "COMPARTMENT", "LABEL"]
_TYPE_CANDIDATES = ["ROOM_TYPE", "TYPE", "CATEGORY", "USE", "FUNCTION"]
_VOL_CANDIDATES = ["VOLUME_M3", "VOLUME", "VOL_M3", "VOL"]
_ACH_CANDIDATES = ["BASE_ACH", "ACH", "AIR_CHANGES", "VENTILATION"]
_DECK_CANDIDATES = ["DECK", "LEVEL", "FLOOR"]
_TRAFFIC_CANDIDATES = ["TRAFFIC", "USAGE", "DENSITY"]
_FLOW_CANDIDATES = ["FLOW_RATE", "FLOW_M3H", "FLOW_RATE_M3H", "CFM"]
_DUCTED_CANDIDATES = ["IS_DUCTED", "IS_HVAC_DUCTED", "DUCTED", "HVAC"]

_DEFAULT_ROOM_TYPE = "Free"
_DEFAULT_VOLUME = 100
_DEFAULT_ACH = 6.0
_DEFAULT_DECK = "main"
_DEFAULT_TRAFFIC = "medium"
_DEFAULT_FLOW_RATE = 50.0


def _resolve_column(
    columns: list[str],
    candidates: list[str],
    override: str | None = None,
) -> str | None:
    """Find the first matching column name (case-insensitive)."""
    if override:
        for c in columns:
            if c.upper() == override.upper():
                return c
        return None
    upper_cols = {c.upper(): c for c in columns}
    for candidate in candidates:
        if candidate.upper() in upper_cols:
            return upper_cols[candidate.upper()]
    return None


# ── Polygon → layout nodes ───────────────────────────────────────────────

def _polygons_to_zones(
    gdf: gpd.GeoDataFrame,
    col_id: str | None,
    col_type: str | None,
    col_volume: str | None,
    col_ach: str | None,
    col_deck: str | None,
    col_traffic: str | None,
) -> list[dict[str, Any]]:
    """Convert polygon features to spatial_layout zone dicts."""
    cols = list(gdf.columns)
    id_col = _resolve_column(cols, _ID_CANDIDATES, col_id)
    type_col = _resolve_column(cols, _TYPE_CANDIDATES, col_type)
    vol_col = _resolve_column(cols, _VOL_CANDIDATES, col_volume)
    ach_col = _resolve_column(cols, _ACH_CANDIDATES, col_ach)
    deck_col = _resolve_column(cols, _DECK_CANDIDATES, col_deck)
    traffic_col = _resolve_column(cols, _TRAFFIC_CANDIDATES, col_traffic)

    zones: list[dict[str, Any]] = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if not isinstance(geom, (Polygon, MultiPolygon)):
            continue

        centroid = geom.centroid
        zone_id = str(row[id_col]) if id_col and id_col in row.index else f"Zone_{idx}"
        zone_id = zone_id.replace(" ", "_")

        zone: dict[str, Any] = {
            "id": zone_id,
            "type": str(row[type_col]) if type_col and type_col in row.index else _DEFAULT_ROOM_TYPE,
            "traffic": str(row[traffic_col]).lower() if traffic_col and traffic_col in row.index else _DEFAULT_TRAFFIC,
            "volume_m3": float(row[vol_col]) if vol_col and vol_col in row.index else _DEFAULT_VOLUME,
            "deck": str(row[deck_col]).lower() if deck_col and deck_col in row.index else _DEFAULT_DECK,
            "display": {
                "x": round(centroid.x, 2),
                "y": round(centroid.y, 2),
            },
        }

        if ach_col and ach_col in row.index:
            zone["base_ach"] = float(row[ach_col])

        zones.append(zone)

    return zones


# ── Line layers → HVAC / adjacency edges ────────────────────────────────

def _lines_to_edges(
    line_gdf: gpd.GeoDataFrame,
    poly_gdf: gpd.GeoDataFrame,
    zone_ids: list[str],
    col_flow: str | None = None,
    col_ducted: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """
    Trace line geometries to find which compartment polygons they connect.

    Returns (cross_zone_links, adjacency).
    """
    cols = list(line_gdf.columns)
    flow_col = _resolve_column(cols, _FLOW_CANDIDATES, col_flow)
    ducted_col = _resolve_column(cols, _DUCTED_CANDIDATES, col_ducted)

    G = nx.DiGraph()
    adjacency: list[dict[str, str]] = []

    for _, line_row in line_gdf.iterrows():
        line_geom = line_row.geometry
        if line_geom is None or line_geom.is_empty:
            continue
        if not isinstance(line_geom, (LineString, MultiLineString)):
            continue

        lines = [line_geom] if isinstance(line_geom, LineString) else list(line_geom.geoms)

        for single_line in lines:
            connected: list[str] = []
            for poly_idx, poly_row in poly_gdf.iterrows():
                poly_geom = poly_row.geometry
                if poly_geom is None or poly_geom.is_empty:
                    continue
                if single_line.intersects(poly_geom):
                    pid = zone_ids[poly_idx] if poly_idx < len(zone_ids) else f"Zone_{poly_idx}"
                    if pid not in connected:
                        connected.append(pid)

            if len(connected) >= 2:
                for i in range(len(connected) - 1):
                    from_z = connected[i]
                    to_z = connected[i + 1]

                    flow_rate = _DEFAULT_FLOW_RATE
                    if flow_col and flow_col in line_row.index:
                        try:
                            flow_rate = float(line_row[flow_col])
                        except (ValueError, TypeError):
                            pass

                    is_ducted = False
                    if ducted_col and ducted_col in line_row.index:
                        val = line_row[ducted_col]
                        is_ducted = bool(val) if not isinstance(val, str) else val.lower() in ("true", "yes", "1")

                    edge_key = (from_z, to_z)
                    if not G.has_edge(*edge_key):
                        G.add_edge(
                            from_z, to_z,
                            flow_rate_m3h=flow_rate,
                            is_hvac_ducted=is_ducted,
                        )
                        adj_type = "hvac_duct" if is_ducted else "passageway"
                        adjacency.append({
                            "from": from_z,
                            "to": to_z,
                            "type": adj_type,
                        })

    cross_zone_links: list[dict[str, Any]] = []
    for u, v, data in G.edges(data=True):
        cross_zone_links.append({
            "from": u,
            "to": v,
            "flow_rate_m3h": data["flow_rate_m3h"],
            "is_hvac_ducted": data["is_hvac_ducted"],
            "path": f"{u}_to_{v}",
        })

    return cross_zone_links, adjacency


def _compute_polygon_adjacency(
    poly_gdf: gpd.GeoDataFrame,
    zone_ids: list[str],
) -> list[dict[str, str]]:
    """Compute adjacency from polygon touches/overlaps (no line layer)."""
    adjacency: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for i in range(len(poly_gdf)):
        geom_i = poly_gdf.iloc[i].geometry
        if geom_i is None or geom_i.is_empty:
            continue
        for j in range(i + 1, len(poly_gdf)):
            geom_j = poly_gdf.iloc[j].geometry
            if geom_j is None or geom_j.is_empty:
                continue
            if geom_i.touches(geom_j) or geom_i.intersects(geom_j):
                a, b = zone_ids[i], zone_ids[j]
                if (a, b) not in seen:
                    seen.add((a, b))
                    adjacency.append({"from": a, "to": b, "type": "passageway"})

    return adjacency


# ── HVAC zone grouping ───────────────────────────────────────────────────

def _group_hvac_zones(
    zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group rooms by deck into HVAC zones."""
    deck_groups: dict[str, list[str]] = {}
    deck_ach: dict[str, float] = {}

    for z in zones:
        deck = z.get("deck", _DEFAULT_DECK)
        deck_groups.setdefault(deck, []).append(z["id"])
        ach = z.get("base_ach", _DEFAULT_ACH)
        deck_ach[deck] = max(deck_ach.get(deck, 0), ach)

    hvac_zones: list[dict[str, Any]] = []
    for deck, rooms in sorted(deck_groups.items()):
        hvac_zones.append({
            "id": f"zone_{deck}",
            "rooms": rooms,
            "ach": deck_ach.get(deck, _DEFAULT_ACH),
            "description": f"{deck.title()} deck ventilation zone",
        })

    return hvac_zones


# ── Main conversion ─────────────────────────────────────────────────────

def convert(
    input_path: str,
    output_dir: str,
    hvac_path: str | None = None,
    platform_name: str | None = None,
    col_id: str | None = None,
    col_type: str | None = None,
    col_volume: str | None = None,
    col_ach: str | None = None,
    col_deck: str | None = None,
    col_traffic: str | None = None,
) -> tuple[str, str]:
    """
    Convert a GIS file into spatial_layout.json and air_flow_paths.json.

    Returns (spatial_path, airflow_path).
    """
    print(f"  Reading compartment polygons from: {input_path}")
    gdf = gpd.read_file(input_path)
    print(f"  Loaded {len(gdf)} features, CRS={gdf.crs}")

    # Separate polygons and lines
    poly_mask = gdf.geometry.apply(
        lambda g: isinstance(g, (Polygon, MultiPolygon)) if g else False
    )
    line_mask = gdf.geometry.apply(
        lambda g: isinstance(g, (LineString, MultiLineString)) if g else False
    )

    poly_gdf = gdf[poly_mask].reset_index(drop=True)
    line_gdf = gdf[line_mask].reset_index(drop=True)

    if len(poly_gdf) == 0:
        print("  ERROR: No polygon features found in input file.", file=sys.stderr)
        sys.exit(1)

    print(f"  Found {len(poly_gdf)} polygon features (compartments)")
    print(f"  Found {len(line_gdf)} line features (ducts/corridors)")

    # Convert polygons to zone nodes
    zones = _polygons_to_zones(
        poly_gdf, col_id, col_type, col_volume, col_ach, col_deck, col_traffic,
    )
    zone_ids = [z["id"] for z in zones]
    print(f"  Generated {len(zones)} zone nodes")

    for z in zones:
        print(f"    {z['id']:20s}  type={z['type']:10s}  "
              f"vol={z['volume_m3']:6.0f}m3  "
              f"centroid=({z['display']['x']:.1f}, {z['display']['y']:.1f})")

    # Load separate HVAC line layer if provided
    hvac_line_gdf = None
    if hvac_path:
        print(f"\n  Reading HVAC duct layer from: {hvac_path}")
        hvac_line_gdf = gpd.read_file(hvac_path)
        hvac_line_mask = hvac_line_gdf.geometry.apply(
            lambda g: isinstance(g, (LineString, MultiLineString)) if g else False
        )
        hvac_line_gdf = hvac_line_gdf[hvac_line_mask].reset_index(drop=True)
        print(f"  Found {len(hvac_line_gdf)} HVAC line features")

    # Build adjacency and cross-zone links
    cross_zone_links: list[dict[str, Any]] = []
    adjacency: list[dict[str, str]] = []

    combined_lines = line_gdf
    if hvac_line_gdf is not None and len(hvac_line_gdf) > 0:
        import pandas as pd
        combined_lines = pd.concat([line_gdf, hvac_line_gdf], ignore_index=True)
        combined_lines = gpd.GeoDataFrame(combined_lines, geometry="geometry")

    if len(combined_lines) > 0:
        cross_zone_links, adjacency = _lines_to_edges(
            combined_lines, poly_gdf, zone_ids,
        )
        print(f"  Generated {len(cross_zone_links)} cross-zone links from line features")
        print(f"  Generated {len(adjacency)} adjacency edges from line features")
    else:
        print("  No line features — computing adjacency from polygon topology")
        adjacency = _compute_polygon_adjacency(poly_gdf, zone_ids)
        print(f"  Generated {len(adjacency)} adjacency edges from polygon touches")

    # Group HVAC zones by deck
    hvac_zones = _group_hvac_zones(zones)
    print(f"  Grouped into {len(hvac_zones)} HVAC zones by deck")

    # Derive platform name
    if not platform_name:
        platform_name = os.path.splitext(os.path.basename(input_path))[0]

    # Build output dicts
    spatial_layout = {
        "platform": platform_name,
        "description": f"Auto-generated from {os.path.basename(input_path)}",
        "zones": zones,
    }

    air_flow_paths = {
        "platform": platform_name,
        "description": f"HVAC and adjacency network from {os.path.basename(input_path)}",
        "hvac_zones": hvac_zones,
        "cross_zone_links": cross_zone_links,
        "adjacency": adjacency,
    }

    # Write output
    os.makedirs(output_dir, exist_ok=True)
    spatial_path = os.path.join(output_dir, "spatial_layout.json")
    airflow_path = os.path.join(output_dir, "air_flow_paths.json")

    with open(spatial_path, "w", encoding="utf-8") as fh:
        json.dump(spatial_layout, fh, indent=2, ensure_ascii=False)
    print(f"\n  Wrote: {spatial_path}")

    with open(airflow_path, "w", encoding="utf-8") as fh:
        json.dump(air_flow_paths, fh, indent=2, ensure_ascii=False)
    print(f"  Wrote: {airflow_path}")

    return spatial_path, airflow_path


def emit_deck_graphics(
    input_path: str,
    output_path: str,
    platform_id: str | None = None,
) -> str:
    """
    Write deck_graphics.geojson from GIS polygons and lines (visual-only sidecar).

    Compartment polygons use ROOM_NAME/NAME as zone_id; lines become hvac_path features.
    """
    gdf = gpd.read_file(input_path)
    pid = platform_id or os.path.splitext(os.path.basename(input_path))[0]

    poly_mask = gdf.geometry.apply(
        lambda g: isinstance(g, (Polygon, MultiPolygon)) if g else False
    )
    line_mask = gdf.geometry.apply(
        lambda g: isinstance(g, (LineString, MultiLineString)) if g else False
    )
    poly_gdf = gdf[poly_mask].reset_index(drop=True)
    line_gdf = gdf[line_mask].reset_index(drop=True)

    cols = list(gdf.columns)
    id_col = _resolve_column(cols, _ID_CANDIDATES, None)
    deck_col = _resolve_column(cols, _DECK_CANDIDATES, None)
    type_col = _resolve_column(cols, _TYPE_CANDIDATES, None)

    features: list[dict[str, Any]] = []

    def _ring_from_geom(geom: Any) -> list[list[float]] | None:
        if geom is None or geom.is_empty:
            return None
        if isinstance(geom, MultiPolygon):
            geom = max(geom.geoms, key=lambda g: g.area)
        if not isinstance(geom, Polygon):
            return None
        ext = list(geom.exterior.coords)
        return [[float(x), float(y)] for x, y in ext]

    xs: list[float] = []
    ys: list[float] = []

    for idx, row in poly_gdf.iterrows():
        geom = row.geometry
        ring = _ring_from_geom(geom)
        if not ring:
            continue
        for pt in ring:
            xs.append(pt[0])
            ys.append(pt[1])
        zid = str(row[id_col]) if id_col and id_col in row.index else f"Zone_{idx}"
        zid = zid.replace(" ", "_")
        props: dict[str, Any] = {
            "kind": "compartment",
            "zone_id": zid,
            "deck": str(row[deck_col]) if deck_col and deck_col in row.index else "main",
        }
        if type_col and type_col in row.index:
            props["room_type"] = str(row[type_col])
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })

    for _, row in line_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if isinstance(geom, MultiLineString):
            lines = list(geom.geoms)
            geom = lines[0] if lines else None
        if not isinstance(geom, LineString):
            continue
        coords = [[float(x), float(y)] for x, y in geom.coords]
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
        hull_ring = [
            [min(xs) - pad, min(ys) - pad],
            [max(xs) + pad, min(ys) - pad],
            [max(xs) + pad, max(ys) + pad],
            [min(xs) - pad, max(ys) + pad],
            [min(xs) - pad, min(ys) - pad],
        ]
        features.insert(0, {
            "type": "Feature",
            "properties": {"kind": "hull_outline", "platform_id": pid},
            "geometry": {"type": "Polygon", "coordinates": [hull_ring]},
        })

    collection = {"type": "FeatureCollection", "features": features}
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, indent=2, ensure_ascii=False)
    return output_path


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert GIS vector files (Shapefile/GeoJSON) to Crusher "
                    "Labs native JSON layout specifications.",
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to compartment polygon file (Shapefile or GeoJSON)",
    )
    parser.add_argument(
        "--hvac",
        help="Optional separate HVAC duct line layer (Shapefile or GeoJSON)",
    )
    parser.add_argument(
        "--output", "-o",
        default="data/platforms/imported/",
        help="Output directory for generated JSON files "
             "(default: data/platforms/imported/)",
    )
    parser.add_argument(
        "--platform", "-p",
        help="Platform name (default: derived from input filename)",
    )

    # Column mapping overrides
    parser.add_argument("--col-id", help="Column name for room/zone ID")
    parser.add_argument("--col-type", help="Column name for room type")
    parser.add_argument("--col-volume", help="Column name for room volume (m3)")
    parser.add_argument("--col-ach", help="Column name for air changes per hour")
    parser.add_argument("--col-deck", help="Column name for deck/level")
    parser.add_argument("--col-traffic", help="Column name for traffic density")
    parser.add_argument(
        "--emit-deck-graphics",
        nargs="?",
        const="",
        default=None,
        metavar="PATH",
        help="Also write deck_graphics.geojson to PATH or <output>/deck_graphics.geojson",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  GIS SPATIAL BRIDGE — Crusher Labs Layout Converter")
    print("=" * 70)

    convert(
        input_path=args.input,
        output_dir=args.output,
        hvac_path=args.hvac,
        platform_name=args.platform,
        col_id=args.col_id,
        col_type=args.col_type,
        col_volume=args.col_volume,
        col_ach=args.col_ach,
        col_deck=args.col_deck,
        col_traffic=args.col_traffic,
    )

    if args.emit_deck_graphics is not None:
        gfx_path = args.emit_deck_graphics
        if not gfx_path or not str(gfx_path).endswith(".geojson"):
            gfx_path = os.path.join(args.output, "deck_graphics.geojson")
        emit_deck_graphics(args.input, gfx_path, platform_name=args.platform)
        print(f"  Wrote deck graphics: {gfx_path}")

    print("=" * 70)
    print("  Conversion complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
