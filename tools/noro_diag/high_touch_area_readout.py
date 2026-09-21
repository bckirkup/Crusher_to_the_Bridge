#!/usr/bin/env python3
"""Readout for the NORO-HIGH-TOUCH-AREA-01 arms against the shipped baseline.

Aggregation only: reads the per-seed ``*.json.gz`` dumps that
``per_host_dose_challenge.py`` wrote for one sweep arm and for the shipped
baseline (the ``NORO-TRANSFER-PRODUCT-01`` cells at the same seeds), and
scores the four admissibility criteria the ledger froze **before** any arm
ran. It re-derives nothing and changes no constant.

Criteria (``docs/ledger/NORO-HIGH-TOUCH-AREA-01.md`` §4):

1. **neutrality** -- not scored here; the shipped arm is not re-run, the
   per-commit smoke in the PR is the gate.
2. **scaling** -- two layers, both reported:
   * *per touch* (sharp): the witness records ``sum_surface_area_m2`` and
     ``sum_log10_f_touch`` per call, so the mean area per pickup must be
     exactly ``scale x`` the baseline's per class, and the pooled mean
     ``log10 f_touch`` must shift by ``-log10(scale)`` per class. Both are
     properties of the *instrumented call*, so they hold regardless of how
     the voyages' trajectories diverge.
   * *whole voyage* (the frozen ±10 % test): median over seeds of
     ``hand_to_mouth_dose_gec x scale`` against the baseline median. This
     is the one that can legitimately depart, because trajectories diverge
     and pools deplete; a departure is attributed, not hidden.
3. **saturation** -- ``calls_capped / calls`` pooled over classes, and
   ``sum_requested / sum_offered`` from the delivery-scale witness.
4. **secondaries** -- summed over seeds, with the frozen resolvability floor.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
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

BASELINE_DIR = (
    REPO_ROOT / "docs" / "norovirus" / "noro_transfer_product_01"
    / "classic_cruise_1900"
)
WHOLE_VOYAGE_TOLERANCE = 0.10
CAP_SHARE_CEILING = 0.01
SECONDARIES_RESOLVABLE_AT = 20


def _load(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def load_arm(directory: Path, tag: str | None) -> dict[int, dict[str, Any]]:
    stem = "per_host_dose_challenge_" + (f"{tag}_" if tag else "")
    cells = {}
    for path in sorted(directory.glob(f"{stem}seed*.json.gz")):
        cell = _load(path)
        cells[int(cell["seed"])] = cell
    return cells


SOURCES = ("pool", "patch")


def _per_class_pickup(
    cell: dict[str, Any], sources: tuple[str, ...] = SOURCES,
) -> dict[str, dict[str, float]]:
    """Surface->hand witness rows for the given sources, merged per zone class.

    ``pool`` rows divide by the high-touch area under test; ``patch`` rows
    divide by the emesis-patch area, which the same scale multiplies but
    from a different base, so the two are never mixed when scoring area.
    """
    merged: dict[str, dict[str, float]] = {}
    for source in sources:
        rows = cell["transfer_product_witness"]["surface_to_hand"].get(source, {})
        for zone_class, row in rows.items():
            acc = merged.setdefault(zone_class, {
                "calls": 0.0, "calls_clean": 0.0, "calls_capped": 0.0,
                "sum_surface_area_m2": 0.0, "sum_log10_f_touch": 0.0,
                "sum_sq_log10_f_touch": 0.0,
            })
            for key in acc:
                acc[key] += float(row.get(key, 0.0))
    return merged


def _pool_classes(
    cells: dict[int, dict[str, Any]], sources: tuple[str, ...] = SOURCES,
) -> dict[str, dict[str, float]]:
    pooled: dict[str, dict[str, float]] = {}
    for cell in cells.values():
        for zone_class, row in _per_class_pickup(cell, sources).items():
            acc = pooled.setdefault(zone_class, dict.fromkeys(row, 0.0))
            for key, value in row.items():
                acc[key] += value
    return pooled


def _mean_and_se(total: float, total_sq: float, n: float) -> tuple[float, float]:
    if n <= 0:
        return math.nan, math.nan
    mean = total / n
    var = max(total_sq / n - mean * mean, 0.0)
    return mean, math.sqrt(var / n)


def per_touch_scaling(
    arm: dict[int, dict[str, Any]], base: dict[int, dict[str, Any]], scale: float,
) -> dict[str, Any]:
    """Criterion 2, per-touch layer, on pool pickups only.

    The area ratio is exact (no draw sits between the scale and the
    recorded denominator). The ``log10 f_touch`` shift carries the draws of
    the contact fraction, hand area and efficiency, so it is compared at
    three pooled standard errors.
    """
    arm_pool = _pool_classes(arm, ("pool",))
    base_pool = _pool_classes(base, ("pool",))
    out: dict[str, Any] = {}
    for zone_class in sorted(set(arm_pool) | set(base_pool)):
        a = arm_pool.get(zone_class)
        b = base_pool.get(zone_class)
        if not a or not b or a["calls"] == 0 or b["calls"] == 0:
            out[zone_class] = {"verdict": "no calls in one arm"}
            continue
        area_arm = a["sum_surface_area_m2"] / a["calls"]
        area_base = b["sum_surface_area_m2"] / b["calls"]
        # f_touch is logged only for clean (uncapped, unconfined, nonzero) calls.
        lf_arm, se_arm = _mean_and_se(
            a["sum_log10_f_touch"], a["sum_sq_log10_f_touch"], a["calls_clean"],
        )
        lf_base, se_base = _mean_and_se(
            b["sum_log10_f_touch"], b["sum_sq_log10_f_touch"], b["calls_clean"],
        )
        shift = lf_arm - lf_base
        se_shift = math.hypot(se_arm, se_base)
        expected = -math.log10(scale)
        out[zone_class] = {
            "calls_arm": a["calls"],
            "calls_base": b["calls"],
            "mean_area_per_call_m2_arm": area_arm,
            "mean_area_per_call_m2_base": area_base,
            "area_ratio": area_arm / area_base,
            "area_ratio_expected": scale,
            "mean_log10_f_touch_arm": lf_arm,
            "mean_log10_f_touch_base": lf_base,
            "calls_clean_arm": a["calls_clean"],
            "calls_clean_base": b["calls_clean"],
            "log10_f_touch_shift": shift,
            "log10_f_touch_shift_se": se_shift,
            "log10_f_touch_shift_expected": expected,
            "verdict": (
                "conforms"
                if math.isclose(area_arm / area_base, scale, rel_tol=1e-9)
                and (math.isnan(shift) or abs(shift - expected) <= 3.0 * se_shift)
                else "departs"
            ),
        }
    return out


def patch_pickups(cells: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Emesis-patch pickups, reported separately (different area base)."""
    pooled = _pool_classes(cells, ("patch",))
    return {
        zone_class: {
            "calls": row["calls"],
            "mean_area_per_call_m2": (
                row["sum_surface_area_m2"] / row["calls"] if row["calls"] else None
            ),
        }
        for zone_class, row in sorted(pooled.items())
    }


