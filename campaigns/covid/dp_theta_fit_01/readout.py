#!/usr/bin/env python3
"""DP-THETA-FIT-01 readout: the frozen covid.T3 selector over theta.

Applies the criteria frozen in ``docs/covid/covid_dp_theta_fit_01_design.md``
to the cell artifacts of ``campaigns/covid/dp_theta_fit_01``. Thresholds are
constants of this module and mirror the design doc; changing one after a
cell ran is a criterion change, not a readout fix.

Usage:
    aws s3 sync s3://<bucket>/campaign/covid_dp_theta_fit_01/ out/dpfit/
    scripts/campaign readout covid/dp_theta_fit_01 -- --cells-dir out/dpfit \
        --out docs/covid/dp_theta_fit_01_readout.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DESIGN = _REPO_ROOT / "picard_framework/runs/covid_dp_theta_fit_01_design.json"
_ARM = "replay_niid"

# Frozen thresholds (design doc, "Frozen criteria").
_SIDE_SEEDS = 18          # seeds on one side of the target that exclude a theta
_DEAD_SEEDS = 20          # seeds with zero scored positives that mark a dead cell
_SATURATION_FRACTION = 0.95
_BIMODAL_BAND = (0.5, 2.0)  # multiples of the target
_BIMODAL_MIN_SEEDS = 6
_ACTIVATION_EPOCH = 391
_ONSET_DAY = 3.0
_ALPHA, _BETA = 0.18, 58.0


def _load_cells(cells_dir: Path) -> dict[float, dict[int, dict[str, Any]]]:
    """Every ``cell_<seed>.json`` under ``cells_dir``, keyed theta -> seed."""
    cells: dict[float, dict[int, dict[str, Any]]] = {}
    for path in sorted(cells_dir.rglob("cell_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        block = payload.get("dp_theta_fit") or {}
        if block.get("arm_id") != _ARM or block.get("smoke_num_epochs") is not None:
            continue
        by_seed = cells.setdefault(float(block["theta"]), {})
        if int(block["seed"]) in by_seed:
            raise SystemExit(f"duplicate cell for {path}")
        by_seed[int(block["seed"])] = payload
    return cells


def _audit_cell(cell: dict[str, Any], theta: float, through_day: int) -> list[str]:
    """Audit-invariant deviations of one cell (empty list = clean)."""
    t3 = cell["dp_theta_fit"]["t3"]
    witness = cell.get("quarantine_witness") or {}
    fidelity = cell.get("platform_fidelity") or {}
    scale = (cell.get("dose_response") or {}).get("susceptibility_scale")
    checks = {
        "platform": fidelity.get("resolved_platform_id") == "diamond_princess",
        "index_onset_day": cell.get("index_onset_day") == _ONSET_DAY,
        "susceptibility_scale": scale is not None and math.isclose(
            scale, theta * (_ALPHA + _BETA) / _ALPHA, rel_tol=1e-9,
        ),
        "quarantine_activation": (
            bool(witness.get("activated"))
            and witness.get("activation_epoch") == _ACTIVATION_EPOCH
        ),
        "close_zones": not fidelity.get("close_zones_fired_flag"),
        "testing_ran": t3["specimens_through_day"] > 0,
        "no_post_window_specimens": (
            t3["last_specimen_day"] is not None
            and t3["last_specimen_day"] <= through_day
            and not t3["specimens_by_wave"]
        ),
        "observable_agrees": (
            t3["positives_through_day"]
            == cell["observables"]["campaign_positives"]
        ),
    }
    return sorted(name for name, ok in checks.items() if not ok)


def _theta_row(
    theta: float, by_seed: dict[int, dict[str, Any]], target: dict[str, Any],
) -> dict[str, Any]:
    """Per-theta summary: the scored statistic, edge flags, reported-only."""
    positives_target = int(target["cumulative_positives"])
    through_day = int(target["through_day_index"])
    seeds = sorted(by_seed)
    positives = [
        by_seed[s]["dp_theta_fit"]["t3"]["positives_through_day"] for s in seeds
    ]
    secondaries = [by_seed[s]["infections_total"] - 1 for s in seeds]
    aboard = by_seed[seeds[0]]["aboard_total"]
    above = sum(1 for p in positives if p > positives_target)
    below = sum(1 for p in positives if p < positives_target)
    side = "compatible"
    if above >= _SIDE_SEEDS:
        side = "above"
    elif below >= _SIDE_SEEDS:
        side = "below"
    low, high = (positives_target * f for f in _BIMODAL_BAND)
    audits = {
        str(s): found for s in seeds
        if (found := _audit_cell(by_seed[s], theta, through_day))
    }
    return {
        "theta": theta,
        "n": len(seeds),
        "median_positives": statistics.median(positives),
        "seeds_above_target": above,
        "seeds_below_target": below,
        "side": side,
        "dead": sum(1 for p in positives if p == 0) >= _DEAD_SEEDS,
        "saturated": (
            statistics.median(secondaries) >= _SATURATION_FRACTION * (aboard - 1)
        ),
        "seeds_in_band": sum(1 for p in positives if low <= p <= high),
        "audit_deviations": audits,
        "reported_only": {
            "positives_per_seed": dict(zip(map(str, seeds), positives)),
            "secondaries_per_seed": dict(zip(map(str, seeds), secondaries)),
            "extinct_seeds": sum(1 for s in secondaries if s == 0),
            "median_secondaries": statistics.median(secondaries),
            "median_attack_rate": statistics.median(
                by_seed[s]["attack_rate"] for s in seeds
            ),
            "median_specimens": statistics.median(
                by_seed[s]["dp_theta_fit"]["t3"]["specimens_through_day"]
                for s in seeds
            ),
            "median_recorded_onsets": statistics.median(
                by_seed[s]["observables"]["recorded_onsets"] for s in seeds
            ),
            "median_lab_confirmed_total": statistics.median(
                by_seed[s]["lab_confirmed_total"] for s in seeds
            ),
            "median_infections_before_quarantine": statistics.median(
                by_seed[s]["infections_before_quarantine"] for s in seeds
            ),
        },
    }


def _bracket(rows: list[dict[str, Any]], positives_target: int) -> dict[str, Any] | None:
    """Lowest adjacent pair whose medians straddle the target, interpolated."""
    for lower, upper in zip(rows, rows[1:]):
        m_lo, m_hi = lower["median_positives"], upper["median_positives"]
        if m_lo < positives_target <= m_hi:
            fraction = (positives_target - m_lo) / (m_hi - m_lo)
            log_theta = math.log10(lower["theta"]) + fraction * (
                math.log10(upper["theta"]) - math.log10(lower["theta"])
            )
            return {
                "theta_lo": lower["theta"],
                "theta_hi": upper["theta"],
                "theta_star_interpolated": 10 ** log_theta,
            }
    return None


def _selection(rows: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    """The frozen selector over complete rows."""
    positives_target = int(target["cumulative_positives"])
    medians = [row["median_positives"] for row in rows]
    compatible = [
        row for row in rows
        if row["side"] == "compatible" and not row["dead"] and not row["saturated"]
    ]
    selected = min(
        compatible,
        key=lambda row: (abs(row["median_positives"] - positives_target), row["theta"]),
        default=None,
    )
    return {
        "bracket": _bracket(rows, positives_target),
        "monotone_medians": medians == sorted(medians),
        "compatible_thetas": [row["theta"] for row in compatible],
        "selected_theta": None if selected is None else selected["theta"],
        "selected_median_not_representative": (
            None if selected is None
            else selected["seeds_in_band"] < _BIMODAL_MIN_SEEDS
        ),
        "dead_thetas": [row["theta"] for row in rows if row["dead"]],
        "saturated_thetas": [row["theta"] for row in rows if row["saturated"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-dir", required=True,
                        help="local directory holding the synced cell artifacts")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    design = json.loads(_DESIGN.read_text(encoding="utf-8"))
    target = design["fit_target"]
    expected = int(design["seeds"])
    cells = _load_cells(Path(args.cells_dir))
    rows = [_theta_row(theta, cells[theta], target) for theta in sorted(cells)]
    complete = [row for row in rows if row["n"] == expected]
    readout = {
        "task_id": "DP-THETA-FIT-01",
        "design_id": design["design_id"],
        "target": target,
        "declared_thetas": design["thetas"],
        "complete_thetas": [row["theta"] for row in complete],
        "incomplete_thetas": {
            str(row["theta"]): row["n"] for row in rows if row["n"] != expected
        },
        "selection": (
            _selection(complete, target)
            if len(complete) == len(design["thetas"]) else None
        ),
        "rows": rows,
    }
    text = json.dumps(readout, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"WROTE {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
