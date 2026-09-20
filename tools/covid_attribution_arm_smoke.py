"""Local smoke for the covid_quarantine_attribution_v1 arm wiring.

For each selected arm this builds the run spec the cell would execute,
prints the read-back of every override channel (so a silently-ignored
override is visible instead of presenting as a null result), runs the cell
with the attribution ledger, and writes the payload JSON. The A5 check
prints the route-level dose accumulators so "the air routes do not matter"
cannot be confused with "the override never reached the engine".

``--v9-witness`` re-runs the v9 design's matching cell and diffs its payload
against A0's: arm A0 is declared to reproduce the v9 cell byte-for-byte
outside the cell block and the new attribution keys.

Usage:
    python3 tools/covid_attribution_arm_smoke.py [--theta 1e5]
        [--seed 20200205] [--num-epochs 432] [--arms A0_declared A5...]
        [--out-dir DIR] [--v9-witness]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (
    QuarantineAttributionLedger,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
    simulate_screen_cell,
)
from picard_framework.covid_theta_fit import PATHOGEN_ID, run_fit_spec

ATTRIBUTION_DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_quarantine_attribution_v1_design.json",
)
V9_DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_theta_screen_v9_design.json",
)
ATTRIBUTION_KEYS = {
    "arm_id",
    "infections_before_quarantine",
    "infections_during_quarantine",
    "infections_after_quarantine",
    "during_quarantine_by_role",
    "during_quarantine_by_zone_class",
    "during_quarantine_by_route",
    "confined_passenger_infections_during_quarantine",
    "quarantine_witness",
}


def _read_back(raw: dict) -> dict:
    """Every channel an arm may override, read from the spec itself."""
    overrides = raw.get("config_overrides", {})
    protocols = overrides.get("scenario_schedule", {}).get("protocols", [])
    pathogen = raw.get("pathogen_overrides", {}).get(PATHOGEN_ID, {})
    return {
        "scenario_schedule": [
            {
                "protocol_id": p.get("protocol_id"),
                "start_day": p.get("start_day"),
                "end_day": p.get("end_day"),
            }
            for p in protocols
        ],
        "hvac.pathogen_pool_transport": overrides.get("hvac", {}).get(
            "pathogen_pool_transport",
        ),
        "transmission.near_field_air": overrides.get("transmission", {}).get(
            "near_field_air",
        ),
        "pathogen_overrides.route_efficiency_multipliers": pathogen.get(
            "route_efficiency_multipliers",
        ),
    }


def _dose_route_sums(sim) -> dict[str, float]:
    """Summed per-route acquired dose over non-seeded infection records."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    totals: dict[str, float] = {}
    for agent in sim.engine.agents:
        if agent.agent_id in seeded:
            continue
        inf = agent.infections.get(PATHOGEN_ID)
        if not inf:
            continue
        for route, dose in (inf.get("acquired_particles_by_route") or {}).items():
            totals[route] = totals.get(route, 0.0) + float(dose)
    return totals


def _run_arm(design, cell, *, num_epochs: int, repo_root: str, out_dir: str):
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    print(f"\n── {cell.arm_id} ({cell.key})")
    print(json.dumps({"read_back": _read_back(raw)}, indent=2))
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=ledger.observe)
    payload = cell_payload(design, cell, sim, ledger, raw)
    path = os.path.realpath(os.path.join(out_dir, cell.key))
    if os.path.commonpath([out_dir, path]) != out_dir:
        raise ValueError(
            f"cell key {cell.key!r} escapes --out-dir {out_dir!r}",
        )
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)

    state = sim.state
    dose_sums = _dose_route_sums(sim)
    record_during = payload["infections_during_quarantine"]
    by_role = payload["during_quarantine_by_role"] or {}
    role_sum = sum(by_role.values())
    if record_during is not None:
        assert role_sum == record_during, (
            f"record-based during count {record_during} != "
            f"event-based role sum {role_sum}"
        )
    print(json.dumps({
        "console_only": {
            "infection_dose_share_by_route": dict(
                getattr(state, "infection_dose_share_by_route", {}),
            ),
            "infections_by_dominant_route": dict(
                getattr(state, "infections_by_dominant_route", {}),
            ),
            "acquired_particles_sums": dose_sums,
            "a5_zero_dose_proof": {
                "droplet": dose_sums.get("droplet", 0.0),
                "hvac_airborne": dose_sums.get("hvac_airborne", 0.0),
            },
            "during_record_vs_role_sum": [record_during, role_sum],
            "quarantine_witness": payload["quarantine_witness"],
        },
    }, indent=2))
    return payload


def _v9_witness(a0_payload: dict, *, theta: float, seed: int,
                num_epochs: int, repo_root: str) -> None:
    v9 = load_design(V9_DESIGN_REL, repo_root=repo_root)
    cell = next(
        c for c in enumerate_cells(v9)
        if math.isclose(c.theta, theta, rel_tol=1e-12)
        and math.isclose(c.infection_age_days, 3.3, rel_tol=1e-12)
        and c.imports == 1 and c.seed == seed
    )
    v9_payload = simulate_screen_cell(
        v9, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    a0_stripped = {
        k: v for k, v in a0_payload.items() if k not in ATTRIBUTION_KEYS
    }
    if v9_payload == a0_stripped:
        print("\nv9 witness: A0 payload equals the v9 cell's payload "
              "outside the cell block and attribution keys")
        return
    print("\nv9 witness: MISMATCH")
    print(json.dumps({
        "a0_only_or_differs": {
            k: a0_stripped.get(k) for k in a0_stripped
            if a0_stripped.get(k) != v9_payload.get(k)
        },
        "v9": {k: v9_payload.get(k) for k in a0_stripped},
    }, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theta", type=float, default=1e5)
    parser.add_argument("--seed", type=int, default=20200205)
    parser.add_argument(
        "--num-epochs", type=int, default=432,
        help="432 epochs = 18 days at 1 h epochs; the quarantine opens day 16",
    )
    parser.add_argument("--arms", nargs="*", default=None)
    parser.add_argument(
        "--out-dir", default="results/covid_attribution_smoke",
    )
    parser.add_argument("--v9-witness", action="store_true")
    parser.add_argument("--repo-root", default=os.getcwd())
    args = parser.parse_args()

    design = load_design(ATTRIBUTION_DESIGN_REL, repo_root=args.repo_root)
    wanted = set(args.arms) if args.arms else set(design.arm_ids)
    cells = [
        c for c in enumerate_cells(design)
        if math.isclose(c.theta, args.theta, rel_tol=1e-12)
        and c.seed == args.seed
        and c.arm_id in wanted
    ]
    if not cells:
        parser.error("no cells matched theta/seed/arms")

    a0_payload = None
    for cell in cells:
        payload = _run_arm(
            design, cell, num_epochs=args.num_epochs,
            repo_root=args.repo_root,
            out_dir=os.path.realpath(args.out_dir),
        )
        if cell.arm_id == design.baseline_arm_id:
            a0_payload = payload

    if args.v9_witness:
        if a0_payload is None:
            parser.error("--v9-witness needs the baseline arm to have run")
        _v9_witness(
            a0_payload, theta=args.theta, seed=args.seed,
            num_epochs=args.num_epochs, repo_root=args.repo_root,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
