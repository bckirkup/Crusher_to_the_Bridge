"""
crusher_labs.instrument_turnaround
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configurable turnaround-time (TAT) queue for observation instruments.
Results are submitted when sampled and released to the Medical Officer
view (and stoplights) when ``available_epoch`` is reached.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any

from engines.sim_clock import LEGACY_CLOCK, SimClock
from simulation_utils.paths import resolve_repo_path, validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass(frozen=True)
class TurnaroundSpec:
    """Resolved delay in whole simulation epochs."""

    delay_epochs: int = 0

    @classmethod
    def from_config_block(
        cls,
        block: dict[str, Any] | None,
        *,
        clock: SimClock,
    ) -> TurnaroundSpec:
        """Resolve one instrument block.

        ``delay_hours`` and ``full_run_hours`` are physical and pass through the
        run's clock; ``delay_epochs`` and ``epoch_fraction`` are grid-native and
        are taken as written, which is what makes an explicit zero "this epoch".
        """
        if not block:
            return cls(0)
        if "delay_epochs" in block:
            return cls(max(0, int(block["delay_epochs"])))
        if "delay_hours" in block:
            return cls(clock.epochs_for_hours(float(block["delay_hours"])))
        return cls._from_run_length(block, clock=clock)

    @classmethod
    def from_profile_turnaround(
        cls,
        turnaround: dict[str, Any] | None,
        *,
        clock: SimClock,
    ) -> TurnaroundSpec:
        """Resolve a deployment profile's own turnaround block.

        A physical ``full_run_hours`` outranks ``epoch_fraction``: the fraction
        is grid-native, and every shipped one was written against the
        day-per-epoch grid, so honouring it first delivered a 48-hour MinION run
        inside the ordering epoch at any clock.
        """
        return cls._from_run_length(turnaround, clock=clock)

    @classmethod
    def _from_run_length(
        cls,
        block: dict[str, Any] | None,
        *,
        clock: SimClock,
    ) -> TurnaroundSpec:
        if not block:
            return cls(0)
        if "full_run_hours" in block:
            return cls(clock.epochs_for_hours(float(block["full_run_hours"])))
        if "epoch_fraction" in block:
            frac = float(block["epoch_fraction"])
            if frac < 1.0:
                return cls(0)
            return cls(max(0, int(math.ceil(frac))))
        return cls(0)


@dataclass
class _PendingAssay:
    instrument: str
    key: str
    payload: dict[str, Any]
    ordered_epoch: int
    available_epoch: int


class InstrumentTurnaroundRegistry:
    """Loads per-instrument TAT rules from JSON config."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        long_read_profile_turnaround: dict[str, Any] | None = None,
        clock: SimClock | None = None,
    ) -> None:
        self.clock = clock or self._clock_from_config(config)
        self._instruments = config.get("instruments", {})
        self._long_read_profile_turnaround = long_read_profile_turnaround

    @staticmethod
    def _clock_from_config(config: dict[str, Any]) -> SimClock:
        """Fallback clock for a registry built without the run's own.

        ``hours_per_epoch`` in the TAT config is retained only for that case: the
        run's ``voyage.epoch_duration_hours`` is authoritative whenever a clock is
        passed, so the two cannot disagree in a simulation.
        """
        hours = config.get("hours_per_epoch")
        if hours is None:
            return LEGACY_CLOCK
        return SimClock(epoch_duration_hours=float(hours), mode="hours")

    @classmethod
    def load(
        cls,
        path: str,
        *,
        repo_root: str | None = None,
        long_read_profile_turnaround: dict[str, Any] | None = None,
        clock: SimClock | None = None,
    ) -> InstrumentTurnaroundRegistry:
        root = repo_root or REPO_ROOT
        path = resolve_repo_path(root, path)
        with validated_open(path, "r", allowed_roots=(root,), encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(
            data,
            long_read_profile_turnaround=long_read_profile_turnaround,
            clock=clock,
        )

    def delay_epochs_for(self, instrument: str) -> int:
        block = self._instruments.get(instrument, {})
        if block.get("use_profile"):
            return TurnaroundSpec.from_profile_turnaround(
                self._long_read_profile_turnaround,
                clock=self.clock,
            ).delay_epochs
        return TurnaroundSpec.from_config_block(
            block,
            clock=self.clock,
        ).delay_epochs


class InstrumentTurnaroundQueue:
    """FIFO pending assays keyed by instrument and collection key."""

    def __init__(self, registry: InstrumentTurnaroundRegistry) -> None:
        self.registry = registry
        self._pending: list[_PendingAssay] = []

    def submit(
        self,
        instrument: str,
        key: str,
        payload: dict[str, Any],
        ordered_epoch: int,
        delay_epochs: int | None = None,
    ) -> dict[str, Any]:
        """Queue one assay; returns stamped payload copy."""
        if delay_epochs is None:
            delay_epochs = self.registry.delay_epochs_for(instrument)
        available = ordered_epoch + max(0, delay_epochs)
        stamped = dict(payload)
        stamped["ordered_epoch"] = ordered_epoch
        stamped["available_epoch"] = available
        stamped["status"] = "pending" if ordered_epoch < available else "complete"
        self._pending.append(
            _PendingAssay(
                instrument=instrument,
                key=key,
                payload=stamped,
                ordered_epoch=ordered_epoch,
                available_epoch=available,
            ),
        )
        return stamped

    def submit_dict(
        self,
        instrument: str,
        results: dict[Any, dict[str, Any]],
        ordered_epoch: int,
        delay_epochs: int | None = None,
        *,
        key_fn: Any = None,
    ) -> dict[Any, dict[str, Any]]:
        """Submit all entries in a results dict; keys coerced to str for storage."""
        out: dict[Any, dict[str, Any]] = {}
        for raw_key, payload in results.items():
            key = key_fn(raw_key) if key_fn else str(raw_key)
            out[raw_key] = self.submit(
                instrument, key, payload, ordered_epoch, delay_epochs,
            )
        return out

    def release(self, epoch: int) -> dict[str, dict[str, dict[str, Any]]]:
        """Return visible results per instrument for *epoch*.

        Complete assays include full payload; pending assays show metadata only.
        Completed entries are removed from the queue.
        """
        visible: dict[str, dict[str, dict[str, Any]]] = {}
        still_pending: list[_PendingAssay] = []

        for item in self._pending:
            if item.ordered_epoch > epoch:
                still_pending.append(item)
                continue

            if epoch >= item.available_epoch:
                released = dict(item.payload)
                released["status"] = "complete"
                visible.setdefault(item.instrument, {})[item.key] = released
            else:
                pending_view = {
                    "status": "pending",
                    "ordered_epoch": item.ordered_epoch,
                    "available_epoch": item.available_epoch,
                    "instrument": item.instrument,
                }
                for meta_key in (
                    "request_id",
                    "specimen_source",
                    "collection_key",
                    "zone",
                    "agent_id",
                ):
                    if meta_key in item.payload:
                        pending_view[meta_key] = item.payload[meta_key]
                visible.setdefault(item.instrument, {})[item.key] = pending_view
                still_pending.append(item)

        self._pending = still_pending
        return visible

    def pending_summary(self, epoch: int) -> dict[str, int]:
        """Count in-flight assays by instrument at *epoch*."""
        counts: dict[str, int] = {}
        for item in self._pending:
            if item.ordered_epoch <= epoch < item.available_epoch:
                counts[item.instrument] = counts.get(item.instrument, 0) + 1
        return counts


# Instrument keys used in turnaround config and queue
INSTRUMENT_AIR = "continuous_air_sampler"
INSTRUMENT_SWAB = "targeted_surface_swab"
INSTRUMENT_WW = "wastewater_sequencing"
INSTRUMENT_RDT = "clinical_rdt"
INSTRUMENT_QPCR = "clinical_qpcr"
INSTRUMENT_MICROBIO = "clinical_microbiology"
INSTRUMENT_LONG_READ = "long_read_verification"


def merge_released_into_observation(
    released: dict[str, dict[str, dict[str, Any]]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Map queue instrument keys to observation_engine field shapes."""

    def _zone_dict(inst: str) -> dict[str, dict[str, Any]]:
        raw = released.get(inst, {})
        return dict(raw)

    def _agent_dict(inst: str) -> dict[int, dict[str, Any]]:
        raw = released.get(inst, {})
        out: dict[int, dict[str, Any]] = {}
        for k, v in raw.items():
            try:
                out[int(k)] = v
            except ValueError:
                out[k] = v  # type: ignore[assignment]
        return out

    air = _zone_dict(INSTRUMENT_AIR)
    swab = _zone_dict(INSTRUMENT_SWAB)
    ww = _zone_dict(INSTRUMENT_WW)
    rdt = _agent_dict(INSTRUMENT_RDT)
    qpcr = _agent_dict(INSTRUMENT_QPCR)
    microbio = _agent_dict(INSTRUMENT_MICROBIO)
    lr = _zone_dict(INSTRUMENT_LONG_READ)
    return air, swab, ww, rdt, qpcr, microbio, lr
