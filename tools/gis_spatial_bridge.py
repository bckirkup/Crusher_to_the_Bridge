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
from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

@dataclass(frozen=True)
class _ZoneColumns:
    """Resolved column names for polygon → zone conversion."""

    id: str | None
    type: str | None
    volume: str | None
    ach: str | None
    deck: str | None
    traffic: str | None


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
    columns = _ZoneColumns(
        id=_resolve_column(cols, _ID_CANDIDATES, col_id),
        type=_resolve_column(cols, _TYPE_CANDIDATES, col_type),
        volume=_resolve_column(cols, _VOL_CANDIDATES, col_volume),
        ach=_resolve_column(cols, _ACH_CANDIDATES, col_ach),
        deck=_resolve_column(cols, _DECK_CANDIDATES, col_deck),
        traffic=_resolve_column(cols, _TRAFFIC_CANDIDATES, col_traffic),
    )

    zones: list[dict[str, Any]] = []
    for idx, row in gdf.iterrows():
        zone = _zone_from_row(row, idx, columns)
        if zone is not None:
            zones.append(zone)
    return zones


def _zone_from_row(
    row: Any,
    idx: int,
    columns: _ZoneColumns,
) -> dict[str, Any] | None:
    geom = row.geometry
    if geom is None or geom.is_empty:
        return None
    if not isinstance(geom, (Polygon, MultiPolygon)):
        return None

    centroid = geom.centroid
    zone_id = (
        str(row[columns.id])
        if columns.id and columns.id in row.index
        else f"Zone_{idx}"
    )
    zone_id = zone_id.replace(" ", "_")

    zone: dict[str, Any] = {
        "id": zone_id,
        "type": str(row[columns.type]) if columns.type and columns.type in row.index else _DEFAULT_ROOM_TYPE,
        "traffic": str(row[columns.traffic]).lower() if columns.traffic and columns.traffic in row.index else _DEFAULT_TRAFFIC,
        "volume_m3": float(row[columns.volume]) if columns.volume and columns.volume in row.index else _DEFAULT_VOLUME,
        "deck": str(row[columns.deck]).lower() if columns.deck and columns.deck in row.index else _DEFAULT_DECK,
        "display": {
            "x": round(centroid.x, 2),
            "y": round(centroid.y, 2),
        },
    }

    if columns.ach and columns.ach in row.index:
        zone["base_ach"] = float(row[columns.ach])

    return zone


# ── Line layers → HVAC / adjacency edges ────────────────────────────────

def _connected_zone_ids(
    single_line: LineString,
    poly_gdf: gpd.GeoDataFrame,
    zone_ids: list[str],
) -> list[str]:
    """Ordered, de-duplicated zone ids whose polygons the line intersects."""
    connected: list[str] = []
    for poly_idx, poly_row in poly_gdf.iterrows():
        poly_geom = poly_row.geometry
        if poly_geom is None or poly_geom.is_empty:
            continue
        if not single_line.intersects(poly_geom):
            continue
        pid = zone_ids[poly_idx] if poly_idx < len(zone_ids) else f"Zone_{poly_idx}"
        if pid not in connected:
            connected.append(pid)
    return connected


def _edge_attributes(
    line_row: Any,
    flow_col: str | None,
    ducted_col: str | None,
) -> tuple[float, bool]:
    """Flow rate and ducted flag for the edges traced from one line row."""
    flow_rate = _DEFAULT_FLOW_RATE
    if flow_col and flow_col in line_row.index:
        try:
            flow_rate = float(line_row[flow_col])
        except (ValueError, TypeError):
            # Retain the calibrated default for malformed flow data.
            pass

    is_ducted = False
    if ducted_col and ducted_col in line_row.index:
        val = line_row[ducted_col]
        is_ducted = bool(val) if not isinstance(val, str) else val.lower() in ("true", "yes", "1")

    return flow_rate, is_ducted


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
        edge_attrs = _edge_attributes(line_row, flow_col, ducted_col)
        _trace_line_edges(lines, poly_gdf, zone_ids, edge_attrs, G, adjacency)

    return _cross_zone_links(G), adjacency


