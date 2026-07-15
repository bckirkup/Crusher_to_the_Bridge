#!/usr/bin/env python3
"""
contam_prj_bridge.py – CONTAM ``.prj`` import/export bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Translates between this project's native JSON contracts
(``spatial_layout.json`` + ``air_flow_paths.json``) and the NIST CONTAM
multizone ``.prj`` project-file format so that a Crusher-to-the-Bridge
platform can be opened as a CONTAM floor plan in ContamW, and a CONTAM
project can be re-imported as a platform.

CONTAM (NIST multizone airflow / contaminant transport) is documented in
NIST Technical Note 1887r1 ("CONTAM User Guide and Program Documentation
Version 3.4"): https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1887r1.pdf

Concept crosswalk (see ``docs/CONTAM_INTEROP.md`` for the full table):

    Crusher JSON term                CONTAM concept
    ------------------------------   -----------------------------------
    zone (spatial_layout)            CONTAM zone (airflow node)
    volume_m3                        zone volume (area x ceiling height)
    floor_area_m2 / ceiling_height_m CONTAM zone floor area / level height
    elevation_m                      relative level elevation
    adjacency (air_flow_paths)       CONTAM airflow path (opening element)
    hvac_zones                       CONTAM simple air-handling system (AHS)
    ach                              air change rate
    cross_zone_links                 inter-AHS ducted/passive links
    filter_efficiency                CONTAM filter element

Why a hand-written serializer:
    The sibling ``py-contam`` repository (see the docstring of
    ``engines/py_contam_bridge.py`` and ``docs/OPERATORS_MANUAL.md`` 11.3)
    only ships a *binary* ``.sim`` results reader (``contam_output.py``) and
    weather/species file writers (``contam_input.py``) — it contains no
    ``.prj`` reader or writer to reuse.  Sibling repositories are read-only
    (Law 6), so this module implements a self-contained CONTAM ``.prj``
    ASCII serializer / parser here.

The emitted file follows the documented CONTAM 3.x project-file layout
(a ``ContamW`` signature line followed by ``!``-delimited sections closed
by ``-999`` sentinels).  The importer parses the same sections, so the
JSON -> .prj -> JSON round-trip preserves zone identity, geometry, and the
full airflow graph (hvac_zones, cross_zone_links, adjacency).

Usage::

    # Export a platform directory to a CONTAM .prj
    python tools/contam_prj_bridge.py --export \\
        --platform data/platforms/destroyer_baseline \\
        --output out/destroyer_baseline.prj

    # Import a CONTAM .prj back into spatial_layout.json + air_flow_paths.json
    python tools/contam_prj_bridge.py --import \\
        --input out/destroyer_baseline.prj \\
        --output data/platforms/imported_from_contam/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.py_contam_bridge import derive_volume_m3  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)

PRJ_SIGNATURE = "ContamW 3.1"
_SENTINEL = "-999"
_NONE_TOKEN = "*"  # marks an absent optional numeric field
_DEFAULT_CEILING_HEIGHT_M = 3.0
_DEFAULT_ZONE_TEMP_K = 293.15

_SPATIAL_LAYOUT_JSON = "spatial_layout.json"
_AIR_FLOW_PATHS_JSON = "air_flow_paths.json"


# ── token helpers ────────────────────────────────────────────────────────

def _tok(value: Any) -> str:
    """Serialize a single whitespace-free token (``*`` marks ``None``)."""
    if value is None:
        return _NONE_TOKEN
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    return text.replace(" ", "_") if text else _NONE_TOKEN


def _num(token: str) -> float | None:
    """Parse an optional float token (``*`` -> ``None``)."""
    if token == _NONE_TOKEN:
        return None
    return float(token)


def _int_or_zero(token: str) -> int:
    if token == _NONE_TOKEN:
        return 0
    return int(float(token))


def _clean_float(value: float) -> float | int:
    """Render whole numbers without a trailing ``.0`` for JSON tidiness."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# ── section writers ──────────────────────────────────────────────────────

