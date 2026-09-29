"""COVID-COOP-02 canary: one takeoff cell under the cooperative-packet arm.

    python3 tools/covid_coop_arm_canary.py \
        --design picard_framework/runs/covid_theta_screen_v12_stage2_design.json \
        --theta 2.37e11 --seeds 20200205 \
        --n-star 3 --mu-dry 0.05 --mu-wet 20.0 [--epochs N] [--out out.json]

The run is the instrumented takeoff cell with only the pathogen's
``dose_response`` override switched to ``cooperative_packet``: the theta
composite stays on ``susceptibility_scale`` and the beta frailty draw is
unchanged, so the delta against the beta-Poisson cell isolates the dose
law. ``carrier_loading`` is a declared point inside the COVID-COOP-01
occupancy envelopes (dry [0.004, 0.1], wet [0.04, 500]).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from simulation_utils.paths import resolve_repo_path, validated_open
from tools.covid_assay_smoke import repo_root_of
from tools.covid_takeoff_attribution import analyse_spec


def coop_override(
    raw: dict,
    n_star: int,
    mu_dry: float,
    mu_wet: float,
) -> dict:
    """The same spec with the pathogen's dose law switched to the arm.

    Only the arm's declared fields are touched: alpha, beta and the
    theta-carried susceptibility_scale ride over from the cell's own
    overrides so the draw stream stays aligned for the A/B.
    """
    patched = copy.deepcopy(raw)
    dose_response = (
        patched.setdefault("pathogen_overrides", {})
        .setdefault(PATHOGEN_ID, {})
        .setdefault("dose_response", {})
    )
    dose_response.update({
        "model": "cooperative_packet",
        "n_star": int(n_star),
        "carrier_loading": {"dry": float(mu_dry), "wet": float(mu_wet)},
    })
    return patched


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--design",
        default="picard_framework/runs/"
                "covid_theta_screen_v12_stage2_design.json",
    )
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument("--seeds", default="20200205")
    parser.add_argument("--n-star", type=int, required=True)
    parser.add_argument("--mu-dry", type=float, required=True)
    parser.add_argument("--mu-wet", type=float, required=True)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design = load_design(os.path.join(repo_root, args.design))
    seeds = {int(s) for s in args.seeds.split(",")}
    cells = [
        c for c in enumerate_cells(design)
        if c.seed in seeds and abs(c.theta - args.theta) < args.theta * 0.001
    ]
    if not cells:
        raise SystemExit(
            f"no cells match theta={args.theta} seeds={sorted(seeds)}",
        )

    results = []
    for cell in cells:
        raw = prepare_cell_run_spec(
            design, cell, num_epochs=args.epochs, repo_root=repo_root,
        )
        result = analyse_spec(
            coop_override(raw, args.n_star, args.mu_dry, args.mu_wet),
            design, cell, repo_root=repo_root,
        )
        result["coop_arm"] = {
            "model": "cooperative_packet",
            "n_star": args.n_star,
            "carrier_loading": {"dry": args.mu_dry, "wet": args.mu_wet},
        }
        results.append(result)
    text = json.dumps(results, indent=1, default=str)
    if args.out:
        resolved = resolve_repo_path(repo_root, args.out)
        with validated_open(
            resolved, "w", allowed_roots=(repo_root,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {resolved}")
    else:
        print(text)


if __name__ == "__main__":
    main()
