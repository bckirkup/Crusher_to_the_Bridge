"""Phase 1b boarding-axis screen: design, cells, axis mutation, merge.

No hull runs. The axis is applied to a real fit run-spec and read back; the
merge is fed a stub whose onsets are a known function of the axis so pairing
and the sanitary execution witness can be checked exactly.
"""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from picard_framework.covid_boarding_screen import (
    BoardingScreenDesign,
    ScreenCell,
    apply_boarding_axis,
    enumerate_cells,
    load_design,
    merge_screen,
)
from picard_framework.covid_theta_fit import HullObservables, build_fit_run_spec

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_entrypoint():
    path = REPO_ROOT / "deploy" / "aws" / "covid_boarding_screen_entrypoint.py"
    spec = importlib.util.spec_from_file_location("covid_boarding_screen_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_payload(cell: ScreenCell, *, visits: float = 100.0) -> dict:
    """Early onsets grow with age and imports; total onsets with imports only."""
    early = int(10 * cell.infection_age_days + 20 * cell.imports)
    total = 100 * cell.imports + (cell.seed % 7)
    obs = HullObservables(
        scenario_id=cell.scenario_id, theta=cell.theta, seed=cell.seed,
        recorded_onsets=total,
        onsets_before_split_day=early,
        onsets_on_or_after_split_day=total - early,
        passenger_onsets_before=1, passenger_onsets_after=1,
        crew_onsets_before=1, crew_onsets_after=1,
        campaign_specimens=2000, campaign_positives=300,
        campaign_asymptomatic_positives=150,
    )
    return {
        "design_id": "x",
        "cell": cell.as_dict(),
        "observables": obs.as_dict(),
        "onset_curve": {},
        "first_onset_day": 20 - int(cell.infection_age_days),
        "sanitary_activity": {"visits": visits, "person_seconds": visits * 155},
    }


@pytest.fixture(scope="module")
def design() -> BoardingScreenDesign:
    return load_design()


def test_design_is_the_declared_180_cell_screen(design):
    assert design.design_id == "covid_boarding_screen_v1"
    assert design.scenario_id == "diamond_princess_2020"
    assert design.thetas == (1e4, pytest.approx(10 ** 4.5), 1e5)
    assert design.infection_age_days == (0.0, 3.0, 6.0)
    assert design.imports == (1, 3)
    assert design.sanitary_visit_mode == "dwell_weighted"
    assert design.seeds == 10
    cells = enumerate_cells(design)
    assert len(cells) == 180
    assert [c.index for c in cells] == list(range(180))
    assert len({c.key for c in cells}) == 180


def test_baseline_cell_is_in_the_grid(design):
    cells = enumerate_cells(design)
    for theta in design.thetas:
        base = [
            c for c in cells
            if c.theta == theta and (c.infection_age_days, c.imports) == design.baseline
        ]
        assert [c.seed for c in base] == list(design.seed_values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sanitary_visit_mode", "always"),
        ("seeds", 0),
        ("infection_age_days", (0.0, -1.0)),
        ("imports", (0,)),
        ("thetas", (0.0,)),
    ],
)
def test_design_rejects_malformed_axes(design, field, value):
    with pytest.raises(ValueError):
        replace(design, **{field: value})


def test_apply_boarding_axis_edits_only_the_declared_seed_and_visit_mode():
    raw = build_fit_run_spec("diamond_princess_2020", 1e5, 20200205)
    before = raw["config_overrides"]["initiation"]["explicit_seeds"][0]
    assert (before["count"], before["infection_age_days"]) == (1, 0.0)
    out = apply_boarding_axis(
        raw, infection_age_days=6.0, imports=3, sanitary_visit_mode="dwell_weighted",
    )
    seed = out["config_overrides"]["initiation"]["explicit_seeds"][0]
    assert (seed["count"], seed["infection_age_days"]) == (3, 6.0)
    assert seed["pathogen"] == before["pathogen"]
    assert seed["epoch"] == before["epoch"]
    assert out["config_overrides"]["transmission"]["sanitary_visit_mode"] == "dwell_weighted"
    assert out is raw
    untouched = build_fit_run_spec("diamond_princess_2020", 1e5, 20200205)
    for key in untouched:
        if key != "config_overrides":
            assert out[key] == untouched[key], key
    for block in untouched["config_overrides"]:
        if block not in ("initiation", "transmission"):
            assert out["config_overrides"][block] == untouched["config_overrides"][block]


