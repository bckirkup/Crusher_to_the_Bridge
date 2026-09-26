"""Local preflight smoke for covid_sero_channel_v1 (campaign-preflight 1).

Proves the three things the frozen design assumes, before any Batch cell
runs:

1. Spec-lands: the design enumerates the declared 360 cells in
   point-major, arm-second, seed-innermost order (9 thetas x 2 channel
   arms x 20 seeds), and each arm's declared ``onset_recording`` block
   resolves verbatim into the run spec's ``pathogen_overrides`` — the
   period arm's channel lands, the declared arm's stays absent.
2. Runtime binding: truncated runs read back the resolved channel on the
   live modality — ``onset_recording_channel`` returns the declared block
   on a period cell and None on a declared cell, so a spec-lands-but-
   inert channel is a bug signature, not physics.
3. Contract: ``cell_payload`` on the truncated runs still carries the
   declared fields (observables, index geometry, arm attribution block).

Shared enumeration / truncated-run machinery lives in
``tools/covid_assay_smoke.py``; this tool keeps only the channel checks.

Usage:
    python3 tools/covid_sero_channel_smoke.py \
        [--design picard_framework/runs/covid_sero_channel_v1_design.json] \
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import PATHOGEN_ID
from tools.covid_assay_smoke import (
    drive,
    prepare_cell_run_spec,
    run_cell,
)

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_sero_channel_v1_design.json",
)
RUN_EPOCHS = 48
PERIOD_ARM = "P1_period"
DECLARED_ARM = "D0_declared"


def declared_onset_recording(design: Any, arm_id: str) -> Any:
    """The channel block the arm declares, or None."""
    return (
        design.arm_overrides(arm_id)
        .get("pathogen_overrides", {})
        .get(PATHOGEN_ID, {})
        .get("observation_model", {})
        .get("onset_recording")
    )


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
    design: Any, cell: Any, repo_root: str,
) -> None:
    """The arm's declared channel must reach the spec, verbatim."""
    landed = spec_onset_recording(design, cell, repo_root)
    declared = declared_onset_recording(design, cell.arm_id)
    assert landed == declared, (
        f"{cell.arm_id}: spec onset_recording {landed} "
        f"!= declared {declared}"
    )


def engine_onset_recording(sim: Any) -> Any:
    """The channel the live modality resolved — the runtime read-back."""
    return sim.modalities["syndromic"].onset_recording_channel(PATHOGEN_ID)


def check_channel_binds(  # pragma: no cover - CLI-driven check
    design: Any, runs: dict[str, Any], report: dict[str, Any],
) -> None:
    """The period arm must resolve its block; the declared arm none."""
    expected = declared_onset_recording(design, PERIOD_ARM)
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


def _channel_run(  # pragma: no cover - CLI-driven check
    design: Any, cell: Any, repo_root: str,
) -> dict[str, Any]:
    return run_cell(
        design, cell, repo_root, RUN_EPOCHS,
        extra_readback=lambda sim: {
            "engine_onset_recording": engine_onset_recording(sim),
        },
    )


if __name__ == "__main__":
    drive(
        file_name=__file__,
        design_rel=DESIGN_REL,
        spec_check=check_channel_spec_lands,
        runtime_arms=(DECLARED_ARM, PERIOD_ARM),
        cell_runner=_channel_run,
        binding_check=check_channel_binds,
        arm_line=lambda arm, r: (
            f"{arm}: channel={r['engine_onset_recording']} "
            f"recorded={r['recorded_onsets']}"
        ),
    )
