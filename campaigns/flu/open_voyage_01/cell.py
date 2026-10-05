#!/usr/bin/env python3
"""FLU-OPEN-01 cell worker: one open-voyage ``influenza_a`` run per
(platform, seed) cell.

The spec is the conditioned-census spec minus ``scenario_schedule`` —
isolated ``influenza_a`` on the active bundle, an explicit 2-passenger
index pair at epoch 0, the shipped boarding-prevalence draw, shipped
constants, and the observation/escalation stack left free-running
(``confinement="organic"``). Design + frozen verdict frames live in
``DESIGN.md`` beside this file.

Payload is the cell artifact ``cell_<seed>.json``: funnel counts,
per-band presentation/severity tallies, caregiver reach, organic
confinement witnesses, and the complement histograms the readout needs
to compute implied expectations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.infection_dynamics_bridge import ever_presented  # noqa: E402
from engines.natural_history import host_age_band  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from tools.diag.conditioned_cell import ACTIVE, conditioned_spec  # noqa: E402
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402

_PATHOGEN_FALLBACK = "influenza_a"


def _infection_rows(
    agents: list[Any],
    pathogen_id: str,
    ever_ill: set[int],
    ever_reported: set[int],
) -> list[dict[str, Any]]:
    """One row per agent ever infected with *pathogen_id*."""
    rows = []
    for ag in agents:
        inf = ag.infections.get(pathogen_id)
        if inf is None:
            continue
        routes = dict(inf.get("acquired_particles_by_route") or {})
        rows.append(
            {
                "id": ag.agent_id,
                "role": getattr(ag, "role", "") or "",
                "band": host_age_band(ag) or "unbanded",
                "ill": ag.agent_id in ever_ill,
                "reported": ag.agent_id in ever_reported,
                "presented": ever_presented(inf),
                "severity_peak": inf.get("symptom_severity_peak"),
                "infection_epoch": inf.get("infection_epoch"),
                "onset_time_infected": inf.get("onset_time_infected"),
                "index": inf.get("infection_epoch") == 0,
                "routes": routes,
                "dominant_route": (max(routes, key=routes.get) if routes else None),
            }
        )
    return rows


def _complement(agents: list[Any]) -> dict[str, Any]:
    """Band/role histograms over the whole complement."""
    roles: dict[str, int] = {}
    bands: dict[str, int] = {}
    for ag in agents:
        role = getattr(ag, "role", "") or "unknown"
        roles[role] = roles.get(role, 0) + 1
        band = host_age_band(ag) or "unbanded"
        bands[band] = bands.get(band, 0) + 1
    return {"total": len(agents), "roles": roles, "bands": bands}


def run_cell(
    *,
    platform: str,
    seed: int,
    epochs: int,
    pathogen_id: str,
    bundle: str,
) -> dict[str, Any]:
    """Run the open voyage and return the cell payload."""
    spec_dict, _profile = conditioned_spec(
        bundle=bundle,
        pathogen_id=pathogen_id,
        seed=seed,
        platform=platform,
        epochs=epochs,
        confinement="organic",
    )
    with materialized_picard_spec(spec_dict, _REPO_ROOT) as picard_spec:
        sim = ShipSimulation(picard_spec, display=False)
        result = sim.run()
    state = sim.state
    ever_ill = set(getattr(state, "ever_ill_ids", set()) or set())
    ever_reported = set(getattr(state, "ever_reported_ids", set()) or set())
    quarantined = set(getattr(state, "quarantined_ids", set()) or set())
    isolated = set(getattr(state, "isolated_ids", set()) or set())
    ever_infected = set(
        getattr(state, "ever_infected_ids", set()) or set(),
    )
    rows = _infection_rows(
        sim.engine.agents,
        pathogen_id,
        ever_ill,
        ever_reported,
    )
    return {
        "schema": "flu_open_voyage_01.v1",
        "seed": seed,
        "platform": platform,
        "pathogen_id": pathogen_id,
        "bundle": bundle,
        "epochs": epochs,
        "engine_git_sha": os.environ.get("ENGINE_GIT_SHA") or "unknown",
        "final_trigger_status": result.final_trigger_status,
        "counts": {
            "ever_infected": len(rows),
            "ever_infected_state": len(ever_infected),
            "ever_ill": len(ever_ill),
            "ever_reported": len(ever_reported),
            "index_cases": sum(1 for r in rows if r["index"]),
            "onboard_acquired": sum(1 for r in rows if not r["index"]),
            "quarantined_end": len(quarantined),
            "isolated_end": len(isolated),
        },
        "complement": _complement(sim.engine.agents),
        "caregiver_telemetry": dict(
            getattr(sim.tx_core, "caregiver_telemetry", {}) or {},
        ),
        "infections": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--seeds", required=True, help="single seed for this array child")
    parser.add_argument("--pathogen-id", default=_PATHOGEN_FALLBACK)
    parser.add_argument("--bundle", default=ACTIVE)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    seed = int(args.seeds)
    payload = run_cell(
        platform=args.platform,
        seed=seed,
        epochs=args.epochs,
        pathogen_id=args.pathogen_id,
        bundle=args.bundle,
    )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{seed}.json"
    artifact.write_text(
        json.dumps(payload, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
