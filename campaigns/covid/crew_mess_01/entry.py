"""CREW-MESS-01 argv hook for the generic campaign entrypoint.

The stock argv shapes (manifest tier, or platform+epochs+seeds) cannot
express a boarding-screen cell: a cell is (theta, arm_id, seed) inside the
design JSON's enumeration. Each block declares ``theta``/``arm_id`` in its
``args``; this hook translates (block args, seed) into the cell worker's
argv and names the artifact the entrypoint uploads.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_DESIGN = "picard_framework/runs/covid_crew_mess_01_design.json"
_WORKER = "campaigns/covid/crew_mess_01/cell.py"


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one (theta, arm_id, seed) cell and its artifact path."""
    artifact = Path(out_dir) / block["artifact"].format(
        seed=seed, platform=args.platform,
    )
    command = [
        sys.executable, _WORKER,
        "--design", _DESIGN,
        "--theta", str(block["args"]["theta"]),
        "--arm", block["args"]["arm_id"],
        "--seed", str(seed),
        "--out", str(out_dir),
    ]
    return command, artifact
