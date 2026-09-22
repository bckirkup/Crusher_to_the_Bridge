#!/usr/bin/env python3
"""Readout for the high-touch-area sweep arms against the shipped baseline.

Aggregation only: reads the per-seed ``*.json.gz`` dumps that
``per_host_dose_challenge.py`` wrote for one sweep arm and for the shipped
baseline (the ``NORO-TRANSFER-PRODUCT-01`` cells at the same seeds), and
scores the admissibility criteria the ledger froze **before** any arm
ran. It re-derives nothing and changes no constant.

Criteria (``docs/ledger/NORO-HIGH-TOUCH-SWEEP-01.md`` §4, carrying over
``NORO-HIGH-TOUCH-AREA-01`` §4 with the per-class generalisation and the
rescored 2b):

1. **neutrality** -- not scored here; the shipped arm is not re-run, the
   per-commit smoke in the PR is the gate.
2. **scaling** -- two layers, both reported:
   * *per touch* (sharp, per class): the witness records
     ``sum_surface_area_m2`` and ``sum_log10_f_touch`` per call, so the
     mean area per pickup must be exactly ``scale_c x`` the baseline's
     per class, and the pooled mean ``log10 f_touch`` must shift by
     ``-log10(scale_c)`` per class. A class whose capped share exceeds
     1 % is ``censored``: ``f_touch`` is logged only for uncapped calls,
     so the surviving draws are the low tail.
   * *whole voyage* (rescored, paired per-seed distribution): per shared
     seed ``r_s = log10(dose_arm) - log10(dose_base)``; a pair with either
     dose exactly 0 is undefined and excluded. The only scored statistic
     is the sign: exact two-sided binomial(n, 1/2) at alpha = 0.05 in the
     frozen predicted direction (``--predicted-direction``; ``hardware``
     is up, ``shared``/``broad`` are down). Magnitudes are reported, never
     scored; ``legacy_median_ratio_unscaled`` is printed for continuity
     with the ``g0.25`` readout and carries no verdict.
3. **saturation** -- ``calls_capped / calls`` pooled and per class, with
   ``calls_confined`` and ``calls_zero_mass`` shares, a per-class regime
   label, and ``classes_measuring_the_cap`` (> 20 % capped calls).
4. **secondaries** -- summed over seeds, with the frozen resolvability floor.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
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

BASELINE_DIR = (
    REPO_ROOT / "docs" / "norovirus" / "noro_transfer_product_01"
    / "classic_cruise_1900"
)
CAP_SHARE_CEILING = 0.01
CAP_MEASURE_CEILING = 0.20
BINOMIAL_ONE_SIDED_ALPHA = 0.025
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


def _scale_for(scales: dict[str, float], zone_class: str, default: float) -> float:
    """Per-class multiplier; an unlisted class rides at the engine default."""
    return scales.get(zone_class, default)


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
                "calls_confined": 0.0, "calls_zero_mass": 0.0,
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
    arm: dict[int, dict[str, Any]],
    base: dict[int, dict[str, Any]],
    scales: dict[str, float],
    default_scale: float,
) -> dict[str, Any]:
    """Criterion 2a, per-touch layer, per class, on pool pickups only.

    The area ratio is exact (no draw sits between the scale and the
    recorded denominator). The ``log10 f_touch`` shift carries the draws of
    the contact fraction, hand area and efficiency, so it is compared at
    three pooled standard errors. A class whose capped share exceeds
    ``CAP_SHARE_CEILING`` is ``censored`` regardless of agreement.
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
        scale_c = _scale_for(scales, zone_class, default_scale)
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
        expected = -math.log10(scale_c)
        area_ratio = area_arm / area_base
        area_matches = math.isclose(area_ratio, scale_c, rel_tol=1e-9)
        shift_matches = (
            math.isnan(shift) or abs(shift - expected) <= 3.0 * se_shift
        )
        capped_share = a["calls_capped"] / a["calls"]
        if capped_share > CAP_SHARE_CEILING:
            verdict = "censored"
        elif area_matches and shift_matches:
            verdict = "conforms"
        else:
            verdict = "departs"
        out[zone_class] = {
            "scale_c": scale_c,
            "calls_arm": a["calls"],
            "calls_base": b["calls"],
            "mean_area_per_call_m2_arm": area_arm,
            "mean_area_per_call_m2_base": area_base,
            "area_ratio": area_ratio,
            "area_ratio_expected": scale_c,
            "mean_log10_f_touch_arm": lf_arm,
            "mean_log10_f_touch_base": lf_base,
            "calls_clean_arm": a["calls_clean"],
            "calls_clean_base": b["calls_clean"],
            "log10_f_touch_shift": shift,
            "log10_f_touch_shift_se": se_shift,
            "log10_f_touch_shift_expected": expected,
            "area_ratio_matches": area_matches,
            "log10_shift_within_3se": shift_matches,
            "capped_share": capped_share,
            "verdict": verdict,
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


def _binomial_one_sided_tail(n: int, k: int) -> float:
    """P(X >= k) for X ~ binomial(n, 1/2)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2**n


def _binomial_p_two_sided(n: int, k: int) -> float | None:
    """Exact two-sided binomial p at p=0.5, doubled one-sided tail."""
    if n <= 0:
        return None
    if k >= n / 2:
        tail = _binomial_one_sided_tail(n, k)
    else:
        tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2**n
    return min(1.0, 2.0 * tail)


def _k_threshold_alpha05(n: int) -> int | None:
    """Smallest k whose one-sided binomial(n, 1/2) tail is <= alpha/2."""
    for k in range(n + 1):
        if _binomial_one_sided_tail(n, k) <= BINOMIAL_ONE_SIDED_ALPHA:
            return k
    return None


def paired_dose_distribution(
    arm: dict[int, dict[str, Any]],
    base: dict[int, dict[str, Any]],
    scales: dict[str, float],
    predicted_direction: str,
) -> dict[str, Any]:
    """Criterion 2b, rescored: paired per-seed log10 dose shift.

    ``r_s = log10(dose_arm) - log10(dose_base)`` over the shared seeds; a
    pair with either dose exactly 0 is ``undefined`` and excluded from
    ``n``. The only scored statistic is the sign of ``r_s`` against the
    frozen ``predicted_direction``; magnitudes are reported, never scored.
    """
    seeds = sorted(set(arm) & set(base))
    arm_doses = [arm[s]["fomite_witness"]["hand_to_mouth_dose_gec"] for s in seeds]
    base_doses = [base[s]["fomite_witness"]["hand_to_mouth_dose_gec"] for s in seeds]
    paired = [
        {
            "seed": s,
            "dose_base": b,
            "dose_arm": a,
            "r_s": (
                math.log10(a) - math.log10(b) if a > 0 and b > 0 else None
            ),
        }
        for s, a, b in zip(seeds, arm_doses, base_doses, strict=True)
    ]
    r_values = [row["r_s"] for row in paired if row["r_s"] is not None]
    n = len(r_values)

    def matches(r: float) -> bool:
        return r > 0 if predicted_direction == "up" else r < 0

    k = sum(1 for r in r_values if matches(r))
    k_threshold = _k_threshold_alpha05(n)
    if n == 0:
        verdict = "undefined: no defined pairs"
    elif k_threshold is not None and k >= k_threshold:
        verdict = "shifted"
    elif k_threshold is not None and n - k >= k_threshold:
        verdict = "shifted against prediction"
    else:
        verdict = f"not resolvable at n={n}"
    iqr = (
        list(statistics.quantiles(r_values, n=4, method="inclusive"))[::2]
        if n >= 4 else None
    )
    med_arm = statistics.median(arm_doses)
    med_base = statistics.median(base_doses)
    return {
        "seeds": seeds,
        "paired": paired,
        "pairs_defined": n,
        "pairs_undefined": len(paired) - n,
        "n": n,
        "predicted_direction": predicted_direction,
        "k_matching_predicted_sign": k,
        "k_threshold_alpha05": k_threshold,
        "binomial_p_two_sided": _binomial_p_two_sided(n, k),
        "verdict": verdict,
        "median_r": statistics.median(r_values) if r_values else None,
        "iqr_r": iqr,
        "min_r": min(r_values) if r_values else None,
        "max_r": max(r_values) if r_values else None,
        "legacy_median_ratio_unscaled": (
            med_arm / med_base if med_base > 0 else None
        ),
        "note": (
            "legacy_median_ratio_unscaled is the retired whole-voyage "
            "median ratio printed for continuity with the g0.25 readout; "
            "it carries no verdict (ledger NORO-HIGH-TOUCH-SWEEP-01 §4.3)."
        ),
    }


def _regime(capped_share: float | None) -> str:
    if capped_share is None or capped_share <= CAP_SHARE_CEILING:
        return "linear"
    if capped_share <= CAP_MEASURE_CEILING:
        return "capped regime"
    return "measures the cap"


def _saturation_class_row(row: dict[str, float]) -> dict[str, Any]:
    calls = row["calls"]

    def share(key: str) -> float | None:
        return row[key] / calls if calls else None

    capped_share = share("calls_capped")
    return {
        "calls": calls,
        "calls_capped": row["calls_capped"],
        "capped_share": capped_share,
        "calls_confined": row["calls_confined"],
        "confined_share": share("calls_confined"),
        "calls_zero_mass": row["calls_zero_mass"],
        "zero_mass_share": share("calls_zero_mass"),
        "regime": _regime(capped_share),
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
        zone_class: _saturation_class_row(row)
        for zone_class, row in sorted(_pool_classes(cells, ("pool",)).items())
    }
    measuring_the_cap = [
        zone_class
        for zone_class, row in per_class.items()
        if row["capped_share"] is not None
        and row["capped_share"] > CAP_MEASURE_CEILING
    ]
    return {
        "per_zone_class_pool": per_class,
        "classes_measuring_the_cap": measuring_the_cap,
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


def readout(
    arm_dir: Path,
    tag: str,
    scale: float | None = None,
    scale_by_zone_class: dict[str, Any] | None = None,
    predicted_direction: str = "up",
) -> dict[str, Any]:
    arm = load_arm(arm_dir, tag)
    base = load_arm(BASELINE_DIR, None)
    base = {s: c for s, c in base.items() if s in arm}
    missing = sorted(set(arm) - set(base))
    if missing:
        raise SystemExit(f"no baseline cell for seeds {missing}")
    if scale_by_zone_class is not None:
        scales = {zc: float(v) for zc, v in scale_by_zone_class.items()}
        default_scale = 1.0
    else:
        scales = {}
        default_scale = float(scale)
    result: dict[str, Any] = {
        "arm_tag": tag,
        "predicted_direction": predicted_direction,
        "cells": len(arm),
        "per_touch_scaling": per_touch_scaling(arm, base, scales, default_scale),
        "patch_pickups_arm": patch_pickups(arm),
        "patch_pickups_base": patch_pickups(base),
        "paired_dose_distribution": paired_dose_distribution(
            arm, base, scales, predicted_direction,
        ),
        "saturation_arm": saturation(arm),
        "saturation_base": saturation(base),
        "secondaries_arm": secondaries(arm),
        "secondaries_base": secondaries(base),
    }
    if scale_by_zone_class is not None:
        result["scale_by_zone_class"] = scales
    else:
        result["scale"] = float(scale)
    return result


def _fmt(value: float | None, spec: str = ".4g") -> str:
    return format(value, spec) if isinstance(value, float) else str(value)


def _print(r: dict[str, Any]) -> None:
    scale_desc = (
        f"scale {r['scale']}"
        if "scale" in r
        else f"scale_by_zone_class {r['scale_by_zone_class']}"
    )
    print(f"== {r['arm_tag']} ({scale_desc}) over {r['cells']} cells ==")
    cap_classes = r["saturation_arm"]["classes_measuring_the_cap"]
    if cap_classes:
        print(
            "HEADLINE: arm measures the conservation cap, not the chain: "
            + ", ".join(cap_classes)
        )
    print("criterion 2a, per touch:")
    for zone_class, row in r["per_touch_scaling"].items():
        if "area_ratio" not in row:
            print(f"  {zone_class:10s} {row['verdict']}")
            continue
        matches = (
            f" [area_match={row['area_ratio_matches']}, "
            f"shift_match={row['log10_shift_within_3se']}]"
            if row["verdict"] == "censored" else ""
        )
        print(
            f"  {zone_class:10s} area x{row['area_ratio']:.6f} (exp {row['area_ratio_expected']}), "
            f"log10 f_touch shift {row['log10_f_touch_shift']:+.3f}"
            f"±{row['log10_f_touch_shift_se']:.3f} "
            f"(exp {row['log10_f_touch_shift_expected']:+.3f}), "
            f"capped {row['capped_share']:.2e}, "
            f"pool n={int(row['calls_arm'])}/{int(row['calls_base'])}  -> {row['verdict']}"
            f"{matches}",
        )
    for label in ("arm", "base"):
        rows = r[f"patch_pickups_{label}"]
        desc = ", ".join(
            f"{zc} n={int(v['calls'])} A={v['mean_area_per_call_m2']:.3g} m2"
            for zc, v in rows.items()
        ) or "none"
        print(f"  patch pickups, {label}: {desc}")
    p = r["paired_dose_distribution"]
    iqr = (
        f"[{_fmt(p['iqr_r'][0], '+.3f')}, {_fmt(p['iqr_r'][1], '+.3f')}]"
        if p["iqr_r"] else "n/a"
    )
    print(
        f"criterion 2b, paired dose: n={p['n']} defined "
        f"({p['pairs_undefined']} undefined), "
        f"k={p['k_matching_predicted_sign']} matching "
        f"'{p['predicted_direction']}', "
        f"median r={_fmt(p['median_r'], '+.3f')} IQR {iqr} "
        f"[{_fmt(p['min_r'], '+.3f')}, {_fmt(p['max_r'], '+.3f')}], "
        f"binomial p={_fmt(p['binomial_p_two_sided'])}  -> {p['verdict']}",
    )
    print(
        "    legacy median ratio (unscaled, no verdict): "
        f"{_fmt(p['legacy_median_ratio_unscaled'])}",
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
                f"{zc} {int(v['calls_capped'])}/{int(v['calls'])} {v['regime']}"
                for zc, v in s["per_zone_class_pool"].items()
            ),
        )
    for label in ("arm", "base"):
        s = r[f"secondaries_{label}"]
        print(f"criterion 4, {label}: {s['secondaries_total']} secondaries over {s['seeds']} seeds -> {s['verdict']}")


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError(
            f"expected a JSON object, got {value!r}",
        )
    return parsed


def _safe_path(path: str) -> str:
    """Canonicalise a CLI-derived target and refuse anything outside the repo."""
    resolved = os.path.realpath(path)
    base_dir = os.path.realpath(str(REPO_ROOT))
    if resolved != base_dir and not resolved.startswith(base_dir + os.sep):
        raise ValueError(f"path {path!r} is outside the allowed directory")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-dir", type=Path, required=True)
    parser.add_argument("--arm-tag", type=_identifier, required=True)
    scale_group = parser.add_mutually_exclusive_group(required=True)
    scale_group.add_argument("--scale", type=float)
    scale_group.add_argument(
        "--scale-by-zone-class", type=_json_object,
        help='JSON object of per-zone-class multipliers, e.g. '
             '\'{"cabin": 0.116, "galley": 0.05}\'; classes absent from the '
             'map ride at the engine default 1.0',
    )
    parser.add_argument(
        "--predicted-direction", choices=("up", "down"), required=True,
        help="frozen per arm in the ledger: hardware=up, shared/broad=down",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = readout(
        args.arm_dir,
        args.arm_tag,
        scale=args.scale,
        scale_by_zone_class=args.scale_by_zone_class,
        predicted_direction=args.predicted_direction,
    )
    out_dir = prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),))
    filename = resolve_child_path(
        str(out_dir), f"high_touch_area_readout_{args.arm_tag}.json",
    )
    path = _safe_path(filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=1, sort_keys=True, default=str) + "\n")
    _print(result)
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
