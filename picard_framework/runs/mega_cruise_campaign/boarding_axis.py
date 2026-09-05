"""The boarding-channel campaign axis for initiation-owned pathogens.

A pathogen the initiation engine owns has no fiat index case: it arrives
aboard through the boarding prevalence channel of ``engines/initiation.py``,
and the coordinates that move between runs are that channel's own
(``prevalence``, ``state_split``), not a seed count. This module is the single
place that says which pathogens are owned, what each swept coordinate is
allowed to take, and how a run id and a run's ``initiation`` config override
are built from a point on that grid.

Evidence, from ``docs/parameter_provenance_register.md``:

* ``never_symptomatic_fraction`` has no licensed point for this model's own
  population (adults and geriatrics under natural exposure). Two intervals are
  admissible and are **not pooled**: adult challenge ``[0.22, 0.36]`` and
  community cohorts ``[0.59, 0.68]``. They are kept as two named regimes here
  rather than as one union interval, because a union sweep would place runs in
  ``(0.36, 0.59)``, which neither body of evidence measures, and because the
  community interval is paediatric-leaning while this model's mean age is 72.6
  (consensus tranche 24 §F4). The adult-challenge regime is the default; the
  community regime stays available, named, for the transport question.
* Boarding prevalence is an interval per role, Grade B: passenger
  ``[0.025, 0.040]``, crew ``[0.007, 0.030]``. A tier that does not sweep it
  boards at the interval midpoint.
* ``presymptomatic_share_of_presenting`` is Grade C and derived (0.5 /
  (0.5 + 15 - 3) = 0.04 from the profile's own shedding geometry), so it is
  swept rather than adopted as a measurement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Any

from picard_framework.catalog.registry import CatalogRegistry
from picard_framework.pathogen_overrides import (
    REPO_ROOT,
    load_pathogen_bundle,
)

# Pathogens the shipped ``initiation`` block owns. A pathogen listed here may
# not carry a profile ``initial_infected``, and no campaign tier may sweep one
# for it: the engine would ignore the field, and the incidence would be
# attributable to neither mechanism.
BOARDING_PATHOGEN_IDS = frozenset({"norwalk_gi"})

# never_symptomatic_fraction, as two unpooled regimes (interval endpoints and
# midpoint). Neither regime licenses a point; a run states which regime and
# which point in it, and the screen reads the axis, not a single run.
NEVER_SYMPTOMATIC_REGIMES: dict[str, tuple[float, ...]] = {
    "adult_challenge": (0.22, 0.29, 0.36),
    "community_cohort": (0.59, 0.635, 0.68),
}
DEFAULT_NEVER_SYMPTOMATIC_REGIME = "adult_challenge"

# The point a tier that does not sweep the axis boards at: the midpoint of the
# default regime, named as a midpoint rather than as a licensed value.
DEFAULT_NEVER_SYMPTOMATIC_FRACTION = 0.29

PASSENGER_PREVALENCE_INTERVAL = (0.025, 0.040)
CREW_PREVALENCE_INTERVAL = (0.007, 0.030)
DEFAULT_PASSENGER_PREVALENCE = 0.0325
DEFAULT_CREW_PREVALENCE = 0.0185

DEFAULT_PRESYMPTOMATIC_SHARE = 0.04

# Tier keys, and the fiat-count keys they replace for an owned pathogen.
NEVER_SYMPTOMATIC_KEY = "never_symptomatic_fractions"
REGIME_KEY = "never_symptomatic_regime"
PRESYMPTOMATIC_KEY = "presymptomatic_shares"
PREVALENCE_KEY = "boarding_prevalence_points"
LEGACY_COUNT_KEYS = ("initial_infected", "initial_infected_values")

# A design whose experimental variable is the number of introductions itself —
# the pre-boarding outbreak surface over k, or a calibration arm that fits one
# platform at a stated k — states this key. The run then withdraws the
# ``initiation`` block altogether, so the count it writes is the mechanism the
# engine actually uses rather than a number the boarding channel would ignore.
# Boarding is the shipped default; a fiat count is the exception and must say so.
FIAT_INDEX_CASE_KEY = "fiat_index_case"

# campaign_parameters / factor names, also read by ``initiation_override``.
FACTOR_NEVER_SYMPTOMATIC = "never_symptomatic_fraction"
FACTOR_PRESYMPTOMATIC = "presymptomatic_share_of_presenting"
FACTOR_PASSENGER_PREVALENCE = "boarding_passenger_prevalence"
FACTOR_CREW_PREVALENCE = "boarding_crew_prevalence"

# The count a fiat-index-case design states. Its presence in a run's factors is
# what withdraws the run's ``initiation`` block: the two mechanisms are
# exclusive, and the one the run recorded is the one the engine must use.
FACTOR_FIAT_COUNT = "n_init"


def owns(pathogen_id: str) -> bool:
    """Whether initiation owns this pathogen, so boarding is its mechanism."""
    return str(pathogen_id) in BOARDING_PATHOGEN_IDS


def declares_fiat_index_case(tier: Mapping[str, Any]) -> bool:
    """Whether the tier makes the introduction count its own design variable."""
    return bool(tier.get(FIAT_INDEX_CASE_KEY))


def _fraction_tag(value: float) -> str:
    """Percent fragment for a [0, 1] coordinate: 0.22 → ``22``, 0.635 → ``63p5``."""
    pct = round(float(value) * 100.0, 2)
    text = f"{pct:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", "p")


def _permille_tag(value: float) -> str:
    """Per-mille fragment for a prevalence: 0.0325 → ``32p5``."""
    permille = round(float(value) * 1000.0, 2)
    text = f"{permille:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", "p")


def never_symptomatic_tag(value: float) -> str:
    """Run-id fragment naming the swept never-symptomatic fraction."""
    return f"nsf{_fraction_tag(value)}"


def presymptomatic_tag(value: float) -> str:
    """Run-id fragment naming the swept presymptomatic share."""
    return f"psp{_fraction_tag(value)}"


def prevalence_tag(passenger: float, crew: float) -> str:
    """Run-id fragment naming the swept boarding prevalence pair."""
    return f"bp{_permille_tag(passenger)}c{_permille_tag(crew)}"


def _unique_tags(values: Sequence[float], tag: Any, location: str) -> None:
    tags = [tag(v) for v in values]
    if len(set(tags)) != len(tags):
        raise ValueError(
            f"{location} = {list(values)!r} collapses to run-id tags {tags!r}: "
            "two points on the sweep would share a run id, so the grid could "
            "not be read back apart",
        )


def refuse_legacy_count_axis(tier: Mapping[str, Any], pathogen_id: str) -> None:
    """Refuse a fiat index-case sweep for a pathogen initiation owns.

    The engine reads its cohort from the boarding prevalence, so a tier count
    would be written into the run spec, ignored, and still stamped into the run
    id. Naming the replacement key is the whole point of the message.
    """
    if not owns(pathogen_id) or declares_fiat_index_case(tier):
        return
    for key in LEGACY_COUNT_KEYS:
        if key in tier:
            raise ValueError(
                f"tier declares {key}={tier[key]!r} for {pathogen_id}, which "
                "initiation owns through its boarding prevalence: the count "
                "would be ignored by the engine and still stamped into the "
                f"run id. Sweep {NEVER_SYMPTOMATIC_KEY} (or name a "
                f"{REGIME_KEY}) instead, or declare "
                f"{FIAT_INDEX_CASE_KEY} if the count is this design's own "
                "experimental variable",
            )


def sweeps_never_symptomatic(tier: Mapping[str, Any]) -> bool:
    """Whether the tier declares the never-symptomatic axis, so ids must name it."""
    return NEVER_SYMPTOMATIC_KEY in tier or REGIME_KEY in tier


def never_symptomatic_values(tier: Mapping[str, Any]) -> list[float]:
    """The tier's never-symptomatic sweep: explicit points, a named regime, or
    the default regime's midpoint when the tier does not sweep the axis."""
    if NEVER_SYMPTOMATIC_KEY in tier:
        values = [float(v) for v in tier[NEVER_SYMPTOMATIC_KEY]]
        if not values:
            raise ValueError(
                f"tier {NEVER_SYMPTOMATIC_KEY} is empty: a boarding run needs "
                "the coordinate, and no value for it is licensed",
            )
    elif REGIME_KEY in tier:
        regime = str(tier[REGIME_KEY])
        if regime not in NEVER_SYMPTOMATIC_REGIMES:
            raise ValueError(
                f"tier {REGIME_KEY} = {regime!r} names no regime in the "
                "register; choose from "
                f"{sorted(NEVER_SYMPTOMATIC_REGIMES)}",
            )
        values = list(NEVER_SYMPTOMATIC_REGIMES[regime])
    else:
        return [DEFAULT_NEVER_SYMPTOMATIC_FRACTION]
    _unique_tags(values, never_symptomatic_tag, f"tier {NEVER_SYMPTOMATIC_KEY}")
    return values


