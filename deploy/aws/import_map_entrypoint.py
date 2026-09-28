#!/usr/bin/env python3
"""AWS Batch entrypoint for the NORO-IMPORT-01 import-region campaign.

Each array child runs ONE manifest spec through the growth-chain census
driver (``tools/noro_diag/growth_chain_census.py --manifest --tier
--index --pathogen-id``) and uploads one run zip containing
``summary.json`` in the campaign layout (parameters / timeseries /
derived / summary / cost_accounting, plus the census counts and the
``initiation`` block witnessing the resolved boarding spec and drawn
composition) and ``growth_census.json.gz`` (the per-link payload).

``--tier`` selects the manifest tier (each tier is one arm family of the
design: ``*_scr`` screening cells, ``*_ren`` renewal cells, and the
expedition-12d flag/dose/alpha cells). ``--index-offset`` shifts the
array index so a small canary array can sit on one cell's interior
instead of starting at the tier's first run; ``--index`` overrides the
array index entirely for single-job canaries (``AWS_BATCH_JOB_ARRAY_INDEX``
is reserved and cannot be injected on a non-array job).
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

_DRIVER = "tools/noro_diag/growth_chain_census.py"
_OUT_ROOT = "out/noro_diag/import_map"


def _tier_runs(manifest_path: Path, tier: str) -> list[tuple[str, dict]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if tier not in manifest["tiers"]:
        raise SystemExit(
            f"--tier {tier!r} not in manifest; declared: "
            f"{sorted(manifest['tiers'])}",
        )
    return list(generate_tier_runs(manifest, tier))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--tier", required=True)
    parser.add_argument("--index", type=int, default=None)
    parser.add_argument("--index-offset", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run this array child's manifest spec and upload its run zip."""
    args = parse_args(argv)
    # The jobdef default passes index=-1 so array children resolve the
    # reserved AWS_BATCH_JOB_ARRAY_INDEX; a non-negative --index is the
    # single-job override.
    explicit = args.index if args.index is not None and args.index >= 0 else None
    index = args.index_offset + _array_index(explicit)
    manifest_path = (_REPO_ROOT / args.manifest).resolve()
    runs = _tier_runs(manifest_path, args.tier)
    if index >= len(runs):
        raise SystemExit(
            f"index {index} outside tier {args.tier} ({len(runs)} runs)",
        )
    run_id, _spec = runs[index]

    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    key = f"{prefix}{args.tier}/{run_id}.zip"
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
        "--index", str(index),
        "--pathogen-id", args.pathogen_id,
        "--out", str(out_dir),
    ]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603

    zip_path = out_dir / args.tier / f"{run_id}.zip"
    if not zip_path.exists():
        raise SystemExit(f"driver finished but wrote no zip at {zip_path}")
    client.upload_file(str(zip_path), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)


if __name__ == "__main__":
    main()
