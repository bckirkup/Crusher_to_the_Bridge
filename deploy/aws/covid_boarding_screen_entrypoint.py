#!/usr/bin/env python3
"""AWS Batch worker for the COVID boarding-axis screen (Phase 1b).

Each array child resolves ``AWS_BATCH_JOB_ARRAY_INDEX`` against the screen
design's deterministic cell enumeration and runs ``--stride`` consecutive
cells, uploading one JSON object per cell under the caller's S3 prefix so a
reclaimed Spot child resumes and the merge (``tools/fit_covid_theta.py
screen``) pools cells, not children. Every cell is a full Diamond Princess
run, about half an hour. Same S3 conventions and job role as
``covid_hull_entrypoint.py``.
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

from covid_hull_entrypoint import (  # noqa: E402
    _already_complete,
    _array_index,
    _put_json,
    _s3_client,
    _s3_uri,
)

from picard_framework.covid_boarding_screen import (  # noqa: E402
    ScreenCell,
    enumerate_cells,
    load_design,
    run_cell,
)


def child_cells(
    cells: tuple[ScreenCell, ...], index: int, stride: int,
) -> list[ScreenCell]:
    """The block of cells that array child ``index`` owns."""
    if stride < 1:
        raise SystemExit("--stride must be at least 1")
    start = index * stride
    if index < 0 or start >= len(cells):
        children = -(-len(cells) // stride)
        raise SystemExit(f"Array index {index} outside 0..{children - 1}")
    return list(cells[start:start + stride])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stride", type=int, default=1, help="Cells per array child")
    parser.add_argument(
        "--s3-prefix",
        required=True,
        help="s3://bucket/campaign/covid_boarding_screen_v1/",
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
    cells = child_cells(enumerate_cells(design), _array_index(), args.stride)
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    for cell in cells:
        key = f"{prefix}cells/{cell.key}"
        if _already_complete(client, bucket, key):
            print(f"Already complete: s3://{bucket}/{key}", flush=True)
            continue
        payload = run_cell(design, cell)
        _put_json(client, bucket, key, payload)
        print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
