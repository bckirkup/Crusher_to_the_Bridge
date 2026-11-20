#!/usr/bin/env python3
"""THETA-REFIT-01 readout: audited merge of the refit + held-out surface.

Scans a directory of cell payloads (the S3 prefix synced flat or per-block),
audits them, then hands the stored observables to the same merge machinery
the first-look fits used: ``merge_fit`` selects Theta on the training hull
(covid.T1 + covid.T3, log-residual, equal weights, mean loss over seeds,
bootstrap selection frequency, boundary-pinned flag); ``merge_held_out``
scores Greg Mortimer at the selected Theta and its half-decade neighbours.
No held-out quantity feeds back into the selection — the merge order is the
split enforcement.

Audit refuses a readout that is incomplete, on the wrong scenario, or whose
resolved repair toggles are not the shipped post-B1-B3 defaults
(ambient_on / two_box / airflow / extract / ContamTransportEngine).
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

from picard_framework.covid_first_look import (  # noqa: E402  # noqa: E402
    FIT_PHASE,
    HELD_OUT_PHASE,
    FirstLookDesign,
    PhaseDesign,
    merge_fit,
    merge_held_out,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    candidate_grid,
)

DP_SCENARIO = "diamond_princess_2020"
GM_SCENARIO = "greg_mortimer_2020"
DP_SEEDS = list(range(20200205, 20200225))
GM_SEEDS = list(range(20200205, 20200255))

# The shipped post-B1-B3 defaults every cell must prove it ran under —
# the same witness check REPAIR-ISOLATION-01's audit applies.
_EXPECTED_TOGGLES = {
    "room_air_removal.map_arm": "ambient_on",
    "near_field_air.mode": "two_box",
    "pathogen_pool_transport": "airflow",
    "duty0_terminal_mode": "extract",
}
_EXPECTED_ENGINE = "ContamTransportEngine"
_EXPECTED_DESIGN = {
    DP_SCENARIO: "covid_theta_refit_01_dp",
    GM_SCENARIO: "covid_theta_refit_01_gm",
}
_EXPECTED_ARM = "baseline"


def _grid() -> tuple[float, ...]:
    """The declared candidate grid: fitted 7.9e6 + half-decades 1e7..1e12."""
    return (7.9e6,) + candidate_grid(1e7, 1e12, 11)


def _design() -> FirstLookDesign:
    return FirstLookDesign(
        design_id="covid_theta_refit_01",
        grid=_grid(),
        fit=PhaseDesign(
            phase=FIT_PHASE, scenario_id=DP_SCENARIO, split_role="training",
            seed_base=DP_SEEDS[0], seeds=len(DP_SEEDS),
        ),
        held_out=PhaseDesign(
            phase=HELD_OUT_PHASE, scenario_id=GM_SCENARIO,
            split_role="held_out", seed_base=GM_SEEDS[0], seeds=len(GM_SEEDS),
        ),
        takeoff_recorded_onsets=10,
        bootstrap_resamples=2000,
        bootstrap_seed=20200205,
    )


def _cell_key(phase: str, scenario: str, theta: float, seed: int) -> str:
    exponent = f"{math.log10(theta):.2f}".replace(".", "p")
    return f"{phase}_{scenario}_theta1e{exponent}_seed{seed}.json"


def _resolved_toggles(payload: dict) -> dict[str, str | None]:
    delivery = payload.get("delivery") or {}
    room = delivery.get("room_air_removal") or {}
    near = delivery.get("near_field_air") or {}
    return {
        "room_air_removal.map_arm": room.get("map_arm"),
        "near_field_air.mode": near.get("mode"),
        "pathogen_pool_transport": delivery.get("pathogen_pool_transport"),
        "duty0_terminal_mode": delivery.get("duty0_terminal_mode"),
    }


def _load_cells(cells_dir: Path) -> tuple[dict[str, dict], list[str]]:
    """First-look-shaped payload dict + audit findings."""
    payloads: dict[str, dict] = {}
    findings: list[str] = []
    for path in sorted(cells_dir.rglob("cell_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        cell = payload.get("cell") or {}
        scenario = str(cell.get("scenario_id"))
        theta = float(cell.get("theta"))
        seed = int(cell.get("seed"))
        if scenario == DP_SCENARIO:
            phase = FIT_PHASE
        elif scenario == GM_SCENARIO:
            phase = HELD_OUT_PHASE
        else:
            findings.append(f"{path.name}: unknown scenario {scenario!r}")
            continue
        cell_findings: list[str] = []
        want_design = _EXPECTED_DESIGN[scenario]
        got_design = payload.get("design_id")
        if got_design != want_design:
            cell_findings.append(
                f"{path.name}: design_id {got_design!r} (want {want_design!r})"
            )
        got_arm = cell.get("arm_id")
        if got_arm != _EXPECTED_ARM:
            cell_findings.append(
                f"{path.name}: arm_id {got_arm!r} (want {_EXPECTED_ARM!r})"
            )
        resolved = _resolved_toggles(payload)
        for key, want in _EXPECTED_TOGGLES.items():
            got = resolved[key]
            if got != want:
                cell_findings.append(
                    f"{path.name}: wrong toggle {key}={got!r} (want {want!r})"
                )
        engine = (payload.get("delivery") or {}).get(
            "transport_engine_resolved")
        if engine != _EXPECTED_ENGINE:
            cell_findings.append(
                f"{path.name}: resolved engine {engine!r} "
                f"(want {_EXPECTED_ENGINE!r})"
            )
        key = _cell_key(phase, scenario, theta, seed)
        if key in payloads:
            findings.append(f"{path.name}: duplicate cell {key}")
            continue
        if cell_findings:
            findings.extend(cell_findings)
            continue
        payloads[key] = {"observables": payload["observables"]}
    return payloads, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-dir", required=True, type=Path)
    parser.add_argument("--allow-partial", action="store_true",
                        help="merge whatever cells are present (canary)")
    args = parser.parse_args(argv)

    payloads, findings = _load_cells(args.cells_dir)
    for f in findings:
        print(f"AUDIT {f}")
    print(f"cells: {len(payloads)} loaded, {len(findings)} audit findings")

    design = _design()
    fit = merge_fit(
        design, payloads,
        allow_partial=args.allow_partial,
    )
    print("\n=== FIT (training hull: Diamond Princess) ===")
    for c in fit.candidates:
        print(
            f"  theta={c.theta:.4g}  mean_loss={c.mean_loss:.4f}  "
            f"takeoff_p={c.takeoff_probability:.2f}  "
            f"positives med={c.as_dict()['campaign_positives']['median']}  "
            f"onsets med={c.as_dict()['recorded_onsets']['median']}  "
            f"n={len(c.seeds)}"
        )
    print(f"selected theta={fit.theta:.4g}  mean_loss={fit.mean_loss:.4f}  "
          f"boundary_pinned={fit.boundary_pinned}")
    print(f"selection frequency: {fit.selection_frequency}")
    if fit.partial:
        print(f"coverage: {fit.coverage}")

    held_cells = [k for k in payloads if k.startswith(f"{HELD_OUT_PHASE}_")]
    if held_cells:
        held = merge_held_out(
            design, payloads, fit.theta,
            allow_partial=args.allow_partial,
        )
        print(
            "\n=== HELD OUT (Greg Mortimer, scored at fitted theta + neighbours) ==="
        )
        print(json.dumps(held, indent=2, sort_keys=True))
    else:
        print("\n=== HELD OUT: no held-out cells present — skipped (fit-only readout)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
