"""Axis labels and tick formats with explicit natural units."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AxisSpec:
    title: str
    tickformat: str | None = None
    hovertemplate: str | None = None


# Registry of quantity keys → axis metadata
_AXIS_REGISTRY: dict[str, AxisSpec] = {
    "time_epoch": AxisSpec("Epoch (24 h)"),
    "time_voyage_day": AxisSpec("Voyage day"),
    "persons": AxisSpec("Persons"),
    "attack_rate": AxisSpec("Attack rate (fraction)", tickformat=".1%"),
    "aerosol_mass": AxisSpec("Aerosol mass (relative units)"),
    "aerosol_concentration": AxisSpec("Concentration (ng/m³)"),
    "surface_mass": AxisSpec("Surface mass (relative units)"),
    "usd": AxisSpec("USD"),
    "ois": AxisSpec("Operational impact score (dimensionless)"),
    "length_m": AxisSpec("Length (m)"),
    "beam_m": AxisSpec("Beam (m)"),
    "deck_stack": AxisSpec("Deck stack (keel → top)"),
    "dose": AxisSpec("Infectious dose (model units)"),
    "epoch_delay": AxisSpec("Epoch delay"),
    "hours_since_order": AxisSpec("Hours since order"),
    "fluorescence": AxisSpec("Fluorescence (RFU)"),
    "read_counts": AxisSpec("Read counts"),
    "cycle": AxisSpec("Cycle"),
    "sample": AxisSpec("Sample"),
    "new_agents": AxisSpec("New agents"),
    "active_infections": AxisSpec("Active infections"),
    "active_cases": AxisSpec("Active cases (persons)"),
    "cruise": AxisSpec("Cruise"),
}


def axis(quantity: str) -> AxisSpec:
    """Return axis metadata for a registered quantity key."""
    return _AXIS_REGISTRY.get(quantity, AxisSpec(quantity.replace("_", " ").title()))


def time_xaxis_title(history: list[dict[str, Any]]) -> str:
    """Prefer voyage day when voyage_epoch is present in telemetry."""
    if history and any(rec.get("voyage_epoch", {}).get("voyage_day") is not None for rec in history):
        return axis("time_voyage_day").title
    return axis("time_epoch").title


def time_x_values(history: list[dict[str, Any]]) -> list[int | float]:
    """X-axis values for time series: voyage day when available, else epoch."""
    if history and any(rec.get("voyage_epoch", {}).get("voyage_day") is not None for rec in history):
        return [
            rec.get("voyage_epoch", {}).get("voyage_day", rec["epoch"])
            for rec in history
        ]
    return [rec["epoch"] for rec in history]


def apply_axis(fig: Any, *, x: str | None = None, y: str | None = None) -> None:
    """Apply registered axis titles and tick formats to a Plotly figure."""
    if x:
        spec = axis(x)
        fig.update_xaxes(title_text=spec.title, tickformat=spec.tickformat)
    if y:
        spec = axis(y)
        fig.update_yaxes(title_text=spec.title, tickformat=spec.tickformat)
