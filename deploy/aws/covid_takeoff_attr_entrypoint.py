#!/usr/bin/env python3
"""AWS Batch worker for COVID-TAKEOFF-ATTR-01 (takeoff-burn attribution).

Each array child resolves ``AWS_BATCH_JOB_ARRAY_INDEX`` against the cells of
the declared stage-2 replay restricted to ``--theta`` and ``--seeds`` — one
seed per child — runs the instrumented cell via
``tools/covid_takeoff_attribution.analyse_cell`` and uploads one JSON object
per cell under the caller's S3 prefix. A reclaimed Spot child resumes because
already-uploaded cell objects are skipped. Same S3 conventions and job role
as ``covid_boarding_screen_entrypoint.py``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
for path in (str(_REPO_ROOT), str(_HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from covid_boarding_screen_entrypoint import child_cells  # noqa: E402
from covid_hull_entrypoint import (  # noqa: E402
    _already_complete,
    _array_index,
    _put_json,
    _s3_client,
    _s3_uri,
)

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from tools.covid_takeoff_attribution import analyse_cell  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stride", type=int, default=1, help="Cells per array child",
    )
    parser.add_argument(
        "--index-offset",
        type=int,
        default=0,
        help="Added to AWS_BATCH_JOB_ARRAY_INDEX before resolving the block",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=None,
        help="Array index override for a single-job canary "
             "(AWS_BATCH_JOB_ARRAY_INDEX is reserved and cannot be set "
             "through container overrides)",
    )
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument(
        "--seeds",
        default=None,
        help="Comma-separated seed list; default all seeds in the design",
    )
    parser.add_argument(
        "--s3-prefix",
        required=True,
        help="s3://bucket/campaign/covid_takeoff_attr_v1/<sha>/",
    )
    parser.add_argument(
        "--design",
        default=None,
        help="Design JSON, relative to the repository root",
    )
    args = parser.parse_args()

    design = load_design(
        str(_REPO_ROOT / args.design) if args.design else None,
    )
    cells = [
        c for c in enumerate_cells(design)
        if abs(c.theta - args.theta) < args.theta * 0.001
    ]
    if args.seeds:
        wanted = {int(s) for s in args.seeds.split(",")}
        cells = [c for c in cells if c.seed in wanted]
    if not cells:
        raise SystemExit(
            f"no cells at theta={args.theta} seeds={args.seeds}",
        )
    index = args.index if args.index is not None else _array_index()
    block = child_cells(
        tuple(cells), index, args.stride, args.index_offset,
    )
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    repo_root = str(_REPO_ROOT)
    for cell in block:
        key = f"{prefix}cells/{cell.key}"
        if _already_complete(client, bucket, key):
            print(f"Already complete: s3://{bucket}/{key}", flush=True)
            continue
        payload = analyse_cell(design, cell, num_epochs=None,
                               repo_root=repo_root)
        _put_json(client, bucket, key, payload)
        print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
