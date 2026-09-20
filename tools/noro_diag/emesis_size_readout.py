#!/usr/bin/env python3
"""Readout for the NORO-EMESIS-SIZE-01 replicate cells.

Aggregation only: this script reads the per-seed ``*.json.gz`` dumps written by
``per_host_dose_challenge.py`` (no ``--alpha``) and never re-runs or re-derives
a measurement. It answers the four questions frozen in
``docs/ledger/NORO-EMESIS-SIZE-01.md`` against the criteria declared there:

* **admissibility** -- a cell with zero accumulate calls is void, and more than
  ``MAX_VOID_CELLS`` void cells is a NO-GO for the study;
* **incidence** -- the fraction of admissible voyages with an emesis event, and
  the per-voyage event-count distribution;
* **size** -- median and range of patch mass, patch pickup dose, and the
  pickup/mass ratio expressed as a log10 loss;
* **share** -- patch pickup dose against credited scaled dose, reported as an
  upper bound because the two are measured on opposite sides of route
  efficiency and susceptibility scaling;
* **consequence** -- summed evaluated hazard per cell against the declared
  ``P(>=1 secondary)`` thresholds 0.105 and 0.693.

The emesis-on against emesis-off comparison it prints is *associational across
seeds*, not a paired contrast: seeds differ in every draw, not only in whether
a host vomited.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.noro_diag.cell_readout import (  # noqa: E402
    accumulate_calls,
    dig,
    gate_report,
    load_cells,
    partition,
    print_block,
    spread,
)
from tools.noro_diag.cell_readout import (  # noqa: E402
    number as _number,
)

MIN_EMESIS_VOYAGES = 3
HAZARD_PLAUSIBLE = 0.105
HAZARD_LIKELY = 0.693

COLUMNS = (
    ("seed", "seed"),
    ("imports", "transmission.imports"),
    ("secondaries", "transmission.secondaries"),
    ("emesis_events", "emesis_witness.emesis_events"),
    ("scheduled_episodes", "emesis_witness.scheduled_episodes"),
    ("patch_mass_gec", "emesis_witness.patch_mass_gec"),
    ("patch_pickups", "emesis_witness.patch_pickups"),
    ("patch_pickup_dose_gec", "emesis_witness.patch_pickup_dose_gec"),
    ("credited_scaled_gec", "reconciliation.sum_credited_scaled_gec"),
    ("sum_evaluated_hazard", "reconciliation.sum_evaluated_hazard"),
)


def markdown_table(cells: list[dict[str, Any]]) -> str:
    header = (
        "| " + " | ".join(name for name, _ in COLUMNS)
        + " | accumulate_calls |"
    )
    rule = "|" + "---|" * (len(COLUMNS) + 1)
    rows = [
        "| " + " | ".join(
            _format(dig(summary, dotted)) for _, dotted in COLUMNS
        ) + f" | {accumulate_calls(summary)} |"
        for summary in cells
    ]
    return "\n".join([header, rule, *rows])


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _spread(values: list[float]) -> dict[str, float]:
    return spread(values)


def incidence(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 1: how often does an emesis event happen, and how many."""
    counts = [int(_number(s, "emesis_witness.emesis_events")) for s in cells]
    with_event = [c for c in counts if c >= 1]
    distribution: dict[str, int] = {}
    for count in counts:
        distribution[str(count)] = distribution.get(str(count), 0) + 1
    return {
        "voyages": len(counts),
        "voyages_with_event": len(with_event),
        "fraction_with_event": len(with_event) / len(counts) if counts else 0.0,
        "events_per_voyage_distribution": distribution,
        "events_when_present": _spread(
            [float(c) for c in with_event],
        ) if with_event else {"n": 0},
        "sizeable": len(with_event) >= MIN_EMESIS_VOYAGES,
    }


