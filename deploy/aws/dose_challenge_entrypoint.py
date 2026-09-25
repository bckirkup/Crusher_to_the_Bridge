#!/usr/bin/env python3
"""AWS Batch worker for one cell of a per-host dose-challenge block.

The array is ``3 x seed_count`` children: child ``i`` runs seed
``seed_base + (i % seed_count)`` under arm ``ARMS[i // seed_count]`` and
uploads exactly its own ``.json.gz`` dump. Arms are the frozen
NORO-TOUCH-SHARE-01 triad -- ``per_surface_areal`` and
``per_surface_declared`` (the coincidence pair) plus ``pooled`` (the
DISAGG-01 identity control) -- so every seed lands three dumps under one
S3 prefix and the readout runs locally after ``aws s3 sync``.

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

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-",
)

ARMS = ("per_surface_areal", "per_surface_declared", "pooled")
_TOUCH_SHARE = {
    "per_surface_areal": "areal",
    "per_surface_declared": "declared",
}
_DRIVER = "tools/noro_diag/per_host_dose_challenge.py"
_OUT_ROOT = "dose_challenge_out"


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


def _cell(index: int, seed_count: int) -> tuple[str, int]:
    """The (arm, seed) this array index owns."""
    if not 0 <= index < len(ARMS) * seed_count:
        raise SystemExit(
            f"array index {index} outside 0..{len(ARMS) * seed_count - 1}",
        )
    return ARMS[index // seed_count], index % seed_count


def _driver_argv(
    args: argparse.Namespace,
    arm: str,
    seed: int,
    out_dir: Path,
) -> list[str]:
    argv = [
        sys.executable,
        _DRIVER,
        "--platform", args.platform,
        "--bundle", args.bundle,
        "--pathogen-id", args.pathogen_id,
        "--epochs", str(args.epochs),
        "--seeds", str(seed),
        "--arm-tag", arm,
        "--out", str(out_dir),
    ]
    if arm == "pooled":
        argv += ["--fomite-representation", "pooled"]
    else:
        argv += ["--fomite-representation", "per_surface"]
        argv += ["--fomite-touch-share", _TOUCH_SHARE[arm]]
        if arm == "per_surface_declared":
            argv += ["--fomite-touch-share-table", args.touch_share_table]
    return argv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line for one dose-challenge cell."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--seed-count", type=int, required=True)
    parser.add_argument("--seed-base", type=int, default=8020)
    parser.add_argument("--platform", default="spirit_cruise_3000")
    parser.add_argument("--bundle", default="norwalk_only")
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument(
        "--touch-share-table",
        default="data/config/fomite_touch_share_declared.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this array child's cell and upload exactly its own dump."""
    args = parse_args(argv)
    arm, seed_offset = _cell(_array_index(), args.seed_count)
    seed = args.seed_base + seed_offset
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    name = f"per_host_dose_challenge_{arm}_seed{seed}.json.gz"
    key = f"{prefix}arm_{arm}/{name}"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / _OUT_ROOT / f"arm_{arm}"
    dump = out_dir / name
    command = _driver_argv(args, arm, seed, out_dir)
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603
    if not dump.exists():
        raise SystemExit(f"driver finished but wrote no dump at {dump}")

    client.upload_file(str(dump), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
