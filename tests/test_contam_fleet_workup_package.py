"""Offline package and verifier of the airflow workup.

Built here from the committed four-hull canary reduction alone, so the
fleet-wide count checks are expected to fail; every other check must pass,
and each tamper below must be caught by the check that names it.
"""
from __future__ import annotations

import contextlib
import csv
import io
import os
import shutil

import pytest

from tools.diag import contam_fleet_workup_package as package
from tools.diag import contam_fleet_workup_verify as verifier

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANARY = os.path.join(REPO, "campaigns/contam/fleet_workup_canary_01/readout")
FLEET_ONLY = {
    "row IDs are the frozen matrix exactly once",
    "planned counts are met",
    "hulls are the 77 bundled hulls",
    "one corrected canary cohort and eight fleet cohorts, with the frozen rosters",
    "the two untouched as-shipped baselines are separate references that recompute",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("pkg") / "p")
    package.build({package.CANARY_COHORT: CANARY}, out)
    return out


def _failed(root):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        verifier.verify(root)
    return {line[6:].split("  ")[0] for line in out.getvalue().splitlines()
            if line.startswith("FAIL")}


def _copy(built, tmp_path):
    root = str(tmp_path / "p")
    shutil.copytree(built, root)
    return root


def _rewrite(root, name, change):
    path = os.path.join(root, name)
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        columns, rows = reader.fieldnames, list(reader)
    rows = change(rows)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    package.write_sums(root)


def test_canary_only_package_fails_only_the_fleet_wide_checks(built):
    assert _failed(built) == FLEET_ONLY


def test_package_has_no_raw_record_and_only_documented_files(built):
    names = set(package._files(built))
    assert names == set(verifier.COLUMNS) | set(verifier.OTHER_FILES) | {"SHA256SUMS"}
    assert not [n for n in names if n.endswith((".jsonl", ".prj", ".sim", ".log"))]


def test_archive_is_byte_reproducible(built, tmp_path):
    first = package.archive(built, str(tmp_path / "a.tar.gz"), "pkg")
    second = package.archive(built, str(tmp_path / "b.tar.gz"), "pkg")
    assert first == second


def test_edited_byte_is_caught_by_the_checksum(built, tmp_path):
    root = _copy(built, tmp_path)
    with open(os.path.join(root, "data/results_long.csv"), "a", encoding="utf-8") as fh:
        fh.write("\n")
    assert _failed(root) == {"every file matches SHA256SUMS"}


def test_extra_file_is_refused(built, tmp_path):
    root = _copy(built, tmp_path)
    with open(os.path.join(root, "data/cells.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("{}\n")
    package.write_sums(root)
    assert _failed(root) == {"file set is exactly the documented set"}


def test_missing_row_is_caught_even_with_consistent_checksums(built, tmp_path):
    root = _copy(built, tmp_path)
    _rewrite(root, "data/coverage_observed.csv", lambda rows: rows[:-1])
    assert "row IDs are the frozen matrix exactly once" in _failed(root)
    assert "planned counts are met" in _failed(root)


def test_duplicate_row_is_caught(built, tmp_path):
    root = _copy(built, tmp_path)
    _rewrite(root, "data/coverage_observed.csv", lambda rows: [*rows, rows[0]])
    assert "no duplicate row ID in coverage" in _failed(root)


def test_zero_in_place_of_an_unresolved_blank_is_caught(built, tmp_path):
    root = _copy(built, tmp_path)

    def change(rows):
        for row in rows:
            if row["lane"] != verifier.NATIVE and row["metric"] == "outdoor_air_total_m3h":
                row["value"] = "0.0"
                break
        return rows

    _rewrite(root, "data/results_long.csv", change)
    failed = _failed(root) - FLEET_ONLY
    assert "solver-unresolved outdoor-air and exhaust totals are blank, not zero" in failed
    assert "a value appears only with status ok or unchanged" in failed


def test_changed_value_no_longer_recomputes(built, tmp_path):
    root = _copy(built, tmp_path)

    def change(rows):
        for row in rows:
            if row["value"] not in ("", "0", "0.0"):
                row["value"] = repr(float(row["value"]) * 1.01)
                break
        return rows

    _rewrite(root, "data/results_long.csv", change)
    assert "results_long values are the last measured repeat of each row" in _failed(root)


def test_relabelled_phase_and_changed_timing_are_caught(built, tmp_path):
    root = _copy(built, tmp_path)

    def relabel(rows):
        for row in rows:
            if row["phase"] == "contamx_import":
                row["phase"] = "contamx_solve"
                break
        return rows

    _rewrite(root, "data/timing_raw.csv", relabel)
    failed = _failed(root)
    assert "every executed row has 1 warm-up, 5 measured and 5 cached timings per phase" in failed

    root2 = _copy(built, tmp_path / "second")

    def slower(rows):
        for row in rows:
            if row["repeat_kind"] == "measured":
                row["wall_ns"] = str(int(row["wall_ns"]) * 3)
                break
        return rows

    _rewrite(root2, "data/timing_raw.csv", slower)
    assert "timing_summary recomputes from timing_raw; no summary pools two cohorts" in _failed(root2)


def test_columns_are_whole_hull_aggregates_only():
    banned = ("zone", "room", "deck", "path_id", "opening", "source", "pathogen", "dose",
              "infect", "voyage", "rank")
    for name, columns in verifier.COLUMNS.items():
        assert not [c for c in columns if any(b in c for b in banned)], name


def test_earlier_canary_run_is_refused_as_the_canary_cohort(tmp_path):
    out = str(tmp_path / "p")
    package.build({package.CANARY_COHORT: CANARY.replace("readout", "readout_run1")}, out)
    assert ("the canary cohort is the corrected run 2, by job, artifact, image and runner"
            in _failed(out))


def test_metric_dropped_from_every_derived_table_is_caught(built, tmp_path):
    root = _copy(built, tmp_path)

    def drop(rows):
        return [r for r in rows if r["metric"] != "interzone_gross_m3h"]

    for name in ("results_long", "contrasts", "reference_baselines"):
        _rewrite(root, f"data/{name}.csv", drop)
    assert ("results_long carries every metric of every executed row, and no other"
            in _failed(root))
