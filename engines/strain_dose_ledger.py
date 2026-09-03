"""Strain-resolved dose accounting for the six transmission pathways.

CTB pools dose per ``(agent, pathogen)`` and then draws infection once, so a
transmission event has no source and no inheritable strain (see
``docs/paper3/variant_surveillance_plan.md`` §1). This module adds the missing ledger:
each pathway attributes its dose to the strains that emitted it, the summed dose
still drives the dose-response draw, and on infection the parent is drawn from
the strain-weighted contributions.

Two invariants the transmission core relies on:

* **Dose conservation.** The strain-resolved doses for a pathway sum to that
  pathway's pooled dose, so infection probability is unchanged by attribution.
* **Emission-side transmissibility.** ``transmissibility_multiplier`` scales a
  strain's *emitted* contribution (plan §0 decision 3), which for the linear
  pathway kernels is equivalent to scaling the recipient's dose by the
  emission-weighted mean multiplier — exposed as ``EmissionMix.emission_factor``.
  With every multiplier at 1.0 the factor is exactly 1.0.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

# A dose contributor: the strain, and the shedder when the pathway knows it
# (reservoir pathways attribute a strain without a named source agent).
Contributor = tuple[str, int | None]

NO_SOURCE_AGENT: int | None = None

# Pseudo-strain holding pool mass whose lineage is below the resolution floor.
# It is never registered, so an acquisition drawn from it has no callable parent
# — which is what a sub-detection-limit pool fraction means for an assay.
UNRESOLVED_STRAIN = "unresolved"
# Genotype labels that cannot be reported as resolved lineages.
UNREPORTABLE_GENOTYPES = frozenset({"", UNRESOLVED_STRAIN})


class EmissionContribution(NamedTuple):
    """One source's emitted mass and its strain's transmissibility."""

    strain_id: str
    source_agent_id: int | None
    emitted: float
    transmissibility: float = 1.0


@dataclass(frozen=True)
class EmissionMix:
    """Normalized strain shares of an exposure, plus its emission scaling.

    ``shares`` are transmissibility-weighted (what a parent draw needs);
    ``emission_factor`` is the emission-weighted mean multiplier (what the
    recipient's dose is scaled by).
    """

    shares: Mapping[Contributor, float]
    emission_factor: float

    @property
    def contributors(self) -> tuple[Contributor, ...]:
        return tuple(self.shares)


def build_emission_mix(
    contributions: Iterable[EmissionContribution],
) -> EmissionMix | None:
    """Emission mix for one exposure, or ``None`` when nothing was emitted."""
    entries = [c for c in contributions if c.emitted > 0.0]
    total = sum(c.emitted for c in entries)
    if total <= 0.0:
        return None

    weighted: dict[Contributor, float] = {}
    factor = 0.0
    for contribution in entries:
        weight = (contribution.emitted / total) * contribution.transmissibility
        if weight <= 0.0:
            continue
        key: Contributor = (contribution.strain_id, contribution.source_agent_id)
        weighted[key] = weighted.get(key, 0.0) + weight
        factor += weight
    if factor <= 0.0:
        return None
    return EmissionMix(
        shares={key: weight / factor for key, weight in weighted.items()},
        emission_factor=factor,
    )


def single_strain_mix(
    strain_id: str,
    *,
    source_agent_id: int | None = NO_SOURCE_AGENT,
    transmissibility: float = 1.0,
) -> EmissionMix:
    """Mix for an exposure with one known strain (e.g. a reservoir founder)."""
    return EmissionMix(
        shares={(strain_id, source_agent_id): 1.0},
        emission_factor=transmissibility,
    )


class StrainDoseLedger:
    """Strain-resolved dose per agent per pathway, for one pathogen pass.

    Kept pathway-resolved because ``route_efficiency_multipliers`` rescales
    pathways after the fact; folding early would apply the wrong weight.
    """

    def __init__(self) -> None:
        self._doses: dict[int, dict[str, dict[Contributor, float]]] = {}

    def add(
        self,
        agent_id: int,
        pathway: str,
        dose: float,
        mix: EmissionMix,
    ) -> None:
        """Split ``dose`` over ``mix``'s contributors for one exposure."""
        if dose <= 0.0:
            return
        by_pathway = self._doses.setdefault(agent_id, {})
        bucket = by_pathway.setdefault(pathway, {})
        for contributor, share in mix.shares.items():
            bucket[contributor] = bucket.get(contributor, 0.0) + dose * share

    def is_empty(self) -> bool:
        return not self._doses

    def pathway_doses(self, agent_id: int) -> Mapping[str, Mapping[Contributor, float]]:
        """Raw per-pathway strain doses (pre route weighting)."""
        return self._doses.get(agent_id, {})

    def agent_ids(self) -> tuple[int, ...]:
        return tuple(self._doses)

    def strain_doses(
        self,
        agent_id: int,
        pathway_weights: Mapping[str, float] | None = None,
    ) -> dict[Contributor, float]:
        """Contributor doses summed over pathways, each route-weighted."""
        totals: dict[Contributor, float] = {}
        for pathway, bucket in self._doses.get(agent_id, {}).items():
            weight = 1.0 if pathway_weights is None else float(
                pathway_weights.get(pathway, 1.0),
            )
            if weight <= 0.0:
                continue
            for contributor, dose in bucket.items():
                totals[contributor] = totals.get(contributor, 0.0) + dose * weight
        return totals


@dataclass(frozen=True)
class DoseAttribution:
    """A ledger plus the mix an exposure should be attributed to."""

    ledger: StrainDoseLedger
    mix: EmissionMix

    def record(self, agent_id: int, pathway: str, dose: float) -> None:
        self.ledger.add(agent_id, pathway, dose, self.mix)

    @property
    def emission_factor(self) -> float:
        return self.mix.emission_factor


def attribution(
    ledger: StrainDoseLedger | None,
    mix: EmissionMix | None,
) -> DoseAttribution | None:
    """Pair a ledger with a mix, or ``None`` when either is absent."""
    if ledger is None or mix is None:
        return None
    return DoseAttribution(ledger=ledger, mix=mix)


def draw_contributor(
    shares: Mapping[Contributor, float],
    rng: np.random.Generator,
) -> Contributor | None:
    """Draw one contributor with probability proportional to its dose share."""
    total = sum(shares.values())
    if total <= 0.0:
        return None
    threshold = float(rng.random()) * total
    cumulative = 0.0
    contributor: Contributor | None = None
    for contributor, weight in shares.items():
        cumulative += weight
        if cumulative >= threshold:
            return contributor
    return contributor


@dataclass
class ReservoirComposition:
    """Strain composition of lagged reservoirs (air, surfaces, food, environment).

    Pool *masses* stay where they are in the transmission core; this tracks only
    who deposited what, so a pickup epochs later is attributed to the strains
    still present rather than to whoever happens to be shedding now. Decay is
    applied with the same factor as the pool it shadows, which is what makes
    older deposits fade relative to newer ones.

    Only *shares* are read (through :meth:`mix`), so a composition tracks its
    pool up to a constant: any uniform rescaling of a pool — external CONTAM
    transport included — leaves attribution unchanged.
    """

    _mass: dict[str, dict[Contributor, float]] = field(default_factory=dict)

    @staticmethod
    def key(kind: str, pathogen_id: str, zone: str) -> str:
        """Composition key for one reservoir (``kind`` separates food from surfaces)."""
        return f"{kind}|{pathogen_id}|{zone}"

    def deposit(
        self,
        key: str,
        contributor: Contributor,
        mass: float,
    ) -> None:
        if mass <= 0.0:
            return
        bucket = self._mass.setdefault(key, {})
        bucket[contributor] = bucket.get(contributor, 0.0) + mass

    def decay(self, factor: float, key: str | None = None) -> None:
        """Scale one key's composition, or every key's when ``key`` is None."""
        keys: Sequence[str] = (key,) if key is not None else tuple(self._mass)
        self._scale(factor, keys)

    def decay_kind(self, factor: float, kind: str) -> None:
        """Scale every reservoir of one kind, e.g. all surface pools."""
        prefix = f"{kind}|"
        self._scale(factor, [k for k in self._mass if k.startswith(prefix)])

    def _scale(self, factor: float, keys: Sequence[str]) -> None:
        scale = max(0.0, float(factor))
        for name in keys:
            bucket = self._mass.get(name)
            if not bucket:
                continue
            for contributor in bucket:
                bucket[contributor] *= scale

    def contributors(self, key: str) -> Mapping[Contributor, float]:
        return self._mass.get(key, {})

    def keys(self) -> tuple[str, ...]:
        return tuple(self._mass)

    def strain_ids(self) -> set[str]:
        """Every strain still present in any reservoir."""
        return {
            strain_id
            for bucket in self._mass.values()
            for strain_id, _ in bucket
        }

    def total_mass(self, key: str) -> float:
        """Mass a reservoir's composition accounts for, unresolved bin included."""
        return sum(self._mass.get(key, {}).values())

    def drop_empty(self, threshold: float = 0.0) -> None:
        """Forget contributors that have decayed to nothing."""
        for name in tuple(self._mass):
            bucket = self._mass[name]
            for contributor in tuple(bucket):
                if bucket[contributor] <= threshold:
                    del bucket[contributor]
            if not bucket:
                del self._mass[name]

    def lump(self, min_fraction: float, key: str | None = None) -> None:
        """Collapse the sub-floor tail of a reservoir (GutIBM's lumping).

        Without a floor a reservoir accumulates one entry per
        ``(strain, depositor)`` pair, so state grows with the product of
        lineages and hosts. Below the floor the depositor is forgotten first
        (the lineage survives, its provenance does not), and a lineage still
        below the floor moves to :data:`UNRESOLVED_STRAIN`: a pool assay cannot
        call a variant under its limit of detection, so such mass is real but
        unattributable. Mass is therefore conserved exactly — only who gets
        credited for it changes — and the largest lineage is always kept, so a
        reservoir never loses its identity just because its diversity is flat.
        """
        if min_fraction <= 0.0:
            return
        names: Sequence[str] = (key,) if key is not None else tuple(self._mass)
        for name in names:
            bucket = self._mass.get(name)
            if bucket:
                self._mass[name] = _lumped(bucket, min_fraction)

    def mix(
        self,
        key: str,
        transmissibility: Mapping[str, float] | None = None,
    ) -> EmissionMix | None:
        """Emission mix of the reservoir's current composition."""
        multipliers = transmissibility or {}
        return build_emission_mix(
            EmissionContribution(
                strain_id=strain_id,
                source_agent_id=source_agent_id,
                emitted=mass,
                transmissibility=float(multipliers.get(strain_id, 1.0)),
            )
            for (strain_id, source_agent_id), mass in self.contributors(key).items()
        )


def _lumped(
    bucket: Mapping[Contributor, float],
    min_fraction: float,
) -> dict[Contributor, float]:
    """One reservoir's composition with its sub-floor tail collapsed."""
    total = sum(bucket.values())
    if total <= 0.0:
        return dict(bucket)
    floor = total * min_fraction
    by_strain: dict[str, float] = {}
    for (strain_id, _), mass in bucket.items():
        by_strain[strain_id] = by_strain.get(strain_id, 0.0) + mass
    kept = {sid for sid, mass in by_strain.items() if mass >= floor}
    if not kept:
        kept = {max(by_strain, key=lambda sid: by_strain[sid])}

    lumped: dict[Contributor, float] = {}
    for (strain_id, agent_id), mass in bucket.items():
        if strain_id in kept:
            resolved = agent_id if mass >= floor else NO_SOURCE_AGENT
            contributor: Contributor = (strain_id, resolved)
        else:
            contributor = (UNRESOLVED_STRAIN, NO_SOURCE_AGENT)
        lumped[contributor] = lumped.get(contributor, 0.0) + mass
    return lumped
