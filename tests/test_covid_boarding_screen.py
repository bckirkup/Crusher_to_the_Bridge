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
    prepare_cell_run_spec,
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
    # infection_age_days moved 0.0 → 6.8 under SEED-ONSET-01: with the
    # declared onset_day (-1.0) it only fixes the implied incubation at the
    # profile median 5.8 d; it is no longer an independent assumption.
    assert (before["count"], before["infection_age_days"]) == (1, 6.8)
    assert before["onset_day"] == -1.0
    out = apply_boarding_axis(
        raw, infection_age_days=6.0, imports=3, sanitary_visit_mode="dwell_weighted",
    )
    seed = out["config_overrides"]["initiation"]["explicit_seeds"][0]
    assert (seed["count"], seed["infection_age_days"]) == (3, 6.0)
    assert seed["pathogen"] == before["pathogen"]
    assert seed["epoch"] == before["epoch"]
    # The axis moves infection_age_days only; a declared onset_day is the
    # record's and is carried through untouched.
    assert seed["onset_day"] == -1.0
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
    offset_block = [c.index for i in range(20) for c in entry.child_cells(cells, i, 1, 160)]
    assert offset_block == list(range(160, 180))
    with pytest.raises(SystemExit):
        entry.child_cells(cells, 180, 1)
    with pytest.raises(SystemExit):
        entry.child_cells(cells, 20, 1, 160)
    with pytest.raises(SystemExit):
        entry.child_cells(cells, 0, 1, -1)
    with pytest.raises(SystemExit):
        entry.child_cells(cells, 0, 0)


# ── v7 admissibility readout ──────────────────────────────────────────────

V7_DESIGN_REL = REPO_ROOT / "picard_framework" / "runs" / "covid_theta_screen_v7_design.json"


def test_v7_design_loads_and_enumerates_the_declared_screen():
    design = load_design(str(V7_DESIGN_REL))
    assert design.design_id == "covid_theta_screen_v7"
    assert design.scenario_id == "diamond_princess_2020"
    assert design.sanitary_visit_mode == "dwell_weighted"
    assert not design.is_refinement
    assert design.baseline == (0.0, 1)
    cells = enumerate_cells(design)
    assert len(cells) == 3080
    assert {c.imports for c in cells} == {1}
    assert len({c.key for c in cells}) == 3080


V8_DESIGN_REL = REPO_ROOT / "picard_framework" / "runs" / "covid_theta_screen_v8_design.json"


def test_v8_design_is_the_declared_refinement_screen():
    """v8 re-screens the v7 near-critical corner under a declared onset.

    The design is a point-list refinement because the paired baseline
    (infection age 0, one import) became a contradiction under
    SEED-ONSET-01 — onset day -1.0 at age 0 implies a negative incubation.
    """
    import json

    design = load_design(str(V8_DESIGN_REL))
    assert design.design_id == "covid_theta_screen_v8"
    assert design.scenario_id == "diamond_princess_2020"
    assert design.is_refinement
    assert design.parent_design == "covid_theta_screen_v7"
    cells = enumerate_cells(design)
    assert len(cells) == 1680
    assert len({c.key for c in cells}) == 1680
    assert design.thetas == (
        1e7, 31622776.60168379, 1e8, 316227766.01683795,
        1e9, 3162277660.1683793, 1e10,
    )
    assert design.infection_age_days == (3.3, 4.8, 6.8, 9.8, 12.8, 15.6)
    raw = json.loads(V8_DESIGN_REL.read_text(encoding="utf-8"))
    assert raw["admissibility"]["declared_before_running"] is True


