from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from engines.sim_clock import SimClock
from engines.transmission_core import (
    OUTBREAK_CLEANING_COVERAGE,
    ROUTINE_CLEANING_COVERAGE,
    ROUTINE_CLEANING_LOG10_REDUCTION,
    TransmissionCore,
)

ROOT = Path(__file__).resolve().parents[1]
PATHOGEN = "norwalk_gi"
ZONE = "Bridge"


def _core(
    *,
    coverage: float = ROUTINE_CLEANING_COVERAGE,
    log10_reduction: float = ROUTINE_CLEANING_LOG10_REDUCTION,
    events_per_day: float = 1.0,
    clock: SimClock | None = None,
    surface_decay_log10_per_day: float = 0.124939,
) -> TransmissionCore:
    return TransmissionCore(
        np.random.default_rng(11),
        pathogen_profiles={
            PATHOGEN: {
                "surface_decay_log10_per_day": surface_decay_log10_per_day,
            },
        },
        zone_types={ZONE: "Work"},
        clock=clock,
        cfg={
            "transmission": {
                "surface_cleaning": {
                    "enabled": True,
                    "routine": {
                        "coverage": coverage,
                        "log10_reduction": log10_reduction,
                        "events_per_day": events_per_day,
                    },
                    "outbreak_response": {
                        "coverage": OUTBREAK_CLEANING_COVERAGE,
                        "log10_reduction": 4.29,
                    },
                },
            },
        },
    )


def _mass(core: TransmissionCore) -> float:
    return core.surface_pools_by_pathogen[PATHOGEN][ZONE]


def _cleanable(core: TransmissionCore) -> float:
    return core.surface_pools_cleanable_by_pathogen[PATHOGEN][ZONE]


def _assert_invariant(core: TransmissionCore) -> None:
    total = _mass(core)
    cleanable = _cleanable(core)
    assert math.isfinite(total)
    assert math.isfinite(cleanable)
    assert total >= 0.0
    assert cleanable >= 0.0
    assert cleanable <= total + 1e-12


def test_compartment_invariant_across_surface_operations() -> None:
    core = _core()
    core.initialize_zones([ZONE])
    core._deposit_surface_mass(PATHOGEN, ZONE, 10.0)
    _assert_invariant(core)
    core._update_surface_pools({})
    _assert_invariant(core)
    core._consume_surface_mass(PATHOGEN, ZONE, 1.0, _mass(core))
    _assert_invariant(core)
    core._routine_cleaning_event(ZONE)
    _assert_invariant(core)
    core.disinfect_surfaces(4.29, OUTBREAK_CLEANING_COVERAGE)
    _assert_invariant(core)


def _steady_total(
    *,
    coverage: float = ROUTINE_CLEANING_COVERAGE,
    log10_reduction: float = ROUTINE_CLEANING_LOG10_REDUCTION,
    events_per_day: float = 1.0,
) -> tuple[float, float]:
    core = _core(
        coverage=coverage,
        log10_reduction=log10_reduction,
        events_per_day=events_per_day,
        clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
    )
    core.initialize_zones([ZONE])
    for _ in range(2400):
        core._deposit_surface_mass(PATHOGEN, ZONE, 1.0)
        core._update_surface_pools({})
    return _mass(core), _cleanable(core)


def test_routine_cleaning_retains_nonzero_missed_reservoir() -> None:
    total, cleanable = _steady_total()
    assert total > 0.0
    assert cleanable < total
    clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    survival = 1.0 - clock.decay_per_epoch(0.25)
    # Missed mass follows M_next = survival * (M + 1 - coverage), so
    # its fixed point is survival * (1 - coverage) / (1 - survival).
    missed_floor = (
        survival * (1.0 - ROUTINE_CLEANING_COVERAGE) / (1.0 - survival)
    )
    assert total >= missed_floor


