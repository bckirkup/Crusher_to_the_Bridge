#!/usr/bin/env python3
"""AWS Batch worker for one cell of the CABIN-FLOOR-01 roster.

The array is ``len(ROSTER) x seed_count`` children of
``tools/cabin_floor_probe.py``: child ``i`` runs roster arm
``ROSTER[i // seed_count]`` (an isolated (bundle, pathogen_id) pair) at
seed ``seeds[i % seed_count]`` and uploads its JSON dump under
``s3://<bucket>/<prefix>arm_<bundle>__<pathogen_id>/``. The confined-window
verdict table is assembled locally after ``aws s3 sync``. Reuses the
S3/array-cell helpers of ``dose_challenge_entrypoint`` (same retry -> done
semantics, same ambient boto3 job-role identity).
"""
from __future__ import annotations

import argparse
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.dose_challenge_entrypoint import (  # noqa: E402
    _already_uploaded,
    _array_index,
    _s3_client,
    _s3_uri,
)
from tools.cabin_floor_probe import DEFAULT_SEEDS, ROSTER  # noqa: E402

_DRIVER = "tools/cabin_floor_probe.py"
_OUT_ROOT = "cabin_floor_out"


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
    parser.add_argument(
        "--confinement", choices=("organic", "declared"), default="organic",
    )
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
    name = f"cabin_floor_{pathogen_id}_{args.confinement}_seed{seed}.json"
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
        "--confinement", args.confinement,
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