def test_v8_axis_cannot_reintroduce_the_baseline_contradiction():
    """Every declared point's implied incubation is positive and inside
    the profile's shedding window, and age 0 is off the axis: under the
    declared onset_day = -1.0 the v7 root-grid baseline would be a
    load-time refusal, so a future axis edit fails loudly instead of
    silently screening a nonsense cell."""
    import json

    from engines.initiation import apply_explicit_seeds, resolve_initiation_plan

    raw = json.loads(V8_DESIGN_REL.read_text(encoding="utf-8"))
    ages = raw["infection_age_days"]
    assert 0.0 not in ages

    onset_day = -1.0  # the scenario's declared index onset (SEED-ONSET-01)
    profile = json.loads(
        (REPO_ROOT / "data" / "pathogens" / "active_profiles.json").read_text(
            encoding="utf-8",
        ),
    )
    sars = next(
        p for p in profile["pathogens"] if p["pathogen_id"] == "sars_cov2_resp"
    )
    shedding_window = float(
        sars.get("shedding_duration_days", sars["recovery_day"])
    )
    for age in ages:
        incubation = age + onset_day
        assert 0.0 < incubation < shedding_window, (
            f"age {age} implies incubation {incubation} d, outside "
            f"(0, {shedding_window})"
        )

    # And the refused cell itself: the root-grid baseline (age 0) with the
    # declared onset is a contradiction, so applying it raises rather than
    # screening a host whose onset precedes its acquisition.
    import numpy as np

    from engines.infection_dynamics_bridge import KorkinAgent
    from engines.sim_clock import SimClock

    clock = SimClock(epoch_duration_hours=6.0, mode="hours")
    agent = KorkinAgent(
        agent_id=0, role="passenger", immune=False, home_zone="Z",
        dining_zone="Z", work_zone="Z", free_zone="Z",
        schedule=["Free"] * 4,
    )
    agent.clock = clock
    agent.current_location = "Z"

    class _Engine:
        def __init__(self) -> None:
            self.clock = clock
            self.agents = [agent]
            self.initiation_manifest = {}

    plan = resolve_initiation_plan(
        {
            "initiation": {
                "explicit_seeds": [
                    {
                        "pathogen": "sars_cov2_resp",
                        "count": 1,
                        "epoch": 0,
                        "infection_age_days": 0.0,
                        "onset_day": onset_day,
                    },
                ],
            },
        },
        {"sars_cov2_resp": sars},
    )
    with pytest.raises(ValueError, match="onset"):
        apply_explicit_seeds(
            plan, _Engine(), 0, np.random.default_rng(0),
            {"sars_cov2_resp": sars},
        )


def _v7_stub(cell: ScreenCell, onsets: int, *, boards_symptomatic: bool) -> dict:
    """A payload centred near ``onsets`` whose T1 interval contains it."""
    seed_jitter = (cell.seed % 3) - 1  # -1, 0, +1
    recorded = onsets + 5 * seed_jitter
    before = round(recorded * (34 / 197))
    obs = HullObservables(
        scenario_id=cell.scenario_id, theta=cell.theta, seed=cell.seed,
        recorded_onsets=recorded,
        onsets_before_split_day=before,
        onsets_on_or_after_split_day=recorded - before,
        passenger_onsets_before=1, passenger_onsets_after=1,
        crew_onsets_before=1, crew_onsets_after=1,
        campaign_specimens=3063 + 10 * seed_jitter,
        campaign_positives=634 + 5 * seed_jitter,
        campaign_asymptomatic_positives=320,
    )
    return {
        "design_id": "x",
        "cell": cell.as_dict(),
        "observables": obs.as_dict(),
        "onset_curve": {},
        "first_onset_day": None,
        "sanitary_activity": {"visits": 100.0},
        "index_onset_day": -2.5 if boards_symptomatic else 1.5,
        "index_shedding_at_day0": boards_symptomatic,
        "index_departed_epoch": 120,
        "infections_total": int(recorded),
        "aboard_total": 3711,
        "attack_rate": recorded / 3711,
        "vsp_reported_case_fraction_max": 0.04 if seed_jitter > 0 else 0.01,
    }


