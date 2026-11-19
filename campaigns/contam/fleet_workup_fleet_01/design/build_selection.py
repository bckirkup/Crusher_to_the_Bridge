#!/usr/bin/env python3
"""Build ``fleet_selection.json``: which hulls the fleet stage runs, and where.

Selection metadata only. Acceptance criteria, tolerances, the matrix and the
row IDs stay in the canary campaign's frozen files; this file names the 73
remaining hulls (the frozen 77 minus the four canary hulls), splits them into
serial cohorts, states the row counts each cohort must reproduce, and copies
each hull's committed ``platform.prj`` SHA-256 from the frozen input manifest
so the authored-lane gate has a pin for every hull.

``--check`` exits 1 if the committed file differs from a rebuild.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CANARY = HERE.parents[1] / "fleet_workup_canary_01" / "design"
FROZEN = CANARY / "frozen"
OUT = HERE / "fleet_selection.json"
COHORTS = 8
EXECUTE = "planned_execute"


def _counts(rows: list[dict[str, str]]) -> dict[str, int]:
    executed = [r for r in rows if r["planned_status"] == EXECUTE]
    return {
        "rows_total": len(rows),
        "rows_planned_execute": len(executed),
        "contamx_solver_invocations": sum(int(r["contamx_solves_planned"]) for r in executed),
        "cold_cell_executions": sum(
            int(r["warmup_reps"]) + int(r["measured_reps"]) for r in executed),
        "cached_cell_executions": sum(int(r["cached_reps"]) for r in executed),
        "smoke_cells_untimed": len(executed),
    }


def _split(hulls: list[str], parts: int) -> list[list[str]]:
    """Contiguous alphabetical chunks; the first ``len % parts`` get one more."""
    size, extra = divmod(len(hulls), parts)
    out, start = [], 0
    for index in range(parts):
        stop = start + size + (1 if index < extra else 0)
        out.append(hulls[start:stop])
        start = stop
    return out


def build() -> dict[str, Any]:
    criteria_bytes = (CANARY / "canary_criteria.json").read_bytes()
    criteria = json.loads(criteria_bytes)
    manifest = json.loads((FROZEN / "input_manifest.json").read_text(encoding="utf-8"))
    with (FROZEN / "run_matrix.csv").open(encoding="utf-8", newline="") as fh:
        matrix = list(csv.DictReader(fh))
    with (FROZEN / "coverage.csv").open(encoding="utf-8", newline="") as fh:
        coverage = list(csv.DictReader(fh))
    canary = sorted(criteria["canary"]["hulls"])
    in_scope = sorted(manifest["hulls"])
    fleet = [h for h in in_scope if h not in canary]
    prj = {}
    for hull in fleet:
        entry = next(f for f in manifest["hulls"][hull]["files"]
                     if f["path"].endswith("/contam/platform.prj"))
        prj[hull] = entry["sha256"]
    cohorts = _split(fleet, COHORTS)
    return {
        "id": "CONTAM-FLEET-WORKUP-FLEET-01",
        "kind": "fleet selection metadata; not acceptance criteria. Gates, tolerances, "
                "matrix, row IDs, settings and repetitions are the canary's frozen files, "
                "unchanged.",
        "criteria_sha256": hashlib.sha256(criteria_bytes).hexdigest(),
        "design_commit": criteria["design_commit"],
        "input_commit": criteria["input_commit"],
        "canary_hulls": canary,
        "excluded_no_bundle": {
            c["platform"]: c["exclusion_reason"] for c in coverage if c["in_scope"] != "1"},
        "hulls": fleet,
        "roster_rule": "frozen in-scope hulls (input_manifest.json) minus canary_hulls",
        "cohort_rule": f"{COHORTS} contiguous alphabetical chunks; one serial Batch job each, "
                       "one host per job; timings are never pooled across cohorts",
        "cohorts": [
            {"cohort": i, "hulls": hulls,
             "expected": _counts([r for r in matrix if r["hull"] in hulls])}
            for i, hulls in enumerate(cohorts)
        ],
        "expected_fleet": _counts([r for r in matrix if r["hull"] in fleet]),
        "expected_union_with_canary": _counts(matrix),
        "authored_prj_sha256": prj,
        "authored_prj_sha256_source": "design/frozen/input_manifest.json, contam/platform.prj "
                                      "entry of each hull",
    }


def render() -> str:
    return json.dumps(build(), indent=1, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render()
    if args.check:
        return 0 if OUT.read_text(encoding="utf-8") == text else 1
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