def presymptomatic_values(tier: Mapping[str, Any]) -> list[float]:
    """The tier's presymptomatic-share sweep; the derived 0.04 when unswept."""
    if PRESYMPTOMATIC_KEY not in tier:
        return [DEFAULT_PRESYMPTOMATIC_SHARE]
    values = [float(v) for v in tier[PRESYMPTOMATIC_KEY]]
    if not values:
        raise ValueError(f"tier {PRESYMPTOMATIC_KEY} is empty")
    _unique_tags(values, presymptomatic_tag, f"tier {PRESYMPTOMATIC_KEY}")
    return values


def prevalence_points(tier: Mapping[str, Any]) -> list[tuple[float, float]]:
    """The tier's boarding-prevalence sweep; the interval midpoints when unswept."""
    if PREVALENCE_KEY not in tier:
        return [(DEFAULT_PASSENGER_PREVALENCE, DEFAULT_CREW_PREVALENCE)]
    points: list[tuple[float, float]] = []
    for raw in tier[PREVALENCE_KEY]:
        if isinstance(raw, Mapping):
            points.append((float(raw["passenger"]), float(raw["crew"])))
        else:
            passenger, crew = raw
            points.append((float(passenger), float(crew)))
    if not points:
        raise ValueError(f"tier {PREVALENCE_KEY} is empty")
    tags = [prevalence_tag(p, c) for p, c in points]
    if len(set(tags)) != len(tags):
        raise ValueError(
            f"tier {PREVALENCE_KEY} = {points!r} collapses to run-id tags "
            f"{tags!r}: two points on the sweep would share a run id",
        )
    return points


