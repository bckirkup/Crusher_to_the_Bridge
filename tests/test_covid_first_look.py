"""The replicated COVID first look: design, cells, and merge discipline.

No hull runs here. A stub runner whose observables are a known function of
Theta and seed stands in for the simulation, and what is tested is the
discipline: cells enumerate deterministically, the design cannot swap the
fixed split's roles, the fit reads training cells only, a partial grid is
refused unless declared partial, the held-out hull is scored at the fitted
Theta and its neighbours and nowhere else, and the array child slicing covers
every cell of a phase exactly once.
"""

from __future__ import annotations

import importlib.util
import math
from dataclasses import replace
from pathlib import Path

import pytest

from picard_framework.covid_first_look import (
    FIT_PHASE,
    HELD_OUT_PHASE,
    Cell,
    enumerate_cells,
    load_design,
    merge_fit,
    merge_held_out,
    observables_from_payload,
    run_cell,
)
from picard_framework.covid_theta_fit import HullObservables

REPO_ROOT = Path(__file__).resolve().parent.parent
TRUE_THETA = 1e6


def _load_entrypoint():
    path = REPO_ROOT / "deploy" / "aws" / "covid_hull_entrypoint.py"
    spec = importlib.util.spec_from_file_location("covid_hull_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub(
    scenario_id: str,
    theta: float,
    seed: int,
    *,
    cabin_air_mode: str | None = None,
) -> HullObservables:
    """Onsets peak at TRUE_THETA; every third seed is an extinction."""
    distance = abs(math.log10(theta) - math.log10(TRUE_THETA))
    onsets = 0 if seed % 3 == 0 else int(round(300 * math.exp(-distance)))
    specimens = 2400 if scenario_id.startswith("diamond") else 160
    positives = min(specimens, int(onsets * 1.4))
    return HullObservables(
        scenario_id=scenario_id, theta=theta, seed=seed,
        recorded_onsets=onsets,
        onsets_before_split_day=onsets // 3,
        onsets_on_or_after_split_day=onsets - onsets // 3,
        passenger_onsets_before=1, passenger_onsets_after=1,
        crew_onsets_before=1, crew_onsets_after=1,
        campaign_specimens=specimens,
        campaign_positives=positives,
        campaign_asymptomatic_positives=positives // 2,
    )


@pytest.fixture(scope="module")
def design():
    return load_design()


@pytest.fixture(scope="module")
def cells(design):
    return enumerate_cells(design)


@pytest.fixture(scope="module")
def payloads(design, cells):
    return {cell.key: run_cell(design, cell, runner=_stub) for cell in cells}


def test_the_design_declares_both_phases_against_the_fixed_split(design):
    assert design.fit.split_role == "training"
    assert design.held_out.split_role == "held_out"
    assert design.fit.scenario_id == "diamond_princess_2020"
    assert design.held_out.scenario_id == "greg_mortimer_2020"


def test_cells_enumerate_once_each_in_a_fixed_order(design, cells):
    expected = len(design.grid) * (design.fit.seeds + design.held_out.seeds)
    assert len(cells) == expected
    assert [cell.index for cell in cells] == list(range(expected))
    assert len({cell.key for cell in cells}) == expected
    phases = [cell.phase for cell in cells]
    assert phases == sorted(phases, key=(FIT_PHASE, HELD_OUT_PHASE).index)
    assert enumerate_cells(design) == cells


def test_every_candidate_sees_the_same_matched_seeds(design, cells):
    fit_cells = [cell for cell in cells if cell.phase == FIT_PHASE]
    by_theta = {}
    for cell in fit_cells:
        by_theta.setdefault(cell.theta, []).append(cell.seed)
    seed_sets = {tuple(seeds) for seeds in by_theta.values()}
    assert seed_sets == {design.fit.seed_values}


def test_a_cell_payload_round_trips_its_observables(design, cells):
    cell = cells[0]
    payload = run_cell(design, cell, runner=_stub)
    assert payload["design_id"] == design.design_id
    assert payload["cabin_air_mode"] == design.cabin_air_mode
    assert payload["cell"]["key"] == cell.key
    assert observables_from_payload(payload) == _stub(cell.scenario_id, cell.theta, cell.seed)


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_legacy_designs_default_to_zone_pool_and_keep_their_cells(version):
    design = load_design(
        REPO_ROOT / "picard_framework" / "runs"
        / f"covid_first_look_v{version}_design.json",
    )
    assert design.cabin_air_mode == "zone_pool"
    assert len(enumerate_cells(design)) == 11 * (20 + 50)
    assert enumerate_cells(design)[0].key.startswith("fit_")


def test_v5_design_uses_cabin_compartments_and_declares_770_cells():
    design = load_design(
        REPO_ROOT / "picard_framework" / "runs" / "covid_first_look_v5_design.json",
    )
    assert design.cabin_air_mode == "cabin_compartment"
    assert design.grid == pytest.approx(
        [1e7, 3.162277660168379e7, 1e8, 3.162277660168379e8,
         1e9, 3.162277660168379e9, 1e10, 3.162277660168379e10,
         1e11, 3.162277660168379e11, 1e12],
    )
    assert len(enumerate_cells(design)) == 220 + 550


