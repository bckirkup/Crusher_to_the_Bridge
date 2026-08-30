"""Sweep sourced routine-cleaning schedules through the Park surface check.

The schedule is not fitted here. This harness reports the envelope over the
specified bounds and deliberately selects no cell for the model.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

from telemetry_buffer.observation_model.park_surface_check import (
    CABIN_LOCALIZATION_SWEEP,
    concentration_per_swab,
    emesis_inclusive_surface_values,
    expectations,
    routine_cleaning_multiplier,
    steady_state_pool,
    surface_loss_per_hour,
)

ZONE_CLASSES = ("cabin", "dining", "public", "galley", "crew_mess")
FREQUENCY_BOUNDS = {
    "cabin": (0.33, 1.0),
    "public": (1.0, 12.0),
    "dining": (1.0, 6.0),
    "galley": (1.0, 6.0),
    "crew_mess": (1.0, 6.0),
}
COVERAGE_BOUNDS = {
    "cabin": (0.336, 0.600),
    "public": (0.292, 0.454),
    "dining": (0.292, 0.600),
    "galley": (0.292, 0.600),
    "crew_mess": (0.292, 0.600),
}


def grid_values(
    bounds: tuple[float, float],
    *,
    geometric: bool = False,
) -> tuple[float, float, float]:
    """Return the fixed low/mid/high grid for one swept quantity."""
    low, high = bounds
    midpoint = math.sqrt(low * high) if geometric else (low + high) / 2.0
    return low, midpoint, high


def sweep_cells() -> list[dict[str, float]]:
    """Evaluate the 3x3x3x3 cabin/public schedule grid."""
    exp_ = expectations()
    cabin_loss = surface_loss_per_hour("cabin", 1.0, exp_)
    public_loss = surface_loss_per_hour("public", 60.0, exp_)
    cabin_bare = concentration_per_swab(
        steady_state_pool("cabin", 22.0, 1.0, exp_, cleaning=False),
        "cabin",
    )
    public_bare = concentration_per_swab(
        steady_state_pool(
            "public", 60.0, 60.0, exp_, cleaning=False,
        ),
        "public",
    )
    cells: list[dict[str, float]] = []
    for cabin_coverage, cabin_events, public_coverage, public_events in (
        itertools.product(
            grid_values(COVERAGE_BOUNDS["cabin"]),
            grid_values(FREQUENCY_BOUNDS["cabin"], geometric=True),
            grid_values(COVERAGE_BOUNDS["public"]),
            grid_values(FREQUENCY_BOUNDS["public"], geometric=True),
        )
    ):
        cabin_multiplier = routine_cleaning_multiplier(
            cabin_loss,
            coverage=cabin_coverage,
            events_per_day=cabin_events,
        )
        public_multiplier = routine_cleaning_multiplier(
            public_loss,
            coverage=public_coverage,
            events_per_day=public_events,
        )
        cabin_copies = cabin_bare * cabin_multiplier
        public_copies = public_bare * public_multiplier
        cells.append(
            {
                "cabin_coverage": cabin_coverage,
                "cabin_events_per_day": cabin_events,
                "public_coverage": public_coverage,
                "public_events_per_day": public_events,
                "cabin_multiplier": cabin_multiplier,
                "public_multiplier": public_multiplier,
                "cabin_copies_per_swab": cabin_copies,
                "public_copies_per_swab": public_copies,
                "gradient": cabin_copies / public_copies,
            },
        )
    return cells


def emesis_cells(
    fraction: float,
    cells: list[dict[str, float]] | None = None,
) -> list[dict[str, float]]:
    """Add emesis-inclusive copies and gradients for one localization value."""
    if cells is None:
        cells = sweep_cells()
    exp_ = expectations()
    results: list[dict[str, float]] = []
    for cell in cells:
        cabin_copies, public_copies, gradient = (
            emesis_inclusive_surface_values(
                fraction,
                exp_,
                {
                    "sick passenger confined to cabin": cell[
                        "cabin_copies_per_swab"
                    ],
                    "lounge, 60 shedder-hours/day": cell[
                        "public_copies_per_swab"
                    ],
                },
                cabin_cleaning_multiplier=cell["cabin_multiplier"],
                public_cleaning_multiplier=cell["public_multiplier"],
            )
        )
        results.append(
            {
                **cell,
                "emesis_cabin_copies_per_swab": cabin_copies,
                "emesis_public_copies_per_swab": public_copies,
                "emesis_gradient": gradient,
            },
        )
    return results


def _uniform_emesis_values(
    fraction: float,
    exp_: dict[str, float],
) -> tuple[float, float, float]:
    cabin_loss = surface_loss_per_hour("cabin", 1.0, exp_)
    public_loss = surface_loss_per_hour("public", 60.0, exp_)
    hand_only = {
        "sick passenger confined to cabin": concentration_per_swab(
            steady_state_pool("cabin", 22.0, 1.0, exp_, cleaning=False),
            "cabin",
        ) * routine_cleaning_multiplier(cabin_loss),
        "lounge, 60 shedder-hours/day": concentration_per_swab(
            steady_state_pool(
                "public", 60.0, 60.0, exp_, cleaning=False,
            ),
            "public",
        ) * routine_cleaning_multiplier(public_loss),
    }
    return emesis_inclusive_surface_values(fraction, exp_, hand_only)


def _render() -> str:
    cells = sweep_cells()
    exp_ = expectations()
    default_cabin_loss = surface_loss_per_hour("cabin", 1.0, exp_)
    default_public_loss = surface_loss_per_hour("public", 60.0, exp_)
    default_cabin = concentration_per_swab(
        steady_state_pool(
            "cabin", 22.0, 1.0, exp_, cleaning=False,
        ),
        "cabin",
    ) * routine_cleaning_multiplier(default_cabin_loss)
    default_public = concentration_per_swab(
        steady_state_pool(
            "public", 60.0, 60.0, exp_, cleaning=False,
        ),
        "public",
    ) * routine_cleaning_multiplier(default_public_loss)
    gradients = [cell["gradient"] for cell in cells]
    default_gradient = default_cabin / default_public
    lines = [
        "Cleaning schedule sweep through the Park surface check",
        "=" * 68,
        "The grid is fixed by the sourced bounds in "
        "cleaning_schedule_sweep_spec.md.",
        "Only cabin and public schedules affect this Park gradient: "
        f"{len(cells)} cells (3x3x3x3).",
        "",
        (
            "cabin coverage: "
            f"{grid_values(COVERAGE_BOUNDS['cabin'])}"
        ),
        (
            "cabin events/day (geometric): "
            f"{grid_values(FREQUENCY_BOUNDS['cabin'], geometric=True)}"
        ),
        (
            "public coverage: "
            f"{grid_values(COVERAGE_BOUNDS['public'])}"
        ),
        (
            "public events/day (geometric): "
            f"{grid_values(FREQUENCY_BOUNDS['public'], geometric=True)}"
        ),
        "",
        (
            "cabin cov | cabin/day | public cov | public/day | "
            "cabin x | public x | cabin copies/swab | public copies/swab | "
            "gradient"
        ),
        "-" * 150,
    ]
    for cell in cells:
        lines.append(
            f"{cell['cabin_coverage']:>9.3f} | "
            f"{cell['cabin_events_per_day']:>10.4f} | "
            f"{cell['public_coverage']:>10.3f} | "
            f"{cell['public_events_per_day']:>10.4f} | "
            f"{cell['cabin_multiplier']:>8.5f} | "
            f"{cell['public_multiplier']:>8.5f} | "
            f"{cell['cabin_copies_per_swab']:>17.6g} | "
            f"{cell['public_copies_per_swab']:>18.6g} | "
            f"{cell['gradient']:>8.5f}x"
        )
    lines.extend(
        [
            "",
            "Hand-only envelope over the sourced box:",
            "  Park already shows this channel is unreachable at any "
            "occupancy.",
            f"  minimum gradient: {min(gradients):.6g}x",
            f"  maximum gradient: {max(gradients):.6g}x",
            f"  uniform shipped default gradient: {default_gradient:.6g}x",
            (
                "  maximum/default leverage: "
                f"{max(gradients) / default_gradient:.6g}x upward"
            ),
            (
                "  default shortfall from Park's 100x lower bound: "
                f"{100.0 / default_gradient:.6g}x"
            ),
            "",
            "Emesis-inclusive envelope by unmeasured cabin-localization f:",
            "f is a separate behavioural axis, not part of the schedule grid.",
            (
                "       f | min gradient | max gradient | "
                "cells in Park 100-300x | uniform default"
            ),
            "-" * 78,
        ]
    )
    for fraction in CABIN_LOCALIZATION_SWEEP:
        emesis = emesis_cells(fraction, cells)
        emesis_gradients = [cell["emesis_gradient"] for cell in emesis]
        _, _, default_emesis_gradient = _uniform_emesis_values(
            fraction, exp_,
        )
        in_park = [
            gradient
            for gradient in emesis_gradients
            if 100.0 <= gradient <= 300.0
        ]
        lines.append(
            f"{fraction:>8.2f} | {min(emesis_gradients):>12.6g} | "
            f"{max(emesis_gradients):>12.6g} | {len(in_park):>22} | "
            f"{default_emesis_gradient:>15.6g}x"
        )
    lines.extend(
        [
            "Rule 3: the best-fitting cell is not read back into the model.",
            "The sweep selects nothing; no cell becomes a parameter value.",
            "The f-axis is also unmeasured and must not be read from Park.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    report = _render()
    print(report, end="")
    output = Path(__file__).with_name("cleaning_schedule_sweep_out.txt")
    output.write_text(report, encoding="utf-8")
    print(f"written: {output}")


if __name__ == "__main__":
    main()
