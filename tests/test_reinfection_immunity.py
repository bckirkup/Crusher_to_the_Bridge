"""REINFECT-01: cleared-and-reinfected hosts keep immune memory and a
true episode history.

Without a strain registry (every ``variant_surveillance.enabled`` false run),
a cleared infection used to leave no ImmuneRecord, so the next epoch's dose
re-infected the host and ``infect_with_pathogen`` overwrote the first
episode's stamps wholesale. These tests pin the three repairs: the
genotype-blind clearance record, its protection through
``_challenge_protection``, and the episode bookkeeping on the infection
record.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    InfectionStatus,
    KorkinAgent,
)
from engines.natural_history import advance_infections
from engines.sim_clock import HOURS, SimClock
from engines.strain_state import IMMUNITY_FROM_INFECTION, StrainRegistry
from engines.transmission_core import TransmissionCore

PATHOGEN = "norwalk_gi"
OTHER = "sars_cov2_resp"
ZONE = "Deck_1"
EPOCHS_PER_DAY = 24


def _agent(aid: int = 1, *, clock: SimClock | None = None) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = clock or SimClock(epoch_duration_hours=1.0, mode=HOURS)
    agent.current_location = ZONE
    return agent


def _waning_profile(
    refractory_days: float, refractory_protection: float,
) -> dict:
    """Minimal profile carrying only the ``immune_waning`` axis."""
    return {
        "pathogen_id": PATHOGEN,
        "strain_evolution": {
            "genotypes": ["G1"],
            "immune_waning": {
                "refractory_days": refractory_days,
                "refractory_protection": refractory_protection,
                "half_life_days": 0.0,
            },
        },
    }


def _core(profiles: dict[str, dict], seed: int = 7) -> TransmissionCore:
    """A no-registry core: the ``variant_surveillance``-off configuration."""
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 60.0},
        pathogen_profiles=profiles,
        zone_types={ZONE: "Cabin_Corridor"},
        cfg={},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    assert core.strain_registry is None
    return core


def _fast_clearance_profile() -> dict:
    return {
        "recovery_day": 1,
        "shedding_duration_days": 1,
        "symptom_onset_day": 1.0,
        "symptomatic_fraction": 0.0,
    }


def _clear(agent: KorkinAgent, registry=None, epoch: int = 96) -> None:
    """Advance the host past clearance so the infection resolves at *epoch*."""
    profile = _fast_clearance_profile()
    for _ in range(int(agent.clock.epochs_for_days(3))):
        advance_infections(
            agent, {PATHOGEN: profile}, np.random.default_rng(1),
            registry, epoch,
        )


class TestUnlabeledClearanceRecord:
    """(a) A resolved infection must always leave an immune record."""

    def test_no_registry_writes_one_genotype_blind_record(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        _clear(agent)
        assert agent.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        records = [
            r for r in agent.immune_history if r.pathogen_id == PATHOGEN
        ]
        assert len(records) == 1
        record = records[0]
        assert record.genotype == ""
        assert record.strain_id == ""
        assert record.origin == IMMUNITY_FROM_INFECTION
        assert record.epoch == 96

    def test_registry_run_adds_no_unlabeled_record(self) -> None:
        """With lineages tracked, the count is unchanged vs the old path."""
        agent = _agent()
        registry = StrainRegistry()
        strain = registry.mint(PATHOGEN, genotype="GII.4")
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=strain.strain_id,
        )
        _clear(agent, registry=registry)
        records = [
            r for r in agent.immune_history if r.pathogen_id == PATHOGEN
        ]
        assert len(records) == 1
        assert records[0].genotype == "GII.4"


class TestUnlabeledProtection:
    """(b, c, f) ``_challenge_protection`` reads infection-origin records."""

    def _protection(
        self, profiles: dict, records: list, epoch: int,
        pathogen: str = PATHOGEN,
    ) -> float:
        core = _core(profiles)
        agent = _agent(clock=core.clock)
        for record in records:
            agent.record_immunity(record)
        return core._challenge_protection(agent, pathogen, epoch)

    def test_refractory_window_is_absolute_then_gone(self) -> None:
        """Graded: protection 1.0 inside the window at 0/R/2/R days, 0 after."""
        from engines.strain_state import ImmuneRecord
        profile = _waning_profile(56.0, 1.0)
        record_epoch = 0
        ages = [0.0, 28.0, 56.0]
        values = [
            self._protection(
                {PATHOGEN: profile},
                [ImmuneRecord(pathogen_id=PATHOGEN, genotype="",
                              epoch=record_epoch)],
                record_epoch + int(age * EPOCHS_PER_DAY),
            )
            for age in ages
        ]
        assert values == [pytest.approx(1.0)] * 3
        after = self._protection(
            {PATHOGEN: profile},
            [ImmuneRecord(pathogen_id=PATHOGEN, genotype="", epoch=0)],
            int(57.0 * EPOCHS_PER_DAY),
        )
        assert after == pytest.approx(0.0)

    def test_partial_refractory_protection_scales_the_window(self) -> None:
        """A 0.6 window yields 0.6 inside it, not the legacy 1.0 or 0.0."""
        from engines.strain_state import ImmuneRecord
        profile = _waning_profile(56.0, 0.6)
        value = self._protection(
            {PATHOGEN: profile},
            [ImmuneRecord(pathogen_id=PATHOGEN, genotype="", epoch=0)],
            int(10.0 * EPOCHS_PER_DAY),
        )
        assert value == pytest.approx(0.6)

    def test_no_immune_waning_block_leaves_protection_at_zero(self) -> None:
        """Negative control: a profile without the block protects nothing."""
        from engines.strain_state import ImmuneRecord
        value = self._protection(
            {PATHOGEN: {"pathogen_id": PATHOGEN}},
            [ImmuneRecord(pathogen_id=PATHOGEN, genotype="", epoch=0)],
            0,
        )
        assert value == pytest.approx(0.0)

    def test_records_are_pathogen_specific(self) -> None:
        """An A-record gives nothing against B."""
        from engines.strain_state import ImmuneRecord
        profiles = {
            PATHOGEN: _waning_profile(56.0, 1.0),
            OTHER: {**_waning_profile(56.0, 1.0), "pathogen_id": OTHER},
        }
        value = self._protection(
            profiles,
            [ImmuneRecord(pathogen_id=PATHOGEN, genotype="", epoch=0)],
            0,
            pathogen=OTHER,
        )
        assert value == pytest.approx(0.0)

    def test_protection_stays_bounded_over_a_sweep(self) -> None:
        """Bounds: protection stays in [0, 1] for a spread of ages/params."""
        from engines.strain_state import ImmuneRecord
        rng = np.random.default_rng(3)
        for _ in range(20):
            refractory = float(rng.uniform(0.0, 200.0))
            protection = float(rng.uniform(0.0, 1.0))
            age_days = float(rng.uniform(0.0, 400.0))
            value = self._protection(
                {PATHOGEN: _waning_profile(refractory, protection)},
                [ImmuneRecord(pathogen_id=PATHOGEN, genotype="", epoch=0)],
                int(age_days * EPOCHS_PER_DAY),
            )
            assert 0.0 <= value <= 1.0


class TestEpisodeBookkeeping:
    """(d) A second infection extends the record instead of erasing it."""

    def test_second_episode_keeps_the_first_infection_epoch(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 10)
        agent.infect_with_pathogen(PATHOGEN, 1e4, 400)
        inf = agent.infections[PATHOGEN]
        assert inf["infection_epoch"] == 400
        assert inf["first_infection_epoch"] == 10
        assert inf["episode"] == 2
        assert inf["episode_epochs"] == [10, 400]

    def test_other_pathogen_records_are_untouched(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(OTHER, 1e4, 5)
        agent.infect_with_pathogen(PATHOGEN, 1e4, 10)
        agent.infect_with_pathogen(PATHOGEN, 1e4, 20)
        other = agent.infections[OTHER]
        assert other["infection_epoch"] == 5
        assert other["episode"] == 1
        assert other["episode_epochs"] == [5]


class TestOnsetRedating:
    """(e) A later episode's onset replaces the stale stored onset."""

    def _modality(self):
        from crusher_labs.modalities.syndromic import SyndromicSurveillance
        return SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            noise_categories=[],
            rng=np.random.default_rng(0),
        )

    @staticmethod
    def _agent_dict(aid: int, infection_epoch: int, elapsed: int) -> dict:
        from telemetry_buffer.agent_axes import (
            COMPLIANCE_COMPLIANT,
            INFECTION_INFECTED,
            PRESENTATION_SYMPTOMATIC,
        )
        return {
            "agent_id": aid,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                PATHOGEN: {
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "moderate",
                    "infection_epoch": infection_epoch,
                    "epochs_since_symptom_onset": elapsed,
                },
            },
        }

    def test_a_later_episode_redates_the_onset(self) -> None:
        modality = self._modality()
        modality.query_ground_truth(
            {"epoch": 10, "agents": [self._agent_dict(1, 0, 5)]},
        )
        assert modality._presentation_onset_epoch[1] == 5
        modality.query_ground_truth(
            {"epoch": 100, "agents": [self._agent_dict(1, 50, 2)]},
        )
        assert modality._presentation_onset_epoch[1] == 98

    def test_the_same_episode_is_not_redated(self) -> None:
        modality = self._modality()
        modality.query_ground_truth(
            {"epoch": 10, "agents": [self._agent_dict(1, 0, 5)]},
        )
        modality.query_ground_truth(
            {"epoch": 60, "agents": [self._agent_dict(1, 0, 55)]},
        )
        assert modality._presentation_onset_epoch[1] == 5
