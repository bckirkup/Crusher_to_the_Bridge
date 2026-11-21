"""QUAR-TAIL-SEAM-01 argv hook for the generic campaign entrypoint.

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

_DESIGN = "picard_framework/runs/covid_quar_tail_01_design.json"
_WORKER = "campaigns/covid/quar_tail_01/cell.py"


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    """Argv for one (theta, arm_id, seed) cell and its artifact path.

    The worker writes ``cell_<seed>.json`` inside its --out directory; the
    out dir is arm-scoped so a local multi-block run (``scripts/campaign
    run`` shares one ``out/<campaign>`` across blocks) does not overwrite
    a previous arm's cell at the same seed. On Batch each array child gets
    a fresh scratch dir, so the subdir is a no-op there.
    """
    work_dir = Path(out_dir) / str(block["args"]["arm_id"])
    artifact = work_dir / block["artifact"].format(
        seed=seed, platform=args.platform,
    )
    command = [
        sys.executable, _WORKER,
        "--design", _DESIGN,
        "--theta", str(block["args"]["theta"]),
        "--arm", block["args"]["arm_id"],
        "--seed", str(seed),
        "--out", str(work_dir),
    ]
    return command, artifact
