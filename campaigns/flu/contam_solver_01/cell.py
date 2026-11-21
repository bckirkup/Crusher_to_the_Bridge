#!/usr/bin/env python3
"""FLU-CONTAM-SOLVER-01 cell worker: paired native vs. ContamX influenza cell.

Runs one open-voyage ``influenza_a`` cell (``conditioned_spec(...,
confinement="organic")``) with ``config_overrides.hvac.transport_engine`` set
to ``native`` or ``contamx``. Fails closed if the resolved transport engine
does not match the declared solver. Records outbreak totals, daily incidence
trajectories, acquisition-route attribution, and split init/run wall and CPU
timing (including ``RUSAGE_CHILDREN`` for the ``contamx3`` subprocess).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.contamx_runner import find_contamx  # noqa: E402
from engines.infection_dynamics_bridge import ever_presented  # noqa: E402
from engines.natural_history import host_age_band  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from tools.diag.conditioned_cell import ACTIVE, conditioned_spec  # noqa: E402
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402

_PATHOGEN_FALLBACK = "influenza_a"
_CONTAMX_SHA256 = (
    "d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b"
)
_CONTAMX_S3_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_CONTAMX_S3_KEY = "campaign/covid_transport_fit_01/vendor/contamx3"
_EXPECTED_ENGINES = {
    "contamx": "ContamXTransportEngine",
    "native": "ContamTransportEngine",
}
_AIRBORNE_ROUTE_KEYS = ("hvac_airborne", "airborne")


def _verify_contamx_sha256(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != _CONTAMX_SHA256:
        raise SystemExit(
            f"contamx binary sha256 mismatch at {path}: got {digest}, "
            f"expected {_CONTAMX_SHA256}",
        )


def _ensure_contamx_binary() -> str:
    """Resolve and SHA-256-verify a runnable NIST ContamX binary."""
    local = find_contamx({})
    if local is not None:
        _verify_contamx_sha256(Path(local))
        return local
    dest = Path(tempfile.mkdtemp(prefix="crusher_contamx_bin_")) / "contamx3"
    import boto3

    client = boto3.client("s3")
    client.download_file(_CONTAMX_S3_BUCKET, _CONTAMX_S3_KEY, str(dest))
    _verify_contamx_sha256(dest)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    os.environ["CONTAMX_BINARY"] = str(dest)
    return str(dest)


def _rusage_snapshot() -> dict[str, float]:
    """Capture user+sys CPU seconds and max RSS for self and child processes."""
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "self_cpu": float(ru_self.ru_utime + ru_self.ru_stime),
        "child_cpu": float(ru_child.ru_utime + ru_child.ru_stime),
        "self_rss_kb": int(ru_self.ru_maxrss),
        "child_rss_kb": int(ru_child.ru_maxrss),
    }


def _first_epoch(inf: dict[str, Any]) -> int | None:
    """First infection epoch for cross-arm comparison."""
    first = inf.get("first_infection_epoch")
    if first is not None:
        return int(first)
    ep = inf.get("infection_epoch")
    return int(ep) if ep is not None else None


def _infection_rows(
    agents: list[Any],
    pathogen_id: str,
    ever_ill: set[int],
    ever_reported: set[int],
) -> list[dict[str, Any]]:
    """One row per agent ever infected with *pathogen_id*."""
    rows: list[dict[str, Any]] = []
    for ag in agents:
        inf = ag.infections.get(pathogen_id)
        if inf is None:
            continue
        routes = {
            k: float(v)
            for k, v in (inf.get("acquired_particles_by_route") or {}).items()
            if v
        }
        first_ep = _first_epoch(inf)
        rows.append(
            {
                "id": ag.agent_id,
                "role": getattr(ag, "role", "") or "",
                "band": host_age_band(ag) or "unbanded",
                "ill": ag.agent_id in ever_ill,
                "reported": ag.agent_id in ever_reported,
                "presented": ever_presented(inf),
                "severity_peak": inf.get("symptom_severity_peak"),
                "first_infection_epoch": first_ep,
                "infection_epoch": inf.get("infection_epoch"),
                "episode_epochs": list(inf.get("episode_epochs") or []),
                "onset_time_infected": inf.get("onset_time_infected"),
                "index": first_ep == 0,
                "routes": routes,
                "dominant_route": (max(routes, key=routes.get) if routes else None),
            }
        )
    return rows


def _complement(agents: list[Any]) -> dict[str, Any]:
    """Role and age-band histograms over the whole ship complement."""
    roles: dict[str, int] = {}
    bands: dict[str, int] = {}
    for ag in agents:
        role = getattr(ag, "role", "") or "unknown"
        roles[role] = roles.get(role, 0) + 1
        band = host_age_band(ag) or "unbanded"
        bands[band] = bands.get(band, 0) + 1
    return {"total": len(agents), "roles": roles, "bands": bands}


def _dynamics_summary(rows: list[dict[str, Any]], epochs: int) -> dict[str, Any]:
    """Daily incidence curve, cumulative trajectory, and timing summaries."""
    n_days = max(1, math.ceil(epochs / 24))  # clock-exempt: 1h campaign epochs binned into 24h voyage days
    daily_new = [0] * n_days
    onboard_epochs: list[int] = []
    for row in rows:
        ep = row["first_infection_epoch"]
        if ep is None:
            continue
        day = min(max(ep // 24, 0), n_days - 1)  # clock-exempt: 1h campaign epochs binned into 24h voyage days
        daily_new[day] += 1
        if not row["index"]:
            onboard_epochs.append(ep)
    cumulative: list[int] = []
    running = 0
    for count in daily_new:
        running += count
        cumulative.append(running)
    peak_daily = max(daily_new) if daily_new else 0
    peak_day = daily_new.index(peak_daily) if peak_daily > 0 else None
    onboard_epochs.sort()
    median_ep = (
        onboard_epochs[len(onboard_epochs) // 2] if onboard_epochs else None
    )
    return {
        "n_days": n_days,
        "daily_new_infections": daily_new,
        "daily_cumulative_infections": cumulative,
        "peak_day": peak_day,
        "peak_daily_new": peak_daily,
        "first_secondary_epoch": onboard_epochs[0] if onboard_epochs else None,
        "median_secondary_epoch": median_ep,
    }


def _route_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Acquisition-route counts and particle totals across onboard infections."""
    dominant_counts: dict[str, int] = {}
    particles_sum: dict[str, float] = {}
    airborne_any = 0
    airborne_dominant = 0
    for row in rows:
        if row["index"]:
            continue
        dom = row["dominant_route"] or "unknown"
        dominant_counts[dom] = dominant_counts.get(dom, 0) + 1
        if dom in _AIRBORNE_ROUTE_KEYS:
            airborne_dominant += 1
        routes = row["routes"]
        if any(routes.get(k, 0.0) > 0.0 for k in _AIRBORNE_ROUTE_KEYS):
            airborne_any += 1
        for route, val in routes.items():
            particles_sum[route] = particles_sum.get(route, 0.0) + val
    return {
        "dominant_route_counts": dominant_counts,
        "particles_by_route_sum": particles_sum,
        "airborne_any_count": airborne_any,
        "airborne_dominant_count": airborne_dominant,
    }


