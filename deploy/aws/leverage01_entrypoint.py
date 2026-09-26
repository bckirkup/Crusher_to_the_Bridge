#!/usr/bin/env python3
"""AWS Batch worker for one LEVERAGE-01 perturbation run.

Array child ``i`` owns ``enumerate_runs(design)[i]``: one
(axis, endpoint, seed[, hull]) point of the frozen design file. The child
runs ``picard_framework.leverage_screen`` for that point and uploads its
record as ``<run_id>.json`` under ``<s3-prefix>/<channel>/``. A Spot
reclaim retries the child; an existing S3 object means done, not redo.
``--index`` overrides the Batch array env var for single-job canaries.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.dose_challenge_entrypoint import (  # noqa: E402
    _already_uploaded,
    _s3_client,
    _s3_uri,
)
from picard_framework.leverage_screen import enumerate_runs, load_design  # noqa: E402

_DRIVER = "-m"
_DRIVER_MODULE = "picard_framework.leverage_screen"
_OUT_DIR = "leverage01_out"


def _array_index(args: argparse.Namespace) -> int:
    """The run index: an explicit ``--index`` beats the Batch env var.

    ``--index`` arrives as a string so a job definition can carry
    ``Ref::index`` with an empty default: the empty string falls through
    to the array env var.
    """
    raw = args.index or os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if not raw:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX or --index is required")
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit("array index must be an integer") from exc


def _run_argv(ref: dict[str, Any], out_dir: Path) -> list[str]:
    argv = [
        sys.executable,
        _DRIVER,
        _DRIVER_MODULE,
        "--axis", ref["axis_id"],
        "--seed", str(ref["seed"]),
        "--out", str(out_dir),
    ]
    if ref.get("endpoint") is not None:
        argv += ["--endpoint", repr(float(ref["endpoint"]))]
    if ref["axis_id"] == "baseline":
        argv += ["--channel", ref["channel"]]
    if ref["channel"] == "covid":
        argv += ["--hull", ref["hull"]]
    return argv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line for one leverage run: the S3 prefix is the only input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--index", default="",
                        help="run index; defaults to AWS_BATCH_JOB_ARRAY_INDEX")
    parser.add_argument("--list", action="store_true", dest="list_runs",
                        help="print the run count and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this child's point and upload its record."""
    args = parse_args(argv)
    design = load_design()
    runs = enumerate_runs(design)
    if args.list_runs:
        print(f"{len(runs)} runs")
        return 0
    index = _array_index(args)
    if not 0 <= index < len(runs):
        raise SystemExit(f"array index {index} outside 0..{len(runs) - 1}")
    ref = runs[index]
    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"

    run_id = _run_id(ref)
    key = f"{prefix}{ref['channel']}/{run_id}.json"
    client = _s3_client()
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / _OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    command = _run_argv(ref, out_dir)
    print(json.dumps(ref), flush=True)
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603
    dump = out_dir / f"{run_id}.json"
    if not dump.exists():
        raise SystemExit(f"driver finished but wrote no record at {dump}")
    client.upload_file(str(dump), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


def _run_id(ref: dict[str, Any]) -> str:
    """The record filename stem the driver writes.

    The driver renders ``args.endpoint`` (a float) verbatim, so the design's
    JSON ints must be formatted as floats here too: ``5`` -> ``5.0``.
    """
    axis = ref["axis_id"]
    endpoint = ref.get("endpoint")
    ep = repr(float(endpoint)) if endpoint is not None else "None"
    if ref["channel"] == "covid":
        return f"leverage01_{axis}_{ep}_{ref['hull']}_{ref['seed']}"
    return f"leverage01_{axis}_{ep}_{ref['seed']}"


if __name__ == "__main__":
    raise SystemExit(main())
