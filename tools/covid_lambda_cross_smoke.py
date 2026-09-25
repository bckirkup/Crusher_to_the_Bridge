"""Local preflight smoke for covid_lambda_cross_v1 (campaign-preflight 1).

Proves the three things the frozen design assumes, before any Batch cell runs:

1. Spec-lands: the design enumerates the declared 140 cells in point-major
   order (7 thetas x 1 arm x 20 seeds), and every theta point resolves into
   the run spec's ``pathogen_overrides`` — ``theta_profile_overrides`` sets
   ``dose_response.susceptibility_scale = theta * (alpha + beta) / alpha``,
   so the swept value is asserted against the spec, not the design JSON.
2. Runtime binding: truncated runs at the grid's top and bottom thetas read
   back the resolved ``susceptibility_scale`` on the live engine and the
   ratio must equal the theta ratio — a spec-lands-but-inert theta axis is
   a bug signature, not physics.
3. Contract: ``cell_payload`` on the truncated runs still carries the
   declared fields (observables, index geometry, arm attribution block).

Shared enumeration / truncated-run machinery lives in
``tools/covid_assay_smoke.py``; this tool keeps only the theta-axis checks.

Usage:
    python3 tools/covid_lambda_cross_smoke.py \
        [--design picard_framework/runs/covid_lambda_cross_v1_design.json]
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    enumerate_cells,
)
from picard_framework.covid_theta_fit import load_covid_profile
from tools.covid_assay_smoke import (
    check_enumeration,
    load_declared_cells,
    prepare_cell_run_spec,
    repo_root_of,
    run_cell,
)

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_lambda_cross_v1_design.json",
)
RUN_EPOCHS = 48


def expected_susceptibility_scale(profile: dict[str, Any], theta: float) -> float:
    """The scale theta_profile_overrides declares for a given theta."""
    dr = profile["dose_response"]
    return theta * (dr["alpha"] + dr["beta"]) / dr["alpha"]


def spec_susceptibility_scale(design: Any, cell: Any, repo_root: str) -> float:
    """The dose_response scale the run spec carries for one cell's theta."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=24, repo_root=repo_root,
    )
    return float(
        raw["pathogen_overrides"][PATHOGEN_ID]["dose_response"][
            "susceptibility_scale"
        ],
    )


def engine_susceptibility_scale(tx_core: Any, pathogen_id: str) -> float:
    """The scale the live engine parses — the runtime read-back."""
    return float(
        tx_core.pathogen_profiles[pathogen_id]["dose_response"][
            "susceptibility_scale"
        ],
    )


def check_theta_spec_lands(  # pragma: no cover - CLI-driven check
    design: Any, repo_root: str,
) -> dict[str, float]:
    """Every theta point must reach the spec's dose_response block."""
    profile = load_covid_profile(repo_root)
    seen: dict[float, float] = {}
    for cell in enumerate_cells(design):
        if cell.theta in seen:
            continue
        landed = spec_susceptibility_scale(design, cell, repo_root)
        expected = expected_susceptibility_scale(profile, cell.theta)
        assert abs(landed - expected) < 1e-6 * expected, (
            f"theta {cell.theta}: spec susceptibility_scale {landed} "
            f"!= expected {expected}"
        )
        seen[cell.theta] = landed
    return seen


def _cell_at(design: Any, theta: float, seed: int) -> Any:
    return next(
        c for c in enumerate_cells(design)
        if c.theta == theta and c.seed == seed
    )


def main() -> None:  # pragma: no cover - CLI driver, exercised by hand
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--design", default=DESIGN_REL)
    parser.add_argument("--seed", type=int, default=20200205)
    parser.add_argument(
        "--spec-only",
        action="store_true",
        help="enumeration + spec-lands checks only, no engine runs",
    )
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design, declared_cells = load_declared_cells(repo_root, args.design)
    report: dict[str, Any] = {"design_id": design.design_id}
    report["cell_blocks"] = check_enumeration(design, declared_cells)
    print(f"enumeration: {declared_cells} cells")

    landed = check_theta_spec_lands(design, repo_root)
    print(f"spec-lands: {len(landed)} theta points resolve")

    if not args.spec_only:
        thetas = sorted(landed)
        hi, lo = thetas[-1], thetas[0]
        runs: dict[float, Any] = {}
        for theta in (hi, lo):
            cell = _cell_at(design, theta, args.seed)
            runs[theta] = run_cell(
                design, cell, repo_root, RUN_EPOCHS,
                extra_readback=lambda sim: {
                    "engine_susceptibility_scale": engine_susceptibility_scale(
                        sim.tx_core, PATHOGEN_ID,
                    ),
                },
            )
            print(
                f"theta={theta}: engine_scale="
                f"{runs[theta]['engine_susceptibility_scale']} "
                f"recorded={runs[theta]['recorded_onsets']}",
            )
        ratio = (
            runs[hi]["engine_susceptibility_scale"]
            / runs[lo]["engine_susceptibility_scale"]
        )
        expected_ratio = hi / lo
        report["theta_axis_binding"] = {
            "observed_ratio": ratio,
            "expected_ratio": expected_ratio,
        }
        assert abs(ratio - expected_ratio) < 1e-9, (
            f"engine susceptibility scale ratio {ratio:.6f} != "
            f"theta ratio {expected_ratio:.6f} — the theta axis "
            "does not bind the hazard rate"
        )

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
