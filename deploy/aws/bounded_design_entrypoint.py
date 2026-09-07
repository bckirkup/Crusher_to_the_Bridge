#!/usr/bin/env python3
"""AWS Batch worker for one shard of a bounded design over the norovirus box.

Two designs share this worker, because they shard the same way -- a unit of
work is self-contained and the units pool afterwards:

* ``--design screen``: one shard of the Morris screen's trajectories. Every
  shard draws the whole design and evaluates the trajectories congruent to its
  index, so a sharded screen evaluates the design an unsharded screen would
  have evaluated at the same ``--design-seed``. The shard uploads its raw
  elementary effects; ``bounded_screen.py --mode merge`` pools them.
* ``--design region``: one shard of the feasibility gate's Sobol' points. The
  shard uploads its point stream (JSONL); ``admissible_region.py --merge``
  pools the streams and refuses a grid with a hole in it.

Neither design fits anything. The screen ranks factors by elementary effect and
the gate classifies points against the anchors; a shard that finished is not a
licence to read a verdict off a partial design, which is why the merge step
checks coverage rather than summarising what happened to arrive.

The container writes nothing outside its own S3 prefix and takes its identity
from the Batch job role through the ambient boto3 chain.
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

from telemetry_buffer.observation_model.bounded_screen import (  # noqa: E402
    DEFAULT_PLATFORM,
)

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-",
)

_SCREEN = "screen"
_REGION = "region"


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
    """Whether this shard's artifact is already in S3.

    A Spot reclaim retries the child, and a shard is deterministic, so an
    existing artifact means the work is done rather than that it must be redone.
    """
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - boto3 raises per-client classes
        response = getattr(exc, "response", {}) or {}
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 403:
            raise SystemExit(
                "S3 HeadObject returned 403: the design prefix must be under "
                "the job role's campaign/* scope",
            ) from exc
        if status not in (404, None):
            raise
        return False
    return True


def _complement_argv(args: argparse.Namespace) -> list[str]:
    """The complement flag, or nothing so the hull's declaration is used.

    A stated complement is passed through and the design refuses it unless it
    is the hull's, so a job definition cannot put one class's population in
    another class's spatial graph.
    """
    if args.num_agents is None:
        return []
    return ["--num-agents", str(args.num_agents)]


def _screen_argv(args: argparse.Namespace, shard: int, out: Path) -> list[str]:
    return [
        sys.executable,
        "telemetry_buffer/observation_model/bounded_screen.py",
        "--mode", "screen",
        "--pathogen-id", args.pathogen_id,
        "--platform", args.platform,
        "--epochs", str(args.epochs),
        *_complement_argv(args),
        "--trajectories", str(args.trajectories),
        "--seeds", str(args.seeds),
        "--design-seed", str(args.design_seed),
        "--shard-count", str(args.shard_count),
        "--shard-index", str(shard),
        "--seed-shards", str(args.seed_shards),
        "--out", str(out),
    ]


def _only_points(raw: str) -> list[str]:
    """The design indices a subset re-run names, as a comma-separated list.

    A Batch parameter is one string, so the selection arrives as ``"7,13,204"``
    rather than as repeated arguments. An index that is not an integer is
    refused here: a mistyped subset would otherwise re-run the wrong points.
    """
    indices = [part.strip() for part in raw.split(",") if part.strip()]
    for index in indices:
        if not index.isdigit():
            raise SystemExit(f"--only-points takes design indices: {raw!r}")
    return indices


def _region_argv(
    args: argparse.Namespace,
    shard: int,
    out: Path,
    stream: Path,
) -> list[str]:
    argv = [
        sys.executable,
        "telemetry_buffer/observation_model/admissible_region.py",
        "--pathogen-id", args.pathogen_id,
        "--platform", args.platform,
        "--era", args.era,
        "--epochs", str(args.epochs),
        *_complement_argv(args),
        "--sobol-m", str(args.sobol_m),
        "--seeds", str(args.seeds),
        "--design-seed", str(args.design_seed),
        "--seed-shards", str(args.seed_shards),
        "--shard-count", str(args.shard_count),
        "--shard-index", str(shard),
        "--stream", str(stream),
        "--resume",
        "--out", str(out),
    ]
    # A subset re-run keeps the grid's own indices, so the array is sized by
    # the selection while every point means what it meant in the full design.
    selection = _only_points(args.only_points)
    if selection:
        argv += ["--only-points", *selection]
    # A Batch parameter is a string, so the arm arrives as on/off rather than
    # as the presence of a flag; the two arms must otherwise be the same
    # design at the same --design-seed for the seeds to be matched.
    if args.crew_duty_exclusion == "on":
        argv += ["--crew-duty-exclusion"]
    return argv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line for one design shard."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", choices=(_SCREEN, _REGION), required=True)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    parser.add_argument("--era", default="pre", choices=("pre", "post"))
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument("--num-agents", type=int, default=None)
    parser.add_argument("--trajectories", type=int, default=20)
    parser.add_argument("--seed-shards", type=int, default=1)
    parser.add_argument("--only-points", default="")
    parser.add_argument(
        "--crew-duty-exclusion", default="off", choices=("on", "off"),
    )
    parser.add_argument("--sobol-m", type=int, default=7)
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--design-seed", type=int, default=17)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this array child's shard and upload exactly its own artifacts."""
    args = parse_args(argv)
    shard = _array_index()
    if not 0 <= shard < args.shard_count:
        raise SystemExit(
            f"array index {shard} outside 0..{args.shard_count - 1}",
        )
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    key = f"{prefix}{args.design}/shard_{shard:04d}.json"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / "telemetry_buffer" / "observation_model"
    out = out_dir / f"batch_{args.design}_shard_{shard:04d}.json"
    stream = out_dir / f"batch_{args.design}_shard_{shard:04d}.jsonl"
    stream_key = f"{prefix}{args.design}/shard_{shard:04d}.jsonl"
    if args.design == _SCREEN:
        command = _screen_argv(args, shard, out)
    else:
        # A reclaimed child restarts with an empty disk, so the points this
        # shard already scored are recovered from S3 rather than re-run.
        if _already_uploaded(client, bucket, stream_key):
            client.download_file(bucket, stream_key, str(stream))
            print(f"Resuming from s3://{bucket}/{stream_key}", flush=True)
        command = _region_argv(args, shard, out, stream)
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603

    # The stream goes first: the shard report is the completion marker this
    # worker checks on retry, so it must not exist while the points it
    # summarises are still only on the container's disk.
    if args.design == _REGION and stream.exists():
        client.upload_file(str(stream), bucket, stream_key)
        print(f"Uploaded s3://{bucket}/{stream_key}", flush=True)
    client.upload_file(str(out), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
