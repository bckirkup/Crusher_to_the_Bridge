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
    echo_screen_cell,
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
    engine = _Engine()
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="onset"):
        apply_explicit_seeds(
            plan, engine, 0, rng,
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
    assert cells[800].theta == pytest.approx(1e8)
    assert cells[800].seed == 20201001
    assert cells[999].theta == pytest.approx(1e8)
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


def test_generic_spec_opens_the_swab_channel_from_embarkation(v11, design):
    generic = prepare_cell_run_spec(v11, enumerate_cells(v11)[800])
    assert (
        "molecular_ascertainment_start_day"
        not in generic["config_overrides"]["syndromic"]
    )
    declared = prepare_cell_run_spec(design, enumerate_cells(design)[160])
    assert (
        declared["config_overrides"]["syndromic"][
            "molecular_ascertainment_start_day"
        ] == pytest.approx(14)
    )


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
    assert entry["p_recorded_ge_0p015"] == pytest.approx(0.0)


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


# ── covid_rebase_01: seed_patch arms and the seed-ring readout ───────────

REBASE_DESIGN_REL = (
    REPO_ROOT / "picard_framework" / "runs" / "covid_rebase_01_design.json"
)


def test_rebase_design_is_the_declared_generic_fleet_screen():
    rebase = load_design(str(REBASE_DESIGN_REL))
    assert rebase.design_id == "covid_rebase_01"
    assert rebase.scenario_id == "diamond_princess_2020"
    assert rebase.voyage_mode == "generic"
    assert rebase.thetas == (
        1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10,
        1.33e10, 1.78e10, 2.37e10, 3.16e10, 4.22e10, 5.62e10, 7.5e10,
        1e11, 1e12,
    )
    assert rebase.infection_age_days == (0.0,)
    assert rebase.imports == (1,)
    assert rebase.seeds == 200
    assert rebase.seed_base == 20201001
    assert rebase.seed_ring_readout is False
    cells = enumerate_cells(rebase)
    assert len(cells) == 3200
    # Theta-outer, seed-inner: the canary row is 4.22e10 at 2200..2399.
    assert cells[2200].theta == pytest.approx(4.22e10)
    assert cells[2200].seed == 20201001
    assert cells[2219].seed == 20201020
    assert cells[2399].theta == pytest.approx(4.22e10)


def _arm_design(arms: list[dict]) -> BoardingScreenDesign:
    """A declared-replay arm probe: one Theta, declared age, two seeds."""
    return BoardingScreenDesign(
        design_id="seed_patch_probe", scenario_id="diamond_princess_2020",
        thetas=(1e9,), infection_age_days=(6.8,), imports=(1,),
        sanitary_visit_mode="dwell_weighted", seed_base=20200205,
        seeds=2, takeoff_recorded_onsets=10,
        arms=tuple(arms), seed_ring_readout=True,
    )


def test_seed_patch_arm_writes_the_seed_record():
    design = _arm_design([
        {"arm_id": "B0_declared", "overrides": {}},
        {
            "arm_id": "B1_late_onset",
            "overrides": {"seed_patch": {"onset_day": 3.0, "count": 4}},
        },
    ])
    cells = enumerate_cells(design)
    base = next(c for c in cells if c.arm_id == "B0_declared")
    patched = next(c for c in cells if c.arm_id == "B1_late_onset")
    seed_b = _generic_seed(prepare_cell_run_spec(design, base))
    seed_p = _generic_seed(prepare_cell_run_spec(design, patched))
    assert seed_b["onset_day"] == pytest.approx(-1.0)
    assert seed_b["count"] == 1
    assert seed_p["onset_day"] == pytest.approx(3.0)
    assert seed_p["count"] == 4
    assert seed_p["departure_day"] == pytest.approx(5.0)


def test_seed_patch_null_removes_the_field():
    design = _arm_design([
        {"arm_id": "B0_declared", "overrides": {}},
        {"arm_id": "B2_no_onset", "overrides": {"seed_patch": {"onset_day": None}}},
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B2_no_onset"
    )
    seed = _generic_seed(prepare_cell_run_spec(design, cell))
    assert "onset_day" not in seed
    assert seed["departure_day"] == pytest.approx(5.0)


@pytest.mark.parametrize("patch", [
    {"bogus_field": 1},
    {"count": 0},
    {"count": 2.5},
    {"count": True},
    {"onset_day": "soon"},
    {"infection_age_days": -1.0},
    {"onset_day": float("inf")},
    {"role": 7},
    [3.0],
])
def test_seed_patch_rejects_out_of_grammar_values(patch):
    design = _arm_design([
        {"arm_id": "B0_declared", "overrides": {}},
        {"arm_id": "B1_bad", "overrides": {"seed_patch": patch}},
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_bad"
    )
    with pytest.raises(ValueError, match="seed_patch"):
        prepare_cell_run_spec(design, cell)


def test_seed_ring_readout_flag_round_trips(design):
    flagged = replace(design, seed_ring_readout=True)
    assert flagged.as_dict()["seed_ring_readout"] is True
    assert design.as_dict()["seed_ring_readout"] is False


def test_seed_ring_summary_aggregates_per_seed_blocks():
    design = BoardingScreenDesign(
        design_id="ring_probe", scenario_id="diamond_princess_2020",
        thetas=(1e10,), infection_age_days=(6.8,), imports=(1,),
        sanitary_visit_mode="dwell_weighted", seed_base=20200205,
        seeds=4, takeoff_recorded_onsets=10, seed_ring_readout=True,
    )
    onsets = {20200205: 100, 20200206: 100, 20200207: 5, 20200208: 5}
    yields = {20200205: 10.0, 20200206: 20.0, 20200207: 30.0, 20200208: 40.0}
    payloads = {}
    for cell in enumerate_cells(design):
        payload = _per_seed_stub(cell, onsets)
        payload["seed_ring"] = {
            "seeded_count": 1,
            "seed_spec": {"onset_day": -1.0, "departure_day": 5.0},
            "index_departure_epoch": 120,
            "aboard_window_acquisitions": int(yields[cell.seed]),
            "aboard_window_clean_bound": int(yields[cell.seed]) - 2,
            "first_secondary_shed_epoch": 30,
            "aboard_window_by_route": {"droplet_far": int(yields[cell.seed])},
            "aboard_window_by_day": {"1": int(yields[cell.seed])},
            "yield_per_seeded_host": yields[cell.seed],
        }
        payloads[cell.key] = payload
    entry = merge_screen(design, payloads)["surface"][0]
    ring = entry["seed_ring"]
    assert ring["n"] == 4
    assert ring["yield_per_seeded_host"]["median"] == pytest.approx(25.0)
    assert ring["aboard_window_clean_bound"]["median"] == pytest.approx(23.0)
    assert ring["yield_per_seeded_host_on_takeoff"]["n"] == 2
    assert (
        ring["yield_per_seeded_host_on_takeoff"]["median"]
        == pytest.approx(15.0)
    )
    assert ring["aboard_window_by_route_pooled"] == {"droplet_far": 100}


def test_seed_ring_summary_absent_without_blocks():
    entry = _single_cell_surface({20200205 + i: 9 for i in range(5)})
    assert "seed_ring" not in entry


def test_a_real_declared_cell_reports_the_seed_ring(design):
    """Echo readout at initialize(): the ring block echoes the applied seed
    spec and the aboard-window counts are present (emptiness is a valid
    reading)."""
    flagged = replace(design, seed_ring_readout=True)
    cell = ScreenCell(
        index=0, scenario_id="diamond_princess_2020", theta=1e10,
        infection_age_days=6.8, imports=1, seed=20200205,
    )
    payload = echo_screen_cell(flagged, cell)
    ring = payload["seed_ring"]
    assert ring["seeded_count"] == 1
    assert ring["seed_spec"]["onset_day"] == pytest.approx(-1.0)
    assert ring["seed_spec"]["departure_day"] == pytest.approx(5.0)
    assert ring["seed_spec"]["infection_age_days"] == pytest.approx(6.8)
    assert len(ring["seeded_hosts"]) == 1
    host = ring["seeded_hosts"][0]
    assert host["role"] == "passenger"
    assert host["agent_class"]
    assert host["home_zone"]
    assert host["cabin_ring_size"] >= 0
    assert host["table_ring_size"] >= 0
    assert ring["index_departure_epoch"] is not None
    assert ring["aboard_window_acquisitions"] >= 0
    assert ring["aboard_window_clean_bound"] <= (
        ring["aboard_window_acquisitions"]
    )


def test_a_placement_arm_cell_reports_seeded_host_placement():
    """Echo readout on a crew + count + ring-inclusion arm: the
    seeded_hosts echo reports each drawn host's realized role and ring
    sizes, and the resolved exposure-cap flag is echoed."""

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_crew_ring",
            "overrides": {
                "seed_patch": {"role": "crew", "count": 3},
                "transmission_overrides": {
                    "exposure_cap": {"include_fixed_rings": True},
                },
            },
        },
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_crew_ring"
    )
    payload = echo_screen_cell(design, cell)
    assert payload["exposure_cap_include_fixed_rings"] is True
    ring = payload["seed_ring"]
    assert ring["seeded_count"] == 3
    assert ring["seed_spec"]["role"] == "crew"
    assert ring["seed_spec"]["count"] == 3
    hosts = ring["seeded_hosts"]
    assert len(hosts) == 3
    assert len({h["agent_id"] for h in hosts}) == 3
    for host in hosts:
        assert host["role"] == "crew"
        assert host["home_zone"].startswith("CC_")
        assert isinstance(host["cabin_ring_size"], int)
        assert isinstance(host["table_ring_size"], int)


def test_a_real_coop_arm_cell_echoes_the_resolved_dose_response():
    """Echo readout: a cooperative_packet arm's payload echoes the
    resolved dose_response block (model, n_star, carrier_loading, and the
    beta-frailty params that ride over the deep-merge)."""

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_coop",
            "overrides": {
                "pathogen_overrides": {
                    "sars_cov2_resp": {
                        "dose_response": {
                            "model": "cooperative_packet",
                            "n_star": 3,
                            "carrier_loading": {"dry": 0.05, "wet": 20.0},
                        },
                    },
                },
            },
        },
    ])
    cells = enumerate_cells(design)
    coop = next(c for c in cells if c.arm_id == "B1_coop")
    payload = echo_screen_cell(design, coop)
    echo = payload["dose_response"]
    assert echo["model"] == "cooperative_packet"
    assert echo["n_star"] == 3
    assert echo["carrier_loading"] == {"dry": 0.05, "wet": 20.0}
    assert echo["alpha"] == pytest.approx(0.18)
    assert echo["beta"] == pytest.approx(58.0)
    assert echo["susceptibility_scale"] > 0.0

    base = next(c for c in cells if c.arm_id == "B0_baseline")
    base_echo = echo_screen_cell(design, base)["dose_response"]
    assert base_echo["model"] == "beta_poisson"
    assert "n_star" not in base_echo


