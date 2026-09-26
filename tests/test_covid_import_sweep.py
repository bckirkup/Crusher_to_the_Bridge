"""Adaptive-density refinement of the imports x Theta sweep.

No hull runs. Stage-1 surfaces are stubbed with a known response so the
refinement's choice of midpoints, its ranking, its budget and the resulting
stage-2 design can be checked exactly.
"""

from __future__ import annotations

import json
import math

import pytest

from picard_framework.covid_boarding_screen import (
    ScreenCell,
    enumerate_cells,
    load_design,
    merge_screen,
)
from picard_framework.covid_import_sweep import (
    CellResponse,
    RefinementRule,
    pair_score,
    refine_points,
    refined_design,
    responses_from_surface,
)
from picard_framework.covid_theta_fit import HullObservables

DESIGN_REL = "picard_framework/runs/covid_import_sweep_v1_design.json"


def _entry(theta, imports, takeoff, early, total):
    cond = {
        "n": 20,
        "onsets_before_split_day": {"median": early} if early is not None else None,
        "recorded_onsets": {"median": total} if total is not None else None,
    }
    return {
        "theta": theta, "infection_age_days": 0.0, "imports": imports,
        "takeoff_probability": takeoff, "conditional_on_takeoff": cond,
    }


def _surface(entries, design_id="covid_import_sweep_v1"):
    return {"design": {"design_id": design_id}, "surface": entries}


@pytest.fixture(scope="module")
def stage1():
    return load_design(DESIGN_REL)


def test_stage1_design_is_the_declared_700_cell_grid(stage1):
    assert stage1.design_id == "covid_import_sweep_v1"
    assert stage1.is_refinement is False
    assert stage1.imports == (1, 2, 3, 5, 8, 13, 20)
    assert len(stage1.thetas) == 5
    assert stage1.seeds == 20
    assert len(enumerate_cells(stage1)) == 700
    assert stage1.baseline in {(a, n) for _, a, n in stage1.axis_points}


def test_pair_score_is_graded_in_the_takeoff_step():
    rule = RefinementRule()
    a = CellResponse(1e7, 1, 0.1, 5.0, 50.0)
    scores = [
        pair_score(a, CellResponse(1e7, 2, 0.1 + step, 5.0, 50.0), rule)["score"]
        for step in (0.05, 0.2, 0.4, 0.8)
    ]
    assert scores == sorted(scores)
    assert scores[0] < 1.0 < scores[2]
    assert math.isclose(scores[3], 0.8 / rule.takeoff_tolerance)


def test_a_crossing_of_the_observed_count_scores_at_least_one():
    rule = RefinementRule()
    a = CellResponse(1e7, 3, 0.9, 30.0, 190.0)
    b = CellResponse(1e7, 5, 0.9, 38.0, 205.0)
    scored = pair_score(a, b, rule)
    assert scored["crosses_observed_early"] is True
    assert scored["crosses_observed_total"] is True
    assert scored["score"] >= 1.0
    flat = pair_score(a, CellResponse(1e7, 5, 0.9, 31.0, 191.0), rule)
    assert flat["score"] < 1.0


def test_undefined_conditional_medians_do_not_refine():
    rule = RefinementRule()
    a = CellResponse(1e7, 1, 0.0, None, None)
    b = CellResponse(1e7, 2, 0.05, None, None)
    assert pair_score(a, b, rule)["score"] < 1.0


def test_refine_inserts_midpoints_only_where_the_response_moves():
    # takeoff steps between imports 3 and 5 at every Theta; flat elsewhere
    thetas = (1e7, 1e8)
    responses = {}
    for theta in thetas:
        for n in (1, 3, 5, 8):
            take = 0.1 if n <= 3 else 0.9
            responses[(theta, n)] = CellResponse(theta, n, take, 5.0, 50.0)
    chosen = refine_points(responses, RefinementRule(budget=12))
    assert [(c["theta"], c["imports"]) for c in chosen] == [(1e7, 4), (1e8, 4)]
    assert all(c["axis"] == "imports" for c in chosen)


