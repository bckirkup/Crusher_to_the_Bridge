"""Outbreak-response surface disinfection is metered on the clock, not the epoch.

A disinfection pass is a discrete housekeeping event. The pre-repair code ran
one full outbreak pass per epoch while an SOP modifier was in force, so at
1-hour epochs cabins lost ~100 log10 of surface mass per day — every fomite
route in every voyage that reached ALERT. These tests pin the metered
contract: one activation-edge pass plus ``events_per_day`` metered passes,
invariant under the epoch length, per the clock-unit-safety skill.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from engines.sim_clock import SimClock
from engines.transmission_core import (
    OUTBREAK_CLEANING_COVERAGE,
    EmesisPatch,
    TransmissionCore,
)

PATHOGEN = "norwalk_gi"
CABIN = "Cabin_1"
PUBLIC = "Lounge_1"
REDUCTION = 4.29


def _core(
    *,
    clock: SimClock,
    cabin_events: float = 1.0,
    public_events: float = 24.0,
    cabin_coverage: float | None = None,
) -> TransmissionCore:
    cabin_override: dict[str, float] = {"events_per_day": cabin_events}
    if cabin_coverage is not None:
        cabin_override["coverage"] = cabin_coverage
    return TransmissionCore(
        rng=np.random.default_rng(11),
        pathogen_profiles={PATHOGEN: {}},
        zone_types={CABIN: "Room", PUBLIC: "Work"},
        clock=clock,
        cfg={
            "transmission": {
                "surface_cleaning": {
                    "enabled": True,
                    "routine": {
                        "coverage": 0.37,
                        "log10_reduction": 1.29,
                        "events_per_day": 1.0,
                    },
                    "outbreak_response": {
                        "coverage": OUTBREAK_CLEANING_COVERAGE,
                        "log10_reduction": REDUCTION,
                        "events_per_day": public_events,
                        "by_zone_class": {
                            "cabin": cabin_override,
                        },
                    },
                },
            },
        },
    )


def _seed_masses(core: TransmissionCore, mass: float = 1.0e7) -> None:
    core.initialize_zones([CABIN, PUBLIC])
    core._deposit_surface_mass(PATHOGEN, CABIN, mass)
    core._deposit_surface_mass(PATHOGEN, PUBLIC, mass)
    core.emesis_patch_pools_by_pathogen.setdefault(
        PATHOGEN, {},
    ).setdefault(CABIN, []).append(
        EmesisPatch(
            mass=mass,
            high_touch_area_m2=0.1,
            occupant_share=0.5,
            epoch=0,
        ),
    )


def _run_sop_hours(core: TransmissionCore, hours: float) -> None:
    epochs = int(round(hours / core.clock.hours_per_epoch))
    for _ in range(epochs):
        core.set_outbreak_disinfection(REDUCTION)


def _patch(core: TransmissionCore) -> EmesisPatch:
    return core.emesis_patch_pools_by_pathogen[PATHOGEN][CABIN][0]


class TestClockInvariance:
    """The headline regression: 24 h of SOP must do the same work at any
    epoch length. Accumulated-hourly must equal the one-day result, not
    merely run."""

    @pytest.mark.parametrize("hours_per_epoch", (1.0, 2.0, 4.0))
    def test_24h_of_sop_is_epoch_length_invariant(
        self,
        hours_per_epoch: float,
    ) -> None:
        core = _core(clock=SimClock(
            epoch_duration_hours=hours_per_epoch,
            mode="hours",
        ))
        _seed_masses(core)
        _run_sop_hours(core, 24.0)
        # Each clock burns the activation-edge pass plus exactly one sourced
        # daily cabin pass and 24 public passes over 24 simulated hours.
        assert core._outbreak_cleaning_event_counts[CABIN] == 1
        assert core._outbreak_cleaning_event_counts[PUBLIC] == 24

    def test_surviving_mass_agrees_across_epoch_lengths(self) -> None:
        masses: dict[float, tuple[float, float]] = {}
        for hours_per_epoch in (1.0, 2.0, 4.0):
            core = _core(clock=SimClock(
                epoch_duration_hours=hours_per_epoch,
                mode="hours",
            ))
            _seed_masses(core)
            _run_sop_hours(core, 24.0)
            masses[hours_per_epoch] = (
                core.surface_pools_by_pathogen[PATHOGEN][CABIN],
                _patch(core).mass,
            )
        ref_pool, ref_patch = masses[1.0]
        for hpe, (pool, patch) in masses.items():
            assert pool == pytest.approx(ref_pool, rel=1e-9), (
                f"cabin pool differs at {hpe}h epochs"
            )
            assert patch == pytest.approx(ref_patch, rel=1e-9), (
                f"emesis patch differs at {hpe}h epochs"
            )


class TestPassCounting:
    def test_24_hourly_epochs_fire_edge_plus_one_cabin_pass(self) -> None:
        core = _core(clock=SimClock(epoch_duration_hours=1.0, mode="hours"))
        _seed_masses(core)
        _run_sop_hours(core, 24.0)
        # The cabin meter is the sourced daily pass. 24 (a pass per epoch)
        # would reintroduce the defect this change removes.
        assert core._outbreak_cleaning_event_counts[CABIN] == 1
        # Public areas keep the pre-repair hourly circuit (Grade C
        # assumption), i.e. one metered pass per 1-hour epoch.
        assert core._outbreak_cleaning_event_counts[PUBLIC] == 24

    def test_activation_edge_fires_one_immediate_pass(self) -> None:
        core = _core(
            clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
            cabin_events=0.0,
            public_events=0.0,
        )
        _seed_masses(core)
        before = core.surface_pools_by_pathogen[PATHOGEN][CABIN]
        core.set_outbreak_disinfection(REDUCTION)
        after_edge = core.surface_pools_by_pathogen[PATHOGEN][CABIN]
        assert after_edge < before
        # Staying armed with no metered rate must not re-fire on the edge
        # path: further calls change nothing.
        core.set_outbreak_disinfection(REDUCTION)
        assert core.surface_pools_by_pathogen[PATHOGEN][CABIN] == pytest.approx(
            after_edge,
        )


class TestGradedSensitivity:
    """Cabin events_per_day is a live knob: more sourced passes -> less
    surviving emesis-patch mass after the same 24 simulated hours."""

    def test_cabin_events_per_day_orders_surviving_mass(self) -> None:
        survivors: list[float] = []
        for cabin_events in (0.0, 1.0, 4.0):
            core = _core(
                clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
                cabin_events=cabin_events,
            )
            _seed_masses(core)
            _run_sop_hours(core, 24.0)
            survivors.append(_patch(core).mass)
        assert survivors[0] > survivors[1] > survivors[2]
        span = (survivors[0] - survivors[2]) / survivors[0]
        assert span > 0.2, f"cabin pass rate looks dead: span={span:.3f}"

    def test_cabin_coverage_override_reaches_metered_passes(self) -> None:
        """A per-zone-class coverage override must reach the metered pass.

        Cabin coverage below the routine coverage kills the routine->outbreak
        nesting, so every metered pass leaves strictly more patch mass than
        the default 0.58 coverage. A live difference asserts the override
        actually reached `_outbreak_cleaning_event`, not just the parser.
        """
        survivors: dict[float, float] = {}
        for coverage in (0.20, OUTBREAK_CLEANING_COVERAGE):
            core = _core(
                clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
                cabin_coverage=coverage,
            )
            _seed_masses(core)
            _run_sop_hours(core, 24.0)
            survivors[coverage] = _patch(core).mass
        assert survivors[0.20] > survivors[OUTBREAK_CLEANING_COVERAGE]


class TestBounds:
    def test_cabin_patch_survives_24h_of_sop(self) -> None:
        """A cabin patch must retain a non-negligible share after 24 h.

        Arithmetic, not a fitted bound: the sourced cabin rate is one
        metered 4.29-log10 pass per day plus the activation-edge pass —
        two passes, 8.58 log10 total, so the retained fraction is
        10^-8.58 ~= 2.6e-9. Pre-repair the same window applied 24 passes
        (~103 log10). The bound asserts >= 1e-11, two decades of margin
        below the sourced arithmetic and far above the defect's annihilation.
        """
        core = _core(clock=SimClock(epoch_duration_hours=1.0, mode="hours"))
        _seed_masses(core)
        _run_sop_hours(core, 24.0)
        remaining = _patch(core).mass
        assert math.isfinite(remaining)
        assert remaining >= 1.0e7 * 1e-11
        assert remaining <= 1.0e7


class TestEdgeBehaviour:
    def test_clearing_silences_meter_and_rearming_fires_new_edge(self) -> None:
        core = _core(clock=SimClock(epoch_duration_hours=1.0, mode="hours"))
        _seed_masses(core)
        _run_sop_hours(core, 24.0)
        cabin_passes = core._outbreak_cleaning_event_counts[CABIN]
        public_passes = core._outbreak_cleaning_event_counts[PUBLIC]
        # SOP cleared for a day: nothing fires.
        for _ in range(24):
            core.set_outbreak_disinfection(None)
        assert core._outbreak_cleaning_event_counts[CABIN] == cabin_passes
        assert core._outbreak_cleaning_event_counts[PUBLIC] == public_passes
        mass_before = _patch(core).mass
        # Re-activation is a fresh edge: one immediate pass.
        core.set_outbreak_disinfection(REDUCTION)
        assert _patch(core).mass < mass_before