def test_a_delivery_arm_cell_echoes_the_resolved_delivery_block():
    """Echo readout on delivery-machinery arms (HEAT-V1 lineage): the
    payload's delivery block echoes the resolved half-life, the merged
    route-efficiency map, the pool transport mode, the exposure_cap
    sub-block + engine-active flag, and the resolved activity_contacts
    table."""

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_heat",
            "overrides": {
                "pathogen_overrides": {
                    "sars_cov2_resp": {"airborne_half_life_hours": 0.5},
                },
                "profile_route_efficiency_multipliers": {
                    "droplet": 0.03,
                    "hvac_airborne": 0.03,
                },
                "pathogen_pool_transport": "none",
                "transmission_overrides": {
                    "exposure_cap": {"include_fixed_rings": True},
                },
            },
        },
    ])
    cells = enumerate_cells(design)
    heat = next(c for c in cells if c.arm_id == "B1_heat")
    delivery = echo_screen_cell(design, heat)["delivery"]
    assert delivery["airborne_half_life_hours"] == pytest.approx(0.5)
    eff = delivery["route_efficiency_multipliers"]
    assert eff["droplet"] == pytest.approx(0.03)
    assert eff["hvac_airborne"] == pytest.approx(0.03)
    assert eff["direct_contact"] == pytest.approx(0.25)
    assert eff["fomite"] == pytest.approx(0.1)
    assert delivery["pathogen_pool_transport"] == "none"
    assert delivery["exposure_cap"] == {"include_fixed_rings": True}
    assert delivery["exposure_cap_active"] is True
    contacts = delivery["activity_contacts"]
    assert contacts["dining_table"]["passenger"] == pytest.approx(2.0)

    base = next(c for c in cells if c.arm_id == "B0_baseline")
    base_delivery = echo_screen_cell(design, base)["delivery"]
    assert base_delivery["airborne_half_life_hours"] == pytest.approx(1.1)
    assert base_delivery["route_efficiency_multipliers"]["droplet"] == (
        pytest.approx(0.3)
    )
    assert base_delivery["pathogen_pool_transport"] == "airflow"
    assert base_delivery["exposure_cap"] == {}
    assert base_delivery["exposure_cap_active"] is True


