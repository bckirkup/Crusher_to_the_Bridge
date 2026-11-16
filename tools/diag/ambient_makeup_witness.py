#!/usr/bin/env python3
"""Before/after witness bundle for make-up ``ambient_openings`` stages.

CONTAM-AMBIENT-MAKEUP-CRUISE-01 (proposal
``docs/proposals/ambient_exposure_audit_and_fix_plan.md`` §6, stage 3).  Runs
the four committed witnesses on each hull as the tree stands and writes one
summary, so the same command on the base tree and on the changed tree gives
the before/after pair:

* ``contam_pressure_balance_diagnostic.py`` — design, commissioned and
  authored lanes, every path row, material-time cells for the hull's sources
* ``contam_flow_compare.py --run-contamx`` — native vs field per-path flows
* ``contam_paired_diagnostic.py`` — where the tool supports the hull
* ``forced_exhaust_audit.py exact-check``

The summary also carries the D5 reading: per ``ambient_opening`` leg the
solved ``Flow0`` and ``dP``, and per hull and lane the outward and inward
totals.  Outward is what the field lane removes contaminant with (the
boundary-sink rule); inward is clean make-up air.

Diagnostic only: nothing under ``data/`` is written.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

_SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPT_ROOT)

from simulation_utils.paths import (  # noqa: E402
    REPO_ROOT,
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)

CRUISE_HULLS = (
    "classic_cruise_1900",
    "diamond_princess",
    "expedition_cruise_450",
    "greg_mortimer",
    "mega_cruise_5000",
    "spirit_cruise_3000",
)
# Witness source zones: the dining room the galley transfer air is drawn
# from, and the zone the prescribed exhaust sink leaves.
SOURCES = {
    "classic_cruise_1900": ("MainDining_L", "MainGalley"),
    "diamond_princess": ("International", "MainGalley"),
    "expedition_cruise_450": ("MainDining", "MainGalley"),
    "greg_mortimer": ("DiningRoom", "MainGalley"),
    "mega_cruise_5000": ("MainDining_L", "Windjammer"),
    "spirit_cruise_3000": ("MainDining_L", "MainGalley"),
}
PAIRED_HULLS = ("expedition_cruise_450",)
LANES = ("design", "commissioned", "authored")
OPENING_KIND = "ambient_opening"
_DIAG = os.path.join("tools", "diag")
_TOOLS = {
    "pressure": os.path.join(_DIAG, "contam_pressure_balance_diagnostic.py"),
    "paired": os.path.join(_DIAG, "contam_paired_diagnostic.py"),
    "exact": os.path.join(_DIAG, "forced_exhaust_audit.py"),
    "compare": os.path.join("tools", "contam_flow_compare.py"),
}


def _run(tool: str, *args: str) -> None:
    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, _TOOLS[tool]), *args],
        cwd=REPO_ROOT, check=True, stdout=subprocess.DEVNULL,
    )


def _load(rel_path: str) -> Any:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def opening_summary(paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Solved flow through the ``ambient_opening`` legs of one field."""
    legs = [p for p in paths if p["kind"] == OPENING_KIND]
    flows = [float(p["flow_m3h"]) for p in legs]
    return {
        "legs": [
            {k: p[k] for k in ("path_nr", "from_zone", "flow_m3h", "dp_pa")}
            for p in legs
        ],
        "outward_m3h": sum(f for f in flows if f > 0.0),
        "inward_m3h": -sum(f for f in flows if f < 0.0),
        "max_abs_dp_pa": max((abs(float(p["dp_pa"])) for p in legs), default=None),
    }


def _class_max(row: dict[str, Any], path_class: str) -> float | None:
    stats = row["dp"]["by_class"].get(path_class)
    return None if stats is None else stats["max_abs_dp_pa"]


