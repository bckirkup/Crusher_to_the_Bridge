"""Read a sentinel fit directory back into memory.

The fit runners write CSV and JSON and then exit; figures and the report are
built from those files rather than from the posterior. That is deliberate: a fit
is expensive and a plot is not, so ``run_sentinel --from-fit`` can redraw a
report from a fit produced weeks earlier, on a machine with no CmdStan, and the
report can never disagree with the CSV a reader was handed.

A fleet fit and a single-ship fit write different files (``fleet_port_hazards``
vs ``port_hazards``, and only the fleet has visits, weeks, and crew), so the
loader reports which mode it found instead of guessing per-file.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Any

from picard_framework.analysis._io import allowed_roots, read_json, safe_path
from simulation_utils.paths import validated_open

MODE_FLEET = "fleet"
MODE_SINGLE = "single_ship"

_FLEET_HAZARDS_CSV = "fleet_port_hazards.csv"
_SINGLE_HAZARDS_CSV = "port_hazards.csv"
_VISIT_HAZARDS_CSV = "visit_hazards.csv"
_FLEET_TIME_CSV = "fleet_time.csv"


@dataclass(frozen=True)
class SentinelArtifacts:
    """Everything a fit directory holds, in the shapes figures and report need."""

    fit_dir: str
    mode: str
    status: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    port_rows: list[dict[str, Any]] = field(default_factory=list)
    visit_rows: list[dict[str, Any]] = field(default_factory=list)
    week_rows: list[dict[str, Any]] = field(default_factory=list)
    onboard: dict[str, Any] = field(default_factory=dict)
    crew: dict[str, Any] = field(default_factory=dict)
    wastewater: dict[str, Any] = field(default_factory=dict)

    @property
    def pathogen(self) -> str:
        return str(self.meta.get("pathogen") or "unknown")

    @property
    def engine(self) -> str:
        """Sampler that produced the draws, or why there are none."""
        return str(self.status.get("engine") or self.status.get("status") or "unknown")

    @property
    def is_reference_walker(self) -> bool:
        """True when the intervals came from the numpy walker, not NUTS."""
        return self.engine in {"numpy_rw_mh", "smoke"}


def read_csv_rows(path: str) -> list[dict[str, Any]]:
    """Rows of a CSV written by the fit runners, values left as strings."""
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8", newline="",
    ) as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def as_float(value: Any, default: float = float("nan")) -> float:
    """``float(value)`` for a CSV cell, with blanks reported as ``default``."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    """CSV round-trips booleans as text; ``bool('False')`` is True, so parse."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _optional_json(fit_dir: str, name: str) -> dict[str, Any]:
    path = os.path.join(fit_dir, name)
    if not os.path.isfile(path):
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _optional_csv(fit_dir: str, name: str) -> list[dict[str, Any]]:
    path = os.path.join(fit_dir, name)
    return read_csv_rows(path) if os.path.isfile(path) else []


def load_fit_artifacts(fit_dir: str) -> SentinelArtifacts:
    """Load a fit directory, refusing one that holds no hazard table.

    A fit that was skipped (no CmdStan) or errored writes ``fit_status.json`` and
    no hazards. Reporting on that as if it were a fit is the failure mode this
    raise exists to prevent — the caller should surface the status instead.
    """
    resolved = safe_path(fit_dir)
    if not os.path.isdir(resolved):
        raise SystemExit(f"Not a fit directory: {fit_dir}")

    fleet_rows = _optional_csv(resolved, _FLEET_HAZARDS_CSV)
    single_rows = _optional_csv(resolved, _SINGLE_HAZARDS_CSV)
    if not fleet_rows and not single_rows:
        status = _optional_json(resolved, "fit_status.json")
        reason = status.get("reason") or "no hazard table was written"
        raise SystemExit(
            f"{fit_dir} holds no port hazards to report on "
            f"(status {status.get('status', 'missing')!r}: {reason})",
        )

    mode = MODE_FLEET if fleet_rows else MODE_SINGLE
    return SentinelArtifacts(
        fit_dir=resolved,
        mode=mode,
        status=_optional_json(resolved, "fit_status.json"),
        meta=_optional_json(resolved, "stan_data_meta.json"),
        port_rows=fleet_rows or single_rows,
        visit_rows=_optional_csv(resolved, _VISIT_HAZARDS_CSV),
        week_rows=_optional_csv(resolved, _FLEET_TIME_CSV),
        onboard=_optional_json(resolved, "onboard_summary.json"),
        crew=_optional_json(resolved, "crew_exposure.json"),
        wastewater=_optional_json(resolved, "wastewater_channel.json"),
    )