def _verify_solver(sim: ShipSimulation, solver: str) -> str:
    """Verify the resolved transport engine matches *solver* or exit."""
    engine = getattr(sim, "contam_engine", None)
    resolved = type(engine).__name__ if engine is not None else None
    expected = _EXPECTED_ENGINES[solver]
    if resolved != expected:
        raise SystemExit(
            f"declared solver {solver!r} expected {expected!r} but resolved "
            f"{resolved!r}; refusing to emit a fallback result",
        )
    return resolved


def run_cell(
    *,
    platform: str,
    seed: int,
    epochs: int,
    pathogen_id: str,
    bundle: str,
    solver: str,
) -> dict[str, Any]:
    """Run one paired influenza cell and return the structured payload."""
    if solver not in _EXPECTED_ENGINES:
        raise SystemExit(f"unsupported solver {solver!r}; use native or contamx")
    binary_path = _ensure_contamx_binary() if solver == "contamx" else None
    spec_dict, _profile = conditioned_spec(
        bundle=bundle,
        pathogen_id=pathogen_id,
        seed=seed,
        platform=platform,
        epochs=epochs,
        confinement="organic",
    )
    spec_dict.setdefault("config_overrides", {}).setdefault("hvac", {})[
        "transport_engine"
    ] = solver

    ru0 = _rusage_snapshot()
    t0 = time.perf_counter()
    with materialized_picard_spec(spec_dict, _REPO_ROOT) as picard_spec:
        sim = ShipSimulation(picard_spec, display=False)
        sim.initialize()
        t1 = time.perf_counter()
        ru1 = _rusage_snapshot()
        resolved = _verify_solver(sim, solver)
        result = sim.run()
        t2 = time.perf_counter()
        ru2 = _rusage_snapshot()

    state = sim.state
    ever_ill = set(getattr(state, "ever_ill_ids", set()) or set())
    ever_reported = set(getattr(state, "ever_reported_ids", set()) or set())
    quarantined = set(getattr(state, "quarantined_ids", set()) or set())
    isolated = set(getattr(state, "isolated_ids", set()) or set())
    ever_infected = set(getattr(state, "ever_infected_ids", set()) or set())
    rows = _infection_rows(sim.engine.agents, pathogen_id, ever_ill, ever_reported)
    pax_inf = sum(1 for r in rows if r["role"] == "passenger")
    crew_inf = sum(1 for r in rows if r["role"] != "passenger")

    init_self = ru1["self_cpu"] - ru0["self_cpu"]
    init_child = ru1["child_cpu"] - ru0["child_cpu"]
    run_self = ru2["self_cpu"] - ru1["self_cpu"]
    run_child = ru2["child_cpu"] - ru1["child_cpu"]

    return {
        "schema": "flu_contam_solver_01.v1",
        "seed": seed,
        "platform": platform,
        "pathogen_id": pathogen_id,
        "bundle": bundle,
        "epochs": epochs,
        "engine_git_sha": os.environ.get("ENGINE_GIT_SHA") or "unknown",
        "solver": {
            "declared": solver,
            "resolved": resolved,
            "binary": binary_path,
        },
        "timing": {
            "init_wall_s": round(t1 - t0, 4),
            "run_wall_s": round(t2 - t1, 4),
            "total_wall_s": round(t2 - t0, 4),
            "init_cpu_self_s": round(init_self, 4),
            "init_cpu_children_s": round(init_child, 4),
            "run_cpu_self_s": round(run_self, 4),
            "run_cpu_children_s": round(run_child, 4),
            "total_cpu_self_s": round(init_self + run_self, 4),
            "total_cpu_children_s": round(init_child + run_child, 4),
            "total_cpu_s": round(init_self + init_child + run_self + run_child, 4),
            "maxrss_self_kb": ru2["self_rss_kb"],
            "maxrss_children_kb": ru2["child_rss_kb"],
        },
        "final_trigger_status": result.final_trigger_status,
        "counts": {
            "ever_infected": len(rows),
            "ever_infected_state": len(ever_infected),
            "ever_ill": len(ever_ill),
            "ever_reported": len(ever_reported),
            "index_cases": sum(1 for r in rows if r["index"]),
            "onboard_acquired": sum(1 for r in rows if not r["index"]),
            "passenger_infected": pax_inf,
            "crew_infected": crew_inf,
            "quarantined_end": len(quarantined),
            "isolated_end": len(isolated),
        },
        "dynamics": _dynamics_summary(rows, epochs),
        "routes": _route_summary(rows),
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
    parser.add_argument("--seeds", required=True, help="single seed for this child")
    parser.add_argument("--solver", required=True, choices=sorted(_EXPECTED_ENGINES))
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
        solver=args.solver,
    )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{seed}.json"
    artifact.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
