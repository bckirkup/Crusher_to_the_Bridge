"""COVID-RHYTHM-01: run one rhythm A/B cell under the attribution stack.

Pairs ``picard_framework/covid_rhythm_cells`` (the four-class cell
declaration) with ``tools/covid_takeoff_attribution.analyse_spec`` (the
instrumented run), wiring the per-platform zone sets and the catalog
synchronized-end mask into the ledger so the summary carries the
``rhythm_ab`` block: corridor occupancy vs the program clock, and the
crew-zone passenger emptiness measurement.

Usage:
    python3 tools/covid_rhythm_ab.py \
        [--design picard_framework/runs/covid_rhythm_ab_v1_design.json] \
        [--index 0 | --class mega_cruise --arm off --seeds 20200205] \
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
    crew_zone_names,
    enumerate_rhythm_cells,
    load_rhythm_design,
    prepare_rhythm_cell_spec,
    sync_end_epoch_mask,
    transit_zone_names,
)
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402
from tools.covid_assay_smoke import repo_root_of  # noqa: E402
from tools.covid_takeoff_attribution import analyse_spec  # noqa: E402

DEFAULT_DESIGN = (
    "picard_framework/runs/covid_rhythm_ab_v1_design.json"
)


def cell_zone_sets(platform_id: str, *, repo_root: str) -> dict[str, Any]:
    """The transit/crew zone partitions the rhythm-A/B tallies need."""
    return {
        "transit": transit_zone_names(platform_id, repo_root=repo_root),
        "crew": crew_zone_names(platform_id, repo_root=repo_root),
    }


def run_cell(design: Any, cell: Any, *, repo_root: str) -> dict[str, Any]:
    """Spec + instrumented run + summary for one A/B cell."""
    raw = prepare_rhythm_cell_spec(design, cell, repo_root=repo_root)
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


def select_cells(
    cells: list[Any],
    *,
    index: int | None,
    class_id: str | None,
    arm_id: str | None,
    seeds: set[int] | None,
) -> list[Any]:
    cells = list(cells)
    if index is not None:
        if index < 0 or index >= len(cells):
            raise SystemExit(
                f"--index {index} out of range (0..{len(cells) - 1})",
            )
        return [cells[index]]
    if class_id is not None:
        cells = [c for c in cells if c.class_id == class_id]
    if arm_id is not None:
        cells = [c for c in cells if c.arm_id == arm_id]
    if seeds:
        cells = [c for c in cells if c.seed in seeds]
    if not cells:
        raise SystemExit("no cells match the filters")
    return cells


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--design", default=DEFAULT_DESIGN)
    parser.add_argument("--index", type=int, default=None,
                        help="Run exactly the cell at this enumeration index")
    parser.add_argument("--class", dest="class_id", default=None)
    parser.add_argument("--arm", dest="arm_id", default=None,
                        choices=[None, "off", "on"])
    parser.add_argument("--seeds", default=None,
                        help="Comma-separated seed list")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design = load_rhythm_design(
        str(resolve_repo_path(repo_root, args.design))
        if not os.path.isabs(args.design) else args.design,
    )
    seeds = (
        {int(s) for s in args.seeds.split(",")} if args.seeds else None
    )
    cells = select_cells(
        list(enumerate_rhythm_cells(design)),
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
