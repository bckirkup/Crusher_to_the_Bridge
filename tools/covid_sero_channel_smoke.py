"""Local preflight smoke for covid_sero_channel_v1 (campaign-preflight 1).

Proves the three things the frozen design assumes, before any Batch cell
runs:

1. Spec-lands: the design enumerates the declared 360 cells in
   point-major, arm-second, seed-innermost order (9 thetas x 2 channel
   arms x 20 seeds), and the period arm's ``onset_recording`` block
   resolves into the run spec's ``pathogen_overrides`` while the declared
   arm's spec carries none — the additive channel is off by absence.
2. Runtime binding: truncated runs read back the resolved channel on the
   live modality — ``onset_recording_channel`` returns the declared block
   on a period cell and None on a declared cell, and the payload echoes
   the same — a spec-lands-but-inert channel is a bug signature, not
   physics.
3. Contract: ``cell_payload`` on the truncated runs still carries the
   declared fields (observables, index geometry, arm attribution block,
   the onset_recording echo).

Shared enumeration / truncated-run machinery lives in
``tools/covid_assay_smoke.py``; this tool keeps only the channel checks.

Usage:
    python3 tools/covid_sero_channel_smoke.py \
        [--design picard_framework/runs/covid_sero_channel_v1_design.json] \
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    enumerate_cells,
)
from tools.covid_assay_smoke import (
    check_enumeration,
    load_declared_cells,
    prepare_cell_run_spec,
    repo_root_of,
    run_cell,
)

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_sero_channel_v1_design.json",
)
RUN_EPOCHS = 48
PERIOD_ARM = "P1_period"
DECLARED_ARM = "D0_declared"


def spec_onset_recording(design: Any, cell: Any, repo_root: str) -> Any:
    """The channel block the run spec carries for one cell's arm."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=24, repo_root=repo_root,
    )
    return (
        raw["pathogen_overrides"][PATHOGEN_ID]
        .get("observation_model", {})
        .get("onset_recording")
    )


def check_channel_spec_lands(  # pragma: no cover - CLI-driven check
    design: Any, repo_root: str,
) -> dict[str, Any]:
    """Each arm's declared channel must reach the spec, verbatim."""
    seen: dict[str, Any] = {}
    for cell in enumerate_cells(design):
        if cell.arm_id in seen:
            continue
        landed = spec_onset_recording(design, cell, repo_root)
        declared = (
            design.arm_overrides(cell.arm_id)
            .get("pathogen_overrides", {})
            .get(PATHOGEN_ID, {})
            .get("observation_model", {})
            .get("onset_recording")
        )
        assert landed == declared, (
            f"{cell.arm_id}: spec onset_recording {landed} "
            f"!= declared {declared}"
        )
        seen[cell.arm_id] = landed
    return seen


def engine_onset_recording(sim: Any) -> Any:
    """The channel the live modality resolved — the runtime read-back."""
    return sim.modalities["syndromic"].onset_recording_channel(PATHOGEN_ID)


def _cell_at(design: Any, arm_id: str, seed: int) -> Any:
    return next(
        c for c in enumerate_cells(design)
        if c.arm_id == arm_id and c.seed == seed
    )


def main() -> None:  # pragma: no cover - CLI driver, exercised by hand
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--design", default=DESIGN_REL)
    parser.add_argument("--seed", type=int, default=20200205)
    parser.add_argument(
        "--spec-only",
        action="store_true",
        help="enumeration + spec-lands checks only, no engine runs",
    )
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design, declared_cells = load_declared_cells(repo_root, args.design)
    report: dict[str, Any] = {"design_id": design.design_id}
    report["cell_blocks"] = check_enumeration(design, declared_cells)
    print(f"enumeration: {declared_cells} cells")

    landed = check_channel_spec_lands(design, repo_root)
    print(f"spec-lands: channel blocks resolve on {len(landed)} arms")

    if not args.spec_only:
        runs: dict[str, Any] = {}
        for arm_id in (DECLARED_ARM, PERIOD_ARM):
            cell = _cell_at(design, arm_id, args.seed)
            runs[arm_id] = run_cell(
                design, cell, repo_root, RUN_EPOCHS,
                extra_readback=lambda sim: {
                    "engine_onset_recording": engine_onset_recording(sim),
                },
            )
            print(
                f"{arm_id}: channel={runs[arm_id]['engine_onset_recording']} "
                f"recorded={runs[arm_id]['recorded_onsets']}",
            )
        expected = design.arm_overrides(PERIOD_ARM)["pathogen_overrides"][
            PATHOGEN_ID
        ]["observation_model"]["onset_recording"]
        assert runs[PERIOD_ARM]["engine_onset_recording"] == expected, (
            "period arm resolved "
            f"{runs[PERIOD_ARM]['engine_onset_recording']} != {expected}"
        )
        assert runs[DECLARED_ARM]["engine_onset_recording"] is None, (
            "declared arm resolved a channel it does not declare"
        )
        report["channel_binding"] = {
            arm: r["engine_onset_recording"] for arm, r in runs.items()
        }

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
