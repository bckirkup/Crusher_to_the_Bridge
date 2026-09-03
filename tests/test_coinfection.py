"""Same-pathogen co-infection and within-host competition (Paper 3 PR 3b).

Until now a second lineage of the same pathogen could never establish: infected
agents were skipped before dose was even computed, so recombination had no
substrate and a mixed infection could not be typed. These tests hold the new
resident-strain layer to four properties: superinfection frequency responds
monotonically to the interference factor, a single resident behaves exactly like
the legacy single infection, pathogen-level status and legacy fields stay
coherent under co-infection, and a co-infected host's shedding is conserved
against the sum of its per-strain curves.
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
)
from engines.transmission_core import TransmissionCore  # noqa: E402
from orchestrator_epoch import (  # noqa: E402
    _advance_agent_pathogen_infections,
)

PATHOGEN = "norwalk_gi"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]
GENOTYPES = ("GII.4", "GII.17")
RESIDENT = "s:resident"
INVADER = "s:invader"


def _norwalk_profile() -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    return copy.deepcopy(
        {
            **next(p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN),
            "symptom_onset_day": 0,
        },
    )


def _agent(aid: int = 1, loc: str = "MainDining_L", *, immune: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=immune,
        home_zone=loc,
        dining_zone=loc,
        work_zone=loc,
        free_zone=loc,
        schedule=["Free"] * 24,
    )
    agent.current_location = loc
    return agent


def _core(
    *,
    cfg: dict | None = VARIANT_CFG,
    seed: int = 5,
    susceptibility: float | None = None,
) -> TransmissionCore:
    profile = _norwalk_profile()
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={PATHOGEN: profile},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=cfg,
    )
    core.initialize_zones(ZONES)
    if susceptibility is not None:
        core.strain_configs = {
            PATHOGEN: StrainEvolutionConfig(
                pathogen_id=PATHOGEN,
                genotypes=GENOTYPES,
                superinfection_susceptibility=susceptibility,
            ),
        }
    return core


def _coinfected(
    *,
    dose_a: float = 1e4,
    dose_b: float = 1e4,
    dpi_a: int = 2,
    epoch_b: int = 5,
    shedding_b: float = 1.0,
    symptomatic: bool = True,
) -> KorkinAgent:
    """One host carrying two lineages, the second acquired later."""
    agent = _agent()
    agent.infect_with_pathogen(
        PATHOGEN, dose_a, 0, time_infected=dpi_a,
        strain_id=RESIDENT, strain_phenotype=Phenotype(),
    )
    if symptomatic:
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.superinfect_with_strain(
        PATHOGEN, INVADER, dose_b, epoch_b,
        phenotype=Phenotype(shedding_multiplier=shedding_b),
    )
    return agent


# ── Resident-strain state ───────────────────────────────────────────────

class TestResidentStrains:
    def test_tracked_infection_has_exactly_one_resident(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        residents = agent.resident_strains(PATHOGEN)
        assert list(residents) == [RESIDENT]
        assert agent.strain_id_for(PATHOGEN) == RESIDENT

    def test_untracked_infection_has_no_residents(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        assert agent.resident_strains(PATHOGEN) == {}
        assert agent.strain_id_for(PATHOGEN) is None

    def test_recovered_infection_has_no_residents(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        agent.infections[PATHOGEN]["status"] = InfectionStatus.RECOVERED
        assert agent.resident_strains(PATHOGEN) == {}

    def test_superinfection_adds_a_lineage_without_touching_the_infection(self) -> None:
        agent = _coinfected()
        inf = agent.infections[PATHOGEN]
        assert set(agent.resident_strains(PATHOGEN)) == {RESIDENT, INVADER}
        assert inf["status"] == InfectionStatus.INFECTED
        assert inf["strain_id"] == RESIDENT
        assert inf["time_infected"] == 2
        assert inf["acquired_particles"] == pytest.approx(1e4)

    def test_invader_starts_its_own_clock(self) -> None:
        agent = _coinfected(dpi_a=4)
        residents = agent.resident_strains(PATHOGEN)
        assert residents[RESIDENT].time_infected == 4
        assert residents[INVADER].time_infected == 0

    def test_homologous_re_exposure_absorbs_dose_without_a_new_lineage(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        established = agent.superinfect_with_strain(PATHOGEN, RESIDENT, 500.0, 3)
        residents = agent.resident_strains(PATHOGEN)
        assert established is False
        assert list(residents) == [RESIDENT]
        assert residents[RESIDENT].acquired_particles == pytest.approx(1e4 + 500.0)

    def test_untracked_infection_cannot_be_superinfected(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        assert agent.superinfect_with_strain(PATHOGEN, INVADER, 1e4, 2) is False
        assert agent.resident_strains(PATHOGEN) == {}

    def test_uninfected_agent_cannot_be_superinfected(self) -> None:
        agent = _agent()
        assert agent.superinfect_with_strain(PATHOGEN, INVADER, 1e4, 2) is False
        assert PATHOGEN not in agent.infections

    def test_within_host_replacement_keeps_the_co_resident(self) -> None:
        agent = _coinfected()
        agent.replace_strain(PATHOGEN, RESIDENT, "s:child", Phenotype())
        residents = agent.resident_strains(PATHOGEN)
        assert set(residents) == {"s:child", INVADER}
        assert residents["s:child"].time_infected == 2
        assert agent.strain_id_for(PATHOGEN) == "s:child"


# ── Shedding composition ───────────────────────────────────────────────

class TestSheddingComposition:
    def test_single_resident_sheds_exactly_the_legacy_amount(self) -> None:
        profile = _norwalk_profile()
        legacy = _agent()
        legacy.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=3)
        tracked = _agent(2)
        tracked.infect_with_pathogen(
            PATHOGEN, 1e4, 0, time_infected=3,
            strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        assert tracked.get_pathogen_shedding(PATHOGEN, profile) == pytest.approx(
            legacy.get_pathogen_shedding(PATHOGEN, profile),
        )

    def test_co_infection_conserves_total_shedding_at_equal_ages(self) -> None:
        """Two lineages of the same age partition one host's capacity."""
        profile = _norwalk_profile()
        single = _agent()
        single.infect_with_pathogen(
            PATHOGEN, 1e4, 0, time_infected=0,
            strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        single.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
        mixed = _coinfected(dpi_a=0, epoch_b=0)
        assert mixed.get_pathogen_shedding(PATHOGEN, profile) == pytest.approx(
            single.get_pathogen_shedding(PATHOGEN, profile),
        )

    def test_total_equals_the_sum_of_per_strain_curves(self) -> None:
        profile = _norwalk_profile()
        agent = _coinfected(dose_a=3e4, dose_b=1e4, dpi_a=3)
        total = agent.get_pathogen_shedding(PATHOGEN, profile)
        shares = agent.strain_shedding_shares(PATHOGEN, profile)
        assert sum(shares.values()) == pytest.approx(1.0)
        assert total == pytest.approx(
            sum(total * share for share in shares.values()),
        )

    def test_shares_follow_the_establishing_inoculum(self) -> None:
        profile = _norwalk_profile()
        agent = _coinfected(dose_a=3e4, dose_b=1e4, dpi_a=0, epoch_b=0)
        shares = agent.strain_shedding_shares(PATHOGEN, profile)
        assert shares[RESIDENT] == pytest.approx(0.75)
        assert shares[INVADER] == pytest.approx(0.25)

    def test_a_higher_shedding_lineage_takes_over_the_mixture(self) -> None:
        profile = _norwalk_profile()
        fractions = []
        for multiplier in (0.5, 1.0, 2.0, 8.0):
            agent = _coinfected(dpi_a=0, epoch_b=0, shedding_b=multiplier)
            fractions.append(
                agent.strain_shedding_shares(PATHOGEN, profile)[INVADER],
            )
        assert fractions == sorted(fractions)
        assert fractions[0] < 0.5 < fractions[-1]

    def test_single_resident_has_no_shares_to_report(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        assert agent.strain_shedding_shares(PATHOGEN, _norwalk_profile()) == {}

    def test_a_co_infected_host_emits_a_mixture_onward(self) -> None:
        core = _core(susceptibility=0.5)
        agent = _coinfected(dose_a=3e4, dose_b=1e4, dpi_a=0, epoch_b=0)
        masses = dict(core._shed_masses(agent, PATHOGEN, 100.0))
        assert masses[RESIDENT] == pytest.approx(75.0)
        assert masses[INVADER] == pytest.approx(25.0)


# ── Per-strain progression and recovery ────────────────────────────────

def _advance(agent: KorkinAgent, days: int, *, recovery_day: int = 3) -> None:
    rng = np.random.default_rng(1)
    profile = {
        **_norwalk_profile(),
        "recovery_day": recovery_day,
        "shedding_duration_days": recovery_day,
    }
    for _ in range(days):
        _advance_agent_pathogen_infections(agent, {PATHOGEN: profile}, rng)


class TestPerStrainRecovery:
    def test_single_resident_recovers_after_incubation_plus_recovery(self) -> None:
        legacy = _agent()
        legacy.infect_with_pathogen(PATHOGEN, 1e4, 0)
        tracked = _agent(2)
        tracked.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        _advance(legacy, 5)
        _advance(tracked, 5)
        assert legacy.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        assert tracked.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        assert tracked.resident_strains(PATHOGEN) == {}

    def test_a_later_lineage_holds_the_infection_open(self) -> None:
        agent = _coinfected(dpi_a=0, epoch_b=0)
        agent.resident_strains(PATHOGEN)[INVADER].time_infected = -2
        _advance(agent, 5)
        inf = agent.infections[PATHOGEN]
        assert inf["status"] == InfectionStatus.INFECTED
        assert list(agent.resident_strains(PATHOGEN)) == [INVADER]
        assert inf["time_infected"] == 5

    def test_the_pathogen_recovers_when_the_last_lineage_clears(self) -> None:
        agent = _coinfected(dpi_a=0, epoch_b=0)
        agent.resident_strains(PATHOGEN)[INVADER].time_infected = -2
        _advance(agent, 7)
        assert agent.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        assert agent.resident_strains(PATHOGEN) == {}

    def test_a_surviving_lineage_inherits_the_pathogen_level_fields(self) -> None:
        agent = _coinfected(dpi_a=0, epoch_b=0, shedding_b=2.0)
        agent.resident_strains(PATHOGEN)[INVADER].time_infected = -2
        _advance(agent, 5)
        inf = agent.infections[PATHOGEN]
        assert inf["strain_id"] == INVADER
        assert inf["strain_shedding_multiplier"] == pytest.approx(2.0)

    def test_lineage_clocks_advance_independently(self) -> None:
        agent = _coinfected(dpi_a=0, epoch_b=0)
        agent.resident_strains(PATHOGEN)[INVADER].time_infected = -1
        _advance(agent, 2, recovery_day=10)
        residents = agent.resident_strains(PATHOGEN)
        assert residents[RESIDENT].time_infected == 2
        assert residents[INVADER].time_infected == 1

    def test_untracked_infection_progresses_unchanged(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e12, 0)
        _advance(agent, 2, recovery_day=10)
        inf = agent.infections[PATHOGEN]
        assert inf["status"] == InfectionStatus.INFECTED
        assert inf["time_infected"] == 2
        assert agent.resident_strains(PATHOGEN) == {}


# ── Superinfection gate ────────────────────────────────────────────────

class TestSuperinfectionGate:
    def test_gate_is_shut_without_variant_surveillance(self) -> None:
        core = _core(cfg=None)
        assert core._superinfection_open(PATHOGEN) is False

    def test_gate_is_shut_at_zero_susceptibility(self) -> None:
        core = _core(susceptibility=0.0)
        assert core._superinfection_open(PATHOGEN) is False
        assert core._superinfection_susceptibility(PATHOGEN) == pytest.approx(0.0)

    def test_gate_opens_with_positive_susceptibility(self) -> None:
        core = _core(susceptibility=0.4)
        assert core._superinfection_open(PATHOGEN) is True
        assert core._superinfection_susceptibility(PATHOGEN) == pytest.approx(0.4)

    def test_susceptibility_is_clamped_to_the_unit_interval(self) -> None:
        assert _core(susceptibility=5.0)._superinfection_susceptibility(
            PATHOGEN,
        ) == pytest.approx(1.0)

    def test_infected_agents_stay_challengeable_only_when_the_gate_is_open(self) -> None:
        infected = _agent(3)
        infected.infect_with_pathogen(
            PATHOGEN, 1e4, 0, strain_id=RESIDENT, strain_phenotype=Phenotype(),
        )
        shut = _core(susceptibility=0.0)._get_susceptible([infected], PATHOGEN)
        open_ = _core(susceptibility=0.5)._get_susceptible([infected], PATHOGEN)
        assert shut == []
        assert open_ == [infected]

    def test_immune_agents_are_challengeable_only_with_genotype_immunity(self) -> None:
        """An escape mutant that never reaches an immune host cannot escape."""
        immune = _agent(4, immune=True)
        plain = _core(susceptibility=0.5)
        genotyped = _core(susceptibility=0.5)
        genotyped.strain_configs = {
            PATHOGEN: StrainEvolutionConfig(
                pathogen_id=PATHOGEN,
                genotypes=GENOTYPES,
                cross_immunity={GENOTYPES[0]: {GENOTYPES[1]: 0.3}},
            ),
        }
        assert plain._get_susceptible([immune], PATHOGEN) == []
        assert genotyped._get_susceptible([immune], PATHOGEN) == [immune]

    def test_flag_off_keeps_infected_agents_out_of_the_pool(self) -> None:
        infected = _agent(5)
        infected.infect_with_pathogen(PATHOGEN, 1e4, 0)
        assert _core(cfg=None)._get_susceptible([infected], PATHOGEN) == []


# ── Monotone response to the interference factor ───────────────────────

def _superinfections(susceptibility: float, *, epochs: int = 6) -> int:
    """Count lineages acquired by already-infected hosts over a short run."""
    core = _core(susceptibility=susceptibility, seed=11)
    registry = core.strain_registry
    assert registry is not None
    shedders = []
    for i in range(4):
        strain = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
        agent = _agent(i)
        agent.infect_with_pathogen(
            PATHOGEN, 1e6, 0, time_infected=2,
            strain_id=strain.strain_id, strain_phenotype=Phenotype.of(strain),
        )
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
        shedders.append(agent)
    target_strain = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
    targets = []
    for i in range(30):
        agent = _agent(100 + i)
        agent.infect_with_pathogen(
            PATHOGEN, 1e3, 0, time_infected=1,
            strain_id=target_strain.strain_id,
            strain_phenotype=Phenotype.of(target_strain),
        )
        targets.append(agent)
    agents = shedders + targets
    for epoch in range(epochs):
        core.execute_transmission(
            epoch=epoch,
            agents=agents,
            zone_pathogen_mass=dict.fromkeys(ZONES, 1e6),
            multi_pathogen_mass={PATHOGEN: dict.fromkeys(ZONES, 1e6)},
        )
    return sum(
        len(agent.resident_strains(PATHOGEN)) - 1 for agent in targets
    )


class TestSuperinfectionFrequency:
    def test_no_superinfection_at_zero_susceptibility(self) -> None:
        assert _superinfections(0.0) == 0

    def test_frequency_rises_with_susceptibility(self) -> None:
        counts = [_superinfections(s) for s in (0.0, 0.05, 0.25, 1.0)]
        assert counts == sorted(counts)
        assert counts[0] == 0
        assert counts[-1] > 0
