"""COVID-VULN-01: the susceptibility-shape A/B cell machinery.

The shipped ``dose_response: {beta_poisson, alpha 0.18, beta 58.0}`` on
``sars_cov2_resp`` carries the shape of the per-host susceptibility draw;
the register locks ``beta`` as a scale factor degenerate with Theta to
within 0.7% on the 5th-95th quantiles, so alpha alone is the shape axis.
This module declares the endpoint-only A/B — the same takeoff-conditioned
cells as RHYTHM-01 at the v12 admissible-band midpoint Theta = 2.37e11,
with ``dose_response.alpha`` set to each endpoint of the declared interval
and ``susceptibility_scale`` recomputed as ``Theta * (alpha + beta) /
alpha`` so E[s] = Theta on every arm and only the draw's shape moves.

Legs, conditioning, seed bases and the SOP-017 windows are the rhythm
A/B's verbatim (``covid_rhythm_cells``); the arms differ: each arm carries
a declared ``alpha`` instead of a rhythm flag, and every cell pins
``rhythm.enabled: true`` plus ``transmission.exposure_cap.enabled: true``
so the axis is measured on the cap-on/rhythm-on exposure-set context.

Cells enumerate leg-major, then arm (``alpha_lo`` before ``alpha_hi``),
then seed, so the canary is index 0 (mega/alpha_lo/seed 20200205) with its
hi-arm pair at index 20.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    SANITARY_VISIT_MODES,
)
from picard_framework.covid_rhythm_cells import (
    RhythmLeg,
    campaign_cell_dict,
    campaign_cell_key,
    enumerate_campaign_cells,
    find_leg,
    leg_spec,
    load_design_json,
    parse_leg_dicts,
    validate_leg_fields,
)

# Register-locked: beta^-1 is degenerate with the emission scale (Theta),
# so beta stays at the shipped value and alpha alone carries the shape.
BETA_FIXED = 58.0


@dataclass(frozen=True)
class VulnABDesign:
    """The alpha-endpoint A/B as declared before any cell ran."""

    design_id: str
    theta: float
    beta: float
    infection_age_days: float
    imports: int
    sanitary_visit_mode: str
    takeoff_recorded_onsets: int
    arms: tuple[dict[str, Any], ...]
    legs: tuple[RhythmLeg, ...]
    seed_ring_readout: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.theta) or self.theta <= 0:
            raise ValueError(f"theta must be finite and positive, got {self.theta!r}")
        if not math.isfinite(self.beta) or self.beta <= 0:
            raise ValueError(f"beta must be finite and positive, got {self.beta!r}")
        if self.sanitary_visit_mode not in SANITARY_VISIT_MODES:
            raise ValueError(
                f"sanitary_visit_mode must be one of {SANITARY_VISIT_MODES}, "
                f"got {self.sanitary_visit_mode!r}",
            )
        arm_ids = [a.get("arm_id") for a in self.arms]
        if len(arm_ids) != 2 or len(set(arm_ids)) != 2:
            raise ValueError("the vulnerability A/B declares exactly two distinct arms")
        alphas = []
        for arm in self.arms:
            alpha = arm.get("alpha")
            if not isinstance(alpha, (int, float)) or not (
                math.isfinite(float(alpha)) and float(alpha) > 0
            ):
                raise ValueError(
                    f"arm {arm.get('arm_id')!r} must declare a finite "
                    f"positive alpha, got {alpha!r}",
                )
            alphas.append(float(alpha))
        if alphas[0] == alphas[1]:
            raise ValueError("the two arms must carry distinct alpha endpoints")
        validate_leg_fields(self.legs)

    def leg(self, class_id: str) -> RhythmLeg:
        return find_leg(self.legs, class_id)

    def arm_alpha(self, arm_id: str) -> float:
        """The declared alpha endpoint one arm writes into every cell."""
        for arm in self.arms:
            if arm.get("arm_id") == arm_id:
                return float(arm["alpha"])
        raise KeyError(f"unknown arm_id {arm_id!r}")

    def susceptibility_scale(self, arm_id: str) -> float:
        """scale = Theta * (alpha + beta) / alpha, keeping E[s] = Theta."""
        alpha = self.arm_alpha(arm_id)
        return float(self.theta) * (alpha + float(self.beta)) / alpha


@dataclass(frozen=True)
class VulnCell:
    """One (class, arm, seed) the array evaluates."""

    index: int
    class_id: str
    platform_id: str
    scenario_id: str            # record id or class label
    theta: float
    infection_age_days: float
    imports: int
    seed: int
    arm_id: str
    alpha: float

    @property
    def key(self) -> str:
        alpha = f"{self.alpha:g}".replace(".", "p")
        return campaign_cell_key(
            "vuln", self.class_id, self.theta,
            self.infection_age_days, self.imports, self.seed, f"a{alpha}",
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            **campaign_cell_dict(self),
            "alpha": self.alpha,
        }


def enumerate_vuln_cells(design: VulnABDesign) -> tuple[VulnCell, ...]:
    """Every cell in a fixed order: leg, then arm, then seed."""
    return enumerate_campaign_cells(
        design, VulnCell, lambda arm: {"alpha": float(arm["alpha"])},
    )


def prepare_vuln_cell_spec(
    design: VulnABDesign,
    cell: VulnCell,
    *,
    repo_root: str,
) -> dict[str, Any]:
    """Build the run spec one cell executes, arm alpha written explicitly.

    The leg builders are the rhythm A/B's takeoff-conditioned spec
    constructors (same legs, same conditioning); the arm difference lands
    in ``pathogen_overrides`` — ``dose_response.alpha`` plus the
    Theta-preserving ``susceptibility_scale`` — while
    ``config_overrides`` pins rhythm on and the exposure cap on so the
    axis is measured on the declared exposure-set context.
    """
    raw = leg_spec(design, design.leg(cell.class_id), cell,
                   repo_root=repo_root)
    overrides = raw.setdefault("config_overrides", {})
    overrides["rhythm"] = {"enabled": True}
    overrides.setdefault("transmission", {})["exposure_cap"] = {
        "enabled": True,
    }
    dose_response = raw["pathogen_overrides"][PATHOGEN_ID].setdefault(
        "dose_response", {},
    )
    dose_response["model"] = "beta_poisson"
    dose_response["alpha"] = float(cell.alpha)
    dose_response["beta"] = float(design.beta)
    dose_response["susceptibility_scale"] = design.susceptibility_scale(
        cell.arm_id,
    )
    return raw


def load_vuln_design(path: str) -> VulnABDesign:
    """Parse the A/B design file; every criterion must already be in it."""
    raw = load_design_json(path)
    return VulnABDesign(
        design_id=str(raw["design_id"]),
        theta=float(raw["theta"]),
        beta=float(raw["beta"]),
        infection_age_days=float(raw["infection_age_days"]),
        imports=int(raw["imports"]),
        sanitary_visit_mode=str(raw["sanitary_visit_mode"]),
        takeoff_recorded_onsets=int(raw["takeoff_recorded_onsets"]),
        arms=tuple(raw["arms"]),
        legs=parse_leg_dicts(raw["legs"]),
    )
