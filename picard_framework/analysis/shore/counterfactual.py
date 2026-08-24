"""Ship-versus-port detection counterfactual on one shore renewal process."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability
from picard_framework.analysis.shore.detection import port_detection_epoch
from picard_framework.analysis.shore.importation import PortCallImportation
from picard_framework.analysis.shore.renewal import (
    ShoreRenewalParameters,
    ShoreRenewalResult,
    renewal_result,
)


def _validate_fraction(value: float) -> float:
    """Validate residual export after detection."""
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError("residual_importation_fraction must be in [0, 1]")
    return float(value)


def _curtailed_importation(
    importation: PortCallImportation,
    detection_epoch: int | None,
    residual_fraction: float,
) -> PortCallImportation:
    """Apply one detection arm's export curtailment."""
    if detection_epoch is None:
        return importation
    factor = np.ones(importation.horizon, dtype=float)
    factor[max(int(detection_epoch), 0) :] = residual_fraction
    return PortCallImportation(
        port_id=importation.port_id,
        pathogen_id=importation.pathogen_id,
        epoch_hours=importation.epoch_hours,
        strain_importations={
            label: tuple(np.asarray(values, dtype=float) * factor)
            for label, values in importation.strain_importations.items()
        },
        ship_detection_epoch=importation.ship_detection_epoch,
    )


@dataclass(frozen=True)
class ShoreArmResult:
    """One arm's combined and strain-resolved renewal trajectory."""

    total_cases: float
    trajectory: np.ndarray
    total_by_strain: Mapping[str, float]
    trajectories_by_strain: Mapping[str, np.ndarray]
    attack_fraction: float
    depletion_regime: bool
    unbounded_growth: bool


def _arm_result(result: ShoreRenewalResult) -> ShoreArmResult:
    """Expose the renewal result under arm terminology."""
    return ShoreArmResult(
        total_cases=result.total_cases,
        trajectory=result.trajectory,
        total_by_strain=result.total_by_strain,
        trajectories_by_strain=result.by_strain,
        attack_fraction=result.attack_fraction,
        depletion_regime=result.depletion_regime,
        unbounded_growth=result.unbounded_growth,
    )


@dataclass(frozen=True)
class CounterfactualResult:
    """Difference between ship-timed and port-timed export curtailment."""

    ship_arm: ShoreArmResult
    port_arm: ShoreArmResult
    ship_detection_epoch: int | None
    port_detection_epoch: int | None
    detection_lead_epochs: int | None
    benefit: float
    benefit_fraction: float
    attack_fraction_ship: float
    attack_fraction_port: float
    depletion_regime_ship: bool
    depletion_regime_port: bool

    @property
    def total_ship_arm(self) -> float:
        """Return total shore cases in the ship-timed arm."""
        return self.ship_arm.total_cases

    @property
    def total_port_arm(self) -> float:
        """Return total shore cases in the port-timed arm."""
        return self.port_arm.total_cases


def evaluate_counterfactual(
    importation: PortCallImportation,
    parameters: ShoreRenewalParameters,
    *,
    residual_importation_fraction: float,
    case_threshold: float,
    capability: PortSurveillanceCapability | None = None,
    surveillance_label: str | None = None,
) -> CounterfactualResult:
    """Evaluate the required two-arm counterfactual.

    Port detection is computed from the uncontrolled trajectory.  A missing
    detection epoch remains ``None`` and means that arm never curtails export.
    """
    residual = _validate_fraction(residual_importation_fraction)
    uncontrolled = renewal_result(importation, parameters)
    port_epoch = port_detection_epoch(
        uncontrolled.trajectory,
        port_id=importation.port_id,
        pathogen_id=importation.pathogen_id,
        epoch_hours=importation.epoch_hours,
        case_threshold=case_threshold,
        capability=capability,
        surveillance_label=surveillance_label,
    )
    ship_importation = _curtailed_importation(
        importation,
        importation.ship_detection_epoch,
        residual,
    )
    port_importation = _curtailed_importation(importation, port_epoch, residual)
    ship_arm = _arm_result(renewal_result(ship_importation, parameters))
    port_arm = _arm_result(renewal_result(port_importation, parameters))
    benefit = port_arm.total_cases - ship_arm.total_cases
    fraction = (
        0.0
        if abs(port_arm.total_cases) < 1e-15
        else benefit / port_arm.total_cases
    )
    lead = (
        None
        if port_epoch is None or importation.ship_detection_epoch is None
        else port_epoch - importation.ship_detection_epoch
    )
    return CounterfactualResult(
        ship_arm=ship_arm,
        port_arm=port_arm,
        ship_detection_epoch=importation.ship_detection_epoch,
        port_detection_epoch=port_epoch,
        detection_lead_epochs=lead,
        benefit=float(benefit),
        benefit_fraction=float(fraction),
        attack_fraction_ship=ship_arm.attack_fraction,
        attack_fraction_port=port_arm.attack_fraction,
        depletion_regime_ship=ship_arm.depletion_regime,
        depletion_regime_port=port_arm.depletion_regime,
    )
