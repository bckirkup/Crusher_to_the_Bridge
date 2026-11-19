"""Four-hull fleet-workup canary: settings, blocks, gates, reducer, pins.

No ContamX executable is needed: ContamX fields are small synthetic flow
maps, and the native lane is built from the committed destroyer inputs.
"""
from __future__ import annotations

import argparse
import copy
import filecmp
import json
import os

import pytest

from tools.diag import contam_fleet_workup_cell as cell
from tools.diag import contam_fleet_workup_gates as gates
from tools.diag import contam_fleet_workup_reduce as reduce_mod
from tools.diag import contam_fleet_workup_run as run_mod

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(REPO, "docs/audits/2026-11-19_contam_fleet_workup_protocol/evidence")
HULL = "destroyer_baseline"
OA = "recirculating_supply_group_oa_fraction"
RECIRC = "recirculating_supply_group_recirculated_fraction"


@pytest.fixture(scope="module")
def criteria():
    with open(run_mod.CRITERIA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def inputs():
    return cell.load_hull(HULL)


def _native(inputs, parameter="none", level=""):
    airflow, _wind = cell.apply_setting(inputs["airflow"], parameter, level)
    engine = cell._native_engine(inputs["spatial"], airflow)
    solved = cell.native_solved_block(engine, airflow)
    down = cell.downstream_block(engine, solved["supply_total_m3h"]["value"])
    return engine, airflow, solved, down


# ── frozen design ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", sorted(os.listdir(EVIDENCE)))
def test_frozen_copy_is_byte_identical_to_the_design(name):
    assert filecmp.cmp(
        os.path.join(EVIDENCE, name), os.path.join(run_mod.FROZEN_DIR, name), shallow=False,
    )


def test_design_pins_and_canary_counts_hold(criteria):
    assert run_mod.verify_design(criteria)
    rows = run_mod.canary_rows(criteria)
    assert len(rows) == 112
    assert sum(r["planned_status"] == "planned_execute" for r in rows) == 77


def test_a_changed_design_pin_is_refused(criteria):
    tampered = copy.deepcopy(criteria)
    tampered["frozen_design_sha256"]["run_matrix.csv"] = "0" * 64
    with pytest.raises(run_mod.RunError):
        run_mod.verify_design(tampered)


def test_a_different_canary_count_is_refused(criteria):
    tampered = copy.deepcopy(criteria)
    tampered["canary"]["hulls"] = tampered["canary"]["hulls"][:3]
    with pytest.raises(run_mod.RunError):
        run_mod.canary_rows(tampered)


def test_wrong_solver_bytes_are_refused(criteria, tmp_path):
    fake = tmp_path / "contamx3"
    fake.write_bytes(b"not the pinned executable")
    args = argparse.Namespace(binary=str(fake), contamx_uri=None)
    with pytest.raises(run_mod.RunError):
        run_mod.provision_contamx(args, criteria["contamx"], str(tmp_path))


def test_canary_inputs_match_the_manifest(criteria):
    assert run_mod.verify_inputs(criteria["canary"]["hulls"])


# ── settings ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("factor", [0.5, 1.0, 1.5])
def test_duty_setting_scales_native_supply_by_the_factor(inputs, factor):
    base = _native(inputs)[2]["supply_total_m3h"]["value"]
    moved = _native(inputs, "supply_group_hvac_duty", str(factor))[2]["supply_total_m3h"]["value"]
    assert moved == pytest.approx(base * factor, rel=1e-12)


def test_ach_and_duty_are_one_parameter_on_the_native_lane(inputs):
    duty = _native(inputs, "supply_group_hvac_duty", "1.5")[3]
    ach = _native(inputs, "supply_group_ach", "1.5")[3]
    for name, metric in duty.items():
        assert ach[name]["value"] == pytest.approx(metric["value"], rel=1e-12), name


@pytest.mark.parametrize(
    ("parameter", "expected"), [(OA, 0.1), (RECIRC, 0.6)],
)
def test_outdoor_air_settings_reach_the_operator_and_leave_terminals(inputs, parameter, expected):
    _e, _a, base_solved, base_down = _native(inputs)
    engine, airflow, solved, down = _native(inputs, parameter, "0.5")
    assert down["effective_outdoor_air_fraction_of_supply"]["value"] == pytest.approx(expected)
    assert cell.declared_oa_of_supply(engine, airflow) == pytest.approx(expected)
    assert solved["supply_total_m3h"]["value"] == pytest.approx(
        base_solved["supply_total_m3h"]["value"], rel=1e-12)
    assert solved["return_total_m3h"]["value"] == pytest.approx(
        base_solved["return_total_m3h"]["value"], rel=1e-12)
    assert down["uniform_tracer_material_time_h"]["value"] != pytest.approx(
        base_down["uniform_tracer_material_time_h"]["value"], rel=1e-6)


def test_wind_settings_only_set_override_keys(inputs):
    airflow, wind = cell.apply_setting(
        inputs["airflow"], "relative_wind_speed+relative_wind_direction", "10+90")
    assert airflow == inputs["airflow"]
    assert wind == {"relative_wind_speed_m_s": 10.0, "relative_wind_direction_deg": 90.0}


def test_unknown_setting_is_an_error(inputs):
    with pytest.raises(cell.CellError):
        cell.apply_setting(inputs["airflow"], "hatch_state", "open")


def test_harmonization_copies_declared_oa_and_leaves_committed_inputs(inputs):
    before = copy.deepcopy(inputs)
    airflow, wind = cell.apply_setting(inputs["airflow"], OA, "0.5")
    overrides = cell.harmonized_overrides(inputs["overrides"], airflow, wind)
    groups = cell.supply_groups(airflow)
    assert groups
    for group in groups:
        assert overrides["oa_fraction"][group["id"]] == pytest.approx(0.1)
    room = groups[0]["rooms"][0]
    entries = cell.declare_terminal_oa(
        [{"kind": "ahs_supply", "to_zone": room, "from_zone": "ahs1(Sup)"},
         {"kind": "passageway", "to_zone": room, "from_zone": "elsewhere"}], airflow)
    assert entries[0]["declared_oa_fraction"] == pytest.approx(0.1)
    assert "declared_oa_fraction" not in entries[1]
    assert inputs == before


# ── blocks ────────────────────────────────────────────────────────────────


def _entries():
    return [
        {"path_nr": 1, "kind": "ahs_supply", "from_zone": "ahs1(Sup)", "to_zone": "A", "ahs_nr": 1},
        {"path_nr": 2, "kind": "ahs_return", "from_zone": "A", "to_zone": "ahs1(Ret)", "ahs_nr": 1},
        {"path_nr": 3, "kind": "ahs_oa", "from_zone": "ambient", "to_zone": "ahs1(Sup)", "ahs_nr": 1},
        {"path_nr": 4, "kind": "ahs_exhaust", "from_zone": "ahs1(Ret)", "to_zone": "ambient", "ahs_nr": 1},
        {"path_nr": 5, "kind": "ahs_recirc", "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "ahs_nr": 1},
        {"path_nr": 6, "kind": "envelope_leak", "from_zone": "A", "to_zone": "ambient", "ahs_nr": 0},
        {"path_nr": 7, "kind": "passageway", "from_zone": "A", "to_zone": "B", "ahs_nr": 0},
        {"path_nr": 8, "kind": "envelope_leak", "from_zone": "B", "to_zone": "ambient", "ahs_nr": 0},
    ]


def test_unresolved_ahs_paths_are_blank_with_a_reason_never_zero():
    flows = {1: 100.0, 2: 120.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: -30.0, 7: 10.0, 8: 10.0}
    block = cell.contamx_solved_block(
        {"A": 50.0, "B": 50.0}, _entries(), flows, dict.fromkeys(flows, 1.0))
    for name in ("outdoor_air_total_m3h", "exhaust_total_m3h"):
        assert block[name]["value"] is None
        assert block[name]["status"] == "unimplemented"
        assert block[name]["reason"]
    assert block["ambient_inward_total_m3h"]["value"] == pytest.approx(30.0)
    assert block["ambient_outward_total_m3h"]["value"] == pytest.approx(10.0)
    assert block["interzone_gross_m3h"]["value"] == pytest.approx(10.0)
    assert block["hull_balance_residual_m3h"]["value"] == pytest.approx(0.0, abs=1e-12)
    assert block["max_abs_zone_balance_residual_m3h"]["value"] == pytest.approx(0.0, abs=1e-12)


def test_resolved_ahs_paths_are_reported_as_numbers():
    flows = {1: 100.0, 2: 100.0, 3: 20.0, 4: 20.0, 5: 80.0, 6: 0.0, 7: 0.0, 8: 0.0}
    block = cell.contamx_solved_block(
        {"A": 50.0, "B": 50.0}, _entries(), flows, dict.fromkeys(flows, 1.0))
    assert block["outdoor_air_total_m3h"]["value"] == pytest.approx(20.0)
    assert block["exhaust_total_m3h"]["status"] == "ok"


def test_unsolved_pressure_rows_are_counted():
    flows = dict.fromkeys(range(1, 9), 1.0)
    block = cell.contamx_solved_block({"A": 1.0, "B": 1.0}, _entries(), flows, {1: 2.0, 2: -4.0})
    assert block["pressure_rows_unsolved"]["value"] == 6
    assert block["pressure_abs_dp_max_pa"]["value"] == pytest.approx(4.0)


def test_native_pressure_is_not_applicable_and_blank(inputs):
    solved = _native(inputs)[2]
    assert solved["pressure_abs_dp_max_pa"]["value"] is None
    assert solved["pressure_abs_dp_max_pa"]["status"] == "not_applicable"


def test_downstream_operator_closes_and_equals_the_sum_of_its_parts(inputs):
    down = _native(inputs)[3]
    assert down["uniform_tracer_closure_error"]["value"] <= 1e-9
    assert abs(down["operator_parts_residual_m3h"]["value"]) <= 1e-9 * down[
        "clean_air_equivalent_with_filter_m3h"]["value"]
    assert 0.0 < down["uniform_tracer_material_time_h"]["value"] < cell.TRACER_HORIZON_H


def test_field_digest_changes_with_any_flow():
    assert cell.field_sha256({1: 1.0, 2: 2.0}) == cell.field_sha256({2: 2.0, 1: 1.0})
    assert cell.field_sha256({1: 1.0, 2: 2.0}) != cell.field_sha256({1: 1.0, 2: 2.0000001})


def test_weather_record_is_read_from_the_steady_line():
    text = "x\n293.150 101325.0  10.000  90.0 0.000 1 2 0 0 1 ! steady simulation\n"
    assert cell.weather_record(text) == {"ws_m_s": 10.0, "wd_deg": 90.0}
    assert cell.weather_record("no weather here") is None


# ── gates ─────────────────────────────────────────────────────────────────


def _fake(solved, down, real=None):
    def block(values):
        return {k: {"value": v, "unit": "", "status": "ok", "reason": ""} for k, v in values.items()}
    return {"cell": {"blocks": {gates.SOLVED: block(solved), gates.DOWNSTREAM: block(down)},
                     "realization": real or {}}}


def _oa_pair(recirc_after, supply_after=100.0):
    base = _fake({"supply_total_m3h": 100.0, "return_total_m3h": 100.0},
                 {"effective_outdoor_air_fraction_of_supply": 0.2,
                  "clean_air_equivalent_with_filter_m3h": 44.0,
                  "recirculated_supply_leg_total_m3h": 80.0})
    after = _fake({"supply_total_m3h": supply_after, "return_total_m3h": 100.0},
                  {"effective_outdoor_air_fraction_of_supply": 1.0 - recirc_after / 100.0,
                   "clean_air_equivalent_with_filter_m3h": 100.0 - 0.7 * recirc_after,
                   "recirculated_supply_leg_total_m3h": recirc_after})
    return base, after


def _oa_failures(criteria, base, after):
    ledger = gates._Ledger()
    row = {"row_id": "h|l|s", "lane": gates.NATIVE}
    gates._outdoor_air(ledger, row, after, base, criteria["tolerances"], 0.3)
    return {c["gate"] for c in ledger.checks if not c["passed"]}


def test_oa_gate_passes_when_mixing_moves_and_terminals_do_not(criteria):
    assert _oa_failures(criteria, *_oa_pair(90.0)) == set()


def test_oa_gate_fails_when_the_setting_is_only_a_configuration_echo(criteria):
    assert "oa_setting_reaches_mixing" in _oa_failures(criteria, *_oa_pair(80.0))


def test_oa_gate_fails_when_terminal_flow_moves(criteria):
    assert "oa_only_terminal_flow_unchanged" in _oa_failures(criteria, *_oa_pair(90.0, 101.0))


@pytest.mark.parametrize(("ratio", "passes"), [(1.5, True), (1.5004, True), (1.52, False)])
def test_duty_gate_grades_the_solved_ratio(criteria, ratio, passes):
    base = _fake({"supply_total_m3h": 100.0}, {}, {"declared_terminal_supply_m3h": 100.0})
    after = _fake({"supply_total_m3h": 100.0 * ratio}, {}, {"declared_terminal_supply_m3h": 150.0})
    ledger = gates._Ledger()
    row = {"row_id": "h|l|s", "lane": gates.COMMISSIONED, "level": "1.5"}
    gates._duty(ledger, row, after, base, criteria["tolerances"])
    realized = [c for c in ledger.checks if c["gate"] == "duty_ach_realized"]
    assert realized[0]["passed"] is passes


def _weather_cells(field_after, inward_after, record):
    real = {"weather_requested": {"ws_m_s": 1.0, "wd_deg": 0.0}, "field_sha256": "a"}
    base = _fake({"ambient_inward_total_m3h": 10.0}, {}, real)
    after = _fake({"ambient_inward_total_m3h": inward_after}, {},
                  {"weather_record": record, "wind_profile_boundary_path_count": 3,
                   "field_sha256": field_after})
    return base, after


def _weather_failures(criteria, base, after):
    ledger = gates._Ledger()
    row = {"row_id": "h|l|wind_speed_10", "setting_id": "wind_speed_10",
           "parameter": "relative_wind_speed", "level": "10"}
    gates._weather(ledger, row, after, base, criteria["tolerances"])
    return {c["gate"] for c in ledger.checks if not c["passed"]}


def test_weather_gate_passes_when_record_and_solved_field_move(criteria):
    cells = _weather_cells("b", 25.0, {"ws_m_s": 10.0, "wd_deg": 0.0})
    assert _weather_failures(criteria, *cells) == set()


def test_weather_gate_fails_when_only_the_record_changes(criteria):
    cells = _weather_cells("a", 10.0, {"ws_m_s": 10.0, "wd_deg": 0.0})
    assert _weather_failures(criteria, *cells) == {"weather_applied_in_solver"}


def test_weather_gate_fails_when_the_level_is_not_exported(criteria):
    cells = _weather_cells("b", 25.0, {"ws_m_s": 1.0, "wd_deg": 0.0})
    assert _weather_failures(criteria, *cells) == {"weather_record_exported"}


def test_blank_metric_with_a_number_or_ok_metric_without_one_fails():
    record = _fake({"x": 1.0}, {"y": 2.0})
    record["cell"]["blocks"][gates.SOLVED]["x"]["status"] = "unimplemented"
    ledger = gates._Ledger()
    gates._blank_is_not_zero(ledger, "r", record)
    failed = [c for c in ledger.checks if not c["passed"]]
    assert [c["block"] for c in failed] == [gates.SOLVED]


# ── order and reducer ─────────────────────────────────────────────────────


def test_lanes_alternate_first_position_by_repeat():
    rows = [{"lane": "contamx_commissioned_export"}, {"lane": "native_prescribed"}]
    assert run_mod.lane_order(rows, 0)[0]["lane"] == "native_prescribed"
    assert run_mod.lane_order(rows, 1)[0]["lane"] == "contamx_commissioned_export"


def test_settings_run_hull_sorted_then_matrix_order(criteria):
    rows = run_mod.canary_rows(criteria)
    order = run_mod.settings_in_order(rows)
    hulls = [h for h, _s in order]
    assert hulls == sorted(hulls)
    assert order[0] == ("destroyer_baseline", "baseline")
    assert len(order) == len(set(order))


def _record(kind, index, value, status="ok"):
    out = {"row_id": "h|native_prescribed|baseline", "repeat_kind": kind, "repeat_index": index,
           "observed_status": status, "reason": "" if status == "ok" else "boom",
           "process_wall_ns": 1000 + index, "loadavg_1m": 0.0}
    if status == "ok":
        fake = _fake({"m": value}, {"d": value})
        fake["cell"]["phases"] = {"downstream": {"wall_ns": 10 * (index + 1), "cpu_parent_ns": 1,
                                                 "cpu_child_ns": 0}}
        fake["cell"]["cached"] = []
        out.update(fake)
    return out


def test_row_status_is_measured_unchanged_only_within_tolerance():
    row = {"row_id": "r", "planned_status": "planned_execute", "setting_id": "x", "reason": ""}
    base = _record("measured", 0, 1.0)
    same = reduce_mod.row_status(row, [_record("measured", 0, 1.0 + 1e-12)], base, 1e-9)
    moved = reduce_mod.row_status(row, [_record("measured", 0, 1.01)], base, 1e-9)
    assert same["overall"] == "unchanged"
    assert moved["overall"] == "ok"


def test_row_status_keeps_planned_nonresponse_and_reports_failures():
    planned = {"row_id": "r", "planned_status": "structural_nonresponse", "setting_id": "x",
               "reason": "no weather input"}
    assert reduce_mod.row_status(planned, [], None, 1e-9)["overall"] == "structural_nonresponse"
    executed = {**planned, "planned_status": "planned_execute"}
    failed = reduce_mod.row_status(executed, [_record("measured", 0, 0.0, "timeout")], None, 1e-9)
    assert failed["overall"] == "timeout"
    assert failed["reason"] == "boom"


def test_timing_spread_is_robust_and_exact_on_a_known_sample():
    spread = reduce_mod._spread([10, 20, 30, 40, 1000])
    assert spread["wall_median_ns"] == 30
    assert spread["wall_min_ns"] == 10
    assert spread["wall_max_ns"] == 1000
    assert spread["wall_iqr_ns"] == 20
    assert spread["wall_mad_ns"] == 10


def test_csv_writer_leaves_missing_values_empty_not_zero(tmp_path):
    path = tmp_path / "t.csv"
    reduce_mod.write_csv(str(path), ("a", "b"), [{"a": None, "b": 0.0}])
    assert path.read_text(encoding="utf-8").splitlines() == ["a,b", ",0.0"]


class _FakeReduction:
    rows = [{"row_id": "h|native_prescribed|baseline", "hull": "h",
             "lane": "native_prescribed", "setting_id": "baseline"}]


def test_timeouts_are_counted_on_every_phase_and_cached_work_leaves_the_cold_total():
    red = _FakeReduction()
    ok = _record("measured", 0, 1.0)
    ok["cell"]["cached"] = [{"wall_ns": 300, "cpu_parent_ns": 1, "cpu_child_ns": 0}]
    timed_out = _record("measured", 1, 0.0, "timeout")
    timed_out["censored"] = 1
    red.cells = [ok, timed_out]
    raw = reduce_mod.timing_raw(red)
    totals = [r["wall_ns"] for r in raw if r["phase"] == reduce_mod.PROCESS_PHASE]
    assert totals == [700, 1001]
    summary = {(s["repeat_kind"], s["phase"]): s for s in reduce_mod.timing_summary(red, raw)}
    assert summary[("measured", "downstream")]["timeouts"] == 1
    assert summary[("measured", "downstream")]["n"] == 1
    assert summary[("measured", reduce_mod.PROCESS_PHASE)]["n"] == 1
