"""The shipped norwalk_gi boards (#54 / Track-C C1).

The shipped config and profile resolve to a boarding plan that owns
norwalk_gi; the campaign's index-case axis is the boarding grid for that
pathogen and the fiat count for every other; a design whose variable is the
count itself must say so and then withdraws the block. Sensitivity and
invariants rather than goldens: swept coordinates move the run's initiation
config and its id, unswept ones stay at the register's midpoints.
"""

from __future__ import annotations

from itertools import product

import pytest

from crusher_labs import load_config
from engines.initiation import (
    initiation_owned_pathogens,
    resolve_initiation_plan,
)
from orchestrator_init import load_pathogen_profiles
from picard_framework.analysis.parse_run_id import (
    drawn_boarding_introductions,
    resolve_initial_infected,
)
from picard_framework.runs.mega_cruise_campaign import boarding_axis
from picard_framework.runs.mega_cruise_campaign.boarding_axis import (
    IndexCaseAxis,
)
from picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian import (
    index_axis_size,
)

NORO_ONLY = {"remove": ["sars_cov2_resp"]}


def test_shipped_config_boards_norwalk_gi_and_owns_it() -> None:
    cfg = load_config()
    profiles = load_pathogen_profiles(cfg)
    assert profiles["norwalk_gi"]["initial_infected"] is None
    plan = resolve_initiation_plan(cfg, profiles)
    assert not plan.legacy
    assert initiation_owned_pathogens(plan) == frozenset({"norwalk_gi"})
    (spec,) = plan.boarding
    assert spec.pathogen_id == "norwalk_gi"
    assert spec.passenger_prevalence == pytest.approx(0.0325)
    assert spec.crew_prevalence == pytest.approx(0.0185)
    assert spec.never_symptomatic_fraction == pytest.approx(0.29)
    assert spec.presymptomatic_share_of_presenting == pytest.approx(0.04)


def test_shipped_profile_refuses_a_fiat_count_over_the_boarding_block() -> None:
    cfg = load_config()
    profiles = load_pathogen_profiles(cfg)
    profiles["norwalk_gi"]["initial_infected"] = 3
    with pytest.raises(ValueError, match="initial_infected"):
        resolve_initiation_plan(cfg, profiles)


def test_unowned_pathogen_keeps_its_fiat_count() -> None:
    axis = IndexCaseAxis.for_tier(
        {"initial_infected": [1, 5]}, "sars_cov2_resp",
    )
    assert not axis.boarding
    assert axis.points == (1, 5)
    assert axis.tags(5) == ["init5"]
    assert axis.factors(5) == {"n_init": 5}
    assert axis.pathogen_overrides({}, 5) == {
        "sars_cov2_resp": {"initial_infected": 5},
    }


def test_owned_pathogen_refuses_a_count_axis_unless_declared_fiat() -> None:
    with pytest.raises(ValueError, match="fiat_index_case"):
        IndexCaseAxis.for_tier({"initial_infected_values": [1, 2]}, "norwalk_gi")
    fiat = IndexCaseAxis.for_tier(
        {"initial_infected_values": [1, 2], "fiat_index_case": True}, "norwalk_gi",
    )
    assert not fiat.boarding
    assert fiat.points == (1, 2)
    assert fiat.tags(2) == ["init2"]
    # A fiat run withdraws the shipped block rather than boarding as well.
    assert boarding_axis.initiation_override(
        "active_profiles", NORO_ONLY, fiat.factors(2),
    ) == {"initiation": None}
    assert boarding_axis.recorded_factors(
        "active_profiles", NORO_ONLY, fiat.factors(2),
    ) == {}


def test_unswept_owned_pathogen_boards_at_register_midpoints() -> None:
    axis = IndexCaseAxis.for_tier({}, "norwalk_gi")
    assert axis.boarding
    (point,) = axis.points
    assert axis.tags(point) == []
    assert axis.factors(point) == {
        "never_symptomatic_fraction": pytest.approx(0.29),
        "presymptomatic_share_of_presenting": pytest.approx(0.04),
        "boarding_passenger_prevalence": pytest.approx(0.0325),
        "boarding_crew_prevalence": pytest.approx(0.0185),
    }
    assert axis.pathogen_overrides({}, point) == {}


def test_never_symptomatic_regimes_are_separate_and_not_pooled() -> None:
    adult = boarding_axis.never_symptomatic_values(
        {"never_symptomatic_regime": "adult_challenge"},
    )
    community = boarding_axis.never_symptomatic_values(
        {"never_symptomatic_regime": "community_cohort"},
    )
    assert adult == [0.22, 0.29, 0.36]
    assert community == [0.59, 0.635, 0.68]
    assert max(adult) < min(community)
    with pytest.raises(ValueError, match="names no regime"):
        boarding_axis.never_symptomatic_values(
            {"never_symptomatic_regime": "pooled"},
        )