def test_merge_evaluates_the_v7_admissibility_criteria():
    """Graded: only the cell centred on the T1 reading passes; geometry flips
    on the sign of the seeded host's own onset day."""
    design = BoardingScreenDesign(
        design_id="v7_probe", scenario_id="diamond_princess_2020",
        thetas=(1e10,), infection_age_days=(0.0, 5.0, 9.0), imports=(1,),
        sanitary_visit_mode="dwell_weighted", seed_base=20200205,
        seeds=10, takeoff_recorded_onsets=10,
    )
    centre = {0.0: 100, 5.0: 197, 9.0: 400}
    payloads = {
        c.key: _v7_stub(
            c, centre[c.infection_age_days],
            boards_symptomatic=(c.infection_age_days == 5.0),
        )
        for c in enumerate_cells(design)
    }
    surface = merge_screen(design, payloads)
    by_age = {e["infection_age_days"]: e for e in surface["surface"]}
    assert [by_age[a]["t1_ok"] for a in (0.0, 5.0, 9.0)] == [False, True, False]
    assert [by_age[a]["t3_ok"] for a in (0.0, 5.0, 9.0)] == [True, True, True]
    assert [by_age[a]["index_geometry_ok"] for a in (0.0, 5.0, 9.0)] == [
        False, True, False,
    ]
    assert by_age[5.0]["index_geometry_pass_fraction"] == 1.0
    assert by_age[0.0]["index_geometry_pass_fraction"] == 0.0
    crossing = by_age[5.0]["vsp_threshold_crossing_fraction"]
    assert 0.0 < crossing < 1.0
    assert by_age[5.0]["attack_rate_quantiles"]["q50"] > 0.0
    assert (
        by_age[5.0]["attack_rate_quantiles_given_vsp_crossing"]["q50"]
        > by_age[5.0]["attack_rate_quantiles"]["q10"]
    )


def test_geometry_fields_are_none_on_pre_v7_payloads(design):
    """v1-shaped payloads carry no index fields; absence reads as None,
    not as a failed criterion."""
    cells = enumerate_cells(design)
    payloads = {c.key: _stub_payload(c) for c in cells}
    for entry in merge_screen(design, payloads)["surface"]:
        assert entry["index_geometry_ok"] is None
        assert entry["index_geometry_pass_fraction"] is None


def test_a_real_cell_reports_the_index_geometry(design):
    """Age 9: onset lands before boarding and the host emits at epoch 0;
    age 0: onset cannot precede boarding (or never arrives in-window)."""
    cell_at = lambda age: ScreenCell(  # noqa: E731
        index=0, scenario_id="greg_mortimer_2020", theta=1e10,
        infection_age_days=age, imports=1, seed=20200205,
    )
    from picard_framework.covid_boarding_screen import simulate_screen_cell
    aged = simulate_screen_cell(design, cell_at(9.0), num_epochs=48)
    assert aged["index_onset_day"] is not None
    assert aged["index_onset_day"] < 0.0
    assert aged["index_shedding_at_day0"] is True
    fresh = simulate_screen_cell(design, cell_at(0.0), num_epochs=48)
    assert fresh["index_shedding_at_day0"] is False
    assert fresh["index_onset_day"] is None or fresh["index_onset_day"] >= 0.0