def test_a_hand_mode_arm_cell_echoes_the_resolved_hand_mode():
    """Echo readout on hand-reservoir arms (COVID-HAND-AB-01): the
    delivery block echoes the engine-resolved transmission
    .hand_reservoir_mode so the arm is auditable from the payload."""

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_hand",
            "overrides": {
                "transmission_overrides": {
                    "hand_reservoir_mode": "spike_decay",
                },
            },
        },
    ])
    cells = enumerate_cells(design)
    arm = next(c for c in cells if c.arm_id == "B1_hand")
    delivery = echo_screen_cell(design, arm)["delivery"]
    assert delivery["hand_reservoir_mode"] == "spike_decay"

    base = next(c for c in cells if c.arm_id == "B0_baseline")
    base_delivery = echo_screen_cell(design, base)["delivery"]
    # The baseline arm resolves the shipped default (hygiene_cycle).
    assert base_delivery["hand_reservoir_mode"] == "hygiene_cycle"


# ── SUSCEPT-V1: susceptibility / effective-population arms ───────────────

SUSCEPT_V1_DESIGN = (
    REPO_ROOT
    / "picard_framework"
    / "runs"
    / "covid_suscept_v1_design.json"
)


def test_suscept_v1_design_is_the_declared_480_cell_screen():
    design = load_design(str(SUSCEPT_V1_DESIGN))
    cells = enumerate_cells(design)
    assert len(cells) == 480
    assert design.arm_ids == (
        "D0_declared", "REF_M0P56", "IMM10", "IMM25", "IMM50", "IMM75",
        "IMM25_C0", "IMM25_C90", "IMM0_C90", "FRAIL_A05", "FRAIL_A1",
        "FRAIL_A2", "CAP_OFF", "CAP_FR", "IMM50_CAPOFF",
        "FRAIL_A05_CAPOFF",
    )
    # Point x arm x seed, anchor theta first, seeds innermost.
    assert cells[0].theta == pytest.approx(2.37e11)
    assert cells[0].seed == 20200205
    assert cells[9].seed == 20200214
    assert cells[150].arm_id == "FRAIL_A05_CAPOFF"
    assert cells[159].theta == pytest.approx(2.37e11)
    assert cells[160].theta == pytest.approx(1e11)
    assert cells[320].theta == pytest.approx(1e12)


