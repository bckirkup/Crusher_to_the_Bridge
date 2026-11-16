#!/usr/bin/env python3
"""Fleet pressure/balance diagnostic for ContamX fields (CONTAM-FIELD-PRESSURE-REVIEW-01).

Solves each hull's ContamX field and reports, per hull and lane:

* per-path ``dP`` (Pa), summarised by path kind and by decade of ``|dP|``
* ``envelope_leak`` direction, flow and ``dP``
* AHS terminal balance: solved supply, return, return-minus-supply and
  recirculation per AHS group, against the declared terminal flows
* the hull boundary balance: return-minus-supply plus ducted exhaust sinks is
  the make-up air the envelope leaks have to carry
* native-vs-field specific outflow coefficients ``k`` (1/h) per zone

Lanes:

* ``authored`` — the committed ``contam/platform.prj`` + ``path_map.json``
* ``commissioned`` / ``design`` — a fresh in-memory export in that
  ``ahs_terminal_mode``

``--source`` adds per-zone outflow rows and, per ``--timing``, the paired
diagnostic's material-time cell for NATIVE and each field lane. Diagnostic
only: nothing is written into ``data/``; the report goes under
``telemetry_buffer/``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import tempfile
from typing import Any

import numpy as np

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
    ENVELOPE_LEAK_KIND,
    ENVELOPE_LEAK_MODES,
)
from simulation_utils.paths import (  # noqa: E402
    REPO_ROOT,
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.diag import contam_paired_diagnostic as paired  # noqa: E402
from tools.diag.contam_envelope_leak_enumeration import (  # noqa: E402
    bundled_hulls,
    summarize_envelope_leaks,
)

LANES = ("authored", "commissioned", "design")
DEFAULT_LANES = ("authored", "design")
TIMINGS = paired.TIMINGS
_PLATFORMS_REL = os.path.join("data", "platforms")
_PRJ_NAME = "platform.prj"
_PATH_RECORD = np.dtype([("nr", "<i4"), ("dp", "<f4"), ("flow0", "<f4"), ("flow1", "<f4")])
# Reporting bins only (decades of |dP|); not a plausibility constant.
DP_DECADES_PA = (10.0, 100.0, 1.0e3, 1.0e4, 1.0e5)
_FLOW_EPS_M3H = 1.0e-9
_RATIO_BANDS = (0.5, 2.0)

CLASS_ENVELOPE = "envelope_leak"
CLASS_AHS_TERMINAL = "ahs_terminal"
CLASS_AHS_SYSTEM = "ahs_system"
CLASS_EXHAUST_SINK = "exhaust_sink"
CLASS_DUCTED = "ducted_transfer"
CLASS_PRESCRIBED = "prescribed_link"
_PRESCRIBED_MECHANISM = "prescribed_flow"
CLASS_PASSIVE = "passive_opening"
_AHS_TERMINAL_KINDS = ("ahs_supply", "ahs_return")
_HULL_NUMBER_RE = re.compile(r"_([a-z]+)\d+$")


def hull_class(hull: str) -> str:
    """Reporting class from the platform id: hull-number type, cruise, or other."""
    if "cruise" in hull or hull in ("diamond_princess", "greg_mortimer"):
        return "cruise"
    if hull.startswith("enterprise_"):
        return "fiction"
    match = _HULL_NUMBER_RE.search(hull)
    return match.group(1) if match else "other"


def hull_group(hull: str) -> str:
    """Coarse reporting group: ``cruise``, ``fiction`` or ``naval``."""
    cls = hull_class(hull)
    return cls if cls in ("cruise", "fiction") else "naval"


def prescribed_kinds(airflow: dict[str, Any]) -> frozenset[str]:
    """Path kinds of the hull's ``prescribed_flow`` cross-zone links."""
    return frozenset(
        str(link["path"]) for link in airflow.get("cross_zone_links", [])
        if link.get("mechanism") == _PRESCRIBED_MECHANISM and link.get("path")
    )


