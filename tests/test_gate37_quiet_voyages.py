"""The quiet-voyage read-out must be arithmetic, not narrative.

Bounds and graded-sensitivity checks (skill `ci-test-design`) on
`telemetry_buffer/observation_model/gate37_quiet_voyages.py`: the counts have to
add up against the artifact's own cells, and the conditional-level bound has to
stay a bound.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import telemetry_buffer.observation_model.gate37_quiet_voyages as quiet_voyages
from telemetry_buffer.observation_model.gate37_quiet_voyages import (
    DEFAULT_ARTIFACT,
    by_a1_band,
    conditional_levels,
    load_points,
    posting_totals,
    report,
    voyage_days,
)
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD


def _point(
    a1: float,
    posted: int,
    incidence: float,
    seeds: int = 180,
    reported: float = 0.0,
) -> dict[str, Any]:
    return {
        "cell": {
            "A1_ever_ill_passenger": a1,
            "A9_eligible_runs": seeds,
            "A9_posted_eligible": posted,
            "A8_pax_incidence": incidence,
            "reported_case_attack_rate_passenger": reported,
            "infection_attack_rate_passenger": 0.05,
        },
    }


def test_posting_totals_sum_the_cells() -> None:
    points = [_point(0.0, 6, 40.0), _point(0.15, 180, 900.0)]
    assert posting_totals(points) == (360, 174)


def test_a1_bands_partition_the_points_and_their_voyages() -> None:
    points = [_point(0.001, 6, 40.0), _point(0.03, 90, 400.0), _point(0.15, 180, 900.0)]
    rows = by_a1_band(points)
    assert sum(row["points"] for row in rows) == len(points)
    assert sum(row["eligible"] for row in rows) == 540
    assert sum(row["quiet"] for row in rows) == 174 + 90 + 0


def test_voyage_days_are_recovered_from_a8s_own_definition() -> None:
    points = [{"cell": {"reported_case_attack_rate_passenger": 0.03, "A8_pax_incidence": 400.0}}]
    assert voyage_days(points) == pytest.approx(7.5)


def test_voyage_days_refuse_a_cell_that_never_scored_a8() -> None:
    with pytest.raises(SystemExit):
        voyage_days([{"cell": {"reported_case_attack_rate_passenger": 0.0, "A8_pax_incidence": 0.0}}])


def test_the_conditional_level_is_a_bracket_around_the_cell_mean() -> None:
    # 10 of 180 voyages post; the cell mean is 0.5% reported attack rate.
    points = [_point(0.02, 10, 1e5 * 0.005 / 7.0)]
    levels = conditional_levels(points, days=7.0)
    ceiling = levels["ceiling_quartiles"][0]
    floor = levels["floor_quartiles"][0]
    assert ceiling == pytest.approx(0.005 * 180 / 10, rel=1e-6)
    assert floor <= ceiling
    # The mean alone cannot exclude quiet voyages sitting just under the bar.
    assert floor == pytest.approx(0.0)


def test_a_louder_cell_raises_the_bound_monotonically() -> None:
    quiet = conditional_levels([_point(0.02, 10, 60.0)], days=7.0)
    loud = conditional_levels([_point(0.02, 10, 120.0)], days=7.0)
    assert loud["ceiling_quartiles"][0] > quiet["ceiling_quartiles"][0]


def test_points_that_post_on_most_voyages_are_out_of_scope() -> None:
    assert conditional_levels([_point(0.15, 180, 900.0)], days=7.0)["n_points"] == 0
    assert conditional_levels([_point(0.0, 0, 0.0)], days=7.0)["n_points"] == 0


def test_the_report_states_the_counts_its_own_cells_imply() -> None:
    points = [
        _point(0.001, 6, 400.0, reported=0.03),
        _point(0.15, 180, 900.0),
    ]
    lines = report(points)
    assert "2 points, 360 eligible voyages" in lines[0]
    assert "174 (48.333%)" in lines[1]
    # One point posts on every voyage, one does not; both bands are named.
    assert "points with at least one quiet voyage: 1" in "\n".join(lines)
    assert "points posting on every voyage: 1" in "\n".join(lines)
    assert sum(1 for line in lines if line.startswith("  [")) == 2


def test_the_report_says_so_when_no_point_is_quiet_enough_to_bound() -> None:
    lines = report([_point(0.15, 180, 900.0, reported=0.30)])
    assert "no point posts on under half its voyages" in lines
    assert not any("E[reported AR | posted]" in line for line in lines)


def test_a_quiet_point_reaches_the_reported_bracket_lines() -> None:
    lines = "\n".join(report([_point(0.02, 10, 400.0, reported=0.005)]))
    assert "1 points posting on under half their voyages" in lines
    assert "E[reported AR | posted] <=" in lines
    assert "median ceiling / threshold:" in lines


def test_an_artifact_is_read_from_inside_the_repository_and_nowhere_else(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inside = tmp_path / "repo"
    inside.mkdir()
    monkeypatch.setattr(quiet_voyages, "REPO_ROOT", inside)
    points = [_point(0.02, 10, 400.0, reported=0.005)]
    (inside / "points.json").write_text(json.dumps({"points": points}), encoding="utf-8")
    assert load_points(inside / "points.json") == points

    outside = tmp_path / "points.json"
    outside.write_text(json.dumps({"points": points}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_points(outside)


@pytest.mark.skipif(not DEFAULT_ARTIFACT.exists(), reason="merged gate artifact absent")
def test_the_committed_gate_artifact_still_reads_as_documented() -> None:
    points = json.loads(Path(DEFAULT_ARTIFACT).read_text(encoding="utf-8"))["points"]
    eligible, quiet = posting_totals(points)
    assert (eligible, quiet) == (46080, 36087)
    levels = conditional_levels(points, voyage_days(points))
    assert levels["n_points"] == 222
    assert levels["silent_median_points"] == 176
    # Every posting voyage clears the threshold, so the ceiling must too.
    assert min(levels["ceiling_quartiles"]) > A9_POSTING_THRESHOLD
