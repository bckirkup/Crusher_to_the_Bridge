"""
strain_mutation.py — The single mutation operator for variant surveillance.

Two sources feed one operator (plan §0 decision 2, §3 PR 3):

* **transmission** — Bernoulli(``mutation_rate``) per infection event, which
  caps mutational supply at the number of transmissions in a voyage;
* **within-host** — Bernoulli(``within_host_mutation_rate``) per
  infected-agent-epoch, default 0, which is what lets the de novo regime have
  any supply at all over seven days.

A mutation mints a new lineage; a transmission *without* one keeps the parent's
strain id, so a strain label means "this genome", not "this infection". Only a
fraction ``phenotype_mutation_fraction`` of mutations touch a phenotype axis —
the rest are neutral, still visible to sequencing but epidemiologically silent,
which is exactly the signal the typing-introduced-diversity arm reads.

``generation`` counts *transmission* generations only: a within-host mutant is
the same generation with one more mutation, so the phylogeny keeps its meaning
(see ``StrainRegistry.derive``).

Recombination (plan §3 PR 3c) is the third source and the only one with two
parents. It lives here rather than in its own module because it draws against
the same registry, rates, and RNG, and because a recombinant is a mutant with a
second parent as far as every consumer downstream is concerned.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np

from engines.strain_state import (
    PHENOTYPE_AXES,
    Phenotype,
    PhenotypeEffectRanges,
    StrainEvolutionConfig,
    StrainRegistry,
    StrainState,
)

# Multipliers are compounded across generations, so they are held inside a wide
# but finite band: an unbounded random walk eventually produces a strain that
# either cannot transmit or dominates by numerical accident alone.
MIN_MULTIPLIER = 0.05
MAX_MULTIPLIER = 20.0

TRANSMISSION_ORIGIN = "transmission"
WITHIN_HOST_ORIGIN = "within_host"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _draw(rng: np.random.Generator, bounds: tuple[float, float]) -> float:
    lo, hi = bounds
    return float(rng.uniform(lo, hi))


def _mutate_transmissibility(
    parent: Phenotype, ranges: PhenotypeEffectRanges, rng: np.random.Generator,
) -> Phenotype:
    return replace(
        parent,
        transmissibility_multiplier=_clamp(
            parent.transmissibility_multiplier * _draw(rng, ranges.transmissibility),
            MIN_MULTIPLIER,
            MAX_MULTIPLIER,
        ),
    )


def _mutate_shedding(
    parent: Phenotype, ranges: PhenotypeEffectRanges, rng: np.random.Generator,
) -> Phenotype:
    return replace(
        parent,
        shedding_multiplier=_clamp(
            parent.shedding_multiplier * _draw(rng, ranges.shedding),
            MIN_MULTIPLIER,
            MAX_MULTIPLIER,
        ),
    )


def _mutate_incubation(
    parent: Phenotype, ranges: PhenotypeEffectRanges, rng: np.random.Generator,
) -> Phenotype:
    return replace(
        parent,
        incubation_modifier=(
            parent.incubation_modifier + _draw(rng, ranges.incubation_days)
        ),
    )


def _mutate_immune_escape(
    parent: Phenotype, ranges: PhenotypeEffectRanges, rng: np.random.Generator,
) -> Phenotype:
    return replace(
        parent,
        immune_escape=_clamp(
            parent.immune_escape + _draw(rng, ranges.immune_escape), 0.0, 1.0,
        ),
    )


# One effect per axis: multiplicative on transmissibility and shedding, additive
# on incubation and immune escape — GutIBM's ``fix_mutation`` treatment, ranged
# rather than a single scalar effect size.
AXIS_EFFECTS: Mapping[
    str, Callable[[Phenotype, PhenotypeEffectRanges, np.random.Generator], Phenotype],
] = {
    "transmissibility": _mutate_transmissibility,
    "shedding": _mutate_shedding,
    "incubation": _mutate_incubation,
    "immune_escape": _mutate_immune_escape,
}


def mutate_phenotype(
    parent: Phenotype,
    ranges: PhenotypeEffectRanges,
    rng: np.random.Generator,
) -> Phenotype:
    """Apply one typed effect to one uniformly chosen axis (spec §1.2)."""
    axis = PHENOTYPE_AXES[int(rng.integers(len(PHENOTYPE_AXES)))]
    return AXIS_EFFECTS[axis](parent, ranges, rng)


def crossover_phenotype(
    recipient: Phenotype,
    donor: Phenotype,
    rng: np.random.Generator,
) -> Phenotype:
    """Uniform crossover: each axis independently from one parent (spec §1.5).

    Uniform rather than single-crossover because CTB carries no locus order —
    the four axes are unlinked by construction, so any crossover model that
    needs a genome coordinate would be inventing one.
    """
    def pick(mine: float, theirs: float) -> float:
        return mine if rng.random() < 0.5 else theirs

    return Phenotype(
        transmissibility_multiplier=pick(
            recipient.transmissibility_multiplier,
            donor.transmissibility_multiplier,
        ),
        shedding_multiplier=pick(
            recipient.shedding_multiplier, donor.shedding_multiplier,
        ),
        incubation_modifier=pick(
            recipient.incubation_modifier, donor.incubation_modifier,
        ),
        immune_escape=pick(recipient.immune_escape, donor.immune_escape),
    )


@dataclass(frozen=True)
class MutationOperator:
    """Draws mutations for both sources against one registry.

    Holds no state of its own: the registry owns lineage, the configs own rates,
    and the caller owns the RNG — so a run's mutational history is reproducible
    from the seed alone.
    """

    registry: StrainRegistry
    configs: Mapping[str, StrainEvolutionConfig]

    def config_for(self, pathogen_id: str) -> StrainEvolutionConfig | None:
        return self.configs.get(pathogen_id)

    def on_transmission(
        self,
        parent_strain_id: str,
        rng: np.random.Generator,
        *,
        source_location: str | None = None,
    ) -> str:
        """Strain the recipient acquires: the parent, or a mutated child of it.

        Mutation is drawn once per infection event, so supply scales with the
        number of transmissions rather than with time.
        """
        return self._draw(
            parent_strain_id, rng, TRANSMISSION_ORIGIN, source_location,
        )

    def within_host(
        self,
        strain_id: str,
        rng: np.random.Generator,
        *,
        source_location: str | None = None,
    ) -> str:
        """Strain an already-infected host carries after one epoch of replication."""
        return self._draw(strain_id, rng, WITHIN_HOST_ORIGIN, source_location)

    def recombine(
        self,
        resident_strain_ids: Sequence[str],
        rng: np.random.Generator,
        *,
        source_location: str | None = None,
    ) -> tuple[str, str] | None:
        """One recombination draw for a co-infected host.

        Returns ``(replaced_strain_id, recombinant_strain_id)`` on a hit and
        ``None`` otherwise, so the caller substitutes the recombinant for the
        lineage it arose in and leaves the donor resident — GutIBM's
        donor/recipient conjugation event with both parents inside one host.
        The Bernoulli is drawn once per co-infected host-epoch and the parent
        pair only on a hit, so an epoch in which nothing recombines costs the
        same RNG draws whatever the resident count is.
        """
        known = tuple(sid for sid in resident_strain_ids if sid in self.registry)
        if len(known) < 2:
            return None
        config = self.configs.get(self.registry.get(known[0]).pathogen_id)
        if config is None or config.recombination_rate <= 0.0:
            return None
        if rng.random() >= config.recombination_rate:
            return None
        first, second = rng.choice(len(known), size=2, replace=False)
        recipient = self.registry.get(known[int(first)])
        donor = self.registry.get(known[int(second)])
        if recipient.pathogen_id != donor.pathogen_id:
            return None
        child = self.registry.recombine(
            recipient,
            donor,
            genotype=(
                recipient.genotype if rng.random() < 0.5 else donor.genotype
            ),
            phenotype=crossover_phenotype(
                Phenotype.of(recipient), Phenotype.of(donor), rng,
            ),
            source_location=source_location,
        )
        return recipient.strain_id, child.strain_id

    def _rate(self, config: StrainEvolutionConfig, origin: str) -> float:
        if origin == TRANSMISSION_ORIGIN:
            return config.mutation_rate
        return config.within_host_mutation_rate

    def _draw(
        self,
        parent_strain_id: str,
        rng: np.random.Generator,
        origin: str,
        source_location: str | None,
    ) -> str:
        if not parent_strain_id or parent_strain_id not in self.registry:
            return parent_strain_id
        parent = self.registry.get(parent_strain_id)
        config = self.configs.get(parent.pathogen_id)
        if config is None:
            return parent_strain_id
        rate = self._rate(config, origin)
        if rate <= 0.0 or rng.random() >= rate:
            return parent_strain_id
        return self._mutant(parent, config, rng, origin, source_location).strain_id

    def _mutant(
        self,
        parent: StrainState,
        config: StrainEvolutionConfig,
        rng: np.random.Generator,
        origin: str,
        source_location: str | None,
    ) -> StrainState:
        """Register one mutant child, phenotype-affecting or neutral."""
        phenotype = Phenotype.of(parent)
        if rng.random() < config.phenotype_mutation_fraction:
            phenotype = mutate_phenotype(phenotype, config.effect_ranges, rng)
        return self.registry.derive(
            parent,
            origin=origin,
            source_location=source_location,
            mutations_added=1,
            phenotype=phenotype,
        )
