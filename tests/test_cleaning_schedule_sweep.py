from __future__ import annotations

import math

import numpy as np
import pytest

from engines.sim_clock import SimClock
from engines.transmission_core import (
    OUTBREAK_CLEANING_COVERAGE,
    ROUTINE_CLEANING_COVERAGE,
    ROUTINE_CLEANING_LOG10_REDUCTION,
    TransmissionCore,
)
from telemetry_buffer.observation_model import cleaning_schedule_sweep

PATHOGEN = "norwalk_gi"
ZONES = {
    "Cabin-1": "Cabin_Corridor",
    "Dining-1": "Dining",
    "Bridge": "Work",
}


def _core(
    *,
    by_zone_class: dict[str, dict[str, float]] | None = None,
    clock: SimClock | None = None,
) -> TransmissionCore:
    routine = {
        "coverage": ROUTINE_CLEANING_COVERAGE,
        "log10_reduction": ROUTINE_CLEANING_LOG10_REDUCTION,
        "events_per_day": 1.0,
    }
    if by_zone_class is not None:
        routine["by_zone_class"] = by_zone_class
    return TransmissionCore(
        np.random.default_rng(11),
        pathogen_profiles={PATHOGEN: {"surface_decay_per_day": 0.25}},
        zone_types=ZONES,
        clock=clock,
        cfg={
            "transmission": {
                "surface_cleaning": {
                    "enabled": True,
                    "routine": routine,
                    "outbreak_response": {
                        "coverage": OUTBREAK_CLEANING_COVERAGE,
                        "log10_reduction": 4.29,
                    },
                },
            },
        },
    )


def _run_day(core: TransmissionCore) -> None:
    core.initialize_zones(list(ZONES))
    for zone_name in ZONES:
        core._deposit_surface_mass(PATHOGEN, zone_name, 10.0)
    for _ in range(24):
        core._update_surface_pools({})


def test_unset_zone_schedule_is_uniform_default() -> None:
    default = _core()
    explicit = _core(
        by_zone_class={
            zone_class: {
                "coverage": ROUTINE_CLEANING_COVERAGE,
                "events_per_day": 1.0,
            }
            for zone_class in ("cabin", "dining", "public", "galley", "crew_mess")
        },
    )
    assert default.routine_cleaning_by_zone_class == {}
    assert default._routine_cleaning_schedule("Cabin-1") == (
        ROUTINE_CLEANING_COVERAGE,
        1.0,
    )
    assert default._routine_cleaning_schedule("Bridge") == (
        ROUTINE_CLEANING_COVERAGE,
        1.0,
    )
    _run_day(default)
    _run_day(explicit)
    assert default.surface_pools_by_pathogen == explicit.surface_pools_by_pathogen
    assert default._routine_cleaning_event_counts == (
        explicit._routine_cleaning_event_counts
    )


def test_frequency_change_only_increases_passes_for_that_class() -> None:
    core = _core(
        by_zone_class={
            "cabin": {"events_per_day": 3.0},
            "public": {"events_per_day": 2.0},
        },
    )
    _run_day(core)
    assert core._routine_cleaning_event_counts["Cabin-1"] == 3
    assert core._routine_cleaning_event_counts["Bridge"] == 2
    assert core._routine_cleaning_event_counts["Dining-1"] == 1


@pytest.mark.parametrize(
    "zone_class, zone_name",
    [("cabin", "Cabin-1"), ("public", "Bridge"), ("dining", "Dining-1")],
)
def test_schedule_is_clock_invariant_per_zone_class(
    zone_class: str,
    zone_name: str,
) -> None:
    schedule = {
        zone_class: {
            "coverage": 0.5,
            "events_per_day": 3.0,
        },
    }
    hourly = _core(
        by_zone_class=schedule,
        clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
    )
    legacy = _core(by_zone_class=schedule, clock=SimClock(mode="legacy_epoch_day"))
    for core in (hourly, legacy):
        core.initialize_zones([zone_name])
        core._deposit_surface_mass(PATHOGEN, zone_name, 10.0)
    for _ in range(24):
        hourly._update_surface_pools({})
    legacy._update_surface_pools({})
    assert hourly._routine_cleaning_event_counts[zone_name] == 3
    assert legacy._routine_cleaning_event_counts[zone_name] == 3
    assert hourly._routine_cleaning_event_counts[zone_name] == (
        legacy._routine_cleaning_event_counts[zone_name]
    )


def test_unknown_zone_class_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown.*zone class"):
        _core(by_zone_class={"atrium": {"coverage": 0.4}})


def test_schedule_resolution_clamps_mutable_coverage() -> None:
    core = _core(by_zone_class={"public": {"coverage": 0.4}})
    core.routine_cleaning_by_zone_class["public"]["coverage"] = 2.0
    core.routine_cleaning_coverage = -1.0
    assert core._routine_cleaning_schedule("Bridge")[0] == 1.0
    assert core._routine_cleaning_schedule("Cabin-1")[0] == 0.0


@pytest.mark.parametrize(
    "schedule, message",
    [
        ([], "must be a mapping"),
        ({"public": []}, "must be a mapping"),
        ({"public": {"unexpected": 1.0}}, "unknown fields"),
    ],
)
def test_malformed_zone_schedule_is_rejected(
    schedule: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _core(by_zone_class=schedule)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "setting",
    [
        {"coverage": -0.1},
        {"coverage": 1.1},
        {"events_per_day": -1.0},
    ],
)
def test_zone_schedule_bounds_are_rejected(
    setting: dict[str, float],
) -> None:
    with pytest.raises(ValueError):
        _core(by_zone_class={"public": setting})


