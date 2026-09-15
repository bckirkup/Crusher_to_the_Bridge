#!/usr/bin/env python3
"""AWS Batch worker for the replicated COVID first look (covid_first_look_v1).

Each array child resolves ``AWS_BATCH_JOB_ARRAY_INDEX`` against the design's
deterministic cell enumeration, restricted to one phase, and runs a block of
``--stride`` consecutive cells. Every cell uploads its own JSON object under
the caller's S3 prefix, so a reclaimed Spot child resumes where it stopped and
the merge (``tools/fit_covid_theta.py merge``) pools cells, not children.

A training cell on the Diamond Princess hull runs about half an hour; a
held-out Greg Mortimer cell runs in seconds, which is why the held-out phase
is submitted with a stride of a whole seed set. The container uses only its
ambient Batch job-role credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_first_look import (  # noqa: E402
    PHASES,
    Cell,
    enumerate_cells,
    load_design,
    run_cell,
)

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-")


def _s3_uri(raw: str) -> tuple[str, str]:
    parsed = urlparse(raw)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    if parsed.scheme != "s3" or not bucket or any(char not in _BUCKET_CHARS for char in bucket):
        raise SystemExit(f"Invalid S3 URI: {raw!r}")
    if any(char not in _KEY_CHARS for char in key):
        raise SystemExit(f"Invalid S3 key: {key!r}")
    return bucket, key.rstrip("/")


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("boto3 is required in the Batch image") from exc
    return boto3.client("s3")


def _array_index() -> int:
    raw = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw is None:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX is required")
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be an integer") from exc


def child_cells(cells: tuple[Cell, ...], phase: str, index: int, stride: int) -> list[Cell]:
    """The block of one phase's cells that array child ``index`` owns."""
    if phase not in PHASES:
        raise SystemExit(f"--phase must be one of {PHASES}, got {phase!r}")
    if stride < 1:
        raise SystemExit("--stride must be at least 1")
    phase_cells = [cell for cell in cells if cell.phase == phase]
    start = index * stride
    if index < 0 or start >= len(phase_cells):
        children = -(-len(phase_cells) // stride)
        raise SystemExit(f"Array index {index} outside 0..{children - 1} for phase {phase}")
    return phase_cells[start:start + stride]


def _already_complete(client: Any, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except client.exceptions.NoSuchKey:
        return False
    except Exception as exc:
        status_code = getattr(exc, "response", {}).get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if status_code == 403:
            raise SystemExit(
                "S3 HeadObject returned 403: the prefix must be under the job "
                "role's campaign/* scope"
            ) from exc
        if status_code == 404:
            return False
        raise


def _put_json(client: Any, bucket: str, key: str, payload: Any) -> None:
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"),
        ContentType="application/json",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, help="fit or held_out")
    parser.add_argument("--stride", type=int, default=1, help="Cells per array child")
    parser.add_argument(
        "--s3-prefix",
        required=True,
        help="s3://bucket/campaign/covid_first_look_v1/",
    )
    parser.add_argument(
        "--design",
        default=None,
        help="Design JSON, relative to the repository root (default: v1)",
    )
    args = parser.parse_args()

    design = load_design(
        str(_REPO_ROOT / args.design) if args.design else None,
    )
    cells = child_cells(enumerate_cells(design), args.phase, _array_index(), args.stride)
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
