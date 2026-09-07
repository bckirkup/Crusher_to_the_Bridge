"""Stopping rules for a staged, class-mixed posting campaign.

A cell is one Sobol' point on one hull. Each stage adds a block of *new*
voyages to a cell (a fresh ``--seed-base``, so no seed is ever counted twice)
and this readout pools every stage's rows into one Beta-Binomial posterior per
cell on its posting rate, against A9's target band. A cell stops when the
posterior has settled on one side of the band; it continues while the band is
still a live possibility. Nothing here estimates a parameter of the model: the
posterior is on the frequency a fixed cell exhibits, and the rule only decides
where the next voyages are spent.

The prior is Jeffreys' Beta(1/2, 1/2). The decision thresholds are stated,
not tuned: a cell stops once 95% of its posterior mass lies above (or below)
the band. Both posting rules are scored -- the or-rule the in-sim trigger
fires on and the passenger channel A9's numerators actually count -- and a
cell continues if *either* is undecided, so a stop is never bought by the
channel that happened to settle first.

    python3 -m telemetry_buffer.observation_model.staged_posting_readout \\
        --rows s3sync/classmix_stage1/*/region/*.jsonl \\
        --out telemetry_buffer/observation_model/classmix_stage1_readout.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from scipy.stats import beta

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parents[2]

# A9's target: postings per eligible voyage, MMWR 2006-2019 (see the anchor
# register); the band is what the stopping rule is scored against.
A9_BAND: tuple[float, float] = (0.0042, 0.0056)
JEFFREYS: tuple[float, float] = (0.5, 0.5)
STOP_MASS = 0.95
# MIDRS eligibility, as ``score_anchors._a9_eligible_rows`` applies it.
MIN_PASSENGERS = 100
VOYAGE_DAYS: tuple[float, float] = (3.0, 21.0)

CHANNELS: tuple[str, ...] = ("or_rule", "passenger")
CONTINUE = "continue"
STOP_ABOVE = "stop_above"
STOP_BELOW = "stop_below"


def posted_or_rule(row: dict[str, Any]) -> bool:
    """The in-sim trigger: either complement reaches the threshold."""
    return (
        row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
        or row["reported_case_attack_rate_crew"] >= A9_POSTING_THRESHOLD
    )


def posted_passenger(row: dict[str, Any]) -> bool:
    """A9's numerator: the passenger complement reaches the threshold."""
    return row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD


def eligible(row: dict[str, Any]) -> bool:
    return (
        row["passenger_complement"] >= MIN_PASSENGERS
        and VOYAGE_DAYS[0] <= row["voyage_days"] <= VOYAGE_DAYS[1]
    )


def band_mass(
    k: int,
    n: int,
    band: tuple[float, float] = A9_BAND,
    prior: tuple[float, float] = JEFFREYS,
) -> dict[str, float]:
    """Posterior mass below, inside and above the band for k of n postings."""
    a, b = prior[0] + k, prior[1] + (n - k)
    below = float(beta.cdf(band[0], a, b))
    above = float(beta.sf(band[1], a, b))
    return {
        "below": below,
        "inside": max(0.0, 1.0 - below - above),
        "above": above,
        "mean": a / (a + b),
    }


def decision(mass: dict[str, float], stop_mass: float = STOP_MASS) -> str:
    if mass["above"] >= stop_mass:
        return STOP_ABOVE
    if mass["below"] >= stop_mass:
        return STOP_BELOW
    return CONTINUE