def path_class(entry: dict[str, Any], prescribed: frozenset[str] = frozenset()) -> str:
    """Coarse path class used to group ``dP`` statistics.

    ``prescribed`` names the kinds whose flow is declared, so their ``dP`` is
    the zone pressure difference a fan element spans, not an opening's drop.
    """
    kind = str(entry.get("kind", ""))
    if kind == ENVELOPE_LEAK_KIND:
        return CLASS_ENVELOPE
    if kind in _AHS_TERMINAL_KINDS:
        return CLASS_AHS_TERMINAL
    if kind.startswith("ahs_"):
        return CLASS_AHS_SYSTEM
    if entry.get("sink") or kind == CLASS_EXHAUST_SINK:
        return CLASS_EXHAUST_SINK
    if kind in prescribed:
        return CLASS_PRESCRIBED
    if entry.get("is_hvac_ducted"):
        return CLASS_DUCTED
    return CLASS_PASSIVE


def read_path_dp(sim: SimResults) -> dict[int, float]:
    """Path ``nr`` -> ``dP`` (Pa) at the steady-state frame.

    ``SimResults`` decodes ``Flow0`` only; ``dP`` sits in the same 16-byte path
    record (``nr dP Flow0 Flow1``), so it is read at the same stride here.
    """
    frame = sim.steady_state_frame()
    index = next(i for i, candidate in enumerate(sim.frames) if candidate is frame)
    sizes = sim._record_sizes()
    offset = sim._data_start + index * sum(sizes) + sizes[0]
    records = np.frombuffer(
        sim._buf, dtype=_PATH_RECORD, count=sim.header["nafpt"], offset=offset,
    )
    return {int(nr): float(dp) for nr, dp in zip(records["nr"], records["dp"], strict=True)}


def dp_stats(values: list[float]) -> dict[str, Any]:
    """Count, max, median and decade exceedance counts of ``|dP|``."""
    magnitudes = [abs(v) for v in values]
    return {
        "n": len(magnitudes),
        "max_abs_dp_pa": max(magnitudes, default=0.0),
        "median_abs_dp_pa": statistics.median(magnitudes) if magnitudes else 0.0,
        "n_over_pa": {
            f"{threshold:g}": sum(1 for m in magnitudes if m > threshold)
            for threshold in DP_DECADES_PA
        },
    }