def lane_summary(row: dict[str, Any]) -> dict[str, Any]:
    """The acceptance quantities of one pressure-diagnostic hull/lane row."""
    if "error" in row:
        return {"error": row["error"]}
    cells = {
        f"{c['source_zone']}/{c['timing']}/{c['lane']}": c["whole_hull_material_time_h"]
        for c in row.get("source_cells", [])
    }
    return {
        "path_count": row["path_count"],
        "max_abs_dp_pa": row["dp"]["all"]["max_abs_dp_pa"],
        "envelope_max_abs_dp_pa": _class_max(row, "envelope_leak"),
        "exhaust_sink_max_abs_dp_pa": _class_max(row, "exhaust_sink"),
        "interior_max_abs_dp_pa": row["dp"]["interior"]["max_abs_dp_pa"],
        "interior_flowing_max_abs_dp_pa": row["dp"]["interior_flowing"]["max_abs_dp_pa"],
        "interior_blocked_n": row["dp"]["interior_blocked"]["n"],
        "exhaust_sink_out_m3h": row["boundary"]["exhaust_sink_out_m3h"],
        "ahs_return_minus_supply_m3h": row["boundary"]["ahs_return_minus_supply_m3h"],
        "makeup_demand_m3h": row["boundary"]["makeup_demand_m3h"],
        "envelope_net_inward_m3h": row["boundary"]["envelope_net_inward_m3h"],
        "ambient_opening_net_inward_m3h": row["boundary"].get(
            "ambient_opening_net_inward_m3h", 0.0
        ),
        "balance_residual_m3h": row["boundary"]["balance_residual_m3h"],
        "opening": opening_summary(row["paths"]),
        "k_field_over_native_median": row["outflow"]["median_field_over_native"],
        "whole_hull_material_time_h": cells,
    }


def compare_summary(report: dict[str, Any]) -> dict[str, Any]:
    cx = report["contamx"]
    keys = (
        "n_path_map", "fate_counts", "n_kept_real_paths", "n_synth_ahs_paths",
        "n_boundary_sink_paths", "boundary_sink_out_m3h", "n_ambient_opening_paths",
        "ambient_opening_sink_out_m3h", "ambient_opening_inward_m3h",
    )
    native = report["native"]
    return {
        "native_n_paths": native["n_paths"],
        "native_ambient_exchange": [
            {k: link.get(k) for k in ("path_id", "from_zone", "to_zone", "flow_m3h", "path_type")}
            for link in native["links"]
            if str(link.get("path_type", "")).startswith("ambient_exchange_")
        ],
        **{k: cx[k] for k in keys},
    }


def run_hull(hull: str, out_rel: str) -> dict[str, Any]:
    pressure = os.path.join(out_rel, f"pressure_{hull}.json")
    compare = os.path.join(out_rel, f"flow_compare_{hull}.json")
    exact_dir = os.path.join(out_rel, f"exact_check_{hull}")
    lane_args = [arg for lane in LANES for arg in ("--lane", lane)]
    source_args = [arg for zone in SOURCES[hull] for arg in ("--source", zone)]
    _run("pressure", "--hull", hull, *lane_args, *source_args, "--all-paths",
         "--out", pressure)
    _run("compare", "--platform", hull, "--run-contamx", "--inject", SOURCES[hull][0],
         "--output", compare)
    _run("exact", "exact-check", "--hull", hull, "--out", exact_dir)
    summary: dict[str, Any] = {
        "lanes": {r["lane"]: lane_summary(r) for r in _load(pressure)["rows"]},
        "flow_compare": compare_summary(_load(compare)),
        "exact_check": _load(
            os.path.join(exact_dir, "forced_exhaust_exact_integral_check.json")
        )["hulls"][hull],
    }
    if hull in PAIRED_HULLS:
        paired = os.path.join(out_rel, f"paired_{hull}.json")
        _run("paired", "--hull", hull, "--out", paired)
        summary["paired_cells"] = [
            {k: c[k] for k in (
                "source_zone", "lane", "timing", "whole_hull_material_time_h",
                "transport_loss", "closure_error",
            )}
            for c in _load(paired)["cells"]
        ]
    return summary


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def _pair(before: dict[str, Any], after: dict[str, Any], key: str) -> str:
    return f"{_fmt(before[key])} -> {_fmt(after[key])}"


_LANE_HEADER = (
    "hull", "lane", "paths", "max dP Pa", "interior flowing max dP Pa",
    "exhaust sinks m3/h", "envelope net in m3/h", "opening in m3/h",
    "opening out m3/h", "opening max dP Pa", "balance residual m3/h",
    "k field/native median",
)


