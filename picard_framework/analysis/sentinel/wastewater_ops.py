"""Shipboard wastewater sampling operations: cadence, holding tank, depth.

The generator side of the channel :mod:`wastewater_signal` fits. That module
states what the observation *means* — pooled read counts as a second look at the
same shedder prevalence, delayed by the plumbing. This module produces those
counts under an explicit operating policy, because the operating policy is the
thing a ship can actually choose:

* ``sampling_interval_epochs`` — how often a sample is drawn. Nothing is
  emitted on other epochs, so cadence sets the temporal resolution the fit can
  ever recover (a 24-epoch interval gives 7 samples on a 7-day voyage).
* ``holding_tank_residence_hours`` — the tank is a first-order lag on shedder
  prevalence with mean residence ``tau``: ``tank <- w * tank + (1 - w) * inflow``
  with ``w = exp(-epoch_hours / tau)``. At ``tau -> 0`` the sample is the
  current epoch's prevalence (direct line tap); at 12 h a port-call spike is
  smeared over half a day and adjacent port calls overlap. This is the
  operational counterpart of the residence lag the fit assumes, and the reason
  cadence and residence interact rather than adding.
* ``sequencing_depth`` — library size per sample. It moves precision, not the
  observed fraction; the fit caps how much precision a single tank draw is
  allowed to claim (``max_effective_reads``), so depth is a cost knob whose
  returns are meant to saturate.
* ``collection_points`` — how many taps are sampled per sampling epoch. Each
  point drains its own share of the ship and gets its own row, but they remain
  replicates of one epoch, which is exactly why ``pool_wastewater`` collapses
  them into a single trial instead of multiplying the evidence.

The inflow is *shedder prevalence*, not shedding mass: the fit's link is on
prevalence (``logit(read_fraction) = base + slope * log(share)``), and the
kernel it convolves incidence with is a survival curve, so the generator that
matches it counts people shedding into the system rather than integrating an
intensity curve in arbitrary units. ``pathogen_shedding_to_reads_scale`` and
``background_read_fraction`` are the two knobs that place that prevalence on the
read-fraction scale metagenomics actually reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

# A six-hour composite with a four-hour tank: a defensible mid-range operating
# point, not a recommendation. The scan exists to find the recommendation.
DEFAULT_SAMPLING_INTERVAL_EPOCHS = 6
DEFAULT_RESIDENCE_HOURS = 4.0
DEFAULT_SEQUENCING_DEPTH = 250_000
DEFAULT_COLLECTION_POINTS: tuple[str, ...] = ("aft_main",)
# 1 - 1e-4 of the library is everything that is not the target pathogen, so a
# fully shedding ship tops out at 1e-4 of the reads: the order metagenomic
# surveillance reports, and the scale ``wastewater_signal``'s base logit assumes.
DEFAULT_BACKGROUND_READ_FRACTION = 0.9999
DEFAULT_SHEDDING_TO_READS_SCALE = 1.0
# Beta-binomial alpha + beta. Deliberately below the deepest library so
# extraction and sampling noise stay wider than binomial at any depth.
DEFAULT_READ_CONCENTRATION = 100_000.0
# Numerical guard for the beta parameterization at the extremes of the link.
_P_FLOOR = 1e-12


@dataclass(frozen=True)
class WastewaterOpsConfig:
    """One run's wastewater sampling policy.

    ``pathogen`` is the delay-catalog key written onto every sample, because that
    is what the fit filters on; ``pathogen_id`` is the ABM profile whose
    infections are counted. The two are different vocabularies, and conflating
    them silently produces a bundle whose wastewater rows are all dropped. Both
    are named by configuration: no pathogen is the simulator's to assume.
    """

    enabled: bool = False
    sampling_interval_epochs: int = DEFAULT_SAMPLING_INTERVAL_EPOCHS
    holding_tank_residence_hours: float = DEFAULT_RESIDENCE_HOURS
    collection_points: tuple[str, ...] = DEFAULT_COLLECTION_POINTS
    sequencing_depth: int = DEFAULT_SEQUENCING_DEPTH
    pathogen_shedding_to_reads_scale: float = DEFAULT_SHEDDING_TO_READS_SCALE
    background_read_fraction: float = DEFAULT_BACKGROUND_READ_FRACTION
    read_concentration: float = DEFAULT_READ_CONCENTRATION
    pathogen: str = ""
    pathogen_id: str = ""

    def __post_init__(self) -> None:
        if self.sampling_interval_epochs < 1:
            raise ValueError(
                "sampling_interval_epochs must be >= 1: "
                f"{self.sampling_interval_epochs}",
            )
        if self.holding_tank_residence_hours < 0.0:
            raise ValueError(
                "holding_tank_residence_hours must be >= 0: "
                f"{self.holding_tank_residence_hours}",
            )
        if self.sequencing_depth < 1:
            raise ValueError(f"sequencing_depth must be >= 1: {self.sequencing_depth}")
        if not self.collection_points:
            raise ValueError("collection_points must name at least one tap")
        if len(set(self.collection_points)) != len(self.collection_points):
            raise ValueError(f"collection_points must be unique: {self.collection_points}")
        if not 0.0 <= self.background_read_fraction < 1.0:
            raise ValueError(
                "background_read_fraction must be in [0, 1): "
                f"{self.background_read_fraction}",
            )
        if self.pathogen_shedding_to_reads_scale <= 0.0:
            raise ValueError(
                "pathogen_shedding_to_reads_scale must be positive: "
                f"{self.pathogen_shedding_to_reads_scale}",
            )
        if self.read_concentration <= 0.0:
            raise ValueError(f"read_concentration must be positive: {self.read_concentration}")
        if self.enabled and not self.pathogen:
            raise ValueError("pathogen must name the delay-catalog key for the samples")

    @property
    def informative_read_fraction(self) -> float:
        """Read fraction a fully shedding ship would produce."""
        return 1.0 - float(self.background_read_fraction)

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> WastewaterOpsConfig:
        """Build from a ``wastewater_surveillance`` config block (or nothing)."""
        cfg = dict(block or {})
        # ``None``/absent means "use the default tap"; an explicit empty list is a
        # configuration error, not a request to sample nothing.
        points = cfg.get("collection_points")
        if points is None:
            points = list(DEFAULT_COLLECTION_POINTS)
        return cls(
            enabled=bool(cfg.get("enabled", False)),
            sampling_interval_epochs=int(
                cfg.get("sampling_interval_epochs", DEFAULT_SAMPLING_INTERVAL_EPOCHS),
            ),
            holding_tank_residence_hours=float(
                cfg.get("holding_tank_residence_hours", DEFAULT_RESIDENCE_HOURS),
            ),
            collection_points=tuple(str(p) for p in points),
            sequencing_depth=int(cfg.get("sequencing_depth", DEFAULT_SEQUENCING_DEPTH)),
            pathogen_shedding_to_reads_scale=float(
                cfg.get(
                    "pathogen_shedding_to_reads_scale",
                    DEFAULT_SHEDDING_TO_READS_SCALE,
                ),
            ),
            background_read_fraction=float(
                cfg.get("background_read_fraction", DEFAULT_BACKGROUND_READ_FRACTION),
            ),
            read_concentration=float(
                cfg.get("read_concentration", DEFAULT_READ_CONCENTRATION),
            ),
            pathogen=str(cfg.get("pathogen", "")),
            pathogen_id=str(cfg.get("pathogen_id", "")),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Operating point as flat labels for campaign bookkeeping."""
        return {
            "wastewater_enabled": bool(self.enabled),
            "ww_sampling_interval_epochs": int(self.sampling_interval_epochs),
            "ww_residence_hours": float(self.holding_tank_residence_hours),
            "ww_sequencing_depth": int(self.sequencing_depth),
            "ww_collection_points": len(self.collection_points),
        }