def test_apply_boarding_axis_refuses_ambiguous_seed_lists():
    raw = build_fit_run_spec("diamond_princess_2020", 1e5, 20200205)
    seeds = raw["config_overrides"]["initiation"]["explicit_seeds"]
    raw["config_overrides"]["initiation"]["explicit_seeds"] = seeds + [dict(seeds[0])]
    with pytest.raises(ValueError):
        apply_boarding_axis(
            raw, infection_age_days=0.0, imports=1, sanitary_visit_mode="none",
        )


def test_merge_pairs_every_axis_cell_against_the_baseline(design):
    cells = enumerate_cells(design)
    payloads = {c.key: _stub_payload(c) for c in cells}
    surface = merge_screen(design, payloads)
    assert surface["coverage"] == {"expected": 180, "found": 180, "partial": False}
    assert surface["sanitary_witness"]["consistent"] is True
    assert surface["sanitary_witness"]["cells_with_visits"] == 180
    assert len(surface["surface"]) == 18
    by_key = {
        (e["theta"], e["infection_age_days"], e["imports"]): e for e in surface["surface"]
    }
    base = by_key[(1e5, 0.0, 1)]
    assert base["is_baseline"] is True
    assert base["delta_vs_baseline"]["recorded_onsets"]["median"] == 0
    moved = by_key[(1e5, 6.0, 3)]
    assert moved["is_baseline"] is False
    assert moved["delta_vs_baseline"]["n"] == 10
    # (60 + 60) - 20 early onsets, exactly, on every paired seed
    assert moved["delta_vs_baseline"]["onsets_before_split_day"]["median"] == 100
    assert moved["delta_vs_baseline"]["onsets_before_split_day"]["q05"] == 100
    # imports 1 -> 3 adds exactly 200 total onsets; the seed term cancels
    assert moved["delta_vs_baseline"]["recorded_onsets"]["median"] == 200
    assert moved["delta_vs_baseline"]["seeds_with_more_early_onsets"] == 10
    assert moved["takeoff_probability"] == 1.0
    assert moved["first_onset_day"]["median"] == 14
    assert base["first_onset_day"]["median"] == 20


def test_merge_refuses_partial_unless_declared(design):
    cells = enumerate_cells(design)
    payloads = {c.key: _stub_payload(c) for c in cells[:-1]}
    with pytest.raises(ValueError):
        merge_screen(design, payloads)
    surface = merge_screen(design, payloads, allow_partial=True)
    assert surface["coverage"]["partial"] is True
    assert surface["coverage"]["found"] == 179


def test_witness_flags_declared_visits_that_never_ran(design):
    cells = enumerate_cells(design)
    payloads = {c.key: _stub_payload(c, visits=0.0) for c in cells}
    surface = merge_screen(design, payloads)
    assert surface["sanitary_witness"]["cells_with_visits"] == 0
    assert surface["sanitary_witness"]["consistent"] is False
    off = replace(design, sanitary_visit_mode="none")
    assert merge_screen(off, payloads)["sanitary_witness"]["consistent"] is True


def test_array_children_cover_every_cell_once(design):
    entry = _load_entrypoint()
    cells = enumerate_cells(design)
    seen = []
    for index in range(-(-len(cells) // 7)):
        seen.extend(c.index for c in entry.child_cells(cells, index, 7))
    assert seen == list(range(180))
    assert [c.index for c in entry.child_cells(cells, 5, 1)] == [5]
    with pytest.raises(SystemExit):
        entry.child_cells(cells, 180, 1)
    with pytest.raises(SystemExit):
        entry.child_cells(cells, 0, 0)
