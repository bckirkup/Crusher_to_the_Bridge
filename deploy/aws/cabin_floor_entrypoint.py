#!/usr/bin/env python3
"""AWS Batch worker for one cell of the CABIN-FLOOR-01 roster.

The array is ``len(ROSTER) x seed_count`` children of
``tools/cabin_floor_probe.py``: child ``i`` runs roster arm
``ROSTER[i // seed_count]`` (an isolated (bundle, pathogen_id) pair) at
seed ``seeds[i % seed_count]`` and uploads its JSON dump under
``s3://<bucket>/<prefix>arm_<bundle>__<pathogen_id>/``. The confined-window
verdict table is assembled locally after ``aws s3 sync``.

A Spot reclaim retries the child, and a cell is deterministic, so an
existing S3 artifact means the cell is done rather than that it must be
redone. The container writes nothing outside its own S3 prefix and takes
its identity from the Batch job role through the ambient boto3 chain.
"""
from __future__ import annotations

import argparse
import os
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.cabin_floor_probe import DEFAULT_SEEDS, ROSTER  # noqa: E402

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-",
)

_DRIVER = "tools/cabin_floor_probe.py"
_OUT_ROOT = "cabin_floor_out"


def _s3_uri(raw: str) -> tuple[str, str]:
    parsed = urlparse(raw)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    bad_bucket = any(char not in _BUCKET_CHARS for char in bucket)
    if parsed.scheme != "s3" or not bucket or bad_bucket:
        raise SystemExit(f"Invalid S3 URI: {raw!r}")
    if any(char not in _KEY_CHARS for char in key):
        raise SystemExit(f"Invalid S3 key: {key!r}")
    return bucket, key.rstrip("/")


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - image always has boto3
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


def _already_uploaded(client: Any, bucket: str, key: str) -> bool:
    """Whether this cell's dump is already in S3 (retry -> done, not redo)."""
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - boto3 raises per-client classes
        response = getattr(exc, "response", {}) or {}
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 403:
            raise SystemExit(
                "S3 HeadObject returned 403: the block prefix must be under "
                "the job role's campaign/* scope",
            ) from exc
        if status not in (404, None):
            raise
        return False
    return True


def _cell(
    index: int,
    seeds: list[int],
) -> tuple[tuple[str, str], int]:
    """The ((bundle, pathogen_id), seed) this array index owns."""
    if not 0 <= index < len(ROSTER) * len(seeds):
        raise SystemExit(
            f"array index {index} outside 0..{len(ROSTER) * len(seeds) - 1}",
        )
    return ROSTER[index // len(seeds)], seeds[index % len(seeds)]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line for one cabin-floor cell."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument(
        "--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS),
        help="comma-separated paired seeds (8105,8106 on classic_cruise_1900)",
    )
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--epochs", type=int, default=288)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this array child's cell and upload exactly its own dump."""
    args = parse_args(argv)
    seeds = [int(s) for s in args.seeds.split(",")]
    (bundle, pathogen_id), seed = _cell(_array_index(), seeds)
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    name = f"cabin_floor_{pathogen_id}_seed{seed}.json"
    key = f"{prefix}arm_{bundle}__{pathogen_id}/{name}"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / _OUT_ROOT / f"{bundle}__{pathogen_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    dump = out_dir / name
    command = [
        sys.executable, _DRIVER,
        "--platform", args.platform,
        "--epochs", str(args.epochs),
        "--seeds", str(seed),
        "--arm", pathogen_id,
        "--bundle", bundle,
        "--out", str(dump),
    ]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603
    if not dump.exists():
        raise SystemExit(f"driver finished but wrote no dump at {dump}")

    client.upload_file(str(dump), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
