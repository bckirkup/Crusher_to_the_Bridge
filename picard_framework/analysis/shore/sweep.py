"""Cartesian shore benefit surfaces over the explicitly swept R axis.

``R_shore`` is unanchored, so a single benefit number would be an artefact of
whichever value was chosen.  The deliverable is therefore a surface over
``R_shore`` x importation multiplier, together with a reported measure of how
much of the answer the unanchored axis actually moves.

That measure is a coefficient of variation across the ``R_shore`` grid at fixed
importation multiplier, averaged over multipliers.  Comparing a raw standard
deviation of a dimensionless fraction against a raw standard deviation of case
counts would be a units artefact, so both quantities are normalised by their
own mean before being compared.  The relative benefit (``benefit_fraction``)
is expected to be far less sensitive to ``R_shore`` than the absolute arm
totals are, which is exactly the claim the surface has to demonstrate rather
than assume.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import product
from math import isfinite
from typing import Any, Iterable, Sequence, cast

import numpy as np

from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability
from picard_framework.analysis.shore.counterfactual import evaluate_counterfactual
from picard_framework.analysis.shore.importation import PortCallImportation
from picard_framework.analysis.shore.renewal import ShoreRenewalParameters


def _scaled_importation(
    importation: PortCallImportation,
    multiplier: float,
) -> PortCallImportation:
    """Scale every exported strain without changing labels or timing."""
    return cast(
        PortCallImportation,
        replace(
            importation,
            strain_importations={
                label: tuple(float(value) * multiplier for value in values)
                for label, values in importation.strain_importations.items()
            },
        ),
    )


def _row(
    importation: PortCallImportation,
    params: ShoreRenewalParameters,
    *,
    multiplier: float,
    residual_importation_fraction: float,
    case_threshold: float,
    capability: PortSurveillanceCapability | None,
    surveillance_label: str | None,
) -> dict[str, Any]:
    """Run and flatten one Cartesian surface point."""
    result = evaluate_counterfactual(
        _scaled_importation(importation, multiplier),
        params,
        residual_importation_fraction=residual_importation_fraction,
        case_threshold=case_threshold,
        capability=capability,
        surveillance_label=surveillance_label,
    )
    return {
        "r_shore": params.r_shore,
        "multiplier": multiplier,
        "total_ship_arm": result.total_ship_arm,
        "total_port_arm": result.total_port_arm,
        "benefit": result.benefit,
        "benefit_fraction": result.benefit_fraction,
        "detection_lead_epochs": result.detection_lead_epochs,
        "ship_detection_epoch": result.ship_detection_epoch,
        "port_detection_epoch": result.port_detection_epoch,
        "depletion_regime_ship": result.depletion_regime_ship,
        "depletion_regime_port": result.depletion_regime_port,
        "unbounded_growth_ship": result.ship_arm.unbounded_growth,
        "unbounded_growth_port": result.port_arm.unbounded_growth,
    }


def _relative_dispersion(values: Sequence[float]) -> float:
    """Coefficient of variation of a non-empty column, 0.0 at a zero mean."""
    arr = np.asarray(list(values), dtype=float)
    mean = float(np.mean(arr))
    return 0.0 if abs(mean) < 1e-15 else float(np.std(arr)) / abs(mean)


def _mean_cv_across_r(
    rows: list[dict[str, Any]],
    multipliers: tuple[float, ...],
    key: str,
) -> float:
    """Mean over multipliers of one metric's CV across the ``R_shore`` grid."""
    columns = [
        [row[key] for row in rows if row["multiplier"] == multiplier]
        for multiplier in multipliers
    ]
    per_column = [_relative_dispersion(column) for column in columns]
    return float(np.mean(per_column))


def benefit_surface(
    importation: PortCallImportation,
    *,
    r_shore_grid: Iterable[float],
    importation_multiplier_grid: Iterable[float],
    generation_median_hours: float,
    generation_sigma: float,
    generation_max_hours: float,
    population: int,
    residual_importation_fraction: float,
    case_threshold: float,
    capability: PortSurveillanceCapability | None = None,
    surveillance_label: str | None = None,
) -> dict[str, Any]:
    """Return rows and dispersion summary for ``R_shore × multiplier``.

    ``R_shore`` and the generation interval are intentionally required axes or
    fields: they are unanchored and must not acquire a convenient default.
    """
    r_values = tuple(float(value) for value in r_shore_grid)
    multipliers = tuple(float(value) for value in importation_multiplier_grid)
    if not r_values or not multipliers:
        raise ValueError("both sweep grids must be non-empty")
    if any(not isfinite(value) or value < 0.0 for value in r_values):
        raise ValueError("r_shore_grid must contain finite non-negative values")
    if any(not isfinite(value) or value < 0.0 for value in multipliers):
        raise ValueError("importation_multiplier_grid must contain finite non-negative values")
    rows = [
        _row(
            importation,
            ShoreRenewalParameters(
                r_shore=r_value,
                generation_median_hours=generation_median_hours,
                generation_sigma=generation_sigma,
                generation_max_hours=generation_max_hours,
                population=population,
            ),
            multiplier=multiplier,
            residual_importation_fraction=residual_importation_fraction,
            case_threshold=case_threshold,
            capability=capability,
            surveillance_label=surveillance_label,
        )
        for r_value, multiplier in product(r_values, multipliers)
    ]
    fraction_cv = _mean_cv_across_r(rows, multipliers, "benefit_fraction")
    ship_cv = _mean_cv_across_r(rows, multipliers, "total_ship_arm")
    port_cv = _mean_cv_across_r(rows, multipliers, "total_port_arm")
    arm_total_cv = 0.5 * (ship_cv + port_cv)
    return {
        "rows": rows,
        "summary": {
            "benefit_fraction_cv_across_r": fraction_cv,
            "ship_arm_total_cv_across_r": ship_cv,
            "port_arm_total_cv_across_r": port_cv,
            "arm_total_cv_across_r": arm_total_cv,
            "cv_ratio_across_r": (
                0.0 if abs(arm_total_cv) < 1e-15 else fraction_cv / arm_total_cv
            ),
            "r_shore_values": list(r_values),
            "importation_multipliers": list(multipliers),
        },
    }
