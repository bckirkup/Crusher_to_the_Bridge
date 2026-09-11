"""DIRECT-HAND-01: the direct route composes through the donor's hand.

The route used to hand each partner the donor's whole-body faecal emission.
It now moves a measured fraction of the donor's *hand* load, which is finite,
shared between that epoch's partners, and reaches the mouth through the same
hand-to-mouth process the fomite chain uses.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    HAND_TO_HAND_TRANSFER_RANGE,
    TransmissionCore,
)

PATHOGEN = "test_pathogen"
ZONE = "Public_Lounge"


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
    }
    profile.update(overrides)
    return profile


def _agent(
    agent_id: int = 1,
    *,
    infected: bool = False,
    hand_load: float | None = None,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    if hand_load is not None:
        agent.hand_load_by_pathogen[PATHOGEN] = hand_load
    return agent


def _core(*, seed: int = 7, profile: dict | None = None) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={ZONE: "Free"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": {"contact_mode": "per_partner_contact"}},
    )
    core.initialize_zones([ZONE])
    return core


def _one_epoch(
    core: TransmissionCore,
    target: KorkinAgent,
    donors: list[KorkinAgent],
    *,
    shedding: float = 1.0e11,
) -> tuple[float, list[tuple[KorkinAgent, float]]]:
    """One composed contact set: the same donor list, one recipient."""
    sampled = [(donor, shedding) for donor in donors]
    return core._per_partner_contact_dose(target, sampled, False, PATHOGEN, 0)


class TestInvariants:
    """Mass cannot be created, and a finite reservoir stays finite."""

    def test_total_transferred_never_exceeds_the_donor_reservoir(self) -> None:
        start = 1.0e6
        for n_partners in (1, 4, 16, 64):
            core = _core(seed=100 + n_partners)
            donor = _agent(1, infected=True, hand_load=start)
            total = 0.0
            for partner_id in range(n_partners):
                _dose, moved = _one_epoch(
                    core, _agent(200 + partner_id), [donor],
                )
                total += sum(amount for _, amount in moved)
            assert total <= start
            assert donor.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
                start - total, rel=1e-12, abs=1e-9,
            )

    def test_the_dose_is_bounded_by_what_reached_the_recipient(self) -> None:
        core = _core(seed=11)
        for _ in range(200):
            donor = _agent(1, infected=True, hand_load=1.0e6)
            target = _agent(2)
            dose, moved = _one_epoch(core, target, [donor])
            acquired = sum(amount for _, amount in moved)
            assert np.isfinite(dose)
            assert dose >= 0.0
            assert dose <= acquired + 1e-9

    def test_an_empty_reservoir_is_a_hard_zero(self) -> None:
        core = _core(seed=5)
        absent = _agent(1, infected=True)
        assert PATHOGEN not in absent.hand_load_by_pathogen
        dose, moved = _one_epoch(core, _agent(2), [absent])
        assert dose == pytest.approx(0.0, abs=0.0)
        assert moved == []

        zeroed = _agent(3, infected=True, hand_load=0.0)
        dose, moved = _one_epoch(core, _agent(4), [zeroed])
        assert dose == pytest.approx(0.0, abs=0.0)
        assert moved == []

    def test_a_spent_donor_is_recorded_in_no_attribution(self) -> None:
        core = _core(seed=6)
        carrying = _agent(1, infected=True, hand_load=1.0e6)
        spent = _agent(2, infected=True, hand_load=0.0)
        _dose, moved = _one_epoch(core, _agent(3), [carrying, spent])
        assert [donor.agent_id for donor, _ in moved] == [1]

    def test_the_realised_fraction_stays_inside_the_frozen_interval(
        self,
    ) -> None:
        core = _core(seed=19)
        low, high = HAND_TO_HAND_TRANSFER_RANGE
        fractions = []
        for _ in range(1000):
            donor = _agent(1, infected=True, hand_load=1.0e6)
            _dose, moved = _one_epoch(core, _agent(2), [donor])
            assert len(moved) == 1
            fractions.append(moved[0][1] / 1.0e6)
        assert min(fractions) >= low
        assert max(fractions) <= high
        # A uniform draw across the interval, not a pinned endpoint.
        assert low < float(np.mean(fractions)) < high


class TestSensitivity:
    """The live knobs are the donor's hand load and the contact count."""

    def test_dose_is_graded_in_the_donor_hand_load(self) -> None:
        means = []
        for load in (1.0e4, 1.0e6, 1.0e8):
            core = _core(seed=31)
            draws = []
            for _ in range(400):
                donor = _agent(1, infected=True, hand_load=load)
                dose, _moved = _one_epoch(core, _agent(2), [donor])
                draws.append(dose)
            means.append(float(np.mean(draws)))
        assert means == sorted(means)
        # Four logs of donor load must move the dose by about four logs, not
        # by a saturating trickle.
        assert means[2] / means[0] > 1.0e3

    def test_the_route_saturates_in_the_contact_count(self) -> None:
        start = 1.0e6

        def _delivered(n_partners: int) -> float:
            totals = []
            for replicate in range(60):
                core = _core(seed=400 + replicate)
                donor = _agent(1, infected=True, hand_load=start)
                total = 0.0
                for partner_id in range(n_partners):
                    dose, _moved = _one_epoch(
                        core, _agent(500 + partner_id), [donor],
                    )
                    total += dose
                totals.append(total)
            return float(np.mean(totals))

        one, four, sixteen = (_delivered(n) for n in (1, 4, 16))
        assert one <= four <= sixteen
        # Sub-linear: a shared finite reservoir, not N independent emissions.
        assert sixteen < 16.0 * one * 0.75
        assert four < 4.0 * one

    def test_perturbing_continuous_shedding_leaves_the_dose_alone(
        self,
    ) -> None:
        """The route no longer reads whole-body faecal emission."""
        doses = []
        for shedding in (1.0e6, 1.0e11, 1.0e14):
            core = _core(seed=77)
            donor = _agent(1, infected=True, hand_load=1.0e6)
            dose, _moved = _one_epoch(
                core, _agent(2), [donor], shedding=shedding,
            )
            doses.append(dose)
        assert doses[1] == pytest.approx(doses[0], rel=1e-12)
        assert doses[2] == pytest.approx(doses[0], rel=1e-12)

    def test_more_carrying_donors_deliver_more(self) -> None:
        means = []
        for n_donors in (1, 2, 4):
            core = _core(seed=91)
            draws = []
            for _ in range(300):
                donors = [
                    _agent(i, infected=True, hand_load=1.0e6)
                    for i in range(n_donors)
                ]
                dose, _moved = _one_epoch(core, _agent(99), donors)
                draws.append(dose)
            means.append(float(np.mean(draws)))
        assert means == sorted(means)
        assert means[2] > 2.0 * means[0]
