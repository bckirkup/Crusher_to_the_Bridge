#!/usr/bin/env python3
"""DP-THETA-PILOT-01 cell worker: run one (theta, arm_id, seed) cell.

Checkpoint C of THETA_AFTER_BEHAVIOR on the DP-REPLAY-ENVIRON-01 environs:
five log-spaced thetas across the DP-REPLAY-DOSE-DIAG-01 measured window on
24 matched seeds, at the declared 120-epoch horizon. The design declares the
arms; ``platform_id``/protocol keys in ``replay_niid`` rewrite the catalog
inside ``prepare_cell_run_spec``. ``--num-epochs`` is the pilot's *declared*
cell horizon (120), not a smoke cap — the pilot's unit of measurement is the
index-only 120 h window the diagnostic measured, so secondary compounding
past that window is out of scope by declaration, not by convenience.

The worker composes the PLATFORM-FIDELITY-02 machinery verbatim: that
module's ``run_pf_cell`` (arm overrides + declared base + fired-SOP echo +
quarantine attribution) plus the ``dp_theta_pilot`` block recording the
declared horizon and resolved cell coordinates. Loaded via
``importlib.util`` the same way campaign readouts chain earlier readouts.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import enumerate_cells  # noqa: E402

_PF02_CELL = _REPO_ROOT / "campaigns/covid/platform_fidelity_02/cell.py"


def _load_pf02_cell() -> Any:
    """PLATFORM-FIDELITY-02's cell machinery, loaded like a chained readout."""
    spec = importlib.util.spec_from_file_location("pf02_cell", _PF02_CELL)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {_PF02_CELL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _match_cell(design: object, theta: float, arm_id: str, seed: int) -> object:
    matches = [
        cell for cell in enumerate_cells(design)
        if cell.arm_id == arm_id and cell.seed == seed
        and math.isclose(cell.theta, theta, rel_tol=1e-12)
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"{len(matches)} cells match theta={theta} arm={arm_id} "
            f"seed={seed}; expected exactly 1",
        )
    return matches[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True,
                        help="repo-relative boarding-screen design JSON")
    parser.add_argument("--theta", required=True, type=float)
    parser.add_argument("--arm", required=True, help="design arm_id")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True,
                        help="directory the cell artifact is written to")
    parser.add_argument("--num-epochs", type=int, default=None,
                        help="declared cell horizon (120 for this pilot)")
    args = parser.parse_args(argv)

    pf02 = _load_pf02_cell()
    design, raw_design, design_path = pf02._load_design_with_base(args.design)
    cell = _match_cell(design, args.theta, args.arm, args.seed)
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **pf02.run_pf_cell(
            design, cell,
            raw_design=raw_design,
            design_path=design_path,
            num_epochs=args.num_epochs,
        ),
        "dp_theta_pilot": {
            "declared_num_epochs": args.num_epochs,
            "theta": cell.theta,
            "arm_id": cell.arm_id,
            "seed": cell.seed,
        },
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{args.seed}.json"
    artifact.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
