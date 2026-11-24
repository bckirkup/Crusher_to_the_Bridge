#!/usr/bin/env python3
"""DP-PARTICIPATION-01 diagnostic: when the index's founder yield lands.

Pure readout over existing campaign cell payloads (sync the S3 blocks
into a directory inside the checkout first). For every cell it reads the ``seed_ring``
echo and reports, per theta, the aboard-window acquisitions by day index
(0 = embarkation day) and by route, the share falling on day 0, and
whether the index was shedding at boarding
(``index_shedding_at_day0``). It runs no simulation.

Every ``cell_*.json`` under ``--cells`` is pooled, so sync only the blocks
that belong to the grid being read (a campaign prefix may also hold pilot
blocks at other thetas).

Usage:
    python3 tools/covid_dp_participation_diag.py --cells <dir> [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

FOUNDER_CLASS_MIN = 10


def cell_row(payload: dict) -> dict:
    ring = payload.get("seed_ring") or {}
    return {
        "theta": payload["cell"]["theta"],
        "seed": payload["cell"]["seed"],
        "founders": int(ring.get("aboard_window_acquisitions") or 0),
        "by_day": {
            int(k): int(v)
            for k, v in (ring.get("aboard_window_by_day") or {}).items()
        },
        "by_route": dict(ring.get("aboard_window_by_route") or {}),
        "index_shedding_at_day0": payload.get("index_shedding_at_day0"),
        "index_onset_day": payload.get("index_onset_day"),
        "index_departed_epoch": payload.get("index_departed_epoch"),
    }


def summarize(rows: list[dict]) -> dict:
    by_day: Counter = Counter()
    by_route: Counter = Counter()
    class_by_route: Counter = Counter()
    for row in rows:
        by_day.update(row["by_day"])
        by_route.update(row["by_route"])
        if row["founders"] >= FOUNDER_CLASS_MIN:
            class_by_route.update(row["by_route"])
    total = sum(by_day.values())
    return {
        "cells": len(rows),
        "founder_class_cells": sum(
            row["founders"] >= FOUNDER_CLASS_MIN for row in rows
        ),
        "acquisitions": total,
        "by_day": dict(sorted(by_day.items())),
        "day0_acquisitions": by_day.get(0, 0),
        "day0_share": (by_day.get(0, 0) / total) if total else None,
        "by_route": dict(by_route),
        "founder_class_by_route": dict(class_by_route),
        "index_shedding_at_day0_cells": sum(
            row["index_shedding_at_day0"] is True for row in rows
        ),
    }


def build(rows: list[dict]) -> dict:
    thetas = sorted({row["theta"] for row in rows})
    return {
        "pooled": summarize(rows),
        "by_theta": {
            f"{theta:.3g}": summarize([r for r in rows if r["theta"] == theta])
            for theta in thetas
        },
        "cells": sorted(rows, key=lambda r: (r["theta"], r["seed"])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cells", required=True, help="directory of cell JSONs")
    parser.add_argument("--out", help="write the full JSON readout here")
    args = parser.parse_args(argv)
    root = str(_REPO_ROOT)
    cells_dir = Path(resolve_repo_path(root, args.cells))
    paths = sorted(cells_dir.rglob("cell_*.json"))
    if not paths:
        print(f"no cell_*.json under {args.cells}", file=sys.stderr)
        return 1
    rows = []
    for path in paths:
        with validated_open(
            str(path), "r", allowed_roots=(root,), encoding="utf-8",
        ) as handle:
            rows.append(cell_row(json.load(handle)))
    result = build(rows)
    if args.out:
        out_path = resolve_repo_path(root, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(root,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {k: v for k, v in result.items() if k != "cells"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
