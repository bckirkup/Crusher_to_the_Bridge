#!/usr/bin/env python3
"""Argv builder for the four-hull fleet-workup canary.

One block, one job, never an array: ``scripts/campaign submit --canary``.
On Batch the job runs the gated, timed canary and fetches the pinned ContamX
archive from the campaign's private S3 prefix. A local run
(``scripts/campaign run``) is the untimed configuration smoke only; a
workstation timing is not a substitute for the benchmark.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNNER = "tools/diag/contam_fleet_workup_run.py"
_ARCHIVE = "external/contam-x-3.4.0.3-Linux-64bit.tar.gz"


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for the single canary job (``seed`` is a placeholder index)."""
    artifact = block["artifact"]
    command = [sys.executable, str(_REPO_ROOT / _RUNNER), "--out", str(out_dir),
               "--artifact", artifact]
    if getattr(args, "local", False):
        from engines.contamx_runner import find_contamx

        binary = find_contamx()
        if not binary:
            raise SystemExit("ContamX binary unavailable for the local smoke")
        command += ["--mode", "smoke", "--binary", str(binary)]
    else:
        prefix = str(getattr(args, "s3_prefix", "") or "").rstrip("/")
        if not prefix:
            raise SystemExit("--s3-prefix is required for the Batch canary")
        command += ["--mode", "canary", "--contamx-uri", f"{prefix}/{_ARCHIVE}"]
    return command, Path(out_dir) / artifact