def sweeps_prevalence(tier: Mapping[str, Any]) -> bool:
    """Whether the tier declares the prevalence axis, so ids must name it."""
    return PREVALENCE_KEY in tier


def sweeps_presymptomatic(tier: Mapping[str, Any]) -> bool:
    """Whether the tier declares the presymptomatic axis, so ids must name it."""
    return PRESYMPTOMATIC_KEY in tier


def run_id_tags(
    tier: Mapping[str, Any],
    pathogen_id: str,
    *,
    never_symptomatic_fraction: float,
    presymptomatic_share: float,
    passenger_prevalence: float,
    crew_prevalence: float,
) -> list[str]:
    """Run-id fragments for the boarding coordinates this tier actually sweeps.

    Unswept coordinates are not named, as with every other campaign axis: they
    are stamped into ``campaign_parameters`` instead.
    """
    if not owns(pathogen_id):
        return []
    tags: list[str] = []
    if sweeps_never_symptomatic(tier):
        tags.append(never_symptomatic_tag(never_symptomatic_fraction))
    if sweeps_presymptomatic(tier):
        tags.append(presymptomatic_tag(presymptomatic_share))
    if sweeps_prevalence(tier):
        tags.append(prevalence_tag(passenger_prevalence, crew_prevalence))
    return tags


def point_factors(
    *,
    never_symptomatic_fraction: float,
    presymptomatic_share: float = DEFAULT_PRESYMPTOMATIC_SHARE,
    passenger_prevalence: float = DEFAULT_PASSENGER_PREVALENCE,
    crew_prevalence: float = DEFAULT_CREW_PREVALENCE,
) -> dict[str, float]:
    """Factor labels for one boarding grid point, for ``yield_run``."""
    return {
        FACTOR_NEVER_SYMPTOMATIC: float(never_symptomatic_fraction),
        FACTOR_PRESYMPTOMATIC: float(presymptomatic_share),
        FACTOR_PASSENGER_PREVALENCE: float(passenger_prevalence),
        FACTOR_CREW_PREVALENCE: float(crew_prevalence),
    }


@dataclass(frozen=True)
class BoardingPoint:
    """One point on the boarding grid."""

    never_symptomatic_fraction: float
    presymptomatic_share: float
    passenger_prevalence: float
    crew_prevalence: float


def boarding_points(tier: Mapping[str, Any]) -> tuple[BoardingPoint, ...]:
    """The tier's boarding grid: never-symptomatic × presymptomatic × prevalence."""
    return tuple(
        BoardingPoint(nsf, psp, passenger, crew)
        for nsf, psp, (passenger, crew) in product(
            never_symptomatic_values(tier),
            presymptomatic_values(tier),
            prevalence_points(tier),
        )
    )