@pytest.mark.parametrize("age", [2.0, 4.0, 6.8, 9.0])
def test_declared_onset_day_returns_the_declared_day(age):
    """SEED-ONSET-01: _index_geometry must return onset_day exactly.

    With onset stamped rather than drawn, ``days_elapsed(infection_epoch)
    + incubation_days - infection_age_days`` collapses to the declared day
    identically — a geometry the free incubation draw could only hit by
    chance.
    """
    import numpy as np

    from engines.infection_dynamics_bridge import KorkinAgent
    from engines.initiation import (
        apply_explicit_seeds,
        resolve_initiation_plan,
    )
    from engines.sim_clock import SimClock
    from picard_framework.covid_boarding_screen import (
        PATHOGEN_ID,
        _index_geometry,
    )

    onset = -1.0
    clock = SimClock(epoch_duration_hours=6.0, mode="hours")
    profile = {
        "shedding_curve_log10": [7.0] * 40,
        "asymptomatic_shedding_log10": [7.0] * 40,
        "symptom_onset_day": 0.0,
        "recovery_day": 1000.0,
        "shedding_duration_days": 30.0,
        "dose_response": {"model": "exponential", "k": 0.05},
    }

    class _Engine:
        def __init__(self, sim_clock) -> None:
            self.clock = sim_clock
            self.initiation_manifest = {}

    engine = _Engine(clock)
    engine.agents = [
        KorkinAgent(
            agent_id=i, role="passenger", immune=False, home_zone="Z",
            dining_zone="Z", work_zone="Z", free_zone="Z",
            schedule=["Free"] * 4,
        )
        for i in range(10)
    ]
    for a in engine.agents:
        a.clock = clock
        a.current_location = "Z"
    plan = resolve_initiation_plan(
        {
            "initiation": {
                "explicit_seeds": [
                    {
                        "pathogen": PATHOGEN_ID,
                        "count": 1,
                        "epoch": 0,
                        "infection_age_days": age,
                        "onset_day": onset,
                    },
                ],
            },
        },
        {PATHOGEN_ID: profile},
    )
    apply_explicit_seeds(
        plan, engine, 0, np.random.default_rng(3), {PATHOGEN_ID: profile},
    )
    cell = ScreenCell(
        index=0, scenario_id="diamond_princess_2020", theta=1e9,
        infection_age_days=age, imports=1, seed=1,
    )
    geometry = _index_geometry(engine, cell, profile)
    assert geometry["index_onset_day"] == pytest.approx(onset)
    assert geometry["index_shedding_at_day0"] is True


# ── v9 onset-mass diagnostic ──────────────────────────────────────────────

V9_DESIGN_REL = REPO_ROOT / "picard_framework" / "runs" / "covid_theta_screen_v9_design.json"


def _per_seed_stub(cell: ScreenCell, by_seed_onsets: dict[int, int]) -> dict:
    """A payload whose recorded_onsets are stated per seed, not jittered."""
    recorded = int(by_seed_onsets[cell.seed])
    before = round(recorded * (34 / 197))
    obs = HullObservables(
        scenario_id=cell.scenario_id, theta=cell.theta, seed=cell.seed,
        recorded_onsets=recorded,
        onsets_before_split_day=before,
        onsets_on_or_after_split_day=recorded - before,
        passenger_onsets_before=1, passenger_onsets_after=1,
        crew_onsets_before=1, crew_onsets_after=1,
        campaign_specimens=3063,
        campaign_positives=634,
        campaign_asymptomatic_positives=320,
    )
    return {
        "design_id": "x",
        "cell": cell.as_dict(),
        "observables": obs.as_dict(),
        "onset_curve": {},
        "first_onset_day": None,
        "sanitary_activity": {"visits": 100.0},
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "index_departed_epoch": 120,
        "infections_total": recorded,
        "aboard_total": 3711,
        "attack_rate": recorded / 3711,
        "vsp_reported_case_fraction_max": 0.04,
    }


def _single_cell_surface(by_seed_onsets: dict[int, int]) -> dict:
    design = BoardingScreenDesign(
        design_id="v9_probe", scenario_id="diamond_princess_2020",
        thetas=(1e9,), infection_age_days=(6.8,), imports=(1,),
        sanitary_visit_mode="dwell_weighted", seed_base=20200205,
        seeds=len(by_seed_onsets), takeoff_recorded_onsets=10,
    )
    payloads = {
        c.key: _per_seed_stub(c, by_seed_onsets)
        for c in enumerate_cells(design)
    }
    surface = merge_screen(design, payloads)
    assert len(surface["surface"]) == 1
    return surface["surface"][0]


def test_onset_mass_is_one_when_every_seed_lands_on_target():
    seeds = {20200205 + i: 180 + 7 * i for i in range(10)}
    entry = _single_cell_surface(seeds)
    assert entry["onset_mass_near_target"] == 1.0
    assert entry["recorded_onsets_per_seed"] == [
        seeds[s] for s in sorted(seeds)
    ]
    assert entry["seeds"] == sorted(seeds)
    assert entry["onset_mass_near_target_bounds"] == [98.5, 394.0]


