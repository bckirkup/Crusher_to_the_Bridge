#!/usr/bin/env python3
"""Readout for the NORO-TRANSFER-PRODUCT-01 cells.

Aggregation only: this script reads the per-seed ``*.json.gz`` dumps written by
``per_host_dose_challenge.py`` and never re-runs or re-derives a measurement.
It answers the question frozen in ``docs/ledger/NORO-TRANSFER-PRODUCT-01.md``:
at which layer the hull's fomite chain is commensurable with published
transfer measurements, and whether it is defensible there.

Four blocks, in the order the ledger declares them:

* **rng_neutrality** -- the gate. Every existing ``fomite_witness`` aggregate
  must reproduce *exactly* the value the ``5870c74`` cells under
  ``docs/norovirus/noro_dose_block_01/classic_cruise_1900/`` recorded. The
  engine is unchanged, so any deviation means the extended instrument consumed
  a draw and the cells are void.
* **surface_to_hand** -- the per-touch factor ``f_touch`` the witness records,
  pooled in log10 space per source and zone class, with the censored share
  (confined / zero-mass / capped calls) reported alongside so an efficiency is
  never quoted without the share of calls it does not describe. The *implied*
  per-touch transfer efficiency is reported as an **inference**: ``f_touch``
  bundles the areal-dilution geometry with the efficiency, and dividing the
  geometry back out uses the geometric means of the two uniform draws, not a
  measurement of them.
* **hand_to_mouth** -- the per-epoch ``dose / hand_load`` ratio, split
  eating/non-eating. This is *not* the per-contact efficiency: the ratio is
  ``contacts * used_fraction * efficiency`` and ``contacts`` is an RNG draw the
  instrument may not re-take, so the per-contact decomposition is unresolved
  from the witness and the closed form over the constants is what §4 of
  ``docs/literature/consensus_tranche_44_transfer_product.md`` compares.
* **bookkeeping_contrast** -- the whole-voyage ratio ``NORO-DOSE-BLOCK-01``
  reported, restated beside the saturation witness that explains it, so the
  two are never read as the same quantity.

The literature figures below are the ones tranche 44 retrieved. They are
comparison targets only; nothing here is fitted to them and this script changes
no constant.
"""

from __future__ import annotations

import argparse
import json
import math
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
from tools.noro_diag.cell_readout import (  # noqa: E402
    dig,
    gate_report,
    load_cells,
    number,
    partition,
    print_block,
)

BLOCK_SEEDS = [*range(8000, 8020)]
PAIR_SEEDS = [8105, 8106]

# The existing witness keys that must reproduce exactly against the 5870c74
# cells for the extended instrument to be RNG-neutral.
WITNESS_KEYS = (
    "surface_mass_offered_gec",
    "mass_requested_gec",
    "mass_delivered_to_hands_gec",
    "hand_load_seen_gec",
    "hand_to_mouth_dose_gec",
    "deliver_calls",
    "hand_to_mouth_calls",
)

# Engine draw supports, restated from engines/transmission_core.py so the
# geometry can be divided back out of f_touch. Not a measurement of the draws.
SURFACE_CONTACT_FRACTION_RANGE = (0.008, 0.25)
HAND_AREA_CM2_RANGE = (445.0, 535.0)

# Tranche 44 comparison targets, per contact, for the *inferred* surface->hand
# efficiency only. Norovirus and norovirus surrogates on non-porous donors by
# infectivity (Tuladhar 2013, Bidawid 2004, Grove 2015); the wider envelope
# over analogous viruses and humidity (Sharps 2012, Lopez 2013, Ansari 1988,
# Behzadinasab 2021).
LIT_SURFACE_TO_HAND_NOROVIRUS = (0.020, 0.24)
LIT_SURFACE_TO_HAND_ENVELOPE = (0.005, 0.80)


def _uniform_geomean(low: float, high: float) -> float:
    """Geometric mean of ``uniform(low, high)``, exactly."""
    span = high - low
    return math.exp(
        ((high * math.log(high) - high) - (low * math.log(low) - low)) / span,
    )


GM_USED_FRACTION = _uniform_geomean(*SURFACE_CONTACT_FRACTION_RANGE)
GM_HAND_AREA_M2 = _uniform_geomean(*HAND_AREA_CM2_RANGE) / 1.0e4


def _baseline_witnesses(baseline_dir: Path) -> dict[int, dict[str, float]]:
    """The 5870c74 ``fomite_witness`` per seed, as the reproduction target."""
    return {
        int(summary["seed"]): {
            key: float(dig(summary, f"fomite_witness.{key}") or 0.0)
            for key in WITNESS_KEYS
        }
        for summary in load_cells(baseline_dir)
    }


