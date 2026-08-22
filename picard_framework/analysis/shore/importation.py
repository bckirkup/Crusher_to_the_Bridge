"""The narrow, serializable interface from a ship port call to shore.

The shore model intentionally knows nothing about agents, cabins, ship
protocols, or genotype mechanics.  A port call supplies infectious
disembarkations on a shared epoch grid and opaque Phase 1 strain labels.  The
labels are propagated, not evolved: a per-strain shore parameter set is a
future seam, not a knob in this model.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

import numpy as np


def _normalise_series(
    raw: Mapping[str, tuple[float, ...]],
) -> dict[str, tuple[float, ...]]:
    """Copy and validate strain-labelled importation series."""
    normalised: dict[str, tuple[float, ...]] = {}
    lengths: set[int] = set()
    for label, values in raw.items():
        key = str(label)
        if not key:
            raise ValueError("strain labels must be non-empty")
        series = tuple(float(value) for value in values)
        if any(value < 0.0 or not isfinite(value) for value in series):
            raise ValueError(f"importations for {key!r} must be finite and non-negative")
        normalised[key] = series
        lengths.add(len(series))
    if len(lengths) > 1:
        raise ValueError("all strain importation series must have equal length")
    return normalised


@dataclass(frozen=True)
class PortCallImportation:
    """Infectious disembarkations for one port call and one pathogen.

    An empty strain map and a zero-length horizon are legal.  This is useful
    for campaigns whose port-call records contain no infectious exporters.
    Strain labels remain opaque strings from ``engines/strain_state.py``.
    """

    port_id: str
    pathogen_id: str
    epoch_hours: float
    strain_importations: Mapping[str, tuple[float, ...]]
    ship_detection_epoch: int | None

    def __post_init__(self) -> None:
        if not str(self.port_id):
            raise ValueError("port_id must be non-empty")
        if not str(self.pathogen_id):
            raise ValueError("pathogen_id must be non-empty")
        if self.epoch_hours <= 0.0 or not isfinite(float(self.epoch_hours)):
            raise ValueError("epoch_hours must be positive and finite")
        if self.ship_detection_epoch is not None:
            if int(self.ship_detection_epoch) != self.ship_detection_epoch:
                raise ValueError("ship_detection_epoch must be an integer")
            if self.ship_detection_epoch < 0:
                raise ValueError("ship_detection_epoch must be >= 0")
        normalised = _normalise_series(self.strain_importations)
        object.__setattr__(self, "port_id", str(self.port_id))
        object.__setattr__(self, "pathogen_id", str(self.pathogen_id))
        object.__setattr__(self, "epoch_hours", float(self.epoch_hours))
        object.__setattr__(self, "strain_importations", normalised)
        if self.ship_detection_epoch is not None:
            object.__setattr__(self, "ship_detection_epoch", int(self.ship_detection_epoch))

    @property
    def total_importations(self) -> float:
        """Total infectious disembarkations across strains and epochs."""
        return float(sum(sum(values) for values in self.strain_importations.values()))

    @property
    def total_by_strain(self) -> dict[str, float]:
        """Imported infectious disembarkations by opaque strain label."""
        return {label: float(sum(values)) for label, values in self.strain_importations.items()}

    @property
    def horizon(self) -> int:
        """Common number of shore epochs."""
        return len(next(iter(self.strain_importations.values()), ()))

    def combined(self) -> np.ndarray:
        """Return the strain-summed importation vector."""
        combined = np.zeros(self.horizon, dtype=float)
        for values in self.strain_importations.values():
            combined += np.asarray(values, dtype=float)
        return combined

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "port_id": self.port_id,
            "pathogen_id": self.pathogen_id,
            "epoch_hours": self.epoch_hours,
            "strain_importations": {
                label: list(values) for label, values in self.strain_importations.items()
            },
            "ship_detection_epoch": self.ship_detection_epoch,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> PortCallImportation:
        """Rebuild an importation record from ``as_dict`` output."""
        return cls(
            port_id=str(raw["port_id"]),
            pathogen_id=str(raw["pathogen_id"]),
            epoch_hours=float(raw["epoch_hours"]),
            strain_importations={
                str(label): tuple(float(value) for value in values)
                for label, values in dict(raw.get("strain_importations") or {}).items()
            },
            ship_detection_epoch=(
                None
                if raw.get("ship_detection_epoch") is None
                else int(raw["ship_detection_epoch"])
            ),
        )
