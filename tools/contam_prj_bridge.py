#!/usr/bin/env python3
"""
contam_prj_bridge.py – CONTAM ``.prj`` import/export bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Translates between this project's native JSON contracts
(``spatial_layout.json`` + ``air_flow_paths.json``) and NIST CONTAM
``.prj`` project files.

**Export (default)** writes ContamW **3.4** grammar that ContamX can parse,
plus a ``path_map.json`` sidecar aligning ContamX path indices to Crusher
zone pairs. See ``tools/contamw34_prj.py``.

**Simplify** reads authentic ContamW 3.4 projects into simplified platform
JSON (Path B — native solver). Controls, schedules, wind, ducts, and
sources are dropped.

**Import** still accepts the legacy Crusher interchange dialect
(``!------`` section headers) for older files.

CONTAM docs: NIST TN 1887r1 —
https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1887r1.pdf

Usage::

    python tools/contam_prj_bridge.py --export \\
        --platform data/platforms/mega_cruise_5000 \\
        --output data/platforms/mega_cruise_5000/contam/platform.prj

    python tools/contam_prj_bridge.py --simplify \\
        --input path/to/full.prj \\
        --output data/platforms/imported_from_contam/

    python tools/contam_prj_bridge.py --import \\
        --input legacy_interchange.prj \\
        --output data/platforms/imported_legacy/
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
from tools.contamw34_prj import (  # noqa: E402
    PRJ_SIGNATURE_34,
    export_contamw34,
    simplify_contamw34,
)

# Legacy interchange signature (still parsed by import_prj)
PRJ_SIGNATURE = "ContamW 3.1"
# ContamW 3.4 export signature
PRJ_SIGNATURE_CONTAMW34 = PRJ_SIGNATURE_34

_SENTINEL = "-999"
_NONE_TOKEN = "*"
_DEFAULT_CEILING_HEIGHT_M = 3.0
_DEFAULT_ZONE_TEMP_K = 293.15

_SPATIAL_LAYOUT_JSON = "spatial_layout.json"
_AIR_FLOW_PATHS_JSON = "air_flow_paths.json"
_PATH_MAP_JSON = "path_map.json"


# ── token helpers ────────────────────────────────────────────────────────

def _tok(value: Any) -> str:
    if value is None:
        return _NONE_TOKEN
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    return text.replace(" ", "_") if text else _NONE_TOKEN


def _num(token: str) -> float | None:
    if token == _NONE_TOKEN:
        return None
    return float(token)


def _int_or_zero(token: str) -> int:
    if token == _NONE_TOKEN:
        return 0
    return int(float(token))


def _clean_float(value: float) -> float | int:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# ── ContamW 3.4 export (primary) ─────────────────────────────────────────

def export_prj(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> str:
    """Serialize platform JSON to ContamW 3.4 ``.prj`` text."""
    text, _path_map = export_contamw34(spatial_layout, air_flow_paths)
    return text


def export_prj_with_path_map(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """Serialize to ContamW 3.4 ``.prj`` text and path_map entries."""
    return export_contamw34(spatial_layout, air_flow_paths)


# ── Legacy interchange export (tests / old tooling) ──────────────────────

def _build_levels(zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def export_prj_interchange(
    spatial_layout: dict[str, Any], air_flow_paths: dict[str, Any],
) -> str:
    """Legacy Crusher ``!------`` interchange dialect (not ContamX-parseable)."""
    zones = spatial_layout.get("zones", [])
    platform = spatial_layout.get("platform", "crusher_platform")

    levels = _build_levels(zones)
    level_index = {lvl["name"]: i + 1 for i, lvl in enumerate(levels)}

    lines: list[str] = []
    lines.append(PRJ_SIGNATURE)
    lines.append(_tok(platform) + "  ! project description (platform id)")
    lines.append("! Crusher-to-the-Bridge <-> CONTAM interchange")
    lines.append("! Generated by tools/contam_prj_bridge.py")

    lines.append("!------ levels ------")
    lines.append(str(len(levels)))
    lines.append("! nr  refht[m]  delht[m]  name")
    for i, lvl in enumerate(levels, start=1):
        lines.append(
            f"{i} {_tok(lvl['refht'])} {_tok(lvl['delht'])} {_tok(lvl['name'])}"
        )
    lines.append(_SENTINEL)

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


# ── parsing (legacy interchange) ─────────────────────────────────────────

def _iter_records(lines: list[str], start: int) -> tuple[list[list[str]], int]:
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
    """Parse CONTAM ``.prj`` text into (spatial_layout, air_flow_paths).

    Auto-detects ContamW 3.4 grammar vs legacy Crusher interchange.
    """
    if "!------ levels" in text or "!------ zones" in text:
        return _import_interchange(text)
    return simplify_contamw34(text)


def _import_interchange(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
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
            rows, i = _iter_records(lines, i + 1)
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
                        {
                            "id": row[1],
                            "rooms": rooms,
                            "ach": _clean_float(float(row[2])),
                        }
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

def export_platform_to_prj(
    platform_dir: str,
    output_path: str,
    *,
    write_path_map: bool = True,
) -> str:
    """Read a platform directory and write a ContamW 3.4 ``.prj`` (+ path_map)."""
    platform_dir = resolve_repo_path(REPO_ROOT, platform_dir)
    spatial_path = os.path.join(platform_dir, _SPATIAL_LAYOUT_JSON)
    airflow_path = os.path.join(platform_dir, _AIR_FLOW_PATHS_JSON)

    with validated_open(
        spatial_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        spatial_layout = json.load(fh)
    with validated_open(
        airflow_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        air_flow_paths = json.load(fh)

    prj_text, path_map = export_prj_with_path_map(spatial_layout, air_flow_paths)

    output_path = resolve_repo_path(REPO_ROOT, output_path)
    prepare_output_directory(
        os.path.dirname(output_path) or REPO_ROOT, allowed_roots=(REPO_ROOT,),
    )
    with validated_open(
        output_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        fh.write(prj_text)

    if write_path_map:
        map_path = os.path.join(os.path.dirname(output_path), _PATH_MAP_JSON)
        # If output is explicitly named, keep path_map beside it
        if os.path.basename(output_path) != "platform.prj":
            stem = os.path.splitext(output_path)[0]
            map_path = stem + ".path_map.json"
        with validated_open(
            map_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(path_map, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    return output_path


def import_prj_to_platform(input_path: str, output_dir: str) -> tuple[str, str]:
    """Read a CONTAM ``.prj`` and write platform JSON (auto-detect dialect)."""
    input_path = resolve_repo_path(REPO_ROOT, input_path)
    with validated_open(
        input_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        text = fh.read()

    spatial_layout, air_flow_paths = import_prj(text)
    return _write_platform_json(spatial_layout, air_flow_paths, output_dir)


def simplify_prj_to_platform(input_path: str, output_dir: str) -> tuple[str, str]:
    """Force ContamW 3.4 simplify path (Path B)."""
    input_path = resolve_repo_path(REPO_ROOT, input_path)
    with validated_open(
        input_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        text = fh.read()
    warn: list[str] = []
    spatial_layout, air_flow_paths = simplify_contamw34(text, warnings_out=warn)
    for w in warn:
        print(f"  warning: {w}")
    return _write_platform_json(spatial_layout, air_flow_paths, output_dir)


def _write_platform_json(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
    output_dir: str,
) -> tuple[str, str]:
    output_dir = resolve_repo_path(REPO_ROOT, output_dir)
    prepare_output_directory(output_dir, allowed_roots=(REPO_ROOT,))
    spatial_path = os.path.join(output_dir, _SPATIAL_LAYOUT_JSON)
    airflow_path = os.path.join(output_dir, _AIR_FLOW_PATHS_JSON)

    with validated_open(
        spatial_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        json.dump(spatial_layout, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with validated_open(
        airflow_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        json.dump(air_flow_paths, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return spatial_path, airflow_path


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import/export between Crusher-to-the-Bridge platform JSON "
                    "and ContamW 3.4 / legacy CONTAM .prj files.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--export", action="store_true",
        help="Export a platform directory to a ContamW 3.4 .prj (+ path_map)",
    )
    mode.add_argument(
        "--import", dest="do_import", action="store_true",
        help="Import a .prj (auto-detect ContamW 3.4 vs legacy interchange)",
    )
    mode.add_argument(
        "--simplify", action="store_true",
        help="Simplify an authentic ContamW 3.4 .prj into platform JSON",
    )
    parser.add_argument(
        "--platform", "-p",
        help="Platform directory to export (with --export)",
    )
    parser.add_argument(
        "--input", "-i",
        help="Input CONTAM .prj file (--import / --simplify)",
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Output .prj (--export) or output directory (--import/--simplify)",
    )
    args = parser.parse_args(argv)

    if args.export:
        if not args.platform:
            parser.error("--export requires --platform")
        out = export_platform_to_prj(args.platform, args.output)
        print(f"  Wrote ContamW 3.4 project file: {out}")
        return 0

    if not args.input:
        parser.error("--import/--simplify requires --input")

    if args.simplify:
        spatial_path, airflow_path = simplify_prj_to_platform(
            args.input, args.output,
        )
    else:
        spatial_path, airflow_path = import_prj_to_platform(
            args.input, args.output,
        )
    print(f"  Wrote: {spatial_path}")
    print(f"  Wrote: {airflow_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
