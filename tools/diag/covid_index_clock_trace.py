#!/usr/bin/env python3
"""COVID-INDEX-CLOCK-01: per-epoch shedding trace of the seeded index host.

Runs one DP-UNION-01 cell locally through the campaign's own worker path
(``run_pf_cell``) with one extra read-only epoch observer, and writes what
the seeded host's shedding clock did each epoch: infection age, days since
onset as ``KorkinAgent._shedding_age`` resolves it, whether the
presymptomatic gate is open, and the value ``get_pathogen_shedding``
returns (the quantity ``_get_shedders`` gates on). The engine is not
modified; the observer only reads agent state after each step.

    python3 tools/diag/covid_index_clock_trace.py --theta 3.16e9 --seed 20200205 \
        --num-epochs 130
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_UNION_CELL = _REPO_ROOT / "campaigns/covid/dp_union_01/cell.py"
_DEFAULT_DESIGN = "picard_framework/runs/covid_dp_union_01_design.json"
# Fixed: the output location is not CLI-controlled (Sonar S8707).
_OUT_DIR = _REPO_ROOT / "reports/covid_index_clock_01"
PATHOGEN_ID = "sars_cov2_resp"


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enum_name(value: Any) -> str | None:
    return None if value is None else str(getattr(value, "name", value))


def index_row(
    sim: Any, agent: Any, profile: dict[str, Any], epoch: int,
) -> dict[str, Any]:
    """One epoch of one seeded host's shedding clock, read-only."""
    clock = sim.clock
    inf = agent.infections.get(PATHOGEN_ID) or {}
    time_infected = inf.get("time_infected")
    presymptomatic = float(profile.get("presymptomatic_shedding_days", 0.0))
    days_since_onset = curve_index = None
    if time_infected is not None:
        days_since_onset, curve_index = agent._shedding_age(
            time_infected, inf, profile, clock,
        )
    residents = agent.resident_strains(PATHOGEN_ID)
    return {
        "epoch": epoch,
        "agent_id": int(agent.agent_id),
        "status": _enum_name(inf.get("status")),
        "illness": _enum_name(inf.get("illness")),
        "time_infected": time_infected,
        "infection_age_days": (
            None if time_infected is None
            else float(clock.days_elapsed(time_infected))
        ),
        "incubation_days": inf.get("incubation_days"),
        "onset_time_infected": inf.get("onset_time_infected"),
        "days_since_onset": days_since_onset,
        "curve_index": curve_index,
        "gate_open": (
            None if days_since_onset is None
            else bool(days_since_onset >= -presymptomatic)
        ),
        "shedding_multiplier": inf.get("shedding_multiplier"),
        "resident_strains": {
            sid: int(r.time_infected) for sid, r in residents.items()
        },
        "shedding": float(agent.get_pathogen_shedding(PATHOGEN_ID, profile)),
        "departure_epoch": agent.departure_epoch,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default=_DEFAULT_DESIGN)
    parser.add_argument("--theta", required=True, type=float)
    parser.add_argument("--arm", default="union_niid")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--num-epochs", type=int, default=None)
    args = parser.parse_args(argv)

    union = _load(_UNION_CELL, "dp_union_cell")
    fit = union._load_fit_cell()
    pf02 = fit._load_pf02_cell()
    design, raw_design, design_path = pf02._load_design_with_base(args.design)
    cell = fit._match_cell(design, args.theta, args.arm, args.seed)

    rows: list[dict[str, Any]] = []
    calls = [0]  # the observer runs once per completed epoch, from epoch 0
    inner_run = pf02.run_fit_spec

    def traced_run(raw: dict[str, Any], **kwargs: Any) -> Any:
        inner_observer = kwargs.pop("epoch_observer", None)

        def observer(sim: Any, work: Any) -> None:
            if inner_observer is not None:
                inner_observer(sim, work)
            profile = sim.pathogen_profiles[PATHOGEN_ID]
            seeded = set(
                getattr(sim.engine, "explicit_seed_agent_ids", None) or (),
            )
            epoch = calls[0]
            calls[0] += 1
            rows.extend(
                index_row(sim, agent, profile, epoch)
                for agent in sim.engine.agents
                if agent.agent_id in seeded
            )

        return inner_run(raw, epoch_observer=observer, **kwargs)

    pf02.run_fit_spec = traced_run
    try:
        run = pf02.run_pf_cell(
            design, cell, raw_design=raw_design, design_path=design_path,
            num_epochs=args.num_epochs,
        )
    finally:
        pf02.run_fit_spec = inner_run

    emitting = [r for r in rows if r["shedding"] > 0.0]
    payload = {
        "design_id": design.design_id,
        "cell": cell.as_dict(),
        "index_onset_day": run.get("index_onset_day"),
        "index_shedding_at_day0": run.get("index_shedding_at_day0"),
        "index_departed_epoch": run.get("index_departed_epoch"),
        "seed_ring": run.get("seed_ring"),
        "acquisitions_by_day": (
            run.get("acquisition_curve") or {}
        ).get("total_by_day"),
        "first_emission": emitting[0] if emitting else None,
        "observer_calls": calls[0],
        "trace": rows,
    }
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = _OUT_DIR / f"index_clock_trace_{int(args.seed)}.json"
    artifact.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
