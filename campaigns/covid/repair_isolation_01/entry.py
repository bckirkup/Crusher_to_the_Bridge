"""REPAIR-ISOLATION-01 argv hook for the generic campaign entrypoint.

Each block declares ``design``, ``theta`` and ``arm_id`` in its ``args``;
this hook translates (block args, seed) into the cell worker's argv and
names the artifact the entrypoint uploads.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_WORKER = "campaigns/covid/repair_isolation_01/cell.py"


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one (theta, arm_id, seed) cell and its artifact path."""
    artifact = Path(out_dir) / block["artifact"].format(
        seed=seed, platform=args.platform,
    )
    block_args = block["args"]
    command = [
        sys.executable, _WORKER,
        "--design", block_args["design"],
        "--theta", str(block_args["theta"]),
        "--arm", block_args["arm_id"],
        "--seed", str(seed),
        "--out", str(out_dir),
    ]
    return command, artifact
