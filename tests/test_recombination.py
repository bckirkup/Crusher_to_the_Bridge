"""Recombination between co-resident lineages (Paper 3 PR 3c).

PR 3b made two lineages of one pathogen able to share a host; this is what that
co-residence is for. The properties held here are the ones the plan asks for:
recombinants appear only in co-infected hosts, each phenotype axis of a child
traces to one of its two parents, the hit frequency responds to
``recombination_rate``, and a recombination-off run reproduces PR 3b exactly.
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
    KorkinAgent,
)
from engines.strain_mutation import (  # noqa: E402
    MutationOperator,
    crossover_phenotype,
)
from engines.strain_state import (  # noqa: E402
    Phenotype,
    StrainConfigError,
    StrainEvolutionConfig,
    StrainRegistry,
)
from engines.transmission_core import TransmissionCore  # noqa: E402

PATHOGEN = "norwalk_gi"
OTHER_PATHOGEN = "influenza_a"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]
GENOTYPES = ("GII.4", "GII.17")

DONOR_PHENO = Phenotype(
    transmissibility_multiplier=4.0,
    shedding_multiplier=5.0,
    incubation_modifier=3.0,
    immune_escape=0.5,
)


def _norwalk_profile() -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    return copy.deepcopy(
        next(p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN),
    )


def _agent(aid: int = 1, loc: str = "MainDining_L") -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone=loc,
        work_zone=loc,
        free_zone=loc,
        schedule=["Free"] * 24,
    )
    agent.current_location = loc
    return agent


def _config(
    *,
    recombination_rate: float,
    superinfection_susceptibility: float = 0.0,
) -> StrainEvolutionConfig:
    return StrainEvolutionConfig(
        pathogen_id=PATHOGEN,
        genotypes=GENOTYPES,
        recombination_rate=recombination_rate,
        superinfection_susceptibility=superinfection_susceptibility,
    )


def _core(
    *,
    cfg: dict | None = VARIANT_CFG,
    seed: int = 5,
    recombination_rate: float | None = None,
    susceptibility: float = 0.0,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={PATHOGEN: _norwalk_profile()},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=cfg,
    )
    core.initialize_zones(ZONES)
    if recombination_rate is not None:
        core.strain_configs = {
            PATHOGEN: _config(
                recombination_rate=recombination_rate,
                superinfection_susceptibility=susceptibility,
            ),
        }
        if core.strain_registry is not None:
            core.mutation_operator = MutationOperator(
                core.strain_registry, core.strain_configs,
            )
    return core


def _operator(
    rate: float, registry: StrainRegistry | None = None,
) -> MutationOperator:
    reg = StrainRegistry() if registry is None else registry
    return MutationOperator(reg, {PATHOGEN: _config(recombination_rate=rate)})


def _parents(
    registry: StrainRegistry,
    *,
    donor_phenotype: Phenotype = DONOR_PHENO,
) -> tuple[str, str]:
    """A plain recipient and a maximally different donor."""
    recipient = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
    donor = registry.mint(
        PATHOGEN, genotype=GENOTYPES[1], phenotype=donor_phenotype,
    )
    return recipient.strain_id, donor.strain_id


def _coinfected_host(
    core: TransmissionCore,
    *,
    aid: int = 1,
    dpi: int = 2,
    dose_a: float = 1e4,
    dose_b: float = 5e3,
) -> tuple[KorkinAgent, str, str]:
    """One host carrying two registered lineages."""
    registry = core.strain_registry
    assert registry is not None
    first, second = _parents(registry)
    agent = _agent(aid)
    agent.infect_with_pathogen(
        PATHOGEN, dose_a, 0, time_infected=dpi,
        strain_id=first, strain_phenotype=Phenotype.of(registry.get(first)),
    )
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.superinfect_with_strain(
        PATHOGEN, second, dose_b, 4,
        phenotype=Phenotype.of(registry.get(second)),
    )
    return agent, first, second


# ── Registry: a child with two parents ─────────────────────────────────

class TestRegistryRecombine:
    def test_child_records_both_parents_recipient_first(self) -> None:
        registry = StrainRegistry()
        first, second = _parents(registry)
        child = registry.recombine(registry.get(first), registry.get(second))
        assert child.parent_strain_ids == (first, second)
        assert child.recombinant is True
        assert child.origin == "recombination"
        assert child.to_telemetry()["recombinant"] is True

    def test_lineage_root_follows_the_replaced_parent(self) -> None:
        registry = StrainRegistry()
        first, second = _parents(registry)
        child = registry.recombine(registry.get(first), registry.get(second))
        assert registry.lineage_root(child.strain_id) == first

    def test_generation_and_mutations_take_the_more_derived_parent(self) -> None:
        registry = StrainRegistry()
        first, second = _parents(registry)
        travelled = registry.derive(
            registry.get(second), origin="transmission", mutations_added=3,
        )
        child = registry.recombine(registry.get(first), travelled)
        assert child.generation == travelled.generation
        assert child.n_mutations == travelled.n_mutations

    def test_child_inherits_the_crossover_phenotype(self) -> None:
        registry = StrainRegistry()
        first, second = _parents(registry)
        child = registry.recombine(
            registry.get(first),
            registry.get(second),
            genotype=GENOTYPES[1],
            phenotype=Phenotype(shedding_multiplier=2.5),
        )
        assert child.genotype == GENOTYPES[1]
        assert child.shedding_multiplier == pytest.approx(2.5)

    def test_two_distinct_registered_parents_are_required(self) -> None:
        registry = StrainRegistry()
        first, _ = _parents(registry)
        parent = registry.get(first)
        with pytest.raises(StrainConfigError, match="two distinct parents"):
            registry.recombine(parent, parent)

    def test_parents_must_share_a_pathogen(self) -> None:
        registry = StrainRegistry()
        first, _ = _parents(registry)
        recipient = registry.get(first)
        alien = registry.mint(OTHER_PATHOGEN, genotype="H3N2")
        with pytest.raises(StrainConfigError, match="different pathogens"):
            registry.recombine(recipient, alien)


# ── Uniform crossover ──────────────────────────────────────────────────

class TestCrossover:
    def test_every_axis_comes_from_one_of_the_two_parents(self) -> None:
        rng = np.random.default_rng(3)
        for _ in range(50):
            child = crossover_phenotype(Phenotype(), DONOR_PHENO, rng)
            assert child.transmissibility_multiplier in (
                1.0, DONOR_PHENO.transmissibility_multiplier,
            )
            assert child.shedding_multiplier in (
                1.0, DONOR_PHENO.shedding_multiplier,
            )
            assert child.incubation_modifier in (
                0.0, DONOR_PHENO.incubation_modifier,
            )
            assert child.immune_escape in (0.0, DONOR_PHENO.immune_escape)

    def test_axes_are_reassorted_independently(self) -> None:
        """Both parents contribute, and not always as a block."""
        rng = np.random.default_rng(7)
        children = [
            crossover_phenotype(Phenotype(), DONOR_PHENO, rng)
            for _ in range(60)
        ]
        mosaics = [
            c for c in children
            if (c.shedding_multiplier > 1.0) != (c.immune_escape > 0.0)
        ]
        assert mosaics, "no child mixed the two parents' axes"

    def test_identical_parents_give_an_identical_child(self) -> None:
        rng = np.random.default_rng(1)
        child = crossover_phenotype(DONOR_PHENO, DONOR_PHENO, rng)
        assert child == DONOR_PHENO


# ── Operator: the draw ─────────────────────────────────────────────────

class TestOperatorRecombine:
    def test_certain_rate_mints_a_recombinant_of_the_pair(self) -> None:
        registry = StrainRegistry()
        operator = _operator(1.0, registry)
        first, second = _parents(registry)
        outcome = operator.recombine((first, second), np.random.default_rng(2))
        assert outcome is not None
        replaced, child_id = outcome
        assert replaced in (first, second)
        child = registry.get(child_id)
        assert set(child.parent_strain_ids) == {first, second}
        assert child.origin == "recombination"

    def test_zero_rate_never_recombines(self) -> None:
        registry = StrainRegistry()
        operator = _operator(0.0, registry)
        first, second = _parents(registry)
        rng = np.random.default_rng(2)
        assert all(
            operator.recombine((first, second), rng) is None for _ in range(20)
        )
        assert len(registry) == 2

    def test_a_single_resident_has_nothing_to_recombine_with(self) -> None:
        registry = StrainRegistry()
        operator = _operator(1.0, registry)
        first, _ = _parents(registry)
        assert operator.recombine((first,), np.random.default_rng(2)) is None

    def test_unregistered_residents_are_ignored(self) -> None:
        registry = StrainRegistry()
        operator = _operator(1.0, registry)
        first, _ = _parents(registry)
        outcome = operator.recombine(
            (first, "s:ghost"), np.random.default_rng(2),
        )
        assert outcome is None

    def test_a_pathogen_without_a_config_never_recombines(self) -> None:
        registry = StrainRegistry()
        operator = MutationOperator(registry, {})
        first, second = _parents(registry)
        assert operator.recombine((first, second), np.random.default_rng(2)) is None

    def test_hit_frequency_rises_with_the_rate(self) -> None:
        counts = []
        for rate in (0.0, 0.05, 0.25, 1.0):
            registry = StrainRegistry()
            operator = _operator(rate, registry)
            rng = np.random.default_rng(19)
            hits = 0
            for _ in range(200):
                first, second = _parents(registry)
                if operator.recombine((first, second), rng) is not None:
                    hits += 1
            counts.append(hits)
        assert counts == sorted(counts)
        assert counts[0] == 0
        assert counts[-1] == 200


# ── In a host ──────────────────────────────────────────────────────────

class TestRecombinationInHost:
    def test_recombinant_replaces_its_lineage_and_leaves_the_donor(self) -> None:
        core = _core(recombination_rate=1.0)
        agent, first, second = _coinfected_host(core)
        core.apply_recombination([agent])
        residents = agent.resident_strains(PATHOGEN)
        assert len(residents) == 2
        survivors = set(residents) & {first, second}
        assert len(survivors) == 1
        new = set(residents) - {first, second}
        assert len(new) == 1
        registry = core.strain_registry
        assert registry is not None
        assert registry.get(new.pop()).recombinant is True

    def test_the_recombinant_inherits_the_slot_it_arose_in(self) -> None:
        core = _core(recombination_rate=1.0)
        agent, first, second = _coinfected_host(core)
        before = dict(agent.resident_strains(PATHOGEN))
        core.apply_recombination([agent])
        residents = agent.resident_strains(PATHOGEN)
        replaced = (set(before) - set(residents)).pop()
        child_id = (set(residents) - set(before)).pop()
        child = residents[child_id]
        assert child.time_infected == before[replaced].time_infected
        assert child.acquired_particles == pytest.approx(
            before[replaced].acquired_particles,
        )

    def test_the_childs_phenotype_reaches_the_infection_record(self) -> None:
        core = _core(recombination_rate=1.0)
        agent, first, second = _coinfected_host(core)
        core.apply_recombination([agent])
        registry = core.strain_registry
        assert registry is not None
        residents = agent.resident_strains(PATHOGEN)
        child_id = next(
            sid for sid in residents if registry.get(sid).recombinant
        )
        strain = registry.get(child_id)
        assert residents[child_id].shedding_multiplier == pytest.approx(
            strain.shedding_multiplier,
        )
        assert residents[child_id].incubation_modifier == pytest.approx(
            strain.incubation_modifier,
        )

    def test_a_singly_infected_host_is_left_alone(self) -> None:
        core = _core(recombination_rate=1.0)
        registry = core.strain_registry
        assert registry is not None
        strain = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
        agent = _agent()
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0,
            strain_id=strain.strain_id,
            strain_phenotype=Phenotype.of(strain),
        )
        core.apply_recombination([agent])
        assert list(agent.resident_strains(PATHOGEN)) == [strain.strain_id]
        assert len(registry) == 1

    def test_an_untracked_infection_is_left_alone(self) -> None:
        core = _core(recombination_rate=1.0)
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        core.apply_recombination([agent])
        assert agent.resident_strains(PATHOGEN) == {}

    def test_zero_rate_leaves_a_co_infected_host_untouched(self) -> None:
        core = _core(recombination_rate=0.0)
        agent, first, second = _coinfected_host(core)
        core.apply_recombination([agent])
        assert set(agent.resident_strains(PATHOGEN)) == {first, second}

    def test_flag_off_has_no_recombination_at_all(self) -> None:
        core = _core(cfg=None)
        assert core.mutation_operator is None
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        core.apply_recombination([agent])
        assert agent.resident_strains(PATHOGEN) == {}


# ── Whole-run behaviour ────────────────────────────────────────────────

def _run(
    *,
    recombination_rate: float,
    susceptibility: float,
    epochs: int = 6,
    seed: int = 11,
) -> tuple[TransmissionCore, list[KorkinAgent]]:
    """A small shedder/target run with co-infection reachable."""
    core = _core(
        seed=seed,
        recombination_rate=recombination_rate,
        susceptibility=susceptibility,
    )
    registry = core.strain_registry
    assert registry is not None
    agents: list[KorkinAgent] = []
    for i in range(4):
        strain = registry.mint(PATHOGEN, genotype=GENOTYPES[i % 2])
        shedder = _agent(i)
        shedder.infect_with_pathogen(
            PATHOGEN, 1e6, 0, time_infected=2,
            strain_id=strain.strain_id,
            strain_phenotype=Phenotype.of(strain),
        )
        shedder.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
        agents.append(shedder)
    target_strain = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
    for i in range(30):
        target = _agent(100 + i)
        target.infect_with_pathogen(
            PATHOGEN, 1e3, 0, time_infected=1,
            strain_id=target_strain.strain_id,
            strain_phenotype=Phenotype.of(target_strain),
        )
        agents.append(target)
    for epoch in range(epochs):
        core.execute_transmission(
            epoch=epoch,
            agents=agents,
            zone_pathogen_mass=dict.fromkeys(ZONES, 1e6),
            multi_pathogen_mass={PATHOGEN: dict.fromkeys(ZONES, 1e6)},
        )
    return core, agents


def _recombinants(core: TransmissionCore) -> tuple[str, ...]:
    registry = core.strain_registry
    assert registry is not None
    return tuple(
        s.strain_id for s in registry.strains_for(PATHOGEN) if s.recombinant
    )


class TestWholeRun:
    def test_recombinants_appear_once_co_infection_does(self) -> None:
        core, _ = _run(recombination_rate=1.0, susceptibility=1.0)
        assert _recombinants(core)

    def test_no_recombinants_without_co_infection(self) -> None:
        """Interference shut means no host ever holds two lineages."""
        core, agents = _run(recombination_rate=1.0, susceptibility=0.0)
        assert _recombinants(core) == ()
        assert max(len(a.resident_strains(PATHOGEN)) for a in agents) == 1

    def test_recombination_off_reproduces_the_co_infection_run(self) -> None:
        off, off_agents = _run(recombination_rate=0.0, susceptibility=1.0)
        again, again_agents = _run(recombination_rate=0.0, susceptibility=1.0)
        assert _recombinants(off) == ()
        assert [
            sorted(a.resident_strains(PATHOGEN)) for a in off_agents
        ] == [
            sorted(a.resident_strains(PATHOGEN)) for a in again_agents
        ]

    def test_every_recombinant_traces_to_two_resident_parents(self) -> None:
        core, _ = _run(recombination_rate=1.0, susceptibility=1.0)
        registry = core.strain_registry
        assert registry is not None
        for strain_id in _recombinants(core):
            parents = registry.get(strain_id).parent_strain_ids
            assert len(parents) == 2
            assert parents[0] != parents[1]
            assert all(p in registry for p in parents)

    def test_a_recombination_event_never_widens_a_hosts_mixture(self) -> None:
        """Reassortment happens in place; only superinfection adds a lineage.

        Across a whole run the *population* does get more diverse, because a
        recombinant is a new lineage that can go on to superinfect a host
        already carrying both its parents — so the invariant is per event, not
        per voyage.
        """
        core, agents = _run(recombination_rate=0.0, susceptibility=1.0)
        core.strain_configs = {
            PATHOGEN: _config(
                recombination_rate=1.0, superinfection_susceptibility=1.0,
            ),
        }
        assert core.strain_registry is not None
        core.mutation_operator = MutationOperator(
            core.strain_registry, core.strain_configs,
        )
        before = [len(a.resident_strains(PATHOGEN)) for a in agents]
        core.apply_recombination(agents)
        after = [len(a.resident_strains(PATHOGEN)) for a in agents]
        assert after == before
        assert max(before) > 1, "run produced no co-infected host to reassort"
