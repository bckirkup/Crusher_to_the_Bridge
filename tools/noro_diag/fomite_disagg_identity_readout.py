#!/usr/bin/env python3
"""Readout for the NORO-FOMITE-DISAGG-01 neutrality identity block.

Aggregation only: reads the per-seed ``*.json.gz`` dumps that
``per_host_dose_challenge.py`` wrote for the two arms -- ``pooled`` and
``per_surface`` with ``areal`` touch shares over the ``shipped`` area
basis -- and scores the identity statistics and tolerances the ledger
(``docs/ledger/NORO-FOMITE-DISAGG-01.md`` §2) froze before the block ran.
It re-derives nothing, fits nothing and changes no constant.

The gate is an identity, not a comparison: under a uniform areal density
the per-class arithmetic sums term by term to the pooled arithmetic, so a
seed outside tolerance is an implementation defect (spec §3.4), never a
model difference. Every dose statistic below is a paired ratio against a
withdrawn baseline (``docs/norovirus/norovirus_open_ledger.md`` §1) and is
relative/derived -- never a dose result.

Swab density and emesis patch area are covered by the unit identity tests
(``tests/test_fomite_per_surface.py``), not here: both are deterministic
functions of the zone roll-up, so a whole-voyage dump adds nothing.

Runtime is reported as the paired ``per_surface / pooled`` ratio of the
in-engine run wall clock, against the 1.5-4x envelope of the proposal §4.
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

RELATIVE_TOLERANCE = 1.0e-9
RUNTIME_ENVELOPE = (1.5, 4.0)

# (dotted path, exact?) -- "exact" statistics are integer counts that an
# identity must reproduce bit for bit; the rest are floats compared as a
# relative deviation against ``RELATIVE_TOLERANCE``.
STATISTICS: tuple[tuple[str, bool], ...] = (
    ("reconciliation.sum_credited_raw_gec", False),
    ("reconciliation.sum_credited_scaled_gec", False),
    ("reconciliation.sum_dose_read_at_challenge_gec", False),
    ("reconciliation.sum_effective_dose_evaluated_gec", False),
    ("reconciliation.sum_evaluated_hazard", False),
    ("fomite_witness.surface_deposit_calls", True),
    ("fomite_witness.surface_mass_deposited_gec", False),
    ("fomite_witness.deliver_calls", True),
    ("fomite_witness.mass_delivered_to_hands_gec", False),
    ("fomite_witness.hand_to_mouth_calls", True),
    ("fomite_witness.hand_load_seen_gec", False),
    ("fomite_witness.hand_to_mouth_dose_gec", False),
    ("joint.hosts_credited_any_dose", True),
    ("transmission.secondaries", True),
    ("transmission.imports", True),
    ("transmission.attack_rate", True),
)


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


def _dig(cell: dict[str, Any], dotted: str) -> float | None:
    node: Any = cell
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return float(node) if isinstance(node, (int, float)) else None


def _relative_deviation(arm: float, base: float) -> float:
    if arm == base:
        return 0.0
    scale = max(abs(arm), abs(base))
    return abs(arm - base) / scale if scale > 0.0 else math.inf


def compare_statistic(
    dotted: str,
    exact: bool,
    arm_cells: dict[int, dict[str, Any]],
    base_cells: dict[int, dict[str, Any]],
    seeds: list[int],
) -> dict[str, Any]:
    """One frozen statistic across the shared seeds."""
    deviations: dict[int, float] = {}
    absent_both: list[int] = []
    absent_one: list[int] = []
    for seed in seeds:
        arm = _dig(arm_cells[seed], dotted)
        base = _dig(base_cells[seed], dotted)
        if arm is None and base is None:
            absent_both.append(seed)
            continue
        if arm is None or base is None:
            absent_one.append(seed)
            continue
        deviations[seed] = _relative_deviation(arm, base)
    tolerance = 0.0 if exact else RELATIVE_TOLERANCE
    outside = sorted(
        seed for seed, dev in deviations.items() if dev > tolerance
    )
    worst = max(deviations.items(), key=lambda kv: kv[1], default=None)
    return {
        "statistic": dotted,
        "comparison": "exact" if exact else f"rel <= {RELATIVE_TOLERANCE:g}",
        "seeds_compared": len(deviations),
        "seeds_absent_in_both_arms": absent_both,
        "seeds_absent_in_one_arm": absent_one,
        "max_relative_deviation": worst[1] if worst else None,
        "max_deviation_seed": worst[0] if worst else None,
        "seeds_outside_tolerance": outside,
        "verdict": (
            "identity"
            if not outside and not absent_one and (deviations or absent_both)
            else "DEFECT"
        ),
    }


def compare_host_doses(
    arm_cells: dict[int, dict[str, Any]],
    base_cells: dict[int, dict[str, Any]],
    seeds: list[int],
) -> dict[str, Any]:
    """The per-host credited dose vector, host by host, per seed."""
    worst_dev = 0.0
    worst_seed: int | None = None
    mismatched_rosters = []
    outside = []
    for seed in seeds:
        arm = {
            int(h["agent_id"]): float(h["credited_scaled_gec"])
            for h in arm_cells[seed]["hosts"]
        }
        base = {
            int(h["agent_id"]): float(h["credited_scaled_gec"])
            for h in base_cells[seed]["hosts"]
        }
        if set(arm) != set(base):
            mismatched_rosters.append(seed)
            continue
        seed_dev = max(
            (_relative_deviation(arm[k], base[k]) for k in arm), default=0.0,
        )
        if seed_dev > RELATIVE_TOLERANCE:
            outside.append(seed)
        if seed_dev > worst_dev:
            worst_dev, worst_seed = seed_dev, seed
    return {
        "statistic": "hosts[].credited_scaled_gec",
        "comparison": f"rel <= {RELATIVE_TOLERANCE:g}, host by host",
        "seeds_compared": len(seeds) - len(mismatched_rosters),
        "seeds_with_different_host_rosters": mismatched_rosters,
        "max_relative_deviation": worst_dev,
        "max_deviation_seed": worst_seed,
        "seeds_outside_tolerance": outside,
        "verdict": (
            "identity" if not outside and not mismatched_rosters else "DEFECT"
        ),
    }


def _wall_clock(cell: dict[str, Any]) -> float | None:
    value = cell.get("wall_clock_seconds_run")
    return float(value) if isinstance(value, (int, float)) else None


def runtime_ratio(
    arm_cells: dict[int, dict[str, Any]],
    base_cells: dict[int, dict[str, Any]],
    seeds: list[int],
) -> dict[str, Any]:
    """Paired per_surface/pooled run wall clock against the §4 envelope."""
    ratios = {}
    for seed in seeds:
        arm = _wall_clock(arm_cells[seed])
        base = _wall_clock(base_cells[seed])
        if arm is None or base is None or base <= 0.0:
            continue
        ratios[seed] = arm / base
    if not ratios:
        return {"seeds": 0, "verdict": "not recorded"}
    values = sorted(ratios.values())
    median = statistics.median(values)
    low, high = RUNTIME_ENVELOPE
    if median > high:
        verdict = "above envelope"
    elif low <= median:
        verdict = "inside envelope"
    else:
        verdict = "below envelope"
    return {
        "seeds": len(values),
        "median_ratio": median,
        "min_ratio": values[0],
        "max_ratio": values[-1],
        "envelope": list(RUNTIME_ENVELOPE),
        "sum_seconds_per_surface": sum(
            _wall_clock(arm_cells[s]) or 0.0 for s in ratios
        ),
        "sum_seconds_pooled": sum(
            _wall_clock(base_cells[s]) or 0.0 for s in ratios
        ),
        "verdict": verdict,
    }


def _arm_labels(cells: dict[int, dict[str, Any]]) -> dict[str, Any]:
    sample = next(iter(cells.values()))
    return {
        "seeds": sorted(cells),
        "epochs": sample.get("epochs"),
        "platform": sample.get("platform"),
        "num_agents": sample.get("num_agents"),
        "arm_tag": sample.get("arm_tag"),
        "fomite_representation": sample.get("fomite_representation"),
        "fomite_representation_resolved": sample.get(
            "fomite_representation_resolved",
        ),
    }


def readout(
    arm_dir: Path, arm_tag: str, base_dir: Path, base_tag: str,
) -> dict[str, Any]:
    """Score the frozen identity statistics over the shared seeds."""
    arm_cells = load_arm(arm_dir, arm_tag)
    base_cells = load_arm(base_dir, base_tag)
    seeds = sorted(set(arm_cells) & set(base_cells))
    if not seeds:
        raise SystemExit(
            f"no shared seeds between {arm_dir}/{arm_tag} and "
            f"{base_dir}/{base_tag}",
        )
    comparisons = [
        compare_statistic(dotted, exact, arm_cells, base_cells, seeds)
        for dotted, exact in STATISTICS
    ]
    comparisons.append(compare_host_doses(arm_cells, base_cells, seeds))
    defects = [c["statistic"] for c in comparisons if c["verdict"] != "identity"]
    return {
        "deliverable": "NORO-FOMITE-DISAGG-01",
        "seeds": seeds,
        "seeds_only_in_arm": sorted(set(arm_cells) - set(base_cells)),
        "seeds_only_in_base": sorted(set(base_cells) - set(arm_cells)),
        "arm": _arm_labels(arm_cells),
        "base": _arm_labels(base_cells),
        "relative_tolerance": RELATIVE_TOLERANCE,
        "comparisons": comparisons,
        "statistics_outside_tolerance": defects,
        "identity_verdict": "holds" if not defects else "DEFECT",
        "runtime": runtime_ratio(arm_cells, base_cells, seeds),
    }


def _print(result: dict[str, Any]) -> None:
    print(
        f"== {result['deliverable']} identity: "
        f"{result['arm']['fomite_representation']} vs "
        f"{result['base']['fomite_representation']} over "
        f"{len(result['seeds'])} paired seeds "
        f"({result['arm']['epochs']} epochs, {result['arm']['platform']}, "
        f"{result['arm']['num_agents']} agents) ==",
    )
    for row in result["comparisons"]:
        dev = row["max_relative_deviation"]
        silent = len(row.get("seeds_absent_in_both_arms", ()))
        note = f", {silent} seeds never fired it" if silent else ""
        print(
            f"  {row['statistic']:48s} {row['comparison']:22s} "
            f"worst {dev if dev is None else format(dev, '.3e')} "
            f"(seed {row['max_deviation_seed']}{note})  -> {row['verdict']}",
        )
    runtime = result["runtime"]
    if runtime.get("seeds"):
        print(
            f"runtime per_surface/pooled: median {runtime['median_ratio']:.3f} "
            f"[{runtime['min_ratio']:.3f}, {runtime['max_ratio']:.3f}] "
            f"vs envelope {runtime['envelope']}  -> {runtime['verdict']}",
        )
    print(f"IDENTITY: {result['identity_verdict']}")
    if result["statistics_outside_tolerance"]:
        print(
            "  outside tolerance: "
            + ", ".join(result["statistics_outside_tolerance"]),
        )


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
    parser.add_argument("--arm-tag", default="per_surface_areal")
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--base-tag", default="pooled")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = readout(
        args.arm_dir, args.arm_tag, args.base_dir, args.base_tag,
    )
    out_dir = prepare_output_directory(
        str(args.out), allowed_roots=(str(REPO_ROOT),),
    )
    filename = resolve_child_path(
        str(out_dir), f"fomite_disagg_identity_{args.arm_tag}.json",
    )
    path = _safe_path(filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(result, indent=1, sort_keys=True, default=str) + "\n",
        )
    _print(result)
    print(f"\nwritten: {path}")
    return 0 if result["identity_verdict"] == "holds" else 1


if __name__ == "__main__":
    raise SystemExit(main())
