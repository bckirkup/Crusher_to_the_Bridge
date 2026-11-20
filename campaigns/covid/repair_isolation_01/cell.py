#!/usr/bin/env python3
"""REPAIR-ISOLATION-01 cell worker: run one (theta, arm_id, seed) DP cell.

Native transport only — TRANSPORT-FIT-01 measured the solver choice as
outcome-identical, so the arm axis is the repair toggles alone
(``room_air_map_arm``, ``near_field_air_mode``,
``pathogen_pool_transport``, ``duty0_terminal_mode``; see the design's
``arms``). The design's ``base_overrides`` block — the DP boxed_s1s2
configuration — is applied to every cell's run spec after
``prepare_cell_run_spec`` composes the arm's own overrides, the
TRANSPORT-FIT-01 composition pattern verbatim.

Every cell audits its resolved transport engine afterwards: the arm
grammar declares no engine axis here, so a resolved engine that is not
the shipped ContamTransportEngine fails the cell rather than emit a
mislabeled payload.

``--num-epochs`` caps the voyage for local smoke validation only; Batch
runs always take the design's full declared voyage.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    QuarantineAttributionLedger,
    apply_arm_overrides,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    load_covid_profile,
    run_fit_spec,
)


def base_overrides(design_path: str, repo_root: Path = _REPO_ROOT) -> dict:
    """The design's declared shared base (empty on designs without one)."""
    raw = json.loads(
        (repo_root / design_path).read_text(encoding="utf-8"),
    )
    return dict(raw.get("base_overrides") or {})


def _match_cell(
    design: object, theta: float, arm_id: str, seed: int,
) -> object:
    """The single design cell at (theta, arm_id, seed), or die."""
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


# The shipped (repaired) resolution of each repair toggle — what an arm
# that does not declare the key runs with.
_TOGGLE_DEFAULTS = {
    "room_air_map_arm": "ambient_on",
    "near_field_air_mode": "two_box",
    "pathogen_pool_transport": "airflow",
    "duty0_terminal_mode": "extract",
}


def _expected_toggles(design: object, arm_id: str) -> dict[str, str]:
    """The resolved repair settings the arm's run must land on."""
    overrides = design.arm_overrides(arm_id) if design.arms else {}
    return {
        key: str(overrides.get(key, default))
        for key, default in _TOGGLE_DEFAULTS.items()
    }


def _resolved_toggles(payload: dict) -> dict[str, str | None]:
    """The engine-resolved repair settings echoed in the delivery block."""
    delivery = payload.get("delivery") or {}
    room_air = delivery.get("room_air_removal") or {}
    near_field = delivery.get("near_field_air") or {}
    return {
        "room_air_map_arm": room_air.get("map_arm"),
        "near_field_air_mode": near_field.get("mode"),
        "pathogen_pool_transport": delivery.get("pathogen_pool_transport"),
        "duty0_terminal_mode": delivery.get("duty0_terminal_mode"),
    }


def run_repair_cell(
    design: object,
    cell: object,
    *,
    design_path: str,
    num_epochs: int | None = None,
) -> dict:
    """Run one cell: base_overrides composed under the arm's overrides."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=str(_REPO_ROOT),
    )
    base = base_overrides(design_path)
    if base:
        apply_arm_overrides(
            raw, base,
            profile=load_covid_profile(str(_REPO_ROOT)),
            theta=cell.theta,
        )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(
        raw, repo_root=str(_REPO_ROOT), epoch_observer=ledger.observe,
    )
    resolved = (
        type(sim.contam_engine).__name__
        if getattr(sim, "contam_engine", None) is not None else None
    )
    if resolved != "ContamTransportEngine":
        raise SystemExit(
            f"arm {cell.arm_id!r} resolved transport engine "
            f"{resolved!r}; every repair-isolation arm is native — "
            f"refusing to emit a mislabeled payload",
        )
    payload = cell_payload(design, cell, sim, ledger, raw)
    payload["transport_engine_binary"] = None
    # Fail closed on the repair toggles too: a voyage where an override
    # silently did not reach the engine would score as its arm's result.
    expected = _expected_toggles(design, cell.arm_id)
    resolved_toggles = _resolved_toggles(payload)
    if resolved_toggles != expected:
        raise SystemExit(
            f"arm {cell.arm_id!r} declared toggles {expected} but the "
            f"engine resolved {resolved_toggles}; refusing to emit a "
            f"mislabeled payload",
        )
    return payload


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
                        help="smoke cap on voyage epochs (local only)")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / args.design))
    cell = _match_cell(design, args.theta, args.arm, args.seed)
    runner = functools.partial(run_repair_cell, design_path=args.design)
    if args.num_epochs is not None:
        runner = functools.partial(
            runner, num_epochs=args.num_epochs,
        )
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **runner(design, cell),
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
