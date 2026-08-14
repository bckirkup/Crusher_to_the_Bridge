"""Delay distributions, forward convolution, renewal, and back-calculation.

Everything the sentinel likelihood needs about *timing*, in pure numpy so it is
testable without cmdstan:

- discretized incubation and generation-interval pmfs on the run's epoch grid
- the forward map infection epochs -> onset epochs (``expected_onsets``)
- the discrete renewal term for onboard secondaries (``renewal_incidence``)
- the right-censoring survival factor ``P(onset <= T_end | infection epoch)``
  (spec 1.6 — without it late ports look safe)
- Richardson-Lucy back-calculation of infection epochs from onsets

Delays are configured in *hours* (``data/incubation_distributions.json``) and
discretized per run, because the epoch grid is a property of the simulation, not
of the pathogen.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from importlib import resources
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis._io import read_json

LOGNORMAL = "lognormal"
DISCRETE = "discrete"

_DISTRIBUTIONS_FILE = "incubation_distributions.json"


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass(frozen=True)
class DelayDistribution:
    """A delay pmf on the epoch grid: ``pmf[k]`` = P(delay lands in epoch k).

    ``k`` counts epochs *after* the exposure epoch, so ``pmf[0]`` is same-epoch
    onset. Mass beyond ``max_hours`` is truncated and the pmf renormalized, so
    it always sums to 1 and can be read as a conditional distribution given the
    delay is within support.
    """

    name: str
    kind: str
    epoch_hours: float
    pmf: tuple[float, ...]

    @property
    def max_lag(self) -> int:
        """Largest lag with mass (in epochs)."""
        return len(self.pmf) - 1

    @property
    def weights(self) -> np.ndarray:
        """pmf as a numpy array."""
        return np.asarray(self.pmf, dtype=float)

    @property
    def cdf(self) -> np.ndarray:
        """Cumulative delay distribution over epoch lags."""
        return np.cumsum(self.weights)

    def mass_within(self, lag_epochs: int) -> float:
        """``P(delay <= lag_epochs)`` — the censoring survival factor (1.6)."""
        if lag_epochs < 0:
            return 0.0
        if lag_epochs >= self.max_lag:
            return 1.0
        return float(self.cdf[lag_epochs])

    def weight_at(self, lag_epochs: int) -> float:
        """pmf mass at a single lag (0.0 outside support)."""
        if lag_epochs < 0 or lag_epochs > self.max_lag:
            return 0.0
        return float(self.pmf[lag_epochs])

    def quantile_hours(self, q: float) -> float:
        """Delay quantile in hours, from the discretized pmf."""
        if not 0.0 < q < 1.0:
            raise ValueError(f"quantile must be in (0, 1): {q}")
        idx = int(np.searchsorted(self.cdf, q, side="left"))
        idx = min(idx, self.max_lag)
        # Epoch k covers (k, k+1] * epoch_hours; report its upper edge.
        return (idx + 1) * self.epoch_hours

    @property
    def mean_hours(self) -> float:
        """Mean delay in hours (epoch midpoints)."""
        lags = np.arange(len(self.pmf), dtype=float) + 0.5
        return float((lags * self.weights).sum() * self.epoch_hours)

    @property
    def iqr_hours(self) -> float:
        """Interquartile delay width — the port-resolution criterion (1.8)."""
        return self.quantile_hours(0.75) - self.quantile_hours(0.25)

    def strictly_lagged(self) -> DelayDistribution:
        """Same distribution with same-epoch mass removed and renormalized.

        A self-exciting term must not let an infection generate secondaries in
        its own epoch; that would be an instantaneous feedback loop rather than
        a generation interval.
        """
        if self.max_lag < 1:
            raise ValueError(f"{self.name}: no lagged mass to renormalize")
        lagged = np.array(self.pmf, dtype=float)
        lagged[0] = 0.0
        total = lagged.sum()
        if total <= 0.0:
            raise ValueError(f"{self.name}: all mass is same-epoch")
        return DelayDistribution(
            name=self.name,
            kind=self.kind,
            epoch_hours=self.epoch_hours,
            pmf=tuple(lagged / total),
        )


def lognormal_delay(
    *,
    name: str,
    median_hours: float,
    sigma: float,
    epoch_hours: float,
    max_hours: float,
) -> DelayDistribution:
    """Discretize a lognormal delay onto the epoch grid by CDF differences."""
    if median_hours <= 0.0:
        raise ValueError(f"{name}: median_hours must be positive")
    if sigma <= 0.0:
        raise ValueError(f"{name}: sigma must be positive")
    hours = float(epoch_hours or 1.0)
    if hours <= 0.0:
        raise ValueError(f"{name}: epoch_hours must be positive")
    n_bins = max(1, int(math.ceil(float(max_hours) / hours)))
    mu = math.log(float(median_hours))
    edges = [_normal_cdf((math.log(k * hours) - mu) / sigma) if k > 0 else 0.0
             for k in range(n_bins + 1)]
    masses = np.diff(np.asarray(edges, dtype=float))
    total = masses.sum()
    if total <= 0.0:
        raise ValueError(f"{name}: no mass within max_hours={max_hours}")
    return DelayDistribution(
        name=name,
        kind=LOGNORMAL,
        epoch_hours=hours,
        pmf=tuple(masses / total),
    )


def discrete_delay(
    *,
    name: str,
    weights: Sequence[float],
    epoch_hours: float,
) -> DelayDistribution:
    """Delay pmf given directly on the epoch grid (normalized here)."""
    arr = np.asarray(list(weights), dtype=float)
    if arr.size == 0:
        raise ValueError(f"{name}: empty delay weights")
    if (arr < 0.0).any():
        raise ValueError(f"{name}: negative delay weight")
    total = arr.sum()
    if total <= 0.0:
        raise ValueError(f"{name}: delay weights sum to zero")
    return DelayDistribution(
        name=name,
        kind=DISCRETE,
        epoch_hours=float(epoch_hours or 1.0),
        pmf=tuple(arr / total),
    )


def delay_from_spec(
    spec: Mapping[str, Any],
    *,
    name: str,
    epoch_hours: float,
) -> DelayDistribution:
    """Build a delay distribution from a config block."""
    family = str(spec.get("family") or LOGNORMAL)
    if family == LOGNORMAL:
        return lognormal_delay(
            name=name,
            median_hours=float(spec["median_hours"]),
            sigma=float(spec["sigma"]),
            epoch_hours=epoch_hours,
            max_hours=float(spec.get("max_hours") or 240.0),
        )
    if family == DISCRETE:
        return discrete_delay(
            name=name,
            weights=list(spec["weights"]),
            epoch_hours=epoch_hours,
        )
    raise ValueError(f"{name}: unknown delay family {family!r}")


def _packaged_catalog() -> dict[str, Any]:
    root = resources.files("picard_framework.analysis.sentinel")
    text = (root / "data" / _DISTRIBUTIONS_FILE).read_text(encoding="utf-8")
    return json.loads(text)


def load_delay_catalog(path: str | None = None) -> dict[str, Any]:
    """Load the delay-distribution catalog (bundled by default)."""
    raw = _packaged_catalog() if path is None else read_json(path)
    if not isinstance(raw, dict):
        raise ValueError("delay distribution catalog must be an object")
    dists = raw.get("distributions")
    if not isinstance(dists, dict) or not dists:
        raise ValueError("delay distribution catalog has no distributions")
    return raw


def default_pathogen(catalog: Mapping[str, Any] | None = None) -> str:
    """The catalog's declared default (Law 2: no pathogen names in code)."""
    doc = dict(catalog) if catalog is not None else load_delay_catalog()
    name = doc.get("default_pathogen")
    if not isinstance(name, str) or not name:
        raise ValueError("delay distribution catalog declares no default_pathogen")
    return name