def _trace_line_edges(
    lines: list[LineString],
    poly_gdf: gpd.GeoDataFrame,
    zone_ids: list[str],
    edge_attrs: tuple[float, bool],
    graph: nx.DiGraph,
    adjacency: list[dict[str, str]],
) -> None:
    flow_rate, is_ducted = edge_attrs
    for single_line in lines:
        connected = _connected_zone_ids(single_line, poly_gdf, zone_ids)

        for from_z, to_z in zip(connected, connected[1:]):
            if graph.has_edge(from_z, to_z):
                continue
            graph.add_edge(
                from_z, to_z,
                flow_rate_m3h=flow_rate,
                is_hvac_ducted=is_ducted,
            )
            adjacency.append({
                "from": from_z,
                "to": to_z,
                "type": "hvac_duct" if is_ducted else "passageway",
            })


def _cross_zone_links(graph: nx.DiGraph) -> list[dict[str, Any]]:
    cross_zone_links: list[dict[str, Any]] = []
    for u, v, data in graph.edges(data=True):
        cross_zone_links.append({
            "from": u,
            "to": v,
            "flow_rate_m3h": data["flow_rate_m3h"],
            "is_hvac_ducted": data["is_hvac_ducted"],
            "path": f"{u}_to_{v}",
        })
    return cross_zone_links


def _compute_polygon_adjacency(
    poly_gdf: gpd.GeoDataFrame,
    zone_ids: list[str],
) -> list[dict[str, str]]:
    """Compute adjacency from polygon touches/overlaps (no line layer)."""
    adjacency: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for i in range(len(poly_gdf)):
        _accumulate_adjacent_pairs(poly_gdf, zone_ids, i, seen, adjacency)

    return adjacency


