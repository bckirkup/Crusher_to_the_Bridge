"""Liu 2013's two hand-rinse moments, read off the shipped hand process.

`TransmissionCore._replenish_hand`'s event mode is a decay-plus-reset
recurrence: the load decays at `hand_inactivation_rate_per_hour` and returns to
`get_pathogen_hand_target`'s ceiling whenever a defecation event falls in the
epoch. Liu et al. 2013 (PMC3837815) measures two stationary properties of the
same process in challenge volunteers, and neither is a scored anchor:

* **occupancy** - 18/71 (25.4%) of hand rinses from symptomatic, stool-positive
  hosts were above a combined-method detection limit of 2.15 log10 GEC/rinse;
* **conditional mean** - 3.86 log10 GEC/hand among those positives, with
  per-subject means spanning 3.30-4.45.

This module reports both for a declared (rate, events/day, sigma) triple so the
hand route can be checked against the measurement that sources it. It adopts
nothing and imports nothing from the engine but `HOURS_PER_DAY`: it reproduces
the recurrence's arithmetic so a candidate declaration can be read before any
code changes.

Two omissions make the reported occupancy an *upper* bound on the engine's:
hand hygiene events (`hand_hygiene_rate_per_hour`, shipped 0.0/h) and the
depletion the surface, food and mouth routes apply are not modelled here.

Reference: `docs/proposals/hand_event_release_spec.md` section 5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from engines.sim_clock import HOURS_PER_DAY

# Liu et al. 2013, AEM, doi:10.1128/aem.02576-13, Results. Grade A for the
# quantity (norovirus GEC per hand, human subjects), Grade C for the setting
# (GI.1 challenge volunteers, not a cruise population).
LIU_OCCUPANCY = 18.0 / 71.0
LIU_CONDITIONAL_MEAN_LOG10 = 3.86
LIU_DETECTION_LIMIT_LOG10 = 2.15
LIU_SUBJECT_MEAN_RANGE_LOG10 = (3.30, 4.45)

DEFAULT_EPOCH_HOURS = 1.0
DEFAULT_HOURS = 200_000


@dataclass(frozen=True)
class HandProcessMoments:
    """Stationary moments of one declared hand process."""

    occupancy: float
    conditional_mean_log10: float
    mean_load_log10: float

    def occupancy_ratio(self) -> float:
        """Occupancy relative to Liu's 25.4%; 1.0 reproduces it."""
        return self.occupancy / LIU_OCCUPANCY

    def conditional_mean_offset_log10(self) -> float:
        """Signed log10 offset from Liu's positive mean; negative is low."""
        return self.conditional_mean_log10 - LIU_CONDITIONAL_MEAN_LOG10


def hand_process_moments(
    inactivation_rate_per_hour: float,
    events_per_day: float,
    ceiling_log10: float,
    sigma_log10: float = 0.0,
    additive: bool = False,
    wash_probability: float = 0.0,
    wash_log10_reduction: float = 1.06,
    epoch_hours: float = DEFAULT_EPOCH_HOURS,
    hours: int = DEFAULT_HOURS,
    seed: int = 11,
) -> HandProcessMoments:
    """Occupancy, positive-sample mean and time-averaged load of one process.

    `additive=False` is the shipped `max(decayed, target)` reset;
    `additive=True` is the arrival-summing form HAND-EVENT-01 section 3.1
    proposes. `sigma_log10` is the within-host amplitude dispersion of section
    3.3, absent from the engine today. `wash_probability` fires a removal
    coupled to the same event (section 3.4), which is the only form in which
    Liu's *lower* post-bathroom loads can arise from a defecation trigger.
    """
    rng = np.random.default_rng(seed)
    survival = math.exp(-inactivation_rate_per_hour * epoch_hours)
    event_probability = 1.0 - math.exp(
        -events_per_day * epoch_hours / HOURS_PER_DAY
    )
    ceiling = 10.0**ceiling_log10
    threshold = 10.0**LIU_DETECTION_LIMIT_LOG10
    epochs = max(1, int(hours / epoch_hours))
    load = 0.0
    total = 0.0
    positive_logs: list[float] = []
    for _ in range(epochs):
        load *= survival
        if rng.random() < event_probability:
            amplitude = ceiling
            if sigma_log10 > 0.0:
                amplitude *= 10.0 ** rng.normal(0.0, sigma_log10)
            load = load + amplitude if additive else max(load, amplitude)
            if rng.random() < wash_probability:
                load *= 10.0**-wash_log10_reduction
        total += load
        if load > threshold:
            positive_logs.append(math.log10(load))
    return HandProcessMoments(
        occupancy=len(positive_logs) / epochs,
        conditional_mean_log10=(float(np.mean(positive_logs)) if positive_logs else float("nan")),
        mean_load_log10=(math.log10(total / epochs) if total > 0.0 else float("nan")),
    )
