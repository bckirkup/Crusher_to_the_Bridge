"""COVID-VULN-01: run one susceptibility-shape A/B cell under the stack.

Pairs ``picard_framework/covid_vuln_cells`` (the four-class, two-alpha-endpoint
cell declaration) with ``tools/covid_takeoff_attribution.analyse_spec``
(the instrumented run), wiring the per-platform zone sets and the catalog
synchronized-end mask into the ledger so the summary carries the
``rhythm_ab`` block alongside the susceptibility machinery. The arm's
alpha endpoint is written into ``pathogen_overrides`` by
``prepare_vuln_cell_spec``; ``summary.dose_response`` echoes the resolved
profile values the engine consumed.

Usage:
    python3 tools/covid_vuln_ab.py \
        [--design picard_framework/runs/covid_vuln_ab_v1_design.json] \
        [--index 0 | --class mega_cruise --arm alpha_lo --seeds 20200205] \
        [--out out.json]
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_rhythm_cells import (  # noqa: E402
    sync_end_epoch_mask,
)
from picard_framework.covid_vuln_cells import (  # noqa: E402
    enumerate_vuln_cells,
    load_vuln_design,
    prepare_vuln_cell_spec,
)
from tools.covid_rhythm_ab import (  # noqa: E402
    ab_cli_main,
    cell_zone_sets,
)
from tools.covid_takeoff_attribution import analyse_spec  # noqa: E402

DEFAULT_DESIGN = (
    "picard_framework/runs/covid_vuln_ab_v1_design.json"
)


def run_cell(design: Any, cell: Any, *, repo_root: str) -> dict[str, Any]:
    """Spec + instrumented run + summary for one A/B cell."""
    raw = prepare_vuln_cell_spec(design, cell, repo_root=repo_root)
    num_epochs = int(
        raw.get("config_overrides", {}).get("num_epochs")
        or raw.get("run", {}).get("num_epochs")
        or 0,
    )
    zone_sets = cell_zone_sets(cell.platform_id, repo_root=repo_root)
    leg = design.leg(cell.class_id)
    mask = sync_end_epoch_mask(
        cell.platform_id, num_epochs,
        repo_root=repo_root, sop_window=leg.sop017_window,
    )
    return analyse_spec(
        raw, design, cell,
        repo_root=repo_root, zone_sets=zone_sets, sync_mask=mask,
    )


def main() -> None:  # pragma: no cover - CLI driver
    ab_cli_main(
        description=__doc__.splitlines()[0],
        default_design=DEFAULT_DESIGN,
        load_design=load_vuln_design,
        enumerate_cells=enumerate_vuln_cells,
        arm_choices=("alpha_lo", "alpha_hi"),
        run_cell_fn=run_cell,
    )


if __name__ == "__main__":
    main()
