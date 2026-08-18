"""Compositional wastewater as a second observation of the same incidence curve.

Not a second hazard channel. A ship's greywater is a closed, integrating system:
what it measures is the prevalence of shedders *aboard*, whatever port they were
infected at, delayed by the holding time of the plumbing (spec 1.3). Given that,
three things follow, and this module exists to enforce them:

1. **The likelihood follows the assay, not a house convention.** A shotgun
   library is ``pathogen_reads`` out of ``total_reads`` with beta-binomial
   overdispersion — a normal on log-concentration would understate uncertainty at
   the depths that actually occur. An RT-qPCR result is a concentration with a
   limit of detection, and its non-detects are *censored*, not zero, so it gets a
   Tobit term on log10 copies/L. The two channels share the latent prevalence and
   nothing else; a bundle may carry both, and each row is routed by the fields it
   populates (``pool_wastewater`` for reads, ``pool_concentrations`` for qPCR).
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


# qPCR channel. With slope 1 the link is the physical chain in
# ``wastewater_assays``: a decade more shedder prevalence is a decade more
# copies per litre. The intercept is then log10 of the concentration a fully
# shedding ship would present (1e10 gc/person/day into 30 L/person/day), and its
# prior is wide enough to absorb a wrong shedding rate without forcing the slope
# to absorb it instead.
DEFAULT_CONC_INTERCEPT_PRIOR_MEAN = 8.5
DEFAULT_CONC_INTERCEPT_PRIOR_SD = 1.5
DEFAULT_CONC_SLOPE_PRIOR_MEAN = 1.0
DEFAULT_CONC_SLOPE_PRIOR_SD = 0.3
# Residual sd on log10 copies/L: extraction and Ct noise, roughly half a decade.
DEFAULT_CONC_SIGMA_PRIOR_SCALE = 0.5
# Guards log10(0) for a tank the assay reports as empty.
CONCENTRATION_FLOOR = 1e-3


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


def _in_observation_window(sample: WastewaterSample, observation_end_epoch: int) -> bool:
    return 1 <= sample.sample_epoch <= int(observation_end_epoch)


def _group_read_samples(
    bundle: ObservationBundle,
    pathogen: str,
    observation_end_epoch: int,
) -> dict[int, list[WastewaterSample]]:
    by_epoch: dict[int, list[WastewaterSample]] = {}
    for sample in bundle.wastewater_samples:
        if sample.pathogen != pathogen or sample.total_reads <= 0:
            continue
        if not _in_observation_window(sample, observation_end_epoch):
            continue
        if sample.pathogen_reads > sample.total_reads:
            raise ValueError(
                f"{bundle.voyage_id} epoch {sample.sample_epoch}: pathogen_reads "
                f"{sample.pathogen_reads} exceeds total_reads {sample.total_reads}",
            )
        by_epoch.setdefault(int(sample.sample_epoch), []).append(sample)
    return by_epoch


def _pooled_read_epoch(
    bundle: ObservationBundle,
    epoch: int,
    group: Sequence[WastewaterSample],
    max_effective_reads: int,
) -> PooledSample:
    reads = sum(s.pathogen_reads for s in group)
    total = sum(s.total_reads for s in group)
    effective = min(total // len(group), int(max_effective_reads))
    # Down-scaling keeps the observed fraction and discards only the claimed
    # precision, which is the part the correlation invalidates.
    effective_reads = int(round(reads * effective / total)) if total else 0
    return PooledSample(
        voyage_id=bundle.voyage_id,
        epoch=epoch,
        pathogen_reads=reads,
        total_reads=total,
        effective_reads=effective,
        effective_pathogen_reads=min(effective_reads, effective),
        n_collection_points=len(group),
    )


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
    by_epoch = _group_read_samples(bundle, pathogen, observation_end_epoch)
    return tuple(
        _pooled_read_epoch(bundle, epoch, by_epoch[epoch], max_effective_reads)
        for epoch in sorted(by_epoch)
    )


@dataclass(frozen=True)
class PooledConcentration:
    """All qPCR results for one voyage-epoch, as a single observation.

    ``censored`` says the epoch's taps all came back below the limit of
    detection, in which case ``log10_copies_per_l`` holds the bound rather than a
    measurement. A censored epoch is evidence — it bounds prevalence from above —
    so it is kept, and the likelihood integrates the normal below the bound
    instead of pretending the tank was empty.

    ``n_detected`` alongside ``n_collection_points`` keeps the replicate
    structure visible: taps sampled the same epoch are draws on one tank, so
    their detections are averaged into one observation and never multiplied into
    the posterior.
    """

    voyage_id: str
    epoch: int
    log10_copies_per_l: float
    censored: bool
    n_collection_points: int
    n_detected: int


def _log10_floor(value: float) -> float:
    """``log10`` with a floor, so an empty tank stays finite."""
    return math.log10(max(float(value), CONCENTRATION_FLOOR))


def _group_concentration_samples(
    bundle: ObservationBundle,
    pathogen: str,
    observation_end_epoch: int,
) -> dict[int, list[WastewaterSample]]:
    by_epoch: dict[int, list[WastewaterSample]] = {}
    for sample in bundle.wastewater_samples:
        if sample.pathogen != pathogen or not sample.has_concentration_observation:
            continue
        if not _in_observation_window(sample, observation_end_epoch):
            continue
        by_epoch.setdefault(int(sample.sample_epoch), []).append(sample)
    return by_epoch


def _pooled_concentration_epoch(
    bundle: ObservationBundle,
    epoch: int,
    group: Sequence[WastewaterSample],
) -> PooledConcentration:
    detected = [
        s.concentration_copies_per_l
        for s in group
        if s.concentration_copies_per_l is not None
    ]
    bounds = [s.lod_copies_per_l for s in group if s.lod_copies_per_l is not None]
    if detected:
        value = sum(_log10_floor(c) for c in detected) / len(detected)
    else:
        value = sum(_log10_floor(b) for b in bounds) / len(bounds)
    return PooledConcentration(
        voyage_id=bundle.voyage_id,
        epoch=epoch,
        log10_copies_per_l=float(value),
        censored=not detected,
        n_collection_points=len(group),
        n_detected=len(detected),
    )


def pool_concentrations(
    bundle: ObservationBundle,
    *,
    pathogen: str,
    observation_end_epoch: int,
) -> tuple[PooledConcentration, ...]:
    """One qPCR observation per sampled epoch, in epoch order.

    Detected taps are averaged on the log10 scale, which is the scale the
    likelihood is on and the scale Ct is linear in. An epoch with no detection
    is censored at the mean limit of detection of the taps that reported one.
    Rows carrying no concentration information at all (a shotgun library, an
    external row without an LOD) are left to the read channel.
    """
    by_epoch = _group_concentration_samples(bundle, pathogen, observation_end_epoch)
    return tuple(
        _pooled_concentration_epoch(bundle, epoch, by_epoch[epoch])
        for epoch in sorted(by_epoch)
    )


def expected_log10_concentration(
    share: Sequence[float] | np.ndarray,
    *,
    intercept: float,
    slope: float,
) -> np.ndarray:
    """``intercept + slope * log10(share + eps)`` — the qPCR link, in numpy."""
    x = np.asarray(list(share), dtype=float)
    return intercept + slope * np.log10(np.clip(x, 0.0, None) + SHARE_FLOOR)


def censored_normal_logpdf(
    observed: Sequence[float] | np.ndarray,
    mean: Sequence[float] | np.ndarray,
    sigma: float,
    censored: Sequence[bool] | np.ndarray,
) -> np.ndarray:
    """Tobit term per observation: density if measured, lower tail if censored.

    Mirrors ``normal_lpdf`` / ``normal_lcdf`` in ``sentinel_fleet.stan`` term for
    term, so the numpy reference sampler and Stan cannot disagree about what a
    non-detect is worth.
    """
    y = np.asarray(list(observed), dtype=float)
    mu = np.asarray(list(mean), dtype=float)
    is_censored = np.asarray(list(censored), dtype=bool)
    sd = float(sigma)
    if sd <= 0.0:
        raise ValueError(f"sigma must be positive: {sd}")
    z = (y - mu) / sd
    density = -0.5 * z**2 - math.log(sd) - 0.5 * math.log(2.0 * math.pi)
    # log Phi(z) via erfc, which stays finite for the very negative z a bound far
    # above the expected concentration produces.
    erfc = np.vectorize(math.erfc)
    tail = np.log(np.clip(0.5 * erfc(-z / math.sqrt(2.0)), 1e-300, None))
    return np.where(is_censored, tail, density)


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
