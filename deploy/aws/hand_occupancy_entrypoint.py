#!/usr/bin/env python3
"""AWS Batch entrypoint for the NORO-HAND-STATIONARY-01 occupancy census.

Each array child runs ONE seed of ONE cell block and uploads its dump:

* ``--block fl_spr_12d`` -- the ignited spirit cell through
  ``tools/noro_diag/growth_chain_census.py``; uploads
  ``<prefix>/fl_spr_12d/<run_id>.zip``.
* ``--block classic_cruise_1900`` -- the EMESIS-SIZE-01 block through
  ``tools/noro_diag/fomite_mass_balance.py``; uploads
  ``<prefix>/classic_cruise_1900/fomite_mass_balance_<platform>_seed<S>.json.gz``.

The flat array index walks the ``--seeds`` list in order. A Spot reclaim
retries the child and a cell is deterministic, so an existing S3 artifact
means the cell is done rather than that it must be redone. ``--index``
overrides ``AWS_BATCH_JOB_ARRAY_INDEX`` for single-job canaries (the env
var is reserved on Batch).
"""
from __future__ import annotations

import argparse
import json
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(
    0, str(_REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"),
)

from campaign_runner import generate_tier_runs  # noqa: E402

from deploy.aws.dose_challenge_entrypoint import (  # noqa: E402
    _already_uploaded,
    _array_index,
    _s3_client,
    _s3_uri,
)

_SPIRIT_DRIVER = "tools/noro_diag/growth_chain_census.py"
_CLASSIC_DRIVER = "tools/noro_diag/fomite_mass_balance.py"
_OUT_ROOT = "out/noro_diag/hand_occupancy"


def _seed_run_index(
    manifest_path: Path, tier: str, seed: int,
) -> tuple[int, str]:
    """The (index-in-tier, run_id) whose spec carries ``seed``."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for index, (run_id, spec) in enumerate(
        generate_tier_runs(manifest, tier),
    ):
        if int(spec["run"]["random_seed"]) == seed:
            return index, run_id
    raise SystemExit(f"seed {seed} not in tier {tier}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument(
        "--block", required=True, choices=("fl_spr_12d", "classic_cruise_1900"),
    )
    parser.add_argument(
        "--seeds", required=True,
        help="comma-separated seeds; array index walks it",
    )
    parser.add_argument(
        "--manifest",
        default="picard_framework/runs/mega_cruise_campaign/"
                "noro_dose_refit_01_manifest.json",
    )
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--tier", default="fl_spr_12d")
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument("--index", type=int, default=None)
    return parser.parse_args(argv)


def _spirit_cell(
    args: argparse.Namespace, seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """The growth-census argv and the zip it must produce."""
    index_in_tier, run_id = _seed_run_index(
        (_REPO_ROOT / args.manifest).resolve(), args.tier, seed,
    )
    command = [
        sys.executable, _SPIRIT_DRIVER,
        "--manifest", str(args.manifest),
        "--tier", args.tier,
        "--index", str(index_in_tier),
        "--pathogen-id", args.pathogen_id,
        "--out", str(out_dir),
    ]
    return command, out_dir / args.tier / f"{run_id}.zip"


def _classic_cell(
    args: argparse.Namespace, seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """The fomite-mass-balance argv and the dump it must produce."""
    command = [
        sys.executable, _CLASSIC_DRIVER,
        "--platform", args.platform,
        "--epochs", str(args.epochs),
        "--seeds", str(seed),
        "--pathogen-id", args.pathogen_id,
        "--out", str(out_dir),
    ]
    if args.bundle:
        command += ["--bundle", args.bundle]
    name = f"fomite_mass_balance_{args.platform}_seed{seed}.json.gz"
    return command, out_dir / name


def main(argv: list[str] | None = None) -> int:
    """Run this array child's cell and upload exactly its own dump."""
    args = parse_args(argv)
    index = _array_index(args.index)
    seeds = [int(v) for v in args.seeds.split(",") if v.strip()]
    if index >= len(seeds):
        raise SystemExit(
            f"array index {index} outside 0..{len(seeds) - 1}",
        )
    seed = seeds[index]
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    out_dir = _REPO_ROOT / _OUT_ROOT
    if args.block == "fl_spr_12d":
        command, artifact = _spirit_cell(args, seed, out_dir)
        key = f"{prefix}{args.tier}/{artifact.name}"
    else:
        command, artifact = _classic_cell(args, seed, out_dir)
        key = f"{prefix}{args.block}/{artifact.name}"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603
    if not artifact.exists():
        raise SystemExit(f"driver finished but wrote no dump at {artifact}")
    client.upload_file(str(artifact), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