def _lane_cells(hull: str, lane: str, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    opening = after["opening"]
    return [
        hull, lane, f"{before['path_count']} -> {after['path_count']}",
        _pair(before, after, "max_abs_dp_pa"),
        _pair(before, after, "interior_flowing_max_abs_dp_pa"),
        _pair(before, after, "exhaust_sink_out_m3h"),
        _pair(before, after, "envelope_net_inward_m3h"),
        _fmt(opening["inward_m3h"]), _fmt(opening["outward_m3h"]),
        _fmt(opening["max_abs_dp_pa"]),
        _pair(before, after, "balance_residual_m3h"),
        _pair(before, after, "k_field_over_native_median"),
    ]


def _table(header: tuple[str, ...], body: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(cells) + " |" for cells in body] + [""]


def _material_rows(hull: str, before: dict[str, Any], after: dict[str, Any]) -> list[list[str]]:
    rows = []
    for lane in LANES:
        cells_b = before["lanes"][lane]["whole_hull_material_time_h"]
        cells_a = after["lanes"][lane]["whole_hull_material_time_h"]
        rows += [[hull, key, _fmt(cells_b[key]), _fmt(cells_a[key])] for key in sorted(cells_a)]
    return rows


def _compare_rows(hull: str, before: dict[str, Any], after: dict[str, Any]) -> list[list[str]]:
    keys = (
        "n_path_map", "native_n_paths", "n_kept_real_paths", "n_synth_ahs_paths",
        "n_ambient_opening_paths", "ambient_opening_inward_m3h",
        "ambient_opening_sink_out_m3h",
    )
    fc_b, fc_a = before["flow_compare"], after["flow_compare"]
    native = sum(link["flow_m3h"] for link in fc_a["native_ambient_exchange"])
    return [[
        hull, *(f"{fc_b[k]:.6g} -> {fc_a[k]:.6g}" for k in keys),
        f"{len(fc_a['native_ambient_exchange'])} / {native:.4g}",
    ]]


def compare_markdown(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Before/after ledger tables from two ``summary.json`` reports."""
    hulls = [h for h in after["hulls"] if h in before["hulls"]]
    lanes, material, flows, paired = [], [], [], []
    for hull in hulls:
        b, a = before["hulls"][hull], after["hulls"][hull]
        lanes += [_lane_cells(hull, lane, b["lanes"][lane], a["lanes"][lane]) for lane in LANES]
        material += _material_rows(hull, b, a)
        flows += _compare_rows(hull, b, a)
        paired += [
            [hull, cb["source_zone"], cb["lane"], cb["timing"],
             _pair(cb, ca, "whole_hull_material_time_h"), _pair(cb, ca, "transport_loss"),
             _pair(cb, ca, "closure_error")]
            for cb, ca in zip(b.get("paired_cells", []), a.get("paired_cells", []))
        ]
    lines = ["### Pressure balance (before -> after)", "", *_table(_LANE_HEADER, lanes)]
    lines += ["### Flow compare (before -> after)", "", *_table((
        "hull", "path_map entries", "native links", "kept Crusher paths", "synth AHS paths",
        "ambient_opening legs", "opening inward m3/h", "opening outward sink m3/h",
        "native ambient_exchange links / total m3/h",
    ), flows)]
    lines += ["### Whole-hull material time, h (pressure diagnostic source cells)", "", *_table(
        ("hull", "source / timing / lane", "before", "after"), material)]
    lines += ["### Paired diagnostic matrix (before -> after)", "", *_table((
        "hull", "source", "lane", "timing", "whole-hull material time h",
        "transport loss", "closure error",
    ), paired)]
    return "\n".join(lines)


def _write_compare(labels: list[str]) -> str:
    root = os.path.join("telemetry_buffer", "ambient_makeup_witness")
    before, after = (
        _load(os.path.join(root, validate_path_component(label), "summary.json"))
        for label in labels
    )
    out_path = resolve_repo_path(REPO_ROOT, os.path.join(root, "compare.md"))
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        fh.write(compare_markdown(before, after))
    return out_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--hull", action="append", choices=CRUISE_HULLS,
                        help="default: the six cruise hulls")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--label", help="run the witnesses into this sub-directory")
    mode.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"),
                      help="write compare.md from two labelled runs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.compare:
        print(f"wrote {_write_compare(args.compare)}")
        return 0
    label = validate_path_component(args.label)
    out_rel = os.path.join("telemetry_buffer", "ambient_makeup_witness", label)
    prepare_output_directory(
        resolve_repo_path(REPO_ROOT, out_rel), allowed_roots=(REPO_ROOT,),
    )
    hulls = args.hull or list(CRUISE_HULLS)
    report = {"label": label, "hulls": {hull: run_hull(hull, out_rel) for hull in hulls}}
    out_path = resolve_repo_path(REPO_ROOT, os.path.join(out_rel, "summary.json"))
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
