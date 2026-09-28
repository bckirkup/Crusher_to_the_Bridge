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

import json
import math
import os
from dataclasses import dataclass
from typing import Any

from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    SANITARY_VISIT_MODES,
    VOYAGE_MODE_DECLARED,
    VOYAGE_MODES,
)
from picard_framework.covid_rhythm_cells import (
    SOP017_WINDOW,
    RhythmLeg,
    _generic_leg_spec,
    _scenario_leg_spec,
)
from simulation_utils.paths import validated_open

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
        class_ids = [leg.class_id for leg in self.legs]
        if len(set(class_ids)) != len(class_ids):
            raise ValueError("leg class_ids must be distinct")
        for leg in self.legs:
            if leg.voyage_mode not in VOYAGE_MODES:
                raise ValueError(
                    f"leg {leg.class_id!r} voyage_mode must be one of "
                    f"{VOYAGE_MODES}, got {leg.voyage_mode!r}",
                )
            if leg.kind not in ("scenario", "generic"):
                raise ValueError(
                    f"leg {leg.class_id!r} kind must be 'scenario' or "
                    f"'generic', got {leg.kind!r}",
                )
            if leg.kind == "scenario" and not leg.scenario_id:
                raise ValueError(
                    f"scenario leg {leg.class_id!r} needs a scenario_id",
                )
            if leg.kind == "generic" and leg.passengers < 1:
                raise ValueError(
                    f"generic leg {leg.class_id!r} needs a passenger count",
                )

    def leg(self, class_id: str) -> RhythmLeg:
        for leg in self.legs:
            if leg.class_id == class_id:
                return leg
        raise KeyError(f"unknown class_id {class_id!r}")

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
        exponent = f"{math.log10(self.theta):.2f}".replace(".", "p")
        age = f"{self.infection_age_days:g}".replace(".", "p")
        alpha = f"{self.alpha:g}".replace(".", "p")
        return (
            f"vuln_{self.class_id}_theta1e{exponent}_age{age}d"
            f"_imports{self.imports}_seed{self.seed}_a{alpha}.json"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "class_id": self.class_id,
            "platform_id": self.platform_id,
            "scenario_id": self.scenario_id,
            "theta": self.theta,
            "infection_age_days": self.infection_age_days,
            "imports": self.imports,
            "seed": self.seed,
            "arm_id": self.arm_id,
            "alpha": self.alpha,
            "key": self.key,
        }


def enumerate_vuln_cells(design: VulnABDesign) -> tuple[VulnCell, ...]:
    """Every cell in a fixed order: leg, then arm, then seed."""
    cells: list[VulnCell] = []
    for leg in design.legs:
        for arm in design.arms:
            for seed in leg.seed_values:
                cells.append(VulnCell(
                    index=len(cells),
                    class_id=leg.class_id,
                    platform_id=leg.platform_id,
                    scenario_id=leg.label,
                    theta=float(design.theta),
                    infection_age_days=float(design.infection_age_days),
                    imports=int(design.imports),
                    seed=int(seed),
                    arm_id=str(arm["arm_id"]),
                    alpha=float(arm["alpha"]),
                ))
    return tuple(cells)


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
    leg = design.leg(cell.class_id)
    if leg.kind == "scenario":
        raw = _scenario_leg_spec(design, leg, cell, repo_root=repo_root)
    else:
        raw = _generic_leg_spec(design, leg, cell, repo_root=repo_root)
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
    with validated_open(
        path, allowed_roots=(os.path.dirname(path) or ".",), encoding="utf-8",
    ) as handle:
        raw = json.load(handle)
    legs = tuple(
        RhythmLeg(
            class_id=str(leg["class_id"]),
            platform_id=str(leg["platform_id"]),
            kind=str(leg["kind"]),
            seed_base=int(leg["seed_base"]),
            seeds=int(leg["seeds"]),
            scenario_id=leg.get("scenario_id"),
            passengers=int(leg.get("passengers") or 0),
            crew=int(leg.get("crew") or 0),
            duration_days=int(leg.get("duration_days") or 32),
            sop017_window=tuple(
                leg.get("sop017_window") or SOP017_WINDOW
            ),
            voyage_mode=str(leg.get("voyage_mode") or VOYAGE_MODE_DECLARED),
        )
        for leg in raw["legs"]
    )
    return VulnABDesign(
        design_id=str(raw["design_id"]),
        theta=float(raw["theta"]),
        beta=float(raw["beta"]),
        infection_age_days=float(raw["infection_age_days"]),
        imports=int(raw["imports"]),
        sanitary_visit_mode=str(raw["sanitary_visit_mode"]),
        takeoff_recorded_onsets=int(raw["takeoff_recorded_onsets"]),
        arms=tuple(raw["arms"]),
        legs=legs,
    )
