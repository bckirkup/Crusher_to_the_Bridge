#!/usr/bin/env python3
"""FLU-VIS-01 cell worker: one open-voyage ``influenza_a`` run per
(platform, seed, visibility arm) cell.

Same spec as FLU-OPEN-01 (``conditioned_spec`` with
``confinement="organic"``) plus a per-arm ``observation_model`` patch
injected through ``pathogen_overrides``: ``--report-scale`` multiplies
both reporting vectors (clip 1.0) and ``--eligibility-corner`` rewrites
``syndrome_case_eligibility_by_severity``. Arm semantics and the frozen
reading frames live in ``DESIGN.md`` beside this file.

Payload is ``cell_<seed>.json``: the OPEN-01 contract (funnel counts,
per-band tallies, caregiver reach, confinement witnesses) plus the
**resolved** severity model the engine used, the escalation log
(recognition timing), and onset-observation severity counts (the
eligibility mechanism witness).
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
_MILD_STATE = "mild"
_ELIGIBILITY_CORNERS = ("declared", "strict")


def _observation_patch(
    profile: dict[str, Any],
    report_scale: float,
    eligibility_corner: str,
) -> dict[str, Any]:
    """The arm's ``observation_model`` patch, computed from the shipped
    vectors so the arm stays self-describing if the profile moves."""
    observation = profile.get("observation_model") or {}
    states = (profile.get("severity_model") or {}).get("states") or []

    def _scaled(key: str) -> list[float]:
        return [
            min(1.0, float(v) * report_scale)
            for v in (observation.get(key) or [])
        ]

    patch: dict[str, Any] = {
        "reporting_probability_by_severity_pre_recognition": _scaled(
            "reporting_probability_by_severity_pre_recognition",
        ),
        "reporting_probability_by_severity_post_recognition": _scaled(
            "reporting_probability_by_severity_post_recognition",
        ),
    }
    if eligibility_corner == "strict":
        eligibility = list(
            observation.get("syndrome_case_eligibility_by_severity") or [],
        )
        if _MILD_STATE in states and len(eligibility) == len(states):
            eligibility[states.index(_MILD_STATE)] = 0.0
        patch["syndrome_case_eligibility_by_severity"] = eligibility
    elif eligibility_corner != "declared":
        raise ValueError(
            f"unknown eligibility corner {eligibility_corner!r} "
            f"(declared: {_ELIGIBILITY_CORNERS})",
        )
    return patch


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


def _resolved_severity_model(
    sim: ShipSimulation,
    pathogen_id: str,
) -> dict[str, Any] | None:
    """The observation vectors the engine actually ran — the arm-echo
    the audit invariants check against the declared arm."""
    syndromic = (getattr(sim, "modalities", None) or {}).get("syndromic")
    resolver = getattr(syndromic, "_severity_model", None)
    if resolver is None:
        return None
    return resolver(pathogen_id)


def _onset_severity_counts(
    sim: ShipSimulation,
    pathogen_id: str,
) -> dict[str, int]:
    """Dated onsets by severity — the eligibility mechanism witness."""
    syndromic = (getattr(sim, "modalities", None) or {}).get("syndromic")
    counts = getattr(syndromic, "onset_observation_severity_counts", None)
    if counts is None:
        return {}
    return dict(counts(pathogen_id))


def run_cell(
    *,
    platform: str,
    seed: int,
    epochs: int,
    pathogen_id: str,
    bundle: str,
    report_scale: float,
    eligibility_corner: str,
) -> dict[str, Any]:
    """Run the open voyage under the visibility arm and return the payload."""
    spec_dict, profile = conditioned_spec(
        bundle=bundle,
        pathogen_id=pathogen_id,
        seed=seed,
        platform=platform,
        epochs=epochs,
        confinement="organic",
    )
    patch = _observation_patch(profile, report_scale, eligibility_corner)
    spec_dict["pathogen_overrides"].setdefault(pathogen_id, {})[
        "observation_model"
    ] = patch
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
        "schema": "flu_visibility_01.v1",
        "seed": seed,
        "platform": platform,
        "pathogen_id": pathogen_id,
        "bundle": bundle,
        "epochs": epochs,
        "engine_git_sha": os.environ.get("ENGINE_GIT_SHA") or "unknown",
        "arm": {
            "report_scale": report_scale,
            "eligibility_corner": eligibility_corner,
            "patch": patch,
            "resolved": _resolved_severity_model(sim, pathogen_id),
        },
        "final_trigger_status": result.final_trigger_status,
        "escalation_log": [
            dict(e) for e in (getattr(state, "escalation_log", None) or [])
        ],
        "onset_severity_counts": _onset_severity_counts(sim, pathogen_id),
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
    parser.add_argument("--report-scale", type=float, required=True)
    parser.add_argument(
        "--eligibility-corner",
        required=True,
        choices=_ELIGIBILITY_CORNERS,
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    seed = int(args.seeds)
    payload = run_cell(
        platform=args.platform,
        seed=seed,
        epochs=args.epochs,
        pathogen_id=args.pathogen_id,
        bundle=args.bundle,
        report_scale=args.report_scale,
        eligibility_corner=args.eligibility_corner,
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