def test_disinfection_nesting_uses_each_zone_coverage() -> None:
    core = _core(
        by_zone_class={
            "cabin": {"coverage": 0.2},
            "public": {"coverage": 0.5},
        },
    )
    core.initialize_zones(["Cabin-1", "Bridge"])
    for zone_name in ("Cabin-1", "Bridge"):
        core._deposit_surface_mass(PATHOGEN, zone_name, 100.0)
    core.disinfect_surfaces(4.29, OUTBREAK_CLEANING_COVERAGE)
    kill = 10.0 ** -4.29
    for zone_name, routine_coverage in (("Cabin-1", 0.2), ("Bridge", 0.5)):
        nested = (OUTBREAK_CLEANING_COVERAGE - routine_coverage) / (
            1.0 - routine_coverage
        )
        expected = (
            routine_coverage * kill
            + (1.0 - routine_coverage) * (
                1.0 - nested * (1.0 - kill)
            )
        )
        actual = core.surface_pools_by_pathogen[PATHOGEN][zone_name] / 100.0
        assert actual == pytest.approx(expected)


def test_sweep_grid_has_specified_endpoints_and_geometric_midpoints() -> None:
    cabin_coverage = cleaning_schedule_sweep.grid_values(
        cleaning_schedule_sweep.COVERAGE_BOUNDS["cabin"],
    )
    cabin_events = cleaning_schedule_sweep.grid_values(
        cleaning_schedule_sweep.FREQUENCY_BOUNDS["cabin"],
        geometric=True,
    )
    public_coverage = cleaning_schedule_sweep.grid_values(
        cleaning_schedule_sweep.COVERAGE_BOUNDS["public"],
    )
    public_events = cleaning_schedule_sweep.grid_values(
        cleaning_schedule_sweep.FREQUENCY_BOUNDS["public"],
        geometric=True,
    )
    assert len(cabin_coverage) == len(cabin_events) == 3
    assert len(public_coverage) == len(public_events) == 3
    assert cabin_coverage[0] == pytest.approx(0.336)
    assert cabin_coverage[-1] == pytest.approx(0.600)
    assert public_coverage[0] == pytest.approx(0.292)
    assert public_coverage[-1] == pytest.approx(0.454)
    assert cabin_events[1] == pytest.approx(math.sqrt(0.33))
    assert public_events[1] == pytest.approx(math.sqrt(12.0))
    assert cabin_events[1] != pytest.approx((0.33 + 1.0) / 2.0)
    assert len(cleaning_schedule_sweep.sweep_cells()) == 81


def test_emesis_sweep_reuses_the_fixed_schedule_grid() -> None:
    cells = cleaning_schedule_sweep.sweep_cells()
    for fraction in cleaning_schedule_sweep.CABIN_LOCALIZATION_SWEEP:
        emesis = cleaning_schedule_sweep.emesis_cells(fraction, cells)
        assert len(emesis) == 81
        gradients = [cell["emesis_gradient"] for cell in emesis]
        assert all(math.isfinite(value) and value > 0.0 for value in gradients)


def test_emesis_cells_defaults_to_full_sweep() -> None:
    fraction = cleaning_schedule_sweep.CABIN_LOCALIZATION_SWEEP[0]
    emesis = cleaning_schedule_sweep.emesis_cells(fraction)
    assert len(emesis) == 81
    assert all(cell["emesis_gradient"] > 0.0 for cell in emesis)


class TestRenderAndMain:
    """Report render covers envelope lines; main writes the sidecar file."""

    def test_render_reports_finite_envelope(self) -> None:
        report = cleaning_schedule_sweep._render()
        assert "Cleaning schedule sweep" in report
        assert "Hand-only envelope" in report
        assert "Emesis-inclusive envelope" in report
        assert "Rule 3:" in report
        assert "minimum gradient:" in report
        assert "maximum gradient:" in report
        # Every numeric gradient token in the table body stays finite.
        assert "nan" not in report.lower()
        assert "inf" not in report.lower()

    def test_uniform_emesis_values_grade_with_localization(self) -> None:
        from telemetry_buffer.observation_model.park_surface_check import expectations

        exp_ = expectations()
        fractions = list(cleaning_schedule_sweep.CABIN_LOCALIZATION_SWEEP[:3])
        gradients = [
            cleaning_schedule_sweep._uniform_emesis_values(f, exp_)[2]
            for f in fractions
        ]
        assert all(math.isfinite(g) and g > 0.0 for g in gradients)
        # Higher cabin localization raises the cabin/public gradient.
        assert gradients == sorted(gradients)
        assert gradients[-1] - gradients[0] > 1.0

    def test_main_writes_output_sidecar(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "cleaning_schedule_sweep_out.txt"

        class _FakePath:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

            def with_name(self, name: str):
                assert name == "cleaning_schedule_sweep_out.txt"
                return out

        monkeypatch.setattr(cleaning_schedule_sweep, "Path", _FakePath)
        cleaning_schedule_sweep.main()
        captured = capsys.readouterr().out
        assert out.is_file()
        text = out.read_text(encoding="utf-8")
        assert "Cleaning schedule sweep" in text
        assert "written:" in captured
        assert all(
            math.isfinite(cell["gradient"])
            for cell in cleaning_schedule_sweep.sweep_cells()
        )
