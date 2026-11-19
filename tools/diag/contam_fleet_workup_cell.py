#!/usr/bin/env python3
"""One cold cell of the fleet native-vs-ContamX workup (aggregate only).

Runs a single ``hull|lane|setting`` row of the frozen matrix
(CONTAM-FLEET-WORKUP-PROTOCOL-01, amended by
CONTAM-FLEET-WORKUP-CANARY-01) in a fresh interpreter: reads the hull inputs
from disk, applies the setting, builds the lane's field, reduces it to
whole-hull aggregates and times each phase.

Two labelled output blocks:

- ``solved_airflow``: sums over the lane's own airflow field (ContamX solved
  ``Flow0``/``dP``; the native lane's prescribed flows). A quantity the
  solver does not resolve is blank with a reason, never 0.
- ``downstream_mixing``: the shared mass-balance operator built on that
  field. Derived; on a ContamX lane it is not an independent ContamX result.

No per-zone, per-path or per-opening value and no zone or path identifier is
written. Inert uniform tracer only; no agent, dose or occupant model.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import resource
import sys
import tempfile
import time
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np  # noqa: E402
from scipy.linalg import expm  # noqa: E402

from engines.contamx_runner import SimResults, run_contamx  # noqa: E402
from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import (  # noqa: E402
    PATH_TYPE_HVAC_RETURN,
    PATH_TYPE_HVAC_SUPPLY,
    PLENUM_PREFIX,
    ContamTransportEngine,
)
from simulation_utils.paths import validated_open  # noqa: E402
from tools.contam_hobbyist import load_hobbyist_overrides, resolve_relative_wind  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.diag.contam_pressure_balance_diagnostic import read_path_dp  # noqa: E402

LANE_NATIVE = "native_prescribed"
LANE_COMMISSIONED = "contamx_commissioned_export"
LANE_AS_COMMITTED = "contamx_commissioned_export_as_committed"
LANE_AUTHORED = "contamx_authored_bundle"
CONTAMX_LANES = (LANE_COMMISSIONED, LANE_AS_COMMITTED, LANE_AUTHORED)

BLOCK_SOLVED = "solved_airflow"
BLOCK_DOWNSTREAM = "downstream_mixing"

FILTER_EFFICIENCY = 0.3
TRACER_HORIZON_H = 12.0
ENVELOPE_LEAK_MODE = "boundary_sink"
DEFAULT_ACH = 6.0
AHS_SYSTEM_KINDS = ("ahs_oa", "ahs_exhaust", "ahs_recirc")
WIND_PROFILE_KINDS = ("envelope_leak", "ambient_opening")
_FLOW_EPS = 1e-12
_WEATHER_MARK = "! steady simulation"

OK = "ok"
UNIMPLEMENTED = "unimplemented"
NOT_APPLICABLE = "not_applicable"
REASON_AHS_UNRESOLVED = (
    "ContamX reports Flow0 = 0 on every simple-AHS outdoor-air, exhaust and "
    "recirculation path in a steady airflow solve; the solver does not "
    "resolve this quantity, so it is blank, not zero"
)
REASON_NATIVE_PRESSURE = "the native lane prescribes flow and solves no pressure"
REASON_PRESCRIBED = "prescribed by the native lane, not solved"


class CellError(RuntimeError):
    """A cell could not be built as the frozen protocol requires."""


# ── inputs and settings ───────────────────────────────────────────────────


def _platform_path(hull: str, name: str) -> str:
    return os.path.join(_REPO_ROOT, "data", "platforms", hull, name)


def _read_json(path: str) -> Any:
    with validated_open(path, "r", allowed_roots=(_REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def load_hull(hull: str) -> dict[str, Any]:
    """Hull input documents, read from disk."""
    return {
        "spatial": _read_json(_platform_path(hull, "spatial_layout.json")),
        "airflow": _read_json(_platform_path(hull, "air_flow_paths.json")),
        "overrides": load_hobbyist_overrides(
            os.path.join(_REPO_ROOT, "data", "platforms", hull),
        ),
    }


def _group_duty(group: dict[str, Any], airflow: dict[str, Any]) -> float:
    return float(group.get("hvac_duty", airflow.get("hvac_duty", 1.0)))


def _group_oa(group: dict[str, Any], airflow: dict[str, Any]) -> float:
    return float(group.get("oa_fraction", airflow.get("oa_fraction", 0.2)))


def supply_groups(airflow: dict[str, Any]) -> list[dict[str, Any]]:
    """HVAC groups with positive duty, the frozen design's supply groups."""
    return [
        g for g in airflow.get("hvac_zones") or [] if _group_duty(g, airflow) > 0.0
    ]


