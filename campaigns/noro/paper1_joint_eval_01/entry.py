#!/usr/bin/env python3
"""Campaign argv hook for noro_paper1_joint_eval_01.

Census blocks drive ``supply_seed_scan.py`` (chunk index in, JSONL out);
every other block is a tier block driving ``cell.py``. Both get
``PYTHONHASHSEED=1`` (freeze contract section 2.5).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNNER_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"


def _census_argv(
    args: Any, block: dict[str, Any], chunk: int, out_dir: Path,
) -> tuple[list[str], Path]:
    cfg = block["args"]
    artifact = f"{cfg['artifact_stem']}_chunk{int(chunk):06d}.jsonl"
    command = [
        sys.executable, block["worker"],
        "--manifest", str(args.manifest),
        "--pathogen-id", str(args.pathogen_id),
        "--tier", str(cfg["tier"]),
        "--arm", str(cfg["arm"]),
        "--hull", str(cfg["hull"]),
        "--seed-start", str(cfg["seed_start"]),
        "--seed-count", str(cfg["seed_count"]),
        "--chunk-index", str(chunk),
        "--chunk-size", str(cfg["chunk_size"]),
        "--epochs", str(cfg["epochs"]),
        "--num-agents", str(cfg["num_agents"]),
        "--out", str(out_dir),
        "--artifact", artifact,
    ]
    return command, Path(out_dir) / artifact


def _tier_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    if str(_RUNNER_DIR) not in sys.path:
        sys.path.insert(0, str(_RUNNER_DIR))
    from campaign_runner import generate_tier_runs

    manifest = json.loads(
        (REPO_ROOT / args.manifest).read_text(encoding="utf-8"),
    )
    tier = block["tier"]
    for index, (run_id, spec) in enumerate(generate_tier_runs(manifest, tier)):
        if int(spec["run"]["random_seed"]) == int(seed):
            command = [
                sys.executable, block["worker"],
                "--manifest", str(args.manifest),
                "--tier", tier,
                "--index", str(index),
                "--pathogen-id", str(args.pathogen_id),
                "--out", str(out_dir),
            ]
            return command, Path(out_dir) / tier / f"{run_id}.zip"
    raise SystemExit(f"seed {seed} not in tier {tier}")


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    os.environ["PYTHONHASHSEED"] = "1"
    if block.get("tier"):
        return _tier_argv(args, block, seed, out_dir)
    return _census_argv(args, block, seed, out_dir)
