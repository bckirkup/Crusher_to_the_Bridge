#!/usr/bin/env python3
"""AWS Batch worker for one cell of the NORO-DEPOSIT-ATTR-01 arm grid.

The array is ``len(ARMS) x seed_count`` children of
``tools/noro_diag/deposit_attr_trace.py``: child ``i`` runs arm
``ARMS[i // seed_count]`` at seed ``seeds[i % seed_count]`` and uploads its
gzipped JSON under ``s3://<bucket>/<prefix>arm_<arm>/``. Reuses the S3 /
array-cell helpers of ``dose_challenge_entrypoint`` (same retry -> done
semantics, same ambient boto3 job-role identity), matching
``cabin_floor_entrypoint``.
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
from tools.noro_diag.deposit_attr_trace import ARMS, DEFAULT_SEEDS  # noqa: E402

_DRIVER = "tools/noro_diag/deposit_attr_trace.py"
_OUT_ROOT = "deposit_attr_out"


def _cell(index: int, seeds: list[int]) -> tuple[str, int]:
    """The (arm, seed) this array index owns."""
    if not 0 <= index < len(ARMS) * len(seeds):
        raise SystemExit(
            f"array index {index} outside 0..{len(ARMS) * len(seeds) - 1}",
        )
    return ARMS[index // len(seeds)], seeds[index % len(seeds)]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line for one deposit-attribution cell."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument(
        "--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS),
        help="comma-separated paired seeds (8105,8106 on fl_spr_12d)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this array child's cell and upload exactly its own dump."""
    args = parse_args(argv)
    seeds = [int(s) for s in args.seeds.split(",")]
    arm, seed = _cell(_array_index(), seeds)
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    name = f"deposit_attr_fl_spr_12d_{arm}_seed{seed}.json.gz"
    key = f"{prefix}arm_{arm}/{name}"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / _OUT_ROOT / arm
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, _DRIVER,
        "--arm", arm,
        "--seeds", str(seed),
        "--out", str(out_dir),
    ]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603
    dump = out_dir / name
    if not dump.exists():
        raise SystemExit(f"driver finished but wrote no dump at {dump}")

    client.upload_file(str(dump), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
