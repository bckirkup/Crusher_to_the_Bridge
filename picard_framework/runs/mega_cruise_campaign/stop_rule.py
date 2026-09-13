"""In-loop stopping rule for a campaign shard.

A shard accumulates one ``summary.json`` per completed run. This module scores
a binary event on each summary's ``derived`` block and keeps a Beta-Binomial
posterior on the event frequency, exactly as
``telemetry_buffer/observation_model/staged_posting_readout.py`` scores a
posting cell: Jeffreys' Beta(1/2, 1/2) prior, posterior mass below / inside /
above a stated band, and a stop once ``STOP_MASS`` (0.95) of the mass has
settled on one side. The prior, the stop mass and the decision function are
imported from that module rather than restated, so the two rules cannot drift.

The band is the *expected* frequency, declared on the command line before
the first run. A stop therefore means: the runs completed so far say the
event frequency lies outside what the campaign was designed around, with
95% posterior mass. That is an "unexpected trend", and the discipline in
``docs/proposals/defect_resolution_plan.md`` applies -- the response is to
report the finding, not to move the band and continue. Nothing in the rule
is tuned during the run; every threshold is in the spec string.

Spec grammar (all four fields required, no defaults to tune)::

    <event>:<band_low>:<band_high>:<min_n>

    event      derived metric name, optionally with a threshold:
               ``outbreak_occurred``      truthy value is the event
               ``attack_rate>=0.3``       value >= 0.3 is the event
               ``peak_epoch<40``          value < 40 is the event
    band_low   expected frequency band, lower edge in [0, 1]
    band_high  upper edge, > band_low
    min_n      scored runs required before the rule may fire (>= 1)

Runs whose ``derived`` block lacks the metric (a failed run, a lightweight
test runner) are not scored and do not count toward ``min_n``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from telemetry_buffer.observation_model.staged_posting_readout import (
    CONTINUE,
    JEFFREYS,
    STOP_ABOVE,
    STOP_BELOW,
    STOP_MASS,
    band_mass,
    decision,
)

__all__ = [
    "CONTINUE",
    "STOP_ABOVE",
    "STOP_BELOW",
    "STOP_MASS",
    "JEFFREYS",
    "StopRule",
    "StopRuleSpecError",
    "parse_stop_rule",
]

_COMPARATORS: dict[str, Callable[[float, float], bool]] = {
    ">=": lambda v, t: v >= t,
    "<=": lambda v, t: v <= t,
    ">": lambda v, t: v > t,
    "<": lambda v, t: v < t,
    "==": lambda v, t: v == t,
}
_EVENT_RE = re.compile(
    r"^(?P<metric>[A-Za-z_]\w*)(?:(?P<op>>=|<=|==|>|<)(?P<threshold>[^:]+))?$",
    re.ASCII,
)


class StopRuleSpecError(ValueError):
    """The ``--stop-rule`` spec is malformed or its thresholds are not admissible."""


@dataclass(frozen=True)
class EventSpec:
    metric: str
    op: str | None = None
    threshold: float | None = None

    def occurs(self, derived: Mapping[str, Any]) -> bool | None:
        """True/False if the metric is present and scorable, else None."""
        if self.metric not in derived:
            return None
        value = derived[self.metric]
        if value is None:
            return None
        if self.op is None:
            return bool(value)
        try:
            return _COMPARATORS[self.op](float(value), float(self.threshold or 0.0))
        except (TypeError, ValueError):
            return None

    def render(self) -> str:
        if self.op is None:
            return self.metric
        return f"{self.metric}{self.op}{self.threshold:g}"


@dataclass
class StopRule:
    """Beta-Binomial stopping rule on one binary event over completed runs."""

    event: EventSpec
    band: tuple[float, float]
    min_n: int
    stop_mass: float = STOP_MASS
    prior: tuple[float, float] = JEFFREYS
    n: int = 0
    k: int = 0
    unscored: int = 0
    scored_run_ids: list[str] = field(default_factory=list)

    def observe(self, run_id: str, derived: Mapping[str, Any]) -> bool | None:
        """Score one completed run; returns the event value or None if unscorable."""
        occurred = self.event.occurs(derived)
        if occurred is None:
            self.unscored += 1
            return None
        self.n += 1
        self.k += int(occurred)
        self.scored_run_ids.append(run_id)
        return occurred

    def observe_entries(self, entries: Mapping[str, Mapping[str, Any]]) -> None:
        """Seed the rule from a shard manifest (``run_id -> {derived: ...}``)."""
        for run_id, entry in entries.items():
            derived = entry.get("derived") if isinstance(entry, Mapping) else None
            self.observe(run_id, derived if isinstance(derived, Mapping) else {})

    def mass(self) -> dict[str, float]:
        return band_mass(self.k, self.n, self.band, self.prior)

    def decision(self) -> str:
        if self.n < self.min_n:
            return CONTINUE
        return decision(self.mass(), self.stop_mass)

    @property
    def triggered(self) -> bool:
        return self.decision() != CONTINUE

    def render_spec(self) -> str:
        return f"{self.event.render()}:{self.band[0]:g}:{self.band[1]:g}:{self.min_n}"

    def verdict(self) -> dict[str, Any]:
        """A self-describing record of the rule and its state, for the shard artefacts."""
        return {
            "mode": "campaign_stop_rule",
            "spec": self.render_spec(),
            "event": self.event.render(),
            "band": list(self.band),
            "min_n": self.min_n,
            "prior": {"family": "beta", "a": self.prior[0], "b": self.prior[1]},
            "stop_mass": self.stop_mass,
            "scored_runs": self.n,
            "events": self.k,
            "unscored_runs": self.unscored,
            "posterior": self.mass() if self.n else None,
            "decision": self.decision(),
            "scored_run_ids": list(self.scored_run_ids),
        }


def _parse_event(text: str) -> EventSpec:
    match = _EVENT_RE.match(text.strip())
    if match is None:
        raise StopRuleSpecError(
            f"stop-rule event {text!r} must be <metric> or <metric><op><threshold>",
        )
    op = match.group("op")
    if op is None:
        return EventSpec(metric=match.group("metric"))
    try:
        threshold = float(match.group("threshold"))
    except ValueError as exc:
        raise StopRuleSpecError(
            f"stop-rule threshold {match.group('threshold')!r} is not a number",
        ) from exc
    return EventSpec(metric=match.group("metric"), op=op, threshold=threshold)


def parse_stop_rule(spec: str) -> StopRule:
    """Parse ``<event>:<band_low>:<band_high>:<min_n>`` into a ``StopRule``."""
    parts = spec.split(":")
    if len(parts) != 4:
        raise StopRuleSpecError(
            f"--stop-rule {spec!r} must have four ':'-separated fields: "
            "<event>:<band_low>:<band_high>:<min_n>",
        )
    event = _parse_event(parts[0])
    try:
        low, high = float(parts[1]), float(parts[2])
        min_n = int(parts[3])
    except ValueError as exc:
        raise StopRuleSpecError(f"--stop-rule {spec!r}: band edges must be floats and min_n an int") from exc
    if not 0.0 <= low < high <= 1.0:
        raise StopRuleSpecError(
            f"--stop-rule {spec!r}: band must satisfy 0 <= low < high <= 1, got [{low}, {high}]",
        )
    if min_n < 1:
        raise StopRuleSpecError(f"--stop-rule {spec!r}: min_n must be >= 1")
    return StopRule(event=event, band=(low, high), min_n=min_n)
