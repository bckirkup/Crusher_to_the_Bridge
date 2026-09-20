#!/usr/bin/env python3
"""Readout for the NORO-DOSE-BLOCK-01 cells.

Aggregation only: this script reads the per-seed ``*.json.gz`` dumps written by
``per_host_dose_challenge.py`` (no ``--alpha``) and never re-runs or re-derives
a measurement. It answers the four questions frozen in
``docs/ledger/NORO-DOSE-BLOCK-01.md`` against the criteria declared there:

* **route attribution** -- each pathway's ``pathway_dose_gec`` as a share of
  the pathway total, per cell, reported as a distribution and split at the
  declared 1e-6 GEC floor below which a share is arithmetic, not attribution;
* **transfer terms** -- surface->hand as
  ``log10(surface_mass_offered / mass_delivered_to_hands)`` and hand->mouth as
  ``log10(hand_load_seen / hand_to_mouth_dose)``, from the same witnesses
  ``NORO-DOSE-01`` read on the 8105/8106 pair;
* **magnitude** -- credited scaled dose and the dose-concentration curve;
* **pair position** -- the percentile 8105 and 8106 occupy inside the 20-seed
  block, measured at one commit.

The block/pair comparison is *within one commit*. The comparison against the
``e83aa06`` block is unpaired by construction: ``REINFECT-01`` shifts the RNG
stream, so per-seed equality across the repair is not expected and its absence
is not a finding.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)

CELL_RE = re.compile(r"per_host_dose_challenge_seed(?P<seed>\d+)\.json\.gz")
PATHOGEN_ID = "norwalk_gi"
RECONCILIATION_RTOL = 1e-9
MAX_VOID_CELLS = 4
# Below this credited total a pathway share is arithmetic on a vanishing
# number, so the cell is reported apart from the attribution distribution.
SHARE_FLOOR_GEC = 1e-6
BLOCK_SEEDS = tuple(range(8000, 8020))
PAIR_SEEDS = (8105, 8106)
# The pair values NORO-DOSE-01 reported, restated here as the comparison
# targets the ledger froze; nothing is fitted to them.
DOSE01_FOMITE_SHARE = 0.935
DOSE01_SURFACE_TO_HAND_LOG10 = 2.17
DOSE01_HAND_TO_MOUTH_LOG10 = 1.93
FOMITE_SHARE_TOLERANCE = 0.10
FOMITE_SHARE_IQR_CEILING = 0.20
TRANSFER_TOLERANCE_LOG10 = 0.5
PAIR_LOW_TAIL_PERCENTILE = 25.0


def _dig(summary: dict[str, Any], dotted: str) -> Any:
    value: Any = summary
    for key in dotted.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _number(summary: dict[str, Any], dotted: str) -> float:
    value = _dig(summary, dotted)
    return float(value) if value is not None else 0.0


def accumulate_calls(summary: dict[str, Any]) -> int:
    """The pathogen's own accumulate-call count, from the per-pathogen map."""
    calls = _dig(summary, "reconciliation.accumulate_calls")
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


def _spread(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p25": _percentile_value(ordered, 25.0),
        "median": statistics.median(ordered),
        "p75": _percentile_value(ordered, 75.0),
        "max": ordered[-1],
    }


