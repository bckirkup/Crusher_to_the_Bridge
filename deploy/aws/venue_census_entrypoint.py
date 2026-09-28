#!/usr/bin/env python3
"""AWS Batch entrypoint for the NORO-VENUE-01 placement census.

Each array child runs ONE (tier, seed) cell through the venue census
probe (``tools/noro_diag/venue_placement_census.py``) and uploads one
campaign-shaped run zip containing ``summary.json`` plus
``venue.json.gz`` (classified emit rows, per-host confinement timelines,
confinement/escalation events, per-epoch confined membership, zone
classification).

The flat array index walks the ``--seeds`` list in order: child ``i``
runs the tier run whose ``run.random_seed`` equals ``seeds[i]``.
``--platform-id``/``--num-agents`` post-mutate the tier spec (the
classic-hull cells re-run the spirit spec on ``classic_cruise_1900``).

``--index`` overrides ``AWS_BATCH_JOB_ARRAY_INDEX`` for single-job
canary runs submitted with a container command override (the array-index
env var is reserved and cannot be injected on a non-array job).
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

_DRIVER = "tools/noro_diag/venue_placement_census.py"
_OUT_ROOT = "out/noro_diag/venue_census"


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
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--tier", required=True)
    parser.add_argument(
        "--seeds", required=True,
        help="comma-separated run.random_seed values; array index walks it",
    )
    parser.add_argument("--platform-id", default=None)
    parser.add_argument("--num-agents", type=int, default=None)
    parser.add_argument("--index", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run this array child's cell and upload its run zip."""
    args = parse_args(argv)
    index = _array_index(args.index)
    seeds = [int(v) for v in args.seeds.split(",") if v.strip()]
    if index >= len(seeds):
        raise SystemExit(
            f"array index {index} outside 0..{len(seeds) - 1}",
        )
    seed = seeds[index]
    manifest_path = (_REPO_ROOT / args.manifest).resolve()
    index_in_tier, run_id = _seed_run_index(
        manifest_path, args.tier, seed,
    )

    cell_label = args.platform_id or args.tier
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    key = f"{prefix}{cell_label}/{run_id}.zip"
    client = _s3_client()
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return

    out_dir = _REPO_ROOT / _OUT_ROOT
    command = [
        sys.executable,
        _DRIVER,
        "--manifest", str(args.manifest),
        "--tier", args.tier,
        "--index", str(index_in_tier),
        "--pathogen-id", args.pathogen_id,
        "--out", str(out_dir),
    ]
    if args.platform_id:
        command += ["--platform-id", args.platform_id]
    if args.num_agents:
        command += ["--num-agents", str(args.num_agents)]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603

    zip_path = out_dir / args.tier / f"{run_id}.zip"
    if not zip_path.exists():
        raise SystemExit(f"driver finished but wrote no zip at {zip_path}")
    client.upload_file(str(zip_path), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)


if __name__ == "__main__":
    main()