def _suscept_spec(arm_id: str, theta: float = 2.37e11) -> dict:
    design = load_design(str(SUSCEPT_V1_DESIGN))
    cell = next(
        c for c in enumerate_cells(design)
        if c.arm_id == arm_id
        and c.theta == pytest.approx(theta)
        and c.seed == 20200205
    )
    return prepare_cell_run_spec(design, cell)


def test_ship_graph_arm_writes_the_declared_fractions():
    raw = _suscept_spec("IMM25_C90")
    graph = raw["config_overrides"]["ship_graph"]
    assert graph["immune_fraction"] == pytest.approx(0.25)
    assert graph["crew_immune_fraction"] == pytest.approx(0.90)
    # The baseline keeps the fit's pinned zero, not the engine default 0.2.
    base = _suscept_spec("D0_declared")
    assert base["config_overrides"]["ship_graph"][
        "immune_fraction"
    ] == pytest.approx(0.0)
    assert "crew_immune_fraction" not in base["config_overrides"]["ship_graph"]


def test_dose_response_frailty_preserves_theta_at_every_lattice_point():
    design = load_design(str(SUSCEPT_V1_DESIGN))
    for theta in design.thetas:
        cell = next(
            c for c in enumerate_cells(design)
            if c.arm_id == "FRAIL_A05"
            and c.theta == pytest.approx(theta)
            and c.seed == 20200205
        )
        dr = prepare_cell_run_spec(design, cell)[
            "pathogen_overrides"
        ]["sars_cov2_resp"]["dose_response"]
        assert dr["model"] == "beta_poisson"
        assert dr["alpha"] == pytest.approx(0.05)
        assert dr["beta"] == pytest.approx(58.0)
        # E[s] = theta: scale * alpha/(alpha+beta) == theta.
        assert dr["susceptibility_scale"] * dr["alpha"] / (
            dr["alpha"] + dr["beta"]
        ) == pytest.approx(theta)