def _build_levels(zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group zones into CONTAM levels by deck.

    Each distinct ``deck`` becomes a CONTAM level whose reference elevation
    is the minimum ``elevation_m`` among its zones (0.0 when none specify
    one) and whose height is the maximum ``ceiling_height_m`` among its
    zones (falling back to the default ceiling height).
    """
    order: list[str] = []
    members: dict[str, list[dict[str, Any]]] = {}
    for zone in zones:
        deck = str(zone.get("deck", "main"))
        if deck not in members:
            members[deck] = []
            order.append(deck)
        members[deck].append(zone)

    levels: list[dict[str, Any]] = []
    for deck in order:
        elevations = [
            z["elevation_m"] for z in members[deck]
            if z.get("elevation_m") is not None
        ]
        heights = [
            z["ceiling_height_m"] for z in members[deck]
            if z.get("ceiling_height_m") is not None
        ]
        refht = min(elevations) if elevations else 0.0
        delht = max(heights) if heights else _DEFAULT_CEILING_HEIGHT_M
        levels.append({"name": deck, "refht": float(refht), "delht": float(delht)})
    return levels


def export_prj(spatial_layout: dict[str, Any], air_flow_paths: dict[str, Any]) -> str:
    """Serialize a platform's JSON contracts into CONTAM ``.prj`` text."""
    zones = spatial_layout.get("zones", [])
    platform = spatial_layout.get("platform", "crusher_platform")

    levels = _build_levels(zones)
    level_index = {lvl["name"]: i + 1 for i, lvl in enumerate(levels)}

    lines: list[str] = []
    lines.append(PRJ_SIGNATURE)
    lines.append(_tok(platform) + "  ! project description (platform id)")
    lines.append("! Crusher-to-the-Bridge <-> CONTAM interchange")
    lines.append("! Generated by tools/contam_prj_bridge.py")

    # ── levels ────────────────────────────────────────────────────────────
    lines.append("!------ levels ------")
    lines.append(str(len(levels)))
    lines.append("! nr  refht[m]  delht[m]  name")
    for i, lvl in enumerate(levels, start=1):
        lines.append(
            f"{i} {_tok(lvl['refht'])} {_tok(lvl['delht'])} {_tok(lvl['name'])}"
        )
    lines.append(_SENTINEL)

    # ── zones ─────────────────────────────────────────────────────────────
    lines.append("!------ zones ------")
    lines.append(str(len(zones)))
    lines.append(
        "! nr  lev  vol[m3]  area[m2]  ht[m]  elev[m]  T0[K]  x  y  "
        "type  traffic  deck  name"
    )
    for i, zone in enumerate(zones, start=1):
        floor_area = zone.get("floor_area_m2")
        ceiling_height = zone.get("ceiling_height_m")
        elevation = zone.get("elevation_m")
        volume = derive_volume_m3(
            zone.get("volume_m3"), floor_area, ceiling_height,
        )
        deck = str(zone.get("deck", "main"))
        display = zone.get("display", {}) or {}
        lines.append(
            f"{i} {level_index.get(deck, 1)} {_tok(float(volume))} "
            f"{_tok(floor_area)} {_tok(ceiling_height)} {_tok(elevation)} "
            f"{_tok(_DEFAULT_ZONE_TEMP_K)} "
            f"{_tok(display.get('x'))} {_tok(display.get('y'))} "
            f"{_tok(zone.get('type', 'Free'))} "
            f"{_tok(zone.get('traffic', 'medium'))} "
            f"{_tok(deck)} {_tok(zone['id'])}"
        )
    lines.append(_SENTINEL)

    # ── airflow paths (from adjacency edges) ───────────────────────────────
    adjacency = air_flow_paths.get("adjacency", [])
    lines.append("!------ flow paths (adjacency openings) ------")
    lines.append(str(len(adjacency)))
    lines.append("! nr  from  to  type")
    for i, adj in enumerate(adjacency, start=1):
        lines.append(
            f"{i} {_tok(adj['from'])} {_tok(adj['to'])} "
            f"{_tok(adj.get('type', 'passageway'))}"
        )
    lines.append(_SENTINEL)

    # ── air-handling systems (from hvac_zones) ─────────────────────────────
    hvac_zones = air_flow_paths.get("hvac_zones", [])
    lines.append("!------ air-handling systems (hvac_zones) ------")
    lines.append(str(len(hvac_zones)))
    lines.append("! nr  id  ach  rooms(csv)")
    for i, hz in enumerate(hvac_zones, start=1):
        rooms = ",".join(hz.get("rooms", [])) or _NONE_TOKEN
        lines.append(
            f"{i} {_tok(hz['id'])} {_tok(float(hz.get('ach', 6.0)))} {rooms}"
        )
    lines.append(_SENTINEL)

    # ── inter-system links (from cross_zone_links) ─────────────────────────
    cross_links = air_flow_paths.get("cross_zone_links", [])
    lines.append("!------ inter-system links (cross_zone_links) ------")
    lines.append(str(len(cross_links)))
    lines.append("! nr  from  to  flow[m3h]  ducted  path")
    for i, link in enumerate(cross_links, start=1):
        lines.append(
            f"{i} {_tok(link['from'])} {_tok(link['to'])} "
            f"{_tok(float(link.get('flow_rate_m3h', 50.0)))} "
            f"{_tok(bool(link.get('is_hvac_ducted', False)))} "
            f"{_tok(link.get('path'))}"
        )
    lines.append(_SENTINEL)

    return "\n".join(lines) + "\n"


# ── parsing ────────────────────────────────────────────────────────────────

def _iter_records(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    """Collect token rows from *start* until the ``-999`` sentinel.

    Skips comment (``!``) and blank lines.  Returns (rows, index_after
    sentinel).
    """
    rows: list[list[str]] = []
    i = start
    while i < len(lines):
        raw = lines[i].strip()
        i += 1
        if not raw or raw.startswith("!"):
            continue
        if raw == _SENTINEL:
            break
        rows.append(raw.split())
    return rows, i


def import_prj(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse CONTAM ``.prj`` text into (spatial_layout, air_flow_paths)."""
    lines = text.splitlines()
    if not lines or not lines[0].strip().startswith("ContamW"):
        raise ValueError(
            "Not a recognized CONTAM .prj file (missing 'ContamW' signature)"
        )

    platform = "imported_platform"
    zones: list[dict[str, Any]] = []
    adjacency: list[dict[str, str]] = []
    hvac_zones: list[dict[str, Any]] = []
    cross_zone_links: list[dict[str, Any]] = []
    levels: dict[int, str] = {}

    # project description is the first non-comment line after the signature
    for raw in lines[1:]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("!"):
            continue
        platform = stripped.split()[0]
        break

    i = 0
    while i < len(lines):
        header = lines[i].strip()
        i += 1
        if not header.startswith("!------"):
            continue

        if header.startswith("!------ levels"):
            rows, i = _iter_records(lines, i + 1)  # +1 skips the count line
            for row in rows:
                if len(row) >= 4:
                    levels[int(row[0])] = row[3]
        elif header.startswith("!------ zones"):
            rows, i = _iter_records(lines, i + 1)
            for row in rows:
                zones.append(_parse_zone_row(row, levels))
        elif header.startswith("!------ flow paths"):
            rows, i = _iter_records(lines, i + 1)
            for row in rows:
                if len(row) >= 4:
                    adjacency.append(
                        {"from": row[1], "to": row[2], "type": row[3]}
                    )
        elif header.startswith("!------ air-handling systems"):
            rows, i = _iter_records(lines, i + 1)
            for row in rows:
                if len(row) >= 3:
                    rooms_tok = row[3] if len(row) >= 4 else _NONE_TOKEN
                    rooms = [] if rooms_tok == _NONE_TOKEN else rooms_tok.split(",")
                    hvac_zones.append(
                        {"id": row[1], "rooms": rooms, "ach": _clean_float(float(row[2]))}
                    )
        elif header.startswith("!------ inter-system links"):
            rows, i = _iter_records(lines, i + 1)
            for row in rows:
                if len(row) >= 5:
                    link: dict[str, Any] = {
                        "from": row[1],
                        "to": row[2],
                        "flow_rate_m3h": _clean_float(float(row[3])),
                        "is_hvac_ducted": row[4] == "1",
                    }
                    if len(row) >= 6 and row[5] != _NONE_TOKEN:
                        link["path"] = row[5]
                    cross_zone_links.append(link)

    spatial_layout: dict[str, Any] = {
        "platform": platform,
        "description": f"Imported from CONTAM .prj ({platform})",
        "zones": zones,
    }
    graywater = [zones[0]["id"]] if zones else []
    if graywater:
        spatial_layout["graywater_zones"] = graywater

    air_flow_paths: dict[str, Any] = {
        "platform": platform,
        "description": f"Imported from CONTAM .prj ({platform})",
        "hvac_zones": hvac_zones,
        "cross_zone_links": cross_zone_links,
        "adjacency": adjacency,
    }
    return spatial_layout, air_flow_paths


def _parse_zone_row(row: list[str], levels: dict[int, str]) -> dict[str, Any]:
    """Parse a single zone record row into a spatial_layout zone dict.

    Column order matches the exporter:
    ``nr lev vol area ht elev T0 x y type traffic deck name``
    """
    lev = _int_or_zero(row[1])
    volume = _num(row[2])
    floor_area = _num(row[3])
    ceiling_height = _num(row[4])
    elevation = _num(row[5])
    x = _num(row[7])
    y = _num(row[8])
    zone_type = row[9]
    traffic = row[10]
    deck = row[11] if row[11] != _NONE_TOKEN else levels.get(lev, "main")
    name = row[12]

    resolved_volume = derive_volume_m3(volume, floor_area, ceiling_height)
    zone: dict[str, Any] = {
        "id": name,
        "type": zone_type,
        "traffic": traffic,
        "volume_m3": _clean_float(resolved_volume),
        "deck": deck,
        "display": {"x": _clean_float(x or 0.0), "y": _clean_float(y or 0.0)},
    }
    if floor_area is not None:
        zone["floor_area_m2"] = _clean_float(floor_area)
    if ceiling_height is not None:
        zone["ceiling_height_m"] = _clean_float(ceiling_height)
    if elevation is not None:
        zone["elevation_m"] = _clean_float(elevation)
    return zone


# ── file-level convenience wrappers ────────────────────────────────────────

def export_platform_to_prj(platform_dir: str, output_path: str) -> str:
    """Read a platform directory and write a CONTAM ``.prj`` file."""
    platform_dir = resolve_repo_path(REPO_ROOT, platform_dir)
    spatial_path = os.path.join(platform_dir, _SPATIAL_LAYOUT_JSON)
    airflow_path = os.path.join(platform_dir, _AIR_FLOW_PATHS_JSON)

    with validated_open(spatial_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        spatial_layout = json.load(fh)
    with validated_open(airflow_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        air_flow_paths = json.load(fh)

    prj_text = export_prj(spatial_layout, air_flow_paths)

    output_path = resolve_repo_path(REPO_ROOT, output_path)
    prepare_output_directory(
        os.path.dirname(output_path) or REPO_ROOT, allowed_roots=(REPO_ROOT,),
    )
    with validated_open(output_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        fh.write(prj_text)
    return output_path


def import_prj_to_platform(input_path: str, output_dir: str) -> tuple[str, str]:
    """Read a CONTAM ``.prj`` file and write the two platform JSON files."""
    input_path = resolve_repo_path(REPO_ROOT, input_path)
    with validated_open(input_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        text = fh.read()

    spatial_layout, air_flow_paths = import_prj(text)

    output_dir = resolve_repo_path(REPO_ROOT, output_dir)
    prepare_output_directory(output_dir, allowed_roots=(REPO_ROOT,))
    spatial_path = os.path.join(output_dir, _SPATIAL_LAYOUT_JSON)
    airflow_path = os.path.join(output_dir, _AIR_FLOW_PATHS_JSON)

    with validated_open(spatial_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(spatial_layout, fh, indent=2, ensure_ascii=False)
    with validated_open(airflow_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(air_flow_paths, fh, indent=2, ensure_ascii=False)
    return spatial_path, airflow_path


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import/export between Crusher-to-the-Bridge platform JSON "
                    "and CONTAM .prj project files.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--export", action="store_true",
        help="Export a platform directory to a CONTAM .prj file",
    )
    mode.add_argument(
        "--import", dest="do_import", action="store_true",
        help="Import a CONTAM .prj file into platform JSON files",
    )
    parser.add_argument(
        "--platform", "-p",
        help="Platform directory to export (with --export)",
    )
    parser.add_argument(
        "--input", "-i",
        help="Input CONTAM .prj file to import (with --import)",
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Output .prj file (--export) or output directory (--import)",
    )
    args = parser.parse_args(argv)

    if args.export:
        if not args.platform:
            parser.error("--export requires --platform")
        out = export_platform_to_prj(args.platform, args.output)
        print(f"  Wrote CONTAM project file: {out}")
    else:
        if not args.input:
            parser.error("--import requires --input")
        spatial_path, airflow_path = import_prj_to_platform(args.input, args.output)
        print(f"  Wrote: {spatial_path}")
        print(f"  Wrote: {airflow_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