@dataclass(frozen=True)
class IndexCaseAxis:
    """How a campaign tier starts infection aboard for one pathogen.

    For a pathogen initiation owns, the axis is the boarding grid and the run
    id names the swept coordinate; for any other pathogen it is the fiat
    ``initial_infected`` count the tier always had, unchanged. One object so a
    tier iterator with mixed pathogens treats each on its own terms.
    """

    pathogen_id: str
    tier: Mapping[str, Any]
    points: tuple[Any, ...]

    @property
    def boarding(self) -> bool:
        """Whether this tier starts this pathogen through the boarding channel."""
        return owns(self.pathogen_id) and not declares_fiat_index_case(self.tier)

    @classmethod
    def for_tier(
        cls,
        tier: Mapping[str, Any],
        pathogen_id: str,
        *,
        defaults: Mapping[str, Any] | None = None,
        legacy_default: int | None = 3,
    ) -> IndexCaseAxis:
        """Read the tier's axis; ``legacy_default`` is the unswept count for an unowned pathogen (``None`` leaves the bundle's own)."""
        if owns(pathogen_id) and not declares_fiat_index_case(tier):
            refuse_legacy_count_axis(tier, pathogen_id)
            return cls(pathogen_id, tier, boarding_points(tier))
        return cls(pathogen_id, tier, tuple(
            legacy_count_values(tier, defaults=defaults, default=legacy_default),
        ))

    def tags(self, point: Any) -> list[str]:
        """Run-id fragments for this point."""
        if self.boarding:
            return run_id_tags(
                self.tier, self.pathogen_id,
                never_symptomatic_fraction=point.never_symptomatic_fraction,
                presymptomatic_share=point.presymptomatic_share,
                passenger_prevalence=point.passenger_prevalence,
                crew_prevalence=point.crew_prevalence,
            )
        return [] if point is None else [f"init{int(point)}"]

    def factors(self, point: Any) -> dict[str, Any]:
        """campaign_parameters labels for this point."""
        if self.boarding:
            return point_factors(
                never_symptomatic_fraction=point.never_symptomatic_fraction,
                presymptomatic_share=point.presymptomatic_share,
                passenger_prevalence=point.passenger_prevalence,
                crew_prevalence=point.crew_prevalence,
            )
        return {} if point is None else {FACTOR_FIAT_COUNT: int(point)}

    def pathogen_overrides(
        self,
        base: Mapping[str, Any] | None,
        point: Any,
        **patch: Any,
    ) -> dict[str, Any]:
        """Profile overrides for this point plus any extra fields (``None`` skipped).

        A boarding point writes nothing into the profile: its coordinates
        travel in the ``initiation`` config override, and the profile's
        ``initial_infected`` stays null so the engine accepts the block.
        """
        fields = {k: v for k, v in patch.items() if v is not None}
        if not self.boarding and point is not None:
            fields["initial_infected"] = int(point)
        path_over = dict(base or {})
        if fields:
            path_over[self.pathogen_id] = {
                **(path_over.get(self.pathogen_id) or {}), **fields,
            }
        return path_over


def axis_for_mixed_tier(
    tier: Mapping[str, Any],
    pathogen_id: str,
    *,
    defaults: Mapping[str, Any] | None = None,
    legacy_default: int | None = 3,
) -> IndexCaseAxis:
    """The axis for one pathogen of a tier that names several.

    A mixed tier's fiat ``initial_infected`` list belongs to the pathogens
    initiation does not own; an owned pathogen reads the tier's boarding keys
    instead and never sees the shared count list, so the tier does not have to
    be split in two to hold both mechanisms.
    """
    if owns(pathogen_id) and not declares_fiat_index_case(tier):
        tier = {k: v for k, v in tier.items() if k not in LEGACY_COUNT_KEYS}
    return IndexCaseAxis.for_tier(
        tier, pathogen_id, defaults=defaults, legacy_default=legacy_default,
    )


def legacy_count_values(
    tier: Mapping[str, Any],
    *,
    defaults: Mapping[str, Any] | None = None,
    default: int | None = 3,
) -> list[int | None]:
    """Fiat index-case sweep for an unowned pathogen: ``initial_infected_values``, ``initial_infected`` (scalar or list), manifest defaults, then ``default``."""
    if "initial_infected_values" in tier:
        return [int(n) for n in tier["initial_infected_values"]]
    raw = tier.get("initial_infected", (defaults or {}).get("initial_infected"))
    if raw is None:
        return [default if default is None else int(default)]
    if isinstance(raw, list):
        return [int(n) for n in raw]
    return [int(raw)]


