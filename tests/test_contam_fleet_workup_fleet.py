"""Fleet stage of the airflow workup: selection metadata, not science.

The 73-hull roster is the frozen 77 minus the canary four; its row IDs are
disjoint from the canary's and their union is the frozen matrix exactly.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os

import pytest

from tools.diag import contam_fleet_workup_run as run_mod

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN = os.path.join(REPO, "campaigns/contam/fleet_workup_fleet_01/design")
SELECTION = os.path.join(DESIGN, "fleet_selection.json")


def _builder():
    spec = importlib.util.spec_from_file_location(
        "fleet_build_selection", os.path.join(DESIGN, "build_selection.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def criteria():
    with open(run_mod.CRITERIA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def matrix():
    with open(os.path.join(run_mod.FROZEN_DIR, "run_matrix.csv"), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def manifest():
    with open(os.path.join(run_mod.FROZEN_DIR, "input_manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_committed_selection_is_a_rebuild_of_the_frozen_design():
    with open(SELECTION, encoding="utf-8") as fh:
        assert fh.read() == _builder().render()


def test_roster_is_the_frozen_77_minus_the_canary_four(criteria, manifest):
    selection = run_mod.load_selection(SELECTION, None, criteria)
    canary = set(criteria["canary"]["hulls"])
    assert len(selection["hulls"]) == 73
    assert set(selection["hulls"]) == set(manifest["hulls"]) - canary
    assert not set(selection["hulls"]) & canary


def test_fleet_and_canary_row_ids_are_disjoint_and_their_union_is_the_matrix(criteria, matrix):
    fleet = run_mod.selected_rows(run_mod.load_selection(SELECTION, None, criteria))
    canary = run_mod.canary_rows(criteria)
    fleet_ids = [r["row_id"] for r in fleet]
    canary_ids = [r["row_id"] for r in canary]
    assert len(set(fleet_ids)) == len(fleet_ids) == 2044
    assert not set(fleet_ids) & set(canary_ids)
    assert sorted(fleet_ids + canary_ids) == sorted(r["row_id"] for r in matrix)
    assert len(matrix) == 2156
    assert sum(r["planned_status"] == "planned_execute" for r in fleet) == 1514
    assert sum(r["planned_status"] == "planned_execute" for r in matrix) == 1591


def test_expected_fleet_counts():
    with open(SELECTION, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["expected_fleet"] == {
        "rows_total": 2044, "rows_planned_execute": 1514, "cold_cell_executions": 9084,
        "contamx_solver_invocations": 6492, "cached_cell_executions": 7570,
        "smoke_cells_untimed": 1514,
    }
    assert sorted(doc["excluded_no_bundle"]) == [
        "expedition_cruise_300", "fletcher_class_destroyer", "legend_class_nsc",
        "messy_cruise_500", "san_antonio_class_lpd",
    ]


def test_cohorts_partition_the_roster_and_keep_matrix_order(criteria, matrix):
    with open(SELECTION, encoding="utf-8") as fh:
        doc = json.load(fh)
    seen: list[str] = []
    rows: list[dict[str, str]] = []
    for index in range(len(doc["cohorts"])):
        selection = run_mod.load_selection(SELECTION, index, criteria)
        seen += selection["hulls"]
        rows += run_mod.selected_rows(selection)
    assert seen == doc["hulls"]
    assert rows == [r for r in matrix if r["hull"] in set(doc["hulls"])]
    for key, value in doc["expected_fleet"].items():
        assert sum(c["expected"][key] for c in doc["cohorts"]) == value


def test_authored_prj_pins_are_the_frozen_manifest_entries(criteria, manifest):
    selection = run_mod.load_selection(SELECTION, None, criteria)
    for hull, digest in selection["authored_prj_sha256"].items():
        entry = [f for f in manifest["hulls"][hull]["files"]
                 if f["path"] == f"data/platforms/{hull}/contam/platform.prj"]
        assert [f["sha256"] for f in entry] == [digest]
    # The canary's own four pins follow the same rule, so the fleet pins extend it.
    for hull, digest in criteria["authored_prj_sha256"].items():
        entry = [f for f in manifest["hulls"][hull]["files"]
                 if f["path"].endswith("/contam/platform.prj")]
        assert entry[0]["sha256"] == digest


def test_selection_repeating_a_canary_hull_is_refused(criteria, tmp_path):
    with open(SELECTION, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["hulls"].append(criteria["canary"]["hulls"][0])
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(run_mod.RunError, match="repeats canary hulls"):
        run_mod.load_selection(str(path), None, criteria)


def test_selection_built_for_other_criteria_is_refused(criteria, tmp_path):
    with open(SELECTION, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["criteria_sha256"] = "0" * 64
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(run_mod.RunError, match="different criteria"):
        run_mod.load_selection(str(path), None, criteria)


def test_selection_carries_no_gate_or_tolerance():
    with open(SELECTION, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert not {"tolerances", "gates", "canary"} & set(doc)


# ── committed 77-hull readout ─────────────────────────────────────────────

READOUT = os.path.join(REPO, "campaigns/contam/fleet_workup_fleet_01/readout")


def _readout(name):
    with open(os.path.join(READOUT, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_committed_coverage_is_the_frozen_matrix_exactly_once(matrix):
    coverage = _readout("coverage_observed.csv")
    assert sorted(r["row_id"] for r in coverage) == sorted(r["row_id"] for r in matrix)
    executed = [r for r in coverage if r["planned_status"] == "planned_execute"]
    assert len(executed) == 1591
    assert {r["observed_status"] for r in executed} == {"ok"}
    assert all(r["observed_status"] == r["planned_status"] and r["reason"]
               for r in coverage if r["planned_status"] != "planned_execute")


def test_committed_cohorts_are_run_two_canary_plus_eight_fleet_jobs(criteria):
    cohorts = {c["cohort"]: c for c in _readout("cohorts.csv")}
    with open(SELECTION, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert sorted(cohorts) == ["canary_run2", *[f"fleet_cohort{i}" for i in range(8)]]
    assert cohorts["canary_run2"]["batch_job_id"] == "ac1b56e1-2080-40cc-be8f-b8473ceca793"
    assert cohorts["canary_run2"]["hulls"].split(";") == sorted(criteria["canary"]["hulls"])
    for entry in doc["cohorts"]:
        row = cohorts[f"fleet_cohort{entry['cohort']}"]
        assert row["hulls"].split(";") == entry["hulls"]
        assert row["gate_failed"] == "0" and row["audit_passed"] == "1"
        assert row["reporting_attempt"] == row["attempts"]
    assert len({c["batch_job_id"] for c in cohorts.values()}) == 9
