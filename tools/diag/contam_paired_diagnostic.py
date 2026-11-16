#!/usr/bin/env python3
"""Exact paired native/ContamX material-time diagnostic for bundled hulls.

The diagnostic is intentionally lane-honest: NATIVE and both ContamX lanes share
Crusher's exponential mass propagator, so differences isolate airflow-field
generation rather than independent contaminant-solver validation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import Any

import numpy as np
from scipy.linalg import expm

_SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPT_ROOT)

from engines.contamx_runner import (  # noqa: E402
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.contamx_transport import (  # noqa: E402
    ENVELOPE_LEAK_BOUNDARY_SINK,
    ENVELOPE_LEAK_MODES,
    ContamXTransportEngine,
)
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    REPO_ROOT,
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402

FILTER_EFFICIENCY = 0.3
NATURAL_DECAY_RATE = 0.10
HORIZON_H = 12.0
SPLIT_OFFSET_H = 1.0
REACHABLE_EPSILON_H = 1e-12
PLATFORM_SOURCES = {
    "expedition_cruise_450": ["MainDining", "HD_5P_M", "PoolDeck", "MainGalley"],
    "destroyer_baseline": ["Mess_Hall", "HD_MAIN_M", "Bridge"],
}
LANES = ("native", "commissioned", "authored")
# Fresh ``ahs_terminal_mode="design"`` export: the pre-#1245 authoring, kept as
# an opt-in lane because it is where outward envelope leaks solve non-zero.
OPTIONAL_LANES = ("design",)
TIMINGS = ("pulse_t0", "split_t0_t1")
_TIMING_DEFINITIONS = {
    "pulse_t0": "one emitted unit at t=0h",
    "split_t0_t1": "0.5 emitted units at t=0h and 0.5 at t=1h",
}


def _load_json(rel_path: str) -> Any:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _platform_rel(hull: str, name: str) -> str:
    return f"data/platforms/{hull}/{name}"


def _load_platform(hull: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        _load_json(_platform_rel(hull, "spatial_layout.json")),
        _load_json(_platform_rel(hull, "air_flow_paths.json")),
    )


def _zone_ids(spatial: dict[str, Any]) -> set[str]:
    return {str(z["id"]) for z in spatial.get("zones", [])}


def _sources_for(
    hull: str, spatial: dict[str, Any], requested: list[str] | None,
) -> list[str]:
    known = _zone_ids(spatial)
    sources = requested or PLATFORM_SOURCES[hull]
    missing = [s for s in sources if s not in known]
    if missing:
        raise ValueError(f"{hull} sources missing from spatial_layout: {missing}")
    return list(dict.fromkeys(sources))


def _timing_pulses(timing: str) -> tuple[tuple[float, float, float], ...]:
    if timing == "pulse_t0":
        return ((0.0, 1.0, HORIZON_H),)
    if timing == "split_t0_t1":
        return (
            (0.0, 0.5, HORIZON_H),
            (SPLIT_OFFSET_H, 0.5, HORIZON_H - SPLIT_OFFSET_H),
        )
    raise ValueError(f"unknown timing {timing!r}")


def _solve_prj_text(prj_text: str, tmp_dir: str, binary: str) -> dict[int, float]:
    prj_path = os.path.join(tmp_dir, "platform.prj")
    with validated_open(
        prj_path, "w", allowed_roots=(REPO_ROOT, tmp_dir), encoding="utf-8",
    ) as fh:
        fh.write(prj_text)
    sim_path = run_contamx(prj_path, binary, allowed_roots=(REPO_ROOT, tmp_dir))
    return SimResults(sim_path, allowed_roots=(REPO_ROOT, tmp_dir)).path_volumetric_flow_m3h()


def _contamx_engine(
    spatial: dict[str, Any],
    entries: list[dict[str, Any]],
    flows: dict[int, float],
    airflow: dict[str, Any],
    envelope_leak_mode: str,
) -> ContamXTransportEngine:
    return ContamXTransportEngine(
        spatial_layout=spatial,
        path_map=entries,
        path_flows_m3h=flows,
        filter_efficiency=FILTER_EFFICIENCY,
        natural_decay_rate=NATURAL_DECAY_RATE,
        path_map_entries=entries,
        oa_fraction=float(airflow.get("oa_fraction", 0.2)),
        envelope_leak_mode=envelope_leak_mode,
    )


def _native_engine(
    spatial: dict[str, Any], airflow: dict[str, Any],
) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
        filter_efficiency=FILTER_EFFICIENCY,
        natural_decay_rate=NATURAL_DECAY_RATE,
    )


def _fresh_export_engine(
    hull: str, spatial: dict[str, Any], airflow: dict[str, Any], binary: str,
    ahs_terminal_mode: str, envelope_leak_mode: str,
) -> ContamXTransportEngine:
    platform_dir = resolve_repo_path(REPO_ROOT, f"data/platforms/{hull}")
    overrides = load_hobbyist_overrides(platform_dir)
    prj_text, entries = export_prj_with_path_map(
        spatial,
        airflow,
        hobbyist=True,
        overrides=overrides,
        filter_efficiency=FILTER_EFFICIENCY,
        ahs_terminal_mode=ahs_terminal_mode,
    )
    with tempfile.TemporaryDirectory(prefix="contam_paired_export_") as tmp_dir:
        flows = _solve_prj_text(prj_text, tmp_dir, binary)
    return _contamx_engine(spatial, entries, flows, airflow, envelope_leak_mode)


def _authored_engine(
    hull: str, spatial: dict[str, Any], airflow: dict[str, Any], binary: str,
    envelope_leak_mode: str,
) -> ContamXTransportEngine:
    prj_full = resolve_repo_path(
        REPO_ROOT, _platform_rel(hull, "contam/platform.prj"),
    )
    map_full = resolve_repo_path(
        REPO_ROOT, _platform_rel(hull, "contam/path_map.json"),
    )
    with validated_open(prj_full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        prj_text = fh.read()
    with validated_open(map_full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        entries = json.load(fh)
    with tempfile.TemporaryDirectory(prefix="contam_paired_authored_") as tmp_dir:
        flows = _solve_prj_text(prj_text, tmp_dir, binary)
    return _contamx_engine(spatial, entries, flows, airflow, envelope_leak_mode)


def _lane_engine(
    hull: str,
    lane: str,
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    binary: str | None,
    envelope_leak_mode: str = ENVELOPE_LEAK_BOUNDARY_SINK,
) -> ContamTransportEngine:
    if lane == "native":
        return _native_engine(spatial, airflow)
    if binary is None:
        raise ContamXUnavailable(f"lane {lane!r} requires a ContamX binary")
    if lane in ("commissioned", "design"):
        return _fresh_export_engine(
            hull, spatial, airflow, binary, lane, envelope_leak_mode,
        )
    if lane == "authored":
        return _authored_engine(hull, spatial, airflow, binary, envelope_leak_mode)
    raise ValueError(f"unknown lane {lane!r}")


def _operator_data(engine: ContamTransportEngine) -> dict[str, Any]:
    zone_ids = list(engine._real_zone_ids)
    decay_free = engine._build_decay_free_operator()
    operator = decay_free - NATURAL_DECAY_RATE * np.eye(len(zone_ids))
    ones = np.ones(len(zone_ids))
    return {
        "zone_ids": zone_ids,
        "zone_index": {zid: i for i, zid in enumerate(zone_ids)},
        "operator": operator,
        "loss_weight": -(decay_free.T @ ones),
    }


def _matrices(operator: np.ndarray, horizons: set[float]) -> dict[float, tuple[np.ndarray, np.ndarray]]:
    n = operator.shape[0]
    out: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    for horizon in sorted(horizons):
        block = np.zeros((2 * n, 2 * n))
        block[:n, :n] = operator
        block[:n, n:] = np.eye(n)
        exp_block = expm(block * horizon)
        out[horizon] = (exp_block[:n, :n], exp_block[:n, n:])
    return out


def _room_to_group(airflow: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for group in airflow.get("hvac_zones", []):
        gid = str(group.get("id", ""))
        for room in group.get("rooms", []):
            out.setdefault(str(room), gid)
    return out


def _group_rooms(airflow: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for group in airflow.get("hvac_zones", []):
        gid = str(group.get("id", ""))
        out[gid] = {str(r) for r in group.get("rooms", [])}
    return out


def _local_remote_indices(
    source: str,
    zone_ids: list[str],
    airflow: dict[str, Any],
) -> tuple[list[int], list[int], str | None]:
    index = {zid: i for i, zid in enumerate(zone_ids)}
    room_map = _room_to_group(airflow)
    group_id = room_map.get(source)
    if group_id is None:
        local_ids = {source}
    else:
        local_ids = _group_rooms(airflow).get(group_id, set()) | {source}
    local = [index[z] for z in local_ids if z in index]
    remote = [i for i, zid in enumerate(zone_ids) if zid not in local_ids]
    return local, remote, group_id


def _trajectory_cell(
    hull: str,
    lane: str,
    source: str,
    timing: str,
    data: dict[str, Any],
    matrices: dict[float, tuple[np.ndarray, np.ndarray]],
    airflow: dict[str, Any],
) -> dict[str, Any]:
    zone_ids = data["zone_ids"]
    source_i = data["zone_index"][source]
    pulses = _timing_pulses(timing)
    integral_vec = np.zeros(len(zone_ids))
    retained_vec = np.zeros(len(zone_ids))
    for _tau, weight, horizon in pulses:
        propagator, integral_matrix = matrices[horizon]
        integral_vec += weight * integral_matrix[:, source_i]
        retained_vec += weight * propagator[:, source_i]

    emitted = float(sum(weight for _tau, weight, _h in pulses))
    material_time = float(integral_vec.sum())
    retained = float(retained_vec.sum())
    natural_decay_loss = NATURAL_DECAY_RATE * material_time
    transport_loss = float(data["loss_weight"] @ integral_vec)
    closure_error = emitted - retained - natural_decay_loss - transport_loss
    local_idx, remote_idx, group_id = _local_remote_indices(
        source, zone_ids, airflow,
    )
    reachable = sum(
        1
        for i, zid in enumerate(zone_ids)
        if zid != source and integral_vec[i] > REACHABLE_EPSILON_H
    )
    return {
        "hull": hull,
        "lane": lane,
        "source_zone": source,
        "timing": timing,
        "ahu_group_id": group_id,
        "zone_count": len(zone_ids),
        "local_room_count": len(local_idx),
        "remote_room_count": len(remote_idx),
        "emitted_units": emitted,
        "whole_hull_material_time_h": material_time,
        "local_material_time_h": float(integral_vec[local_idx].sum()),
        "remote_material_time_h": float(integral_vec[remote_idx].sum()),
        "retained_12h": retained,
        "local_retained_12h": float(retained_vec[local_idx].sum()),
        "remote_retained_12h": float(retained_vec[remote_idx].sum()),
        "natural_decay_loss": natural_decay_loss,
        "transport_loss": transport_loss,
        "closure_error": closure_error,
        "reachable_other_rooms_count": reachable,
        "reachable_epsilon_h": REACHABLE_EPSILON_H,
    }


def _horizons_for(timings: list[str]) -> set[float]:
    horizons = {HORIZON_H}
    if "split_t0_t1" in timings:
        horizons.add(HORIZON_H - SPLIT_OFFSET_H)
    return horizons


def _contamx_binary(lanes: list[str]) -> str | None:
    if all(lane == "native" for lane in lanes):
        return None
    binary = find_contamx()
    if binary is None:
        raise ContamXUnavailable("ContamX binary not found for commissioned/authored lanes")
    return binary


def _lane_bundle(
    hull: str,
    lane: str,
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    binary: str | None,
    timings: list[str],
    lane_cache: dict[tuple[str, str], dict[str, Any]],
    envelope_leak_mode: str = ENVELOPE_LEAK_BOUNDARY_SINK,
) -> dict[str, Any]:
    key = (hull, lane)
    if key not in lane_cache:
        engine = _lane_engine(
            hull, lane, spatial, airflow, binary, envelope_leak_mode,
        )
        data = _operator_data(engine)
        lane_cache[key] = {
            "engine": engine,
            "data": data,
            "matrices": _matrices(data["operator"], _horizons_for(timings)),
        }
    return lane_cache[key]


def _source_cells(
    hull: str,
    lane: str,
    source: str,
    timings: list[str],
    lane_data: dict[str, Any],
    airflow: dict[str, Any],
) -> list[dict[str, Any]]:
    if source not in lane_data["data"]["zone_index"]:
        raise ValueError(f"{hull}/{lane} lacks source zone {source}")
    return [
        _trajectory_cell(
            hull, lane, source, timing,
            lane_data["data"], lane_data["matrices"], airflow,
        )
        for timing in timings
    ]


def _run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    hulls = args.hull or list(PLATFORM_SOURCES)
    lanes = args.lane or list(LANES)
    timings = args.timing or list(TIMINGS)
    binary = _contamx_binary(lanes)

    cells: list[dict[str, Any]] = []
    lane_cache: dict[tuple[str, str], dict[str, Any]] = {}
    for hull in hulls:
        spatial, airflow = _load_platform(hull)
        sources = _sources_for(hull, spatial, args.source)
        for lane in lanes:
            lane_data = _lane_bundle(
                hull, lane, spatial, airflow, binary, timings, lane_cache,
                args.envelope_leak_mode,
            )
            for source in sources:
                cells.extend(_source_cells(hull, lane, source, timings, lane_data, airflow))
    return {
        "meta": {
            "filter_efficiency": FILTER_EFFICIENCY,
            "natural_decay_rate": NATURAL_DECAY_RATE,
            "horizon_h": HORIZON_H,
            "timing_definitions": _TIMING_DEFINITIONS,
            "reachable_epsilon_h": REACHABLE_EPSILON_H,
            "contamx_binary": binary,
            "envelope_leak_mode": args.envelope_leak_mode,
            "hulls": hulls,
            "lanes": lanes,
            "timings": timings,
        },
        "cells": cells,
    }


def _write_output(path: str, payload: dict[str, Any]) -> None:
    out_dir = os.path.dirname(path) or REPO_ROOT
    prepare_output_directory(
        out_dir, allowed_roots=(REPO_ROOT, tempfile.gettempdir()),
    )
    with validated_open(
        path, "w", allowed_roots=(REPO_ROOT, tempfile.gettempdir()), encoding="utf-8",
    ) as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hull", action="append", choices=sorted(PLATFORM_SOURCES))
    parser.add_argument("--lane", action="append", choices=LANES + OPTIONAL_LANES)
    parser.add_argument(
        "--envelope-leak-mode",
        choices=ENVELOPE_LEAK_MODES,
        default=ENVELOPE_LEAK_BOUNDARY_SINK,
        help="boundary_sink (default) or the labelled pressure_only baseline",
    )
    parser.add_argument("--source", action="append")
    parser.add_argument("--timing", action="append", choices=TIMINGS)
    parser.add_argument(
        "--out",
        default="telemetry_buffer/contam_paired_diagnostic/results.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out_path = args.out
    if not os.path.isabs(out_path):
        out_path = resolve_repo_path(REPO_ROOT, out_path)
    payload = _run_matrix(args)
    _write_output(out_path, payload)
    print(f"wrote {len(payload['cells'])} cells to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
