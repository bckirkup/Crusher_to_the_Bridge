"""How much a sequencing channel actually learns about the lineage mixture.

Truth is the census genotype frequency at an epoch; the observation is what a
channel reported by that epoch. Two numbers per epoch:

``js_distance``
    Jensen-Shannon distance (bits, square-rooted so it is a metric in [0, 1])
    between reported and true composition. Zero is a perfect read.

``information_gain_bits``
    ``D_KL(truth || uniform) - D_KL(truth || observed)``, i.e. how many bits
    closer to the truth the report puts you than a genotype-blind uniform guess
    over the known genotype universe. Negative means the channel is worse than
    admitting ignorance — a confidently wrong dominant call — which is a real
    outcome for a low-depth arm, so it is not clipped.

Uniform baseline, not a "no information" of zero: knowing the genotype universe
is itself free, and crediting the assay for it would inflate every arm equally.

The observed distribution enters Jeffreys-smoothed (``alpha = 0.5`` per
genotype in the union universe), because an unsmoothed zero on a genotype the
channel simply never sequenced makes the divergence diverge, and the reported
magnitude would then be an artefact of the floor rather than of the assay. The
smoothing also fixes the degenerate case: a channel that reported nothing
smooths to the uniform baseline and scores exactly ``0.0`` bits.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping

INFORMATION_COLUMNS = (
    "pathogen_id",
    "epoch",
    "voyage_hours",
    "truth_genotypes",
    "observed_genotypes",
    "js_distance",
    "information_gain_bits",
    "truth_entropy_bits",
    "observed_entropy_bits",
    "completeness",
)

OBSERVED_SMOOTHING_ALPHA = 0.5


@dataclass(frozen=True)
class InformationRow:
    """One pathogen's observed-versus-true lineage composition at one hour."""

    pathogen_id: str
    epoch: int
    voyage_hours: float
    truth_genotypes: int
    observed_genotypes: int
    js_distance: float
    information_gain_bits: float
    truth_entropy_bits: float
    observed_entropy_bits: float
    completeness: float

    def as_dict(self) -> dict[str, Any]:
        """Row form for CSV / JSON writers."""
        return asdict(self)


def normalize(weights: Mapping[str, float]) -> dict[str, float]:
    """A frequency distribution over the positive entries of ``weights``."""
    positive = {str(k): float(v) for k, v in weights.items() if float(v) > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        return {}
    return {k: v / total for k, v in positive.items()}


def _aligned(
    truth: Mapping[str, float],
    observed: Mapping[str, float],
) -> tuple[list[float], list[float]]:
    keys = sorted(set(truth) | set(observed))
    return (
        [float(truth.get(k, 0.0)) for k in keys],
        [float(observed.get(k, 0.0)) for k in keys],
    )


def entropy_bits(distribution: Mapping[str, float]) -> float:
    """Shannon entropy of a frequency distribution, in bits."""
    freqs = normalize(distribution)
    return -sum(p * math.log2(p) for p in freqs.values() if p > 0.0)


def js_distance(
    truth: Mapping[str, float],
    observed: Mapping[str, float],
) -> float:
    """Jensen-Shannon distance in [0, 1]; ``1.0`` against an empty report."""
    p_freq = normalize(truth)
    q_freq = normalize(observed)
    if not p_freq or not q_freq:
        return 1.0 if p_freq or q_freq else 0.0
    p_vec, q_vec = _aligned(p_freq, q_freq)
    divergence = 0.0
    for p, q in zip(p_vec, q_vec):
        m = 0.5 * (p + q)
        if p > 0.0:
            divergence += 0.5 * p * math.log2(p / m)
        if q > 0.0:
            divergence += 0.5 * q * math.log2(q / m)
    return math.sqrt(max(0.0, min(1.0, divergence)))


def _kl_bits(truth: list[float], other: list[float]) -> float:
    return sum(
        p * math.log2(p / q) for p, q in zip(truth, other) if p > 0.0 and q > 0.0
    )


def smoothed(
    weights: Mapping[str, float],
    keys: list[str],
    alpha: float = OBSERVED_SMOOTHING_ALPHA,
) -> list[float]:
    """Jeffreys-smoothed frequencies of ``weights`` over ``keys``.

    Uniform when ``weights`` is empty, which is the honest reading of a channel
    that reported nothing at all.
    """
    raw = [max(0.0, float(weights.get(k, 0.0))) for k in keys]
    total = sum(raw) + alpha * len(keys)
    return [(value + alpha) / total for value in raw]


def information_gain_bits(
    truth: Mapping[str, float],
    observed: Mapping[str, float],
) -> float:
    """Bits the report buys over a uniform guess on the same genotype universe.

    ``0.0`` when there is no truth to learn about, and ``0.0`` when the channel
    reported nothing (it has told you exactly what the uniform prior did).
    """
    p_freq = normalize(truth)
    if not p_freq:
        return 0.0
    q_freq = normalize(observed)
    keys = sorted(set(p_freq) | set(q_freq))
    p_vec = [p_freq.get(k, 0.0) for k in keys]
    uniform = [1.0 / len(keys)] * len(keys)
    return _kl_bits(p_vec, uniform) - _kl_bits(p_vec, smoothed(q_freq, keys))


def completeness(
    truth: Mapping[str, float],
    observed: Mapping[str, float],
) -> float:
    """Share of true genotype mass that the report named at all."""
    p_freq = normalize(truth)
    if not p_freq:
        return 0.0
    named = set(normalize(observed))
    return sum(p for genotype, p in p_freq.items() if genotype in named)


def information_row(
    *,
    pathogen_id: str,
    epoch: int,
    voyage_hours: float,
    truth: Mapping[str, float],
    observed: Mapping[str, float],
) -> InformationRow:
    """Assemble one comparison row from a truth and an observed composition."""
    return InformationRow(
        pathogen_id=pathogen_id,
        epoch=epoch,
        voyage_hours=voyage_hours,
        truth_genotypes=len(normalize(truth)),
        observed_genotypes=len(normalize(observed)),
        js_distance=js_distance(truth, observed),
        information_gain_bits=information_gain_bits(truth, observed),
        truth_entropy_bits=entropy_bits(truth),
        observed_entropy_bits=entropy_bits(observed),
        completeness=completeness(truth, observed),
    )
