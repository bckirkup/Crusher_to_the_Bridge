"""Path-safe visit-table records for Sentinel design diagnostics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from picard_framework.analysis._io import (
    allowed_roots,
    read_json,
    safe_path,
    write_json,
)
from simulation_utils.paths import validated_open


@dataclass(frozen=True)
class PortVisit:
    """One ship's call at one port in one calendar week."""

    ship_id: str
    port_id: str
    week: str
    person_hours_ashore: float

    def __post_init__(self) -> None:
        if self.person_hours_ashore < 0.0:
            raise ValueError(
                f"negative person_hours_ashore for {self.port_id}@{self.week}",
            )


def visits_from_records(records: Iterable[Mapping[str, Any]]) -> tuple[PortVisit, ...]:
    """Build visits from decoded records, tolerating the sentinel meta shape."""
    visits: list[PortVisit] = []
    for raw in records:
        missing = [k for k in ("port_id", "week") if raw.get(k) in (None, "")]
        if missing:
            raise ValueError(f"visit record missing {missing}: {dict(raw)}")
        visits.append(
            PortVisit(
                ship_id=str(raw.get("ship_id") or "pooled"),
                port_id=str(raw["port_id"]),
                week=str(raw["week"]),
                person_hours_ashore=float(raw.get("person_hours_ashore") or 0.0),
            ),
        )
    if not visits:
        raise ValueError("visit table is empty")
    return tuple(visits)


def _records_from_json(path: str) -> list[Mapping[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, dict):
        records = payload.get("visits")
        if isinstance(records, list):
            return list(records)
    raise ValueError(f"expected a visit list or a 'visits' key: {path}")


def _records_from_csv(path: str) -> list[Mapping[str, Any]]:
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8", newline="",
    ) as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"visit CSV has no rows: {path}")
    return rows


def load_visit_table(path: str) -> tuple[PortVisit, ...]:
    """Load a visit table from JSON (list or ``{"visits": [...]}``) or CSV."""
    resolved = safe_path(path)
    records = (
        _records_from_csv(resolved)
        if resolved.lower().endswith(".csv")
        else _records_from_json(resolved)
    )
    return visits_from_records(records)


def write_visit_table(path: str, visits: Sequence[PortVisit]) -> str:
    """Write a visit table as JSON so a generated design can be re-diagnosed."""
    payload = {
        "schema_version": "1.0.0",
        "visits": [
            {
                "ship_id": v.ship_id,
                "port_id": v.port_id,
                "week": v.week,
                "person_hours_ashore": round(v.person_hours_ashore, 6),
            }
            for v in visits
        ],
    }
    target = safe_path(path)
    write_json(target, payload)
    return target
