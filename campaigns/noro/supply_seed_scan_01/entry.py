#!/usr/bin/env python3
"""Campaign argv hook for FOOD-SUPPLY-01 seed-initiation chunks."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def build_argv(args: Any, block: dict[str, Any], seed: int, out_dir: Path) -> tuple[list[str], Path]:
    cfg = block.get("args") or {}
    # campaign_entrypoint spawns the worker with this process environment.
    os.environ["PYTHONHASHSEED"] = "1"
    artifact_name = f"{cfg['artifact_stem']}_chunk{int(seed):06d}.jsonl"
    command = [
        sys.executable,
        block["worker"],
        "--manifest", str(args.manifest),
        "--pathogen-id", str(args.pathogen_id),
        "--tier", str(cfg["tier"]),
        "--arm", str(cfg["arm"]),
        "--structure", str(cfg.get("structure", "flat")),
        "--hull", str(cfg["hull"]),
        "--seed-start", str(cfg["seed_start"]),
        "--seed-count", str(cfg["seed_count"]),
        "--chunk-index", str(seed),
        "--chunk-size", str(cfg.get("chunk_size", 100)),
        "--epochs", str(args.epochs or cfg.get("epochs", 1)),
        "--num-agents", str(cfg.get("num_agents", 100)),
        "--out", str(out_dir),
        "--artifact", artifact_name,
    ]
    return command, Path(out_dir) / artifact_name