def test_onset_mass_is_zero_on_the_bimodal_cell_that_passes_t1():
    """The v7 failure mode: the T1 interval covers 197 because half the
    seeds die and half burn — the diagnostic must separate the two."""
    seeds = {
        **{20200205 + i: 2 + i for i in range(5)},
        **{20200205 + 5 + i: 2950 + 10 * i for i in range(5)},
    }
    entry = _single_cell_surface(seeds)
    assert entry["onset_mass_near_target"] == 0.0
    assert entry["t1_ok"] is True  # p10<=197<=p90 and before-share in range
    assert entry["recorded_onsets_per_seed"] == [
        seeds[s] for s in sorted(seeds)
    ]


def test_onset_mass_is_graded_between_the_extremes():
    seeds = {
        **{20200205 + i: 150 + i for i in range(6)},   # inside [98.5, 394]
        **{20200205 + 6 + i: 900 + i for i in range(4)},
    }
    entry = _single_cell_surface(seeds)
    assert 0.0 < entry["onset_mass_near_target"] < 1.0
    assert entry["onset_mass_near_target"] == 0.6


def test_v9_design_is_the_declared_recentring_screen():
    design = load_design(str(V9_DESIGN_REL))
    assert design.design_id == "covid_theta_screen_v9"
    assert design.scenario_id == "diamond_princess_2020"
    assert design.is_refinement
    assert design.parent_design == "covid_theta_screen_v8"
    cells = enumerate_cells(design)
    assert len(cells) == 600
    assert len({c.key for c in cells}) == 600
    assert min(design.thetas) == 1e1
    assert max(design.thetas) == 1e10
    assert design.infection_age_days == (3.3, 6.8, 12.8)
    assert design.seeds == 20


# ── v11 generic-voyage mode ───────────────────────────────────────────────

V11_DESIGN_REL = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_theta_screen_v11_design.json"
)


@pytest.fixture(scope="module")
def v11() -> BoardingScreenDesign:
    return load_design(str(V11_DESIGN_REL))


def test_v11_design_is_the_declared_generic_fleet_screen(v11):
    assert v11.design_id == "covid_theta_screen_v11"
    assert v11.scenario_id == "diamond_princess_2020"
    assert v11.voyage_mode == "generic"
    assert v11.thetas == (1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11)
    assert v11.infection_age_days == (0.0,)
    assert v11.imports == (1,)
    assert v11.seeds == 200
    assert v11.seed_base == 20201001
    cells = enumerate_cells(v11)
    assert len(cells) == 1600
    # Theta-outer, seed-inner: the canary row is 1e8 at indices 800..999.
    assert cells[800].theta == 1e8
    assert cells[800].seed == 20201001
    assert cells[999].theta == 1e8
    assert cells[999].seed == 20201200


def test_design_rejects_an_unknown_voyage_mode(design):
    with pytest.raises(ValueError):
        replace(design, voyage_mode="chartered")


def _generic_seed(raw: dict) -> dict:
    return raw["config_overrides"]["initiation"]["explicit_seeds"][0]


def test_generic_spec_drops_the_declared_onset_and_departure(v11):
    cell = enumerate_cells(v11)[800]
    raw = prepare_cell_run_spec(v11, cell)
    seed = _generic_seed(raw)
    assert "onset_day" not in seed
    assert "departure_day" not in seed
    assert seed["count"] == 1
    # The 168-epoch generic voyage is stamped in all three places.
    assert raw["run"]["num_epochs"] == 168
    assert raw["config_overrides"]["num_epochs"] == 168
    assert raw["config_overrides"]["voyage"]["total_epochs"] == 168


def test_generic_age_is_drawn_paired_across_theta(v11):
    cells = [c for c in enumerate_cells(v11) if c.seed == 20201001]
    assert len(cells) == 8
    ages = {
        _generic_seed(prepare_cell_run_spec(v11, c))["infection_age_days"]
        for c in cells
    }
    assert len(ages) == 1
    assert 0.5 <= ages.pop() <= 21.0


def test_generic_ages_vary_across_seeds_inside_the_window(v11):
    ages = [
        _generic_seed(prepare_cell_run_spec(v11, c))["infection_age_days"]
        for c in enumerate_cells(v11)[800:820]
    ]
    assert len(set(ages)) == len(ages)
    assert all(0.5 <= a <= 21.0 for a in ages)


