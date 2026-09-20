#!/usr/bin/env python3
"""Shared loading and gate helpers for the ``per_host_dose_challenge`` dumps.

Aggregation only: nothing here re-runs or re-derives a measurement. Every
norovirus readout that reads a block of per-seed ``*.json.gz`` cells needs the
same four things — read the dumps, split void from admissible on the
pathogen's own accumulate-call count, check the three dose sums reconcile, and
print a labelled JSON block — so they live here rather than once per study.
"""

from __future__ import annotations

import gzip
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

CELL_RE = re.compile(r"per_host_dose_challenge_seed(?P<seed>\d+)\.json\.gz")
PATHOGEN_ID = "norwalk_gi"
RECONCILIATION_RTOL = 1e-9
MAX_VOID_CELLS = 4


def dig(summary: dict[str, Any], dotted: str) -> Any:
    """Follow a dotted path through the dump, ``None`` if any hop is absent."""
    value: Any = summary
    for key in dotted.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def number(summary: dict[str, Any], dotted: str) -> float:
    """``dig`` as a float, with an absent value read as zero."""
    value = dig(summary, dotted)
    return float(value) if value is not None else 0.0


def accumulate_calls(summary: dict[str, Any]) -> int:
    """The pathogen's own accumulate-call count, from the per-pathogen map."""
    calls = dig(summary, "reconciliation.accumulate_calls")
    if isinstance(calls, dict):
        return int(calls.get(PATHOGEN_ID, 0) or 0)
    return int(calls or 0)


def load_cells(raw_dir: Path) -> list[dict[str, Any]]:
    """Load every per-seed dump in the directory, ordered by seed."""
    cells = []
    for path in sorted(raw_dir.glob("per_host_dose_challenge_seed*.json.gz")):
        if CELL_RE.fullmatch(path.name) is None:
            continue
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            cells.append(json.load(handle))
    return sorted(cells, key=lambda s: s["seed"])


def partition(cells: list[dict[str, Any]]) -> tuple[list, list]:
    """Split the cells into admissible and void, by the declared rule."""
    admissible, void = [], []
    for summary in cells:
        (void if accumulate_calls(summary) <= 0 else admissible).append(summary)
    return admissible, void


def reconciliation_gate(cells: list[dict[str, Any]]) -> tuple[float, bool]:
    """The frozen gate: the three dose sums agree to <= 1e-9 relative."""
    worst = 0.0
    for summary in cells:
        chain = summary["reconciliation"]
        credited = float(chain["sum_credited_scaled_gec"])
        for key in (
            "sum_dose_read_at_challenge_gec",
            "sum_effective_dose_evaluated_gec",
        ):
            diff = abs(float(chain[key]) - credited)
            worst = max(worst, diff / credited if credited else math.inf)
    return worst, worst <= RECONCILIATION_RTOL


def percentile_value(ordered: list[float], pct: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    if len(ordered) == 1:
        return ordered[0]
    position = (pct / 100.0) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def spread(values: list[float], *, quartiles: bool = False) -> dict[str, float]:
    """Min/median/max of a sample, with the quartiles when asked for."""
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    out: dict[str, float] = {
        "n": len(ordered),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "max": ordered[-1],
    }
    if quartiles:
        out["p25"] = percentile_value(ordered, 25.0)
        out["p75"] = percentile_value(ordered, 75.0)
    else:
        out["mean"] = statistics.fmean(ordered)
    return out


def print_block(title: str, payload: dict[str, Any]) -> None:
    """Print one labelled JSON section of a readout."""
    print(f"\n{title}:")
    print(json.dumps(payload, indent=1, sort_keys=True, default=str))


def gate_report(
    cells: list[dict[str, Any]],
    admissible: list[dict[str, Any]],
    void: list[dict[str, Any]],
    raw_dir: Path,
) -> tuple[dict[str, Any], bool]:
    """Print the admissibility and reconciliation gates, and record them."""
    worst, gate_ok = reconciliation_gate(admissible)
    study_go = len(void) <= MAX_VOID_CELLS
    print(f"loaded {len(cells)} cells from {raw_dir}")
    print(f"admissible {len(admissible)}, void {len(void)} "
          f"(void seeds: {[s['seed'] for s in void]})")
    print(f"study admissibility: {'GO' if study_go else 'NO-GO'} "
          f"(void ceiling {MAX_VOID_CELLS})")
    print(f"reconciliation gate (rtol {RECONCILIATION_RTOL:g}): "
          f"worst {worst:.3e} -> {'PASS' if gate_ok else 'FAIL'}")
    payload = {
        "raw_dir": str(raw_dir),
        "cells_loaded": len(cells),
        "void_seeds": [s["seed"] for s in void],
        "study_admissible": study_go,
        "reconciliation": {
            "rtol": RECONCILIATION_RTOL,
            "worst_relative_difference": worst,
            "verdict": "PASS" if gate_ok else "FAIL",
        },
    }
    return payload, gate_ok and study_go
