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

``assay_mode`` chooses what the laboratory reports from that tank —
:mod:`wastewater_assays` holds the four modes and the physical chain they share.
Cadence, residence, and collection-point routing are the *operating* policy and
are identical across modes, on purpose: a mode comparison that also moved the
plumbing would not be a mode comparison. The mode-specific knobs
(``pathogen_shedding_to_reads_scale``, ``background_read_fraction``,
``sequencing_depth``) remain metagenomic knobs and are ignored by the other
modes rather than reinterpreted by them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.wastewater_assays import (
    ASSAY_AMPLICON,
    ASSAY_LONG_READ,
    ASSAY_METAGENOMIC,
    ASSAY_QPCR,
    AmpliconAssayConfig,
    LineageMixture,
    LongReadAssayConfig,
    QpcrAssayConfig,
    ShedLoadModel,
    StrainDeconvolutionConfig,
    deconvolve_lineages,
    gate_config,
    qpcr_reading,
    resolve_assay_mode,
)

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
# Below this the lagged remnant of a lineage is dropped from a tank rather than
# carried forever as a denormal: a tap keeps a mixture, not an archive.
_COMPOSITION_FLOOR = 1e-12


def _normalized_shares(mixture: Mapping[str, float] | None) -> dict[str, float]:
    """Genotype mixture as shares of one, dropping non-positive entries."""
    weights = {
        str(genotype): float(weight)
        for genotype, weight in (mixture or {}).items()
        if float(weight) > 0.0
    }
    total = sum(weights.values())
    if total <= 0.0:
        return {}
    return {genotype: weight / total for genotype, weight in weights.items()}


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
    assay_mode: str = ASSAY_METAGENOMIC
    qpcr: QpcrAssayConfig = field(default_factory=QpcrAssayConfig)
    amplicon: AmpliconAssayConfig = field(default_factory=AmpliconAssayConfig)
    long_read: LongReadAssayConfig = field(default_factory=LongReadAssayConfig)
    strain_deconvolution: StrainDeconvolutionConfig = field(
        default_factory=StrainDeconvolutionConfig,
    )
    load_model: ShedLoadModel = field(default_factory=ShedLoadModel)
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
        if self.assay_mode != resolve_assay_mode(self.assay_mode):
            raise ValueError(f"assay_mode must be normalized: {self.assay_mode!r}")
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
            assay_mode=resolve_assay_mode(cfg.get("assay_mode")),
            qpcr=QpcrAssayConfig.from_mapping(cfg.get("qpcr")),
            amplicon=AmpliconAssayConfig.from_mapping(cfg.get("amplicon")),
            long_read=LongReadAssayConfig.from_mapping(cfg.get("long_read")),
            strain_deconvolution=StrainDeconvolutionConfig.from_mapping(
                cfg.get("strain_deconvolution"),
            ),
            load_model=ShedLoadModel.from_mapping(cfg),
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
            "ww_assay_mode": str(self.assay_mode),
            "ww_sampling_interval_epochs": int(self.sampling_interval_epochs),
            "ww_residence_hours": float(self.holding_tank_residence_hours),
            "ww_sequencing_depth": int(self.sequencing_depth),
            "ww_collection_points": len(self.collection_points),
            "ww_strain_deconvolution": bool(self.strain_deconvolution.enabled),
        }

    @property
    def assay_depth(self) -> int:
        """Library depth the configured mode sequences at (0 for qPCR).

        ``sequencing_depth`` stays the metagenomic knob the ops scan sweeps;
        the sequencing modes carry their own depth because a 250 000-read
        shotgun library and a 50 000-read amplicon library are not the same cost
        or the same measurement.
        """
        depths = {
            ASSAY_METAGENOMIC: int(self.sequencing_depth),
            ASSAY_AMPLICON: int(self.amplicon.sequencing_depth),
            ASSAY_LONG_READ: int(self.long_read.sequencing_depth),
        }
        return depths.get(self.assay_mode, 0)


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
        self._tank: dict[str, float] = dict.fromkeys(config.collection_points, 0.0)
        self._composition: dict[str, dict[str, float]] = {
            point: {} for point in config.collection_points
        }
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

    def tank_composition(self) -> dict[str, dict[str, float]]:
        """Current genotype composition of each tank, on the prevalence scale.

        Lagged by the same residence weight as the prevalence itself, so a
        lineage introduced at a port call is still diluted by yesterday's mixture
        when the bottle is drawn. Empty when no composition is supplied, which is
        what a run without strain tracking hands over.
        """
        return {point: dict(mix) for point, mix in self._composition.items()}

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
        composition_by_point: Mapping[str, Mapping[str, float]] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Mix this epoch's inflow into the tanks and sample on cadence.

        The tank is advanced on *every* epoch even when nothing is sampled: the
        smearing is physical, not an artifact of when the crew shows up with a
        bottle.

        ``composition_by_point`` is the genotype mixture of what is being shed
        into each tap this epoch, shedding-weighted rather than per-capita: the
        pool's *composition* is set by emitted mass, even though its
        concentration proxy is shedder prevalence.
        """
        weight = self.retention_weight
        for point in self.config.collection_points:
            aboard = float(population_by_point.get(point, 0.0))
            shedders = float(shedders_by_point.get(point, 0.0))
            inflow = shedders / aboard if aboard > 0.0 else 0.0
            self._tank[point] = weight * self._tank[point] + (1.0 - weight) * inflow
            self._mix_composition(
                point,
                weight=weight,
                inflow=inflow,
                mixture=(composition_by_point or {}).get(point),
            )
        if not self.is_sampling_epoch(epoch):
            return ()
        drawn = [self._draw_sample(int(epoch), point) for point in self.config.collection_points]
        self._samples.extend(drawn)
        return tuple(dict(row) for row in drawn)

    def _mix_composition(
        self,
        point: str,
        *,
        weight: float,
        inflow: float,
        mixture: Mapping[str, float] | None,
    ) -> None:
        """Lag one tap's genotype composition by the tank's residence weight.

        Composition is carried on the same prevalence scale as the tank, so the
        two decay together: a tap that stops receiving a lineage loses it at the
        residence rate rather than instantly.
        """
        shares = _normalized_shares(mixture)
        lagged = {
            genotype: weight * mass
            for genotype, mass in self._composition[point].items()
            if weight * mass > _COMPOSITION_FLOOR
        }
        for genotype, share in shares.items():
            added = (1.0 - weight) * inflow * share
            if added > 0.0:
                lagged[genotype] = lagged.get(genotype, 0.0) + added
        self._composition[point] = lagged

    def _draw_sample(self, epoch: int, point: str) -> dict[str, Any]:
        """One sample from one tap's current tank, in the configured assay mode."""
        row = {
            "sample_epoch": int(epoch),
            "collection_point": str(point),
            "pathogen": self.config.pathogen,
            "assay_mode": str(self.config.assay_mode),
        }
        row.update(self._assay_fields(self._tank[point], self._composition[point]))
        return row

    def _assay_fields(
        self,
        tank_share: float,
        composition: Mapping[str, float],
    ) -> dict[str, Any]:
        """Assay-specific fields for a tank at the given shedder prevalence.

        Only the sequencing modes see the composition. ``qpcr`` has no library to
        deconvolve, and ``metagenomic`` stays blind by construction: at cruise
        prevalence it has no pathogen reads to divide, so it is the negative
        control for the whole channel rather than a mode that types badly.
        """
        mode = self.config.assay_mode
        if mode == ASSAY_METAGENOMIC:
            return self._metagenomic_fields(tank_share)
        if mode == ASSAY_QPCR:
            return self._qpcr_fields(tank_share)
        if mode == ASSAY_AMPLICON:
            return self._amplicon_fields(tank_share, composition)
        return self._long_read_fields(tank_share, composition)

    def _metagenomic_fields(self, tank_share: float) -> dict[str, Any]:
        """Beta-binomial compositional read draw: the pre-switch behaviour."""
        cfg = self.config
        share = cfg.pathogen_shedding_to_reads_scale * tank_share
        mean = cfg.informative_read_fraction * min(max(share, 0.0), 1.0)
        depth = int(cfg.sequencing_depth)
        p = min(max(mean, _P_FLOOR), 1.0 - _P_FLOOR)
        conc = float(cfg.read_concentration)
        q = float(self._rng.beta(p * conc, (1.0 - p) * conc))
        reads = int(self._rng.binomial(depth, min(max(q, 0.0), 1.0)))
        return {"pathogen_reads": min(reads, depth), "total_reads": depth}

    def _qpcr_fields(self, tank_share: float) -> dict[str, Any]:
        """Ct, detection, and the concentration a detected Ct implies."""
        reading = qpcr_reading(
            self.config.load_model.gc_per_l(tank_share),
            config=self.config.qpcr,
            rng=self._rng,
        )
        return reading.as_row()

    def _deconvolve(
        self,
        pathogen_reads: int,
        composition: Mapping[str, float],
    ) -> LineageMixture:
        """Lineage mixture recovered from a library's on-target reads."""
        return deconvolve_lineages(
            pathogen_reads,
            composition,
            config=self.config.strain_deconvolution,
            rng=self._rng,
        )

    def _amplicon_fields(
        self,
        tank_share: float,
        composition: Mapping[str, float],
    ) -> dict[str, Any]:
        """qPCR gate first, then on-target reads only if the gate opened.

        A library is not sequenced off a negative well, so a non-detect emits an
        empty library rather than a depth's worth of background: an amplicon run
        that reports reads it never generated would let the read channel claim
        precision the assay never had.
        """
        amplicon = self.config.amplicon
        gate = gate_config(
            self.config.qpcr,
            extraction_efficiency=amplicon.extraction_efficiency,
            lod_ct_threshold=amplicon.lod_ct_threshold,
        )
        reading = qpcr_reading(
            self.config.load_model.gc_per_l(tank_share),
            config=gate,
            rng=self._rng,
        )
        fields = reading.as_row()
        depth = int(amplicon.sequencing_depth) if reading.detected else 0
        fraction = (
            amplicon.on_target_fraction(reading.copies_per_reaction)
            if reading.detected
            else 0.0
        )
        reads = int(self._rng.binomial(depth, min(max(fraction, 0.0), 1.0))) if depth else 0
        pathogen_reads = min(reads, depth)
        lineages = self._deconvolve(pathogen_reads, composition)
        fields.update(
            {
                "pathogen_reads": pathogen_reads,
                "total_reads": depth,
                "primer_target": amplicon.primer_targets[0],
                "genotype": lineages.consensus_genotype,
            },
        )
        fields.update(lineages.as_row())
        return fields

    def _long_read_fields(
        self,
        tank_share: float,
        composition: Mapping[str, float],
    ) -> dict[str, Any]:
        """Confirmation run: the same gate, its own depth, and a turnaround.

        With deconvolution configured, ``genotype`` is the consensus lineage the
        reads actually resolved; without it, the configured reference (or
        ``None``), because a typing call the assay did not make is invented.
        """
        long_read = self.config.long_read
        gate = gate_config(
            self.config.qpcr,
            extraction_efficiency=long_read.extraction_efficiency,
            lod_ct_threshold=long_read.lod_ct_threshold,
        )
        reading = qpcr_reading(
            self.config.load_model.gc_per_l(tank_share),
            config=gate,
            rng=self._rng,
        )
        fields = reading.as_row()
        depth = int(long_read.sequencing_depth) if reading.detected else 0
        reads = int(self._rng.binomial(depth, long_read.on_target_fraction)) if depth else 0
        pathogen_reads = min(reads, depth)
        lineages = self._deconvolve(pathogen_reads, composition)
        reference = long_read.reference_genotype if reading.detected else None
        fields.update(
            {
                "pathogen_reads": pathogen_reads,
                "total_reads": depth,
                "turnaround_hours": float(long_read.turnaround_hours),
                "genotype": lineages.consensus_genotype or reference,
            },
        )
        fields.update(lineages.as_row())
        return fields
