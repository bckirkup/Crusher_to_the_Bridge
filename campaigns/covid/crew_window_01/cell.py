#!/usr/bin/env python3
"""CREW-WINDOW-01 cell worker: run one (theta, arm_id, seed) screen cell.

One array child of the generic campaign entrypoint resolves its seed; the
block's ``args`` carry the theta and arm_id the entrypoint cannot express
(``entry.py build_argv``). The worker runs ``run_cell`` from
``picard_framework.covid_boarding_screen`` — the same function the legacy
``covid_boarding_screen_entrypoint.py`` called — and writes the payload as
the cell artifact the entrypoint uploads.

``--num-epochs`` caps the voyage for local smoke validation only; Batch
runs always take the design's full declared voyage.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
    run_cell,
    simulate_screen_cell,
)


def _match_cell(
    design: object, theta: float, arm_id: str, seed: int,
) -> object:
    """The single design cell at (theta, arm_id, seed), or die."""
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
                        help="smoke cap on voyage epochs (local only)")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / args.design))
    cell = _match_cell(design, args.theta, args.arm, args.seed)
    runner = simulate_screen_cell
    if args.num_epochs is not None:
        runner = functools.partial(
            simulate_screen_cell, num_epochs=args.num_epochs,
        )
    payload = run_cell(design, cell, runner=runner)

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