def test_v5c_design_uses_zone_pool_and_declares_210_cells():
    design = load_design(
        REPO_ROOT / "picard_framework" / "runs" / "covid_first_look_v5c_design.json",
    )
    assert design.cabin_air_mode == "zone_pool"
    assert design.grid == pytest.approx([1e7, 3.162277660168379e7, 1e8])
    assert len(enumerate_cells(design)) == 60 + 150


def test_an_invalid_cabin_air_mode_in_a_design_is_refused(design):
    with pytest.raises(ValueError, match="cabin_air_mode"):
        replace(design, cabin_air_mode="invalid")


def test_run_cell_records_and_passes_the_design_cabin_air_mode(design, cells):
    seen: dict[str, object] = {}

    def runner(scenario_id, theta, seed, *, cabin_air_mode):
        seen["mode"] = cabin_air_mode
        return _stub(scenario_id, theta, seed)

    compartment_design = replace(design, cabin_air_mode="cabin_compartment")
    payload = run_cell(compartment_design, cells[0], runner=runner)
    assert seen["mode"] == "cabin_compartment"
    assert payload["cabin_air_mode"] == "cabin_compartment"


def test_the_merge_recovers_the_stub_scale(design, payloads):
    result = merge_fit(design, payloads)
    assert result.theta == TRUE_THETA
    assert not result.boundary_pinned
    assert not result.partial
    assert result.coverage["missing"] == []
    assert result.selection_frequency[TRUE_THETA] > 0.9


def test_loss_improves_toward_the_true_scale(design, payloads):
    result = merge_fit(design, payloads)
    by_theta = {c.theta: c.mean_loss for c in result.candidates}
    below = [t for t in design.grid if t < TRUE_THETA]
    assert [by_theta[t] for t in below] == sorted(
        (by_theta[t] for t in below), reverse=True,
    )


def test_takeoff_probability_is_read_from_the_seeds(design, payloads):
    result = merge_fit(design, payloads)
    extinct = sum(1 for s in design.fit.seed_values if s % 3 == 0)
    expected = 1.0 - extinct / design.fit.seeds
    at_true = next(c for c in result.candidates if c.theta == TRUE_THETA)
    assert at_true.takeoff_probability == pytest.approx(expected)


def test_the_fit_reads_training_cells_only(design, payloads):
    training_only = {
        key: payload for key, payload in payloads.items()
        if payload["cell"]["phase"] == FIT_PHASE
    }
    assert merge_fit(design, training_only).as_dict() == merge_fit(design, payloads).as_dict()


def test_a_partial_grid_is_refused_unless_declared(design, payloads, cells):
    dropped = next(cell for cell in cells if cell.phase == FIT_PHASE).key
    partial = {key: payload for key, payload in payloads.items() if key != dropped}
    with pytest.raises(ValueError, match="partial"):
        merge_fit(design, partial)
    result = merge_fit(design, partial, allow_partial=True)
    assert result.partial
    assert len(result.coverage["missing"]) == 1


def test_held_out_is_scored_at_the_fitted_theta_and_its_neighbours(design, payloads):
    fit = merge_fit(design, payloads)
    report = merge_held_out(design, payloads, fit.theta)
    assert report["split_preserved"] is True
    assert report["scored"]["theta"] == fit.theta
    neighbours = {r["theta"] for r in report["sensitivity"]}
    index = design.grid.index(fit.theta)
    assert neighbours == {design.grid[index - 1], design.grid[index + 1]}
    verdicts = {s["anchor_id"]: s["verdicts"] for s in report["scored"]["scores"]}
    assert set(verdicts) == {"covid.H1", "covid.H2"}
    assert sum(verdicts["covid.H1"].values()) == design.held_out.seeds
    assert report["scored"]["placement"]["anchor_id"] == "covid.H3"


def test_held_out_refuses_a_theta_off_the_grid(design, payloads):
    with pytest.raises(ValueError, match="not on the declared grid"):
        merge_held_out(design, payloads, 12345.0)


def test_extinct_seeds_are_undefined_not_hits(design, payloads):
    fit = merge_fit(design, payloads)
    report = merge_held_out(design, payloads, fit.theta)
    h1 = next(s for s in report["scored"]["scores"] if s["anchor_id"] == "covid.H1")
    assert h1["verdicts"]["undefined"] == 0
    assert report["scored"]["probability_no_positives"] == pytest.approx(
        sum(1 for s in design.held_out.seed_values if s % 3 == 0) / design.held_out.seeds,
    )


def test_a_design_that_swaps_the_split_roles_is_refused(design):
    swapped = replace(
        design,
        fit=replace(design.fit, scenario_id=design.held_out.scenario_id),
    )
    from picard_framework.covid_first_look import _assert_roles

    with pytest.raises(ValueError, match="held_out"):
        _assert_roles(swapped)


@pytest.mark.parametrize("stride", [1, 7, 50])
def test_array_children_cover_a_phase_exactly_once(cells, stride):
    entrypoint = _load_entrypoint()
    phase_cells = [cell for cell in cells if cell.phase == HELD_OUT_PHASE]
    children = -(-len(phase_cells) // stride)
    seen: list[Cell] = []
    for index in range(children):
        seen.extend(entrypoint.child_cells(cells, HELD_OUT_PHASE, index, stride))
    assert seen == phase_cells
    with pytest.raises(SystemExit):
        entrypoint.child_cells(cells, HELD_OUT_PHASE, children, stride)
