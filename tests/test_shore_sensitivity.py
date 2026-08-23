"""Graded sensitivity and surface checks for the shore model."""

from __future__ import annotations

import numpy as np
import pytest

from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability
from picard_framework.analysis.shore import (
    PortCallImportation,
    ShoreRenewalParameters,
    benefit_surface,
    evaluate_counterfactual,
    renewal_result,
)

HORIZON = 200


def _capability(**overrides: object) -> PortSurveillanceCapability:
    values: dict[str, object] = {
        "port_id": "TESTPORT",
        "port_name": "Test Port",
        "region": "TEST",
        "population": 200_000,
        "syndromic_enabled": True,
        "syndromic_coverage": 0.5,
        "syndromic_delay_days": 3,
        "syndromic_pathogens": (),
    }
    values.update(overrides)
    return PortSurveillanceCapability(**values)


def _parameters(**overrides: float) -> ShoreRenewalParameters:
    values: dict[str, float | int] = {
        "r_shore": 0.5,
        "generation_median_hours": 48.0,
        "generation_sigma": 0.6,
        "generation_max_hours": 336.0,
        "population": 200_000,
    }
    values.update(overrides)
    return ShoreRenewalParameters(**values)  # type: ignore[arg-type]


def _continuous_importation(
    *,
    ship_detection_epoch: int = 5,
    rate: float = 2.0,
) -> PortCallImportation:
    series = tuple(rate for _ in range(HORIZON))
    return PortCallImportation(
        port_id="TESTPORT",
        pathogen_id="norwalk_gi",
        epoch_hours=24.0,
        strain_importations={"GII.4": series, "GII.17": tuple(0.5 * x for x in series)},
        ship_detection_epoch=ship_detection_epoch,
    )


def _pulse_importation(*, late: bool = False) -> PortCallImportation:
    values = [0.0] * HORIZON
    start = 60 if late else 0
    for epoch in range(start, start + 20):
        values[epoch] = 4.0
    return PortCallImportation(
        port_id="TESTPORT",
        pathogen_id="norwalk_gi",
        epoch_hours=24.0,
        strain_importations={"GII.4": tuple(values)},
        ship_detection_epoch=10,
    )


