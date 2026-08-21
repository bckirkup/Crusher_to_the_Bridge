"""Mutation on transmission and within host (Paper 3 PR 3).

Graded sensitivity on both mutational sources independently, plus the bounds the
rest of the campaign relies on: phenotypes stay finite and in range over long
chains, ``generation`` counts transmissions only, and a rate of zero mints
nothing at all.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.strain_mutation import (  # noqa: E402
    MAX_MULTIPLIER,
    MIN_MULTIPLIER,
    MutationOperator,
    mutate_phenotype,
)
from engines.strain_state import (  # noqa: E402
    Phenotype,
    PhenotypeEffectRanges,
    StrainEvolutionConfig,
    StrainRegistry,
)
from tests.test_strain_dose_ledger import (  # noqa: E402
    VARIANT_CFG,
    ZONES,
    _core,
    _population,
    _run,
)

PATHOGEN = "norwalk_gi"


def _config(
    *,
    mutation_rate: float = 0.0,
    within_host_mutation_rate: float = 0.0,
    phenotype_mutation_fraction: float = 1.0,
    recombination_rate: float = 0.0,
) -> StrainEvolutionConfig:
    return StrainEvolutionConfig(
        pathogen_id=PATHOGEN,
        mutation_rate=mutation_rate,
        within_host_mutation_rate=within_host_mutation_rate,
        phenotype_mutation_fraction=phenotype_mutation_fraction,
        recombination_rate=recombination_rate,
        genotypes=("GII.4",),
    )


def _operator(config: StrainEvolutionConfig) -> tuple[MutationOperator, str]:
    registry = StrainRegistry()
    founder = registry.mint(PATHOGEN, genotype="GII.4")
    return MutationOperator(registry, {PATHOGEN: config}), founder.strain_id


def _chain(
    config: StrainEvolutionConfig,
    steps: int,
    *,
    seed: int = 5,
    within_host: bool = False,
) -> tuple[MutationOperator, str]:
    """Walk one lineage through ``steps`` events from a single source."""
    operator, strain_id = _operator(config)
    rng = np.random.default_rng(seed)
    for _ in range(steps):
        strain_id = (
            operator.within_host(strain_id, rng)
            if within_host
            else operator.on_transmission(strain_id, rng)
        )
    return operator, strain_id


def _profile_with(**strain_evolution: float) -> dict:
    """The real norovirus profile with its strain rates overridden."""
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = copy.deepcopy(
        next(p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN),
    )
    profile.setdefault("strain_evolution", {}).update(strain_evolution)
    return profile


class TestSensitivity:
    """Graded response: a few rates in -> a few mutation counts out."""

    @pytest.mark.parametrize("within_host", [False, True])
    def test_rate_grades_mutation_count(self, within_host: bool) -> None:
        rates = [0.0, 0.02, 0.1, 0.5]
        counts = []
        for rate in rates:
            config = (
                _config(within_host_mutation_rate=rate)
                if within_host
                else _config(mutation_rate=rate)
            )
            operator, strain_id = _chain(
                config, 200, within_host=within_host,
            )
            counts.append(operator.registry.get(strain_id).n_mutations)

        assert counts == sorted(counts), f"non-monotone in rate: {counts}"
        assert counts[0] == 0, "a zero rate must mint nothing"
        assert counts[-1] >= 10 * max(counts[1], 1), (
            f"rate looks dead across a 25x span: {counts}"
        )

    def test_sources_are_independent(self) -> None:
        """The within-host source supplies mutations with no transmission at all."""
        operator, strain_id = _chain(
            _config(mutation_rate=0.0, within_host_mutation_rate=0.5),
            100,
            within_host=True,
        )
        assert operator.registry.get(strain_id).n_mutations > 0

        transmission_only, tid = _chain(
            _config(mutation_rate=0.5, within_host_mutation_rate=0.0),
            100,
            within_host=True,
        )
        assert transmission_only.registry.get(tid).n_mutations == 0

    def test_phenotype_fraction_grades_phenotype_hits(self) -> None:
        fractions = [0.0, 0.25, 1.0]
        hits = []
        for fraction in fractions:
            operator, _ = _chain(
                _config(mutation_rate=1.0, phenotype_mutation_fraction=fraction),
                150,
            )
            hits.append(sum(
                1
                for strain in operator.registry.strains_for(PATHOGEN)
                if Phenotype.of(strain) != Phenotype()
            ))
        assert hits == sorted(hits), f"non-monotone in fraction: {hits}"
        assert hits[0] == 0, "no phenotype effects when the fraction is zero"
        assert hits[-1] > 100, f"phenotype effects look dead: {hits}"

    def test_recombination_rate_does_not_supply_mutations(self) -> None:
        """Negative control: an unrelated rate leaves mutational supply alone."""
        baseline, base_id = _chain(_config(mutation_rate=0.1), 200)
        perturbed, other_id = _chain(
            _config(mutation_rate=0.1, recombination_rate=0.9), 200,
        )
        assert (
            perturbed.registry.get(other_id).n_mutations
            == baseline.registry.get(base_id).n_mutations
        )


class TestInvariants:
    def test_phenotypes_stay_finite_and_in_range(self) -> None:
        operator, _ = _chain(
            _config(mutation_rate=1.0, phenotype_mutation_fraction=1.0), 400,
        )
        for strain in operator.registry.strains_for(PATHOGEN):
            assert MIN_MULTIPLIER <= strain.transmissibility_multiplier
            assert strain.transmissibility_multiplier <= MAX_MULTIPLIER
            assert MIN_MULTIPLIER <= strain.shedding_multiplier <= MAX_MULTIPLIER
            assert 0.0 <= strain.immune_escape <= 1.0
            assert np.isfinite(strain.incubation_modifier)

    def test_generation_counts_transmissions_only(self) -> None:
        operator, strain_id = _chain(_config(mutation_rate=1.0), 20)
        assert operator.registry.get(strain_id).generation == 20

        within, wid = _chain(
            _config(within_host_mutation_rate=1.0), 20, within_host=True,
        )
        mutant = within.registry.get(wid)
        assert mutant.generation == 0, "within-host draws are the same generation"
        assert mutant.n_mutations == 20

    def test_lineage_is_traceable_to_one_founder(self) -> None:
        operator, strain_id = _chain(_config(mutation_rate=0.3), 200)
        registry = operator.registry
        founder = registry.founders(PATHOGEN)[0]
        assert registry.lineage_root(strain_id) == founder.strain_id

    def test_neutral_mutation_mints_a_lineage_without_phenotype_change(self) -> None:
        operator, strain_id = _chain(
            _config(mutation_rate=1.0, phenotype_mutation_fraction=0.0), 5,
        )
        mutant = operator.registry.get(strain_id)
        assert mutant.n_mutations == 5
        assert Phenotype.of(mutant) == Phenotype()

    def test_unknown_parent_and_unconfigured_pathogen_pass_through(self) -> None:
        operator, strain_id = _operator(_config(mutation_rate=1.0))
        rng = np.random.default_rng(0)
        assert operator.on_transmission("", rng) == ""
        assert operator.on_transmission("no_such:9", rng) == "no_such:9"

        other = MutationOperator(operator.registry, {})
        assert other.on_transmission(strain_id, rng) == strain_id

    def test_one_effect_per_mutation(self) -> None:
        """A single mutation moves exactly one axis."""
        rng = np.random.default_rng(3)
        ranges = PhenotypeEffectRanges()
        moved = set()
        for _ in range(200):
            child = mutate_phenotype(Phenotype(), ranges, rng)
            changed = [
                name
                for name in (
                    "transmissibility_multiplier",
                    "shedding_multiplier",
                    "incubation_modifier",
                    "immune_escape",
                )
                if getattr(child, name) != getattr(Phenotype(), name)
            ]
            assert len(changed) == 1, f"expected one axis, got {changed}"
            moved.update(changed)
        assert len(moved) == 4, f"some axes are unreachable: {moved}"


class TestTransmissionCoreIntegration:
    def test_zero_rate_keeps_every_infection_on_a_founder(self) -> None:
        core = _core(cfg=VARIANT_CFG, profile=_profile_with(mutation_rate=0.0))
        agents = _population(n_shedders=2, n_susceptible=30)
        assert _run(core, agents, epochs=4), "expected transmission to occur"
        assert core.strain_registry is not None
        assert all(
            s.is_founder for s in core.strain_registry.strains_for(PATHOGEN)
        )

    def test_certain_mutation_advances_generation_along_the_chain(self) -> None:
        core = _core(
            cfg=VARIANT_CFG,
            profile=_profile_with(
                mutation_rate=1.0, phenotype_mutation_fraction=0.5,
            ),
        )
        agents = _population(n_shedders=2, n_susceptible=30)
        assert _run(core, agents, epochs=4), "expected transmission to occur"
        registry = core.strain_registry
        assert registry is not None
        derived = [
            s for s in registry.strains_for(PATHOGEN) if not s.is_founder
        ]
        assert derived, "every infection should mint a mutant at rate 1"
        for strain in derived:
            assert strain.origin == "transmission"
            assert strain.generation >= 1
            assert strain.n_mutations >= 1
            parent = registry.get(str(strain.parent_strain_id))
            assert strain.generation == parent.generation + 1

    def test_within_host_source_diversifies_seeded_infections(self) -> None:
        """Mutational supply without any transmission at all."""
        core = _core(
            cfg=VARIANT_CFG,
            profile=_profile_with(
                mutation_rate=0.0, within_host_mutation_rate=1.0,
            ),
        )
        agents = _population(n_shedders=2, n_susceptible=0)
        _run(core, agents, epochs=6)
        registry = core.strain_registry
        assert registry is not None
        mutants = [
            s
            for s in registry.strains_for(PATHOGEN)
            if s.origin == "within_host"
        ]
        assert mutants, "within-host source produced no mutants"
        assert all(s.generation == 0 for s in mutants)

    def test_within_host_off_by_default_and_rng_neutral(self) -> None:
        """Leaving the within-host rate at zero costs no RNG draws."""
        core = _core(cfg=VARIANT_CFG, profile=_profile_with(mutation_rate=0.0))
        agents = _population(n_shedders=2, n_susceptible=10)
        core.apply_within_host_mutations(agents)
        before = core.rng.bit_generator.state
        core.apply_within_host_mutations(agents)
        assert core.rng.bit_generator.state == before

    def test_flag_off_never_mutates(self) -> None:
        core = _core(cfg=None, profile=_profile_with(mutation_rate=1.0))
        agents = _population(n_shedders=2, n_susceptible=20)
        _run(core, agents, epochs=4)
        assert core.mutation_operator is None
        assert all(a.strain_id_for(PATHOGEN) is None for a in agents)


def test_zone_fixture_is_shared_with_the_ledger_suite() -> None:
    """Guard against the imported harness drifting out from under these tests."""
    assert ZONES == ["Cabin_A", "MainDining_L"]