@pytest.mark.parametrize("sg", [
    {"num_agents": 100},
    {"immune_fraction": None},
    {"immune_fraction": -0.1},
    {"immune_fraction": 1.5},
    {"crew_immune_fraction": "most"},
    [0.25],
])
def test_ship_graph_overrides_reject_out_of_grammar_values(sg):
    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {"arm_id": "B1_bad", "overrides": {"ship_graph_overrides": sg}},
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_bad"
    )
    with pytest.raises(ValueError, match="ship_graph_overrides"):
        prepare_cell_run_spec(design, cell)


@pytest.mark.parametrize("spec", [
    {"gamma": 2.0},
    {"alpha": 0.0},
    {"alpha": -1.0},
    {"alpha": "heavy"},
    {"alpha": float("nan")},
    [0.05],
])
def test_dose_response_frailty_rejects_out_of_grammar_values(spec):
    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {"arm_id": "B1_bad", "overrides": {"dose_response_frailty": spec}},
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_bad"
    )
    with pytest.raises(ValueError, match="dose_response_frailty"):
        prepare_cell_run_spec(design, cell)


def test_dose_response_frailty_needs_the_cell_theta():
    from picard_framework.covid_boarding_screen import apply_arm_overrides
    from picard_framework.covid_theta_fit import load_covid_profile

    raw = build_fit_run_spec("diamond_princess_2020", 1e10, 20200205)
    apply_boarding_axis(
        raw, infection_age_days=6.8, imports=1,
        sanitary_visit_mode="dwell_weighted",
        voyage_mode="declared", incubation_profile=load_covid_profile(),
    )
    with pytest.raises(ValueError, match="dose_response_frailty"):
        apply_arm_overrides(
            raw, {"dose_response_frailty": {"alpha": 0.05}},
            profile=load_covid_profile(),
        )


def test_a_real_immune_arm_cell_reports_the_susceptibility_echoes():
    """8-epoch smoke on an immune-split arm: the immune block echoes
    declared + resolved + realized counts, the acquisition curve and
    susceptibility draw blocks are populated, and the resolved cap flag
    is echoed. Susceptibility draws land lazily on the first challenge
    (epoch ~3), so 8 epochs replaces the full-voyage smoke."""
    from picard_framework.covid_boarding_screen import simulate_screen_cell

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_imm_split",
            "overrides": {
                "ship_graph_overrides": {
                    "immune_fraction": 0.25,
                    "crew_immune_fraction": 0.9,
                },
            },
        },
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_imm_split"
    )
    payload = simulate_screen_cell(design, cell, num_epochs=8)
    immune = payload["ship_graph_immune"]
    assert immune["declared"]["immune_fraction"] == pytest.approx(0.25)
    assert immune["declared"]["crew_immune_fraction"] == pytest.approx(0.9)
    assert immune["resolved"]["immune_ratio"] == pytest.approx(0.25)
    assert immune["resolved"]["crew_immune_ratio"] == pytest.approx(0.9)
    realized = immune["realized"]["by_role"]
    complement = immune["realized"]["complement_by_role"]
    # The pools deal without replacement: per-role realized == the
    # integer pool share of that role's complement.
    assert realized["passenger"] == int(complement["passenger"] * 0.25)
    assert realized["crew"] == int(complement["crew"] * 0.9)
    assert payload["exposure_cap_active"] is True
    curve = payload["acquisition_curve"]
    assert set(curve) == {"total_by_day", "confined_by_day"}
    assert all(day.isdigit() for day in curve["total_by_day"])
    draw = payload["susceptibility_draw"]
    assert draw["n"] > 0
    assert draw["q05"] <= draw["q50"] <= draw["q95"]