def test_generic_spec_respects_an_explicit_num_epochs(v11):
    raw = prepare_cell_run_spec(
        v11, enumerate_cells(v11)[800], num_epochs=48,
    )
    assert raw["run"]["num_epochs"] == 48


def test_generic_mode_without_an_incubation_profile_refuses(v11):
    import numpy as np

    raw = build_fit_run_spec("diamond_princess_2020", 1e8, 20201001)
    with pytest.raises(ValueError):
        apply_boarding_axis(
            raw, infection_age_days=0.0, imports=1,
            sanitary_visit_mode="dwell_weighted",
            voyage_mode="generic", incubation_profile={},
            age_stream=np.random.default_rng(0),
        )
    with pytest.raises(ValueError):
        apply_boarding_axis(
            raw, infection_age_days=0.0, imports=1,
            sanitary_visit_mode="dwell_weighted",
            voyage_mode="generic",
            incubation_profile={"incubation": {"median_days": 5.8}},
            age_stream=None,
        )


def test_a_real_generic_cell_runs_and_reports_geometry():
    """A generic voyage on the small hull: the drawn age reaches the index
    geometry fields and the index never departs."""
    from picard_framework.covid_boarding_screen import simulate_screen_cell

    design = BoardingScreenDesign(
        design_id="generic_probe", scenario_id="greg_mortimer_2020",
        thetas=(1e9,), infection_age_days=(0.0,), imports=(1,),
        sanitary_visit_mode="dwell_weighted", seed_base=20200315,
        seeds=1, takeoff_recorded_onsets=10,
        voyage_mode="generic",
    )
    cell = enumerate_cells(design)[0]
    spec = prepare_cell_run_spec(design, cell, num_epochs=48)
    drawn = _generic_seed(spec)["infection_age_days"]
    assert 0.5 <= drawn <= 21.0
    payload = simulate_screen_cell(design, cell, num_epochs=48)
    assert payload["index_departed_epoch"] is None
    assert set(payload) >= {
        "observables", "onset_curve", "first_onset_day",
        "index_onset_day", "index_shedding_at_day0",
        "infections_total", "aboard_total", "attack_rate",
    }


# ── v11 fleet-shape selector ──────────────────────────────────────────────

def test_fleet_shape_passes_inside_the_h3_window():
    # ~9 recorded onsets on a 3,711-host hull ≈ 0.0024 attack rate.
    seeds = {20200205 + i: 7 + (i % 5) for i in range(20)}
    entry = _single_cell_surface(seeds)
    shape = entry["recorded_attack_rate"]
    assert entry["fleet_shape_ok"] is True
    assert 0.0005 <= shape["median"] <= 0.008
    assert shape["mean"] <= 0.06
    assert entry["p_recorded_ge_0p015"] == 0.0


def test_fleet_shape_fails_on_an_extinct_or_burning_row():
    # Half extinct, half burning: median and mean both leave the window.
    seeds = {
        **{20200205 + i: 0 for i in range(10)},
        **{20200205 + 10 + i: 2500 + 10 * i for i in range(10)},
    }
    entry = _single_cell_surface(seeds)
    assert entry["fleet_shape_ok"] is False
    assert entry["recorded_attack_rate"]["median"] > 0.008
    assert entry["recorded_attack_rate"]["mean"] > 0.06
    assert entry["p_recorded_ge_0p10"] == pytest.approx(0.5)


def test_fleet_shape_fails_on_mean_with_a_single_outlier():
    # 19 quiet voyages pin the median inside the window; one burner drags
    # the mean above 0.06 — the selector is three clauses, not one.
    seeds = {
        **{20200205 + i: 9 for i in range(19)},
        20200205 + 19: 8000,
    }
    entry = _single_cell_surface(seeds)
    assert 0.0005 <= entry["recorded_attack_rate"]["median"] <= 0.008
    assert entry["recorded_attack_rate"]["mean"] > 0.06
    assert entry["fleet_shape_ok"] is False