@pytest.mark.parametrize(
    "parameter, values",
    [
        ("coverage", (0.0, ROUTINE_CLEANING_COVERAGE, 1.0)),
        ("log10_reduction", (0.0, ROUTINE_CLEANING_LOG10_REDUCTION, 4.29)),
        ("events_per_day", (0.5, 1.0, 4.0)),
    ],
)
def test_routine_sweeps_are_monotonic(
    parameter: str,
    values: tuple[float, float, float],
) -> None:
    totals = [
        _steady_total(**{parameter: value})[0]
        for value in values
    ]
    assert totals[0] >= totals[1] >= totals[2]


def test_routine_cleaning_is_clock_invariant() -> None:
    hourly = _core(clock=SimClock(epoch_duration_hours=1.0, mode="hours"))
    legacy = _core(clock=SimClock(mode="legacy_epoch_day"))
    for core in (hourly, legacy):
        core.initialize_zones([ZONE])
        core._deposit_surface_mass(PATHOGEN, ZONE, 10.0)
    for _ in range(24):
        hourly._update_surface_pools({})
    legacy._update_surface_pools({})
    assert hourly._routine_cleaning_event_counts[ZONE] == 1
    assert legacy._routine_cleaning_event_counts[ZONE] == 1
    assert _mass(hourly) == pytest.approx(_mass(legacy))


def test_outbreak_disinfection_beats_routine_and_preserves_missed_fraction() -> None:
    routine = _core()
    outbreak = _core()
    for core in (routine, outbreak):
        core.initialize_zones([ZONE])
        core._deposit_surface_mass(PATHOGEN, ZONE, 100.0)
    routine._routine_cleaning_event(ZONE)
    outbreak.disinfect_surfaces(4.29, OUTBREAK_CLEANING_COVERAGE)
    assert _mass(outbreak) < _mass(routine)
    nested_fraction = (
        OUTBREAK_CLEANING_COVERAGE - ROUTINE_CLEANING_COVERAGE
    ) / (1.0 - ROUTINE_CLEANING_COVERAGE)
    missed_before = 100.0 * (1.0 - ROUTINE_CLEANING_COVERAGE)
    assert _mass(outbreak) >= missed_before * (1.0 - nested_fraction)


def test_cleaning_change_detectors() -> None:
    # Change detector: the routine event retains this exact cleanable share.
    core = _core()
    core.initialize_zones([ZONE])
    core._deposit_surface_mass(PATHOGEN, ZONE, 100.0)
    core._routine_cleaning_event(ZONE)
    assert _cleanable(core) == pytest.approx(
        100.0 * ROUTINE_CLEANING_COVERAGE
        * 10.0 ** -ROUTINE_CLEANING_LOG10_REDUCTION,
    )

    core = _core()
    core.initialize_zones([ZONE])
    core._deposit_surface_mass(PATHOGEN, ZONE, 100.0)
    core.disinfect_surfaces(4.29, OUTBREAK_CLEANING_COVERAGE)
    # Change detector: nested coverage retains this exact missed share.
    nested = (OUTBREAK_CLEANING_COVERAGE - ROUTINE_CLEANING_COVERAGE) / (
        1.0 - ROUTINE_CLEANING_COVERAGE
    )
    missed_multiplier = 1.0 - nested * (1.0 - 10.0 ** -4.29)
    assert _mass(core) == pytest.approx(
        100.0 * ROUTINE_CLEANING_COVERAGE * 10.0 ** -4.29
        + 100.0 * (1.0 - ROUTINE_CLEANING_COVERAGE) * missed_multiplier,
    )


def test_protocol_data_contract_uses_disinfection_modifier() -> None:
    data = json.loads(
        (ROOT / "data/config/protocols.json").read_text(encoding="utf-8"),
    )
    protocols = {item["protocol_id"]: item for item in data["protocols"]}
    for protocol_id in ("SOP-003", "SOP-010", "SOP-016"):
        modifiers = protocols[protocol_id]["modifiers"]
        assert not any(
            key.endswith("decontamination_factor") or
            key.endswith("decay_rate_override")
            for key in modifiers
        )
        assert modifiers["surface_disinfection_log10_reduction"] == pytest.approx(4.29)