def test_a_real_frailty_arm_cell_echoes_the_rewritten_dose_response():
    """8-epoch smoke: the frailty arm's payload echoes the arm-written
    beta-Poisson block (declared alpha, recomputed scale) and the draw
    quantiles report the challenged hosts' realized susceptibilities.
    Susceptibility draws land lazily on the first challenge (epoch ~2), so
    the echo fields could read at initialize() but the draw block needs a
    few epochs."""
    from picard_framework.covid_boarding_screen import simulate_screen_cell

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_frail",
            "overrides": {"dose_response_frailty": {"alpha": 0.05}},
        },
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_frail"
    )
    payload = simulate_screen_cell(design, cell, num_epochs=8)
    echo = payload["dose_response"]
    assert echo["model"] == "beta_poisson"
    assert echo["alpha"] == pytest.approx(0.05)
    assert echo["susceptibility_scale"] == pytest.approx(
        cell.theta * (0.05 + 58.0) / 0.05
    )
    draw = payload["susceptibility_draw"]
    assert draw["n"] > 0
    # The challenged hosts' draws sit on the heavy-tailed scale.
    assert draw["mean"] <= echo["susceptibility_scale"]


# ---------------------------------------------------------------------------
# COVID-GM-RESCORE-01: the held-out Greg Mortimer re-score rides this harness.
# Its design's split_role declares the held-out side of the fixed split;
# load_design still refuses a mismatched or absent declaration.
# ---------------------------------------------------------------------------

GM_RESCORE_DESIGN_REL = Path(
    "picard_framework/runs/covid_gm_rescore_v1_design.json",
)
GM_IMPORTS3_DESIGN_REL = Path(
    "picard_framework/runs/covid_gm_rescore_v1_imports3_design.json",
)
_TMP_DESIGN_REL = Path(
    "picard_framework/runs/_gm_rescore_split_role_test.json",
)
_DELETE = object()


def _gm_design_raw() -> dict:
    import json
    path = REPO_ROOT / GM_RESCORE_DESIGN_REL
    return json.loads(path.read_text(encoding="utf-8"))


def _load_mutated_gm(**changes) -> BoardingScreenDesign:
    """Load a copy of the GM design with one field mutated, from disk."""
    import json
    raw = _gm_design_raw()
    for key, value in changes.items():
        if value is _DELETE:
            raw.pop(key, None)
        else:
            raw[key] = value
    path = REPO_ROOT / _TMP_DESIGN_REL
    try:
        path.write_text(json.dumps(raw), encoding="utf-8")
        return load_design(str(_TMP_DESIGN_REL))
    finally:
        path.unlink(missing_ok=True)


def test_gm_rescore_design_is_the_declared_300_cell_scoring():
    design = load_design(str(GM_RESCORE_DESIGN_REL))
    assert design.scenario_id == "greg_mortimer_2020"
    assert design.split_role == "held_out"
    assert design.split_day == 20
    assert design.turn_day == 8
    cells = enumerate_cells(design)
    assert len(cells) == 300
    # Theta-outer, arm-major, seed-inner: the canary row is theta 2.37e11
    # x hygiene_cycle at indices 100..149.
    assert cells[100].theta == pytest.approx(2.37e11)
    assert cells[100].arm_id == "hygiene_cycle"
    assert cells[100].seed == 20200205
    assert cells[149].seed == 20200254
    assert cells[150].arm_id == "spike_decay"
    assert cells[150].seed == 20200205


def test_imports3_diagnostic_design_is_50_labelled_cells():
    design = load_design(str(GM_IMPORTS3_DESIGN_REL))
    assert design.imports == (3,)
    cells = enumerate_cells(design)
    assert len(cells) == 50
    assert all(c.imports == 3 for c in cells)
    assert {c.arm_id for c in cells} == {"hygiene_cycle"}


