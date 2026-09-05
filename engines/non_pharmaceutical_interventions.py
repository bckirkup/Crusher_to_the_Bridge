"""Non-pharmaceutical interventions as declared per-route dose reductions.

This module is the interface ``docs/formal_spec_v2.md`` §3.7 specifies and
nothing more: a measure declares, per transmission route, the fraction of
the external dose that still reaches the host, and a coverage map saying
which roles are reached by the measure at all.

Three boundaries are load-bearing, and the module enforces the ones that
are enforceable:

- **Not route efficiency.** ``route_efficiency_multipliers`` (A5/#25) is
  pathogen biology — how well a route delivers virus to a portal. An NPI
  multiplier is what the *operator* did to an exposure: a mask, a glove,
  an attendant at the buffet door. The two multiply in sequence and never
  share a field, because folding them together would make either one
  unidentifiable from the other.
- **Not the ship's plant.** HVAC filter efficiency, air changes and the
  surface-cleaning schedule already have owning fields in ``config.yaml``.
  A filtration upgrade is declared there, not here; this interface is for
  measures acting on a host's exposure, and re-expressing plant here
  would parameterise the same effect twice.
- **Not a source of numbers.** No reference multiplier is shipped. A
  declared measure must carry its own ``source``, because the magnitudes
  are exactly what E/#10 has to source, and a default here would be an
  unsourced constant with a route key for a citation.

Composition of two measures on one route is multiplicative, which assumes
they act independently. That is a declared assumption, not a measurement:
a mask and a hand-washing prompt plausibly do act on different steps, two
hand-hygiene measures plausibly do not.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

# The transmission engine's route vocabulary. Declared here rather than
# imported from ``transmission_core`` (which imports this module), and
# pinned to it by test, so a route can never be silently misspelled into
# an identity multiplier.
NPI_ROUTE_KEYS: frozenset[str] = frozenset(
    {
        "direct_contact",
        "droplet",
        "hvac_airborne",
        "fomite",
        "food_contamination",
        "environmental_source",
    },
)


@runtime_checkable
class NpiHost(Protocol):
    """The host state this module reads and writes.

    Declared as a protocol rather than importing ``KorkinAgent`` because the
    agent module must not depend on this one, and because the contract is
    genuinely just these three fields.
    """

    role: str
    npi_measures: tuple[str, ...]
    dose_reduction_multipliers: dict[str, float]


def _as_float(value: object, name: str) -> float:
    """Coerce a configured scalar, refusing types that would coerce oddly."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    return float(value)


def _surviving_fraction(value: object, name: str) -> float:
    """Read one route multiplier: the share of dose that still arrives.

    The domain is ``[0, 1]``. A value above 1 would be an intervention that
    increases exposure, which this interface deliberately cannot express —
    such a mechanism is not a dose reduction and needs its own field.
    """
    number = _as_float(value, name)
    if not np.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(
            f"{name} must be a surviving fraction in [0, 1], got {value!r}",
        )
    return number


def _compliance(value: object, name: str) -> float:
    """Read a compliance fraction, defaulting to full compliance."""
    if value is None:
        return 1.0
    number = _as_float(value, name)
    if not np.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must lie in [0, 1], got {value!r}")
    return number


def _coverage_by_role(raw: object, name: str) -> dict[str, float]:
    """Read a role-keyed coverage map, e.g. ``{"passenger": 0.8}``.

    A role absent from the map is uncovered. An empty or missing map is
    refused rather than treated as zero: a measure that reaches nobody is a
    configuration mistake, while an explicit ``0.0`` is a legitimate sweep
    endpoint and is accepted.
    """
    if not isinstance(raw, Mapping) or not raw:
        raise ValueError(f"{name} must be a non-empty mapping of role to coverage")
    return {
        str(role): _bounded_coverage(value, f"{name}.{role}")
        for role, value in raw.items()
    }


def _bounded_coverage(value: object, name: str) -> float:
    """Read one coverage probability."""
    number = _as_float(value, name)
    if not np.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must lie in [0, 1], got {value!r}")
    return number


def _reference_multipliers(raw: object, name: str) -> dict[str, float]:
    """Read the measure's per-route surviving fractions at full compliance."""
    if not isinstance(raw, Mapping) or not raw:
        raise ValueError(
            f"{name} must be a non-empty mapping of route to surviving fraction",
        )
    unknown = sorted(set(map(str, raw)) - NPI_ROUTE_KEYS)
    if unknown:
        raise ValueError(
            f"{name} names unknown routes {unknown}; "
            f"valid routes are {sorted(NPI_ROUTE_KEYS)}",
        )
    return {
        str(route): _surviving_fraction(value, f"{name}.{route}")
        for route, value in raw.items()
    }