def _scale_duty(airflow: dict[str, Any], factor: float) -> None:
    for group in supply_groups(airflow):
        group["hvac_duty"] = _group_duty(group, airflow) * factor


def _scale_ach(airflow: dict[str, Any], factor: float) -> None:
    for group in supply_groups(airflow):
        group["ach"] = float(group.get("ach", DEFAULT_ACH)) * factor


def _scale_oa(airflow: dict[str, Any], factor: float) -> None:
    for group in supply_groups(airflow):
        oa = _group_oa(group, airflow)
        if oa < 1.0:
            group["oa_fraction"] = oa * factor


def _scale_recirc(airflow: dict[str, Any], factor: float) -> None:
    for group in supply_groups(airflow):
        oa = _group_oa(group, airflow)
        if oa < 1.0:
            group["oa_fraction"] = 1.0 - factor * (1.0 - oa)


_VENTILATION_SETTERS = {
    "supply_group_hvac_duty": _scale_duty,
    "supply_group_ach": _scale_ach,
    "recirculating_supply_group_oa_fraction": _scale_oa,
    "recirculating_supply_group_recirculated_fraction": _scale_recirc,
}
_WIND_KEYS = {
    "relative_wind_speed": "relative_wind_speed_m_s",
    "relative_wind_direction": "relative_wind_direction_deg",
}


def apply_setting(
    airflow: dict[str, Any], parameter: str, level: str,
) -> tuple[dict[str, Any], dict[str, float]]:
    """``(airflow copy with the setting applied, wind override keys)``."""
    changed = copy.deepcopy(airflow)
    wind: dict[str, float] = {}
    if parameter == "none":
        return changed, wind
    if parameter in _VENTILATION_SETTERS:
        _VENTILATION_SETTERS[parameter](changed, float(level))
        return changed, wind
    names = parameter.split("+")
    levels = level.split("+")
    if len(names) != len(levels) or any(n not in _WIND_KEYS for n in names):
        raise CellError(f"unknown setting parameter {parameter!r} level {level!r}")
    for name, value in zip(names, levels, strict=True):
        wind[_WIND_KEYS[name]] = float(value)
    return changed, wind


def harmonized_overrides(
    overrides: dict[str, Any], airflow: dict[str, Any], wind: dict[str, float],
) -> dict[str, Any]:
    """Committed overrides with each supply group's declared OA fraction."""
    out = copy.deepcopy(overrides)
    oa_map = dict(out.get("oa_fraction") or {})
    for group in supply_groups(airflow):
        oa_map[str(group["id"])] = _group_oa(group, airflow)
    out["oa_fraction"] = oa_map
    out.update(wind)
    return out


def declare_terminal_oa(
    entries: list[dict[str, Any]], airflow: dict[str, Any],
) -> list[dict[str, Any]]:
    """Path-map copy whose AHS terminals carry their group's declared OA."""
    room_oa: dict[str, float] = {}
    for group in supply_groups(airflow):
        for room in group.get("rooms") or []:
            room_oa[str(room)] = _group_oa(group, airflow)
    out = []
    for entry in entries:
        row = dict(entry)
        kind = str(row.get("kind", ""))
        room = None
        if kind == "ahs_supply":
            room = row["to_zone"]
        elif kind == "ahs_return":
            room = row["from_zone"]
        if room in room_oa:
            row["declared_oa_fraction"] = room_oa[room]
        out.append(row)
    return out


def declared_oa_of_supply(
    engine: ContamTransportEngine, airflow: dict[str, Any],
) -> float | None:
    """Declared OA fraction weighted by declared supply (ach x V x duty)."""
    weighted = 0.0
    total = 0.0
    for group in supply_groups(airflow):
        volume = sum(
            engine.zone_nodes[r].volume_m3
            for r in group.get("rooms") or [] if r in engine.zone_nodes
        )
        flow = float(group.get("ach", DEFAULT_ACH)) * volume * _group_duty(group, airflow)
        weighted += min(max(_group_oa(group, airflow), 0.0), 1.0) * flow
        total += flow
    return weighted / total if total > _FLOW_EPS else None


