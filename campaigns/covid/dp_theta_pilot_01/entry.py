"""DP-THETA-PILOT-01 argv hook for the generic campaign entrypoint.

Blocks declare ``theta``/``arm_id``/``num_epochs`` in their ``args`` and
``design`` explicitly; this hook translates (block args, seed) into the
cell worker's argv and names the artifact the entrypoint uploads. The
design is the 120-epoch Checkpoint C theta pilot on the
DP-REPLAY-ENVIRON-01 environs; the ``niid_t1e11_canary`` block's 20 seeds
are the preflight canary.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_DEFAULT_DESIGN = "picard_framework/runs/covid_dp_theta_pilot_01_design.json"
_WORKER = "campaigns/covid/dp_theta_pilot_01/cell.py"


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
        "--num-epochs", str(block_args["num_epochs"]),
    ]
    return command, artifact
