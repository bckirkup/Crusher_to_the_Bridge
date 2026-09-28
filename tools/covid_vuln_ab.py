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

import argparse
import json
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
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402
from tools.covid_assay_smoke import repo_root_of  # noqa: E402
from tools.covid_rhythm_ab import (  # noqa: E402
    cell_zone_sets,
    select_cells,
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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--design", default=DEFAULT_DESIGN)
    parser.add_argument("--index", type=int, default=None,
                        help="Run exactly the cell at this enumeration index")
    parser.add_argument("--class", dest="class_id", default=None)
    parser.add_argument("--arm", dest="arm_id", default=None,
                        choices=[None, "alpha_lo", "alpha_hi"])
    parser.add_argument("--seeds", default=None,
                        help="Comma-separated seed list")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design = load_vuln_design(
        str(resolve_repo_path(repo_root, args.design))
        if not os.path.isabs(args.design) else args.design,
    )
    seeds = (
        {int(s) for s in args.seeds.split(",")} if args.seeds else None
    )
    cells = select_cells(
        list(enumerate_vuln_cells(design)),
        index=args.index,
        class_id=args.class_id,
        arm_id=args.arm_id,
        seeds=seeds,
    )
    results = [
        run_cell(design, c, repo_root=repo_root) for c in cells
    ]
    text = json.dumps(results, indent=1, default=str)
    if args.out:
        resolved = resolve_repo_path(repo_root, args.out)
        with validated_open(
            resolved, "w", allowed_roots=(repo_root,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {resolved}")
    else:
        print(text)


if __name__ == "__main__":
    main()
