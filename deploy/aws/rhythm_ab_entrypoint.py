#!/usr/bin/env python3
"""AWS Batch entrypoint for the NORO-RHYTHM-01 paired A/B campaign.

Each array child runs ONE manifest spec through the rhythm probe
(``tools/noro_diag/rhythm_ab_probe.py --manifest --tier --index --arm``) and
uploads one campaign-shaped run zip containing ``summary.json``
(anchor-scored directly) plus ``rhythm.json.gz`` (emesis landing partition,
acquisition pedigree, per-epoch occupancy, dealt-day commitments, state
digests). The flat array index walks the declared tiers in order; the arm is
a job-level parameter (``--arm`` or jobdef ``arm`` parameter) so the off and
on blocks are separate array submissions over the same cell layout.

``--index`` overrides ``AWS_BATCH_JOB_ARRAY_INDEX`` for single-job canary
runs submitted with a container command override (the array-index env var is
reserved and cannot be injected on a non-array job).
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

_DRIVER = "tools/noro_diag/rhythm_ab_probe.py"
_TIERS = ("fl_exp_7d", "fl_exp_12d", "fl_spr_12d", "fl_cls_12d", "fl_mega_12d")
_OUT_ROOT = "out/noro_diag/rhythm_ab"
ARMS = ("off", "on")


def _tier_cell(index: int, manifest_path: Path) -> tuple[str, int]:
    """The (tier, index-in-tier) this flat index owns."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    offset = 0
    for tier in _TIERS:
        runs = list(generate_tier_runs(manifest, tier))
        if index < offset + len(runs):
            return tier, index - offset
        offset += len(runs)
    raise SystemExit(f"array index {index} outside 0..{offset - 1}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--index", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run this array child's manifest spec and upload its run zip."""
    args = parse_args(argv)
    index = _array_index(args.index)
    manifest_path = (_REPO_ROOT / args.manifest).resolve()
    tier, index_in_tier = _tier_cell(index, manifest_path)

    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id, _spec = list(generate_tier_runs(manifest, tier))[index_in_tier]
    key = f"{prefix}{args.arm}/{tier}/{run_id}.zip"
    client = _s3_client()
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return

    out_dir = _REPO_ROOT / _OUT_ROOT / args.arm
    command = [
        sys.executable,
        _DRIVER,
        "--manifest", str(args.manifest),
        "--tier", tier,
        "--index", str(index_in_tier),
        "--arm", args.arm,
        "--pathogen-id", args.pathogen_id,
        "--out", str(out_dir),
    ]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603

    zip_path = out_dir / tier / f"{run_id}.zip"
    if not zip_path.exists():
        raise SystemExit(f"driver finished but wrote no zip at {zip_path}")
    client.upload_file(str(zip_path), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)


if __name__ == "__main__":
    main()