def test_split_role_mismatch_against_the_fixed_split_refuses():
    # diamond_princess_2020 is the fit hull: a held_out declaration on it
    # must refuse, as must a training declaration on greg_mortimer_2020.
    with pytest.raises(ValueError, match="split_role"):
        _load_mutated_gm(scenario_id="diamond_princess_2020")
    with pytest.raises(ValueError, match="split_role"):
        _load_mutated_gm(split_role="training")


def test_absent_split_role_keeps_the_fit_gate():
    # Legacy designs declare no role: the held-out hull must still refuse.
    with pytest.raises(ValueError):
        _load_mutated_gm(split_role=_DELETE)


def test_gm_cell_echoes_the_declared_hand_mode_and_seed_ring():
    design = load_design(str(GM_RESCORE_DESIGN_REL))
    cells = enumerate_cells(design)
    base = next(c for c in cells if c.arm_id == "hygiene_cycle")
    arm = next(c for c in cells if c.arm_id == "spike_decay")
    base_payload = echo_screen_cell(design, base)
    arm_payload = echo_screen_cell(design, arm)
    assert (
        base_payload["delivery"]["hand_reservoir_mode"] == "hygiene_cycle"
    )
    assert arm_payload["delivery"]["hand_reservoir_mode"] == "spike_decay"
    for payload in (base_payload, arm_payload):
        spec = payload["seed_ring"]["seed_spec"]
        assert spec["count"] == 1
        assert spec["infection_age_days"] == pytest.approx(0.0)
        assert spec["role"] == "passenger"
        assert payload["aboard_total"] == 223


# ── FRAILTY-V1: continuous per-host frailty on the infection hazard ────────

FRAILTY_V1_DESIGN = (
    REPO_ROOT
    / "picard_framework"
    / "runs"
    / "covid_frailty_v1_design.json"
)


def test_frailty_v1_design_is_the_declared_140_cell_canary():
    design = load_design(str(FRAILTY_V1_DESIGN))
    cells = enumerate_cells(design)
    assert len(cells) == 140
    assert design.arm_ids == (
        "D0_declared", "FRAIL_INERT", "FRAIL_G05", "FRAIL_G10",
        "FRAIL_G20", "FRAIL_L10", "FRAIL_L20",
    )
    # One anchor point, arm-major then seed-innermost.
    assert all(c.theta == pytest.approx(2.37e11) for c in cells)
    assert cells[0].arm_id == "D0_declared"
    assert cells[0].seed == 20200205
    assert cells[19].seed == 20200224
    assert cells[20].arm_id == "FRAIL_INERT"
    assert cells[139].arm_id == "FRAIL_L20"
    assert len({c.key for c in cells}) == 140


def test_hazard_frailty_writes_the_declared_block():
    design = _arm_design([
        {"arm_id": "B0_declared", "overrides": {}},
        {
            "arm_id": "B1_frail",
            "overrides": {
                "hazard_frailty": {"distribution": "gamma", "cv": 1.0},
            },
        },
    ])
    cells = enumerate_cells(design)
    armed = next(c for c in cells if c.arm_id == "B1_frail")
    raw = prepare_cell_run_spec(design, armed)
    dr = raw["pathogen_overrides"]["sars_cov2_resp"]["dose_response"]
    assert dr["frailty"] == {
        "enabled": True, "distribution": "gamma", "cv": 1.0,
    }
    # The theta-preserved beta block is untouched by the frailty key.
    assert dr["susceptibility_scale"] * dr["alpha"] / (
        dr["alpha"] + dr["beta"]
    ) == pytest.approx(armed.theta)
    base = next(c for c in cells if c.arm_id == "B0_declared")
    dr0 = prepare_cell_run_spec(design, base)[
        "pathogen_overrides"
    ]["sars_cov2_resp"]["dose_response"]
    assert "frailty" not in dr0


