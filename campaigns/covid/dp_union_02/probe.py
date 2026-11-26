#!/usr/bin/env python3
"""DP-UNION-02 boarding-emission ascertainment probe.

Runs zero-epoch cells over a predeclared candidate seed sequence and selects
the first N seeds whose index actually emits at boarding. The probe reads no
outcome observable: selection is only the COVID-SEED-ASCERTAIN-01 event-class
condition, never attack, onset, founder, testing, or capture output.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKER = _REPO_ROOT / "campaigns/covid/dp_union_01/cell.py"


def candidate_dates(start: str, count: int) -> list[int]:
    """Calendar-date integer seeds in a fixed sequence."""
    year, month, day = int(start[:4]), int(start[4:6]), int(start[6:8])
    first = date(year, month, day)
    return [
        int((first + timedelta(days=offset)).strftime("%Y%m%d"))
        for offset in range(count)
    ]


def _run_candidate(
    seed: int,
    design: str,
    theta: float,
    arm: str,
    cells_dir: Path,
) -> dict[str, Any]:
    """Run one zero-epoch cell and read only its boarding-emission bit."""
    command = [
        sys.executable, str(_WORKER),
        "--design", design,
        "--theta", str(theta),
        "--arm", arm,
        "--seed", str(seed),
        "--out", str(cells_dir),
        "--num-epochs", "0",
    ]
    completed = subprocess.run(
        command, cwd=_REPO_ROOT, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"probe cell {seed} failed:\n{completed.stdout}\n{completed.stderr}",
        )
    artifact = cells_dir / f"cell_{seed}.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    return {
        "seed": seed,
        "index_shedding_at_day0": payload.get("index_shedding_at_day0"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True)
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument("--arm", default="union_niid")
    parser.add_argument("--start-date", default="20200205")
    parser.add_argument("--candidate-days", type=int, default=360)
    parser.add_argument("--select", type=int, default=24)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    candidates = candidate_dates(args.start_date, args.candidate_days)
    out_dir = Path(args.out)
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    design_path = _REPO_ROOT / args.design
    design_sha = hashlib.sha256(design_path.read_bytes()).hexdigest()

    # The frozen scored design contains only the already-selected cohort.
    # Selection itself needs a candidate design whose explicit seed axis is
    # the whole predeclared sequence; derive that probe-only design here so
    # the measurement remains rerunnable after the scored cohort is frozen.
    raw_design = json.loads(design_path.read_text(encoding="utf-8"))
    raw_design["seeds"] = len(candidates)
    raw_design["seed_values"] = candidates
    raw_design["cells"] = (
        len(candidates) * len(raw_design.get("thetas", []))
        * len(raw_design.get("infection_age_days", []))
        * len(raw_design.get("imports", []))
        * len(raw_design.get("arms", []))
    )
    probe_design_path = (
        _REPO_ROOT / "out" / "dp_union_02_probe"
        / f"probe_design_{design_sha[:12]}_{args.start_date}_{len(candidates)}.json"
    )
    probe_design_path.parent.mkdir(parents=True, exist_ok=True)
    probe_design_path.write_text(
        json.dumps(raw_design, indent=2) + "\n", encoding="utf-8",
    )
    probe_design = str(probe_design_path)

    rows: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(
                _run_candidate, seed, probe_design, args.theta, args.arm, cells_dir,
            ): seed
            for seed in candidates
        }
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: candidates.index(row["seed"]))
    positive = [row["seed"] for row in rows if row["index_shedding_at_day0"] is True]
    selected = positive[:args.select]
    if len(selected) < args.select:
        raise SystemExit(
            f"only {len(selected)} positive seeds in {len(candidates)} candidates; "
            "extend the predeclared candidate sequence before selecting",
        )
    payload = {
        "task_id": "DP-UNION-02-ASCERTAINMENT-PROBE",
        "design": args.design,
        "design_sha256": design_sha,
        "theta": args.theta,
        "arm": args.arm,
        "selection_rule": (
            "first 24 seeds in the predeclared calendar-date candidate sequence "
            "whose zero-epoch payload has index_shedding_at_day0 true; no outcome "
            "observable read"
        ),
        "start_date": int(args.start_date),
        "candidate_days": args.candidate_days,
        "candidate_count": len(candidates),
        "positive_count": len(positive),
        "selected_seeds": selected,
        "positive_seeds": positive,
        "rows": rows,
    }
    destination = out_dir / "ascertainment_probe.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {destination}")
    print(f"positive {len(positive)}/{len(candidates)}; selected {selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
