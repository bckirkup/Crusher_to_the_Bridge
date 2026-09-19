#!/usr/bin/env python3
"""Readout for the NORO-SUSCEPT-03 swept-alpha cells.

Aggregation only: this script reads the per-cell ``*.json.gz`` dumps written by
``per_host_dose_challenge.py --alpha ...`` and never re-runs or re-derives a
measurement. It emits three things:

* a markdown table, one row per (alpha, seed), with the frozen readout columns;
* the frozen reconciliation gate: ``sum_credited_scaled_gec``,
  ``sum_dose_read_at_challenge_gec`` and ``sum_effective_dose_evaluated_gec``
  must agree to a relative difference <= 1e-9 in every run;
* the frozen RNG-alignment check: at a fixed seed, ``emesis_witness`` and
  ``fomite_witness`` must be identical across all alpha cells;

plus a compact ``sweep_cells`` JSON carrying every summary field except the
per-host table and the top-host epoch rows, and the -02 section-e emesis
counters per seed for the record.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
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

RECONCILIATION_RTOL = 1e-9
CELL_RE = re.compile(
    r"per_host_dose_challenge_a(?P<alpha>[0-9.]+)_seed(?P<seed>\d+)\.json\.gz",
)

COLUMNS = (
    ("alpha", "alpha"),
    ("seed", "seed"),
    ("alpha_resolved", "dose_response_resolved.alpha_resolved"),
    ("secondaries", "transmission.secondaries"),
    ("ever_infected", "transmission.ever_infected"),
    ("imports", "transmission.imports"),
    ("attack_rate", "transmission.attack_rate"),
    ("sum_evaluated_hazard", "reconciliation.sum_evaluated_hazard"),
    ("sum_credited_scaled_gec", "reconciliation.sum_credited_scaled_gec"),
    ("frailty_median", "frailty_drawn.median"),
    ("hosts_for_90pct", "concentration.hosts_for_90pct"),
)


def _dig(summary: dict[str, Any], dotted: str) -> Any:
    value: Any = summary
    for key in dotted.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def load_cells(raw_dir: Path) -> list[dict[str, Any]]:
    """Load every per-cell dump, tagged with its alpha and seed."""
    cells = []
    for path in sorted(raw_dir.glob("per_host_dose_challenge_a*.json.gz")):
        match = CELL_RE.fullmatch(path.name)
        if match is None:
            continue
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            summary = json.load(handle)
        summary["alpha"] = float(match.group("alpha"))
        cells.append(summary)
    return sorted(cells, key=lambda s: (s["alpha"], s["seed"]))


def markdown_table(cells: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(name for name, _ in COLUMNS) + " |"
    rule = "|" + "---|" * len(COLUMNS)
    rows = []
    for summary in cells:
        rows.append(
            "| " + " | ".join(
                str(_dig(summary, dotted)) for _, dotted in COLUMNS
            ) + " |",
        )
    return "\n".join([header, rule, *rows])


def reconciliation_gate(cells: list[dict[str, Any]]) -> tuple[float, bool]:
    """The frozen gate: the three dose sums agree to <= 1e-9 relative."""
    worst = 0.0
    all_ok = True
    for summary in cells:
        chain = summary["reconciliation"]
        credited = float(chain["sum_credited_scaled_gec"])
        worst_cell = 0.0
        for key in (
            "sum_dose_read_at_challenge_gec",
            "sum_effective_dose_evaluated_gec",
        ):
            diff = abs(float(chain[key]) - credited)
            rel = diff / credited if credited else float("inf")
            worst_cell = max(worst_cell, rel)
        worst = max(worst, worst_cell)
        ok = worst_cell <= RECONCILIATION_RTOL
        all_ok = all_ok and ok
        print(
            f"  alpha={summary['alpha']:.4f} seed={summary['seed']}: "
            f"worst rel diff {worst_cell:.3e} -> {'PASS' if ok else 'FAIL'}",
        )
    return worst, all_ok


def rng_alignment(cells: list[dict[str, Any]]) -> bool:
    """At a fixed seed the emesis/fomite witnesses must not move with alpha."""
    identical = True
    seeds = sorted({s["seed"] for s in cells})
    for seed in seeds:
        group = [s for s in cells if s["seed"] == seed]
        for witness_key in ("emesis_witness", "fomite_witness"):
            counters = sorted(
                {k for s in group for k in s[witness_key]},
            )
            differing = [
                c for c in counters
                if len({s[witness_key].get(c) for s in group}) > 1
            ]
            if not differing:
                print(f"  seed {seed}: {witness_key} identical across alpha")
                continue
            identical = False
            for counter in differing:
                per_alpha = {
                    f"{s['alpha']:.4f}": s[witness_key].get(counter)
                    for s in group
                }
                print(
                    f"  seed {seed}: {witness_key}.{counter} DIFFERS: "
                    f"{per_alpha}",
                )
    return identical


def cell_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """The full dump minus the hosts table and the top-host epoch rows."""
    return {
        key: value for key, value in summary.items()
        if key not in ("hosts", "top_host_epoch_rows")
    }


def print_emesis_record(cells: list[dict[str, Any]]) -> None:
    """The -02 section-e counters, per seed, for the record only."""
    seeds = sorted({s["seed"] for s in cells})
    for seed in seeds:
        group = [s for s in cells if s["seed"] == seed]
        first = group[0]
        witness = first["emesis_witness"]
        units = first["emesis_unit_names"]
        print(
            f"  seed {seed}: scheduled_episodes="
            f"{witness.get('scheduled_episodes')} "
            f"emesis_events={witness.get('emesis_events')} "
            f"(identical across alpha: "
            f"{all(s['emesis_witness'] == witness for s in group)})",
        )
        print(f"  seed {seed}: emesis_unit_names={units}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_suscept_03/raw",
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_suscept_03",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cells = load_cells(args.raw_dir)
    print(f"loaded {len(cells)} cells from {args.raw_dir}")
    print()
    print(markdown_table(cells))
    print()
    print("reconciliation gate (rtol 1e-9):")
    worst, gate_ok = reconciliation_gate(cells)
    print(f"  worst relative difference: {worst:.3e}")
    print(f"  verdict: {'PASS' if gate_ok else 'FAIL'}")
    print()
    print("RNG-stream alignment:")
    aligned = rng_alignment(cells)
    print(f"  verdict: {'IDENTICAL' if aligned else 'DIFFERS'}")
    print()
    print("emesis counters for the record (-02 section e):")
    print_emesis_record(cells)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    path = resolve_child_path(str(out_dir), "sweep_cells.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "cells": [cell_summary(s) for s in cells],
                "reconciliation": {
                    "rtol": RECONCILIATION_RTOL,
                    "worst_relative_difference": worst,
                    "verdict": "PASS" if gate_ok else "FAIL",
                },
                "rng_alignment_identical": aligned,
            },
            handle,
            indent=1,
        )
    print(f"\nwritten: {path}")
    return 0 if gate_ok and aligned else 1


if __name__ == "__main__":
    raise SystemExit(main())
