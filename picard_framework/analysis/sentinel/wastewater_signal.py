"""Compositional wastewater as a second observation of the same incidence curve.

Not a second hazard channel. A ship's greywater is a closed, integrating system:
what it measures is the prevalence of shedders *aboard*, whatever port they were
infected at, delayed by the holding time of the plumbing (spec 1.3). Given that,
three things follow, and this module exists to enforce them:

1. **The likelihood is on read counts, not concentration.** CTB's modality is
   Dirichlet-multinomial metagenomics, so ``pathogen_reads`` out of
   ``total_reads`` with beta-binomial overdispersion. A normal on
   log-concentration understates uncertainty at the depths that actually occur,
   and ``concentration_copies_per_l`` only exists for external qPCR datasets.
2. **Correlated samples must not be counted as independent evidence.** Several
   collection points sampled the same epoch are replicate draws on one holding
   tank, so they are pooled into a single trial rather than multiplied into the
   posterior; and the pooled depth is capped
   (``max_effective_reads``), because a 10^6-read library is not 10^6
   independent observations of that epoch's prevalence. Without both, the channel
   would silently outvote the clinical line list that carries the port
   information.
3. **It sharpens timing, never attribution.** The signal enters as
   ``latent shedder prevalence``, so it constrains the incidence curve the port
   hazards and the onboard renewal term compete over. It never receives a port
   label of its own.

The link is deliberately on the log-prevalence scale::

    logit(read_fraction[t]) = ww_logit_base + ww_slope * log(share[t] + eps)

``ww_slope`` is then the elasticity of the read fraction in shedder prevalence,
and ``ww_slope -> 0`` is the "this channel carries no information" hypothesis the
posterior is allowed to reach. A linear ``base + scale * share`` link would need
clipping to stay a probability, which is exactly the kink samplers handle worst.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.incubation import (
    DelayDistribution,
    delay_from_spec,
    load_delay_catalog,
)
from picard_framework.analysis.sentinel.observations import (
    ObservationBundle,
    WastewaterSample,
)

WASTEWATER_CHANNEL = "wastewater"

# Fallbacks for a catalog with no ``wastewater`` block.
DEFAULT_RESIDENCE_LAG_HOURS = 12.0
# A metagenomic run is tens of millions of reads, but those reads are one draw on
# one holding tank: the cap is what stops sequencing depth from standing in for
# replication of the epoch's prevalence.
DEFAULT_MAX_EFFECTIVE_READS = 1_000_000
# Beta-binomial concentration: alpha + beta. Below the capped depth on purpose,
# so the residual sampling/extraction noise stays wider than binomial.
DEFAULT_CONCENTRATION_PRIOR_MEDIAN = 100_000.0
DEFAULT_CONCENTRATION_PRIOR_LOG_SD = 1.5
DEFAULT_SLOPE_PRIOR_MEAN = 1.0
DEFAULT_SLOPE_PRIOR_SD = 0.5
# With ``slope = 1`` the base is the read fraction a fully shedding ship would
# produce: ~1e-3 of the library, so a realistic few-percent prevalence lands at
# the 1e-5 range metagenomics actually reports.
DEFAULT_BASE_LOGIT_PRIOR_MEAN = -7.0
DEFAULT_BASE_LOGIT_PRIOR_SD = 2.0
# Guards log(0) for an epoch with no shedders; 1e-6 of the ship's complement is
# well below one person, so it cannot be mistaken for a real prevalence.
SHARE_FLOOR = 1e-6


@dataclass(frozen=True)
class SheddingKernel:
    """``P(still shedding at lag k)`` on the epoch grid, offset by holding time.

    A *survival* kernel, not a delay pmf: convolved with incidence it gives the
    number of people shedding into the system at each epoch, which is what a
    composite wastewater sample measures. A delay pmf would model the sample as
    tracking delayed onsets, losing the integration that makes the channel
    informative between onsets.
    """

    pathogen: str
    epoch_hours: float
    residence_lag_epochs: int
    weights: tuple[float, ...]

    @property
    def array(self) -> np.ndarray:
        """Kernel as a numpy array, lag 0 first."""
        return np.asarray(self.weights, dtype=float)

    @property
    def max_lag(self) -> int:
        """Largest lag the kernel reaches."""
        return len(self.weights) - 1

    @property
    def mean_shedding_hours(self) -> float:
        """Area under the survival curve: mean hours a case sheds for."""
        return float(self.array.sum() * self.epoch_hours)


def wastewater_config(catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """``wastewater`` block of the delay catalog, with defaults filled in."""
    doc = dict(catalog) if catalog is not None else load_delay_catalog()
    block = dict(doc.get("wastewater") or {})
    return {
        "residence_lag_hours": float(
            block.get("residence_lag_hours", DEFAULT_RESIDENCE_LAG_HOURS),
        ),
        "max_effective_reads": int(
            block.get("max_effective_reads", DEFAULT_MAX_EFFECTIVE_READS),
        ),
    }


def shedding_kernel(
    pathogen: str,
    *,
    epoch_hours: float,
    residence_lag_hours: float | None = None,
    catalog: Mapping[str, Any] | None = None,
) -> SheddingKernel:
    """Shedding-survival kernel for a pathogen, shifted by the holding time.

    Falls back to the generation interval when the catalog entry has no
    ``shedding`` block: a pathogen whose serial interval is known but whose
    shedding duration is not is better served by an explicit approximation than
    by silently dropping the channel.
    """
    doc = dict(catalog) if catalog is not None else load_delay_catalog()
    entry = (doc.get("distributions") or {}).get(pathogen)
    if entry is None:
        known = sorted((doc.get("distributions") or {}))
        raise KeyError(f"No delay distributions for {pathogen!r}; known: {known}")
    spec = entry.get("shedding") or entry.get("generation") or entry["incubation"]
    duration: DelayDistribution = delay_from_spec(
        spec, name=f"{pathogen}.shedding", epoch_hours=epoch_hours,
    )
    lag_hours = (
        float(residence_lag_hours)
        if residence_lag_hours is not None
        else wastewater_config(doc)["residence_lag_hours"]
    )
    if lag_hours < 0.0:
        raise ValueError(f"residence_lag_hours must be >= 0: {lag_hours}")
    lag_epochs = int(round(lag_hours / float(epoch_hours or 1.0)))
    # Survival: P(duration > k epochs) = 1 - cdf[k], with lag 0 = 1.0 (a case is
    # shedding the epoch it is infected).
    survival = np.concatenate(([1.0], 1.0 - duration.cdf[:-1]))
    weights = np.concatenate((np.zeros(lag_epochs, dtype=float), survival))
    return SheddingKernel(
        pathogen=pathogen,
        epoch_hours=float(epoch_hours or 1.0),
        residence_lag_epochs=lag_epochs,
        weights=tuple(float(w) for w in weights),
    )


@dataclass(frozen=True)
class PooledSample:
    """All wastewater reads for one voyage-epoch, as a single trial.

    ``n_collection_points`` is kept so a reader can see how many correlated
    replicates went into the trial, and ``total_reads`` alongside
    ``effective_reads`` so the depth cap is visible rather than implicit.

    ``effective_reads`` is the *mean* depth across those collection points, capped:
    replicate taps sharpen the estimate of one epoch's fraction, they do not
    observe more epochs.
    """

    voyage_id: str
    epoch: int
    pathogen_reads: int
    total_reads: int
    effective_reads: int
    effective_pathogen_reads: int
    n_collection_points: int

    @property
    def read_fraction(self) -> float:
        """Observed pathogen read fraction (0.0 for an empty library)."""
        return self.pathogen_reads / self.total_reads if self.total_reads > 0 else 0.0


def pool_wastewater(
    bundle: ObservationBundle,
    *,
    pathogen: str,
    observation_end_epoch: int,
    max_effective_reads: int = DEFAULT_MAX_EFFECTIVE_READS,
) -> tuple[PooledSample, ...]:
    """One trial per sampled epoch, capped in depth, in epoch order.

    Samples for other pathogens, empty libraries, and epochs past the observation
    window are dropped. Pooling is the whole point: the alternative — one
    beta-binomial term per collection point — multiplies one epoch's evidence by
    however many taps the ship happened to sample.
    """
    if max_effective_reads <= 0:
        raise ValueError(f"max_effective_reads must be positive: {max_effective_reads}")
    by_epoch: dict[int, list[WastewaterSample]] = {}
    for sample in bundle.wastewater_samples:
        if sample.pathogen != pathogen:
            continue
        if sample.total_reads <= 0:
            continue
        if sample.sample_epoch < 1 or sample.sample_epoch > int(observation_end_epoch):
            continue
        if sample.pathogen_reads > sample.total_reads:
            raise ValueError(
                f"{bundle.voyage_id} epoch {sample.sample_epoch}: pathogen_reads "
                f"{sample.pathogen_reads} exceeds total_reads {sample.total_reads}",
            )
        by_epoch.setdefault(int(sample.sample_epoch), []).append(sample)

    pooled: list[PooledSample] = []
    for epoch in sorted(by_epoch):
        group = by_epoch[epoch]
        reads = sum(s.pathogen_reads for s in group)
        total = sum(s.total_reads for s in group)
        effective = min(total // len(group), int(max_effective_reads))
        # Down-scaling keeps the observed fraction and discards only the claimed
        # precision, which is the part the correlation invalidates.
        effective_reads = int(round(reads * effective / total)) if total else 0
        pooled.append(
            PooledSample(
                voyage_id=bundle.voyage_id,
                epoch=epoch,
                pathogen_reads=reads,
                total_reads=total,
                effective_reads=effective,
                effective_pathogen_reads=min(effective_reads, effective),
                n_collection_points=len(group),
            ),
        )
    return tuple(pooled)


def shedder_prevalence(
    incidence_total: Sequence[float] | np.ndarray,
    kernel: SheddingKernel | Sequence[float] | np.ndarray,
) -> np.ndarray:
    """People shedding into the system per epoch, from total new infections.

    Takes either a :class:`SheddingKernel` or the kernel weights already on the
    Stan data block, so the assembled model and the reference share one path.
    """
    incidence = np.asarray(list(incidence_total), dtype=float)
    weights = (
        kernel.array
        if isinstance(kernel, SheddingKernel)
        else np.asarray(list(kernel), dtype=float)
    )
    if incidence.size == 0 or weights.size == 0:
        return np.zeros_like(incidence)
    return np.convolve(incidence, weights)[: incidence.size]


def expected_read_fraction(
    share: Sequence[float] | np.ndarray,
    *,
    logit_base: float,
    slope: float,
) -> np.ndarray:
    """``inv_logit(logit_base + slope * log(share + eps))`` — the link, in numpy."""
    x = np.asarray(list(share), dtype=float)
    logit = logit_base + slope * np.log(np.clip(x, 0.0, None) + SHARE_FLOOR)
    # Stable inv_logit for the very negative logits a low read fraction implies.
    return np.exp(-np.logaddexp(0.0, -logit))


def beta_binomial_logpmf(
    successes: Sequence[int] | np.ndarray,
    trials: Sequence[int] | np.ndarray,
    mean: Sequence[float] | np.ndarray,
    concentration: float,
) -> np.ndarray:
    """Beta-binomial log pmf with a mean/concentration parameterization.

    ``alpha = mean * concentration``, ``beta = (1 - mean) * concentration``, so
    ``concentration`` is the only overdispersion knob and the mean is the link's
    output. Mirrors Stan's ``beta_binomial_lpmf`` term for term.
    """
    k = np.asarray(list(successes), dtype=float)
    n = np.asarray(list(trials), dtype=float)
    p = np.clip(np.asarray(list(mean), dtype=float), 1e-12, 1.0 - 1e-12)
    conc = float(concentration)
    if conc <= 0.0:
        raise ValueError(f"concentration must be positive: {conc}")
    alpha = p * conc
    beta = (1.0 - p) * conc
    lgamma = np.vectorize(math.lgamma)
    return (
        lgamma(n + 1.0)
        - lgamma(k + 1.0)
        - lgamma(n - k + 1.0)
        + lgamma(k + alpha)
        + lgamma(n - k + beta)
        - lgamma(n + alpha + beta)
        + lgamma(alpha + beta)
        - lgamma(alpha)
        - lgamma(beta)
    )


def sample_rows(samples: Iterable[PooledSample]) -> list[dict[str, Any]]:
    """Flatten pooled samples for reporting."""
    return [
        {
            "voyage_id": s.voyage_id,
            "epoch": s.epoch,
            "pathogen_reads": s.pathogen_reads,
            "total_reads": s.total_reads,
            "effective_reads": s.effective_reads,
            "n_collection_points": s.n_collection_points,
            "read_fraction": s.read_fraction,
        }
        for s in samples
    ]
