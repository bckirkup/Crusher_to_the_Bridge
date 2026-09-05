"""The shipped pathogens board (#54 / Track-C C1).

The shipped config and profiles resolve to a boarding plan that owns every
loaded profile carrying a ``boarding`` block; the campaign's index-case axis
is the boarding grid for those and the fiat count for the rest (legionella,
whose reservoir is the ship); a design whose variable is the count itself
must say so and then withdraws the block. Sensitivity and invariants rather
than goldens: swept coordinates move the run's initiation config and its id,
unswept ones stay at the profile's own coordinates.
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

NORO_ONLY = {"remove": ["sars_cov2_resp", "influenza_a"]}
UNOWNED = "legionella_pneumophila"


def test_shipped_config_boards_every_loaded_profile_with_a_block() -> None:
    cfg = load_config()
    profiles = load_pathogen_profiles(cfg)
    owned = {pid for pid, p in profiles.items() if "boarding" in p}
    assert "norwalk_gi" in owned
    for pid in owned:
        assert profiles[pid]["initial_infected"] is None, pid
    plan = resolve_initiation_plan(cfg, profiles)
    assert not plan.legacy
    assert initiation_owned_pathogens(plan) == frozenset(owned)
    assert boarding_axis.boarding_pathogen_ids() >= owned
    assert UNOWNED not in boarding_axis.boarding_pathogen_ids()
    (spec,) = [s for s in plan.boarding if s.pathogen_id == "norwalk_gi"]
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
    axis = IndexCaseAxis.for_tier({"initial_infected": [1, 5]}, UNOWNED)
    assert not axis.boarding
    assert axis.points == (1, 5)
    assert axis.tags(5) == ["init5"]
    assert axis.factors(5) == {"n_init": 5}
    assert axis.pathogen_overrides({}, 5) == {
        UNOWNED: {"initial_infected": 5},
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
        "boarding_pathogen": "norwalk_gi",
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


def test_swept_coordinates_reach_only_the_studied_pathogen() -> None:
    factors = boarding_axis.point_factors(never_symptomatic_fraction=0.36)
    block = boarding_axis.initiation_override(
        "active_profiles", None,
        {**factors, boarding_axis.FACTOR_SWEPT_PATHOGEN: "norwalk_gi"},
    )["initiation"]["boarding"]
    assert set(block) == {"enabled", "norwalk_gi"}
    # Unnamed: the state split is a property of every independent draw.
    block = boarding_axis.initiation_override(
        "active_profiles", None, factors,
    )["initiation"]["boarding"]
    assert "norwalk_gi" in block
    assert "influenza_a" in block
    for pid, coords in block.items():
        if pid != "enabled":
            assert coords["state_split"]["never_symptomatic_fraction"] == 0.36


def test_party_axis_moves_the_party_block_and_the_run_id() -> None:
    tier = {
        "never_symptomatic_fractions": [0.05],
        "boarding_party_points": [[0.002, 3], {"probability": 0.01, "size": 5}],
    }
    axis = IndexCaseAxis.for_tier(tier, "ebola_virus")
    assert boarding_axis.boarding_mode("ebola_virus") == "party"
    assert axis.boarding
    assert len(axis.points) == 2
    tags = {"_".join(axis.tags(p)) for p in axis.points}
    assert tags == {"nsf5_pty2n3", "nsf5_pty10n5"}
    for point in axis.points:
        block = boarding_axis.initiation_override(
            "edison_10pathogen_profiles", None, axis.factors(point),
        )["initiation"]["boarding"]["ebola_virus"]
        assert "prevalence" not in block
        assert block["party"] == {
            "probability": point.party[0], "size": point.party[1],
        }
    with pytest.raises(ValueError, match="share a run id"):
        boarding_axis.party_points(
            {"boarding_party_points": [[0.002, 3], [0.002001, 3]]},
        )


def test_run_id_tags_refuse_points_that_collide() -> None:
    with pytest.raises(ValueError, match="share a run id"):
        boarding_axis.never_symptomatic_values(
            {"never_symptomatic_fractions": [0.29, 0.2900001]},
        )


def test_override_is_withdrawn_when_the_run_loads_no_owned_pathogen() -> None:
    none_owned = {"remove": ["norwalk_gi", "sars_cov2_resp", "influenza_a"]}
    assert boarding_axis.initiation_override(
        "active_profiles", none_owned,
    ) == {"initiation": None}
    assert boarding_axis.recorded_factors("active_profiles", none_owned) == {}
    assert boarding_axis.recorded_factors("active_profiles", NORO_ONLY) == {
        "never_symptomatic_fraction": pytest.approx(0.29),
        "presymptomatic_share_of_presenting": pytest.approx(0.04),
        "boarding_passenger_prevalence": pytest.approx(0.0325),
        "boarding_crew_prevalence": pytest.approx(0.0185),
    }


def test_unswept_coordinates_stay_at_each_profile_s_own() -> None:
    """A sweep of one coordinate must not restate the others for everyone.

    The whole point of profile-carried defaults: campylobacter's measured
    asymptomatic share is not norovirus's, so a prevalence sweep may not
    write a state split, and a tier that sweeps nothing writes no block.
    """
    over = boarding_axis.initiation_override(
        "active_profiles", None,
        boarding_axis.point_factors(
            never_symptomatic_fraction=0.36,
        ) | {boarding_axis.FACTOR_SWEPT_PATHOGEN: "norwalk_gi"},
    )["initiation"]["boarding"]
    assert set(over) == {"enabled", "norwalk_gi"}
    prevalence_only = boarding_axis.initiation_override(
        "edison_10pathogen_profiles", None,
        {
            boarding_axis.FACTOR_SWEPT_PATHOGEN: "campylobacter_jejuni",
            boarding_axis.FACTOR_PASSENGER_PREVALENCE: 0.05,
            boarding_axis.FACTOR_CREW_PREVALENCE: 0.01,
        },
    )["initiation"]["boarding"]["campylobacter_jejuni"]
    assert "state_split" not in prevalence_only
    assert prevalence_only["prevalence"] == {"passenger": 0.05, "crew": 0.01}
    unswept = boarding_axis.initiation_override(
        "edison_10pathogen_profiles", None, {},
    )["initiation"]["boarding"]
    assert unswept == {"enabled": True}


def test_tier_wide_party_point_keeps_each_pathogen_s_own_size() -> None:
    """A conditional-import tier states the probability, not the party size.

    Ebola's party and measles' are different sizes, so a tier that studies
    the dynamics given an import moves only the per-voyage probability and
    each profile keeps the size it states.
    """
    tier = {"boarding_party_points": [{"probability": 1.0}]}
    factors = boarding_axis.tier_party_factors(tier)
    assert factors == {"boarding_party_probability": 1.0}
    for pathogen_id, size in (("ebola_virus", 3), ("measles_virus", 2)):
        block = boarding_axis.initiation_override(
            "edison_10pathogen_profiles", None,
            {**factors, boarding_axis.FACTOR_SWEPT_PATHOGEN: pathogen_id},
        )["initiation"]["boarding"][pathogen_id]
        assert block["party"] == {"probability": 1.0}
        assert boarding_axis.recorded_factors(
            "edison_10pathogen_profiles", None,
            {**factors, boarding_axis.FACTOR_SWEPT_PATHOGEN: pathogen_id},
        )["boarding_party_size"] == size
    # More than one point is the axis's to stamp, run id by run id.
    assert boarding_axis.tier_party_factors(
        {"boarding_party_points": [[0.002, 3], [0.01, 5]]},
    ) == {}


def test_recorded_factors_are_the_pathogen_s_effective_coordinates() -> None:
    recorded = boarding_axis.recorded_factors(
        "edison_10pathogen_profiles", None,
        {boarding_axis.FACTOR_SWEPT_PATHOGEN: "clostridioides_difficile"},
    )
    assert recorded["boarding_passenger_prevalence"] == pytest.approx(0.076)
    assert recorded["never_symptomatic_fraction"] == pytest.approx(0.90)
    assert "boarding_party_probability" not in recorded
    party = boarding_axis.recorded_factors(
        "edison_10pathogen_profiles", None,
        {boarding_axis.FACTOR_SWEPT_PATHOGEN: "andes_hantavirus"},
    )
    assert "boarding_passenger_prevalence" not in party
    assert party["boarding_party_size"] == 3


def test_mixed_tier_gives_each_pathogen_its_own_axis() -> None:
    manifest = {
        "pathogen_configs": {
            "norovirus": {"pathogen_id": "norwalk_gi"},
            "legionella": {"pathogen_id": UNOWNED},
        },
    }
    tier = {
        "pathogens": ["norovirus", "legionella"],
        "initial_infected": [1, 2, 5],
        "never_symptomatic_regime": "adult_challenge",
    }
    noro = boarding_axis.axis_for_mixed_tier(tier, "norwalk_gi")
    legion = boarding_axis.axis_for_mixed_tier(tier, UNOWNED)
    assert noro.boarding
    assert not legion.boarding
    assert len(noro.points) == len(legion.points) == 3
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
