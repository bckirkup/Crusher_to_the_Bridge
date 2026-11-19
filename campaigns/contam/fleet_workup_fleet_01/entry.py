#!/usr/bin/env python3
"""Argv builder for the 73-hull fleet stage of the airflow workup.

Blocks: ``gate`` (one untimed job: configuration smoke and frozen gates on all
73 hulls; nothing is timed) and ``fleet`` (eight serial cohort jobs; the seed
is the cohort index; each re-runs its own smoke and gates, then times). Every
job is submitted singly (``scripts/campaign submit --canary --index N``),
never as an array, so one job has one host to itself in the queue's terms.
A local run (``scripts/campaign run``) is the untimed smoke only.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNNER = "tools/diag/contam_fleet_workup_run.py"
_SELECTION = "campaigns/contam/fleet_workup_fleet_01/design/fleet_selection.json"
_ARCHIVE = ("s3://crusherbucket-994254241749-us-east-1-an/campaign/"
            "contam_fleet_workup_canary_01/external/contam-x-3.4.0.3-Linux-64bit.tar.gz")


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one job; ``seed`` is the cohort index on the ``fleet`` block."""
    artifact = block["artifact"].format(seed=seed)
    mode = block["args"]["mode"]
    command = [sys.executable, str(_REPO_ROOT / _RUNNER), "--out", str(out_dir),
               "--artifact", artifact, "--selection", str(_REPO_ROOT / _SELECTION)]
    if mode == "fleet":
        command += ["--cohort", str(seed)]
    if getattr(args, "local", False):
        from engines.contamx_runner import find_contamx

        binary = find_contamx()
        if not binary:
            raise SystemExit("ContamX binary unavailable for the local smoke")
        command += ["--mode", "smoke", "--binary", str(binary)]
    else:
        command += ["--mode", mode, "--contamx-uri", _ARCHIVE]
    return command, Path(out_dir) / artifact
