#!/usr/bin/env python3
"""Readout for the NORO-TOUCH-SHARE-01 coincidence block.

Aggregation only: reads the per-seed ``*.json.gz`` dumps that
``per_host_dose_challenge.py`` wrote for the two arms -- ``per_surface``
with ``areal`` touch shares (base) and ``per_surface`` with the
``declared`` table (arm) -- and scores the statistics and admissibility
rule the ledger (``docs/ledger/NORO-TOUCH-SHARE-01.md`` §4) froze before
the block ran. It re-derives nothing, fits nothing and changes no
constant.

The measured quantity is coincidence: which hosts are credited fomite mass
delivered to hands, per ``zone_class.item_class`` key -- not how much dose,
and every dose quantity below is a paired ratio or share against a
withdrawn baseline (``docs/norovirus/norovirus_open_ledger.md`` §1), never
a dose result. The class witness is keyed by zone class, so the
admissibility statistic reads ``public.button_or_dispenser`` directly
rather than a ship-wide item-class mix.

Admissibility (ledger §4): the declared table ``changes_coincidence`` if
median jaccard < 0.90 and the focus class's delivered share rises by
more than 0.10 absolute in at least 15 seeds; it is ``inert`` if the
credited host sets are identical on every seed; otherwise
``indeterminate``. The verdict is a finding, not a failure: exit is 0.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
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

JACCARD_THRESHOLD = 0.90
FOCUS_SHARE_GAIN = 0.10
FOCUS_GAIN_SEEDS = 15
CAPPED_SHARE_FLAG = 0.10


def _load(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def load_arm(directory: Path, tag: str) -> dict[int, dict[str, Any]]:
    """The per-seed cells one arm wrote, keyed by seed."""
    stem = f"per_host_dose_challenge_{tag}_"
    cells = {}
    for path in sorted(directory.glob(f"{stem}seed*.json.gz")):
        cell = _load(path)
        cells[int(cell["seed"])] = cell
    return cells


def _host_delivered(cell: dict[str, Any]) -> dict[int, float]:
    """Per-host voyage total of fomite mass delivered to hands.

    Reads ``fomite_delivered_by_host`` -- the dump's dedicated top-level
    map, which covers every host whose hands received mass, not only hosts
    that reached the challenge/credit path (``hosts[]``). Absent key is a
    KeyError: this readout only reads dumps written by the same tool
    version.
    """
    return {
        int(agent_id): float(mass)
        for agent_id, mass in cell["fomite_delivered_by_host"].items()
    }


def gini(values: list[float]) -> float:
    """Gini coefficient of non-negative shares via the sorted formula."""
    ordered = sorted(v for v in values if v > 0.0)
    n = len(ordered)
    if n <= 1:
        return 0.0
    total = sum(ordered)
    weighted = sum((index + 1) * v for index, v in enumerate(ordered))
    return (2.0 * weighted) / (n * total) - (n + 1.0) / n


def top_decile_share(values: list[float]) -> float:
    """Share of the total held by the top ceil(n/10) hosts."""
    ordered = sorted((v for v in values if v > 0.0), reverse=True)
    total = sum(ordered)
    if not ordered or total <= 0.0:
        return 0.0
    k = max(1, math.ceil(len(ordered) / 10))
    return sum(ordered[:k]) / total


def _class_stats(cell: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Per dotted class key: shares, hosts credited, capped-call share.

    ``delivered_share`` is over the ship-total delivered mass;
    ``zone_share`` is over keys sharing the same zone-class prefix (the
    text before the first ``.``), which is the share the admissibility
    rule reads: public-zone mass is a small fraction of the ship total,
    so a ship-total share could never move by the frozen threshold.
    """
    by_class = cell.get("fomite_by_class") or {}
    total_delivered = sum(
        float(b.get("delivered_gec", 0.0)) for b in by_class.values()
    )
    zone_totals: dict[str, float] = {}
    for key, bucket in by_class.items():
        zone = key.split(".", 1)[0]
        zone_totals[zone] = zone_totals.get(zone, 0.0) + float(
            bucket.get("delivered_gec", 0.0),
        )
    stats: dict[str, dict[str, float]] = {}
    for item_class, bucket in sorted(by_class.items()):
        delivered = float(bucket.get("delivered_gec", 0.0))
        calls = int(bucket.get("calls", 0))
        capped = int(bucket.get("capped_calls", 0))
        zone_total = zone_totals.get(item_class.split(".", 1)[0], 0.0)
        stats[item_class] = {
            "delivered_gec": delivered,
            "delivered_share": (
                delivered / total_delivered if total_delivered > 0.0 else 0.0
            ),
            "zone_share": (
                delivered / zone_total if zone_total > 0.0 else 0.0
            ),
            "hosts_credited": int(bucket.get("hosts_credited", 0)),
            "calls": calls,
            "capped_share": capped / calls if calls else 0.0,
        }
    return stats


