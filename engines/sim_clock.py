"""
engines.sim_clock
~~~~~~~~~~~~~~~~~

One conversion between the two units this model is written in.

Pathogen natural history is parameterised in **days**, because that is how the
literature reports it: `norwalk_gi` has a 1.2-day incubation median and a
`recovery_day` of 3 symptomatic days from onset. The total course is incubation
plus `recovery_day`. The simulation advances in **epochs**, and the voyage layer
defines an epoch as one hour (`epoch_duration_hours`, 24 epochs per voyage day).
Nothing may bridge those two units except a ``SimClock``: no other module should
multiply or divide by 24.

Two modes exist, and both are needed.

``HOURS``
    The physical reading. A day of natural history takes ``24 /
    epoch_duration_hours`` epochs, so a norovirus case clears after three
    voyage days rather than three epochs.

``LEGACY_EPOCH_DAY``
    One epoch is one day of natural history regardless of the voyage grid. This
    is what the model did before the clock existed, so it is the control arm for
    re-testing published results (see ``docs/history/epoch_time_unit_audit.md``), not a
    physical claim.

Day-valued inputs keep their ``*_day``/``*_days`` names; epoch counters keep
theirs; a value converted here is the only place the two meet.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

HOURS_PER_DAY = 24.0

#: Voyage-layer default: one epoch is one hour.
DEFAULT_EPOCH_DURATION_HOURS = 1.0

HOURS = "hours"
LEGACY_EPOCH_DAY = "legacy_epoch_day"
MODES = (HOURS, LEGACY_EPOCH_DAY)


def config_epochs_for_hours(
    config: Mapping[str, Any],
    canonical_key: str,
    retired_key: str,
    clock: "SimClock",
    default: Any = 0,
) -> int | None:
    """Read a wall-clock delay/interval and convert it once to epochs."""
    if canonical_key in config:
        raw = config[canonical_key]
    elif retired_key in config:
        warnings.warn(
            f"{retired_key} is deprecated; use {canonical_key}",
            DeprecationWarning,
            stacklevel=3,
        )
        raw = config[retired_key]
    else:
        raw = default
    if raw is None:
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"{canonical_key} must be finite")
    return clock.epochs_for_hours(value)


def config_epochs_for_days(
    config: Mapping[str, Any],
    canonical_key: str,
    retired_key: str,
    clock: "SimClock",
    default: Any = 0,
) -> int:
    """Read a natural-history duration and convert it once to epochs."""
    if canonical_key in config:
        raw = config[canonical_key]
    elif retired_key in config:
        warnings.warn(
            f"{retired_key} is deprecated; use {canonical_key}",
            DeprecationWarning,
            stacklevel=3,
        )
        raw = config[retired_key]
    else:
        raw = default
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"{canonical_key} must be finite")
    return max(0, int(math.ceil(clock.epochs_for_days(value))))


def _epoch_duration_hours(
    cfg: Mapping[str, Any],
    voyage: Mapping[str, Any],
) -> float:
    """The one epoch length a config declares, refusing to pick between two.

    A top-level ``epoch_duration_hours`` is accepted for configs with no
    itinerary, but if both are present and disagree the run has two clocks and
    there is no defensible way to choose, so it fails loudly.
    """
    voyage_hours = voyage.get("epoch_duration_hours")
    top_hours = cfg.get("epoch_duration_hours")
    if (
        voyage_hours is not None
        and top_hours is not None
        and float(voyage_hours) != float(top_hours)
    ):
        raise ValueError(
            "epoch_duration_hours disagrees between voyage "
            f"({voyage_hours}) and top-level config ({top_hours}); "
            "the itinerary and the natural history cannot run on two clocks",
        )
    hours = voyage_hours if voyage_hours is not None else top_hours
    if hours is None:
        return DEFAULT_EPOCH_DURATION_HOURS
    return float(hours)


def _clock_mode(
    cfg: Mapping[str, Any],
    voyage: Mapping[str, Any],
    default_mode: str,
) -> str:
    """The one clock mode a config declares, refusing to pick between two.

    Either layer may name it, for the same reason either may name the epoch
    length: some configs carry no itinerary. Two different names is two clocks.
    """
    voyage_mode = voyage.get("natural_history_clock")
    top_mode = cfg.get("natural_history_clock")
    if voyage_mode and top_mode and str(voyage_mode) != str(top_mode):
        raise ValueError(
            "natural_history_clock disagrees between voyage "
            f"({voyage_mode!r}) and top-level config ({top_mode!r}); "
            "a run has one natural-history clock",
        )
    return str(voyage_mode or top_mode or default_mode)


@dataclass(frozen=True)
class SimClock:
    """Converts epoch counts to the day-valued scale pathogen profiles use."""

    epoch_duration_hours: float = DEFAULT_EPOCH_DURATION_HOURS
    mode: str = LEGACY_EPOCH_DAY

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"unknown natural-history clock mode: {self.mode!r}")
        if self.epoch_duration_hours <= 0:
            raise ValueError(
                f"epoch_duration_hours must be positive, got {self.epoch_duration_hours}",
            )

    # ── epochs → wall clock ───────────────────────────────────────────────

    @property
    def hours_per_epoch(self) -> float:
        """Wall-clock hours one epoch spans.

        Under the legacy clock an epoch *is* a day of natural history, so a
        physical delay must be read on that same day-long grid — otherwise the
        control arm gets a 72-epoch (72-day) microbiology turnaround while its
        biology still advances a day per epoch, which is not the pre-clock
        behaviour it exists to reproduce.
        """
        if self.mode == LEGACY_EPOCH_DAY:
            return HOURS_PER_DAY
        return self.epoch_duration_hours

    def hours_elapsed(self, epochs: float) -> float:
        """Wall-clock hours spanned by ``epochs`` epochs."""
        return float(epochs) * self.hours_per_epoch

    @property
    def day_fraction_per_epoch(self) -> float:
        """Fraction of a natural-history day represented by one epoch."""
        return self.hours_per_epoch / HOURS_PER_DAY

    def amount_per_epoch(self, amount_per_day: float) -> float:
        """Convert a per-day amount to the amount for one epoch."""
        if self.mode == LEGACY_EPOCH_DAY:
            return float(amount_per_day)
        return float(amount_per_day) * self.day_fraction_per_epoch

    def probability_per_epoch(self, probability_per_day: float) -> float:
        """Convert an independent per-day probability to one epoch."""
        probability = float(probability_per_day)
        if probability < 0.0:
            raise ValueError("probability_per_day must be non-negative")
        probability = min(1.0, probability)
        if self.mode == LEGACY_EPOCH_DAY:
            return probability
        return 1.0 - (1.0 - probability) ** self.day_fraction_per_epoch

    def decay_per_epoch(self, decay_per_day: float) -> float:
        """Convert a fractional per-day loss to one epoch."""
        decay = float(decay_per_day)
        if decay < 0.0:
            raise ValueError("decay_per_day must be non-negative")
        decay = min(1.0, decay)
        if self.mode == LEGACY_EPOCH_DAY:
            return decay
        return 1.0 - (1.0 - decay) ** self.day_fraction_per_epoch

    def growth_factor_per_epoch(self, growth_factor_per_day: float) -> float:
        """Convert a multiplicative per-day growth factor to one epoch."""
        factor = float(growth_factor_per_day)
        if factor <= 0.0:
            raise ValueError("growth_factor_per_day must be positive")
        if self.mode == LEGACY_EPOCH_DAY:
            return factor
        return factor ** self.day_fraction_per_epoch

    def survival_from_half_life(self, half_life_hours: float) -> float:
        """Return one-epoch survival for an hourly half-life."""
        half_life = float(half_life_hours)
        if half_life <= 0.0:
            raise ValueError("half_life_hours must be positive")
        return 0.5 ** (self.hours_per_epoch / half_life)

    def hour_of_day(self, epoch: float, start_hour: int = 0) -> int:
        """Return the physical hour represented by an epoch."""
        if self.mode == LEGACY_EPOCH_DAY:
            return 12
        return int(self.hours_elapsed(epoch) + start_hour) % 24

    def days_elapsed(self, epochs: float) -> float:
        """Days of natural history that ``epochs`` epochs represent."""
        if self.mode == LEGACY_EPOCH_DAY:
            return float(epochs)
        return self.hours_elapsed(epochs) / HOURS_PER_DAY

    def day_index(self, epochs: float) -> int:
        """Whole days elapsed — the index into a per-day curve.

        Held stepwise rather than interpolated: a daily shedding curve is a
        daily observation, so every epoch inside one day reads the same entry.
        """
        return max(0, int(math.floor(self.days_elapsed(epochs))))

    # ── wall clock → epochs ───────────────────────────────────────────────

    @property
    def epochs_per_day(self) -> float:
        """Epochs in one day of natural history."""
        if self.mode == LEGACY_EPOCH_DAY:
            return 1.0
        return HOURS_PER_DAY / self.epoch_duration_hours

    def epochs_for_days(self, days: float) -> float:
        """Epochs a ``days``-long interval of natural history occupies."""
        return float(days) * self.epochs_per_day

    def epochs_for_hours(self, hours: float) -> int:
        """Whole epochs a wall-clock delay of ``hours`` occupies, rounded up.

        Turnaround is a delay before a result exists, so a partial epoch still
        costs one.
        """
        return max(0, int(math.ceil(float(hours) / self.hours_per_epoch)))

    # ── construction ──────────────────────────────────────────────────────

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any] | None,
        *,
        default_mode: str = HOURS,
    ) -> SimClock:
        """Read the clock from a simulation config.

        ``voyage.epoch_duration_hours`` is the single source of the epoch length,
        so the natural-history clock cannot disagree with the itinerary.
        ``natural_history_clock`` selects the mode, and defaults to the physical
        reading: ``legacy_epoch_day`` has to be asked for, because it is a
        sensitivity control rather than a claim about biology.
        """
        cfg = config or {}
        voyage = cfg.get("voyage") or {}
        return cls(
            epoch_duration_hours=_epoch_duration_hours(cfg, voyage),
            mode=_clock_mode(cfg, voyage, default_mode),
        )

    @classmethod
    def for_run(
        cls,
        config: Mapping[str, Any] | None,
        voyage_config: Mapping[str, Any] | None = None,
        *,
        default_mode: str = HOURS,
    ) -> SimClock:
        """The single clock for one simulation run.

        ``voyage_config`` is the resolved itinerary (platform file plus config
        overrides), so the epoch length the natural history uses is by
        construction the one the itinerary was written on. Every consumer — the
        engine, the multi-pathogen progression, the wearables, the instrument
        turnaround queue — is handed this instance rather than deriving its own.
        """
        cfg = config or {}
        voyage = dict(voyage_config or cfg.get("voyage") or {})
        return cls(
            epoch_duration_hours=_epoch_duration_hours(cfg, voyage),
            mode=_clock_mode(cfg, voyage, default_mode),
        )


def crossed_day_boundary(
    clock: SimClock,
    epochs_infected: float,
    offset_days: float = 0.0,
) -> bool:
    """Whether this epoch opens a new day of natural history since ``offset_days``.

    Per-day hazards (the illness draw) are evaluated on this, so how finely time
    is cut does not change how many chances a host gets to present. Under the
    legacy clock every epoch is a new day, so it is always true once the offset
    is reached.

    ``offset_days`` is the threshold the hazard starts at — a host's drawn
    incubation period, say. Counting the day grid from it rather than from
    infection is what keeps onset off the whole-day lattice: a 1.2-day
    incubation presents in the epoch that crosses 1.2 days, not at the next
    midnight, so realized onset carries the sub-day resolution the incubation
    distribution was drawn at.
    """
    elapsed = clock.days_elapsed(epochs_infected) - offset_days
    if elapsed < 0:
        return False
    previous = clock.days_elapsed(epochs_infected - 1) - offset_days
    if previous < 0:
        return True
    return math.floor(elapsed) != math.floor(previous)


#: Pre-clock behaviour: one epoch advances natural history by one day.
LEGACY_CLOCK = SimClock(
    epoch_duration_hours=DEFAULT_EPOCH_DURATION_HOURS, mode=LEGACY_EPOCH_DAY,
)