# ── clocks ────────────────────────────────────────────────────────────────


class PhaseClock:
    """Wall, parent CPU and child CPU of named phases, never summed."""

    def __init__(self) -> None:
        self.phases: dict[str, dict[str, int]] = {}

    @staticmethod
    def _now() -> tuple[int, int, int]:
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        child = int(round((usage.ru_utime + usage.ru_stime) * 1e9))
        return time.perf_counter_ns(), time.process_time_ns(), child

    def run(self, phase: str, func: Any, *args: Any) -> Any:
        wall0, cpu0, child0 = self._now()
        result = func(*args)
        wall1, cpu1, child1 = self._now()
        self.phases[phase] = {
            "wall_ns": wall1 - wall0,
            "cpu_parent_ns": cpu1 - cpu0,
            "cpu_child_ns": child1 - child0,
        }
        return result


# ── fields ────────────────────────────────────────────────────────────────


def weather_record(prj_text: str) -> dict[str, float] | None:
    """``Ws``/``Wd`` of the steady weather record of a PRJ, when present."""
    for line in prj_text.splitlines():
        if line.rstrip().endswith(_WEATHER_MARK):
            parts = line.split()
            return {"ws_m_s": float(parts[2]), "wd_deg": float(parts[3])}
    return None


def write_prj(prj_text: str, tmp_dir: str) -> str:
    """Write the PRJ into the cell's temporary directory."""
    prj_path = os.path.join(tmp_dir, "platform.prj")
    with validated_open(
        prj_path, "w", allowed_roots=(_REPO_ROOT, tmp_dir), encoding="utf-8",
    ) as fh:
        fh.write(prj_text)
    return prj_path


def read_sim(
    sim_path: str, tmp_dir: str,
) -> tuple[dict[int, float], dict[int, float], dict[str, Any]]:
    """Decode one SIM: flows, dP and the file digest."""
    with validated_open(sim_path, "rb", allowed_roots=(_REPO_ROOT, tmp_dir)) as fh:
        sim_sha = hashlib.sha256(fh.read()).hexdigest()
    sim = SimResults(sim_path, allowed_roots=(_REPO_ROOT, tmp_dir))
    return sim.path_volumetric_flow_m3h(), read_path_dp(sim), {"sim_sha256": sim_sha}


def field_sha256(flows: dict[int, float]) -> str:
    """Digest of the solved flow field (path number and flow, in order)."""
    numbers = np.array(sorted(flows), dtype="<i8")
    values = np.array([flows[n] for n in sorted(flows)], dtype="<f8")
    return hashlib.sha256(numbers.tobytes() + values.tobytes()).hexdigest()


def _real_zones(engine: ContamTransportEngine) -> dict[str, float]:
    return {zid: engine.zone_nodes[zid].volume_m3 for zid in engine._real_zone_ids}


def _metric(value: Any, unit: str, status: str = OK, reason: str = "") -> dict[str, Any]:
    return {"value": value, "unit": unit, "status": status, "reason": reason}


def _blank(unit: str, status: str, reason: str) -> dict[str, Any]:
    return _metric(None, unit, status, reason)


def _add(target: dict[str, float], zone: str, amount: float) -> None:
    if zone in target:
        target[zone] += amount


class _FieldSums:
    """Whole-hull sums of one airflow field; zone detail never leaves here."""

    def __init__(self, zones: dict[str, float]) -> None:
        self.net = dict.fromkeys(zones, 0.0)
        self.totals = dict.fromkeys(
            ("supply", "return", "inward", "outward", "interzone",
             "ahs_oa", "ahs_exhaust", "ahs_recirc"), 0.0,
        )
        self.ahs_system_nonzero = 0

    def boundary(self, zone: str, inward_flow: float) -> None:
        key = "inward" if inward_flow > 0 else "outward"
        self.totals[key] += abs(inward_flow)
        _add(self.net, zone, inward_flow)

    def interzone(self, src: str, dst: str, flow: float) -> None:
        self.totals["interzone"] += abs(flow)
        _add(self.net, src, -flow)
        _add(self.net, dst, flow)

    def metrics(self) -> dict[str, dict[str, Any]]:
        t = self.totals
        residuals = np.array(list(self.net.values()), dtype=float)
        return {
            "supply_total_m3h": _metric(t["supply"], "m3/h"),
            "return_total_m3h": _metric(t["return"], "m3/h"),
            "ambient_inward_total_m3h": _metric(t["inward"], "m3/h"),
            "ambient_outward_total_m3h": _metric(t["outward"], "m3/h"),
            "interzone_gross_m3h": _metric(t["interzone"], "m3/h"),
            "hull_balance_residual_m3h": _metric(float(residuals.sum()), "m3/h"),
            "max_abs_zone_balance_residual_m3h": _metric(
                float(np.abs(residuals).max()) if residuals.size else 0.0, "m3/h",
            ),
        }