def _stream_alignment(
    base_cell: dict[str, Any],
    arm_cell: dict[str, Any],
) -> dict[str, Any]:
    """Deposit/hand event streams from each cell's ``fomite_witness`` block."""
    witness_a = base_cell.get("fomite_witness", {})
    witness_d = arm_cell.get("fomite_witness", {})
    calls_a = int(witness_a.get("surface_deposit_calls", 0))
    calls_d = int(witness_d.get("surface_deposit_calls", 0))
    gec_a = float(witness_a.get("surface_mass_deposited_gec", 0.0))
    gec_d = float(witness_d.get("surface_mass_deposited_gec", 0.0))
    return {
        "deposit_calls_areal": calls_a,
        "deposit_calls_declared": calls_d,
        "deposited_gec_areal": gec_a,
        "deposited_gec_declared": gec_d,
        "hand_to_mouth_calls_areal": int(
            witness_a.get("hand_to_mouth_calls", 0),
        ),
        "hand_to_mouth_calls_declared": int(
            witness_d.get("hand_to_mouth_calls", 0),
        ),
        "deposit_events_aligned": (
            calls_a == calls_d
            and math.isclose(gec_a, gec_d, rel_tol=1e-9)
        ),
    }


def compare_seed(
    base_cell: dict[str, Any],
    arm_cell: dict[str, Any],
    focus_class: str,
) -> dict[str, Any]:
    """The frozen per-seed statistics over one (areal, declared) pair."""
    host_a = _host_delivered(base_cell)
    host_d = _host_delivered(arm_cell)
    set_a, set_d = set(host_a), set(host_d)
    union = set_a | set_d
    jaccard = len(set_a & set_d) / len(union) if union else 1.0
    classes_a = _class_stats(base_cell)
    classes_d = _class_stats(arm_cell)
    per_class = {
        item_class: {
            "delivered_share_areal": classes_a.get(
                item_class, {},
            ).get("delivered_share", 0.0),
            "delivered_share_declared": classes_d.get(
                item_class, {},
            ).get("delivered_share", 0.0),
            "zone_share_areal": classes_a.get(
                item_class, {},
            ).get("zone_share", 0.0),
            "zone_share_declared": classes_d.get(
                item_class, {},
            ).get("zone_share", 0.0),
            "hosts_credited_areal": classes_a.get(
                item_class, {},
            ).get("hosts_credited", 0),
            "hosts_credited_declared": classes_d.get(
                item_class, {},
            ).get("hosts_credited", 0),
            "capped_share_declared": classes_d.get(
                item_class, {},
            ).get("capped_share", 0.0),
        }
        for item_class in sorted(set(classes_a) | set(classes_d))
    }
    delivered_a = sum(host_a.values())
    delivered_d = sum(host_d.values())
    credited_a = float(
        base_cell.get("reconciliation", {}).get(
            "sum_credited_scaled_gec", 0.0,
        ),
    )
    credited_d = float(
        arm_cell.get("reconciliation", {}).get(
            "sum_credited_scaled_gec", 0.0,
        ),
    )
    focus_gain = (
        classes_d.get(focus_class, {}).get("zone_share", 0.0)
        - classes_a.get(focus_class, {}).get("zone_share", 0.0)
    )
    return {
        "seed": int(arm_cell["seed"]),
        **_stream_alignment(base_cell, arm_cell),
        "n_hosts_areal": len(set_a),
        "n_hosts_declared": len(set_d),
        "jaccard": jaccard,
        "gini_areal": gini(list(host_a.values())),
        "gini_declared": gini(list(host_d.values())),
        "top_decile_areal": top_decile_share(list(host_a.values())),
        "top_decile_declared": top_decile_share(list(host_d.values())),
        "per_class": per_class,
        "focus_class": focus_class,
        "focus_share_gain": focus_gain,
        "delivered_ratio": (
            delivered_d / delivered_a if delivered_a > 0.0 else None
        ),
        "credited_scaled_ratio": (
            credited_d / credited_a if credited_a > 0.0 else None
        ),
        "secondaries_delta": int(
            arm_cell.get("transmission", {}).get("secondaries", 0),
        ) - int(
            base_cell.get("transmission", {}).get("secondaries", 0),
        ),
    }