def effective_multiplier(reference: float, compliance: float) -> float:
    """Interpolate a reference multiplier towards no effect by compliance.

    ``m_effective = 1 - compliance * (1 - m_reference)``, the form
    ``formal_spec_v2`` §3.7 specifies: full compliance gives the reference
    efficacy, zero compliance gives identity, and partial compliance is
    linear between them. Linearity is a declared assumption — it treats a
    half-complying population as half-protected, which is right for a
    measure used on half of occasions and wrong for one whose protection
    is threshold-shaped.
    """
    return 1.0 - compliance * (1.0 - reference)


@dataclass(frozen=True)
class NpiMeasure:
    """One declared non-pharmaceutical measure.

    ``source`` is required rather than decorative: it is the provenance of
    every number in ``reference_multipliers``, and the register row for
    this measure has to be able to quote it.
    """

    name: str
    source: str
    coverage_by_role: Mapping[str, float]
    reference_multipliers: Mapping[str, float]
    compliance: float = 1.0

    @classmethod
    def from_config(cls, name: str, raw: Mapping[str, object]) -> NpiMeasure:
        source = str(raw.get("source") or "").strip()
        if not source:
            raise ValueError(
                f"npi.{name}.source is required: an NPI multiplier with no "
                "source is an unsourced constant",
            )
        return cls(
            name=str(name),
            source=source,
            coverage_by_role=_coverage_by_role(
                raw.get("coverage_by_role"), f"npi.{name}.coverage_by_role",
            ),
            reference_multipliers=_reference_multipliers(
                raw.get("reference_multipliers"),
                f"npi.{name}.reference_multipliers",
            ),
            compliance=_compliance(
                raw.get("compliance"), f"npi.{name}.compliance",
            ),
        )

    def route_multipliers(self) -> dict[str, float]:
        """This measure's surviving fractions after its own compliance."""
        return {
            route: effective_multiplier(reference, self.compliance)
            for route, reference in self.reference_multipliers.items()
        }


def resolve_npi(cfg: Mapping[str, object] | None) -> dict[str, NpiMeasure]:
    """Read ``cfg['non_pharmaceutical_interventions']`` into measures.

    A run that declares nothing gets an empty mapping and behaves exactly
    as it did before this module existed.
    """
    raw = (cfg or {}).get("non_pharmaceutical_interventions")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("non_pharmaceutical_interventions must be a mapping")
    measures: dict[str, NpiMeasure] = {}
    for name, block in raw.items():
        if not isinstance(block, Mapping):
            raise ValueError(
                f"non_pharmaceutical_interventions.{name} must be a mapping",
            )
        measures[str(name)] = NpiMeasure.from_config(str(name), block)
    return measures


@dataclass(frozen=True)
class HostNpiState:
    """What one host's declared measures do to its incoming dose."""

    measures: tuple[str, ...] = ()
    route_multipliers: Mapping[str, float] = field(default_factory=dict)


def _host_state(
    role: str,
    measures: Mapping[str, NpiMeasure],
    rng: np.random.Generator,
) -> HostNpiState:
    """Draw which measures reach this host, and fold their multipliers.

    One coverage draw per declared measure per host, in the mapping's own
    order, so the stream is deterministic given the config.
    """
    reached: list[str] = []
    folded: dict[str, float] = {}
    for name, measure in measures.items():
        probability = float(measure.coverage_by_role.get(role, 0.0))
        if probability <= 0.0 or rng.random() >= probability:
            continue
        reached.append(name)
        for route, multiplier in measure.route_multipliers().items():
            folded[route] = folded.get(route, 1.0) * multiplier
    return HostNpiState(measures=tuple(reached), route_multipliers=folded)


def assign_host_npi(
    agents: list[NpiHost],
    measures: Mapping[str, NpiMeasure],
    rng: np.random.Generator,
) -> None:
    """Draw each host's coverage and store its per-route dose multipliers.

    The result is stored rather than applied: an NPI acts on a dose that
    has not arrived yet, so the engine reads these multipliers each epoch
    as doses are delivered.
    """
    if not measures:
        return
    for agent in agents:
        state = _host_state(str(agent.role), measures, rng)
        agent.npi_measures = state.measures
        agent.dose_reduction_multipliers = dict(state.route_multipliers)
