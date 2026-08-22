"""Phenotype axes that mutation can move actually change the simulation (PR 3d).

PR 3 could mint a strain with a shedding, incubation, or immune-escape effect,
but only transmissibility was read by anything. These tests hold each remaining
axis to the same standard: a few different values of the knob produce a few
different values downstream, monotonically, and with the flag off the number is
the legacy number.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.strain_state import (  # noqa: E402
    Phenotype,
    StrainEvolutionConfig,
    StrainRegistry,
)
from engines.transmission_core import TransmissionCore  # noqa: E402
from orchestrator_epoch import (  # noqa: E402
    ONSET_DAY,
    _advance_agent_pathogen_infections,
)

PATHOGEN = "norwalk_gi"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]
GENOTYPES = ("GII.4", "GII.17", "GII.2")


def _norwalk_profile() -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = next(
        p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN
    )
    return copy.deepcopy(profile)


def _agent(aid: int = 1, *, immune: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=immune,
        home_zone="MainDining_L",
        dining_zone="MainDining_L",
        work_zone="MainDining_L",
        free_zone="MainDining_L",
        schedule=["Free"] * 24,
    )
    agent.current_location = "MainDining_L"
    return agent


def _core(*, cfg: dict | None = VARIANT_CFG, seed: int = 5) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={PATHOGEN: _norwalk_profile()},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=cfg,
    )
    core.initialize_zones(ZONES)
    return core


# ── Shedding axis ───────────────────────────────────────────────────────

class TestSheddingAxis:
    @pytest.mark.parametrize("multiplier", [0.25, 0.5, 1.0, 2.0, 4.0])
    def test_shedding_scales_with_strain_multiplier(self, multiplier: float) -> None:
        """The strain factor multiplies the curve, leaving day shape intact."""
        profile = _norwalk_profile()
        baseline = _agent()
        baseline.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=2)
        mutant = _agent()
        mutant.infect_with_pathogen(
            PATHOGEN, 1e4, 0, time_infected=2,
            strain_id="s:1",
            strain_phenotype=Phenotype(shedding_multiplier=multiplier),
        )
        assert mutant.get_pathogen_shedding(PATHOGEN, profile) == pytest.approx(
            baseline.get_pathogen_shedding(PATHOGEN, profile) * multiplier,
        )

    def test_graded_sweep_is_monotone_and_spans_the_range(self) -> None:
        profile = _norwalk_profile()
        values = []
        for multiplier in (0.1, 0.5, 1.0, 5.0):
            agent = _agent()
            agent.infect_with_pathogen(
                PATHOGEN, 1e4, 0, time_infected=1,
                strain_id="s:1",
                strain_phenotype=Phenotype(shedding_multiplier=multiplier),
            )
            values.append(agent.get_pathogen_shedding(PATHOGEN, profile))
        assert values == sorted(values)
        assert values[-1] == pytest.approx(50.0 * values[0])
        assert all(np.isfinite(v) for v in values)
        assert all(v > 0.0 for v in values)

    def test_host_and_strain_factors_compose_without_replacing(self) -> None:
        """A high-shedding host of a high-shedding strain sheds the product."""
        profile = _norwalk_profile()
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, time_infected=2,
            strain_id="s:1",
            strain_phenotype=Phenotype(shedding_multiplier=3.0),
        )
        agent.infections[PATHOGEN]["shedding_multiplier"] = 2.0
        plain = _agent()
        plain.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=2)
        assert agent.get_pathogen_shedding(PATHOGEN, profile) == pytest.approx(
            plain.get_pathogen_shedding(PATHOGEN, profile) * 6.0,
        )

    def test_untracked_infection_sheds_the_legacy_value(self) -> None:
        profile = _norwalk_profile()
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=2)
        assert "strain_shedding_multiplier" not in agent.infections[PATHOGEN]
        expected = agent.infections[PATHOGEN]["shedding_multiplier"]
        # Illness is NOT_ILL at assignment, so the asymptomatic curve applies.
        curve = profile["asymptomatic_shedding_log10"]
        adj = profile.get("dose_adjustment", 4.0)
        assert agent.get_pathogen_shedding(PATHOGEN, profile) == pytest.approx(
            pow(10, curve[2] - adj) * expected,
        )

    def test_strain_shedding_moves_emitted_dose(self) -> None:
        """The axis reaches transmission, not just the shedding accessor."""
        doses = []
        for multiplier in (0.2, 1.0, 5.0):
            core = _core()
            shedder = _agent(0)
            shedder.infection_status = InfectionStatus.INFECTED
            shedder.time_infected = 2
            shedder.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=2)
            shedder.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
            shedder.infections[PATHOGEN]["shedding_multiplier"] = 1.0
            registry = core.strain_registry
            assert registry is not None
            strain = registry.mint(
                PATHOGEN,
                genotype=GENOTYPES[0],
                phenotype=Phenotype(shedding_multiplier=multiplier),
            )
            shedder.assign_strain(PATHOGEN, strain.strain_id, Phenotype.of(strain))
            targets = [_agent(100 + i) for i in range(4)]
            core.execute_transmission(
                epoch=0,
                agents=[shedder, *targets],
                zone_pathogen_mass=dict.fromkeys(ZONES, 0.0),
                multi_pathogen_mass={PATHOGEN: dict.fromkeys(ZONES, 0.0)},
            )
            doses.append(sum(
                core._last_pathogen_doses.get(t.agent_id, {}).get(PATHOGEN, 0.0)
                for t in targets
            ))
        assert doses == sorted(doses)
        assert doses[0] > 0.0
        assert doses[-1] > 5.0 * doses[0]


# ── Incubation axis ─────────────────────────────────────────────────────

def _onset_day(
    modifier: float, *, seed: int = 3, symptom_onset_day: float | None = None,
) -> int:
    """First day post-infection on which symptoms appear, given a modifier."""
    profile = _norwalk_profile()
    if symptom_onset_day is not None:
        profile["symptom_onset_day"] = symptom_onset_day
    # A large dose makes the illness draw all but certain, so the day that comes
    # back is the onset gate rather than a coin flip.
    agent = _agent()
    agent.infect_with_pathogen(
        PATHOGEN, 1e12, 0,
        strain_id="s:1",
        strain_phenotype=Phenotype(incubation_modifier=modifier),
    )
    profile = {**profile, "recovery_day": 30}
    rng = np.random.default_rng(seed)
    for _ in range(12):
        _advance_agent_pathogen_infections(agent, {PATHOGEN: profile}, rng)
        inf = agent.infections[PATHOGEN]
        if inf["illness"] == IllnessStatus.SYMPTOMATIC:
            return int(inf["time_infected"])
    return -1


class TestIncubationAxis:
    def test_graded_modifiers_shift_onset_monotonically(self) -> None:
        onsets = [_onset_day(m) for m in (-2.0, -1.0, 0.0, 1.0, 3.0)]
        assert all(day >= 0 for day in onsets), onsets
        assert onsets == sorted(onsets)
        assert onsets[0] < onsets[-1]

    def test_zero_modifier_reproduces_the_legacy_onset_day(self) -> None:
        assert _onset_day(0.0) == int(ONSET_DAY)
        untracked = _agent()
        untracked.infect_with_pathogen(PATHOGEN, 1e12, 0)
        rng = np.random.default_rng(3)
        profile = {**_norwalk_profile(), "recovery_day": 30}
        _advance_agent_pathogen_infections(untracked, {PATHOGEN: profile}, rng)
        assert untracked.infections[PATHOGEN]["illness"] == IllnessStatus.SYMPTOMATIC

    def test_faster_onset_cannot_precede_the_first_evaluated_day(self) -> None:
        """Nothing presents before the first progression step, however negative."""
        assert _onset_day(-50.0) == int(ONSET_DAY)

    def test_faster_onset_bites_when_the_baseline_onset_is_later(self) -> None:
        """The negative half of the axis is live for a slower-incubating pathogen."""
        baseline = _onset_day(0.0, symptom_onset_day=4.0)
        faster = _onset_day(-2.0, symptom_onset_day=4.0)
        assert baseline == 4
        assert faster == 2

    def test_slower_onset_can_outlast_the_observation_window(self) -> None:
        assert _onset_day(1.0) > int(ONSET_DAY)


# ── Immune escape / cross-immunity ──────────────────────────────────────

def _immunity_core(
    escape: float, *, prior: str, challenge: str,
) -> tuple[TransmissionCore, KorkinAgent]:
    """A core with one immune agent challenged by a single known strain."""
    core = _core()
    registry = core.strain_registry
    assert registry is not None
    strain = registry.mint(
        PATHOGEN,
        genotype=challenge,
        phenotype=Phenotype(immune_escape=escape),
    )
    agent = _agent(7, immune=True)
    agent.prior_genotypes[PATHOGEN] = prior
    core._strain_doses = {
        agent.agent_id: {PATHOGEN: {(strain.strain_id, 0): 100.0}},
    }
    return core, agent


class TestImmuneEscapeAxis:
    def test_escape_grades_protection_down(self) -> None:
        protections = []
        for escape in (0.0, 0.25, 0.5, 1.0):
            core, agent = _immunity_core(
                escape, prior=GENOTYPES[0], challenge=GENOTYPES[0],
            )
            protections.append(core._challenge_protection(agent, PATHOGEN))
        assert protections == sorted(protections, reverse=True)
        assert protections[0] > protections[-1]
        assert all(0.0 <= p <= 1.0 for p in protections)
        assert protections[-1] == pytest.approx(0.0)

    def test_heterologous_challenge_is_less_protected_than_homologous(self) -> None:
        core, agent = _immunity_core(
            0.0, prior=GENOTYPES[0], challenge=GENOTYPES[0],
        )
        homologous = core._challenge_protection(agent, PATHOGEN)
        core, agent = _immunity_core(
            0.0, prior=GENOTYPES[0], challenge=GENOTYPES[1],
        )
        heterologous = core._challenge_protection(agent, PATHOGEN)
        assert homologous > heterologous
        assert 0.0 < heterologous < 1.0

    def test_unattributed_dose_is_not_credited_with_protection(self) -> None:
        """Half the dose from an unidentified strain halves the protection."""
        core, agent = _immunity_core(
            0.0, prior=GENOTYPES[0], challenge=GENOTYPES[0],
        )
        full = core._challenge_protection(agent, PATHOGEN)
        shares = core._strain_doses[agent.agent_id][PATHOGEN]
        (known_key, known_dose), = shares.items()
        shares[("", None)] = known_dose
        assert core._challenge_protection(agent, PATHOGEN) == pytest.approx(
            full / 2.0,
        )
        assert known_key in shares

    def test_pre_immune_agent_is_absolutely_protected_without_genotypes(self) -> None:
        """Legacy immunity is preserved when the pathogen declares no genotypes."""
        core = _core()
        core.strain_configs = {
            PATHOGEN: StrainEvolutionConfig(
                pathogen_id=PATHOGEN, genotypes=GENOTYPES,
            ),
        }
        immune = _agent(3, immune=True)
        susceptible = _agent(4)
        assert core._challenge_protection(immune, PATHOGEN) == pytest.approx(1.0)
        assert core._challenge_protection(susceptible, PATHOGEN) == pytest.approx(0.0)

    def test_flag_off_keeps_immunity_absolute(self) -> None:
        core = _core(cfg=None)
        assert core._challenge_protection(
            _agent(3, immune=True), PATHOGEN,
        ) == pytest.approx(1.0)
        assert core._challenge_protection(_agent(4), PATHOGEN) == pytest.approx(0.0)

    def test_prior_genotype_comes_from_a_resolved_infection(self) -> None:
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        past = registry.mint(PATHOGEN, genotype=GENOTYPES[2])
        agent = _agent(9)
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=past.strain_id,
            strain_phenotype=Phenotype.of(past),
        )
        profile = {**_norwalk_profile(), "recovery_day": 1}
        _advance_agent_pathogen_infections(
            agent, {PATHOGEN: profile}, np.random.default_rng(3), registry, 4,
        )
        assert agent.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        assert core._prior_genotypes(agent, PATHOGEN) == (GENOTYPES[2],)

    def test_pre_immune_prior_genotype_is_drawn_once_and_kept(self) -> None:
        core = _core()
        agent = _agent(11, immune=True)
        first = core._prior_genotypes(agent, PATHOGEN)
        assert len(first) == 1
        assert first[0] in GENOTYPES
        assert core._prior_genotypes(agent, PATHOGEN) == first

    def test_naive_agent_has_no_prior_and_no_protection(self) -> None:
        core = _core()
        agent = _agent(12)
        assert core._prior_genotypes(agent, PATHOGEN) == ()
        assert core._challenge_protection(agent, PATHOGEN) == pytest.approx(0.0)


# ── Negative controls ───────────────────────────────────────────────────

class TestUnrelatedKnobs:
    def test_transmissibility_does_not_move_shedding(self) -> None:
        profile = _norwalk_profile()
        values = []
        for multiplier in (0.5, 1.0, 4.0):
            agent = _agent()
            agent.infect_with_pathogen(
                PATHOGEN, 1e4, 0, time_infected=2,
                strain_id="s:1",
                strain_phenotype=Phenotype(
                    transmissibility_multiplier=multiplier,
                ),
            )
            values.append(agent.get_pathogen_shedding(PATHOGEN, profile))
        assert values[0] == pytest.approx(values[-1])

    def test_shedding_does_not_move_onset(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e12, 0,
            strain_id="s:1",
            strain_phenotype=Phenotype(shedding_multiplier=8.0),
        )
        rng = np.random.default_rng(3)
        profile = {**_norwalk_profile(), "recovery_day": 30}
        _advance_agent_pathogen_infections(agent, {PATHOGEN: profile}, rng)
        assert agent.infections[PATHOGEN]["illness"] == IllnessStatus.SYMPTOMATIC
        assert agent.infections[PATHOGEN]["time_infected"] == int(ONSET_DAY)

    def test_registry_phenotype_reaches_the_infection_record(self) -> None:
        registry = StrainRegistry()
        strain = registry.mint(
            PATHOGEN,
            genotype=GENOTYPES[0],
            phenotype=Phenotype(shedding_multiplier=2.5, incubation_modifier=-0.5),
        )
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        agent.assign_strain(PATHOGEN, strain.strain_id, Phenotype.of(strain))
        inf = agent.infections[PATHOGEN]
        assert inf["strain_id"] == strain.strain_id
        assert inf["strain_shedding_multiplier"] == pytest.approx(2.5)
        assert inf["strain_incubation_modifier"] == pytest.approx(-0.5)
