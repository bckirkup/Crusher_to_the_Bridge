"""
strain_state.py — Heritable strain identity for variant surveillance (Paper 3).

Data layer only: this module owns strain identity, per-pathogen evolution
parameters, and the lineage census. It does not mutate, transmit, or infect —
those seams arrive with the strain-resolved dose ledger and the mutation
operator (see ``docs/variant_surveillance_plan.md`` §3).

Per-pathogen parameters live in an optional ``strain_evolution`` block on each
pathogen profile (``data/pathogens/*.json``); absent block means the pathogen
has no strain structure and every consumer falls back to legacy behaviour.

Strain identity is deliberately origin-agnostic: a strain minted for a shore
community or a port reservoir is the same ``StrainState`` with a different
``origin``/``source_location``, so the shore model (plan §5 PR 11b) reuses this
registry rather than carrying a parallel notion of lineage.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

# Origins a strain can be minted from. ``shore_import`` covers strains that
# entered the ship already formed (embarkation, port reservoir, shore model).
STRAIN_ORIGINS = frozenset(
    {"founder", "transmission", "within_host", "recombination", "shore_import"},
)

SHIP_LOCATION = "ship"

# Phenotype axes a single mutation can act on (spec §1.2).
PHENOTYPE_AXES: tuple[str, ...] = (
    "transmissibility",
    "shedding",
    "incubation",
    "immune_escape",
)


class StrainConfigError(ValueError):
    """Raised when a ``strain_evolution`` block is structurally invalid."""


def _require_unit_interval(name: str, value: float) -> float:
    val = float(value)
    if val < 0.0 or val > 1.0:
        raise StrainConfigError(f"{name} must be in [0,1], got {val}")
    return val


def _require_positive(name: str, value: float) -> float:
    val = float(value)
    if val <= 0.0:
        raise StrainConfigError(f"{name} must be positive, got {val}")
    return val


@dataclass(frozen=True)
class StrainState:
    """One heritable lineage label plus its phenotype offsets (spec §1.1).

    ``transmissibility_multiplier`` scales this strain's *emitted* contribution
    to a recipient's dose, not the recipient's dose-response — a mixed exposure
    otherwise gets the wrong marginal (plan §0 decision 3).
    """

    strain_id: str
    pathogen_id: str
    genotype: str = ""
    parent_strain_ids: tuple[str, ...] = ()
    generation: int = 0
    n_mutations: int = 0
    transmissibility_multiplier: float = 1.0
    shedding_multiplier: float = 1.0
    incubation_modifier: float = 0.0
    immune_escape: float = 0.0
    origin: str = "founder"
    source_location: str = SHIP_LOCATION

    def __post_init__(self) -> None:
        if not self.strain_id:
            raise StrainConfigError("strain_id must be non-empty")
        if not self.pathogen_id:
            raise StrainConfigError("pathogen_id must be non-empty")
        if self.origin not in STRAIN_ORIGINS:
            raise StrainConfigError(
                f"unknown strain origin {self.origin!r}; "
                f"expected one of {sorted(STRAIN_ORIGINS)}",
            )
        if self.generation < 0:
            raise StrainConfigError(f"generation must be >= 0, got {self.generation}")
        if self.n_mutations < 0:
            raise StrainConfigError(f"n_mutations must be >= 0, got {self.n_mutations}")
        _require_positive("transmissibility_multiplier", self.transmissibility_multiplier)
        _require_positive("shedding_multiplier", self.shedding_multiplier)
        _require_unit_interval("immune_escape", self.immune_escape)
        if self.origin == "recombination" and len(self.parent_strain_ids) != 2:
            raise StrainConfigError(
                "recombinant strains must record exactly two parents, "
                f"got {len(self.parent_strain_ids)}",
            )

    @property
    def recombinant(self) -> bool:
        """True when this strain arose from two parents."""
        return len(self.parent_strain_ids) == 2

    @property
    def parent_strain_id(self) -> str | None:
        """Single-parent view (spec §1.1); ``None`` for founders."""
        return self.parent_strain_ids[0] if self.parent_strain_ids else None

    @property
    def is_founder(self) -> bool:
        return not self.parent_strain_ids

    def to_telemetry(self) -> dict[str, Any]:
        """Compact serializable form for line lists and lineage artifacts."""
        return {
            "strain_id": self.strain_id,
            "pathogen_id": self.pathogen_id,
            "genotype": self.genotype,
            "parent_strain_ids": list(self.parent_strain_ids),
            "generation": self.generation,
            "n_mutations": self.n_mutations,
            "transmissibility_multiplier": self.transmissibility_multiplier,
            "shedding_multiplier": self.shedding_multiplier,
            "incubation_modifier": self.incubation_modifier,
            "immune_escape": self.immune_escape,
            "origin": self.origin,
            "source_location": self.source_location,
            "recombinant": self.recombinant,
        }


@dataclass(frozen=True)
class Phenotype:
    """The four heritable phenotype offsets, apart from lineage identity.

    Kept separate from :class:`StrainState` so the mutation operator can hand a
    modified phenotype to the registry without reconstructing an identity.
    """

    transmissibility_multiplier: float = 1.0
    shedding_multiplier: float = 1.0
    incubation_modifier: float = 0.0
    immune_escape: float = 0.0

    @classmethod
    def of(cls, strain: StrainState) -> "Phenotype":
        return cls(
            transmissibility_multiplier=strain.transmissibility_multiplier,
            shedding_multiplier=strain.shedding_multiplier,
            incubation_modifier=strain.incubation_modifier,
            immune_escape=strain.immune_escape,
        )


@dataclass(frozen=True)
class PhenotypeEffectRanges:
    """Effect sizes a phenotype mutation draws from.

    Ranged draws rather than a single scalar, following GutIBM's
    ``escape_affinity_lo``/``hi`` treatment in ``fix_mutation``.
    """

    transmissibility: tuple[float, float] = (0.80, 1.25)
    shedding: tuple[float, float] = (0.80, 1.25)
    incubation_days: tuple[float, float] = (-1.0, 1.0)
    immune_escape: tuple[float, float] = (0.01, 0.30)

    def __post_init__(self) -> None:
        for name, (lo, hi) in (
            ("transmissibility", self.transmissibility),
            ("shedding", self.shedding),
            ("incubation_days", self.incubation_days),
            ("immune_escape", self.immune_escape),
        ):
            if float(hi) < float(lo):
                raise StrainConfigError(
                    f"effect_ranges.{name} is inverted: [{lo}, {hi}]",
                )
        _require_positive(
            "effect_ranges.transmissibility lower bound", self.transmissibility[0],
        )
        _require_positive("effect_ranges.shedding lower bound", self.shedding[0])
        _require_unit_interval(
            "effect_ranges.immune_escape lower bound", self.immune_escape[0],
        )
        _require_unit_interval(
            "effect_ranges.immune_escape upper bound", self.immune_escape[1],
        )

    @classmethod
    def from_config(cls, raw: Mapping[str, Any] | None) -> "PhenotypeEffectRanges":
        if not raw:
            return cls()
        defaults = cls()
        return cls(
            transmissibility=_as_range(
                raw.get("transmissibility"), defaults.transmissibility,
            ),
            shedding=_as_range(raw.get("shedding"), defaults.shedding),
            incubation_days=_as_range(
                raw.get("incubation_days"), defaults.incubation_days,
            ),
            immune_escape=_as_range(raw.get("immune_escape"), defaults.immune_escape),
        )


def _as_range(
    raw: Any,
    default: tuple[float, float],
) -> tuple[float, float]:
    """Coerce a two-element sequence to a float pair."""
    if raw is None:
        return default
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) != 2:
        raise StrainConfigError(f"expected a [lo, hi] pair, got {raw!r}")
    return (float(raw[0]), float(raw[1]))


@dataclass(frozen=True)
class StrainEvolutionConfig:
    """Per-pathogen strain parameters (spec §1.3, §1.4).

    ``mutation_rate`` is per transmission; ``within_host_mutation_rate`` is per
    infected-agent-epoch and defaults to 0 so the transmission-only model stays
    the baseline (plan §0 decision 2).
    """

    pathogen_id: str
    mutation_rate: float = 0.0
    phenotype_mutation_fraction: float = 0.0
    within_host_mutation_rate: float = 0.0
    recombination_rate: float = 0.0
    superinfection_susceptibility: float = 0.0
    genotypes: tuple[str, ...] = ()
    prior_genotype_distribution: Mapping[str, float] = field(default_factory=dict)
    cross_immunity: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    effect_ranges: PhenotypeEffectRanges = field(default_factory=PhenotypeEffectRanges)
    min_strain_fraction: float = 0.0

    @classmethod
    def from_profile(
        cls,
        profile: Mapping[str, Any],
    ) -> "StrainEvolutionConfig | None":
        """Parse a pathogen profile's ``strain_evolution`` block, or ``None``."""
        raw = profile.get("strain_evolution")
        if not raw:
            return None
        if not isinstance(raw, Mapping):
            raise StrainConfigError("strain_evolution must be an object")
        pathogen_id = str(profile.get("pathogen_id", ""))
        genotypes = tuple(str(g) for g in raw.get("genotypes") or ())
        cfg = cls(
            pathogen_id=pathogen_id,
            mutation_rate=_require_unit_interval(
                "mutation_rate", raw.get("mutation_rate", 0.0),
            ),
            phenotype_mutation_fraction=_require_unit_interval(
                "phenotype_mutation_fraction",
                raw.get("phenotype_mutation_fraction", 0.0),
            ),
            within_host_mutation_rate=_require_unit_interval(
                "within_host_mutation_rate", raw.get("within_host_mutation_rate", 0.0),
            ),
            recombination_rate=_require_unit_interval(
                "recombination_rate", raw.get("recombination_rate", 0.0),
            ),
            superinfection_susceptibility=_require_unit_interval(
                "superinfection_susceptibility",
                raw.get("superinfection_susceptibility", 0.0),
            ),
            genotypes=genotypes,
            prior_genotype_distribution=_normalized_prior(
                raw.get("prior_genotype_distribution"), genotypes,
            ),
            cross_immunity=_validated_cross_immunity(
                raw.get("cross_immunity"), genotypes,
            ),
            effect_ranges=PhenotypeEffectRanges.from_config(raw.get("effect_ranges")),
            min_strain_fraction=_require_unit_interval(
                "min_strain_fraction", raw.get("min_strain_fraction", 0.0),
            ),
        )
        if not cfg.pathogen_id:
            raise StrainConfigError("strain_evolution requires a pathogen_id")
        if not cfg.genotypes:
            raise StrainConfigError(
                f"{cfg.pathogen_id}.strain_evolution.genotypes must be non-empty",
            )
        return cfg

    def protection(self, prior_genotype: str, challenge_genotype: str) -> float:
        """Cross-immunity entry [prior][challenge], defaulting to 0 (spec §1.4)."""
        row = self.cross_immunity.get(prior_genotype)
        if not row:
            return 0.0
        return float(row.get(challenge_genotype, 0.0))

    def effective_protection(
        self,
        prior_genotype: str,
        challenge_strain: StrainState,
    ) -> float:
        """``base * (1 - immune_escape)`` (spec §1.4)."""
        base = self.protection(prior_genotype, challenge_strain.genotype)
        return base * (1.0 - challenge_strain.immune_escape)


