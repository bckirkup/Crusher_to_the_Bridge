"""CONTAM-FIELD-PRESSURE-REVIEW-01: fleet pressure/balance diagnostic (structural)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_runner import SimResults  # noqa: E402
from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from tools.diag import contam_pressure_balance_diagnostic as diag  # noqa: E402

_FIXTURE_SIM = REPO_ROOT / "tests" / "fixtures" / "contam" / "destroyer_baseline.sim"
_LAYOUT = {
    "zones": [
        {"id": "A", "volume_m3": 100.0},
        {"id": "B", "volume_m3": 50.0},
    ]
}
_KNOWN = {"A", "B"}


def _entry(nr: int, kind: str, src: str, dst: str, **extra: Any) -> dict[str, Any]:
    return {
        "path_nr": nr, "kind": kind, "from_zone": src, "to_zone": dst,
        "is_hvac_ducted": False, "ahs_nr": 0, **extra,
    }


def _entries() -> list[dict[str, Any]]:
    return [
        _entry(1, "envelope_leak", "A", "ambient"),
        _entry(2, "envelope_leak", "B", "ambient"),
        _entry(3, "doorway", "A", "B"),
        _entry(4, "Hood_Exhaust", "B", "ambient", sink=True, is_hvac_ducted=True),
        _entry(5, "ahs_supply", "ahs1(Sup)", "A", ahs_nr=1, declared_flow_m3h=100.0),
        _entry(6, "ahs_return", "A", "ahs1(Ret)", ahs_nr=1, declared_flow_m3h=100.0),
        _entry(7, "ahs_return", "B", "ahs2(Ret)", ahs_nr=2, declared_flow_m3h=40.0),
        _entry(8, "ahs_recirc", "ahs1(Ret)", "ahs1(Sup)", ahs_nr=1),
    ]


# Balanced field: B loses 40 (exhaust-only AHS 2) + 30 (hood); 50 arrives from A
# through the doorway and 20 through B's leak; A's leak admits the other 50.
_FLOWS = {1: -50.0, 2: -20.0, 3: 50.0, 4: 30.0, 5: 100.0, 6: 100.0, 7: 40.0, 8: 0.0}
_DPS = {1: -2.0e4, 2: -3.0e3, 3: 4.0, 4: -3.0e3, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0}


def _report() -> dict[str, Any]:
    return diag.analyze_field(_entries(), _FLOWS, _DPS, _KNOWN, top_paths=2)


def test_read_path_dp_aligns_with_decoded_path_numbers() -> None:
    sim = SimResults(str(_FIXTURE_SIM))
    dps = diag.read_path_dp(sim)
    frame = sim.steady_state_frame()
    assert sorted(dps) == sorted(int(nr) for nr in frame.path_nr)
    assert all(abs(dp) < float("inf") for dp in dps.values())


def test_path_class_partitions_every_entry() -> None:
    classes = [diag.path_class(e) for e in _entries()]
    assert classes == [
        diag.CLASS_ENVELOPE, diag.CLASS_ENVELOPE, diag.CLASS_PASSIVE,
        diag.CLASS_EXHAUST_SINK, diag.CLASS_AHS_TERMINAL, diag.CLASS_AHS_TERMINAL,
        diag.CLASS_AHS_TERMINAL, diag.CLASS_AHS_SYSTEM,
    ]


def test_dp_stats_decade_counts_are_monotone() -> None:
    stats = diag.dp_stats([-5.0, 50.0, -500.0, 5.0e4])
    counts = [stats["n_over_pa"][f"{t:g}"] for t in diag.DP_DECADES_PA]
    assert stats["n"] == 4
    assert stats["max_abs_dp_pa"] == pytest.approx(5.0e4)
    assert counts == sorted(counts, reverse=True)
    assert counts[0] == 3


def test_dp_summary_ranks_largest_and_separates_interior() -> None:
    dp = _report()["dp"]
    assert [row["path_nr"] for row in dp["top_paths"]] == [1, 2]
    assert dp["interior"]["n"] == 1
    assert dp["interior"]["max_abs_dp_pa"] == pytest.approx(4.0)
    assert sum(block["n"] for block in dp["by_class"].values()) == dp["all"]["n"]
    assert sum(block["n"] for block in dp["by_kind"].values()) == dp["all"]["n"]


def test_envelope_direction_and_net_flow() -> None:
    envelope = _report()["envelope"]
    assert envelope["inward_count"] == 2
    assert envelope["outward_count"] == 0
    assert envelope["net_inward_m3h"] == pytest.approx(70.0)
    assert envelope["dp"]["max_abs_dp_pa"] == pytest.approx(2.0e4)


def test_outward_leak_reduces_net_inward() -> None:
    flows = dict(_FLOWS)
    flows[2] = 5.0
    envelope = diag.analyze_field(_entries(), flows, _DPS, _KNOWN)["envelope"]
    assert envelope["outward_count"] == 1
    assert envelope["net_inward_m3h"] == pytest.approx(45.0)


def test_ambient_opening_is_classed_apart_from_interior_openings() -> None:
    entries = _entries() + [_entry(9, "ambient_opening", "A", "ambient")]
    flows = {**_FLOWS, 9: -5.0}
    dps = {**_DPS, 9: 1.0e6}
    dp = diag.analyze_field(entries, flows, dps, _KNOWN)["dp"]
    assert dp["interior"]["max_abs_dp_pa"] == pytest.approx(4.0)
    assert dp["by_class"][diag.CLASS_AMBIENT_OPENING]["max_abs_dp_pa"] == pytest.approx(1.0e6)


def test_ahs_imbalance_per_group_and_total() -> None:
    ahs = _report()["ahs"]
    by_nr = {g["ahs_nr"]: g for g in ahs["groups"]}
    assert by_nr[1]["return_minus_supply_m3h"] == pytest.approx(0.0)
    assert by_nr[2]["return_minus_supply_m3h"] == pytest.approx(40.0)
    assert by_nr[2]["declared_return_minus_supply_m3h"] == pytest.approx(40.0)
    assert ahs["return_minus_supply_m3h"] == pytest.approx(40.0)
    assert ahs["exhaust_only_group_count"] == 1
    assert ahs["supply_only_group_count"] == 0


def test_boundary_balance_closes_on_a_conserving_field() -> None:
    boundary = _report()["boundary"]
    assert boundary["exhaust_sink_out_m3h"] == pytest.approx(30.0)
    assert boundary["makeup_demand_m3h"] == pytest.approx(70.0)
    assert boundary["balance_residual_m3h"] == pytest.approx(0.0, abs=1e-9)
    assert boundary["makeup_demand_per_leak_m3h"] == pytest.approx(35.0)


def test_boundary_residual_exposes_a_non_conserving_field() -> None:
    flows = dict(_FLOWS)
    flows[4] = 60.0
    boundary = diag.analyze_field(_entries(), flows, _DPS, _KNOWN)["boundary"]
    assert boundary["balance_residual_m3h"] == pytest.approx(30.0)


def test_outflow_rows_compare_the_two_engines() -> None:
    entries = _entries()
    slow = ContamXTransportEngine(_LAYOUT, entries, _FLOWS, natural_decay_rate=0.0)
    fast_flows = {nr: 2.0 * flow for nr, flow in _FLOWS.items()}
    fast = ContamXTransportEngine(_LAYOUT, entries, fast_flows, natural_decay_rate=0.0)
    rows = diag.outflow_rows(slow, fast, ["A", "B"])
    assert [r["zone"] for r in rows] == ["A", "B"]
    for row in rows:
        assert row["k_native_per_h"] > 0.0
        assert row["field_over_native"] == pytest.approx(2.0)
    summary = diag.summarize_outflow(rows)
    assert summary["median_field_over_native"] == pytest.approx(2.0)
    assert summary["n_above_double"] == 0
    assert summary["n_native_dead"] == 0


def test_outflow_ratio_is_none_for_a_native_dead_zone() -> None:
    rows = [{"zone": "A", "k_native_per_h": 0.0, "k_field_per_h": 1.0, "field_over_native": None}]
    summary = diag.summarize_outflow(rows)
    assert summary["n_native_dead"] == 1
    assert summary["median_field_over_native"] is None


@pytest.mark.parametrize(
    ("hull", "expected"),
    [
        ("missouri_bb63", "bb"),
        ("expedition_cruise_450", "cruise"),
        ("enterprise_galaxy_tng", "fiction"),
        ("destroyer_baseline", "other"),
    ],
)
def test_hull_class_from_platform_id(hull: str, expected: str) -> None:
    assert diag.hull_class(hull) == expected


def test_cli_defaults_and_lane_choices() -> None:
    args = diag._parse_args([])
    assert args.lane is None
    assert set(diag.DEFAULT_LANES) <= set(diag.LANES)
    parsed = diag._parse_args(
        ["--hull", "destroyer_baseline", "--lane", "design", "--source", "Bridge",
         "--timing", "pulse_t0"],
    )
    assert (parsed.hull, parsed.lane, parsed.source, parsed.timing) == (
        ["destroyer_baseline"], ["design"], ["Bridge"], ["pulse_t0"],
    )


def test_makeup_demand_grades_with_exhaust_flow() -> None:
    """Sweep the hood exhaust: demand rises 1:1, the envelope total does not move."""
    exhausts = [0.0, 30.0, 300.0, 3000.0]
    demands, inward = [], []
    for exhaust in exhausts:
        flows = dict(_FLOWS)
        flows[4] = exhaust
        report = diag.analyze_field(_entries(), flows, _DPS, _KNOWN)
        demands.append(report["boundary"]["makeup_demand_m3h"])
        inward.append(report["envelope"]["net_inward_m3h"])
    assert demands == sorted(demands)
    assert demands[-1] - demands[0] == pytest.approx(exhausts[-1] - exhausts[0])
    assert inward == pytest.approx([70.0] * len(exhausts))


def test_dp_scale_grades_the_decade_counts() -> None:
    """Scaling every dP by 10x moves paths up the decade ladder, never down."""
    totals = []
    for scale in (0.001, 0.1, 10.0):
        dps = {nr: scale * dp for nr, dp in _DPS.items()}
        stats = diag.analyze_field(_entries(), _FLOWS, dps, _KNOWN)["dp"]["all"]
        assert stats["max_abs_dp_pa"] == pytest.approx(scale * 2.0e4)
        totals.append(sum(stats["n_over_pa"].values()))
    assert totals == sorted(totals)
    assert totals[-1] - totals[0] >= 5


def _fleet_row(hull: str, lane: str, scale: float) -> dict[str, Any]:
    dps = {nr: scale * dp for nr, dp in _DPS.items()}
    row = diag.analyze_field(_entries(), _FLOWS, dps, _KNOWN)
    row.pop("paths")
    row.update(
        hull=hull, lane=lane, hull_class=diag.hull_class(hull), zone_count=2,
        outflow=diag.summarize_outflow([
            {"zone": "A", "k_native_per_h": 1.0, "k_field_per_h": 1.0, "field_over_native": 1.0},
            {"zone": "B", "k_native_per_h": 1.0, "k_field_per_h": 3.0, "field_over_native": 3.0},
        ]),
    )
    return row


def _fleet_rows() -> list[dict[str, Any]]:
    return [
        _fleet_row("missouri_bb63", "authored", 1.0),
        _fleet_row("cannon_de701", "authored", 0.001),
        _fleet_row("expedition_cruise_450", "authored", 10.0),
        {"hull": "olympia_c6", "lane": "authored", "hull_class": "c", "zone_count": 9,
         "error": "ContamXUnavailable: timed out"},
    ]


def test_fleet_summary_groups_hulls_and_counts_unsolved() -> None:
    summary = {(b["lane"], b["group"]): b for b in diag.summarize_fleet(_fleet_rows())}
    naval, cruise = summary["authored", "naval"], summary["authored", "cruise"]
    assert (naval["hulls"], naval["unsolved"]) == (2, 1)
    assert (cruise["hulls"], cruise["unsolved"]) == (1, 0)
    # 2e4 Pa and 20 Pa naval hulls; the 2e5 Pa hull is the cruise one.
    assert (naval["hulls_over_1kpa"], naval["hulls_over_10kpa"]) == (1, 1)
    assert naval["hulls_over_100kpa"] == 0
    assert cruise["hulls_over_100kpa"] == 1
    assert naval["envelope_inward_m3h"] == pytest.approx(140.0)
    assert naval["zones_above_double_native"] == 2
    assert naval["max_abs_balance_residual_m3h"] == pytest.approx(0.0, abs=1e-9)


def test_fleet_summary_of_an_all_unsolved_group_reports_zero_hulls() -> None:
    summary = diag.summarize_fleet(_fleet_rows()[-1:])
    assert summary == [{"lane": "authored", "group": "naval", "unsolved": 1, "hulls": 0}]


def test_fleet_markdown_has_one_line_per_hull_row() -> None:
    rows = _fleet_rows()
    text = diag.fleet_markdown(rows)
    table = text.split("### Fleet table")[1].strip().splitlines()
    assert len(table) == 2 + len(rows)
    widths = {line.count("|") for line in table}
    assert widths == {len(diag._HULL_COLUMNS) + 1}
    unsolved = [line for line in table if "unsolved" in line]
    assert len(unsolved) == 1
    assert "olympia_c6" in unsolved[0]


def test_prescribed_links_leave_the_interior_opening_statistics() -> None:
    airflow = {
        "cross_zone_links": [
            {"path": "Transfer_Fan", "mechanism": "prescribed_flow"},
            {"path": "Door_Gap", "mechanism": "pressure_opening"},
        ]
    }
    prescribed = diag.prescribed_kinds(airflow)
    assert prescribed == frozenset({"Transfer_Fan"})
    entries = _entries() + [_entry(9, "Transfer_Fan", "A", "B"), _entry(10, "Door_Gap", "A", "B")]
    flows = {**_FLOWS, 9: 10.0, 10: 1.0}
    dps = {**_DPS, 9: 9.0e5, 10: 7.0}
    plain = diag.analyze_field(entries, flows, dps, _KNOWN)["dp"]
    split = diag.analyze_field(entries, flows, dps, _KNOWN, prescribed=prescribed)["dp"]
    assert plain["interior"]["max_abs_dp_pa"] == pytest.approx(9.0e5)
    assert split["interior"]["max_abs_dp_pa"] == pytest.approx(7.0)
    assert split["by_class"][diag.CLASS_PRESCRIBED]["max_abs_dp_pa"] == pytest.approx(9.0e5)
    assert split["all"] == plain["all"]


def test_a_path_the_solve_did_not_report_is_an_error() -> None:
    flows = {nr: flow for nr, flow in _FLOWS.items() if nr != 3}
    entries = _entries()
    with pytest.raises(KeyError):
        diag.analyze_field(entries, flows, _DPS, _KNOWN)


def test_blocked_openings_are_reported_apart_from_flowing_ones() -> None:
    entries = _entries() + [_entry(9, "Check_Valve", "A", "B"), _entry(10, "Door_Gap", "A", "B")]
    dps = {**_DPS, 9: -8.0e5, 10: 7.0}
    blocked = diag.analyze_field(entries, {**_FLOWS, 9: 0.0, 10: 1.0}, dps, _KNOWN)["dp"]
    assert blocked["interior_blocked"]["n"] == 1
    assert blocked["interior_blocked"]["max_abs_dp_pa"] == pytest.approx(8.0e5)
    assert blocked["interior_flowing"]["max_abs_dp_pa"] < 8.0e5
    open_ = diag.analyze_field(entries, {**_FLOWS, 9: 5.0, 10: 1.0}, dps, _KNOWN)["dp"]
    assert open_["interior_blocked"]["n"] == 0
    assert open_["interior_flowing"]["max_abs_dp_pa"] == pytest.approx(8.0e5)


def test_terminals_without_a_declaration_report_unknown_not_zero() -> None:
    entries = [
        {k: v for k, v in entry.items() if k != "declared_flow_m3h"} for entry in _entries()
    ]
    ahs = diag.summarize_ahs(entries, _FLOWS)
    assert ahs["declared_supply_total_m3h"] is None
    assert ahs["declared_return_total_m3h"] is None
    assert all(g["declared_return_minus_supply_m3h"] is None for g in ahs["groups"])
    declared = diag.summarize_ahs(_entries(), _FLOWS)
    assert ahs["return_minus_supply_m3h"] == pytest.approx(declared["return_minus_supply_m3h"])
    assert declared["declared_return_total_m3h"] == pytest.approx(140.0)
