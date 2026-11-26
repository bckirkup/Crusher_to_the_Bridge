"""DP-UNION-02 argv hook for the generic campaign entrypoint.

Blocks declare ``theta``/``arm_id`` in their ``args``; this hook translates
(block args, seed) into the shared DP union cell worker's argv and names the
artifact the entrypoint uploads. No horizon is passed: every declared cell
runs the scenario's full declared voyage.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_DEFAULT_DESIGN = "picard_framework/runs/covid_dp_union_02_design.json"
_WORKER = "campaigns/covid/dp_union_01/cell.py"


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one (theta, arm_id, seed) cell and its artifact path."""
    cell_out = Path(out_dir) / args.block
    artifact = cell_out / block["artifact"].format(
        seed=seed, platform=args.platform,
    )
    block_args = block["args"]
    command = [
        sys.executable, _WORKER,
        "--design", block_args.get("design", _DEFAULT_DESIGN),
        "--theta", str(block_args["theta"]),
        "--arm", block_args["arm_id"],
        "--seed", str(seed),
        "--out", str(cell_out),
    ]
    return command, artifact