_FACTOR_DEFAULTS: dict[str, float] = {
    FACTOR_NEVER_SYMPTOMATIC: DEFAULT_NEVER_SYMPTOMATIC_FRACTION,
    FACTOR_PRESYMPTOMATIC: DEFAULT_PRESYMPTOMATIC_SHARE,
    FACTOR_PASSENGER_PREVALENCE: DEFAULT_PASSENGER_PREVALENCE,
    FACTOR_CREW_PREVALENCE: DEFAULT_CREW_PREVALENCE,
}


def _coordinates(factors: Mapping[str, Any]) -> dict[str, float]:
    """All four coordinates, the tier's where it swept them, register defaults elsewhere."""
    return {
        name: float(factors.get(name, default))
        for name, default in _FACTOR_DEFAULTS.items()
    }


@lru_cache(maxsize=None)
def _bundle_pathogen_ids(bundle_id: str) -> frozenset[str]:
    """Pathogen ids in a catalog bundle, or empty when it cannot be resolved."""
    try:
        path = CatalogRegistry.from_repo(REPO_ROOT).resolve_pathogen_bundle(
            str(bundle_id),
        )
    except (KeyError, FileNotFoundError, ValueError):
        return frozenset()
    return frozenset(load_pathogen_bundle(path))


def active_boarding_pathogens(
    bundle: str,
    pathogen_overrides: Mapping[str, Any] | None,
) -> frozenset[str]:
    """Owned pathogens this run actually loads, after the arm's own edits.

    An arm that studies another pathogen removes the rest of its bundle, and a
    bundle need not contain an owned pathogen at all. Either way the boarding
    channel has nothing to draw, and a block naming an absent pathogen is a
    load error by design.
    """
    overrides = dict(pathogen_overrides or {})
    present = set(_bundle_pathogen_ids(bundle))
    for patch in overrides.get("add") or ():
        if isinstance(patch, Mapping) and patch.get("pathogen_id"):
            present.add(str(patch["pathogen_id"]))
    for pid in overrides.get("remove") or ():
        present.discard(str(pid))
    return frozenset(BOARDING_PATHOGEN_IDS & present)


def initiation_override(
    bundle: str,
    pathogen_overrides: Mapping[str, Any] | None,
    factors: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The run's whole ``initiation`` config override.

    Explicit in both directions: a run that loads an owned pathogen boards it
    at the stated coordinates, and a run whose profiles contain no owned
    pathogen — an arm that studies another one, or a bundle without it —
    withdraws the block rather than inheriting one that names a pathogen it
    does not load. Withdrawing it is a null, not a disabled gate: a disabled
    gate is still a declared ``initiation`` block, and declaring one retires
    the engine's own pathogen-unaware index case for that run.
    """
    active = active_boarding_pathogens(bundle, pathogen_overrides)
    if not active or FACTOR_FIAT_COUNT in (factors or {}):
        return {"initiation": None}
    coords = _coordinates(factors or {})
    boarding: dict[str, Any] = {"enabled": True}
    for pathogen_id in sorted(active):
        boarding[pathogen_id] = {
            "prevalence": {
                "passenger": coords[FACTOR_PASSENGER_PREVALENCE],
                "crew": coords[FACTOR_CREW_PREVALENCE],
            },
            "state_split": {
                "never_symptomatic_fraction": coords[FACTOR_NEVER_SYMPTOMATIC],
                "presymptomatic_share_of_presenting": coords[FACTOR_PRESYMPTOMATIC],
            },
        }
    return {"initiation": {"boarding": boarding}}


def recorded_factors(
    bundle: str,
    pathogen_overrides: Mapping[str, Any] | None,
    factors: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    """The coordinates a boarding run must stamp into ``campaign_parameters``.

    All four, swept or not: a parameters block naming only the swept ones
    would leave the rest to be re-derived from a config file that may have
    moved since. Empty for a run that boards nothing.
    """
    if not active_boarding_pathogens(bundle, pathogen_overrides):
        return {}
    if FACTOR_FIAT_COUNT in (factors or {}):
        return {}
    return _coordinates(factors or {})
