#!/usr/bin/env python3
"""Argv builder for the Phase 1 CONTAM tracer campaign."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CAMPAIGN = json.loads(
    (Path(__file__).resolve().parent / "campaign.json").read_text(encoding="utf-8")
)
_CELL = "campaigns/contam/phase1_hvac_tracer_01/cell.py"
_DESIGN = "campaigns/contam/phase1_hvac_tracer_01/design/phase1_hvac_tracer_design.json"


def _artifact(block: dict[str, Any], seed: int, out_dir: Path) -> Path:
    name = block["artifact"]
    if "{seed}" in name:
        name = name.format(seed=seed)
    return Path(out_dir) / name


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one field-cache job or one (hull, lane, seed) trajectory."""
    mode = str(block.get("args", {}).get("mode") or "trajectory")
    command = [
        sys.executable,
        str(_REPO_ROOT / _CELL),
        "--mode",
        "field-cache" if mode == "field_cache" else "trajectory",
        "--design",
        _DESIGN,
        "--epochs",
        str(getattr(args, "epochs", None) or _CAMPAIGN.get("epochs") or 12),
        "--epoch-hours",
        str(getattr(args, "epoch_hours", None) or _CAMPAIGN.get("epoch_hours") or 1.0),
        "--out",
        str(out_dir),
    ]
    if mode == "field_cache":
        return command, _artifact(block, seed, out_dir)

    block_args = block.get("args") or {}
    command += [
        "--hull", str(block_args["hull"]),
        "--lane", str(block_args["lane"]),
        "--seed", str(seed),
    ]
    if getattr(args, "local", False):
        command.append("--inline-field")
    else:
        prefix = str(getattr(args, "s3_prefix", "") or "").rstrip("/")
        if prefix:
            command += ["--field-cache-uri", f"{prefix}/field_cache/field_cache.json"]
    return command, _artifact(block, seed, out_dir)