def test_refine_skips_pairs_whose_geometric_midpoint_is_an_endpoint():
    responses = {
        (1e7, 1): CellResponse(1e7, 1, 0.0, None, None),
        (1e7, 2): CellResponse(1e7, 2, 0.9, 5.0, 50.0),
    }
    assert refine_points(responses, RefinementRule()) == []


def test_refine_ranks_by_score_and_honours_the_budget():
    responses = {
        (1e7, 1): CellResponse(1e7, 1, 0.0, None, None),
        (1e7, 5): CellResponse(1e7, 5, 0.3, 5.0, 50.0),
        (1e7, 20): CellResponse(1e7, 20, 1.0, 10.0, 100.0),
        (1e9, 1): CellResponse(1e9, 1, 0.0, None, None),
        (1e9, 5): CellResponse(1e9, 5, 0.0, None, None),
        (1e9, 20): CellResponse(1e9, 20, 0.0, None, None),
    }
    all_points = refine_points(responses, RefinementRule(budget=12))
    assert [c["score"] for c in all_points] == sorted(
        (c["score"] for c in all_points), reverse=True,
    )
    assert (1e7, 10) in {(c["theta"], c["imports"]) for c in all_points}
    top = refine_points(responses, RefinementRule(budget=1))
    assert len(top) == 1
    assert top[0]["score"] == all_points[0]["score"]


def test_refined_design_round_trips_through_the_screen_loader(stage1, tmp_path):
    entries = []
    for theta in stage1.thetas:
        for n in stage1.imports:
            take = 0.2 if n < 5 else 0.95
            entries.append(_entry(theta, n, take, 5.0 + n, 40.0 * n))
    surface = _surface(entries)
    assert len(responses_from_surface(surface)) == 35
    design = refined_design(
        stage1.as_dict(), surface,
        design_id="covid_import_sweep_v1r", rule=RefinementRule(budget=4),
    )
    assert design["parent_design"] == "covid_import_sweep_v1"
    assert len(design["points"]) == 4
    path = tmp_path / "refined.json"
    path.write_text(json.dumps(design), encoding="utf-8")
    loaded = load_design(str(path), repo_root=str(tmp_path))
    assert loaded.is_refinement is True
    assert loaded.axis_points == tuple(tuple(p) for p in design["points"])
    assert len(enumerate_cells(loaded)) == 4 * stage1.seeds
    assert loaded.seed_values == stage1.seed_values


def test_refined_design_refuses_an_empty_surface(stage1):
    payload = stage1.as_dict()
    surface = _surface([])
    rule = RefinementRule()
    with pytest.raises(ValueError):
        refined_design(payload, surface, design_id="x", rule=rule)


def _stub_payload(cell: ScreenCell) -> dict:
    total = 100 * cell.imports if cell.seed % 2 else 0
    obs = HullObservables(
        scenario_id=cell.scenario_id, theta=cell.theta, seed=cell.seed,
        recorded_onsets=total, onsets_before_split_day=total // 10,
        onsets_on_or_after_split_day=total - total // 10,
        passenger_onsets_before=0, passenger_onsets_after=0,
        crew_onsets_before=0, crew_onsets_after=0,
        campaign_specimens=2000, campaign_positives=total,
        campaign_asymptomatic_positives=total // 2,
    )
    return {
        "design_id": "x", "cell": cell.as_dict(), "observables": obs.as_dict(),
        "onset_curve": {}, "first_onset_day": None,
        "sanitary_activity": {"visits": 1.0},
    }


def test_merge_reports_conditional_on_takeoff_medians(stage1):
    cells = enumerate_cells(stage1)
    payloads = {c.key: _stub_payload(c) for c in cells}
    surface = merge_screen(stage1, payloads)
    assert len(surface["surface"]) == 35
    entry = next(e for e in surface["surface"] if e["imports"] == 5 and e["theta"] == 1e7)
    assert entry["takeoff_probability"] == 0.5
    assert entry["conditional_on_takeoff"]["n"] == 10
    assert entry["conditional_on_takeoff"]["recorded_onsets"]["median"] == 500
    assert entry["conditional_on_takeoff"]["onsets_before_split_day"]["median"] == 50
    # unconditional median mixes the extinct half in
    assert entry["recorded_onsets"]["median"] == 250


