"""The droplet route's continuous emission share is resolved per profile.

An ``emesis_conditioned`` arm emits to air only per vomiting event: the record
supports no continuous respiratory emission for norovirus (tranche 36 §4), and
``pathogen_profiles.schema.json`` forbids ``airborne_emission_fraction`` on such
a profile for that reason. The route applied ``DROPLET_AEROSOL_FRACTION`` to
every arm regardless, so the deletion these tests pin is that an emesis arm now
receives a zero continuous share through *every* droplet call site — the room
pool, the cabin-mate addback and the near field.

The continuous arms are deliberately untouched: whether they should read their
own declared ``airborne_emission_fraction`` instead of the uniform constant is a
separate open item, and the mode-invariance tests here guard that it stays
separate. No golden doses: every expectation is a relation between runs of the
same code, a zero, or an ordering.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import (
    DEFAULT_DROPLET_EMISSION_MODE,
    DROPLET_AEROSOL_FRACTION,
    DROPLET_EMISSION_MODES,
    TransmissionCore,
)

ZONE = "PC_D6_P_F"
VOLUME = 1200.0

EMESIS = {"airborne_emission_mode": "emesis_conditioned"}
CONTINUOUS = {"airborne_emission_mode": "continuous_fraction"}


def _agent(aid: int, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid, role="passenger", immune=False,
        home_zone=ZONE, dining_zone="MainDining",
        work_zone="Lounge", free_zone="Lounge",
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = ZONE
    return a


def _core(
    mode: str | None = None,
    profile: dict | None = None,
) -> TransmissionCore:
    tx: dict = {} if mode is None else {"droplet_emission_mode": mode}
    core = TransmissionCore(
        rng=np.random.default_rng(42),
        zone_volumes={ZONE: VOLUME},
        zone_types={ZONE: "Cabin_Corridor"},
        cfg={"transmission": tx},
        pathogen_profiles={"_default": profile} if profile is not None else None,
    )
    core.initialize_zones([ZONE])
    return core


def _run(
    profile: dict | None,
    mode: str | None = None,
    *,
    cabin_mates: bool = False,
    quarantined_ids: set[int] | None = None,
) -> tuple[float, float]:
    """Droplet dose on the target, and the zone's aerosol pool."""
    shedder, target = _agent(1, infected=True), _agent(2)
    if cabin_mates:
        shedder.cabin_mate_ids = frozenset({2})
        target.cabin_mate_ids = frozenset({1})
    core = _core(mode, profile=profile)
    matrix, _ = core.execute_transmission(
        epoch=1, agents=[shedder, target],
        zone_pathogen_mass={ZONE: 0.0},
        quarantined_ids=quarantined_ids or set(),
    )
    doses = [e["dose"] for e in matrix.droplet_exposures]
    return (doses[0] if doses else 0.0), core.aerosol_pools.get(ZONE, 0.0)


class TestDeclaration:
    def test_the_default_is_the_profile_conditioned_mode(self) -> None:
        assert DEFAULT_DROPLET_EMISSION_MODE == "profile_conditioned"
        assert _core().droplet_emission_mode == "profile_conditioned"

    def test_both_arms_are_selectable(self) -> None:
        assert DROPLET_EMISSION_MODES == {"profile_conditioned", "shipped_uniform"}
        for mode in sorted(DROPLET_EMISSION_MODES):
            assert _core(mode).droplet_emission_mode == mode

    def test_an_unknown_mode_falls_back_to_the_default(self) -> None:
        assert _core("not_a_mode").droplet_emission_mode == DEFAULT_DROPLET_EMISSION_MODE


class TestTheResolvedFraction:
    def test_an_emesis_conditioned_arm_has_no_continuous_share(self) -> None:
        assert _core()._droplet_emission_fraction(EMESIS) == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "profile",
        [CONTINUOUS, {"airborne_emission_mode": "respiratory"}, {}, None],
    )
    def test_a_continuous_arm_keeps_the_uniform_share(self, profile: dict | None) -> None:
        assert _core()._droplet_emission_fraction(profile) == pytest.approx(
            DROPLET_AEROSOL_FRACTION,
        )

    @pytest.mark.parametrize("profile", [EMESIS, CONTINUOUS, {}, None])
    def test_the_shipped_arm_is_uniform_over_every_profile(
        self, profile: dict | None,
    ) -> None:
        assert _core("shipped_uniform")._droplet_emission_fraction(
            profile,
        ) == pytest.approx(DROPLET_AEROSOL_FRACTION)


class TestTheRouteIsSilencedForAnEmesisArm:
    def test_no_dose_and_no_room_pool(self) -> None:
        dose, pool = _run(EMESIS)
        assert dose == pytest.approx(0.0)
        assert pool == pytest.approx(0.0)

    def test_a_continuous_arm_still_doses_and_fills_the_pool(self) -> None:
        dose, pool = _run(CONTINUOUS)
        assert dose > 0.0
        assert pool > 0.0

    def test_the_cabin_mate_addback_is_silenced_too(self) -> None:
        """The addback restores withheld emission, so it is its own call site.

        A confined shedder's cabin mate shares the cabin and is dosed through
        the addback rather than the attenuated pool. With a zero share there is
        nothing to restore, so this pins the second call site independently of
        the room pool.
        """
        dose, _ = _run(EMESIS, cabin_mates=True, quarantined_ids={1})
        assert dose == pytest.approx(0.0)
        continuous, _ = _run(CONTINUOUS, cabin_mates=True, quarantined_ids={1})
        assert continuous > 0.0

    def test_the_shipped_arm_recovers_the_deleted_dose(self) -> None:
        deleted, deleted_pool = _run(EMESIS)
        shipped, shipped_pool = _run(EMESIS, mode="shipped_uniform")
        assert shipped > deleted == pytest.approx(0.0)
        assert shipped_pool > deleted_pool == pytest.approx(0.0)


class TestTheContinuousArmsAreUntouched:
    """The COVID/influenza inconsistency stays separately measurable."""

    @pytest.mark.parametrize("profile", [CONTINUOUS, {}, None])
    def test_a_continuous_arm_reads_the_same_under_either_mode(
        self, profile: dict | None,
    ) -> None:
        conditioned = _run(profile, mode="profile_conditioned")
        shipped = _run(profile, mode="shipped_uniform")
        assert conditioned == pytest.approx(shipped)

    def test_the_route_still_ignores_a_declared_emission_fraction(self) -> None:
        """Pinned as a known gap, not an endorsement: the droplet route does
        not read ``airborne_emission_fraction``. Deleting this test is part of
        the separate change that makes it read the profile."""
        declared = dict(CONTINUOUS, airborne_emission_fraction=0.76)
        assert _core()._droplet_emission_fraction(declared) == pytest.approx(
            DROPLET_AEROSOL_FRACTION,
        )