def _contamx_entry(sums: _FieldSums, entry: dict[str, Any], flow: float) -> None:
    kind = str(entry.get("kind", ""))
    src, dst = entry["from_zone"], entry["to_zone"]
    if kind == "ahs_supply":
        sums.totals["supply"] += abs(flow)
        _add(sums.net, dst, abs(flow))
    elif kind == "ahs_return":
        sums.totals["return"] += abs(flow)
        _add(sums.net, src, -abs(flow))
    elif kind in AHS_SYSTEM_KINDS:
        sums.totals[kind] += abs(flow)
        sums.ahs_system_nonzero += int(abs(flow) > _FLOW_EPS)
    elif src in sums.net and dst in sums.net:
        sums.interzone(src, dst, flow)
    elif src in sums.net:
        sums.boundary(src, -flow)
    elif dst in sums.net:
        sums.boundary(dst, flow)


def _pressure_metrics(
    entries: list[dict[str, Any]], dps: dict[int, float],
) -> dict[str, dict[str, Any]]:
    values = [dps.get(int(e["path_nr"])) for e in entries]
    solved = np.array(
        [abs(v) for v in values if v is not None and np.isfinite(v)], dtype=float,
    )
    out = {"pressure_rows_unsolved": _metric(len(values) - int(solved.size), "count")}
    stats = (
        ("pressure_abs_dp_median_pa", 50.0),
        ("pressure_abs_dp_p95_pa", 95.0),
        ("pressure_abs_dp_max_pa", 100.0),
    )
    for name, pct in stats:
        out[name] = (
            _metric(float(np.percentile(solved, pct)), "Pa") if solved.size
            else _blank("Pa", "failed", "no solved path pressure")
        )
    return out


def contamx_solved_block(
    zones: dict[str, float], entries: list[dict[str, Any]],
    flows: dict[int, float], dps: dict[int, float],
) -> dict[str, dict[str, Any]]:
    """Aggregate ``solved_airflow`` block of one ContamX field."""
    sums = _FieldSums(zones)
    for entry in entries:
        _contamx_entry(sums, entry, float(flows.get(int(entry["path_nr"]), 0.0)))
    out = sums.metrics()
    system_count = sum(str(e.get("kind", "")) in AHS_SYSTEM_KINDS for e in entries)
    out["ahs_system_path_count"] = _metric(system_count, "count")
    out["ahs_system_path_nonzero_count"] = _metric(sums.ahs_system_nonzero, "count")
    if system_count and sums.ahs_system_nonzero == 0:
        out["outdoor_air_total_m3h"] = _blank("m3/h", UNIMPLEMENTED, REASON_AHS_UNRESOLVED)
        out["exhaust_total_m3h"] = _blank("m3/h", UNIMPLEMENTED, REASON_AHS_UNRESOLVED)
    else:
        out["outdoor_air_total_m3h"] = _metric(sums.totals["ahs_oa"], "m3/h")
        out["exhaust_total_m3h"] = _metric(sums.totals["ahs_exhaust"], "m3/h")
    out.update(_pressure_metrics(entries, dps))
    return out