def delays_for_pathogen(
    pathogen: str | None = None,
    *,
    epoch_hours: float = 1.0,
    catalog: Mapping[str, Any] | None = None,
) -> tuple[DelayDistribution, DelayDistribution]:
    """``(incubation, generation)`` for a pathogen on this epoch grid."""
    doc = dict(catalog) if catalog is not None else load_delay_catalog()
    pathogen = pathogen if pathogen is not None else default_pathogen(doc)
    entry = (doc.get("distributions") or {}).get(pathogen)
    if entry is None:
        known = sorted((doc.get("distributions") or {}))
        raise KeyError(f"No delay distributions for {pathogen!r}; known: {known}")
    incubation = delay_from_spec(
        entry["incubation"],
        name=f"{pathogen}.incubation",
        epoch_hours=epoch_hours,
    )
    generation = delay_from_spec(
        entry.get("generation") or entry["incubation"],
        name=f"{pathogen}.generation",
        epoch_hours=epoch_hours,
    )
    return incubation, generation


def port_resolution_adequate(
    incubation: DelayDistribution,
    min_inter_port_hours: float,
) -> bool:
    """Whether ports are separable at all for this pathogen (spec 1.8).

    ``IQR(incubation) < min inter-port interval``; otherwise the honest unit of
    attribution is a port *window set*, not a port.
    """
    if min_inter_port_hours <= 0.0:
        return False
    return incubation.iqr_hours < float(min_inter_port_hours)