def _read_rows(path: Path) -> Iterable[dict[str, Any]]:
    resolved = Path(resolve_repo_path(str(REPO_ROOT), str(path)))
    with validated_open(
        str(resolved), allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            for row in record.get("rows", []):
                yield {**row, "point_index": int(record["point_index"])}


def pool_cells(paths: Sequence[Path]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    """Rows by (hull, point), refusing a voyage that arrives twice.

    Stages are pooled by seed, not by block index: two stages both number
    their blocks from zero, so the only identity a voyage has across stages is
    its seed, and a repeated seed is a stage submitted twice, not more data.
    """
    cells: dict[tuple[str, int], dict[int, dict[str, Any]]] = defaultdict(dict)
    for path in paths:
        for row in _read_rows(path):
            key = (str(row["hull"]), int(row["point_index"]))
            seed = int(row["seed"])
            if seed in cells[key]:
                raise SystemExit(
                    f"{key[0]} point {key[1]} seed {seed} appears twice: a "
                    "stage was pooled twice or its --seed-base overlaps",
                )
            cells[key][seed] = row
    return {
        key: [by_seed[seed] for seed in sorted(by_seed)]
        for key, by_seed in sorted(cells.items())
    }


def score_cell(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """One cell's counts, posteriors and decision, both channels."""
    voyages = [row for row in rows if eligible(row)]
    n = len(voyages)
    counts = {
        "or_rule": sum(posted_or_rule(row) for row in voyages),
        "passenger": sum(posted_passenger(row) for row in voyages),
    }
    channels = {}
    for channel in CHANNELS:
        mass = band_mass(counts[channel], n)
        channels[channel] = {
            "posted": counts[channel],
            **mass,
            "decision": decision(mass),
        }
    decisions = {channels[channel]["decision"] for channel in CHANNELS}
    return {
        "eligible_runs": n,
        "seeds": [int(row["seed"]) for row in rows],
        "channels": channels,
        # Continue if any channel is undecided; a stop needs both settled.
        "decision": (
            CONTINUE if CONTINUE in decisions
            else STOP_ABOVE if decisions == {STOP_ABOVE}
            else STOP_BELOW if decisions == {STOP_BELOW}
            else CONTINUE
        ),
    }


def next_stage(cells: dict[str, dict[int, dict[str, Any]]]) -> dict[str, Any]:
    """Per hull: the points still undecided, and where their seeds resume.

    The next block is as large as the cell so far (a doubling), and starts
    one past the largest seed any cell on the hull has used, so a stage's
    ``--seed-base`` is one number per hull and no voyage repeats.
    """
    plan: dict[str, Any] = {}
    for hull, points in cells.items():
        continuing = sorted(
            index for index, cell in points.items() if cell["decision"] == CONTINUE
        )
        used = [seed for cell in points.values() for seed in cell["seeds"]]
        sizes = {len(points[index]["seeds"]) for index in continuing}
        plan[hull] = {
            "only_points": continuing,
            "seed_base": (max(used) + 1) if used else None,
            "seeds": max(sizes) if sizes else 0,
        }
    return plan


def readout(paths: Sequence[Path]) -> dict[str, Any]:
    pooled = pool_cells(paths)
    cells: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for (hull, index), rows in pooled.items():
        cells[hull][index] = score_cell(rows)
    return {
        "mode": "staged_posting_readout",
        "a9_band": list(A9_BAND),
        "prior": {"family": "beta", "a": JEFFREYS[0], "b": JEFFREYS[1]},
        "stop_mass": STOP_MASS,
        "cells": {hull: dict(sorted(points.items())) for hull, points in cells.items()},
        "next_stage": next_stage(cells),
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        "| hull | point | n | posted (or / pax) | P(below) | P(in band) | P(above) | decision |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for hull, points in report["cells"].items():
        for index, cell in points.items():
            pax = cell["channels"]["passenger"]
            lines.append(
                f"| {hull} | {index} | {cell['eligible_runs']} | "
                f"{cell['channels']['or_rule']['posted']} / {pax['posted']} | "
                f"{pax['below']:.3f} | {pax['inside']:.3f} | {pax['above']:.3f} | "
                f"{cell['decision']} |",
            )
    lines.append("")
    lines.append("Posterior columns are the passenger channel; decision needs both.")
    for hull, plan in report["next_stage"].items():
        lines.append(
            f"{hull}: continue {len(plan['only_points'])} point(s) "
            f"{plan['only_points']} at --seed-base {plan['seed_base']} "
            f"x {plan['seeds']} seeds",
        )
    return "\n".join(lines)


def _write(path: Path, report: dict[str, Any]) -> None:
    resolved = Path(resolve_repo_path(str(REPO_ROOT), str(path)))
    with validated_open(
        str(resolved), "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(report, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    report = readout(args.rows)
    print(render(report))
    if args.out is not None:
        _write(args.out, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