def _percentile_value(ordered: list[float], pct: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    if len(ordered) == 1:
        return ordered[0]
    position = (pct / 100.0) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _percentile_of(ordered: list[float], value: float) -> float:
    """Fraction of the block at or below ``value``, as a percentile."""
    if not ordered:
        return math.nan
    below = sum(1 for item in ordered if item <= value)
    return 100.0 * below / len(ordered)


def _pathway_shares(summary: dict[str, Any]) -> dict[str, float]:
    doses = _dig(summary, "reconciliation.pathway_dose_gec") or {}
    total = sum(float(v) for v in doses.values())
    if total <= 0.0:
        return {}
    return {k: float(v) / total for k, v in doses.items()}


def route_attribution(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 1: is fomite dominance a hull property or a pair property."""
    rows, below_floor = [], []
    for summary in cells:
        shares = _pathway_shares(summary)
        total = sum(
            float(v)
            for v in (_dig(summary, "reconciliation.pathway_dose_gec") or {}
                      ).values()
        )
        row = {"seed": summary["seed"], "pathway_total_gec": total, **shares}
        (rows if total >= SHARE_FLOOR_GEC else below_floor).append(row)
    pathways = sorted({
        key
        for row in rows
        for key in row
        if key not in {"seed", "pathway_total_gec"}
    })
    distribution = {
        pathway: _spread([float(row.get(pathway, 0.0)) for row in rows])
        for pathway in pathways
    }
    fomite = distribution.get("fomite", {"n": 0})
    confirmed = bool(
        fomite.get("n")
        and abs(fomite["median"] - DOSE01_FOMITE_SHARE) <= FOMITE_SHARE_TOLERANCE
        and (fomite["p75"] - fomite["p25"]) <= FOMITE_SHARE_IQR_CEILING,
    )
    return {
        "cells_above_floor": rows,
        "cells_below_floor": below_floor,
        "share_floor_gec": SHARE_FLOOR_GEC,
        "share_distribution": distribution,
        "dose01_pair_fomite_share": DOSE01_FOMITE_SHARE,
        "fomite_share_confirmed_as_hull_property": confirmed,
    }


def _log10_ratio(numerator: float, denominator: float) -> float | None:
    if numerator <= 0.0 or denominator <= 0.0:
        return None
    return math.log10(numerator / denominator)


def transfer_terms(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 2: the surface->hand and hand->mouth log10 losses."""
    rows = []
    for summary in cells:
        witness = summary.get("fomite_witness", {})
        rows.append({
            "seed": summary["seed"],
            "surface_to_hand_log10": _log10_ratio(
                float(witness.get("surface_mass_offered_gec", 0.0)),
                float(witness.get("mass_delivered_to_hands_gec", 0.0)),
            ),
            "hand_to_mouth_log10": _log10_ratio(
                float(witness.get("hand_load_seen_gec", 0.0)),
                float(witness.get("hand_to_mouth_dose_gec", 0.0)),
            ),
        })
    out: dict[str, Any] = {"cells": rows}
    for key, pair_value in (
        ("surface_to_hand_log10", DOSE01_SURFACE_TO_HAND_LOG10),
        ("hand_to_mouth_log10", DOSE01_HAND_TO_MOUTH_LOG10),
    ):
        values = [r[key] for r in rows if r[key] is not None]
        spread = _spread(values)
        out[key] = {
            "distribution": spread,
            "dose01_pair_value": pair_value,
            "confirmed": bool(
                spread.get("n")
                and abs(spread["median"] - pair_value)
                <= TRANSFER_TOLERANCE_LOG10,
            ),
        }
    return out


def magnitude(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 3: credited dose and how few hosts hold most of it."""
    credited = [
        _number(s, "reconciliation.sum_credited_scaled_gec") for s in cells
    ]
    hazards = [
        _number(s, "reconciliation.sum_evaluated_hazard") for s in cells
    ]
    hosts_90 = [_number(s, "concentration.hosts_for_90pct") for s in cells]
    return {
        "credited_scaled_gec": _spread(credited),
        "sum_evaluated_hazard": _spread(hazards),
        "block_sum_evaluated_hazard": sum(hazards),
        "hosts_for_90pct": _spread(hosts_90),
        "secondaries_total": sum(
            int(_number(s, "transmission.secondaries")) for s in cells
        ),
        "imports_total": sum(
            int(_number(s, "transmission.imports")) for s in cells
        ),
    }


def pair_position(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 4: where 8105/8106 sit inside the block, at one commit."""
    block = [s for s in cells if s["seed"] in BLOCK_SEEDS]
    pair = [s for s in cells if s["seed"] in PAIR_SEEDS]
    dose_ordered = sorted(
        _number(s, "reconciliation.sum_credited_scaled_gec") for s in block
    )
    hazard_ordered = sorted(
        _number(s, "reconciliation.sum_evaluated_hazard") for s in block
    )
    rows = []
    for summary in pair:
        dose = _number(summary, "reconciliation.sum_credited_scaled_gec")
        hazard = _number(summary, "reconciliation.sum_evaluated_hazard")
        rows.append({
            "seed": summary["seed"],
            "credited_scaled_gec": dose,
            "dose_percentile_in_block": _percentile_of(dose_ordered, dose),
            "sum_evaluated_hazard": hazard,
            "hazard_percentile_in_block": _percentile_of(
                hazard_ordered, hazard,
            ),
        })
    low_tail = all(
        row["dose_percentile_in_block"] <= PAIR_LOW_TAIL_PERCENTILE
        and row["hazard_percentile_in_block"] <= PAIR_LOW_TAIL_PERCENTILE
        for row in rows
    ) if rows else False
    return {
        "block_seeds_loaded": len(block),
        "pair": rows,
        "percentile_threshold": PAIR_LOW_TAIL_PERCENTILE,
        "pair_is_low_tail": low_tail,
    }


def _print_block(title: str, payload: dict[str, Any]) -> None:
    print(f"\n{title}:")
    print(json.dumps(payload, indent=1, sort_keys=True, default=str))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path,
        default=(
            REPO_ROOT / "docs/norovirus/noro_dose_block_01/classic_cruise_1900"
        ),
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_dose_block_01",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cells = load_cells(args.raw_dir)
    admissible, void = partition(cells)
    block = [s for s in admissible if s["seed"] in BLOCK_SEEDS]
    worst, gate_ok = reconciliation_gate(admissible)
    study_go = len(void) <= MAX_VOID_CELLS
    print(f"loaded {len(cells)} cells from {args.raw_dir}")
    print(f"admissible {len(admissible)}, void {len(void)} "
          f"(void seeds: {[s['seed'] for s in void]})")
    print(f"study admissibility: {'GO' if study_go else 'NO-GO'}")
    print(f"reconciliation gate (rtol {RECONCILIATION_RTOL:g}): "
          f"worst {worst:.3e} -> {'PASS' if gate_ok else 'FAIL'}")
    payload = {
        "raw_dir": str(args.raw_dir),
        "cells_loaded": len(cells),
        "void_seeds": [s["seed"] for s in void],
        "study_admissible": study_go,
        "reconciliation": {
            "rtol": RECONCILIATION_RTOL,
            "worst_relative_difference": worst,
            "verdict": "PASS" if gate_ok else "FAIL",
        },
        "route_attribution": route_attribution(block),
        "transfer_terms": transfer_terms(block),
        "magnitude": magnitude(block),
        "pair_position": pair_position(admissible),
    }
    for key in (
        "route_attribution", "transfer_terms", "magnitude", "pair_position",
    ):
        _print_block(key, payload[key])
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    path = resolve_child_path(str(out_dir), "dose_block_cells.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True, default=str)
    print(f"\nwritten: {path}")
    return 0 if gate_ok and study_go else 1


if __name__ == "__main__":
    raise SystemExit(main())