def expected_onsets(
    infections: Sequence[float] | np.ndarray,
    delay: DelayDistribution,
    *,
    n_epochs: int | None = None,
) -> np.ndarray:
    """Forward map: infection epochs -> expected onsets on the same grid.

    Index 0 is the first observation epoch. Mass that lands past the returned
    horizon is dropped rather than piled onto the last epoch — that loss *is*
    the censoring the survival factor accounts for.
    """
    infect = np.asarray(list(infections), dtype=float)
    horizon = int(n_epochs if n_epochs is not None else infect.size)
    if horizon <= 0:
        return np.zeros(0, dtype=float)
    full = np.convolve(infect, delay.weights)
    onsets = np.zeros(horizon, dtype=float)
    take = min(horizon, full.size)
    onsets[:take] = full[:take]
    return onsets


def renewal_incidence(
    imported: Sequence[float] | np.ndarray,
    r_onboard: float,
    generation: DelayDistribution,
) -> np.ndarray:
    """Imported infections plus onboard secondaries (discrete renewal).

    ``incidence[t] = imported[t] + R * sum_{k>=1} w[k] * incidence[t-k]``, with
    ``w`` strictly lagged. Replaces the sketch's whole-case mixture, which is
    not implementable over an unordered case set (spec 1.5).
    """
    if r_onboard < 0.0:
        raise ValueError(f"r_onboard must be non-negative: {r_onboard}")
    imports = np.asarray(list(imported), dtype=float)
    lagged = generation.strictly_lagged().weights
    incidence = np.zeros(imports.size, dtype=float)
    for t in range(imports.size):
        secondary = 0.0
        for k in range(1, min(t, lagged.size - 1) + 1):
            secondary += lagged[k] * incidence[t - k]
        incidence[t] = imports[t] + r_onboard * secondary
    return incidence


def observed_onset_fraction(
    epochs_remaining: int,
    delay: DelayDistribution,
) -> float:
    """``P(onset <= T_end | infected)`` given epochs left in the window.

    The one term whose absence makes the model report early ports as the
    dangerous ones (spec 1.6): a last-port infection usually has onset after
    disembarkation and never reaches the line list.
    """
    return delay.mass_within(int(epochs_remaining))


def censoring_weights(
    infection_epochs: Sequence[int],
    observation_end_epoch: int,
    delay: DelayDistribution,
) -> np.ndarray:
    """Per-infection-epoch observed fractions (vectorized 1.6 correction)."""
    return np.asarray(
        [
            observed_onset_fraction(int(observation_end_epoch) - int(epoch), delay)
            for epoch in infection_epochs
        ],
        dtype=float,
    )


def deconvolve_onsets(
    onsets: Sequence[float] | np.ndarray,
    delay: DelayDistribution,
    *,
    iterations: int = 60,
    tol: float = 1e-10,
) -> np.ndarray:
    """Back-calculate infection epochs from onsets (Richardson-Lucy EM).

    The per-epoch normalizer is the *observable* delay mass for that infection
    epoch, so infections late in the window are not shrunk toward zero merely
    because most of their onsets fall outside it.
    """
    obs = np.asarray(list(onsets), dtype=float)
    if (obs < 0.0).any():
        raise ValueError("onset counts must be non-negative")
    n = obs.size
    if n == 0:
        return np.zeros(0, dtype=float)
    w = delay.weights
    # visible[s] = P(onset from an epoch-s infection lands inside the window)
    visible = np.array(
        [w[: max(0, n - s)].sum() for s in range(n)],
        dtype=float,
    )
    total = obs.sum()
    est = np.full(n, total / n if total > 0 else 0.0, dtype=float)
    for _ in range(max(1, int(iterations))):
        pred = expected_onsets(est, delay, n_epochs=n)
        ratio = np.divide(obs, pred, out=np.zeros_like(obs), where=pred > 0.0)
        # correlate ratio with the delay kernel: update[s] = sum_t w[t-s]*ratio[t]
        update = np.array(
            [
                float((w[: n - s] * ratio[s:]).sum()) if n - s > 0 else 0.0
                for s in range(n)
            ],
            dtype=float,
        )
        scale = np.divide(
            update,
            visible,
            out=np.zeros_like(update),
            where=visible > 0.0,
        )
        nxt = est * scale
        if np.max(np.abs(nxt - est)) < tol:
            est = nxt
            break
        est = nxt
    return est
