#!/usr/bin/env python3
"""Contact/behaviour binding-constant witness for NORO-HAND-CASCADE-01.

Runs the posted ``carriers_ordered`` M=1 cell with the same read-only
fomite/cascade wrappers as ``hand_cascade_witness``, plus the hand-occupancy
census. The payload reports the realised activity named by
``NORO-HAND-CASCADE-01-CONTACT-AUDIT`` as the next diagnostic: hand occupancy
against the Liu rinse LOD, sanitary visits and dwell realised, deposit and
delivery calls by call site, carrier mass entering surface/food/sanitary
routes, and acquired dose by transmission route. The wrappers call the
engine originals first and only read state; they draw no RNG and write no
engine state.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.instrument_common import (  # noqa: E402
    attr_patches,
    install_wrappers,
    materialized_picard_spec,
)
from tools.diag.manifest_args import identifier  # noqa: E402
from tools.noro_diag import fomite_mass_balance as fmb  # noqa: E402
from tools.noro_diag import hand_cascade_witness as witness  # noqa: E402
from tools.noro_diag import hand_occupancy  # noqa: E402

ARM = "carriers_ordered"


def _route_attribution(sim: Any, pathogen_id: str) -> dict[str, Any]:
    """Acquired-dose route ledger read after the voyage, per infected host."""
    agents = getattr(getattr(sim, "engine", None), "agents", []) or []
    dominant_counts: Counter[str] = Counter()
    dose_by_route: dict[str, float] = defaultdict(float)
    hosts = 0
    for agent in agents:
        infections = getattr(agent, "infections", {}) or {}
        infection = infections.get(pathogen_id) or {}
        ledger = infection.get("acquired_particles_by_route") or {}
        total = sum(float(dose) for dose in ledger.values())
        if total <= 0.0:
            continue
        hosts += 1
        dominant = max(ledger.items(), key=lambda item: float(item[1]))[0]
        dominant_counts[str(dominant)] += 1
        for route, dose in ledger.items():
            dose_by_route[str(route)] += float(dose)
    return {
        "hosts_with_route_ledger": hosts,
        "dominant_route_counts": dict(sorted(dominant_counts.items())),
        "route_dose_gec": {
            route: dose_by_route[route]
            for route in sorted(dose_by_route)
        },
    }


def run_binding(
    *, spec_dict: dict[str, Any], seed: int, pathogen_id: str,
) -> dict[str, Any]:
    """Run one posted cell and return the binding-constant witness row."""
    spec = witness._arm_spec(spec_dict, ARM)
    cfg = spec.get("config_overrides") or {}
    num_agents = int((cfg.get("ship_graph") or {}).get("num_agents") or 0)
    if num_agents <= 0:
        raise ValueError("spec has no ship_graph.num_agents")
    epochs = int(spec["run"]["num_epochs"])

    rec = fmb.Recorder(pathogen_id=pathogen_id)
    rec.occupancy = hand_occupancy.OccupancyRecorder(pathogen_id)
    cascade = witness.CascadeRecorder(pathogen_id)
    with attr_patches() as patches:
        originals = install_wrappers(tc.TransmissionCore, cascade.wrappers())
        patches.note_all(tc.TransmissionCore, originals)
        with (
            materialized_picard_spec(spec, REPO_ROOT) as picard_spec,
            fmb.instrumented(rec),
        ):
            sim = ShipSimulation(picard_spec, display=False)
            sim.run()
            tx_core = getattr(sim, "tx_core", None)
            route = _route_attribution(sim, pathogen_id)
            sanitary = dict(
                getattr(tx_core, "sanitary_telemetry", {}) or {},
            )

    summary = fmb.summarise(rec, seed, epochs)
    summary["platform"] = str(spec["catalog"]["platform_id"])
    summary["bundle"] = str(spec["catalog"]["pathogen_bundle_id"])
    summary["num_agents"] = num_agents
    for key in (
        "epoch_timeline",
        "hand_occupancy_rows",
        "stationary_hand_load_rows",
        "hand_carriage_propensities",
    ):
        summary.pop(key, None)
    summary["cascade"] = cascade.as_dict()
    row = witness._row(summary, summary["cascade"])
    row["arm"] = f"{ARM}_binding"
    row["config_overrides"] = witness.ARMS[ARM]
    row["run_id"] = spec.get("description")
    row["hand_occupancy"] = summary.get("hand_occupancy")
    row["sanitary_telemetry"] = sanitary
    row["route_attribution"] = route
    return row


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tier", type=str, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--pathogen-id", type=identifier, default="norwalk_gi")
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    specs = witness.tier_specs(args.manifest, args.tier, args.seeds)
    rows = []
    for seed in args.seeds:
        row = run_binding(
            spec_dict=specs[int(seed)], seed=int(seed),
            pathogen_id=args.pathogen_id,
        )
        rows.append(row)
        occ = row.get("hand_occupancy") or {}
        san = row.get("sanitary_telemetry") or {}
        route = row.get("route_attribution") or {}
        print(
            f"binding seed {seed}: infected {row['hosts_infected']}, "
            f"symptomatic {row['hosts_symptomatic']}, dose {row['dose_gec']:.6g}, "
            f"delivered {row['delivered_all_paths_gec']:.6g}, "
            f"deposited {row['deposited_gec']:.6g}, "
            f"hand+ {occ.get('positive_rows')}/{occ.get('shedding_rows')}, "
            f"sanitary visits {san.get('visits', 0)}, "
            f"route hosts {route.get('hosts_with_route_ledger', 0)}",
        )
    payload = {
        "tier": args.tier,
        "manifest": str(args.manifest),
        "pathogen_id": args.pathogen_id,
        "arm": ARM,
        "rows": rows,
    }
    path = resolve_child_path(
        str(out_dir), f"contact_binding_{args.tier}.json.gz",
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, default=str)
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