def _normalized_prior(
    raw: Mapping[str, Any] | None,
    genotypes: tuple[str, ...],
) -> dict[str, float]:
    """Validate and renormalize a prior genotype distribution."""
    if not raw:
        return {g: 1.0 / len(genotypes) for g in genotypes} if genotypes else {}
    weights: dict[str, float] = {}
    for key, value in raw.items():
        name = str(key)
        if genotypes and name not in genotypes:
            raise StrainConfigError(
                f"prior_genotype_distribution has unknown genotype {name!r}",
            )
        weight = float(value)
        if weight < 0.0:
            raise StrainConfigError(
                f"prior_genotype_distribution[{name}] must be non-negative, "
                f"got {weight}",
            )
        weights[name] = weight
    total = sum(weights.values())
    if total <= 0.0:
        raise StrainConfigError("prior_genotype_distribution sums to zero")
    return {name: weight / total for name, weight in weights.items()}


def _validated_cross_immunity(
    raw: Mapping[str, Any] | None,
    genotypes: tuple[str, ...],
) -> dict[str, dict[str, float]]:
    """Validate an NxN cross-immunity matrix against the genotype list."""
    if not raw:
        return {}
    matrix: dict[str, dict[str, float]] = {}
    for prior, row in raw.items():
        prior_name = str(prior)
        if genotypes and prior_name not in genotypes:
            raise StrainConfigError(
                f"cross_immunity has unknown prior genotype {prior_name!r}",
            )
        if not isinstance(row, Mapping):
            raise StrainConfigError(
                f"cross_immunity[{prior_name}] must be an object of genotype "
                "-> protection",
            )
        matrix[prior_name] = _validated_immunity_row(prior_name, row, genotypes)
    return matrix


