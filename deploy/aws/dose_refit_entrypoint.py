#!/usr/bin/env python3
"""AWS Batch entrypoint for the NORO-DOSE-REFIT-01 canary.

Each array child runs ONE manifest spec through the instrumented probe
(``tools/noro_diag/per_host_dose_challenge.py --manifest --tier --index``) and
uploads one campaign-shaped run zip containing ``summary.json`` (anchor-scored
directly) plus ``refit.json`` (per-host emesis records + deposit callsite
totals). The flat array index walks the declared tiers in order:
indices ``0..N_spr-1`` are ``fl_spr_12d``, the next ``N_mega`` are
``fl_mega_12d``. A child whose zip already exists in S3 exits 0 so a synced
prefix resumes cleanly.
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

_DRIVER = "tools/noro_diag/per_host_dose_challenge.py"
_TIERS = ("fl_spr_12d", "fl_mega_12d")
_OUT_ROOT = "out/noro_diag/refit_canary"


def _tier_cell(index: int, manifest_path: Path) -> tuple[str, int, int]:
    """The (tier, index-in-tier, array size) this flat index owns."""
    offset = 0
    for tier in _TIERS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        runs = list(generate_tier_runs(manifest, tier))
        if index < offset + len(runs):
            return tier, index - offset, offset + len(runs)
        offset += len(runs)
    raise SystemExit(f"array index {index} outside 0..{offset - 1}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this array child's manifest spec and upload its run zip."""
    args = parse_args(argv)
    index = _array_index()
    manifest_path = (_REPO_ROOT / args.manifest).resolve()
    tier, index_in_tier, _array = _tier_cell(index, manifest_path)

    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"

    # Resume marker: derive the expected zip path before spending the run.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id, _spec = list(generate_tier_runs(manifest, tier))[index_in_tier]
    key = f"{prefix}{tier}/{run_id}.zip"
    client = _s3_client()
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / _OUT_ROOT
    command = [
        sys.executable,
        _DRIVER,
        "--manifest", str(args.manifest),
        "--tier", tier,
        "--index", str(index_in_tier),
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