def native_solved_block(
    engine: ContamTransportEngine, airflow: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Aggregate ``solved_airflow`` block of the native prescribed field."""
    zones = _real_zones(engine)
    sums = _FieldSums(zones)
    supply_plenums = {f"{PLENUM_PREFIX}{g['id']}" for g in supply_groups(airflow)}
    recirculated = 0.0
    for path in engine.airflow_paths:
        flow = float(path.flow_rate_m3h)
        if path.path_type == PATH_TYPE_HVAC_RETURN:
            sums.totals["return"] += flow
            if path.to_zone in supply_plenums:
                sums.totals["supply"] += flow
            else:
                _add(sums.net, path.from_zone, -flow)
        elif path.path_type == PATH_TYPE_HVAC_SUPPLY:
            recirculated += flow
        elif path.sink:
            sums.boundary(path.from_zone, -flow)
            if path.exchange:
                sums.boundary(path.from_zone, flow)
        else:
            sums.interzone(path.from_zone, path.to_zone, flow)
    out = sums.metrics()
    out["outdoor_air_total_m3h"] = _metric(
        sums.totals["supply"] - recirculated, "m3/h", OK, REASON_PRESCRIBED,
    )
    out["exhaust_total_m3h"] = _metric(
        sums.totals["return"] - recirculated, "m3/h", OK, REASON_PRESCRIBED,
    )
    for name, unit in (
        ("pressure_abs_dp_median_pa", "Pa"), ("pressure_abs_dp_p95_pa", "Pa"),
        ("pressure_abs_dp_max_pa", "Pa"), ("pressure_rows_unsolved", "count"),
    ):
        out[name] = _blank(unit, NOT_APPLICABLE, REASON_NATIVE_PRESSURE)
    return out


# ── downstream (shared model, identical for every lane) ───────────────────


def downstream_block(
    engine: ContamTransportEngine, supply_total_m3h: float,
) -> dict[str, dict[str, Any]]:
    """Aggregate mixing/transport metrics of the shared mass-balance operator.

    ``supply_total_m3h`` is the lane's delivered terminal supply (from its
    ``solved_airflow`` block); every other input is the engine itself.
    """
    zones = _real_zones(engine)
    volume = np.array(list(zones.values()), dtype=float)
    total_volume = float(volume.sum())
    operator = engine._build_decay_free_operator()
    loss_weight = -(operator.T @ np.ones(len(volume)))
    returns = sum(
        p.flow_rate_m3h for p in engine.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_RETURN
    )
    recirculated = sum(
        p.flow_rate_m3h for p in engine.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    )
    sinks = sum(p.flow_rate_m3h for p in engine.airflow_paths if p.sink)
    filtered_other = sum(
        p.flow_rate_m3h for p in engine.airflow_paths
        if p.filtered and not p.sink and p.path_type != PATH_TYPE_HVAC_SUPPLY
    )
    removal_no_filter = returns - recirculated + sinks
    removal_with_filter = float(loss_weight @ volume)
    parts = removal_no_filter + engine.filter_efficiency * (recirculated + filtered_other)

    n = len(volume)
    block = np.zeros((2 * n, 2 * n))
    block[:n, :n] = operator
    block[:n, n:] = np.eye(n)
    propagated = expm(block * TRACER_HORIZON_H)
    mass_end = propagated[:n, :n] @ volume
    mass_integral = propagated[:n, n:] @ volume
    closure = abs(
        total_volume - float(mass_end.sum()) - float(loss_weight @ mass_integral)
    ) / total_volume

    def _ratio(num: float, den: float) -> dict[str, Any]:
        if den <= _FLOW_EPS:
            return _blank("1", NOT_APPLICABLE, "no delivered supply on this hull")
        return _metric(num / den, "1")

    return {
        "zone_count": _metric(n, "count"),
        "total_zone_volume_m3": _metric(total_volume, "m3"),
        "return_leg_total_m3h": _metric(returns, "m3/h"),
        "recirculated_supply_leg_total_m3h": _metric(recirculated, "m3/h"),
        "nonrecirculated_return_m3h": _metric(returns - recirculated, "m3/h"),
        "outdoor_air_derived_m3h": _metric(supply_total_m3h - recirculated, "m3/h"),
        "effective_outdoor_air_fraction_of_supply": _ratio(
            supply_total_m3h - recirculated, supply_total_m3h,
        ),
        "boundary_sink_total_m3h": _metric(sinks, "m3/h"),
        "clean_air_equivalent_no_filter_m3h": _metric(removal_no_filter, "m3/h"),
        "clean_air_equivalent_with_filter_m3h": _metric(removal_with_filter, "m3/h"),
        "operator_parts_residual_m3h": _metric(removal_with_filter - parts, "m3/h"),
        "whole_hull_air_change_1_per_h": _metric(removal_no_filter / total_volume, "1/h"),
        "uniform_tracer_material_time_h": _metric(
            float(mass_integral.sum()) / total_volume, "h",
        ),
        "uniform_tracer_closure_error": _metric(closure, "1"),
    }


# ── lanes ─────────────────────────────────────────────────────────────────


def _native_engine(spatial: dict[str, Any], airflow: dict[str, Any]) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial_layout=spatial, air_flow_paths=airflow,
        filter_efficiency=FILTER_EFFICIENCY, natural_decay_rate=0.0,
    )


def _contamx_engine(
    spatial: dict[str, Any], entries: list[dict[str, Any]],
    flows: dict[int, float], airflow: dict[str, Any],
) -> ContamXTransportEngine:
    return ContamXTransportEngine(
        spatial_layout=spatial, path_map=entries, path_flows_m3h=flows,
        filter_efficiency=FILTER_EFFICIENCY, natural_decay_rate=0.0,
        path_map_entries=entries,
        oa_fraction=float(airflow.get("oa_fraction", 0.2)),
        envelope_leak_mode=ENVELOPE_LEAK_MODE,
    )


def _export(
    lane: str, hull: str, inputs: dict[str, Any], airflow: dict[str, Any],
    wind: dict[str, float],
) -> tuple[str, list[dict[str, Any]]]:
    if lane == LANE_AUTHORED:
        with validated_open(
            _platform_path(hull, "contam/platform.prj"), "r",
            allowed_roots=(_REPO_ROOT,), encoding="utf-8",
        ) as fh:
            return fh.read(), _read_json(_platform_path(hull, "contam/path_map.json"))
    overrides = inputs["overrides"]
    if lane == LANE_COMMISSIONED:
        overrides = harmonized_overrides(overrides, airflow, wind)
    prj_text, entries = export_prj_with_path_map(
        inputs["spatial"], airflow, hobbyist=True, overrides=overrides,
        filter_efficiency=FILTER_EFFICIENCY, ahs_terminal_mode="commissioned",
    )
    if lane == LANE_COMMISSIONED:
        entries = declare_terminal_oa(entries, airflow)
    return prj_text, entries


def _terminal_declared(entries: list[dict[str, Any]], kind: str) -> float | None:
    values = [
        e.get("declared_flow_m3h") for e in entries if str(e.get("kind", "")) == kind
    ]
    if not values or any(v is None for v in values):
        return None
    return float(sum(float(v) for v in values))


def _contamx_realization(
    lane: str, hull: str, inputs: dict[str, Any], wind: dict[str, float],
    prj_text: str, entries: list[dict[str, Any]], flows: dict[int, float],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "prj_sha256": hashlib.sha256(prj_text.encode("utf-8")).hexdigest(),
        "field_sha256": field_sha256(flows),
        "path_map_entry_count": len(entries),
        "solved_path_count": len(flows),
        "weather_record": weather_record(prj_text),
        "wind_profile_boundary_path_count": sum(
            str(e.get("kind", "")) in WIND_PROFILE_KINDS for e in entries
        ),
        "declared_terminal_supply_m3h": _terminal_declared(entries, "ahs_supply"),
        "declared_terminal_return_m3h": _terminal_declared(entries, "ahs_return"),
        "ahs_group_count": len(
            {int(e.get("ahs_nr") or 0) for e in entries} - {0},
        ),
    }
    if lane == LANE_AUTHORED:
        with validated_open(
            _platform_path(hull, "contam/platform.prj"), "rb", allowed_roots=(_REPO_ROOT,),
        ) as fh:
            record["prj_file_sha256"] = hashlib.sha256(fh.read()).hexdigest()
    else:
        overrides = dict(inputs["overrides"])
        if lane == LANE_COMMISSIONED:
            overrides.update(wind)
        speed, direction = resolve_relative_wind(overrides)
        record["weather_requested"] = {"ws_m_s": speed, "wd_deg": direction}
    return record


def _run_native(
    clock: PhaseClock, inputs: dict[str, Any], airflow: dict[str, Any],
) -> tuple[ContamTransportEngine, dict[str, Any], dict[str, Any]]:
    engine = clock.run("native_construct", _native_engine, inputs["spatial"], airflow)
    solved = clock.run("field_reduce", native_solved_block, engine, airflow)
    return engine, solved, {"path_count": len(engine.airflow_paths)}


def _export_to_disk(
    args: argparse.Namespace, inputs: dict[str, Any], airflow: dict[str, Any],
    wind: dict[str, float], tmp_dir: str,
) -> tuple[str, list[dict[str, Any]], str]:
    prj_text, entries = _export(args.lane, args.hull, inputs, airflow, wind)
    return prj_text, entries, write_prj(prj_text, tmp_dir)


def _import_field(
    sim_path: str, tmp_dir: str, inputs: dict[str, Any],
    entries: list[dict[str, Any]], airflow: dict[str, Any],
) -> tuple[ContamXTransportEngine, dict[int, float], dict[int, float], dict[str, Any]]:
    flows, dps, sim_facts = read_sim(sim_path, tmp_dir)
    engine = _contamx_engine(inputs["spatial"], entries, flows, airflow)
    return engine, flows, dps, sim_facts


def _run_contamx(
    clock: PhaseClock, args: argparse.Namespace, inputs: dict[str, Any],
    airflow: dict[str, Any], wind: dict[str, float],
) -> tuple[ContamTransportEngine, dict[str, Any], dict[str, Any]]:
    """Phases: export (PRJ and path map, written to disk), solve (the ContamX
    subprocess call only), import (SIM read and decode, engine construction)."""
    with tempfile.TemporaryDirectory(prefix="contam_fleet_workup_") as tmp_dir:
        prj_text, entries, prj_path = clock.run(
            "contamx_export", _export_to_disk, args, inputs, airflow, wind, tmp_dir,
        )
        sim_path = clock.run(
            "contamx_solve",
            lambda: run_contamx(
                prj_path, args.binary, timeout_s=args.timeout_s,
                allowed_roots=(_REPO_ROOT, tmp_dir),
            ),
        )
        engine, flows, dps, sim_facts = clock.run(
            "contamx_import", _import_field, sim_path, tmp_dir, inputs, entries, airflow,
        )
    solved = clock.run(
        "field_reduce", contamx_solved_block, _real_zones(engine), entries, flows, dps,
    )
    realization = _contamx_realization(
        args.lane, args.hull, inputs, wind, prj_text, entries, flows,
    )
    realization.update(sim_facts)
    return engine, solved, realization


def run_cell(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one cold cell and return its aggregate record."""
    clock = PhaseClock()
    inputs = clock.run("input_read", load_hull, args.hull)
    wall0, cpu0, child0 = clock._now()
    airflow, wind = apply_setting(inputs["airflow"], args.parameter, args.level)
    if args.lane == LANE_NATIVE:
        engine, solved, realization = _run_native(clock, inputs, airflow)
    elif args.lane in CONTAMX_LANES:
        engine, solved, realization = _run_contamx(clock, args, inputs, airflow, wind)
    else:
        raise CellError(f"unknown lane {args.lane!r}")
    supply = float(solved["supply_total_m3h"]["value"])
    downstream = clock.run("downstream", downstream_block, engine, supply)
    wall1, cpu1, child1 = clock._now()
    clock.phases["end_to_end"] = {
        "wall_ns": wall1 - wall0, "cpu_parent_ns": cpu1 - cpu0,
        "cpu_child_ns": child1 - child0,
    }
    cached = []
    for _ in range(args.cached_repeats):
        repeat = PhaseClock()
        repeat.run("downstream", downstream_block, engine, supply)
        cached.append(repeat.phases["downstream"])
    realization["declared_outdoor_air_fraction_of_supply"] = declared_oa_of_supply(
        engine, airflow,
    )
    realization["supply_group_count"] = len(supply_groups(airflow))
    realization["hvac_group_count"] = len(airflow.get("hvac_zones") or [])
    return {
        "row_id": args.row_id, "hull": args.hull, "lane": args.lane,
        "parameter": args.parameter, "level": args.level,
        "blocks": {BLOCK_SOLVED: solved, BLOCK_DOWNSTREAM: downstream},
        "realization": realization, "phases": clock.phases, "cached": cached,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row-id", required=True)
    parser.add_argument("--hull", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--parameter", required=True)
    parser.add_argument("--level", default="")
    parser.add_argument("--binary", default=None)
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--cached-repeats", type=int, default=0)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.lane in CONTAMX_LANES and not args.binary:
        raise SystemExit("--binary is required on a ContamX lane")
    record = run_cell(args)
    with validated_open(
        args.out, "w", allowed_roots=(_REPO_ROOT, tempfile.gettempdir()), encoding="utf-8",
    ) as fh:
        json.dump(record, fh, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
