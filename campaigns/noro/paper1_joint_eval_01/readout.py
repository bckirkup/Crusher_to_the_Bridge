#!/usr/bin/env python3
"""Paper-1 WP2 joint-evaluation readout: the go/no-go table.

Reads cell zips written by ``cell.py`` (``<root>/<tier>/<run_id>.zip``) and
scores them against the criteria frozen in the campaign manifest
(``joint_eval.criteria``, written by ``design/build.py`` before any cell
ran). Nothing here chooses a threshold: a criterion missing from the
manifest is an error, not a default.

Every figure in the output is one of three kinds and is labelled:

* measured  -- a count or rate over the zips actually read
* inferred  -- the verdict the frozen rule assigns to those measurements
* hypothesis -- never emitted by this script; an explanation of a verdict
  belongs in the ledger with the evidence that would test it

Reads only; no engine involvement.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scipy.stats import beta  # noqa: E402

FAMILIES = ("burden", "threshold", "first_role", "curves", "environment")
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "manifest.json"


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Two-sided exact binomial interval; (0, 1) when n is 0."""
    if n <= 0:
        return 0.0, 1.0
    alpha = 1.0 - level
    lower = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    upper = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lower, upper


def read_cell(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        summary = json.loads(archive.read("summary.json"))
        members = set(archive.namelist())
    block = summary.get("joint_eval") or {}
    params = summary.get("parameters") or {}
    return {
        "path": str(path),
        "seed": params.get("seed", params.get("random_seed")),
        "engine_git_sha": params.get("engine_git_sha"),
        "families_present": [f for f in FAMILIES if block.get(f)],
        "member_present": "joint_eval.json.gz" in members,
        "posted": bool((block.get("threshold") or {}).get("posted")),
        "first_role": (block.get("first_role") or {}).get("first_role"),
        "burden": block.get("burden") or {},
        "echo_mismatched": (block.get("config_echo") or {}).get("mismatched"),
        "overrides_sha256": (block.get("config_echo") or {}).get(
            "overrides_sha256",
        ),
        "fingerprint": block.get("voyage_fingerprint_sha256"),
        "environment": block.get("environment") or {},
    }


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def _reported_ar(cell: dict[str, Any]) -> float | None:
    b = cell["burden"]
    total = (b.get("passenger_complement") or 0) + (b.get("crew_complement") or 0)
    if not total:
        return None
    return ((b.get("rep_pax_n") or 0) + (b.get("rep_crew_n") or 0)) / total


def tier_row(
    tier_id: str, meta: dict[str, Any], cells: list[dict[str, Any]],
    expected: int, block_sha: str,
) -> dict[str, Any]:
    """Measured quantities for one tier (hull x length x arm)."""
    n = len(cells)
    posted = sum(1 for c in cells if c["posted"])
    lower, upper = clopper_pearson(posted, n)
    ars = [a for a in (_reported_ar(c) for c in cells) if a is not None]
    clean = [
        c for c in cells
        if len(c["families_present"]) == len(FAMILIES)
        and c["member_present"] and c["echo_mismatched"] == []
        and c["overrides_sha256"] == block_sha and c["engine_git_sha"]
    ]
    return {
        "tier": tier_id,
        **meta,
        "kind": "measured",
        "n_expected": expected,
        "n_read": n,
        "n_clean": len(clean),
        "posted": posted,
        "posting_rate": posted / n if n else None,
        "posting_rate_ci95": [round(lower, 4), round(upper, 4)],
        "first_role": dict(Counter(c["first_role"] for c in cells)),
        "reported_ar_median": _quantile(ars, 0.5),
        "reported_ar_p95": _quantile(ars, 0.95),
        "reported_ar_max": max(ars, default=None),
        "swab_detected_voyages": sum(
            1 for c in cells if c["environment"].get("swab_detected_total")
        ),
        "tank_detected_voyages": sum(
            1 for c in cells if c["environment"].get("tank_detected_total")
        ),
        "engine_git_shas": sorted({str(c["engine_git_sha"]) for c in cells}),
    }


def score_cell(
    rows: dict[str, dict[str, Any]], criteria: dict[str, Any],
) -> dict[str, Any]:
    """Inferred verdict for one hull x length from its three stratum rows."""
    quiet, near, loud = (rows.get(s) for s in ("quiet", "near", "outbreak"))
    if not (quiet and near and loud) or None in (
        quiet["posting_rate"], near["posting_rate"], loud["posting_rate"],
    ):
        return {"kind": "inferred", "verdict": "incomplete", "checks": {}}
    q, m, o = (r["posting_rate"] for r in (quiet, near, loud))
    checks = {
        "contract_clean": all(
            r["n_clean"] == r["n_expected"] for r in (quiet, near, loud)
        ),
        "quiet_rare": q <= criteria["quiet_max_posting_rate"],
        "outbreak_posts": o >= criteria["outbreak_min_posting_rate"],
        "near_between": (
            q < m < o
            and criteria["near_min_posting_rate"] <= m
            <= criteria["near_max_posting_rate"]
        ),
        "quiet_not_comparable": (
            q < criteria["comparable_ratio"] * o
            and quiet["posting_rate_ci95"][1] < loud["posting_rate_ci95"][0]
        ),
    }
    return {
        "kind": "inferred",
        "verdict": "go" if all(checks.values()) else "no-go",
        "checks": checks,
    }


def baseline_rows(
    tiers: dict[str, dict[str, Any]], cells: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Bit-identity of each labelled-baseline arm against its reference."""
    out = []
    for tier_id, tier in tiers.items():
        meta = tier.get("joint_eval") or {}
        if meta.get("arm") != "baseline":
            continue
        want = meta.get("reference_fingerprints") or {}
        got = {str(c["seed"]): c["fingerprint"] for c in cells.get(tier_id, [])}
        compared = sorted(set(want) & set(got))
        out.append({
            "tier": tier_id,
            "kind": "measured",
            "n_reference": len(want),
            "n_compared": len(compared),
            "n_identical": sum(1 for s in compared if want[s] == got[s]),
            "reproduces": bool(want) and len(compared) == len(want)
            and all(want[s] == got[s] for s in compared),
        })
    return out


def build_readout(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    design = manifest["joint_eval"]
    criteria = design["criteria"]
    cells = {
        tier_id: [read_cell(p) for p in sorted((root / tier_id).glob("*.zip"))]
        for tier_id in manifest["tiers"]
    }
    tier_rows = []
    grid: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for tier_id, tier in manifest["tiers"].items():
        meta = tier.get("joint_eval") or {}
        if meta.get("arm") != "bridge":
            continue
        row = tier_row(
            tier_id,
            {k: meta[k] for k in ("hull", "epochs", "stratum")},
            cells[tier_id], len(tier["seeds"]), design["block_sha256"],
        )
        tier_rows.append(row)
        grid.setdefault((meta["hull"], meta["epochs"]), {})[meta["stratum"]] = row
    verdicts = [
        {"hull": hull, "epochs": epochs, **score_cell(rows, criteria)}
        for (hull, epochs), rows in sorted(grid.items())
    ]
    baselines = baseline_rows(manifest["tiers"], cells)
    states = {v["verdict"] for v in verdicts}
    if "incomplete" in states or not baselines:
        overall = "incomplete"
    elif states == {"go"} and all(b["reproduces"] for b in baselines):
        overall = "go"
    else:
        overall = "no-go"
    return {
        "campaign": manifest["campaign"],
        "criteria": criteria,
        "criteria_source": "manifest joint_eval.criteria (frozen before cells)",
        "tiers": tier_rows,
        "cells": verdicts,
        "baselines": baselines,
        "overall": {"kind": "inferred", "verdict": overall},
    }


def render(readout: dict[str, Any]) -> str:
    lines = [
        f"# {readout['campaign']} go/no-go",
        "",
        "Measured: posting counts and rates per tier. Inferred: verdicts "
        "under the frozen criteria.",
        "",
        "| hull | epochs | stratum | read/expected | clean | posted | "
        "rate | 95% CI |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in readout["tiers"]:
        rate = "-" if r["posting_rate"] is None else f"{r['posting_rate']:.3f}"
        lines.append(
            f"| {r['hull']} | {r['epochs']} | {r['stratum']} | "
            f"{r['n_read']}/{r['n_expected']} | {r['n_clean']} | "
            f"{r['posted']} | {rate} | {r['posting_rate_ci95']} |",
        )
    lines += ["", "| hull | epochs | verdict | failed checks |", "|---|---|---|---|"]
    for v in readout["cells"]:
        failed = [k for k, ok in v["checks"].items() if not ok]
        lines.append(
            f"| {v['hull']} | {v['epochs']} | {v['verdict']} | "
            f"{', '.join(failed) or '-'} |",
        )
    lines += ["", "| baseline tier | compared/reference | identical | reproduces |",
              "|---|---|---|---|"]
    for b in readout["baselines"]:
        lines.append(
            f"| {b['tier']} | {b['n_compared']}/{b['n_reference']} | "
            f"{b['n_identical']} | {b['reproduces']} |",
        )
    lines += ["", f"Overall (inferred): **{readout['overall']['verdict']}**"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--root", type=Path, required=True,
        help="directory holding <tier>/<run_id>.zip (an S3 sync of the "
             "campaign prefix, or a local smoke out dir)",
    )
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    readout = build_readout(manifest, args.root)
    if args.json:
        args.json.write_text(json.dumps(readout, indent=1), encoding="utf-8")
    print(render(readout))
    return 0 if readout["overall"]["verdict"] == "go" else 1


if __name__ == "__main__":
    sys.exit(main())