def _accumulate_adjacent_pairs(
    poly_gdf: gpd.GeoDataFrame,
    zone_ids: list[str],
    i: int,
    seen: set[tuple[str, str]],
    adjacency: list[dict[str, str]],
) -> None:
    geom_i = poly_gdf.iloc[i].geometry
    if geom_i is None or geom_i.is_empty:
        return
    for j in range(i + 1, len(poly_gdf)):
        geom_j = poly_gdf.iloc[j].geometry
        if geom_j is None or geom_j.is_empty:
            continue
        if not (geom_i.touches(geom_j) or geom_i.intersects(geom_j)):
            continue
        a, b = zone_ids[i], zone_ids[j]
        if (a, b) in seen:
            continue
        seen.add((a, b))
        adjacency.append({"from": a, "to": b, "type": "passageway"})


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
    output_dir = resolve_repo_path(REPO_ROOT, output_dir)
    prepare_output_directory(output_dir, allowed_roots=(REPO_ROOT,))
    spatial_path = os.path.join(output_dir, "spatial_layout.json")
    airflow_path = os.path.join(output_dir, "air_flow_paths.json")

    with validated_open(spatial_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(spatial_layout, fh, indent=2, ensure_ascii=False)
    print(f"\n  Wrote: {spatial_path}")

    with validated_open(airflow_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
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
    columns = _ZoneColumns(
        id=_resolve_column(cols, _ID_CANDIDATES, None),
        type=_resolve_column(cols, _TYPE_CANDIDATES, None),
        volume=None,
        ach=None,
        deck=_resolve_column(cols, _DECK_CANDIDATES, None),
        traffic=None,
    )

    xs: list[float] = []
    ys: list[float] = []
    features = _compartment_features(poly_gdf, columns, xs, ys)
    features += _hvac_path_features(line_gdf, xs, ys)
    hull = _hull_outline_feature(xs, ys, pid)
    if hull is not None:
        features.insert(0, hull)

    collection = {"type": "FeatureCollection", "features": features}
    output_path = resolve_repo_path(REPO_ROOT, output_path)
    prepare_output_directory(os.path.dirname(output_path) or REPO_ROOT, allowed_roots=(REPO_ROOT,))
    with validated_open(output_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(collection, fh, indent=2, ensure_ascii=False)
    return output_path


def _ring_from_geom(geom: Any) -> list[list[float]] | None:
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    if not isinstance(geom, Polygon):
        return None
    ext = list(geom.exterior.coords)
    return [[float(x), float(y)] for x, y in ext]


def _compartment_props(
    row: Any,
    idx: int,
    columns: _ZoneColumns,
) -> dict[str, Any]:
    zid = (
        str(row[columns.id])
        if columns.id and columns.id in row.index
        else f"Zone_{idx}"
    )
    zid = zid.replace(" ", "_")
    props: dict[str, Any] = {
        "kind": "compartment",
        "zone_id": zid,
        "deck": (
            str(row[columns.deck])
            if columns.deck and columns.deck in row.index
            else "main"
        ),
    }
    if columns.type and columns.type in row.index:
        props["room_type"] = str(row[columns.type])
    return props


def _compartment_features(
    poly_gdf: gpd.GeoDataFrame,
    columns: _ZoneColumns,
    xs: list[float],
    ys: list[float],
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for idx, row in poly_gdf.iterrows():
        ring = _ring_from_geom(row.geometry)
        if not ring:
            continue
        xs.extend(pt[0] for pt in ring)
        ys.extend(pt[1] for pt in ring)
        features.append({
            "type": "Feature",
            "properties": _compartment_props(row, idx, columns),
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return features


def _linestring_coords(geom: Any) -> list[list[float]] | None:
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, MultiLineString):
        lines = list(geom.geoms)
        geom = lines[0] if lines else None
    if not isinstance(geom, LineString):
        return None
    return [[float(x), float(y)] for x, y in geom.coords]


def _hvac_path_features(
    line_gdf: gpd.GeoDataFrame,
    xs: list[float],
    ys: list[float],
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for _, row in line_gdf.iterrows():
        coords = _linestring_coords(row.geometry)
        if coords is None:
            continue
        xs.extend(pt[0] for pt in coords)
        ys.extend(pt[1] for pt in coords)
        features.append({
            "type": "Feature",
            "properties": {"kind": "hvac_path"},
            "geometry": {"type": "LineString", "coordinates": coords},
        })
    return features


def _hull_outline_feature(
    xs: list[float],
    ys: list[float],
    pid: str,
) -> dict[str, Any] | None:
    if not (xs and ys):
        return None
    pad = 3.0
    hull_ring = [
        [min(xs) - pad, min(ys) - pad],
        [max(xs) + pad, min(ys) - pad],
        [max(xs) + pad, max(ys) + pad],
        [min(xs) - pad, max(ys) + pad],
        [min(xs) - pad, min(ys) - pad],
    ]
    return {
        "type": "Feature",
        "properties": {"kind": "hull_outline", "platform_id": pid},
        "geometry": {"type": "Polygon", "coordinates": [hull_ring]},
    }


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

    input_path = resolve_repo_path(REPO_ROOT, args.input)
    output_dir = resolve_repo_path(REPO_ROOT, args.output)
    hvac_path = resolve_repo_path(REPO_ROOT, args.hvac) if args.hvac else None

    print("=" * 70)
    print("  GIS SPATIAL BRIDGE — Crusher Labs Layout Converter")
    print("=" * 70)

    convert(
        input_path=input_path,
        output_dir=output_dir,
        hvac_path=hvac_path,
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
            gfx_path = os.path.join(output_dir, "deck_graphics.geojson")
        else:
            gfx_path = resolve_repo_path(REPO_ROOT, gfx_path)
        emit_deck_graphics(input_path, gfx_path, platform_id=args.platform)
        print(f"  Wrote deck graphics: {gfx_path}")

    print("=" * 70)
    print("  Conversion complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