class TestSensitivity:
    """Every caller-supplied seam moves a reported outcome in a graded way."""

    def test_benefit_is_monotone_in_detection_lead_with_minimum_effect(self) -> None:
        benefits = []
        for ship_epoch in (4, 3, 2, 1, 0):
            result = evaluate_counterfactual(
                _continuous_importation(ship_detection_epoch=ship_epoch),
                _parameters(),
                residual_importation_fraction=0.0,
                case_threshold=10.0,
                capability=_capability(),
            )
            benefits.append(result.benefit)
        assert all(left <= right for left, right in zip(benefits, benefits[1:]))
        assert min(np.diff(benefits)) > 1.0

    def test_r_shore_has_ordered_positive_separation(self) -> None:
        totals = [
            renewal_result(_continuous_importation(), _parameters(r_shore=value)).total_cases
            for value in (0.1, 0.3, 0.5, 0.7)
        ]
        assert all(left < right for left, right in zip(totals, totals[1:]))
        assert totals[-1] - totals[0] > 10.0

    def test_generation_median_has_ordered_separation(self) -> None:
        importation = _pulse_importation()
        totals = [
            renewal_result(
                importation,
                _parameters(
                    r_shore=0.8,
                    generation_median_hours=median,
                    generation_max_hours=1344.0,
                ),
            ).total_cases
            for median in (24.0, 72.0, 168.0, 336.0)
        ]
        assert all(left > right for left, right in zip(totals, totals[1:]))
        assert totals[0] - totals[-1] > 1.0

    def test_reporting_delay_has_ordered_positive_separation(self) -> None:
        benefits = []
        for delay_days in (1, 3, 7, 14):
            result = evaluate_counterfactual(
                _continuous_importation(),
                _parameters(),
                residual_importation_fraction=0.0,
                case_threshold=10.0,
                capability=_capability(syndromic_delay_days=delay_days),
            )
            benefits.append(result.benefit)
        assert all(left < right for left, right in zip(benefits, benefits[1:]))
        assert benefits[-1] - benefits[0] > 10.0

    def test_importation_timing_moves_benefit(self) -> None:
        early = evaluate_counterfactual(
            _pulse_importation(late=False),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        late = evaluate_counterfactual(
            _pulse_importation(late=True),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert late.benefit > early.benefit
        assert late.benefit - early.benefit > 20.0

    def test_strain_relabel_is_a_negative_control(self) -> None:
        base = _continuous_importation()
        relabelled = PortCallImportation(
            port_id=base.port_id,
            pathogen_id=base.pathogen_id,
            epoch_hours=base.epoch_hours,
            strain_importations={"unrelated-label": base.strain_importations["GII.4"]},
            ship_detection_epoch=base.ship_detection_epoch,
        )
        params = _parameters()
        first = renewal_result(base, params)
        second = renewal_result(relabelled, params)
        assert second.total_cases == pytest.approx(first.total_by_strain["GII.4"])
        assert first.total_by_strain["GII.4"] == pytest.approx(
            second.total_cases,
            abs=1e-12,
        )


class TestSurface:
    """The reported surface exposes, rather than hides, R sensitivity."""

    def test_surface_has_cartesian_rows_and_insensitivity_summary(self) -> None:
        surface = benefit_surface(
            _continuous_importation(),
            r_shore_grid=(0.2, 0.5, 0.8),
            importation_multiplier_grid=(0.5, 1.0, 2.0),
            generation_median_hours=48.0,
            generation_sigma=0.6,
            generation_max_hours=336.0,
            population=200_000,
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert len(surface["rows"]) == 9
        summary = surface["summary"]
        # Measured on the 3x3 surface: fraction CV across R = 0.066288 and
        # arm-total CV across R = 0.559986, ratio = 0.118374.
        assert summary["benefit_fraction_cv_across_r"] < summary["arm_total_cv_across_r"]
        assert summary["cv_ratio_across_r"] < 0.5

    def test_surface_grid_validation(self) -> None:
        kwargs = {
            "generation_median_hours": 48.0,
            "generation_sigma": 0.6,
            "generation_max_hours": 336.0,
            "population": 200_000,
            "residual_importation_fraction": 0.0,
            "case_threshold": 10.0,
            "capability": _capability(),
        }
        importation = _continuous_importation()
        empty_grid: tuple[float, ...] = ()
        unit_grid = (1.0,)
        negative_r = (-0.1,)
        single_r = (0.5,)
        infinite_multiplier = (float("inf"),)
        with pytest.raises(ValueError, match="non-empty"):
            benefit_surface(
                importation,
                r_shore_grid=empty_grid,
                importation_multiplier_grid=unit_grid,
                **kwargs,
            )
        with pytest.raises(ValueError, match="r_shore_grid"):
            benefit_surface(
                importation,
                r_shore_grid=negative_r,
                importation_multiplier_grid=unit_grid,
                **kwargs,
            )
        with pytest.raises(ValueError, match="multiplier"):
            benefit_surface(
                importation,
                r_shore_grid=single_r,
                importation_multiplier_grid=infinite_multiplier,
                **kwargs,
            )

    def test_degenerate_benefit_column_reports_zero_dispersion(self) -> None:
        surface = benefit_surface(
            _continuous_importation(),
            r_shore_grid=(0.2, 0.5, 0.8),
            importation_multiplier_grid=(0.5, 1.0, 2.0),
            generation_median_hours=48.0,
            generation_sigma=0.6,
            generation_max_hours=336.0,
            population=200_000,
            residual_importation_fraction=1.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        summary = surface["summary"]
        assert summary["benefit_fraction_cv_across_r"] == pytest.approx(0.0)
        assert summary["cv_ratio_across_r"] == pytest.approx(0.0)
