"""Pre-results design of the fleet native-vs-ContamX workup.

Ledger ``CONTAM-FLEET-WORKUP-PROTOCOL-01``. These tests lock the planning
rules on small fixtures and the committed artifacts offline; no field is
solved and no solver is timed.
"""

from __future__ import annotations

import csv
import io
import json

import pytest

from tools import contam_fleet_workup_design as design

_PLENUM_REASON = "sealed life-support"


def _airflow(groups):
    return {
        "oa_fraction": 0.2,
        "hvac_duty": 0.5,
        "hvac_zones": groups,
        "ambient_openings": [
            {"zone": "A", "type": "door", "exchange_m3h": 10.0,
             "wind_speed_m_s": 2.0},
            {"zone": "B", "type": "door", "exchange_m3h": 5.0},
        ],
        "cross_zone_links": [{}],
        "adjacency": [{}, {}],
    }


def _facts(groups, overrides=None):
    spatial = {"zones": [{"id": "A"}, {"id": "B"}]}
    return design.hull_facts(spatial, _airflow(groups), overrides or {})


_MIXED = [
    {"id": "S1", "ach": 6.0, "oa_fraction": 0.4},
    {"id": "S2", "ach": 6.0, "oa_fraction": 1.0},
    {"id": "X1", "ach": 10.0, "oa_fraction": 1.0, "hvac_duty": 0.0},
]


def _by_status(rows):
    out = {}
    for row in rows:
        out.setdefault(row["planned_status"], []).append(row)
    return out


def test_group_facts_count_supply_recirculating_and_export_mismatch():
    facts = _facts(_MIXED)
    assert facts["hvac_group_count"] == 3
    assert facts["supply_group_count"] == 2
    assert facts["duty0_group_count"] == 1
    assert facts["recirculating_supply_group_count"] == 1
    # Export resolves the pack default 0.2 for both supply groups.
    assert facts["export_oa_differs_group_count"] == 2
    assert facts["cross_ventilated_opening_count"] == 1


def test_override_map_removes_export_mismatch():
    facts = _facts(_MIXED, {"oa_fraction": {"S1": 0.4, "_default": 1.0}})
    assert facts["export_oa_differs_group_count"] == 0


def test_default_wind_is_the_exporter_default():
    facts = _facts(_MIXED)
    assert facts["authored_wind_speed_m_s"] == 1.0
    assert facts["authored_wind_direction_deg"] == 0.0
    assert facts["wall_azimuth_basis"] == "display_coordinate_heuristic"


def test_ordinary_hull_rows():
    rows = design.plan_rows("h", _facts(_MIXED))
    assert len(rows) == 2 * len(design.SETTINGS) + 2
    assert len({r["row_id"] for r in rows}) == len(rows)
    grouped = _by_status(rows)
    assert design.NOT_APPLICABLE not in grouped
    nonresponse = grouped[design.NONRESPONSE]
    assert len(nonresponse) == 7
    assert {r["lane"] for r in nonresponse} == {design.LANE_NATIVE}
    assert {r["measured_reps"] for r in nonresponse} == {0}


def test_weather_on_contamx_is_one_sided_not_matched():
    rows = design.plan_rows("h", _facts(_MIXED))
    weather = [
        r for r in rows
        if r["family"].startswith("weather")
        and r["lane"] == design.LANE_COMMISSIONED
    ]
    assert {r["contrast_type"] for r in weather} == {"one_sided_structural"}
    assert {r["planned_status"] for r in weather} == {design.EXECUTE}


def test_operational_rows_are_matched_in_both_lanes():
    rows = design.plan_rows("h", _facts(_MIXED))
    duty = [r for r in rows if r["setting_id"] == "supply_duty_x0p5"]
    assert [r["lane"] for r in duty] == [
        design.LANE_NATIVE, design.LANE_COMMISSIONED,
    ]
    assert {r["contrast_type"] for r in duty} == {"matched_perturbation"}


def test_sealed_hull_weather_is_not_applicable_in_both_lanes():
    facts = _facts(_MIXED, {
        "life_support_plenum": {"enabled": True},
        "relative_wind_speed_m_s": 0.0,
    })
    rows = design.plan_rows("h", facts)
    weather = [r for r in rows if r["family"].startswith("weather")]
    assert len(weather) == 14
    assert {r["planned_status"] for r in weather} == {design.NOT_APPLICABLE}
    assert all(_PLENUM_REASON in r["reason"] for r in weather)
    assert {r["contamx_solves_planned"] for r in weather} == {0}


def test_once_through_hull_has_no_outdoor_air_arm():
    facts = _facts([{"id": "S", "ach": 6.0, "oa_fraction": 1.0}])
    rows = design.plan_rows("h", facts)
    status = {r["setting_id"]: r["planned_status"] for r in rows
              if r["lane"] == design.LANE_NATIVE}
    assert status["supply_oa_x0p5"] == design.NOT_APPLICABLE
    assert status["supply_recirc_x0p5"] == design.NOT_APPLICABLE
    assert status["supply_duty_x0p5"] == design.EXECUTE


