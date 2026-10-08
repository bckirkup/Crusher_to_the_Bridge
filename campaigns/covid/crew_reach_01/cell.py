#!/usr/bin/env python3
"""CREW-REACH-01 cell worker: run one (theta, arm_id, seed) screen cell.

Same composition as the ONSET-REC-01 worker: the design's
``base_overrides`` block (the boxed crew-mess configuration, verbatim
from ``covid_crew_mess_01_design.json`` arm ``sect_mess_boxed``) is
applied to every cell's run spec AFTER ``prepare_cell_run_spec``
composes the arm's own overrides. The arm grammar has no design-level
base and requires the first arm to carry empty overrides, so the boxed
base is declared once in the design and composed here — on
``boxed_declared`` (empty overrides) the resolved spec is boxed +
nothing; on the S1/S2 arms it is boxed + the declared observation
channels (``observation_overrides`` writes only
``config_overrides.syndromic`` — disjoint from the boxed transmission
overrides, so the composition is order-independent).

``--num-epochs`` caps the voyage for local smoke validation only; Batch
runs always take the design's full declared voyage.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    QuarantineAttributionLedger,
    apply_arm_overrides,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    load_covid_profile,
    run_fit_spec,
)

_DESIGN = "picard_framework/runs/covid_crew_reach_01_design.json"


def base_overrides(repo_root: Path = _REPO_ROOT) -> dict:
    """The design's declared shared base (boxed crew-mess block)."""
    raw = json.loads(
        (repo_root / _DESIGN).read_text(encoding="utf-8"),
    )
    return dict(raw.get("base_overrides") or {})


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


def run_reach_cell(
    design: object, cell: object, *, num_epochs: int | None = None,
) -> dict:
    """Run one cell: base_overrides composed under the arm's overrides."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=str(_REPO_ROOT),
    )
    base = base_overrides()
    if base:
        apply_arm_overrides(
            raw, base,
            profile=load_covid_profile(str(_REPO_ROOT)),
            theta=cell.theta,
        )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(
        raw, repo_root=str(_REPO_ROOT), epoch_observer=ledger.observe,
    )
    return cell_payload(design, cell, sim, ledger, raw)


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
    runner = run_reach_cell
    if args.num_epochs is not None:
        import functools
        runner = functools.partial(run_reach_cell, num_epochs=args.num_epochs)
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **runner(design, cell),
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
