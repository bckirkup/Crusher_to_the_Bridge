#!/usr/bin/env python3
"""Frozen smoke gates of the fleet-workup canary (aggregate only).

Every gate reads what a cell *realized* (solved terminal flow, the operator's
recirculated legs, the solved field digest), not the configuration it was
handed. Tolerances come from ``design/canary_criteria.json``; none is defined
here. A failed gate stops the stage; nothing is timed.
"""
from __future__ import annotations

import math
from typing import Any

SOLVED = "solved_airflow"
DOWNSTREAM = "downstream_mixing"
NATIVE = "native_prescribed"
COMMISSIONED = "contamx_commissioned_export"
AUTHORED = "contamx_authored_bundle"
EXECUTE = "planned_execute"
DUTY_PARAMETERS = ("supply_group_hvac_duty", "supply_group_ach")
OA_PARAMETERS = (
    "recirculating_supply_group_oa_fraction",
    "recirculating_supply_group_recirculated_fraction",
)
WEATHER_FAMILIES = ("weather", "weather_interaction")
WIND_RESPONSE_SETTING = "wind_speed_10"


def value(cell: dict[str, Any], block: str, name: str) -> float | None:
    """A metric's number, or None when it is blank."""
    metric = cell["cell"]["blocks"][block].get(name)
    return None if metric is None else metric["value"]


