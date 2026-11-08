"""PLATFORM-FIDELITY-01 argv hook for the generic campaign entrypoint.

A cell is (design, theta, arm_id, seed) inside a boarding-screen design
JSON's enumeration, and this campaign spans two designs — the Diamond
Princess training pair and the Greg Mortimer held-out pair. Each block
declares ``theta``/``arm_id`` in its ``args`` and, for the GM blocks,
``design``; DP blocks take the default DP design. This hook translates
(block args, seed) into the cell worker's argv and names the artifact the
entrypoint uploads.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_DEFAULT_DESIGN = "picard_framework/runs/covid_platform_fidelity_dp_design.json"
_WORKER = "campaigns/covid/platform_fidelity_01/cell.py"


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
        "--design", block_args.get("design", _DEFAULT_DESIGN),
        "--theta", str(block_args["theta"]),
        "--arm", block_args["arm_id"],
        "--seed", str(seed),
        "--out", str(out_dir),
    ]
    return command, artifact