def test_hull_without_supply_groups_has_no_operational_arm():
    facts = _facts([{"id": "X", "ach": 6.0, "oa_fraction": 1.0,
                     "hvac_duty": 0.0}])
    rows = design.plan_rows("h", facts)
    operational = [r for r in rows if r["family"].startswith("operational")]
    assert {r["planned_status"] for r in operational} == {
        design.NOT_APPLICABLE,
    }


def test_separate_baselines_are_single_rows():
    rows = design.plan_rows("h", _facts(_MIXED))
    for lane in (design.LANE_AS_COMMITTED, design.LANE_AUTHORED):
        own = [r for r in rows if r["lane"] == lane]
        assert [r["setting_id"] for r in own] == ["baseline"]
        assert own[0]["block"] != design.BLOCK_COMPARATIVE


def test_roster_needs_every_bundle_file():
    listing = {
        f"data/platforms/full/{name}": "0" * 40 for name in design.HULL_FILES
    }
    listing["data/platforms/partial/contam/platform.prj"] = "0" * 40
    listing["data/platforms/partial/spatial_layout.json"] = "0" * 40
    listing["data/platforms/README.md"] = "0" * 40
    platforms, bundled = design.classify_roster(listing)
    assert platforms == ["full", "partial"]
    assert bundled == ["full"]


def test_canary_rule_is_deterministic():
    facts = {
        "a": {"zone_count": 5, "life_support_plenum": False},
        "b": {"zone_count": 50, "life_support_plenum": False},
        "c": {"zone_count": 20, "life_support_plenum": True},
        "d": {"zone_count": 20, "life_support_plenum": True},
        "destroyer_baseline": {"zone_count": 9, "life_support_plenum": False},
    }
    assert design.select_canary(facts) == ["a", "b", "c", "destroyer_baseline"]


def test_summary_counts_and_workload():
    matrix = design.plan_rows("h", _facts(_MIXED))
    coverage = [design.coverage_row("h", "t", _facts(_MIXED), matrix, True)]
    summary = design.summarize(matrix, coverage)
    executed = 2 * len(design.SETTINGS) + 2 - 7
    assert summary["rows_by_planned_status"] == {
        design.EXECUTE: executed, design.NONRESPONSE: 7,
    }
    work = summary["timing_workload"]
    assert work["cold_cell_executions_total"] == executed * 6
    assert work["cold_cell_executions_measured"] == executed * 5
    assert work["contamx_solver_invocations"] == (len(design.SETTINGS) + 2) * 6
    assert work["rows_not_timed"] == 7


# ── committed artifacts (offline) ─────────────────────────────────────────

@pytest.fixture(scope="module")
def committed():
    return design.read_committed()


def test_committed_artifacts_pass_offline_checks(committed):
    design.check_artifacts(committed)


def test_committed_totals(committed):
    summary = json.loads(committed["dry_run_summary.json"])
    assert summary["platforms_at_pin"] == 82
    assert summary["hulls_in_scope"] == 77
    assert summary["rows_total"] == 77 * 28
    assert sum(summary["rows_by_planned_status"].values()) == 77 * 28
    assert summary["platforms_excluded"] == [
        "expedition_cruise_300", "fletcher_class_destroyer",
        "legend_class_nsc", "messy_cruise_500", "san_antonio_class_lpd",
    ]


def test_committed_manifest_hashes_five_files_per_hull(committed):
    manifest = json.loads(committed["input_manifest.json"])
    assert manifest["input_commit"] == design.INPUT_PIN
    assert len(manifest["hulls"]) == 77
    for hull, entry in manifest["hulls"].items():
        names = [f["path"].split(f"/{hull}/", 1)[1] for f in entry["files"]]
        assert tuple(names) == design.HULL_FILES
        assert all(len(f["sha256"]) == 64 for f in entry["files"])


def test_tampered_matrix_is_rejected(committed):
    broken = dict(committed)
    broken["run_matrix.csv"] = committed["run_matrix.csv"].replace(
        b"planned_execute", b"not_applicable", 1,
    )
    with pytest.raises(design.DesignError):
        design.check_artifacts(broken)


def test_duplicate_row_is_rejected(committed):
    rows = list(csv.DictReader(io.StringIO(
        committed["run_matrix.csv"].decode(),
    )))
    summary = json.loads(committed["dry_run_summary.json"])
    with pytest.raises(design.DesignError):
        design.check_matrix(rows + rows[:1], summary)


def test_matrix_carries_no_zone_or_path_identifier(committed):
    header = committed["run_matrix.csv"].split(b"\n", 1)[0].decode()
    assert header.split(",") == list(design.MATRIX_COLUMNS)
    assert not {"zone", "path", "room", "deck"} & set(header.split(","))


def test_regeneration_from_pin_is_byte_identical():
    try:
        design._rev(f"{design.INPUT_PIN}^{{commit}}")
    except design.DesignError:
        pytest.skip("input pin not present in this clone")
    design.verify_against_pin()