def size(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 2: patch mass, pickup dose, and the route's own attenuation."""
    rows = []
    for summary in cells:
        events = int(_number(summary, "emesis_witness.emesis_events"))
        if events < 1:
            continue
        mass = _number(summary, "emesis_witness.patch_mass_gec")
        dose = _number(summary, "emesis_witness.patch_pickup_dose_gec")
        rows.append({
            "seed": summary["seed"],
            "events": events,
            "patch_mass_gec": mass,
            "patch_pickup_dose_gec": dose,
            "pickups": int(_number(summary, "emesis_witness.patch_pickups")),
            "pickup_over_mass": dose / mass if mass > 0 else None,
            "log10_loss": (
                -math.log10(dose / mass) if mass > 0 and dose > 0 else None
            ),
        })
    if not rows:
        return {"cells": [], "note": "no admissible cell carried an event"}
    ratios = [r["pickup_over_mass"] for r in rows if r["pickup_over_mass"]]
    losses = [r["log10_loss"] for r in rows if r["log10_loss"] is not None]
    return {
        "cells": rows,
        "patch_mass_gec": _spread([r["patch_mass_gec"] for r in rows]),
        "patch_pickup_dose_gec": _spread(
            [r["patch_pickup_dose_gec"] for r in rows],
        ),
        "pickup_over_mass": _spread(ratios) if ratios else {"n": 0},
        "log10_loss": _spread(losses) if losses else {"n": 0},
    }


def share(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 3: emesis pickup dose against the voyage's credited dose."""
    rows = []
    for summary in cells:
        credited = _number(summary, "reconciliation.sum_credited_scaled_gec")
        dose = _number(summary, "emesis_witness.patch_pickup_dose_gec")
        rows.append({
            "seed": summary["seed"],
            "credited_scaled_gec": credited,
            "patch_pickup_dose_gec": dose,
            "upper_bound_share": dose / credited if credited > 0 else None,
        })
    bounds = [r["upper_bound_share"] for r in rows if r["upper_bound_share"]]
    return {
        "cells": rows,
        "upper_bound_share": _spread(bounds) if bounds else {"n": 0},
        "caveat": (
            "pickup dose is measured at delivery and credited dose after "
            "route efficiency and susceptibility scaling; the ratio is an "
            "upper bound on the emesis share, not an equality"
        ),
    }


def consequence(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Question 4: does any voyage get close to producing a secondary."""
    hazards = [
        _number(s, "reconciliation.sum_evaluated_hazard") for s in cells
    ]
    secondaries = [int(_number(s, "transmission.secondaries")) for s in cells]
    return {
        "sum_evaluated_hazard": _spread(hazards) if hazards else {"n": 0},
        "cells_over_plausible": sum(h >= HAZARD_PLAUSIBLE for h in hazards),
        "cells_over_likely": sum(h >= HAZARD_LIKELY for h in hazards),
        "plausible_threshold": HAZARD_PLAUSIBLE,
        "likely_threshold": HAZARD_LIKELY,
        "max_p_at_least_one": (
            1.0 - math.exp(-max(hazards)) if hazards else 0.0
        ),
        "secondaries_total": sum(secondaries),
        "imports_total": sum(
            int(_number(s, "transmission.imports")) for s in cells
        ),
    }


def association(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """The across-seed emesis-on / emesis-off comparison, clearly labelled."""
    groups: dict[str, list[dict[str, Any]]] = {"with": [], "without": []}
    for summary in cells:
        events = int(_number(summary, "emesis_witness.emesis_events"))
        groups["with" if events >= 1 else "without"].append(summary)
    out: dict[str, Any] = {
        "labelled": (
            "associational across seeds, not a paired contrast: seeds differ "
            "in every draw, not only in whether a host vomited"
        ),
    }
    for name, group in groups.items():
        if not group:
            out[name] = {"n": 0}
            continue
        out[name] = {
            "n": len(group),
            "seeds": [s["seed"] for s in group],
            "credited_scaled_gec": _spread([
                _number(s, "reconciliation.sum_credited_scaled_gec")
                for s in group
            ]),
            "sum_evaluated_hazard": _spread([
                _number(s, "reconciliation.sum_evaluated_hazard")
                for s in group
            ]),
        }
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path,
        default=(
            REPO_ROOT
            / "docs/norovirus/noro_emesis_size_01/classic_cruise_1900"
        ),
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_emesis_size_01",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cells = load_cells(args.raw_dir)
    admissible, void = partition(cells)
    payload, gates_ok = gate_report(cells, admissible, void, args.raw_dir)
    print()
    print(markdown_table(cells))
    payload.update({
        "incidence": incidence(admissible),
        "size": size(admissible),
        "share": share(admissible),
        "consequence": consequence(admissible),
        "association": association(admissible),
    })
    for key in ("incidence", "size", "share", "consequence", "association"):
        print_block(key, payload[key])
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    path = resolve_child_path(str(out_dir), "emesis_size_cells.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
    print(f"\nwritten: {path}")
    return 0 if gates_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
