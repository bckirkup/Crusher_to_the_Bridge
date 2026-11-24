#!/usr/bin/env python3
"""DP-UNION-01 cell worker: run one (theta, arm_id, seed) union-arm cell.

The Suite-1 union arm of ``docs/covid/covid_theta_unification_plan.md``:
``replay_niid`` plus the quarter-exempt confinement order, symptomatic-crew
removal and the record's armed testing structure, on the scenario's full
declared voyage. The run is PLATFORM-FIDELITY-02's ``run_pf_cell`` and the
``covid.T3`` reduction is DP-THETA-FIT-01's ``t3_block``, both loaded from
their campaign directories rather than copied. This worker adds the
``dp_union`` block the joint contract of
``docs/covid/covid_dp_union_01_design.md`` is scored on, then drops the
per-host echoes so a cell artifact stays small.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FIT_CELL = _REPO_ROOT / "campaigns/covid/dp_theta_fit_01/cell.py"
_DROPPED_ECHOES = ("campaign_specimen_log", "funnel_hosts")


def _load_fit_cell() -> Any:
    """DP-THETA-FIT-01's worker module (``t3_block`` and the PF-02 loader)."""
    spec = importlib.util.spec_from_file_location("dp_fit_cell", _FIT_CELL)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {_FIT_CELL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture_block(
    funnel_hosts: dict[str, dict[str, Any]], reachable_day_max: int,
) -> dict[str, Any]:
    """Conditioned capture (COVID-CAPTURE-01): confirmed / reachable.

    A host is reachable when its infection day is at most
    ``reachable_day_max`` (five days before the last armed campaign day).
    The unconditioned pair is reported beside it.
    """
    infected = [
        entry for entry in funnel_hosts.values()
        if entry.get("infection_day") is not None
    ]
    reachable = [
        entry for entry in infected
        if int(entry["infection_day"]) <= reachable_day_max
    ]

    def _confirmed(entries: list[dict[str, Any]]) -> int:
        return sum(1 for e in entries if e.get("confirmed_day") is not None)

    return {
        "reachable_infection_day_max": reachable_day_max,
        "infections_funnel": len(infected),
        "confirmed_funnel": _confirmed(infected),
        "infections_reachable": len(reachable),
        "confirmed_reachable": _confirmed(reachable),
        "conditioned_capture": (
            _confirmed(reachable) / len(reachable) if reachable else None
        ),
    }


def timing_block(
    total_by_day: dict[str, int], ignition_mass: int,
) -> dict[str, Any]:
    """Acquisitions by day and the ignition day (COVID-IGNITION-01).

    Reads ``acquisition_curve.total_by_day``, which excludes the seeded
    index as that readout does. Ignition day is the first day cumulative
    acquisitions reach ``ignition_mass``; ``None`` when the cell never does.
    """
    by_day = {int(day): int(count) for day, count in total_by_day.items()}
    ignition_day = None
    running = 0
    for day in sorted(by_day):
        running += by_day[day]
        if running >= ignition_mass:
            ignition_day = day
            break
    return {
        "ignition_mass": ignition_mass,
        "ignition_day": ignition_day,
        "infections_by_day": {str(day): by_day[day] for day in sorted(by_day)},
    }


def union_block(
    run: dict[str, Any], contract: dict[str, Any], t3_block: Any,
) -> dict[str, Any]:
    """The per-cell quantities the joint contract reads."""
    log = run["campaign_specimen_log"]
    hosts = run.get("funnel_hosts") or {}
    return {
        "timing": timing_block(
            run["acquisition_curve"]["total_by_day"],
            int(contract["ignition"]["mass"]),
        ),
        "t3": t3_block(log, int(contract["t3"]["through_day_index"])),
        "onboard_table": t3_block(
            log, int(contract["onboard_table"]["through_day_index"]),
        ),
        "capture": capture_block(
            hosts,
            int(contract["conditioned_capture"]["reachable_infection_day_max"]),
        ),
    }


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
                        help="smoke cap only; declared blocks run the full voyage")
    args = parser.parse_args(argv)

    fit = _load_fit_cell()
    pf02 = fit._load_pf02_cell()
    design, raw_design, design_path = pf02._load_design_with_base(args.design)
    cell = fit._match_cell(design, args.theta, args.arm, args.seed)
    run = pf02.run_pf_cell(
        design, cell,
        raw_design=raw_design,
        design_path=design_path,
        num_epochs=args.num_epochs,
    )
    block = {
        "smoke_num_epochs": args.num_epochs,
        "theta": cell.theta,
        "arm_id": cell.arm_id,
        "seed": cell.seed,
        **union_block(run, raw_design["joint_contract"], fit.t3_block),
    }
    for key in _DROPPED_ECHOES:
        run.pop(key, None)
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **run,
        "dp_union": block,
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{args.seed}.json"
    artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
