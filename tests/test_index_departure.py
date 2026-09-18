"""Declared per-agent departure (INDEX-GEOM-01).

A host that leaves the ship for the rest of the run is placed at the
``"Departed"`` sentinel, which gates transmission exactly the way the
``"Ashore"`` excursion sentinel does — and is additionally excluded from
the denominators (testing rosters, onset records, VSP counters, shore
introductions, wastewater) that a port excursion does not need.

Sensitivity, invariants and validation here; no goldens are added. The
hull change-detector in test_covid_hull_change_detector.py remains the
single pinned reading.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.initiation import apply_explicit_seeds, resolve_initiation_plan
from engines.sim_clock import SimClock
from engines.transmission_core import TransmissionCore
from engines.voyage_itinerary import LOCATION_DEPARTED, agent_is_departed

PATHOGEN = "test_pathogen"
ZONE = "Test_Zone"


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=6.0, mode="hours")


def _agent(agent_id: int, *, role: str = "passenger") -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = _clock()
    agent.current_location = ZONE
    return agent


def _shedder(agent_id: int) -> KorkinAgent:
    agent = _agent(agent_id)
    agent.infection_status = InfectionStatus.INFECTED
    agent.illness_status = IllnessStatus.SYMPTOMATIC
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _profile() -> dict:
    return {
        "shedding_curve_log10": [7.0] * 40,
        "asymptomatic_shedding_log10": [7.0] * 40,
        "symptom_onset_day": 0.0,
        "recovery_day": 1000.0,
        "airborne_half_life_hours": 24.0,
        "dose_response": {"model": "exponential", "k": 0.05},
    }


class _FakeEngine:
    def __init__(self, passengers: int = 40) -> None:
        self.agents = [_agent(i) for i in range(passengers)]
        self.clock = _clock()
        self.initiation_manifest: dict = {"mode": "legacy"}


class TestHasDeparted:
    def test_never_departs_by_default(self) -> None:
        agent = _agent(0)
        assert agent.departure_epoch is None
        assert not any(agent.has_departed(e) for e in range(100))
        assert not agent_is_departed(agent)

    def test_boundary(self) -> None:
        agent = _agent(0)
        agent.departure_epoch = 8
        assert not agent.has_departed(7)
        assert agent.has_departed(8)
        assert agent.has_departed(9)

    def test_dict_shape_reads_the_sentinel(self) -> None:
        assert agent_is_departed({"location": LOCATION_DEPARTED})
        assert not agent_is_departed({"location": ZONE})


class TestSeedDeclaration:
    def _plan(self, **seed_fields):
        seed = {"pathogen": PATHOGEN, "count": 1, "epoch": 0}
        seed.update(seed_fields)
        return resolve_initiation_plan(
            {"initiation": {"explicit_seeds": [seed]}}, {PATHOGEN: _profile()},
        )

    def test_no_departure_leaves_the_field_unset(self) -> None:
        assert self._plan().seeds[0].departure_day is None

    @pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
    def test_invalid_departure_day_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError, match="departure_day"):
            self._plan(departure_day=bad)

    def test_departure_before_boarding_is_refused(self) -> None:
        """A host cannot leave the ship before it boards.

        ``departure_day`` is days; ``epoch`` is epochs. On the 6-hour test
        clock, departure_day 0.5 is epoch 2 — earlier than a seed that
        arrives at epoch 4.
        """
        plan = resolve_initiation_plan(
            {
                "initiation": {
                    "explicit_seeds": [
                        {
                            "pathogen": PATHOGEN,
                            "count": 1,
                            "epoch": 4,
                            "departure_day": 0.5,
                        },
                    ],
                },
            },
            {PATHOGEN: _profile()},
        )
        engine = _FakeEngine()
        with pytest.raises(ValueError, match="before it boards|earlier"):
            apply_explicit_seeds(
                plan, engine, 4, np.random.default_rng(1), {PATHOGEN: _profile()},
            )

    def test_departure_epoch_is_written_on_the_seeded_host(self) -> None:
        plan = self._plan(departure_day=2.0)
        engine = _FakeEngine()
        records = apply_explicit_seeds(
            plan, engine, 0, np.random.default_rng(1), {PATHOGEN: _profile()},
        )
        expected = int(round(engine.clock.epochs_for_days(2.0)))
        seeded = [a for a in engine.agents if PATHOGEN in a.infections]
        assert len(seeded) == 1
        assert seeded[0].departure_epoch == expected
        assert records[0]["departure_day"] == 2.0
        # Everyone else never departs.
        assert all(
            a.departure_epoch is None for a in engine.agents if a is not seeded[0]
        )


class TestTransmissionGating:
    def _core(self) -> TransmissionCore:
        core = TransmissionCore(
            rng=np.random.default_rng(19),
            zone_volumes={ZONE: 50.0},
            pathogen_profiles={PATHOGEN: _profile()},
            zone_types={ZONE: "Dining"},
            clock=_clock(),
        )
        core.initialize_zones([ZONE])
        return core

    def _run_epoch(self, epoch: int, agents: list[KorkinAgent]):
        return self._core().execute_transmission(
            epoch=epoch,
            agents=agents,
            zone_pathogen_mass={ZONE: 0.0},
        )

    def test_departed_shedder_is_in_no_zone_and_doses_nobody(self) -> None:
        shedder = _shedder(0)
        susceptibles = [_agent(i) for i in range(1, 6)]
        aboard_matrix, aboard_events = self._run_epoch(
            0, [shedder] + susceptibles,
        )
        aboard_summary = {row["zone"]: row for row in aboard_matrix.zone_contact_summary}
        assert aboard_summary[ZONE]["occupant_count"] == 6

        shedder.departure_epoch = 0
        shedder.current_location = LOCATION_DEPARTED
        gone_matrix, gone_events = self._run_epoch(
            0, [shedder] + susceptibles,
        )
        gone_summary = {row["zone"]: row for row in gone_matrix.zone_contact_summary}
        assert gone_summary[ZONE]["occupant_count"] == 5
        assert 0 not in gone_summary[ZONE]["shedder_ids"]
        assert len(gone_events) < len(aboard_events)
        assert all(e.source_agent_id != 0 for e in gone_events)

    def test_departed_susceptible_cannot_be_challenged(self) -> None:
        shedder = _shedder(0)
        target = _agent(1)
        target.departure_epoch = 0
        target.current_location = LOCATION_DEPARTED
        _, events = self._run_epoch(0, [shedder, target] + [
            _agent(i) for i in range(2, 5)
        ])
        assert all(e.target_agent_id != 1 for e in events)
        assert PATHOGEN not in target.infections
        assert target.cumulative_exposure.get(PATHOGEN, 0.0) == 0.0


class TestGradedDeparture:
    """Earlier departure cannot infect more: an ordered sweep on events."""

    @staticmethod
    def _infections_over(departure_epoch: int | None, epochs: int) -> int:
        shedder = _shedder(0)
        shedder.departure_epoch = departure_epoch
        agents = [shedder] + [_agent(i) for i in range(1, 30)]
        core = TransmissionCore(
            rng=np.random.default_rng(7),
            zone_volumes={ZONE: 200.0},
            pathogen_profiles={PATHOGEN: _profile()},
            zone_types={ZONE: "Dining"},
            clock=_clock(),
        )
        core.initialize_zones([ZONE])
        total = 0
        for epoch in range(epochs):
            if shedder.has_departed(epoch):
                shedder.current_location = LOCATION_DEPARTED
            _, events = core.execute_transmission(
                epoch=epoch, agents=agents, zone_pathogen_mass={ZONE: 0.0},
            )
            total += len(events)
        return total

    def test_earlier_departure_infects_fewer(self) -> None:
        epochs = 8
        counts = [
            self._infections_over(d, epochs)
            for d in (None, 6, 3, 0)
        ]
        assert counts == sorted(counts, reverse=True), counts
        assert counts[0] > counts[-1], f"departure is a dead knob: {counts}"


class TestDenominators:
    def test_departed_host_is_not_swabbable(self) -> None:
        from crusher_labs.testing_campaign import (
            CampaignDay,
            EligibilityTier,
            TestingCampaign,
        )

        campaign = TestingCampaign(
            campaign_id="t",
            pathogen_id=PATHOGEN,
            source="test",
            evidence_grade="test",
            tiers={"all": EligibilityTier(tier_id="all", rule="everyone")},
            days=[CampaignDay(day_offset=0, tests=10, tiers=("all",))],
        )
        agents = [
            {"agent_id": 1, "role": "passenger", "location": ZONE},
            {"agent_id": 2, "role": "passenger", "location": LOCATION_DEPARTED},
        ]
        roster = campaign.specimen_roster(agents, 0, rng=np.random.default_rng(0))
        assert 2 not in roster

    def test_total_agents_and_sick_call_exclude_departed(self) -> None:
        from crusher_labs.modalities.syndromic import SyndromicSurveillance

        syn = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            clock=_clock(),
            rng=np.random.default_rng(3),
        )
        aboard = {
            "agent_id": 1,
            "role": "passenger",
            "location": ZONE,
            "symptom_presentation": "symptomatic",
            "infection_state": "infected",
            "compliance_status": "compliant",
            "pathogen_infections": {
                PATHOGEN: {"status": "INFECTED", "illness": "SYMPTOMATIC",
                           "symptom_severity": "mild"},
            },
        }
        departed = dict(aboard)
        departed.update({"agent_id": 2, "location": LOCATION_DEPARTED})
        result = syn.query_ground_truth(
            {"epoch": 0, "agents": [aboard, departed]},
        )
        assert result["total_agents"] == 1
        assert 2 not in result["sick_call_agents"]
        assert 2 not in result["true_positive_ids"]

    def test_vsp_counters_exclude_departed(self) -> None:
        from engines.infection_dynamics_bridge import (
            VSP_RULE_INSTANT_PREVALENCE,
            KorkinShipEngine,
        )

        engine = KorkinShipEngine(
            num_passengers=5,
            num_crew=0,
            initial_infected=0,
            immune_ratio=0.0,
            seed=5,
            clock=_clock(),
            vsp_trigger_rule=VSP_RULE_INSTANT_PREVALENCE,
        )
        ill = engine.agents[0]
        ill.illness_status = IllnessStatus.SYMPTOMATIC
        # int(0.3 * 5) = 1: one symptomatic aboard triggers.
        engine.vsp_threshold_fraction = 0.3
        engine._check_vsp_trigger()
        assert engine.vsp_triggered

        engine2 = KorkinShipEngine(
            num_passengers=5,
            num_crew=0,
            initial_infected=0,
            immune_ratio=0.0,
            seed=5,
            clock=_clock(),
            vsp_trigger_rule=VSP_RULE_INSTANT_PREVALENCE,
        )
        ill2 = engine2.agents[0]
        ill2.illness_status = IllnessStatus.SYMPTOMATIC
        ill2.departure_epoch = 0
        # Aboard count is 4 after departure: int(0.3 * 4) = 1 still needed.
        engine2.vsp_threshold_fraction = 0.3
        engine2._check_vsp_trigger()
        assert not engine2.vsp_triggered