def _median_range(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"median": None, "min": None, "max": None}
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Median/[min,max] over seeds for every scalar, plus the verdict."""
    scalars = (
        "jaccard", "gini_areal", "gini_declared",
        "top_decile_areal", "top_decile_declared",
        "delivered_ratio", "credited_scaled_ratio",
        "secondaries_delta", "focus_share_gain",
        "n_hosts_areal", "n_hosts_declared",
        "deposit_calls_areal", "deposit_calls_declared",
        "hand_to_mouth_calls_areal", "hand_to_mouth_calls_declared",
    )
    summary = {
        name: _median_range(
            [float(r[name]) for r in rows if r[name] is not None],
        )
        for name in scalars
    }
    identical = all(
        row["n_hosts_areal"] == row["n_hosts_declared"]
        and math.isclose(row["jaccard"], 1.0, rel_tol=0.0, abs_tol=1e-12)
        for row in rows
    )
    gain_seeds = sum(
        1 for row in rows if row["focus_share_gain"] > FOCUS_SHARE_GAIN
    )
    cap_flags = sorted({
        item_class
        for row in rows
        for item_class, stats in row["per_class"].items()
        if stats["capped_share_declared"] > CAPPED_SHARE_FLAG
    })
    jaccard_median = summary["jaccard"]["median"]
    if identical:
        verdict = "inert"
    elif (
        jaccard_median is not None
        and jaccard_median < JACCARD_THRESHOLD
        and gain_seeds >= FOCUS_GAIN_SEEDS
    ):
        verdict = "changes_coincidence"
    else:
        verdict = "indeterminate"
    return {
        **summary,
        "identical_host_sets_all_seeds": identical,
        "focus_class_share_gain_seeds": gain_seeds,
        "cap_flags": cap_flags,
        "n_seeds_deposit_aligned": sum(
            1 for row in rows if row["deposit_events_aligned"]
        ),
        "verdict": verdict,
    }


def readout(
    arm_dir: Path, arm_tag: str, base_dir: Path, base_tag: str,
    focus_class: str,
) -> dict[str, Any]:
    """Score the frozen coincidence statistics over the shared seeds."""
    arm_cells = load_arm(arm_dir, arm_tag)
    base_cells = load_arm(base_dir, base_tag)
    seeds = sorted(set(arm_cells) & set(base_cells))
    if not seeds:
        raise SystemExit(
            f"no shared seeds between {base_dir}/{base_tag} and "
            f"{arm_dir}/{arm_tag}",
        )
    rows = [
        compare_seed(base_cells[seed], arm_cells[seed], focus_class)
        for seed in seeds
    ]
    return {
        "deliverable": "NORO-TOUCH-SHARE-01",
        "seeds": seeds,
        "seeds_only_in_arm": sorted(set(arm_cells) - set(base_cells)),
        "seeds_only_in_base": sorted(set(base_cells) - set(arm_cells)),
        "focus_class": focus_class,
        "per_seed": rows,
        "aggregate": aggregate(rows),
    }


def _print(result: dict[str, Any]) -> None:
    agg = result["aggregate"]
    print(
        f"== {result['deliverable']} coincidence: declared vs areal over "
        f"{len(result['seeds'])} paired seeds ==",
    )
    header = (
        f"  {'seed':>6} {'n_a':>5} {'n_d':>5} {'jaccard':>8} "
        f"{'gini_a':>7} {'gini_d':>7} {'top10_a':>8} {'top10_d':>8} "
        f"{'focus_gain':>10} {'dep_a':>6} {'dep_d':>6} {'aligned':>7}"
    )
    print(header)
    for row in result["per_seed"]:
        print(
            f"  {row['seed']:>6} {row['n_hosts_areal']:>5} "
            f"{row['n_hosts_declared']:>5} {row['jaccard']:>8.4f} "
            f"{row['gini_areal']:>7.4f} {row['gini_declared']:>7.4f} "
            f"{row['top_decile_areal']:>8.4f} "
            f"{row['top_decile_declared']:>8.4f} "
            f"{row['focus_share_gain']:>10.4f} "
            f"{row['deposit_calls_areal']:>6} "
            f"{row['deposit_calls_declared']:>6} "
            f"{str(row['deposit_events_aligned']):>7}",
        )
    print("aggregate (median [min, max]):")
    for name, stats in agg.items():
        if isinstance(stats, dict) and "median" in stats:
            print(
                f"  {name:24s} {stats['median']} "
                f"[{stats['min']}, {stats['max']}]",
            )
    print(
        f"identical host sets on all seeds: "
        f"{agg['identical_host_sets_all_seeds']}",
    )
    print(
        f"focus class ({result['focus_class']}) share gain > "
        f"{FOCUS_SHARE_GAIN}: {agg['focus_class_share_gain_seeds']} seeds",
    )
    print(
        f"deposit events aligned on {agg['n_seeds_deposit_aligned']}/"
        f"{len(result['per_seed'])} seeds",
    )
    if agg["cap_flags"]:
        print(f"cap flags (declared capped_share > {CAPPED_SHARE_FLAG}): "
              + ", ".join(agg["cap_flags"]))
    print(f"VERDICT: {agg['verdict']}")


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
    parser.add_argument("--arm-tag", default="per_surface_declared")
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--base-tag", default="per_surface_areal")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--focus-class", default="public.button_or_dispenser",
        help="dotted zone_class.item_class key in fomite_by_class",
    )
    args = parser.parse_args(argv)
    result = readout(
        args.arm_dir, args.arm_tag, args.base_dir, args.base_tag,
        args.focus_class,
    )
    out_dir = prepare_output_directory(
        str(args.out), allowed_roots=(str(REPO_ROOT),),
    )
    filename = resolve_child_path(
        str(out_dir), f"touch_share_coincidence_{args.arm_tag}.json",
    )
    path = _safe_path(filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(result, indent=1, sort_keys=True, default=str) + "\n",
        )
    _print(result)
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
