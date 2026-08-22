"""Counterfactual shore cases for ship- and port-timed export control."""

from __future__ import annotations

import numpy as np
import pytest

from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability
from picard_framework.analysis.shore import (
    PortCallImportation,
    ShoreRenewalParameters,
    detect_port,
    evaluate_counterfactual,
    port_detection_epoch,
)

EPOCH_HOURS = 24.0
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


def _importation(
    *,
    ship_detection_epoch: int | None = 2,
    values: tuple[float, ...] | None = None,
    pathogen_id: str = "norwalk_gi",
) -> PortCallImportation:
    series = values or tuple(2.0 for _ in range(HORIZON))
    return PortCallImportation(
        port_id="TESTPORT",
        pathogen_id=pathogen_id,
        epoch_hours=EPOCH_HOURS,
        strain_importations={
            "GII.4": series,
            "GII.17": tuple(0.5 * value for value in series),
        },
        ship_detection_epoch=ship_detection_epoch,
    )


class TestCounterfactual:
    """The only arm difference is the epoch at which imports are curtailed."""

    def test_zero_importations_zero_cases_and_benefit(self) -> None:
        result = evaluate_counterfactual(
            _importation(values=tuple(0.0 for _ in range(HORIZON))),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=1.0,
            capability=_capability(),
        )
        assert result.total_ship_arm == pytest.approx(0.0)
        assert result.total_port_arm == pytest.approx(0.0)
        assert result.benefit == pytest.approx(0.0)
        assert result.benefit_fraction == pytest.approx(0.0)
        assert result.port_detection_epoch is None
        assert result.detection_lead_epochs is None

    def test_earlier_ship_detection_has_more_benefit(self) -> None:
        importation = _importation(ship_detection_epoch=0)
        result = evaluate_counterfactual(
            importation,
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert result.ship_detection_epoch == 0
        assert result.port_detection_epoch is not None
        assert result.detection_lead_epochs == result.port_detection_epoch
        assert result.benefit > 0.0
        assert result.benefit_fraction == pytest.approx(
            result.benefit / result.total_port_arm,
        )

    def test_full_residual_export_makes_arms_identical(self) -> None:
        result = evaluate_counterfactual(
            _importation(),
            _parameters(),
            residual_importation_fraction=1.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert result.total_ship_arm == pytest.approx(result.total_port_arm)
        assert result.benefit == pytest.approx(0.0)

    def test_negative_benefit_is_not_clamped(self) -> None:
        result = evaluate_counterfactual(
            _importation(ship_detection_epoch=10),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert result.port_detection_epoch is not None
        assert result.detection_lead_epochs < 0
        assert result.benefit < 0.0
        assert result.benefit_fraction > -1.0

    def test_missing_ship_detection_is_preserved_and_not_curtailed(self) -> None:
        result = evaluate_counterfactual(
            _importation(ship_detection_epoch=None),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert result.ship_detection_epoch is None
        assert result.detection_lead_epochs is None
        assert result.total_ship_arm > result.total_port_arm
        assert result.benefit < 0.0

    def test_missing_port_detection_is_preserved_and_not_curtailed(self) -> None:
        result = evaluate_counterfactual(
            _importation(),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=1e9,
            capability=_capability(),
        )
        assert result.port_detection_epoch is None
        assert result.detection_lead_epochs is None
        assert result.total_port_arm > result.total_ship_arm
        assert result.benefit > 0.0

    def test_detection_beyond_horizon_is_handled(self) -> None:
        result = evaluate_counterfactual(
            _importation(ship_detection_epoch=HORIZON + 100),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=1.0,
            capability=_capability(),
        )
        assert result.ship_detection_epoch == HORIZON + 100
        assert result.total_ship_arm > 0.0
        assert result.detection_lead_epochs < 0

    def test_negative_residual_fraction_rejected(self) -> None:
        with pytest.raises(ValueError, match="residual_importation_fraction"):
            evaluate_counterfactual(
                _importation(),
                _parameters(),
                residual_importation_fraction=-0.1,
                case_threshold=1.0,
                capability=_capability(),
            )

    def test_non_integer_detection_epoch_rejected(self) -> None:
        with pytest.raises(ValueError, match="integer"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0,)},
                ship_detection_epoch=1.5,  # type: ignore[arg-type]
            )

    def test_residual_fraction_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="residual_importation_fraction"):
            evaluate_counterfactual(
                _importation(),
                _parameters(),
                residual_importation_fraction=1.1,
                case_threshold=1.0,
                capability=_capability(),
            )

    def test_per_strain_arms_conserve_combined_totals(self) -> None:
        result = evaluate_counterfactual(
            _importation(),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert sum(result.ship_arm.total_by_strain.values()) == pytest.approx(
            result.ship_arm.total_cases,
        )
        assert sum(result.port_arm.total_by_strain.values()) == pytest.approx(
            result.port_arm.total_cases,
        )
        assert np.all(result.ship_arm.trajectory >= 0.0)
        assert np.all(result.port_arm.trajectory >= 0.0)

    def test_benefit_fraction_stays_bounded_for_valid_positive_lead(self) -> None:
        result = evaluate_counterfactual(
            _importation(ship_detection_epoch=0),
            _parameters(),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=_capability(),
        )
        assert -1.0 <= result.benefit_fraction <= 1.0


class TestDetection:
    """Port detection uses canonical incubation and profile reporting delay."""

    def test_threshold_never_crossed_returns_none(self) -> None:
        detected = port_detection_epoch(
            np.ones(30),
            port_id="TESTPORT",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            case_threshold=1e9,
            capability=_capability(),
        )
        assert detected is None

    def test_empty_incidence_returns_none(self) -> None:
        assert port_detection_epoch(
            [],
            port_id="TESTPORT",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            case_threshold=1.0,
            capability=_capability(),
        ) is None

    def test_alias_matches_primary_detection_function(self) -> None:
        kwargs = {
            "port_id": "TESTPORT",
            "pathogen_id": "norwalk_gi",
            "epoch_hours": EPOCH_HOURS,
            "case_threshold": 5.0,
            "capability": _capability(),
        }
        primary = port_detection_epoch(np.full(30, 5.0), **kwargs)
        alias = detect_port(np.full(30, 5.0), **kwargs)
        assert alias == primary

    def test_reporting_delay_and_lab_turnaround_are_added(self) -> None:
        incidence = np.full(30, 5.0)
        syndromic_only = port_detection_epoch(
            incidence,
            port_id="TESTPORT",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            case_threshold=5.0,
            capability=_capability(syndromic_delay_days=2),
        )
        with_lab = port_detection_epoch(
            incidence,
            port_id="TESTPORT",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            case_threshold=5.0,
            capability=_capability(
                syndromic_delay_days=2,
                lab_confirmation=True,
                lab_turnaround_days=3.0,
            ),
        )
        assert with_lab - syndromic_only == 3

    def test_non_reportable_pathogen_returns_none(self) -> None:
        capability = _capability(syndromic_pathogens=("dengue",))
        assert port_detection_epoch(
            np.full(30, 5.0),
            port_id="TESTPORT",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            case_threshold=5.0,
            capability=capability,
        ) is None

    def test_active_profile_and_public_label_are_adapted(self) -> None:
        capability = _capability(syndromic_pathogens=("norovirus",))
        detected = port_detection_epoch(
            np.full(30, 5.0),
            port_id="TESTPORT",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            case_threshold=5.0,
            capability=capability,
        )
        assert detected is not None

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({"epoch_hours": 0.0}, "epoch_hours"),
            ({"case_threshold": -1.0}, "case_threshold"),
            ({"case_threshold": float("inf")}, "case_threshold"),
        ],
    )
    def test_detection_arguments_are_validated(
        self,
        kwargs: dict[str, object],
        message: str,
    ) -> None:
        args: dict[str, object] = {
            "port_id": "TESTPORT",
            "pathogen_id": "norwalk_gi",
            "epoch_hours": EPOCH_HOURS,
            "case_threshold": 1.0,
            "capability": _capability(),
        }
        args.update(kwargs)
        with pytest.raises(ValueError, match=message):
            port_detection_epoch([1.0], **args)

    def test_unknown_active_profile_is_rejected(self) -> None:
        with pytest.raises(KeyError, match="missing"):
            port_detection_epoch(
                [1.0],
                port_id="TESTPORT",
                pathogen_id="missing",
                epoch_hours=EPOCH_HOURS,
                case_threshold=1.0,
                capability=_capability(),
            )
