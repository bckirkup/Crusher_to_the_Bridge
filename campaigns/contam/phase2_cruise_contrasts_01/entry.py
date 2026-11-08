#!/usr/bin/env python3
"""Argv builder for Phase 2 CONTAM cruise-contrast trajectory cells.

The 32-field E/P cache is generated locally and uploaded to S3 before any
Batch submit; trajectory argv points at that cache (or uses --inline-field
for a local smoke) and names the block's frozen arm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CAMPAIGN = json.loads(
    (Path(__file__).resolve().parent / "campaign.json").read_text(encoding="utf-8")
)
_CELL = "campaigns/contam/phase2_cruise_contrasts_01/cell.py"
_DESIGN = "campaigns/contam/phase2_cruise_contrasts_01/design/phase2_cruise_contrasts_design.json"


def _artifact(block: dict[str, Any], seed: int, out_dir: Path) -> Path:
    name = block["artifact"]
    if "{seed}" in name:
        name = name.format(seed=seed)
    return Path(out_dir) / name


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one (hull, lane, arm, seed) trajectory cell."""
    command = [
        sys.executable,
        str(_REPO_ROOT / _CELL),
        "--mode",
        "trajectory",
        "--design",
        _DESIGN,
        "--epochs",
        str(getattr(args, "epochs", None) or _CAMPAIGN.get("epochs") or 12),
        "--epoch-hours",
        str(getattr(args, "epoch_hours", None) or _CAMPAIGN.get("epoch_hours") or 1.0),
        "--out",
        str(out_dir),
    ]
    block_args = block.get("args") or {}
    command += [
        "--hull", str(block_args["hull"]),
        "--lane", str(block_args["lane"]),
        "--arm", str(block_args.get("arm", "baseline")),
        "--seed", str(seed),
    ]
    if getattr(args, "local", False):
        command.append("--inline-field")
    else:
        prefix = str(getattr(args, "s3_prefix", "") or "").rstrip("/")
        if prefix:
            command += ["--field-cache-uri", f"{prefix}/field_cache/field_cache.json"]
    return command, _artifact(block, seed, out_dir)