def assign_collection_points(
    zone_names: Sequence[str],
    collection_points: Sequence[str],
) -> dict[str, str]:
    """Route each zone to a collection point in contiguous blocks.

    A stand-in for plumbing topology: zone order is stable for a platform, so
    splitting it into equal blocks gives every tap a fixed, reproducible share of
    the ship without a per-platform drain map. One tap collects the whole ship,
    which is what a single aft main sewer does.
    """
    points = [str(p) for p in collection_points]
    if not points:
        raise ValueError("collection_points must name at least one tap")
    zones = [str(z) for z in zone_names]
    if not zones:
        return {}
    n_points = len(points)
    routing: dict[str, str] = {}
    for index, zone in enumerate(zones):
        # ``index * n_points // n_zones`` walks the tap list once, in order.
        routing[zone] = points[min(index * n_points // len(zones), n_points - 1)]
    return routing


class WastewaterOpsSampler:
    """Accumulate holding-tank state and emit sentinel wastewater samples.

    Stateful by necessity: the tank at epoch *t* depends on every epoch before
    it, which is the whole reason residence time degrades attribution.
    """

    def __init__(
        self,
        config: WastewaterOpsConfig,
        *,
        rng: np.random.Generator,
        epoch_duration_hours: float = 1.0,
    ) -> None:
        self.config = config
        self.epoch_duration_hours = float(epoch_duration_hours or 1.0)
        self._rng = rng
        self._tank: dict[str, float] = {p: 0.0 for p in config.collection_points}
        self._samples: list[dict[str, Any]] = []

    @property
    def retention_weight(self) -> float:
        """Fraction of the tank carried into the next epoch (0 = direct tap)."""
        tau = float(self.config.holding_tank_residence_hours)
        if tau <= 0.0:
            return 0.0
        return float(np.exp(-self.epoch_duration_hours / tau))

    def tank_state(self) -> dict[str, float]:
        """Current tank prevalence per collection point."""
        return dict(self._tank)

    def samples(self) -> tuple[dict[str, Any], ...]:
        """Schema-shaped wastewater rows, in emission order."""
        return tuple(dict(row) for row in self._samples)

    def is_sampling_epoch(self, epoch: int) -> bool:
        """True when the configured cadence draws a sample this epoch.

        Epoch 0 never samples: the tanks are still empty, and the bundle indexes
        wastewater rows from epoch 1, so a draw there would collide with the
        first real sample and be pooled into it.
        """
        return int(epoch) >= 1 and int(epoch) % int(self.config.sampling_interval_epochs) == 0

    def observe_epoch(
        self,
        epoch: int,
        *,
        shedders_by_point: Mapping[str, float],
        population_by_point: Mapping[str, float],
    ) -> tuple[dict[str, Any], ...]:
        """Mix this epoch's inflow into the tanks and sample on cadence.

        The tank is advanced on *every* epoch even when nothing is sampled: the
        smearing is physical, not an artifact of when the crew shows up with a
        bottle.
        """
        weight = self.retention_weight
        for point in self.config.collection_points:
            aboard = float(population_by_point.get(point, 0.0))
            shedders = float(shedders_by_point.get(point, 0.0))
            inflow = shedders / aboard if aboard > 0.0 else 0.0
            self._tank[point] = weight * self._tank[point] + (1.0 - weight) * inflow
        if not self.is_sampling_epoch(epoch):
            return ()
        drawn = [self._draw_sample(int(epoch), point) for point in self.config.collection_points]
        self._samples.extend(drawn)
        return tuple(dict(row) for row in drawn)

    def _draw_sample(self, epoch: int, point: str) -> dict[str, Any]:
        """One beta-binomial read draw from one tap's current tank."""
        cfg = self.config
        share = cfg.pathogen_shedding_to_reads_scale * self._tank[point]
        mean = cfg.informative_read_fraction * min(max(share, 0.0), 1.0)
        depth = int(cfg.sequencing_depth)
        p = min(max(mean, _P_FLOOR), 1.0 - _P_FLOOR)
        conc = float(cfg.read_concentration)
        q = float(self._rng.beta(p * conc, (1.0 - p) * conc))
        reads = int(self._rng.binomial(depth, min(max(q, 0.0), 1.0)))
        return {
            "sample_epoch": int(epoch),
            "collection_point": str(point),
            "pathogen": cfg.pathogen,
            "pathogen_reads": min(reads, depth),
            "total_reads": depth,
        }
