#!/usr/bin/env python3
"""COVID-SEED-RING-02 cell worker: run one (theta, arm_id, seed) screen cell.

One array child of the generic campaign entrypoint resolves its seed; the
block's ``args`` carry the theta and arm_id the entrypoint cannot express
(``entry.py build_argv``). The worker composes the design's
``base_overrides`` block — the DP boxed_s1s2 configuration — UNDER the
arm's own overrides (arm keys win on shared channels), the same pattern
``campaigns/covid/theta_refit_01/cell.py`` uses, and writes the payload as
the cell artifact the entrypoint uploads.

``--num-epochs`` caps the voyage for local smoke validation only; Batch
runs always take the design's full declared voyage.
"""
from __future__ import annotations

import argparse
import dataclasses
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


def run_screen_cell(
    design: object,
    cell: object,
    *,
    design_path: str,
    num_epochs: int | None = None,
) -> dict:
    """Run one cell: base_overrides composed under the arm's overrides.

    The arm keeps final say on channels both blocks touch: every key the
    arm declares is dropped from the base block before either is applied,
    so e.g. a protocol-swapping arm (FRAQMB) renames the shipped SOP-017
    schedule entry itself (``_swap_scheduled_protocol`` only resolves the
    shipped name). ``prepare_cell_run_spec`` applies the arm internally,
    so the spec is built against an arms-stripped design copy and both
    blocks are applied here in order: base-minus-arm, then arm.
    """
    arm = (
        design.arm_overrides(cell.arm_id)
        if design.arms and cell.arm_id is not None else {}
    )
    build_time = {"pathogen_pool_transport", "room_air_map_arm"} & set(arm)
    if build_time:
        raise SystemExit(
            f"arm {cell.arm_id} declares build-time overrides "
            f"{sorted(build_time)} the base-composition path cannot honor",
        )
    bare = (
        dataclasses.replace(design, arms=()) if design.arms else design
    )
    raw = prepare_cell_run_spec(
        bare, cell, num_epochs=num_epochs, repo_root=str(_REPO_ROOT),
    )
    base = {
        key: value
        for key, value in base_overrides(design_path).items()
        if key not in arm
    }
    profile = load_covid_profile(str(_REPO_ROOT))
    if base:
        apply_arm_overrides(raw, base, profile=profile, theta=cell.theta)
    if arm:
        apply_arm_overrides(
            raw, arm, profile=profile, theta=cell.theta,
        )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(
        raw, repo_root=str(_REPO_ROOT), epoch_observer=ledger.observe,
    )
    return cell_payload(design, cell, sim, ledger, raw)


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
    result = run_screen_cell(
        design, cell, design_path=args.design,
        num_epochs=args.num_epochs,
    )
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **result,
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
