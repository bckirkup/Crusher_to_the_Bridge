#!/usr/bin/env python3
"""DP-THETA-FIT-01 cell worker: run one (theta, arm_id, seed) cell.

The extended-horizon theta fit on the ``replay_niid`` arm: the cell runs the
scenario's full declared voyage (no ``--num-epochs`` in the declared blocks),
so the 5 Feb quarantine and the published 5-20 Feb testing campaign both
fall inside the run. The design sets ``funnel_echo`` so the campaign's own
specimen log reaches the payload; this worker reduces that log to the
``dp_theta_fit`` block — the frozen ``covid.T3`` mapping of
``docs/covid/covid_dp_theta_fit_01_design.md`` — and drops the per-host
echoes so a cell artifact stays small.

The run itself is PLATFORM-FIDELITY-02's ``run_pf_cell`` verbatim, loaded
the way the pilot worker loads it.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import enumerate_cells  # noqa: E402

_PF02_CELL = _REPO_ROOT / "campaigns/covid/platform_fidelity_02/cell.py"
_DROPPED_ECHOES = ("campaign_specimen_log", "funnel_hosts")


def _load_pf02_cell() -> Any:
    """PLATFORM-FIDELITY-02's cell machinery, loaded like a chained readout."""
    spec = importlib.util.spec_from_file_location("pf02_cell", _PF02_CELL)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {_PF02_CELL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _match_cell(design: object, theta: float, arm_id: str, seed: int) -> object:
    matches = [
        cell for cell in enumerate_cells(design)
        if cell.arm_id == arm_id and cell.seed == seed
        and math.isclose(cell.theta, theta, rel_tol=1e-12)
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"{len(matches)} cells match theta={theta} arm={arm_id} "
            f"seed={seed}; expected exactly 1",
        )
    return matches[0]


def t3_block(
    specimen_log: list[dict[str, Any]], through_day_index: int,
) -> dict[str, Any]:
    """The frozen covid.T3 mapping, read off the campaign specimen log.

    ``positives_through_day`` is the scored quantity: positive specimens
    taken on or before ``through_day_index``. The by-day table and wave
    tallies are the audit that nothing later (the 23 Feb crew wave) entered
    the count.
    """
    by_day: dict[int, dict[str, int]] = {}
    waves: dict[str, int] = {}
    for entry in specimen_log:
        row = by_day.setdefault(
            int(entry["day"]), {"specimens": 0, "positives": 0},
        )
        row["specimens"] += 1
        row["positives"] += 1 if entry["positive"] else 0
        wave = entry.get("wave") or ""
        if wave:
            waves[wave] = waves.get(wave, 0) + 1
    in_window = [d for d in by_day if d <= through_day_index]
    return {
        "through_day_index": through_day_index,
        "specimens_through_day": sum(by_day[d]["specimens"] for d in in_window),
        "positives_through_day": sum(by_day[d]["positives"] for d in in_window),
        "specimens_all": len(specimen_log),
        "positives_all": sum(1 for e in specimen_log if e["positive"]),
        "first_specimen_day": min(by_day) if by_day else None,
        "last_specimen_day": max(by_day) if by_day else None,
        "specimens_by_wave": waves,
        "by_day": {str(d): by_day[d] for d in sorted(by_day)},
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

    pf02 = _load_pf02_cell()
    design, raw_design, design_path = pf02._load_design_with_base(args.design)
    cell = _match_cell(design, args.theta, args.arm, args.seed)
    run = pf02.run_pf_cell(
        design, cell,
        raw_design=raw_design,
        design_path=design_path,
        num_epochs=args.num_epochs,
    )
    through_day = int(raw_design["fit_target"]["through_day_index"])
    fit_block = {
        "smoke_num_epochs": args.num_epochs,
        "theta": cell.theta,
        "arm_id": cell.arm_id,
        "seed": cell.seed,
        "t3": t3_block(run["campaign_specimen_log"], through_day),
    }
    for key in _DROPPED_ECHOES:
        run.pop(key, None)
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **run,
        "dp_theta_fit": fit_block,
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{args.seed}.json"
    artifact.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
