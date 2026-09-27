#!/usr/bin/env python3
"""AWS Batch entrypoint for the FLU-RHYTHM-01 paired A/B campaign.

Each array child runs ONE manifest cell through the flu probe
(``tools/flu_rhythm_ab_probe.py --platform --seed --epochs --arm --tier``)
and uploads one campaign-shaped run zip containing ``summary.json``
(anchor-scored directly) plus ``rhythm.json.gz`` (cabin-pair challenge
table, stage-resolved delivery decomposition, per-epoch dosed sets,
acquisition pedigree, dealt-day commitments, state digests). The flat
array index walks the declared tiers in order, then the tier's seed
list; the arm is a job-level parameter so the off and on blocks are
separate array submissions over the same cell layout.

``--index`` overrides ``AWS_BATCH_JOB_ARRAY_INDEX`` for single-job canary
runs submitted with a container command override (the array-index env
var is reserved and cannot be injected on a non-array job).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.dose_challenge_entrypoint import (  # noqa: E402
    _already_uploaded,
    _s3_client,
    _s3_uri,
)

_DRIVER = "tools/flu_rhythm_ab_probe.py"
_TIERS = ("flu_exp_12d", "flu_spr_12d", "flu_cls_12d", "flu_mega_12d")
_OUT_ROOT = "out/flu_diag/rhythm_ab"
ARMS = ("off", "on")


def tier_cells(manifest: dict, tier: str) -> list[dict]:
    """One cell dict per declared seed in the tier."""
    block = manifest["tiers"][tier]
    seeds = block["seeds"]
    return [
        {
            "platform": block["platform"],
            "epochs": int(block["epochs"]),
            "seed": int(seeds["start"] + i),
        }
        for i in range(int(seeds["count"]))
    ]


def _cell_index(args: argparse.Namespace) -> int:
    """``--index`` (canary override) else the Batch array env."""
    if args.index is not None:
        return int(args.index)
    raw = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw is None:
        raise SystemExit(
            "AWS_BATCH_JOB_ARRAY_INDEX is required (or pass --index)",
        )
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(
            "AWS_BATCH_JOB_ARRAY_INDEX must be an integer",
        ) from exc


def _flat_cell(index: int, manifest: dict) -> tuple[str, dict]:
    """The (tier, cell) this flat index owns."""
    offset = 0
    for tier in _TIERS:
        cells = tier_cells(manifest, tier)
        if index < offset + len(cells):
            return tier, cells[index - offset]
        offset += len(cells)
    raise SystemExit(f"array index {index} outside 0..{offset - 1}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--index", type=int, default=None)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print the cell this index would run and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run this array child's manifest cell and upload its run zip."""
    args = parse_args(argv)
    index = _cell_index(args)
    manifest_path = (_REPO_ROOT / args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tier, cell = _flat_cell(index, manifest)
    run_id = f"s{cell['seed']}"

    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    key = f"{prefix}{args.arm}/{tier}/{run_id}.zip"

    if args.dry_run:
        print(json.dumps({"index": index, "tier": tier, "key": key, **cell}))
        return

    client = _s3_client()
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return

    out_dir = _REPO_ROOT / _OUT_ROOT / args.arm
    command = [
        sys.executable,
        _DRIVER,
        "--platform", str(cell["platform"]),
        "--seed", str(cell["seed"]),
        "--epochs", str(cell["epochs"]),
        "--arm", args.arm,
        "--tier", tier,
        "--confinement", str(manifest.get("confinement", "declared")),
        "--out", str(_REPO_ROOT / _OUT_ROOT),
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