def _validated_immunity_row(
    prior_name: str,
    row: Mapping[str, Any],
    genotypes: tuple[str, ...],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for challenge, value in row.items():
        challenge_name = str(challenge)
        if genotypes and challenge_name not in genotypes:
            raise StrainConfigError(
                f"cross_immunity[{prior_name}] has unknown challenge genotype "
                f"{challenge_name!r}",
            )
        out[challenge_name] = _require_unit_interval(
            f"cross_immunity[{prior_name}][{challenge_name}]", value,
        )
    return out


@dataclass(frozen=True)
class LineageCensus:
    """Population-level lineage summary at one epoch.

    Snapshots rather than a full event log, following GutIBM's
    ``LineageSnapshot``: it is what keeps a multi-thousand-run campaign's
    artifacts finite.
    """

    epoch: int
    pathogen_id: str
    lineage_counts: Mapping[str, int]
    total_carriers: int
    num_lineages: int
    dominant_strain_id: str
    dominant_fraction: float

    def to_telemetry(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "pathogen_id": self.pathogen_id,
            "lineage_counts": dict(self.lineage_counts),
            "total_carriers": self.total_carriers,
            "num_lineages": self.num_lineages,
            "dominant_strain_id": self.dominant_strain_id,
            "dominant_fraction": self.dominant_fraction,
        }


class StrainRegistry:
    """Owns strain id allocation, the founder set, and the lineage census.

    Ids are ``"<pathogen_id>:<n>"`` with ``n`` monotone per pathogen, so a
    strain id is self-describing in a line list and stable across a run.
    """

    def __init__(self) -> None:
        self._strains: dict[str, StrainState] = {}
        self._counters: dict[str, int] = {}
        self._founders: dict[str, list[str]] = {}
        self._snapshots: list[LineageCensus] = []

    # ── identity ────────────────────────────────────────────────────────

    def allocate_id(self, pathogen_id: str) -> str:
        """Next unused strain id for a pathogen."""
        if not pathogen_id:
            raise StrainConfigError("pathogen_id must be non-empty")
        nxt = self._counters.get(pathogen_id, 0) + 1
        self._counters[pathogen_id] = nxt
        return f"{pathogen_id}:{nxt}"

    def register(self, strain: StrainState) -> StrainState:
        """Add an already-built strain; ids must be unique."""
        if strain.strain_id in self._strains:
            raise StrainConfigError(f"duplicate strain_id {strain.strain_id!r}")
        self._strains[strain.strain_id] = strain
        if strain.is_founder:
            self._founders.setdefault(strain.pathogen_id, []).append(strain.strain_id)
        return strain

    def mint(
        self,
        pathogen_id: str,
        *,
        genotype: str = "",
        origin: str = "founder",
        source_location: str = SHIP_LOCATION,
        parent_strain_ids: Iterable[str] = (),
        phenotype: Phenotype | None = None,
    ) -> StrainState:
        """Allocate an id and register a new strain in one step."""
        parents = tuple(str(p) for p in parent_strain_ids)
        for parent_id in parents:
            if parent_id not in self._strains:
                raise StrainConfigError(f"unknown parent strain {parent_id!r}")
        pheno = phenotype or Phenotype()
        strain = StrainState(
            strain_id=self.allocate_id(pathogen_id),
            pathogen_id=pathogen_id,
            genotype=genotype,
            origin=origin,
            source_location=source_location,
            parent_strain_ids=parents,
            transmissibility_multiplier=pheno.transmissibility_multiplier,
            shedding_multiplier=pheno.shedding_multiplier,
            incubation_modifier=pheno.incubation_modifier,
            immune_escape=pheno.immune_escape,
        )
        return self.register(strain)

    def derive(
        self,
        parent: StrainState,
        *,
        origin: str = "transmission",
        source_location: str | None = None,
        mutations_added: int = 0,
        genotype: str | None = None,
        phenotype: Phenotype | None = None,
    ) -> StrainState:
        """Child of one parent, inheriting phenotype unless overridden.

        ``generation`` counts transmission generations, so it advances only for
        ``origin='transmission'``; a within-host mutant is the same generation
        with one more mutation.
        """
        if parent.strain_id not in self._strains:
            raise StrainConfigError(f"unknown parent strain {parent.strain_id!r}")
        if mutations_added < 0:
            raise StrainConfigError(
                f"mutations_added must be >= 0, got {mutations_added}",
            )
        generation = parent.generation + (1 if origin == "transmission" else 0)
        pheno = phenotype or Phenotype.of(parent)
        child = replace(
            parent,
            strain_id=self.allocate_id(parent.pathogen_id),
            parent_strain_ids=(parent.strain_id,),
            generation=generation,
            n_mutations=parent.n_mutations + mutations_added,
            origin=origin,
            source_location=source_location or parent.source_location,
            genotype=parent.genotype if genotype is None else genotype,
            transmissibility_multiplier=pheno.transmissibility_multiplier,
            shedding_multiplier=pheno.shedding_multiplier,
            incubation_modifier=pheno.incubation_modifier,
            immune_escape=pheno.immune_escape,
        )
        return self.register(child)

    def recombine(
        self,
        recipient: StrainState,
        donor: StrainState,
        *,
        genotype: str | None = None,
        phenotype: Phenotype | None = None,
        source_location: str | None = None,
    ) -> StrainState:
        """Child of two co-resident parents (plan §3 PR 3c).

        ``generation`` is the more advanced parent's and ``n_mutations`` likewise
        the larger: recombination happens inside one host, so no transmission
        generation passes, and the mosaic is at least as far from the founder as
        the parent it inherited most of its segments from. Parents are recorded
        recipient-first, so ``lineage_root`` follows the lineage the recombinant
        physically replaced rather than the one that donated to it.
        """
        for parent in (recipient, donor):
            if parent.strain_id not in self._strains:
                raise StrainConfigError(f"unknown parent strain {parent.strain_id!r}")
        if recipient.pathogen_id != donor.pathogen_id:
            raise StrainConfigError(
                "cannot recombine strains of different pathogens: "
                f"{recipient.pathogen_id!r} and {donor.pathogen_id!r}",
            )
        if recipient.strain_id == donor.strain_id:
            raise StrainConfigError(
                f"recombination needs two distinct parents, got {recipient.strain_id!r} twice",
            )
        pheno = phenotype or Phenotype.of(recipient)
        child = replace(
            recipient,
            strain_id=self.allocate_id(recipient.pathogen_id),
            parent_strain_ids=(recipient.strain_id, donor.strain_id),
            generation=max(recipient.generation, donor.generation),
            n_mutations=max(recipient.n_mutations, donor.n_mutations),
            origin="recombination",
            source_location=source_location or recipient.source_location,
            genotype=recipient.genotype if genotype is None else genotype,
            transmissibility_multiplier=pheno.transmissibility_multiplier,
            shedding_multiplier=pheno.shedding_multiplier,
            incubation_modifier=pheno.incubation_modifier,
            immune_escape=pheno.immune_escape,
        )
        return self.register(child)

    def get(self, strain_id: str) -> StrainState:
        try:
            return self._strains[strain_id]
        except KeyError:
            raise StrainConfigError(f"unknown strain {strain_id!r}") from None

    def __contains__(self, strain_id: object) -> bool:
        return strain_id in self._strains

    def __len__(self) -> int:
        return len(self._strains)

    def strains_for(self, pathogen_id: str) -> tuple[StrainState, ...]:
        return tuple(
            s for s in self._strains.values() if s.pathogen_id == pathogen_id
        )

    def founders(self, pathogen_id: str) -> tuple[StrainState, ...]:
        return tuple(
            self._strains[sid] for sid in self._founders.get(pathogen_id, ())
        )

    def lineage_root(self, strain_id: str) -> str:
        """Founder this strain descends from (first parent at each step)."""
        seen: set[str] = set()
        current = self.get(strain_id)
        while not current.is_founder:
            if current.strain_id in seen:
                raise StrainConfigError(
                    f"cycle in strain ancestry at {current.strain_id!r}",
                )
            seen.add(current.strain_id)
            parent_id = current.parent_strain_id
            current = self.get(str(parent_id))
        return current.strain_id

    def ancestors(self, strain_id: str) -> set[str]:
        """Every ancestor of a strain, following both parents of a recombinant."""
        seen: set[str] = set()
        frontier = [strain_id]
        while frontier:
            current = frontier.pop()
            for parent_id in self.get(current).parent_strain_ids:
                if parent_id in self._strains and parent_id not in seen:
                    seen.add(parent_id)
                    frontier.append(parent_id)
        return seen

    def collect(self, live_strain_ids: Iterable[str]) -> tuple[str, ...]:
        """Forget extinct lineages, keeping the ancestry of the live ones.

        A voyage under mutation mints a lineage per transmission, so without
        collection the registry is the run's whole phylogeny in memory. Ancestors
        of live strains are retained even when extinct themselves, because
        ``lineage_root`` and the ancestry a sequencing assay reconstructs are
        exactly what a phylogenomic observatory is for; only lineages with no
        living descendant and no pool remnant are dropped. Ids are never reused
        (the counters are monotone), so a collected id cannot be confused with a
        later strain.
        """
        keep: set[str] = set()
        for strain_id in live_strain_ids:
            if strain_id in self._strains and strain_id not in keep:
                keep.add(strain_id)
                keep |= self.ancestors(strain_id)
        dropped = tuple(sid for sid in self._strains if sid not in keep)
        for strain_id in dropped:
            del self._strains[strain_id]
        for pathogen_id, founders in tuple(self._founders.items()):
            self._founders[pathogen_id] = [
                sid for sid in founders if sid in self._strains
            ]
        return dropped

    # ── census ──────────────────────────────────────────────────────────

    def census(
        self,
        epoch: int,
        pathogen_id: str,
        carrier_counts: Mapping[str, int],
    ) -> LineageCensus:
        """Summarize a strain -> carrier-count mapping without storing it."""
        counts = {
            sid: int(n)
            for sid, n in carrier_counts.items()
            if int(n) > 0 and self.get(sid).pathogen_id == pathogen_id
        }
        total = sum(counts.values())
        dominant_id = max(counts, key=lambda sid: counts[sid]) if counts else ""
        dominant_fraction = counts[dominant_id] / total if total else 0.0
        return LineageCensus(
            epoch=epoch,
            pathogen_id=pathogen_id,
            lineage_counts=counts,
            total_carriers=total,
            num_lineages=len(counts),
            dominant_strain_id=dominant_id,
            dominant_fraction=dominant_fraction,
        )

    def take_snapshot(
        self,
        epoch: int,
        pathogen_id: str,
        carrier_counts: Mapping[str, int],
    ) -> LineageCensus:
        """Record a census in the run's snapshot history."""
        snapshot = self.census(epoch, pathogen_id, carrier_counts)
        self._snapshots.append(snapshot)
        return snapshot

    def snapshots(self, pathogen_id: str | None = None) -> tuple[LineageCensus, ...]:
        if pathogen_id is None:
            return tuple(self._snapshots)
        return tuple(s for s in self._snapshots if s.pathogen_id == pathogen_id)

    def to_telemetry(self) -> dict[str, Any]:
        """Run-level strain artifact: every strain plus the snapshot series."""
        return {
            "strains": [s.to_telemetry() for s in self._strains.values()],
            "founders": {
                pid: list(sids) for pid, sids in self._founders.items()
            },
            "snapshots": [s.to_telemetry() for s in self._snapshots],
        }
