#!/usr/bin/env python3
"""AWS Batch entrypoint for the NORO-CHANNEL-03 observation-funnel probe.

Each array child runs ONE seed of ONE NORO-OUTBREAK-01 cell through
``tools/noro_diag/observation_channel_funnel.py --manifest`` mode and
uploads its per-seed funnel dump:

    <prefix>/<tier>/<matchtag>/observation_channel_funnel_<arm>_seed<S>.json.gz

``--match`` tokens are run_id substrings selecting the cell inside the
tier (e.g. ``rung-shipped`` ``bp32p5c18p5``); the funnel refuses unless
exactly one spec resolves per seed.

The flat array index walks the ``--seeds`` list in order. A Spot reclaim
retries the child and a cell is deterministic, so an existing S3
artifact means the cell is done rather than that it must be redone.
``--index`` overrides ``AWS_BATCH_JOB_ARRAY_INDEX`` for single-job
canaries (the env var is reserved on Batch).
"""
from __future__ import annotations

import argparse
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.dose_challenge_entrypoint import (  # noqa: E402
    _already_uploaded,
    _array_index,
    _s3_client,
    _s3_uri,
)

_DRIVER = "tools/noro_diag/observation_channel_funnel.py"
_DEFAULT_MANIFEST = (
    "picard_framework/runs/mega_cruise_campaign/"
    "noro_outbreak_01_manifest.json"
)
_OUT_ROOT = "out/noro_diag/observation_channel_funnel"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument(
        "--match", type=str, nargs="*", default=[],
        help="run_id substrings selecting the cell inside --tier; all "
        "must appear in the resolved run id. Accepts comma-joined "
        "tokens and/or bare tokens (jobdef Ref:: substitution).",
    )
    parser.add_argument(
        "--seeds", required=True, type=str, nargs="+",
        help="seed list; accepts comma-joined tokens and/or bare tokens "
        "(--container-overrides splits commas into separate argv items, "
        "and jobdef Ref:: substitution joins them back)",
    )
    parser.add_argument("--manifest", default=_DEFAULT_MANIFEST)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--index", type=int, default=None)
    parser.add_argument("--index-offset", type=int, default=0)
    return parser.parse_args(argv)


def _match_tokens(args: argparse.Namespace) -> list[str]:
    return [
        v
        for item in args.match
        for v in item.split(",")
        if v.strip()
    ]


def _arm_tag(args: argparse.Namespace) -> str:
    tag = args.tier
    match = _match_tokens(args)
    if match:
        tag += "_" + "-".join(match)
    return tag


def main(argv: list[str] | None = None) -> int:
    """Run this array child's funnel voyage and upload its dump."""
    args = parse_args(argv)
    # The jobdef default passes index=-1 so array children resolve the
    # reserved AWS_BATCH_JOB_ARRAY_INDEX; a non-negative --index is the
    # single-job override.
    explicit = args.index if args.index is not None and args.index >= 0 else None
    index = args.index_offset + _array_index(explicit)
    seeds = [
        int(v)
        for item in args.seeds
        for v in item.split(",")
        if v.strip()
    ]
    if index >= len(seeds):
        raise SystemExit(
            f"array index {index} outside 0..{len(seeds) - 1}",
        )
    seed = seeds[index]
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    out_dir = _REPO_ROOT / _OUT_ROOT / _arm_tag(args)
    arm_tag = _arm_tag(args)
    artifact = (
        out_dir
        / f"observation_channel_funnel_{arm_tag}_seed{seed}.json.gz"
    )
    match_tokens = _match_tokens(args)
    matchtag = "-".join(match_tokens) if match_tokens else "cell"
    key = f"{prefix}{args.tier}/{matchtag}/{artifact.name}"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0
    command = [
        sys.executable, _DRIVER,
        "--manifest", str(_REPO_ROOT / args.manifest),
        "--tier", args.tier,
        "--seeds", str(seed),
        "--pathogen-id", args.pathogen_id,
        "--arm-tag", arm_tag,
        "--out", str(out_dir),
    ]
    for token in match_tokens:
        command += ["--match", token]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603
    if not artifact.exists():
        raise SystemExit(f"driver finished but wrote no dump at {artifact}")
    client.upload_file(str(artifact), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