def whole_voyage_scaling(
    arm: dict[int, dict[str, Any]], base: dict[int, dict[str, Any]], scale: float,
) -> dict[str, Any]:
    """Criterion 2, whole-voyage layer, exactly as frozen (median, ±10 %)."""
    seeds = sorted(set(arm) & set(base))
    arm_doses = [arm[s]["fomite_witness"]["hand_to_mouth_dose_gec"] for s in seeds]
    base_doses = [base[s]["fomite_witness"]["hand_to_mouth_dose_gec"] for s in seeds]
    med_arm_scaled = statistics.median(d * scale for d in arm_doses)
    med_base = statistics.median(base_doses)
    ratio = med_arm_scaled / med_base if med_base > 0 else math.inf
    paired = [
        {
            "seed": s,
            "dose_base": b,
            "dose_arm": a,
            "arm_over_base": (a / b) if b > 0 else None,
        }
        for s, a, b in zip(seeds, arm_doses, base_doses, strict=True)
    ]
    return {
        "seeds": seeds,
        "median_hand_to_mouth_dose_gec_base": med_base,
        "median_hand_to_mouth_dose_gec_arm": statistics.median(arm_doses),
        "median_arm_times_scale_over_base": ratio,
        "tolerance": WHOLE_VOYAGE_TOLERANCE,
        "verdict": (
            "conforms" if abs(ratio - 1.0) <= WHOLE_VOYAGE_TOLERANCE else "departs"
        ),
        "paired": paired,
    }


def saturation(cells: dict[int, dict[str, Any]]) -> dict[str, Any]:
    pooled = _pool_classes(cells)
    calls = sum(r["calls"] for r in pooled.values())
    capped = sum(r["calls_capped"] for r in pooled.values())
    requested = sum(
        c["delivery_scale_witness"]["sum_requested_gec"] for c in cells.values()
    )
    offered = sum(
        c["delivery_scale_witness"]["sum_offered_gec"] for c in cells.values()
    )
    per_seed = [
        {
            "seed": s,
            "requested_over_offered": (
                c["delivery_scale_witness"]["sum_requested_gec"]
                / c["delivery_scale_witness"]["sum_offered_gec"]
                if c["delivery_scale_witness"]["sum_offered_gec"] > 0 else None
            ),
        }
        for s, c in sorted(cells.items())
    ]
    share = capped / calls if calls else math.nan
    per_class = {
        zone_class: {
            "calls": row["calls"],
            "calls_capped": row["calls_capped"],
            "capped_share": row["calls_capped"] / row["calls"] if row["calls"] else None,
        }
        for zone_class, row in sorted(_pool_classes(cells, ("pool",)).items())
    }
    return {
        "per_zone_class_pool": per_class,
        "surface_pickup_calls": calls,
        "calls_capped": capped,
        "capped_share": share,
        "capped_share_ceiling": CAP_SHARE_CEILING,
        "sum_requested_over_sum_offered": requested / offered if offered else None,
        "per_seed": per_seed,
        "verdict": "linear regime" if share <= CAP_SHARE_CEILING else "out of linear regime",
    }


