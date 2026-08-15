"""Coordinate-wise adaptive Metropolis, shared by the sentinel reference samplers.

Stan is the inferential engine; this exists so the sentinel suites can assert on
a real posterior on a box with no CmdStan toolchain (the ``[analysis]`` extra is
optional). It is deliberately the crudest sampler that works on these densities:

- **one coordinate per update.** A joint random-walk proposal is rejected almost
  always once the onset curve carries a few hundred cases, which is how a chain
  silently returns its initial value for every draw. The fleet density has tens
  of parameters, where that failure is certain rather than likely.
- **Robbins-Monro step adaptation during warmup only,** so the kept draws come
  from a fixed transition kernel.

Chains are short and the proposal is crude: treat the intervals as indicative.
The suites assert ordering, coverage, and the direction of a shift, never a
calibrated interval width.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence

import numpy as np

# Acceptance target for a one-dimensional random-walk update. The 0.44 optimum
# is for a Gaussian target; these posteriors are skewed enough that a slightly
# hotter chain mixes better across the log-rate scales.
TARGET_ACCEPT = 0.35


def _initial_step(scale: Sequence[float] | float, theta: np.ndarray) -> np.ndarray:
    step = (
        np.full(theta.size, float(scale))
        if np.isscalar(scale)
        else np.asarray(list(scale), dtype=float)
    )
    if step.shape != theta.shape:
        raise ValueError(f"scale has shape {step.shape}, expected {theta.shape}")
    return step


def _coordinate_sweep(
    log_density: Callable[[np.ndarray], float],
    theta: np.ndarray,
    lp: float,
    step: np.ndarray,
    rng: np.random.Generator,
    *,
    gain: float | None,
) -> tuple[np.ndarray, float]:
    """One update per coordinate; adapts ``step`` in place when ``gain`` is given.

    ``gain`` is the Robbins-Monro rate, and ``None`` means the kernel is frozen —
    which is what makes the kept draws come from one transition kernel.
    """
    for j in range(theta.size):
        proposal = theta.copy()
        proposal[j] += rng.normal(0.0, step[j])
        lp_new = log_density(proposal)
        accept = lp_new > lp or math.log(rng.uniform()) < lp_new - lp
        if accept:
            theta, lp = proposal, lp_new
        if gain is not None:
            # Shrink the step when rejecting, grow it when accepting, with a
            # decaying gain so warmup settles instead of oscillating.
            step[j] *= math.exp(gain * ((1.0 if accept else 0.0) - TARGET_ACCEPT))
    return theta, lp


def adaptive_metropolis(
    log_density: Callable[[np.ndarray], float],
    init: Sequence[float],
    *,
    draws: int,
    warmup: int,
    thin: int = 1,
    scale: Sequence[float] | float = 0.4,
    seed: int = 1701,
) -> np.ndarray:
    """``(draws, n_params)`` samples from ``log_density``.

    ``init`` must have finite log density: an initial point in a rejected region
    would leave the chain pinned there, and silently returning that constant is
    the failure mode this whole module exists to avoid.
    """
    theta = np.asarray(list(init), dtype=float)
    if theta.ndim != 1 or theta.size == 0:
        raise ValueError("init must be a non-empty parameter vector")
    step = _initial_step(scale, theta)

    lp = log_density(theta)
    if not math.isfinite(lp):
        raise ValueError("initial parameter vector has non-finite log density")

    rng = np.random.default_rng(seed)
    kept: list[np.ndarray] = []
    n_iter = int(warmup) + int(draws) * int(thin)
    for i in range(n_iter):
        theta, lp = _coordinate_sweep(
            log_density,
            theta,
            lp,
            step,
            rng,
            gain=1.0 / math.sqrt(i + 2.0) if i < warmup else None,
        )
        if i >= warmup and (i - warmup) % thin == 0:
            kept.append(theta.copy())
    return np.asarray(kept)
