#!/usr/bin/env python3
"""
contam_commissioned_check.py — hull -> solver commissioning proof.

Exports a platform's ``.prj`` with ``ahs_terminal_mode="commissioned"``
(per-room ``ach x V_room x duty`` Fahs on a constant schedule; exhaust-only
head-deck branches emit supply 0 / return ``ach x V``), solves it with the
local ContamX binary, and reports each terminal's solved flow against the
declared per-branch flow.

The check is two-layered:

1. ``declared`` — recomputed here from the platform JSON (independent of
   the emitter) and cross-checked against the emitter's own
   ``declared_flow_m3h`` in ``path_map``.
2. ``solved`` — ContamX ``Flow0`` volumetric for that path, required to sit
   inside ``--tolerance`` (relative, default 5%) of declared. ~0.3% is the
   observed density-conversion residue.

Usage::

    python3 tools/contam_commissioned_check.py
    python3 tools/contam_commissioned_check.py --platform destroyer_baseline \
        --platform expedition_cruise_450 --tolerance 0.05
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_runner import (  # noqa: E402
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from tools.contam_prj_bridge import export_platform_to_prj  # noqa: E402

DEFAULT_PLATFORMS = ("destroyer_baseline", "expedition_cruise_450")
_DEFAULT_TOLERANCE = 0.05
_ABS_EPS_M3H = 0.5  # near-zero legs: absolute slack below relative math
# Exports must live under the repo root (validated_open) but stay out of
# git — telemetry_buffer/ is the established gitignored scratch tree.
_DEFAULT_WORKDIR = os.path.join(
    REPO_ROOT, "telemetry_buffer", "contam_commissioned",
)


def _load_platform(platform: str) -> tuple[str, dict, dict]:
    platform_dir = os.path.join(REPO_ROOT, "data", "platforms", platform)
    with open(
        os.path.join(platform_dir, "spatial_layout.json"), encoding="utf-8",
    ) as fh:
        spatial = json.load(fh)
    with open(
        os.path.join(platform_dir, "air_flow_paths.json"), encoding="utf-8",
    ) as fh:
        airflow = json.load(fh)
    return platform_dir, spatial, airflow


def _room_volume(spatial: dict, room: str) -> float:
    for zone in spatial.get("zones", []):
        if zone["id"] == room:
            if zone.get("volume_m3") is not None:
                return float(zone["volume_m3"])
            area = float(zone.get("floor_area_m2") or 0.0)
            height = float(zone.get("ceiling_height_m") or 0.0)
            return area * height
    raise KeyError(f"room {room!r} not in spatial_layout")


def declared_terminal_flows(
    spatial: dict, airflow: dict,
) -> dict[str, dict[str, float]]:
    """Independent recomputation of the declared per-branch field.

    Returns ``{room: {"supply": m3h, "return": m3h}}`` for every room of
    every hvac_zone: ``ach x V x duty`` on balanced branches; supply 0 /
    return ``ach x V`` on exhaust-only branches (``hvac_duty`` <= 0).
    """
    default_duty = float(airflow.get("hvac_duty", 1.0) or 0.0)
    declared: dict[str, dict[str, float]] = {}
    for hz in airflow.get("hvac_zones", []):
        ach = float(hz.get("ach", 6.0))
        raw_duty = hz.get("hvac_duty")
        duty = default_duty if raw_duty is None else float(raw_duty)
        for room in hz.get("rooms", []):
            vol = _room_volume(spatial, room)
            if duty <= 0.0:
                declared[room] = {"supply": 0.0, "return": ach * vol}
            else:
                declared[room] = {"supply": ach * vol * duty,
                                  "return": ach * vol * duty}
    return declared


def _check_emission(
    path_map: list[dict], declared: dict[str, dict[str, float]],
) -> list[str]:
    """Emitter self-consistency: path_map declared == recomputed declared."""
    errors: list[str] = []
    for entry in path_map:
        kind = entry.get("kind")
        if kind not in ("ahs_supply", "ahs_return"):
            continue
        room = entry["to_zone"] if kind == "ahs_supply" else entry["from_zone"]
        emitted = float(entry.get("declared_flow_m3h", -1.0))
        expected = declared[room]["supply" if kind == "ahs_supply" else "return"]
        if abs(emitted - expected) > _ABS_EPS_M3H:
            errors.append(
                f"emitter mismatch {entry['path_nr']} {kind} {room}: "
                f"path_map declared {emitted:.2f} != recomputed {expected:.2f}"
            )
    return errors


def _check_solved(
    path_map: list[dict],
    declared: dict[str, dict[str, float]],
    flows_m3h: dict[int, float],
    tolerance: float,
) -> tuple[list[str], list[str]]:
    """Compare solved Flow0 vs declared per terminal."""
    errors: list[str] = []
    rows: list[str] = []
    for entry in path_map:
        kind = entry.get("kind")
        if kind not in ("ahs_supply", "ahs_return"):
            continue
        room = entry["to_zone"] if kind == "ahs_supply" else entry["from_zone"]
        leg = "supply" if kind == "ahs_supply" else "return"
        want = declared[room][leg]
        got = abs(float(flows_m3h.get(int(entry["path_nr"]), 0.0)))
        if want <= _ABS_EPS_M3H:
            ok = got <= _ABS_EPS_M3H
            ratio = float("nan") if got <= _ABS_EPS_M3H else float("inf")
        else:
            ratio = got / want
            ok = abs(ratio - 1.0) <= tolerance
        flag = "" if ok else "  <-- OUT OF TOLERANCE"
        rows.append(
            f"  p{entry['path_nr']:>3} ahs{entry.get('ahs_nr', 0):>2} "
            f"{leg:<6} {room:<16} declared={want:10.2f} "
            f"solved={got:10.2f} ratio={ratio:6.3f}{flag}"
        )
        if not ok:
            errors.append(
                f"terminal p{entry['path_nr']} {leg} {room}: solved {got:.2f} "
                f"vs declared {want:.2f} outside tolerance {tolerance:.0%}"
            )
    return errors, rows


def check_platform(
    platform: str,
    workdir: str,
    *,
    tolerance: float,
    solve: bool,
) -> list[str]:
    """Run the commissioning check for one platform; returns error strings."""
    errors: list[str] = []
    platform_dir, spatial, airflow = _load_platform(platform)
    declared = declared_terminal_flows(spatial, airflow)

    prj_path = os.path.join(workdir, f"{platform}.prj")
    export_platform_to_prj(
        platform_dir, prj_path,
        write_path_map=True, hobbyist=True,
        ahs_terminal_mode="commissioned",
    )
    map_path = os.path.splitext(prj_path)[0] + ".path_map.json"
    with open(map_path, encoding="utf-8") as fh:
        path_map = json.load(fh)
    print(f"[{platform}] emitted {prj_path} "
          f"({len(path_map)} paths, {len(declared)} declared rooms)")

    errors.extend(_check_emission(path_map, declared))
    if not solve:
        return errors

    try:
        sim_path = run_contamx(prj_path)
    except ContamXUnavailable as exc:
        errors.append(f"{platform}: ContamX solve failed: {exc}")
        return errors
    flows = SimResults(
        sim_path, allowed_roots=(REPO_ROOT,),
    ).path_volumetric_flow_m3h()
    solved_errors, rows = _check_solved(path_map, declared, flows, tolerance)
    print(f"[{platform}] solved {sim_path}:")
    for row in rows:
        print(row)
    errors.extend(solved_errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Hull -> solver commissioning check for authored .prj.",
    )
    parser.add_argument(
        "--platform", action="append", dest="platforms",
        help="Platform id under data/platforms/ (repeatable). "
             f"Default: {', '.join(DEFAULT_PLATFORMS)}",
    )
    parser.add_argument(
        "--tolerance", type=float, default=_DEFAULT_TOLERANCE,
        help="Relative solved-vs-declared tolerance (default 0.05).",
    )
    parser.add_argument(
        "--emit-only", action="store_true",
        help="Check emission only; skip the ContamX solve.",
    )
    parser.add_argument(
        "--workdir", default=_DEFAULT_WORKDIR,
        help="Directory for emitted .prj/.sim artifacts "
             f"(default {_DEFAULT_WORKDIR}).",
    )
    args = parser.parse_args(argv)
    platforms = args.platforms or list(DEFAULT_PLATFORMS)

    solve = not args.emit_only
    if solve and find_contamx() is None:
        print("ERROR: no ContamX binary (CONTAMX_BINARY / third_party/contamx)")
        return 2

    os.makedirs(args.workdir, exist_ok=True)
    errors: list[str] = []
    for platform in platforms:
        errors.extend(
            check_platform(
                platform, args.workdir,
                tolerance=args.tolerance, solve=solve,
            )
        )

    if errors:
        print("\nFAILED:")
        for err in errors:
            print(f"  {err}")
        return 1
    print("\nPASS: every commissioned terminal solved inside "
          f"{args.tolerance:.0%} of declared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