@pytest.mark.parametrize("spec", [
    {"distribution": "weibull", "cv": 1.0},
    {"distribution": "gamma"},
    {"cv": 1.0},
    {"distribution": "gamma", "cv": -1.0},
    {"distribution": "gamma", "cv": "high"},
    {"distribution": "gamma", "cv": True},
    {"distribution": "gamma", "cv": float("nan")},
    {"distribution": "gamma", "cv": 1.0, "shape": 2.0},
    [1.0],
])
def test_hazard_frailty_rejects_out_of_grammar_values(spec):
    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {"arm_id": "B1_bad", "overrides": {"hazard_frailty": spec}},
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_bad"
    )
    with pytest.raises(ValueError, match="hazard_frailty"):
        prepare_cell_run_spec(design, cell)


def test_hazard_frailty_cell_reports_the_draw_echoes():
    """8-epoch smoke on an armed arm: the resolved frailty block echoes on
    dose_response, frailty_draw quantiles report the challenged hosts'
    realized multipliers at declared cv, and the draw set is exactly the
    challenged set (same n as the susceptibility draw)."""
    from picard_framework.covid_boarding_screen import simulate_screen_cell

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_frail",
            "overrides": {
                "hazard_frailty": {"distribution": "gamma", "cv": 1.0},
            },
        },
    ])
    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B1_frail"
    )
    payload = simulate_screen_cell(design, cell, num_epochs=8)
    echo = payload["dose_response"]["frailty"]
    assert echo == {"enabled": True, "distribution": "gamma", "cv": 1.0}
    draw = payload["frailty_draw"]
    assert draw["n"] > 0
    # The same challenged hosts carry both draws.
    assert draw["n"] == payload["susceptibility_draw"]["n"]
    assert draw["q05"] <= draw["q50"] <= draw["q95"]
    # Mean pinned 1.0 by construction; a smoke-sized draw is loose but
    # cannot sit near zero or explode.
    assert 0.2 <= draw["mean"] <= 5.0


def test_hazard_frailty_inert_corner_is_bit_identical_to_baseline():
    """The cv 0 corner must reproduce the baseline exactly: frailty fires,
    every challenged host carries a recorded 1.0, and the shared stream is
    untouched so the whole payload — outcomes and draw quantiles alike —
    is identical between B0 and the inert arm at the same seed."""
    from picard_framework.covid_boarding_screen import simulate_screen_cell

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_inert",
            "overrides": {
                "hazard_frailty": {"distribution": "gamma", "cv": 0.0},
            },
        },
    ])
    cells = {
        c.arm_id: c for c in enumerate_cells(design) if c.seed == 20200205
    }
    base = simulate_screen_cell(design, cells["B0_baseline"], num_epochs=8)
    inert = simulate_screen_cell(design, cells["B1_inert"], num_epochs=8)
    assert inert["frailty_draw"]["n"] > 0
    # Exact 1.0 — the inert corner writes float(1.0), never a draw.
    assert inert["frailty_draw"]["mean"] == pytest.approx(
        1.0, rel=0.0, abs=0.0,
    )
    assert inert["frailty_draw"]["q05"] == pytest.approx(
        1.0, rel=0.0, abs=0.0,
    )
    assert inert["frailty_draw"]["q95"] == pytest.approx(
        1.0, rel=0.0, abs=0.0,
    )
    assert base["frailty_draw"] == {"n": 0}
    for key in (
        "infections_total", "aboard_total", "observables",
        "onset_curve", "acquisition_curve", "susceptibility_draw",
    ):
        assert inert[key] == base[key], key


def test_hazard_frailty_draws_are_deterministic_per_seed():
    """Same seed, same armed corner -> identical frailty draws (the
    dedicated stream keys on the run seed's own seed material)."""
    from picard_framework.covid_boarding_screen import simulate_screen_cell

    design = _arm_design([
        {"arm_id": "B0_baseline", "overrides": {}},
        {
            "arm_id": "B1_frail",
            "overrides": {
                "hazard_frailty": {
                    "distribution": "lognormal", "cv": 2.0,
                },
            },
        },
    ])
    cell = next(
        c for c in enumerate_cells(design)
        if c.arm_id == "B1_frail" and c.seed == 20200205
    )
    first = simulate_screen_cell(design, cell, num_epochs=8)
    second = simulate_screen_cell(design, cell, num_epochs=8)
    assert first["frailty_draw"] == second["frailty_draw"]
    assert first["infections_total"] == second["infections_total"]