def secondaries(cells: dict[int, dict[str, Any]]) -> dict[str, Any]:
    total = sum(int(c["transmission"]["secondaries"]) for c in cells.values())
    return {
        "seeds": len(cells),
        "secondaries_total": total,
        "per_seed": {s: int(c["transmission"]["secondaries"]) for s, c in sorted(cells.items())},
        "resolvable_at": SECONDARIES_RESOLVABLE_AT,
        "verdict": (
            "changed" if total >= SECONDARIES_RESOLVABLE_AT
            else f"not resolvable at n={len(cells)}"
        ),
    }


def readout(arm_dir: Path, tag: str, scale: float) -> dict[str, Any]:
    arm = load_arm(arm_dir, tag)
    base = load_arm(BASELINE_DIR, None)
    base = {s: c for s, c in base.items() if s in arm}
    missing = sorted(set(arm) - set(base))
    if missing:
        raise SystemExit(f"no baseline cell for seeds {missing}")
    return {
        "arm_tag": tag,
        "scale": scale,
        "cells": len(arm),
        "per_touch_scaling": per_touch_scaling(arm, base, scale),
        "patch_pickups_arm": patch_pickups(arm),
        "patch_pickups_base": patch_pickups(base),
        "whole_voyage_scaling": whole_voyage_scaling(arm, base, scale),
        "saturation_arm": saturation(arm),
        "saturation_base": saturation(base),
        "secondaries_arm": secondaries(arm),
        "secondaries_base": secondaries(base),
    }


def _print(r: dict[str, Any]) -> None:
    print(f"== {r['arm_tag']} (scale {r['scale']}) over {r['cells']} cells ==")
    print("criterion 2a, per touch:")
    for zone_class, row in r["per_touch_scaling"].items():
        if "area_ratio" not in row:
            print(f"  {zone_class:10s} {row['verdict']}")
            continue
        print(
            f"  {zone_class:10s} area x{row['area_ratio']:.6f} (exp {row['area_ratio_expected']}), "
            f"log10 f_touch shift {row['log10_f_touch_shift']:+.3f}"
            f"±{row['log10_f_touch_shift_se']:.3f} "
            f"(exp {row['log10_f_touch_shift_expected']:+.3f}), "
            f"pool n={int(row['calls_arm'])}/{int(row['calls_base'])}  -> {row['verdict']}",
        )
    for label in ("arm", "base"):
        rows = r[f"patch_pickups_{label}"]
        desc = ", ".join(
            f"{zc} n={int(v['calls'])} A={v['mean_area_per_call_m2']:.3g} m2"
            for zc, v in rows.items()
        ) or "none"
        print(f"  patch pickups, {label}: {desc}")
    w = r["whole_voyage_scaling"]
    print(
        "criterion 2b, whole voyage: median(arm x scale)/median(base) = "
        f"{w['median_arm_times_scale_over_base']:.3f}  -> {w['verdict']}",
    )
    for label in ("arm", "base"):
        s = r[f"saturation_{label}"]
        print(
            f"criterion 3, {label}: capped {int(s['calls_capped'])}/{int(s['surface_pickup_calls'])} "
            f"= {s['capped_share']:.2e}, requested/offered "
            f"{s['sum_requested_over_sum_offered']:.3f}  -> {s['verdict']}",
        )
        print(
            "    per class (pool): " + ", ".join(
                f"{zc} {int(v['calls_capped'])}/{int(v['calls'])}"
                for zc, v in s["per_zone_class_pool"].items()
            ),
        )
    for label in ("arm", "base"):
        s = r[f"secondaries_{label}"]
        print(f"criterion 4, {label}: {s['secondaries_total']} secondaries over {s['seeds']} seeds -> {s['verdict']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-dir", type=Path, required=True)
    parser.add_argument("--arm-tag", required=True)
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = readout(args.arm_dir, args.arm_tag, args.scale)
    out_dir = prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),))
    path = resolve_child_path(str(out_dir), f"high_touch_area_readout_{args.arm_tag}.json")
    Path(path).write_text(json.dumps(result, indent=1, sort_keys=True, default=str) + "\n")
    _print(result)
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