def rng_neutrality(
    cells: list[dict[str, Any]], baseline_dir: Path,
) -> dict[str, Any]:
    """The gate: exact reproduction of every pre-existing witness total."""
    baseline = _baseline_witnesses(baseline_dir)
    rows, mismatches, missing = [], [], []
    for summary in cells:
        seed = int(summary["seed"])
        target = baseline.get(seed)
        if target is None:
            missing.append(seed)
            continue
        deviations = {
            key: {
                "expected": target[key],
                "observed": float(dig(summary, f"fomite_witness.{key}") or 0.0),
            }
            for key in WITNESS_KEYS
            if float(dig(summary, f"fomite_witness.{key}") or 0.0) != target[key]
        }
        rows.append({"seed": seed, "keys_compared": len(WITNESS_KEYS),
                     "exact": not deviations})
        if deviations:
            mismatches.append({"seed": seed, "deviations": deviations})
    verdict = bool(rows) and not mismatches and not missing
    return {
        "baseline_dir": str(baseline_dir),
        "cells_compared": rows,
        "seeds_absent_from_baseline": missing,
        "mismatches": mismatches,
        "verdict": "PASS" if verdict else "FAIL",
        "cells_void_if_failed": not verdict,
    }


def _merge_buckets(buckets: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    """Pool like-for-like accumulator buckets across cells."""
    out: dict[str, Any] = {}
    for bucket in buckets:
        for key, value in bucket.items():
            if key.startswith("hist_log10"):
                merged = out.setdefault(key, [0] * len(value))
                out[key] = [a + b for a, b in zip(merged, value, strict=True)]
            elif key.startswith(("calls", "sum_", "hist_under", "hist_over")):
                out[key] = out.get(key, 0) + value
            elif key == f"min_{prefix}" and value is not None:
                out[key] = min(out.get(key, math.inf), value)
            elif key == f"max_{prefix}" and value is not None:
                out[key] = max(out.get(key, -math.inf), value)
    return out


def _log_stats(bucket: dict[str, Any], prefix: str, n: int) -> dict[str, Any]:
    """Geometric mean and log10 sd of a pooled log-accumulator bucket."""
    if n <= 0:
        return {"n": 0}
    mean_log = bucket[f"sum_{prefix}"] / n
    variance = max(0.0, bucket[f"sum_sq_{prefix}"] / n - mean_log**2)
    return {
        "n": n,
        "geometric_mean": 10.0**mean_log,
        "mean_log10": mean_log,
        "sd_log10": math.sqrt(variance),
        "min": (
            10.0 ** bucket[f"min_{prefix}"]
            if bucket.get(f"min_{prefix}") is not None
            else None
        ),
        "max": (
            10.0 ** bucket[f"max_{prefix}"]
            if bucket.get(f"max_{prefix}") is not None
            else None
        ),
    }


def _censoring(bucket: dict[str, Any]) -> dict[str, Any]:
    """The share of calls an efficiency estimate does not describe."""
    calls = bucket.get("calls", 0)
    named = ("calls_clean", "calls_capped", "calls_confined", "calls_zero_mass")
    shares = {
        key: (bucket.get(key, 0) / calls if calls else 0.0) for key in named
    }
    return {"calls": calls, **{k: bucket.get(k, 0) for k in named},
            "shares": shares}


def _classify(value: float, window: tuple[float, float]) -> str:
    low, high = window
    if value < low:
        return "below"
    return "inside" if value <= high else "above"


def surface_to_hand(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-touch f_touch by source and zone class, plus the implied efficiency."""
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for summary in cells:
        witness = dig(summary, "transfer_product_witness.surface_to_hand") or {}
        for source, zones in witness.items():
            for zone_class, bucket in zones.items():
                grouped.setdefault(source, {}).setdefault(
                    zone_class, [],
                ).append(bucket)
    out: dict[str, Any] = {
        "geometry_divisor": {
            "geomean_used_fraction": GM_USED_FRACTION,
            "geomean_hand_area_m2": GM_HAND_AREA_M2,
            "note": (
                "implied_efficiency divides the areal geometry back out of "
                "f_touch using the geometric means of the two uniform draws "
                "and the mean witnessed surface area; it is an inference, not "
                "a measurement of the efficiency draw"
            ),
        },
    }
    for source, zones in sorted(grouped.items()):
        for zone_class, buckets in sorted(zones.items()):
            out[f"{source}/{zone_class}"] = _surface_cell(buckets)
    return out


def _surface_cell(buckets: list[dict[str, Any]]) -> dict[str, Any]:
    """One pooled (source, zone class) row: f_touch and implied efficiency."""
    merged = _merge_buckets(buckets, "log10_f_touch")
    clean = merged.get("calls_clean", 0)
    stats = _log_stats(merged, "log10_f_touch", clean)
    row: dict[str, Any] = {
        "f_touch_per_contact": stats,
        "censoring": _censoring(merged),
    }
    if not clean:
        return row
    mean_area = merged["sum_surface_area_m2"] / merged["calls"]
    implied = (
        stats["geometric_mean"] * mean_area
        / (GM_USED_FRACTION * GM_HAND_AREA_M2)
    )
    row["mean_surface_area_m2"] = mean_area
    row["implied_efficiency_geomean"] = implied
    row["vs_norovirus_band"] = _classify(
        implied, LIT_SURFACE_TO_HAND_NOROVIRUS,
    )
    row["vs_analogue_envelope"] = _classify(
        implied, LIT_SURFACE_TO_HAND_ENVELOPE,
    )
    return row


def hand_to_mouth(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-epoch dose/hand_load, eating and non-eating. Not a per-contact rate."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for summary in cells:
        witness = dig(summary, "transfer_product_witness.hand_to_mouth") or {}
        for meal, bucket in witness.items():
            grouped.setdefault(meal, []).append(bucket)
    out: dict[str, Any] = {
        "note": (
            "dose/hand_load is contacts * used_fraction * efficiency per "
            "epoch; contacts is an RNG draw the instrument may not re-take, "
            "so the per-contact efficiency is unresolved from this witness"
        ),
    }
    for meal, buckets in sorted(grouped.items()):
        merged = _merge_buckets(buckets, "log10_ratio")
        calls = merged.get("calls", 0)
        out[meal] = {
            "ratio_per_epoch": _log_stats(merged, "log10_ratio", calls),
            "calls": calls,
            "calls_capped": merged.get("calls_capped", 0),
            "capped_share": (
                merged.get("calls_capped", 0) / calls if calls else 0.0
            ),
        }
    return out


def bookkeeping_contrast(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """The whole-voyage ratio beside the saturation that explains it."""
    rows = []
    for summary in cells:
        offered = number(summary, "fomite_witness.surface_mass_offered_gec")
        requested = number(summary, "fomite_witness.mass_requested_gec")
        delivered = number(
            summary, "fomite_witness.mass_delivered_to_hands_gec",
        )
        scale = dig(summary, "delivery_scale_witness") or {}
        deliver_calls = float(scale.get("deliver_calls", 0) or 0)
        rows.append({
            "seed": summary["seed"],
            "requested_over_offered": (
                requested / offered if offered else math.nan
            ),
            "whole_voyage_loss_log10": (
                math.log10(offered / delivered)
                if offered > 0.0 and delivered > 0.0 else math.nan
            ),
            "scaled_call_share": (
                float(scale.get("scaled_calls", 0) or 0) / deliver_calls
                if deliver_calls else math.nan
            ),
            "geometric_mean_scale": scale.get("geometric_mean_scale"),
        })
    saturated = [
        row for row in rows if row["requested_over_offered"] >= 1.0
    ]
    return {
        "cells": rows,
        "cells_demand_exceeded_pool": [row["seed"] for row in saturated],
        "note": (
            "offered sums a persisting pool once per epoch it survives, so "
            "this ratio is a mass-epoch bookkeeping quantity truncated by "
            "conservation, not a transfer efficiency"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path,
        default=(
            REPO_ROOT
            / "docs/norovirus/noro_transfer_product_01/classic_cruise_1900"
        ),
    )
    parser.add_argument(
        "--baseline-dir", type=Path,
        default=(
            REPO_ROOT / "docs/norovirus/noro_dose_block_01/classic_cruise_1900"
        ),
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_transfer_product_01",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cells = load_cells(args.raw_dir)
    admissible, void = partition(cells)
    payload, gates_ok = gate_report(cells, admissible, void, args.raw_dir)
    neutrality = rng_neutrality(cells, args.baseline_dir)
    payload.update({
        "rng_neutrality": neutrality,
        "surface_to_hand": surface_to_hand(admissible),
        "hand_to_mouth": hand_to_mouth(admissible),
        "bookkeeping_contrast": bookkeeping_contrast(admissible),
        "block_seeds": BLOCK_SEEDS,
        "pair_seeds": PAIR_SEEDS,
    })
    for key in (
        "rng_neutrality", "surface_to_hand", "hand_to_mouth",
        "bookkeeping_contrast",
    ):
        print_block(key, payload[key])
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    path = resolve_child_path(str(out_dir), "transfer_product_cells.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True, default=str)
    print(f"\nwritten: {path}")
    return 0 if gates_ok and neutrality["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