def path_rows(
    entries: list[dict[str, Any]], flows: dict[int, float], dps: dict[int, float],
    prescribed: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """One row per path-map entry with its solved ``dP`` and volumetric flow.

    A path-map entry the solve did not report raises ``KeyError``.
    """
    return [
        {
            "path_nr": int(entry["path_nr"]),
            "kind": str(entry.get("kind", "")),
            "path_class": path_class(entry, prescribed),
            "from_zone": entry["from_zone"],
            "to_zone": entry["to_zone"],
            "dp_pa": float(dps[int(entry["path_nr"])]),
            "flow_m3h": float(flows[int(entry["path_nr"])]),
        }
        for entry in sorted(entries, key=lambda e: int(e["path_nr"]))
    ]


def summarize_dp(rows: list[dict[str, Any]], top_paths: int) -> dict[str, Any]:
    """``dP`` statistics by path class and raw kind, plus the largest paths."""
    by_class: dict[str, list[float]] = {}
    by_kind: dict[str, list[float]] = {}
    for row in rows:
        by_class.setdefault(row["path_class"], []).append(row["dp_pa"])
        by_kind.setdefault(row["kind"], []).append(row["dp_pa"])
    ranked = sorted(rows, key=lambda r: abs(r["dp_pa"]), reverse=True)
    interior = [r for r in rows if r["path_class"] in (CLASS_PASSIVE, CLASS_DUCTED)]
    return {
        "all": dp_stats([r["dp_pa"] for r in rows]),
        "interior": dp_stats([r["dp_pa"] for r in interior]),
        # A one-way opening held shut by an adverse dP carries exactly no flow.
        "interior_flowing": dp_stats([r["dp_pa"] for r in interior if r["flow_m3h"] != 0.0]),
        "interior_blocked": dp_stats([r["dp_pa"] for r in interior if r["flow_m3h"] == 0.0]),
        "by_class": {name: dp_stats(vals) for name, vals in sorted(by_class.items())},
        "by_kind": {name: dp_stats(vals) for name, vals in sorted(by_kind.items())},
        "top_paths": ranked[:top_paths],
    }


def summarize_envelope(
    entries: list[dict[str, Any]],
    flows: dict[int, float],
    dps: dict[int, float],
    known_zones: set[str],
) -> dict[str, Any]:
    """Envelope direction/flow (shared enumeration) plus its ``dP`` statistics."""
    summary = summarize_envelope_leaks(entries, flows, known_zones)
    leak_dps = [
        dps.get(int(e["path_nr"]), 0.0)
        for e in entries
        if str(e.get("kind", "")) == ENVELOPE_LEAK_KIND
    ]
    summary["inward_count"] = sum(
        1
        for e in entries
        if str(e.get("kind", "")) == ENVELOPE_LEAK_KIND
        and flows.get(int(e["path_nr"]), 0.0) < -_FLOW_EPS_M3H
    )
    summary["net_inward_m3h"] = summary["inward_total_m3h"] - summary["outward_total_m3h"]
    summary["dp"] = dp_stats(leak_dps)
    return summary


def _ahs_group(groups: dict[int, dict[str, Any]], ahs_nr: int) -> dict[str, Any]:
    return groups.setdefault(ahs_nr, {
        "ahs_nr": ahs_nr,
        "supply_m3h": 0.0,
        "return_m3h": 0.0,
        "recirc_m3h": 0.0,
        "oa_m3h": 0.0,
        "exhaust_m3h": 0.0,
        "declared_supply_m3h": 0.0,
        "declared_return_m3h": 0.0,
        "terminal_count": 0,
    })


_AHS_FLOW_KEYS = {
    "ahs_supply": "supply_m3h",
    "ahs_return": "return_m3h",
    "ahs_recirc": "recirc_m3h",
    "ahs_oa": "oa_m3h",
    "ahs_exhaust": "exhaust_m3h",
}


def _add_declared(group: dict[str, Any], key: str, declared: Any) -> None:
    """Accumulate a terminal's declared flow; one undeclared terminal voids the group.

    Only a ``commissioned`` export records ``declared_flow_m3h``; elsewhere the
    declared flows are unknown (``None``), not zero.
    """
    if declared is None or group[key] is None:
        group["declared_supply_m3h"] = group["declared_return_m3h"] = None
        return
    group[key] += float(declared)


def _declared_total(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [g[key] for g in rows]
    return None if any(v is None for v in values) else sum(values)


def summarize_ahs(
    entries: list[dict[str, Any]], flows: dict[int, float],
) -> dict[str, Any]:
    """Solved and declared AHS flows per group and the return-minus-supply imbalance."""
    groups: dict[int, dict[str, Any]] = {}
    for entry in entries:
        key = _AHS_FLOW_KEYS.get(str(entry.get("kind", "")))
        ahs_nr = int(entry.get("ahs_nr") or 0)
        if key is None or ahs_nr <= 0:
            continue
        group = _ahs_group(groups, ahs_nr)
        group[key] += abs(float(flows.get(int(entry["path_nr"]), 0.0)))
        if entry["kind"] in _AHS_TERMINAL_KINDS:
            group["terminal_count"] += 1
            _add_declared(group, f"declared_{key}", entry.get("declared_flow_m3h"))
    rows = [groups[nr] for nr in sorted(groups)]
    for group in rows:
        group["return_minus_supply_m3h"] = group["return_m3h"] - group["supply_m3h"]
        group["declared_return_minus_supply_m3h"] = (
            None if group["declared_return_m3h"] is None
            else group["declared_return_m3h"] - group["declared_supply_m3h"]
        )
    supply = sum(g["supply_m3h"] for g in rows)
    returned = sum(g["return_m3h"] for g in rows)
    return {
        "group_count": len(rows),
        "supply_total_m3h": supply,
        "return_total_m3h": returned,
        "return_minus_supply_m3h": returned - supply,
        "recirc_total_m3h": sum(g["recirc_m3h"] for g in rows),
        "declared_supply_total_m3h": _declared_total(rows, "declared_supply_m3h"),
        "declared_return_total_m3h": _declared_total(rows, "declared_return_m3h"),
        "exhaust_only_group_count": sum(
            1 for g in rows if g["return_m3h"] > _FLOW_EPS_M3H >= g["supply_m3h"]
        ),
        "supply_only_group_count": sum(
            1 for g in rows if g["supply_m3h"] > _FLOW_EPS_M3H >= g["return_m3h"]
        ),
        "groups": rows,
    }


def summarize_boundary(
    rows: list[dict[str, Any]], envelope: dict[str, Any], ahs: dict[str, Any],
) -> dict[str, Any]:
    """Hull air balance: make-up demand against what the envelope leaks carry."""
    sink_out = sum(
        r["flow_m3h"] for r in rows
        if r["path_class"] == CLASS_EXHAUST_SINK and r["flow_m3h"] > 0.0
    )
    demand = ahs["return_minus_supply_m3h"] + sink_out
    leaks = envelope["envelope_leak_count"]
    return {
        "exhaust_sink_out_m3h": sink_out,
        "ahs_return_minus_supply_m3h": ahs["return_minus_supply_m3h"],
        "makeup_demand_m3h": demand,
        "envelope_net_inward_m3h": envelope["net_inward_m3h"],
        "balance_residual_m3h": demand - envelope["net_inward_m3h"],
        "makeup_demand_per_leak_m3h": demand / leaks if leaks else 0.0,
    }


def outflow_rows(
    native: Any, field: Any, zones: list[str],
) -> list[dict[str, Any]]:
    """Specific outflow coefficient ``k`` (1/h) per zone, NATIVE vs field."""
    out = []
    for zone in zones:
        k_native = float(native.zone_specific_outflow_rate(zone))
        k_field = float(field.zone_specific_outflow_rate(zone))
        out.append({
            "zone": zone,
            "k_native_per_h": k_native,
            "k_field_per_h": k_field,
            "field_over_native": k_field / k_native if k_native > 0.0 else None,
        })
    return out


def summarize_outflow(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fleet-table summary of the per-zone field/native outflow ratio."""
    ratios = [r["field_over_native"] for r in rows if r["field_over_native"] is not None]
    low, high = _RATIO_BANDS
    return {
        "zone_count": len(rows),
        "median_field_over_native": statistics.median(ratios) if ratios else None,
        "min_field_over_native": min(ratios, default=None),
        "max_field_over_native": max(ratios, default=None),
        "n_below_half": sum(1 for r in ratios if r < low),
        "n_above_double": sum(1 for r in ratios if r > high),
        "n_native_dead": sum(1 for r in rows if r["k_native_per_h"] <= 0.0),
        "n_field_dead": sum(1 for r in rows if r["k_field_per_h"] <= 0.0),
        "k_native_total_per_h": sum(r["k_native_per_h"] for r in rows),
        "k_field_total_per_h": sum(r["k_field_per_h"] for r in rows),
    }


def analyze_field(
    entries: list[dict[str, Any]],
    flows: dict[int, float],
    dps: dict[int, float],
    known_zones: set[str],
    top_paths: int = 10,
    prescribed: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Pressure/balance report for one solved field (no ContamX needed)."""
    rows = path_rows(entries, flows, dps, prescribed)
    envelope = summarize_envelope(entries, flows, dps, known_zones)
    ahs = summarize_ahs(entries, flows)
    return {
        "path_count": len(rows),
        "dp": summarize_dp(rows, top_paths),
        "envelope": envelope,
        "ahs": ahs,
        "boundary": summarize_boundary(rows, envelope, ahs),
        "paths": rows,
    }


def _read_text(rel_path: str) -> str:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return fh.read()


def _lane_inputs(
    hull: str, lane: str, spatial: dict[str, Any], airflow: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    base = os.path.join(_PLATFORMS_REL, hull)
    if lane == "authored":
        return (
            _read_text(os.path.join(base, "contam", _PRJ_NAME)),
            paired._load_json(os.path.join(base, "contam", "path_map.json")),
        )
    overrides = load_hobbyist_overrides(resolve_repo_path(REPO_ROOT, base))
    return export_prj_with_path_map(
        spatial, airflow, hobbyist=True, overrides=overrides,
        filter_efficiency=paired.FILTER_EFFICIENCY, ahs_terminal_mode=lane,
    )


def _solve(
    prj_text: str, binary: str, timeout_s: float,
) -> tuple[dict[int, float], dict[int, float]]:
    with tempfile.TemporaryDirectory(prefix="contam_pressure_balance_") as tmp_dir:
        roots = (REPO_ROOT, tmp_dir)
        prj_path = os.path.join(tmp_dir, _PRJ_NAME)
        with validated_open(prj_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write(prj_text)
        sim_path = run_contamx(prj_path, binary, timeout_s=timeout_s, allowed_roots=roots)
        sim = SimResults(sim_path, allowed_roots=roots)
        return sim.path_volumetric_flow_m3h(), read_path_dp(sim)


def _source_cells(
    hull: str, lane: str, engine: Any, airflow: dict[str, Any],
    sources: list[str], timings: list[str],
) -> list[dict[str, Any]]:
    data = paired._operator_data(engine)
    matrices = paired._matrices(data["operator"], paired._horizons_for(timings))
    return [
        paired._trajectory_cell(hull, lane, source, timing, data, matrices, airflow)
        for source in sources
        for timing in timings
    ]


def _hull_rows(hull: str, binary: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    spatial, airflow = paired._load_platform(hull)
    zones = [str(z["id"]) for z in spatial.get("zones", [])]
    sources = paired._sources_for(hull, spatial, args.source) if args.source else []
    timings = args.timing or list(TIMINGS)
    native = paired._native_engine(spatial, airflow)
    rows: list[dict[str, Any]] = []
    for lane in args.lane or list(DEFAULT_LANES):
        row: dict[str, Any] = {
            "hull": hull, "lane": lane, "hull_class": hull_class(hull),
            "zone_count": len(zones),
        }
        rows.append(row)
        try:
            prj_text, entries = _lane_inputs(hull, lane, spatial, airflow)
            flows, dps = _solve(prj_text, binary, args.timeout_s)
        except (ContamXUnavailable, OSError, ValueError, KeyError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            continue
        row.update(
            analyze_field(
                entries, flows, dps, set(zones), args.top_paths, prescribed_kinds(airflow),
            )
        )
        if not args.all_paths:
            row.pop("paths")
        field = paired._contamx_engine(
            spatial, entries, flows, airflow, args.envelope_leak_mode,
        )
        per_zone = outflow_rows(native, field, zones)
        row["outflow"] = summarize_outflow(per_zone)
        if sources:
            row["source_outflow"] = [r for r in per_zone if r["zone"] in sources]
            row["source_cells"] = (
                _source_cells(hull, "native", native, airflow, sources, timings)
                + _source_cells(hull, lane, field, airflow, sources, timings)
            )
    return rows


def _min_med_max(values: list[float]) -> str:
    return f"{min(values):.3g} / {statistics.median(values):.3g} / {max(values):.3g}"


def _count_over(values: list[float], threshold: float) -> int:
    return sum(1 for value in values if value > threshold)


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Hull-class aggregate over the solved rows of one lane and group."""
    peak = [r["dp"]["all"]["max_abs_dp_pa"] for r in rows]
    interior = [r["dp"]["interior"]["max_abs_dp_pa"] for r in rows]
    flowing = [r["dp"]["interior_flowing"]["max_abs_dp_pa"] for r in rows]
    blocked = [r["dp"]["interior_blocked"] for r in rows]
    per_leak = [r["boundary"]["makeup_demand_per_leak_m3h"] or 0.0 for r in rows]
    ratios = [
        r["outflow"]["median_field_over_native"] for r in rows
        if r["outflow"]["median_field_over_native"] is not None
    ]
    return {
        "hulls": len(rows),
        "max_abs_dp_pa": _min_med_max(peak),
        "hulls_over_1kpa": _count_over(peak, 1.0e3),
        "hulls_over_10kpa": _count_over(peak, 1.0e4),
        "hulls_over_100kpa": _count_over(peak, 1.0e5),
        "interior_max_abs_dp_pa": _min_med_max(interior),
        "hulls_interior_over_1kpa": _count_over(interior, 1.0e3),
        "interior_flowing_max_abs_dp_pa": _min_med_max(flowing),
        "hulls_interior_flowing_over_1kpa": _count_over(flowing, 1.0e3),
        "interior_blocked_paths": sum(b["n"] for b in blocked),
        "interior_blocked_paths_over_1kpa": sum(b["n_over_pa"]["1000"] for b in blocked),
        "hulls_with_blocked_over_1kpa": sum(1 for b in blocked if b["n_over_pa"]["1000"]),
        "makeup_per_leak_m3h": _min_med_max(per_leak),
        "ahs_return_minus_supply_m3h": sum(r["ahs"]["return_minus_supply_m3h"] for r in rows),
        "exhaust_sink_out_m3h": sum(r["boundary"]["exhaust_sink_out_m3h"] for r in rows),
        "envelope_inward_m3h": sum(r["envelope"]["inward_total_m3h"] for r in rows),
        "envelope_outward_m3h": sum(r["envelope"]["outward_total_m3h"] for r in rows),
        "hulls_with_outward_leak": sum(1 for r in rows if r["envelope"]["outward_count"]),
        "max_abs_balance_residual_m3h": max(
            abs(r["boundary"]["balance_residual_m3h"]) for r in rows
        ),
        "median_field_over_native": _min_med_max(ratios) if ratios else None,
        "zones": sum(r["outflow"]["zone_count"] for r in rows),
        "zones_below_half_native": sum(r["outflow"]["n_below_half"] for r in rows),
        "zones_above_double_native": sum(r["outflow"]["n_above_double"] for r in rows),
    }


def summarize_fleet(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One aggregate per (lane, hull group), in first-seen lane order."""
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    unsolved: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["lane"], hull_group(row["hull"]))
        if "error" in row:
            unsolved[key] = unsolved.get(key, 0) + 1
            buckets.setdefault(key, [])
        else:
            buckets.setdefault(key, []).append(row)
    return [
        {
            "lane": lane, "group": group, "unsolved": unsolved.get((lane, group), 0),
            **(summarize_group(solved) if solved else {"hulls": 0}),
        }
        for (lane, group), solved in buckets.items()
    ]


_HULL_COLUMNS = (
    "hull", "class", "lane", "zones", "max dP Pa", "envelope median dP Pa",
    "interior max dP Pa", "interior flowing max dP Pa", "blocked interior n (>1 kPa)",
    "leaks in/out", "envelope in m3/h", "envelope out m3/h",
    "AHS return-supply m3/h", "exhaust sinks m3/h", "make-up per leak m3/h",
    "exhaust-only AHS", "k field/native median (min-max)", "zones <0.5x / >2x",
)


def _hull_cells(row: dict[str, Any]) -> list[str]:
    head = [row["hull"], row["hull_class"], row["lane"], str(row["zone_count"])]
    if "error" in row:
        return head + ["unsolved"] + [""] * (len(_HULL_COLUMNS) - len(head) - 1)
    envelope, boundary, outflow = row["envelope"], row["boundary"], row["outflow"]
    blocked = row["dp"]["interior_blocked"]
    ratio = outflow["median_field_over_native"]
    spread = (
        "n/a" if ratio is None else
        f"{ratio:.2f} ({outflow['min_field_over_native']:.2f}-"
        f"{outflow['max_field_over_native']:.2f})"
    )
    return head + [
        f"{row['dp']['all']['max_abs_dp_pa']:.3g}",
        f"{envelope['dp']['median_abs_dp_pa']:.3g}",
        f"{row['dp']['interior']['max_abs_dp_pa']:.3g}",
        f"{row['dp']['interior_flowing']['max_abs_dp_pa']:.3g}",
        f"{blocked['n']} ({blocked['n_over_pa']['1000']})",
        f"{envelope['inward_count']}/{envelope['outward_count']}",
        f"{envelope['inward_total_m3h']:.1f}",
        f"{envelope['outward_total_m3h']:.4g}",
        f"{row['ahs']['return_minus_supply_m3h']:.1f}",
        f"{boundary['exhaust_sink_out_m3h']:.1f}",
        f"{boundary['makeup_demand_per_leak_m3h'] or 0.0:.1f}",
        f"{row['ahs']['exhaust_only_group_count']}/{row['ahs']['group_count']}",
        spread,
        f"{outflow['n_below_half']}/{outflow['n_above_double']}",
    ]


def _markdown_table(header: list[str], body: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(cells) + " |" for cells in body)
    return lines


def fleet_markdown(rows: list[dict[str, Any]]) -> str:
    """Hull-class summary table followed by the per-hull fleet table."""
    summary = summarize_fleet(rows)
    keys = [k for k in summary[0] if k not in ("lane", "group")] if summary else []
    for block in summary:
        keys.extend(k for k in block if k not in keys and k not in ("lane", "group"))
    transposed = [
        [key] + [_format_cell(block.get(key)) for block in summary] for key in keys
    ]
    header = ["metric"] + [f"{b['lane']} / {b['group']}" for b in summary]
    ordered = sorted(rows, key=lambda r: (hull_group(r["hull"]), r["hull_class"], r["hull"]))
    lines = ["### Hull-class summary", "", *_markdown_table(header, transposed), ""]
    lines += ["### Fleet table", ""]
    lines += _markdown_table(list(_HULL_COLUMNS), [_hull_cells(r) for r in ordered])
    return "\n".join(lines) + "\n"


def _format_cell(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hull", action="append", help="default: every bundled hull")
    parser.add_argument("--lane", action="append", choices=LANES)
    parser.add_argument("--source", action="append", help="zone id present on every --hull")
    parser.add_argument("--timing", action="append", choices=TIMINGS)
    parser.add_argument(
        "--envelope-leak-mode", choices=ENVELOPE_LEAK_MODES,
        default=ENVELOPE_LEAK_BOUNDARY_SINK,
    )
    parser.add_argument("--top-paths", type=int, default=10)
    parser.add_argument("--all-paths", action="store_true", help="keep every per-path row")
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument(
        "--out",
        default="telemetry_buffer/contam_pressure_balance_diagnostic/results.json",
    )
    parser.add_argument("--markdown", help="also write the fleet tables as Markdown")
    parser.add_argument(
        "--from-json", help="render --markdown from an earlier --out report; no solve",
    )
    return parser.parse_args(argv)


def _write_markdown(rel_path: str, rows: list[dict[str, Any]]) -> None:
    md_path = resolve_repo_path(REPO_ROOT, rel_path)
    prepare_output_directory(os.path.dirname(md_path), allowed_roots=(REPO_ROOT,))
    with validated_open(md_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        fh.write(fleet_markdown(rows))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.from_json:
        if not args.markdown:
            raise SystemExit("--from-json needs --markdown")
        src = resolve_repo_path(REPO_ROOT, args.from_json)
        with validated_open(src, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
            _write_markdown(args.markdown, json.load(fh)["rows"])
        return 0
    binary = find_contamx()
    if binary is None:
        raise ContamXUnavailable("ContamX binary not found")
    hulls = [
        validate_path_component(h, label="platform id") for h in (args.hull or bundled_hulls())
    ]
    rows = [row for hull in hulls for row in _hull_rows(hull, binary, args)]
    out_path = resolve_repo_path(REPO_ROOT, args.out)
    prepare_output_directory(os.path.dirname(out_path), allowed_roots=(REPO_ROOT,))
    meta = {
        "lanes": args.lane or list(DEFAULT_LANES),
        "envelope_leak_mode": args.envelope_leak_mode,
        "filter_efficiency": paired.FILTER_EFFICIENCY,
        "dp_decades_pa": list(DP_DECADES_PA),
        "timeout_s": args.timeout_s,
    }
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(
            {"meta": meta, "summary": summarize_fleet(rows), "rows": rows},
            fh, indent=2, sort_keys=True,
        )
        fh.write("\n")
    if args.markdown:
        _write_markdown(args.markdown, rows)
    failed = [r for r in rows if "error" in r]
    print(f"wrote {len(rows)} rows ({len(failed)} unsolved) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