@pytest.mark.parametrize(
    "kwargs", [{"takeoff_tolerance": 0.0}, {"log_ratio_tolerance": 0.0}, {"budget": 0}],
)
def test_rule_rejects_degenerate_tolerances(kwargs):
    with pytest.raises(ValueError):
        RefinementRule(**kwargs)


def test_stage3_pairs_a_stage2_midpoint_with_both_of_its_stage1_neighbours(stage1):
    # Stage 1: imports 1 and 20 at one Theta, flat elsewhere; stage 2 put a
    # midpoint at imports 4 (sqrt(1*20) ~ 4). Stage 3 must see (1,4) and
    # (4,20) as neighbours, not (1,20), even though 4 is absent from other
    # Theta rows.
    stage1_surface = _surface([
        _entry(1e7, 1, 0.0, None, None), _entry(1e7, 20, 1.0, 40.0, 400.0),
        _entry(1e8, 1, 1.0, 30.0, 300.0), _entry(1e8, 20, 1.0, 40.0, 400.0),
    ])
    stage2_surface = _surface(
        [_entry(1e7, 4, 0.1, 5.0, 50.0)], design_id="covid_import_sweep_v1r",
    )
    rule = RefinementRule(takeoff_tolerance=0.15, log_ratio_tolerance=math.log(1.5))
    design = refined_design(
        stage1.as_dict(), [stage1_surface, stage2_surface],
        design_id="covid_import_sweep_v1rr", rule=rule, stage=3,
    )
    assert design["refinement"]["stage"] == 3
    assert design["refinement"]["surfaces_read"] == [
        "covid_import_sweep_v1", "covid_import_sweep_v1r",
    ]
    assert design["refinement"]["cells_read"] == 5
    chosen = {(c["theta"], c["imports"]) for c in design["refinement"]["chosen"]}
    # (4,20) moves 0.1 -> 1.0 and 5 -> 40: midpoint round(sqrt(80)) = 9.
    assert (1e7, 9) in chosen
    # (1,4) moves 0.0 -> 0.1 with undefined medians on one side: below tolerance.
    assert (1e7, 2) not in chosen
    # the stale stage-1 pair (1,20) is no longer adjacent.
    assert (1e7, 4) not in chosen
    assert all(len(p) == 3 for p in design["points"])


def test_duplicate_cells_across_surfaces_are_refused(stage1):
    surface = _surface([_entry(1e7, 1, 0.0, None, None), _entry(1e7, 20, 1.0, 40.0, 400.0)])
    payload = stage1.as_dict()
    rule = RefinementRule()
    with pytest.raises(ValueError, match="more than one surface"):
        refined_design(
            payload, [surface, surface],
            design_id="x", rule=rule, stage=3,
        )


def test_refinement_stage_must_be_at_least_two(stage1):
    surface = _surface([_entry(1e7, 1, 0.0, None, None), _entry(1e7, 20, 1.0, 40.0, 400.0)])
    payload = stage1.as_dict()
    rule = RefinementRule()
    with pytest.raises(ValueError, match="start at 2"):
        refined_design(payload, surface, design_id="x", rule=rule, stage=1)


@pytest.mark.parametrize("stage, takeoff, ratio", [(2, 0.25, 2.0), (3, 0.15, 1.5), (4, 0.09, 1.25)])
def test_refine_cli_tolerances_tighten_per_stage(stage, takeoff, ratio):
    from tools.fit_covid_theta import _stage_tolerances

    got = _stage_tolerances(stage, None, None)
    assert got == pytest.approx((takeoff, ratio))
    assert _stage_tolerances(stage, 0.5, 3.0) == (0.5, 3.0)