def rel_diff(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    return abs(a - b) / scale if scale > 0.0 else 0.0


def max_solved_change(cell: dict[str, Any], base: dict[str, Any]) -> float:
    """Largest relative change of any numeric ``solved_airflow`` aggregate."""
    changes = [0.0]
    for name, metric in cell["cell"]["blocks"][SOLVED].items():
        other = base["cell"]["blocks"][SOLVED][name]["value"]
        if metric["value"] is not None and other is not None:
            changes.append(rel_diff(float(metric["value"]), float(other)))
    return max(changes)


class _Ledger:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(self, gate: str, row_id: str, passed: bool, **detail: Any) -> None:
        self.checks.append({"gate": gate, "row_id": row_id, "passed": bool(passed), **detail})


def _blank_is_not_zero(ledger: _Ledger, row_id: str, cell: dict[str, Any]) -> None:
    for block, metrics in cell["cell"]["blocks"].items():
        bad = [n for n, m in metrics.items() if (m["status"] != "ok") != (m["value"] is None)]
        finite = all(
            math.isfinite(float(m["value"])) for m in metrics.values() if m["value"] is not None
        )
        ledger.add("unsupported_is_blank_not_zero", row_id, not bad, block=block, offending=len(bad))
        ledger.add("values_finite", row_id, finite, block=block)


def _structural(
    ledger: _Ledger, row: dict[str, str], cell: dict[str, Any], base: dict[str, Any],
    tol: dict[str, float],
) -> None:
    row_id = row["row_id"]
    closure = value(cell, DOWNSTREAM, "uniform_tracer_closure_error")
    ledger.add("tracer_closure", row_id, closure <= tol["tracer_closure_abs"], measured=closure)
    parts = abs(value(cell, DOWNSTREAM, "operator_parts_residual_m3h"))
    scale = max(1.0, abs(value(cell, DOWNSTREAM, "clean_air_equivalent_with_filter_m3h")))
    ledger.add("operator_sum_of_parts", row_id, parts <= tol["parts_rel"] * scale,
               measured_rel=parts / scale)
    same_zones = value(cell, DOWNSTREAM, "zone_count") == value(base, DOWNSTREAM, "zone_count")
    volume = rel_diff(value(cell, DOWNSTREAM, "total_zone_volume_m3"),
                      value(base, DOWNSTREAM, "total_zone_volume_m3"))
    ledger.add("zones_equal_across_lanes", row_id,
               same_zones and volume <= tol["volume_rel"], volume_rel=volume)
    if row["lane"] == NATIVE:
        return
    real = cell["cell"]["realization"]
    ledger.add("path_map_matches_solved_paths", row_id,
               real["path_map_entry_count"] == real["solved_path_count"])
    ledger.add("ahs_group_count_matches", row_id,
               real["ahs_group_count"] == real["hvac_group_count"],
               ahs=real["ahs_group_count"], groups=real["hvac_group_count"])
    ledger.add("pressure_solved_on_every_path", row_id,
               value(cell, SOLVED, "pressure_rows_unsolved") == 0)


def _duty(
    ledger: _Ledger, row: dict[str, str], cell: dict[str, Any], base: dict[str, Any],
    tol: dict[str, float],
) -> None:
    factor = float(row["level"])
    base_supply = value(base, SOLVED, "supply_total_m3h")
    if not base_supply:
        ledger.add("duty_ach_realized", row["row_id"], False, reason="no baseline supply")
        return
    ratio = value(cell, SOLVED, "supply_total_m3h") / base_supply
    if row["lane"] == NATIVE:
        ledger.add("duty_ach_realized", row["row_id"],
                   rel_diff(ratio, factor) <= tol["native_factor_rel"],
                   realized_ratio=ratio, factor=factor)
        return
    declared = (cell["cell"]["realization"]["declared_terminal_supply_m3h"]
                / base["cell"]["realization"]["declared_terminal_supply_m3h"])
    ledger.add("duty_ach_exported", row["row_id"],
               rel_diff(declared, factor) <= tol["export_factor_rel"],
               exported_ratio=declared, factor=factor)
    ledger.add("duty_ach_realized", row["row_id"],
               rel_diff(ratio, factor) <= tol["solved_factor_rel"],
               realized_ratio=ratio, factor=factor)


def _outdoor_air(
    ledger: _Ledger, row: dict[str, str], cell: dict[str, Any], base: dict[str, Any],
    tol: dict[str, float], filter_efficiency: float,
) -> None:
    row_id = row["row_id"]
    for name in ("supply_total_m3h", "return_total_m3h"):
        change = rel_diff(value(cell, SOLVED, name), value(base, SOLVED, name))
        ledger.add("oa_only_terminal_flow_unchanged", row_id,
                   change <= tol["unchanged_rel"], metric=name, measured_rel=change)
    name = "effective_outdoor_air_fraction_of_supply"
    moved = abs(value(cell, DOWNSTREAM, name) - value(base, DOWNSTREAM, name))
    ledger.add("oa_setting_reaches_mixing", row_id, moved > tol["oa_response_abs"],
               measured_abs=moved)
    d_removal = (value(cell, DOWNSTREAM, "clean_air_equivalent_with_filter_m3h")
                 - value(base, DOWNSTREAM, "clean_air_equivalent_with_filter_m3h"))
    d_recirc = (value(cell, DOWNSTREAM, "recirculated_supply_leg_total_m3h")
                - value(base, DOWNSTREAM, "recirculated_supply_leg_total_m3h"))
    gap = abs(d_removal + (1.0 - filter_efficiency) * d_recirc)
    scale = max(1.0, abs(value(base, DOWNSTREAM, "clean_air_equivalent_with_filter_m3h")))
    ledger.add("oa_change_is_the_only_operator_change", row_id,
               gap <= tol["operator_tie_rel"] * scale, measured_rel=gap / scale)


def _effective_oa(
    ledger: _Ledger, row: dict[str, str], cell: dict[str, Any], tol: dict[str, float],
) -> None:
    declared = cell["cell"]["realization"]["declared_outdoor_air_fraction_of_supply"]
    realized = value(cell, DOWNSTREAM, "effective_outdoor_air_fraction_of_supply")
    if declared is None or realized is None:
        ledger.add("effective_oa_realized", row["row_id"], declared is None and realized is None,
                   reason="no delivered supply")
        return
    limit = tol["native_oa_abs"] if row["lane"] == NATIVE else tol["contamx_oa_abs"]
    ledger.add("effective_oa_realized", row["row_id"], abs(realized - declared) <= limit,
               realized=realized, declared=declared, tolerance=limit)


def _expected_wind(row: dict[str, str], base: dict[str, Any]) -> dict[str, float]:
    expected = dict(base["cell"]["realization"]["weather_requested"])
    keys = {"relative_wind_speed": "ws_m_s", "relative_wind_direction": "wd_deg"}
    for name, level in zip(row["parameter"].split("+"), row["level"].split("+"), strict=True):
        expected[keys[name]] = float(level)
    return expected


def _weather(
    ledger: _Ledger, row: dict[str, str], cell: dict[str, Any], base: dict[str, Any],
    tol: dict[str, float],
) -> None:
    real = cell["cell"]["realization"]
    expected = _expected_wind(row, base)
    record = real["weather_record"] or {}
    echoed = (
        abs(record.get("ws_m_s", math.nan) - expected["ws_m_s"]) <= tol["wind_speed_abs_m_s"]
        and abs(record.get("wd_deg", math.nan) - expected["wd_deg"]) <= tol["wind_direction_abs_deg"]
    )
    ledger.add("weather_record_exported", row["row_id"], echoed, record=record, expected=expected)
    ledger.add("wind_profile_paths_present", row["row_id"],
               real["wind_profile_boundary_path_count"] > 0,
               count=real["wind_profile_boundary_path_count"])
    if row["setting_id"] == WIND_RESPONSE_SETTING:
        change = max_solved_change(cell, base)
        differs = real["field_sha256"] != base["cell"]["realization"]["field_sha256"]
        ledger.add("weather_applied_in_solver", row["row_id"],
                   differs and change > tol["unchanged_rel"], max_aggregate_rel_change=change)


def _row_gates(
    ledger: _Ledger, row: dict[str, str], cell: dict[str, Any],
    bases: dict[str, dict[str, Any]], criteria: dict[str, Any],
) -> None:
    tol = criteria["tolerances"]
    lane_base = bases.get(row["lane"], cell)
    _blank_is_not_zero(ledger, row["row_id"], cell)
    _structural(ledger, row, cell, bases[NATIVE], tol)
    if row["lane"] in (NATIVE, COMMISSIONED):
        _effective_oa(ledger, row, cell, tol)
    if row["parameter"] in DUTY_PARAMETERS:
        _duty(ledger, row, cell, lane_base, tol)
    if row["parameter"] in OA_PARAMETERS:
        _outdoor_air(ledger, row, cell, lane_base, tol, criteria["filter_efficiency"])
    if row["family"] in WEATHER_FAMILIES and row["lane"] == COMMISSIONED:
        _weather(ledger, row, cell, lane_base, tol)
    if row["lane"] == AUTHORED:
        real = cell["cell"]["realization"]
        ledger.add("authored_reference_solved_as_committed", row["row_id"],
                   real["prj_file_sha256"] == criteria["authored_prj_sha256"][row["hull"]])


def evaluate(
    rows: list[dict[str, str]], cells: dict[str, dict[str, Any]], criteria: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate every frozen gate on the smoke cells; aggregate verdict."""
    ledger = _Ledger()
    executed = [r for r in rows if r["planned_status"] == EXECUTE]
    complete = {r["row_id"] for r in executed if cells.get(r["row_id"], {}).get("cell")}
    for row in executed:
        ledger.add("cell_completed", row["row_id"], row["row_id"] in complete,
                   status=cells.get(row["row_id"], {}).get("observed_status", "missing"),
                   reason=cells.get(row["row_id"], {}).get("reason", ""))
    for hull in sorted({r["hull"] for r in executed}):
        hull_rows = [r for r in executed if r["hull"] == hull]
        bases = {
            r["lane"]: cells[r["row_id"]] for r in hull_rows
            if r["setting_id"] == "baseline" and r["row_id"] in complete
        }
        if NATIVE not in bases or COMMISSIONED not in bases:
            ledger.add("baselines_present", hull, False)
            continue
        for row in hull_rows:
            if row["row_id"] in complete:
                _row_gates(ledger, row, cells[row["row_id"]], bases, criteria)
    failed = sorted({c["gate"] for c in ledger.checks if not c["passed"]})
    summary: dict[str, dict[str, int]] = {}
    for check in ledger.checks:
        entry = summary.setdefault(check["gate"], {"passed": 0, "failed": 0})
        entry["passed" if check["passed"] else "failed"] += 1
    return {"passed": not failed, "failed": failed, "summary": summary, "checks": ledger.checks}