def test_swept_coordinates_move_the_initiation_override_and_the_run_id() -> None:
    tier = {
        "never_symptomatic_regime": "adult_challenge",
        "presymptomatic_shares": [0.02, 0.04],
        "boarding_prevalence_points": [
            {"passenger": 0.025, "crew": 0.007},
            {"passenger": 0.040, "crew": 0.030},
        ],
    }
    axis = IndexCaseAxis.for_tier(tier, "norwalk_gi")
    assert len(axis.points) == 3 * 2 * 2
    ids = {"_".join(axis.tags(p)) for p in axis.points}
    assert len(ids) == len(axis.points)
    assert "nsf22_psp2_bp25c7" in ids
    assert "nsf36_psp4_bp40c30" in ids
    seen: set[tuple[float, float, float, float]] = set()
    for point in axis.points:
        block = boarding_axis.initiation_override(
            "active_profiles", NORO_ONLY, axis.factors(point),
        )["initiation"]["boarding"]
        assert block["enabled"] is True
        noro = block["norwalk_gi"]
        coords = (
            noro["state_split"]["never_symptomatic_fraction"],
            noro["state_split"]["presymptomatic_share_of_presenting"],
            noro["prevalence"]["passenger"],
            noro["prevalence"]["crew"],
        )
        assert coords == (
            point.never_symptomatic_fraction,
            point.presymptomatic_share,
            point.passenger_prevalence,
            point.crew_prevalence,
        )
        seen.add(coords)
    assert len(seen) == len(axis.points)


def test_run_id_tags_refuse_points_that_collide() -> None:
    with pytest.raises(ValueError, match="share a run id"):
        boarding_axis.never_symptomatic_values(
            {"never_symptomatic_fractions": [0.29, 0.2900001]},
        )


def test_override_is_withdrawn_when_the_run_loads_no_owned_pathogen() -> None:
    assert boarding_axis.initiation_override(
        "active_profiles", {"remove": ["norwalk_gi"]},
    ) == {"initiation": None}
    assert boarding_axis.recorded_factors(
        "active_profiles", {"remove": ["norwalk_gi"]},
    ) == {}
    assert boarding_axis.recorded_factors("active_profiles", NORO_ONLY) == {
        "never_symptomatic_fraction": pytest.approx(0.29),
        "presymptomatic_share_of_presenting": pytest.approx(0.04),
        "boarding_passenger_prevalence": pytest.approx(0.0325),
        "boarding_crew_prevalence": pytest.approx(0.0185),
    }


def test_mixed_tier_gives_each_pathogen_its_own_axis() -> None:
    manifest = {
        "pathogen_configs": {
            "norovirus": {"pathogen_id": "norwalk_gi"},
            "sarscov2": {"pathogen_id": "sars_cov2_resp"},
        },
    }
    tier = {
        "pathogens": ["norovirus", "sarscov2"],
        "initial_infected": [1, 2, 5],
        "never_symptomatic_regime": "adult_challenge",
    }
    noro = boarding_axis.axis_for_mixed_tier(tier, "norwalk_gi")
    covid = boarding_axis.axis_for_mixed_tier(tier, "sars_cov2_resp")
    assert noro.boarding
    assert not covid.boarding
    assert len(noro.points) == len(covid.points) == 3
    assert index_axis_size(manifest, tier) == 3
    tier["initial_infected"] = [1, 2]
    with pytest.raises(ValueError, match="disagree"):
        index_axis_size(manifest, tier)


def test_cartesian_index_axis_grades_with_the_boarding_grid() -> None:
    manifest = {"pathogen_configs": {"norovirus": {"pathogen_id": "norwalk_gi"}}}
    sizes = []
    for n_nsf, n_prev in product((1, 3), (1, 2)):
        tier = {
            "pathogen": "norovirus",
            "never_symptomatic_fractions": [0.22, 0.29, 0.36][:n_nsf],
            "boarding_prevalence_points": [[0.025, 0.007], [0.04, 0.03]][:n_prev],
        }
        sizes.append(index_axis_size(manifest, tier))
    assert sizes == [1, 2, 3, 6]


def test_analysis_reads_k_from_the_realised_boarding_draw() -> None:
    initiation = {
        "mode": "boarding",
        "boarding": {"norwalk_gi": {"drawn_by_role": {"passenger": 7, "crew": 2}}},
    }
    assert drawn_boarding_introductions(initiation) == 9
    assert drawn_boarding_introductions({"mode": "legacy"}) is None
    assert resolve_initial_infected(
        parameters={"n_init": 3}, run_id="x_init3_s1", initiation=initiation,
    ) == 9
    assert resolve_initial_infected(
        parameters={"n_init": 3}, run_id="x_init3_s1", initiation={},
    ) == 3
