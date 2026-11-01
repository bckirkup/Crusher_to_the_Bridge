#!/usr/bin/env python3
"""Score the A0-vs-A2 pool-transport contrast at HEAD across engine lanes.

Reads the per-seed payloads written by
``tools/covid_attribution_arm_smoke.py --theta 1e9 --num-epochs 0
--arms A0_declared A2_pool_transport_off --transport-engine <lane>`` for
each lane directory given, then applies the design's frozen attribution
criterion (``covid_quarantine_attribution_v1_design.json``) to the arm
contrast *within* each lane: takeoff is ``recorded_onsets >= 10``,
(i) is the all-seed median of ``infections_during_quarantine``, (ii) the
median over seeds that took off in BOTH arms. A channel is load-bearing
when (ii) falls >= 50% AND (i) also falls; non-load-bearing below 20%
shift; indeterminate between.

Per-lane rows are also joined against the settled QUAR-ATTR-V2 surface
(commit d62f10d) so the HEAD contrast reads against the recorded -66%.

Usage:
    python3 tools/covid_quar_head_contrast.py \
        --lane native=results/quar_head/native \
        --lane contamx=results/quar_head/contamx \
        --out-csv docs/covid/covid_quar_contrast_head_surface.csv \
        --out-json results/quar_head/contrast_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.covid_quar_attr_contamx_compare import (  # noqa: E402
    PROBE_EXTRA_COLUMNS,
    SURFACE_COLUMNS,
    _lane_rows,
    _load_settled_rows,
    _median,
)

ATTRIBUTION_DESIGN_REL = (
    "picard_framework/runs/covid_quarantine_attribution_v1_design.json"
)
SETTLED_SURFACE_REL = "docs/covid/covid_quarantine_attribution_v2_surface.csv"
ARMS = ("A0_declared", "A2_pool_transport_off")
TAKEOFF_ONSETS = 10  # design.takeoff_recorded_onsets


def _takeoffs(rows: dict[int, dict]) -> set[int]:
    return {
        s for s, r in rows.items()
        if r.get("recorded_onsets") is not None
        and float(r["recorded_onsets"]) >= TAKEOFF_ONSETS
    }


def _all_seed_median(rows: dict[int, dict]) -> float | None:
    return _median([
        float(r["infections_during_quarantine"])
        for r in rows.values()
        if r.get("infections_during_quarantine") is not None
    ])


def _arm_contrast(a0: dict[int, dict], arm: dict[int, dict]) -> dict:
    """The frozen criterion applied to (A0, A2) rows of one lane."""
    both = sorted(_takeoffs(a0) & _takeoffs(arm))
    all_a0 = _all_seed_median(a0)
    all_arm = _all_seed_median(arm)
    result = {
        "takeoff_a0": f"{len(_takeoffs(a0))}/{len(a0)}",
        "takeoff_arm": f"{len(_takeoffs(arm))}/{len(arm)}",
        "n_both": len(both),
        "shared_takeoff_seeds": both,
        "all_seed_median": {"a0": all_a0, "arm": all_arm},
    }
    if not both:
        result["band"] = "not eligible (no takeoff overlap)"
        return result
    med_a0 = _median([float(a0[s]["infections_during_quarantine"])
                      for s in both])
    med_arm = _median([float(arm[s]["infections_during_quarantine"])
                       for s in both])
    result["med_ii_a0"] = med_a0
    result["med_ii_arm"] = med_arm
    if not med_a0:
        result["band"] = "not eligible (A0 conditional median 0)"
        return result
    shift = (med_arm - med_a0) / med_a0
    result["shift"] = shift
    if shift <= -0.5 and (all_arm or 0) < (all_a0 or 0):
        result["band"] = "load_bearing"
    elif abs(shift) < 0.2:
        result["band"] = "non_load_bearing_shift"
    else:
        result["band"] = "indeterminate"
    return result


def _lane_contrast(lane_dir: Path, cells_by_arm: dict[str, list]) -> dict:
    lanes = {
        arm: _lane_rows(str(lane_dir), cells)
        for arm, cells in cells_by_arm.items()
    }
    seeds = {
        arm: sorted(rows) for arm, rows in lanes.items()
    }
    contrast = _arm_contrast(lanes["A0_declared"], lanes["A2_pool_transport_off"])
    engines = {
        arm: sorted({
            str(r.get("engine_class")) for r in rows.values()
        })
        for arm, rows in lanes.items()
    }
    return {
        "rows": lanes,
        "seeds_present": seeds,
        "engine_classes": engines,
        "contrast": contrast,
    }


def _engine_parity(native: dict[int, dict], probe: dict[int, dict]) -> dict:
    """Seed-paired native-vs-probe medians for one arm."""
    shared = sorted(set(native) & set(probe))
    deltas = [
        float(probe[s]["infections_during_quarantine"])
        - float(native[s]["infections_during_quarantine"])
        for s in shared
        if probe[s].get("infections_during_quarantine") is not None
        and native[s].get("infections_during_quarantine") is not None
    ]
    return {
        "n_shared": len(shared),
        "shared_seeds": shared,
        "median_delta_during_quarantine": _median(deltas),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lane", action="append", required=True,
        help="name=dir, e.g. native=results/quar_head/native",
    )
    parser.add_argument("--theta", type=float, default=1e9)
    parser.add_argument("--settled-csv", default=SETTLED_SURFACE_REL)
    parser.add_argument("--out-csv", default="")
    parser.add_argument("--out-json", default="")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args()

    repo_root = resolve_repo_path(REPO_ROOT, args.repo_root) \
        if not Path(args.repo_root).is_absolute() \
        else Path(args.repo_root).resolve()
    design = load_design(
        str(repo_root / ATTRIBUTION_DESIGN_REL), repo_root=str(repo_root),
    )
    cells_by_arm = {
        arm: [
            c for c in enumerate_cells(design)
            if c.theta == args.theta and c.arm_id == arm
        ]
        for arm in ARMS
    }

    lanes = {}
    for spec in args.lane:
        name, _, raw_dir = spec.partition("=")
        lane_dir = Path(raw_dir)
        if not lane_dir.is_absolute():
            lane_dir = Path(resolve_repo_path(str(repo_root), raw_dir))
        lanes[name] = _lane_contrast(lane_dir, cells_by_arm)

    settled = {
        arm: _load_settled_rows(
            str(repo_root / args.settled_csv), args.theta, arm,
        )
        for arm in ARMS
    }
    settled_contrast = _arm_contrast(settled["A0_declared"], settled["A2_pool_transport_off"])

    parity = {}
    if "native" in lanes:
        for name, lane in lanes.items():
            if name == "native":
                continue
            parity[name] = {
                arm: _engine_parity(
                    lanes["native"]["rows"][arm], lane["rows"][arm],
                )
                for arm in ARMS
            }

    summary = {
        "theta": args.theta,
        "settled_d62f10d_contrast": settled_contrast,
        "lanes": {
            name: {
                "seeds_present": lane["seeds_present"],
                "engine_classes": lane["engine_classes"],
                "contrast": lane["contrast"],
            }
            for name, lane in lanes.items()
        },
        "engine_parity_vs_native": parity,
    }
    print(json.dumps(summary, indent=2, default=str))

    if args.out_csv:
        out_csv = Path(resolve_repo_path(str(repo_root), args.out_csv))
        prepare_output_directory(
            str(out_csv.parent), allowed_roots=(str(repo_root),),
        )
        fieldnames = (
            ["engine_lane"] + SURFACE_COLUMNS + PROBE_EXTRA_COLUMNS
        )
        with validated_open(
            str(out_csv), "w", allowed_roots=(str(repo_root),),
            newline="", encoding="utf-8",
        ) as fh:
            writer = csv.DictWriter(
                fh, fieldnames=fieldnames, extrasaction="ignore",
            )
            writer.writeheader()
            for name, lane in lanes.items():
                for arm, cells in cells_by_arm.items():
                    rows = lane["rows"][arm]
                    for cell in cells:
                        if cell.seed in rows:
                            writer.writerow(
                                {"engine_lane": name, **rows[cell.seed]},
                            )
    if args.out_json:
        out_json = Path(resolve_repo_path(str(repo_root), args.out_json))
        prepare_output_directory(
            str(out_json.parent), allowed_roots=(str(repo_root),),
        )
        with validated_open(
            str(out_json), "w", allowed_roots=(str(repo_root),),
            encoding="utf-8",
        ) as fh:
            json.dump(summary, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
