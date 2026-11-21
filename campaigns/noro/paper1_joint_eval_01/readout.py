#!/usr/bin/env python3
"""Paper-1 WP2 joint-evaluation readout.

Reads cell zips written by ``cell.py`` (``<root>/<tier>/<run_id>.zip``) and
reports three things, in this order and kept apart:

1. **Technical completion** (the bridge gate). Intended inputs used,
   outcomes extractable, independent attempts accounted for, paired
   comparisons meaningful. This is the only gate. No outcome voids it.
2. **Ordering diagnostic.** Posting rates by diagnostic stratum against the
   bands frozen in the manifest. A quiet stratum that posts, or a hull with
   no events, is a measured result. It selects a predeclared continuation
   (reconstruction / population-geometry / uncertainty / precision /
   justified defect fix); it never re-opens mechanism work by itself.
3. **Pilots.** The temporal pilot (prefix identity across paired lengths)
   and the joint-outcome pilot (source-weighted estimates from
   independently sampled evaluation seeds, with the replication each
   endpoint's precision target implies).

Every rule and number comes from the manifest's ``joint_eval`` block,
written by ``design/build.py`` before any cell ran. Each output row is
labelled ``measured`` or ``inferred``. This script emits no hypotheses.

Reads only; no engine involvement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from scipy.stats import beta

FAMILIES = (
    "burden", "threshold", "size_distribution", "first_role", "curves",
    "environment",
)
ROLE_KEYS = (
    "cumulative_reported_cases_passenger", "cumulative_reported_cases_crew",
)
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "manifest.json"
Z95 = 1.959964


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Two-sided exact binomial interval; (0, 1) when n is 0."""
    if n <= 0:
        return 0.0, 1.0
    alpha = 1.0 - level
    lower = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    upper = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lower, upper


def zero_event_upper(n: int, level: float = 0.95) -> float | None:
    """Exact one-sided upper bound for 0 events in n: 1 - (1-level)^(1/n)."""
    return None if n <= 0 else 1.0 - (1.0 - level) ** (1.0 / n)


def read_cell(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        summary = json.loads(archive.read("summary.json"))
        members = set(archive.namelist())
    block = summary.get("joint_eval") or {}
    params = summary.get("parameters") or {}
    families = block.get("families") or {}
    series = summary.get("timeseries") or []
    return {
        "path": str(path),
        "seed": params.get("seed"),
        "num_epochs": len(series),
        "engine_git_sha": params.get("engine_git_sha"),
        "families_missing": [
            f for f in FAMILIES
            if (families.get(f) or {}).get("status") != "present"
        ],
        "member_present": "joint_eval.json.gz" in members,
        "posted_epoch": (block.get("threshold") or {}).get("vsp_trigger_epoch"),
        "first_role": (block.get("first_role") or {}).get("first_role"),
        "burden": block.get("burden") or {},
        "arm": block.get("arm") or {},
        "effective": block.get("effective_config") or {},
        "roles": block.get("roles") or {},
        "fingerprint": block.get("voyage_fingerprint_sha256"),
        "environment": block.get("environment") or {},
        "role_series": [[row.get(k) for k in ROLE_KEYS] for row in series],
    }


def inputs_ok(cell: dict[str, Any], tier: dict[str, Any], sha: str) -> bool:
    meta = tier["joint_eval"]
    return bool(
        cell["arm"].get("changed_paths") == meta["changed_paths"]
        and cell["arm"].get("effective_sha256") == sha
        and cell["num_epochs"] == meta["epochs"]
        and cell["effective"].get("mismatched") == []
        and cell["effective"].get("runner_changed_paths") == []
        and cell["roles"].get("initialised") == meta["intended_roles"]
        and cell["roles"].get("payload") == meta["intended_roles"]
        and cell["engine_git_sha"]
    )


def canonical_sha(tree: dict[str, Any]) -> str:
    blob = json.dumps(tree, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def completion_row(
    tier_id: str, tier: dict[str, Any], cells: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measured technical-completion facts for one tier."""
    sha = canonical_sha(tier["config_overrides"])
    expected = sorted(int(s) for s in tier["seeds"])
    seen = Counter(int(c["seed"]) for c in cells if c["seed"] is not None)
    shas = sorted({str(c["engine_git_sha"]) for c in cells})
    row = {
        "tier": tier_id,
        "kind": "measured",
        "arm": tier["joint_eval"]["arm"],
        "n_expected": len(expected),
        "n_read": len(cells),
        "seeds_missing": [s for s in expected if s not in seen],
        "seeds_unexpected": sorted(s for s in seen if s not in set(expected)),
        "seeds_duplicated": sorted(s for s, n in seen.items() if n > 1),
        "n_inputs_ok": sum(1 for c in cells if inputs_ok(c, tier, sha)),
        "n_outcomes_ok": sum(
            1 for c in cells
            if not c["families_missing"] and c["member_present"]
        ),
        "engine_git_shas": shas,
    }
    row["intended_inputs_used"] = (
        row["n_inputs_ok"] == len(cells) > 0 and len(shas) == 1
    )
    row["outcomes_extractable"] = row["n_outcomes_ok"] == len(cells) > 0
    row["attempts_accounted"] = not (
        row["seeds_missing"] or row["seeds_unexpected"]
        or row["seeds_duplicated"]
    )
    return row


def rate_row(
    tier_id: str, meta: dict[str, Any], cells: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measured posting and burden for one tier."""
    n = len(cells)
    posted = sum(1 for c in cells if c["posted_epoch"] is not None)
    lower, upper = clopper_pearson(posted, n)
    ars = sorted(a for a in (_reported_ar(c) for c in cells) if a is not None)
    return {
        "tier": tier_id,
        "kind": "measured",
        **{k: meta[k] for k in ("hull", "epochs") if k in meta},
        "stratum": meta.get("stratum") or meta.get("source_stratum"),
        "n": n,
        "posted": posted,
        "posting_rate": posted / n if n else None,
        "posting_rate_ci95": [round(lower, 4), round(upper, 4)],
        "zero_event_upper95_one_sided": (
            round(zero_event_upper(n), 5) if n and posted == 0 else None
        ),
        "first_role": dict(Counter(str(c["first_role"]) for c in cells)),
        "reported_ar_median": statistics.median(ars) if ars else None,
        "reported_ar_max": ars[-1] if ars else None,
        "swab_detected_voyages": sum(
            1 for c in cells if c["environment"].get("swab_detected_total")
        ),
        "tank_detected_voyages": sum(
            1 for c in cells if c["environment"].get("tank_detected_total")
        ),
    }


def _reported_ar(cell: dict[str, Any]) -> float | None:
    b = cell["burden"]
    total = (b.get("passenger_complement") or 0) + (b.get("crew_complement") or 0)
    if not total:
        return None
    return ((b.get("rep_pax_n") or 0) + (b.get("rep_crew_n") or 0)) / total


def _stratum_state(row: dict[str, Any], lo: float, hi: float) -> str:
    """in / out / undetermined for a rate against the band [lo, hi]."""
    rate = row["posting_rate"]
    low, high = row["posting_rate_ci95"]
    if rate is None:
        return "undetermined"
    if lo <= rate <= hi:
        return "in"
    return "out" if (low > hi or high < lo) else "undetermined"


def band_state(
    rows: dict[str, dict[str, Any]], bands: dict[str, Any],
) -> dict[str, Any]:
    """Inferred diagnostic state of one hull x length."""
    states = {
        "quiet": _stratum_state(
            rows["quiet"], 0.0, bands["quiet_max_posting_rate"],
        ),
        "outbreak": _stratum_state(
            rows["outbreak"], bands["outbreak_min_posting_rate"], 1.0,
        ),
        "near": _stratum_state(
            rows["near"], bands["near_min_posting_rate"],
            bands["near_max_posting_rate"],
        ),
    }
    rates = [rows[s]["posting_rate"] for s in ("quiet", "near", "outbreak")]
    ordered = None not in rates and rates[0] < rates[1] < rates[2]
    if "out" in states.values():
        state = "out"
    elif ordered and set(states.values()) == {"in"}:
        state = "in"
    else:
        state = "undetermined"
    return {"kind": "inferred", "state": state, "strata": states,
            "ordered": ordered}


def hull_state(cell_states: list[str]) -> str:
    if "out" in cell_states:
        return "out"
    return "in" if set(cell_states) == {"in"} else "undetermined"


def continuation(
    hull_states: dict[str, str], defect_evidence: list[str],
) -> dict[str, Any]:
    """The predeclared continuation the diagnostic selects."""
    states = list(hull_states.values())
    if defect_evidence:
        choice = "justified_defect_fix"
    elif states and set(states) == {"out"}:
        choice = "reconstruction"
    elif "out" in states:
        choice = "population_geometry"
    elif "undetermined" in states or not states:
        choice = "uncertainty"
    else:
        choice = "precision"
    return {"kind": "inferred", "continuation": choice,
            "hull_states": hull_states, "defect_evidence": defect_evidence}


def temporal_pilot(
    by_length: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Is a shorter voyage the prefix of the same seed's longest voyage?"""
    lengths = sorted(by_length)
    longest = {int(c["seed"]): c for c in by_length[lengths[-1]]}
    compared = identical = 0
    for length in lengths[:-1]:
        for cell in by_length[length]:
            ref = longest.get(int(cell["seed"]))
            if ref is None:
                continue
            compared += 1
            n = len(cell["role_series"])
            identical += int(ref["role_series"][:n] == cell["role_series"])
    return {"kind": "measured", "pairs_compared": compared,
            "prefix_identical": identical,
            "truncation_valid": compared > 0 and identical == compared}


def pilot_estimate(
    strata: dict[str, tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Source-weighted posting probability from evaluation seeds."""
    estimate = variance = 0.0
    neyman = {}
    for source, (meta, row) in strata.items():
        n, p, w = row["n"], row["posting_rate"], meta.get("source_weight")
        if not n or p is None or w is None:
            return {"kind": "measured", "estimate": None, "reason": "incomplete"}
        estimate += w * p
        variance += w * w * p * (1 - p) / n
        neyman[source] = w * math.sqrt(p * (1 - p))
    total = sum(neyman.values())
    return {
        "kind": "measured",
        "estimate": estimate,
        "standard_error": math.sqrt(variance),
        "neyman_share": {
            s: (v / total if total else None) for s, v in neyman.items()
        },
        "n_for_half_width_0p10": (
            math.ceil((Z95 * total / 0.10) ** 2) if total else None
        ),
        "note": "evaluation seeds only; a zero-variance stratum is sized "
                "by the quiet_bound target, not by this formula",
    }


VOYAGE_KEYS = (
    "parameters", "trigger_status", "timeseries", "derived", "summary",
    "cost_accounting", "role_checkpoints",
)


FINGERPRINT_EXCLUDED_PARAMETERS = ("engine_git_sha", "tier_id")


def archive_fingerprint(summary: dict[str, Any]) -> str:
    """``cell.fingerprint`` applied to an archived ``summary.json``."""
    body = {k: summary[k] for k in VOYAGE_KEYS if k in summary}
    body["parameters"] = {
        k: v for k, v in (body.get("parameters") or {}).items()
        if k not in FINGERPRINT_EXCLUDED_PARAMETERS
    }
    blob = json.dumps(body, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def reference_fingerprints(root: Path, source_tier: str) -> dict[str, str]:
    """seed -> fingerprint over the prior campaign's zips of *source_tier*.

    The prior campaign reuses its seeds across arms, so archives of any
    other tier are skipped; a seed archived twice for the tier is an error.
    """
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            summary = json.loads(archive.read("summary.json"))
        params = summary.get("parameters") or {}
        if params.get("tier_id") != source_tier or params.get("seed") is None:
            continue
        seed = str(params["seed"])
        if seed in out:
            raise SystemExit(f"two reference archives for seed {seed}")
        out[seed] = archive_fingerprint(summary)
    return out


def reproduction_rows(
    tiers: dict[str, dict[str, Any]], cells: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    out = []
    for tier_id, tier in tiers.items():
        meta = tier["joint_eval"]
        if meta["arm"] != "reproduction":
            continue
        want = meta.get("reference_fingerprints") or {}
        got = {str(c["seed"]): c["fingerprint"] for c in cells[tier_id]}
        compared = sorted(set(want) & set(got))
        out.append({
            "tier": tier_id,
            "kind": "measured",
            "n_expected": len(tier["seeds"]),
            "n_reference": len(want),
            "n_compared": len(compared),
            "n_identical": sum(1 for s in compared if want[s] == got[s]),
        })
    return out


def _grid(
    manifest: dict[str, Any], cells: dict[str, list[dict[str, Any]]], arm: str,
) -> dict[str, dict[int, dict[str, str]]]:
    """hull -> epochs -> stratum -> tier id, for one arm."""
    grid: dict[str, dict[int, dict[str, str]]] = {}
    for tier_id, tier in manifest["tiers"].items():
        meta = tier["joint_eval"]
        if meta["arm"] != arm:
            continue
        key = meta.get("stratum") or meta.get("source_stratum")
        grid.setdefault(meta["hull"], {}).setdefault(
            meta["epochs"], {},
        )[key] = tier_id
    return grid


def build_readout(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    design = manifest["joint_eval"]
    tiers = {
        t: v for t, v in manifest["tiers"].items()
        if v["joint_eval"]["arm"] != "census"
    }
    cells = {
        t: [read_cell(p) for p in sorted((root / t).glob("*.zip"))]
        for t in tiers
    }
    completion = [completion_row(t, tiers[t], cells[t]) for t in tiers]
    rates = {t: rate_row(t, tiers[t]["joint_eval"], cells[t]) for t in tiers}
    bridge = _grid(manifest, cells, "bridge")
    pairs_ok = bool(bridge)
    diag, temporal, hull_states = [], [], {}
    for hull, lengths in sorted(bridge.items()):
        states = []
        for epochs, strata in sorted(lengths.items()):
            state = band_state(
                {s: rates[t] for s, t in strata.items()},
                design["diagnostic_bands"],
            )
            states.append(state["state"])
            diag.append({"hull": hull, "epochs": epochs, **state})
        hull_states[hull] = hull_state(states)
        for stratum in sorted(next(iter(lengths.values()))):
            by_length = {e: cells[s[stratum]] for e, s in lengths.items()}
            seed_sets = {
                frozenset(c["seed"] for c in v) for v in by_length.values()
            }
            pairs_ok = pairs_ok and len(seed_sets) == 1 and all(by_length.values())
            temporal.append({
                "hull": hull, "stratum": stratum, **temporal_pilot(by_length),
            })
    reproduction = reproduction_rows(tiers, cells)
    pilot = [
        {"hull": hull, "epochs": epochs, **pilot_estimate({
            s: (tiers[t]["joint_eval"], rates[t]) for s, t in strata.items()
        })}
        for hull, lengths in sorted(_grid(manifest, cells, "pilot").items())
        for epochs, strata in sorted(lengths.items())
    ]
    gate = {
        "kind": "inferred",
        "stage_b_emitted": bool(design["stage_b_emitted"]),
        "intended_inputs_used": all(r["intended_inputs_used"] for r in completion),
        "outcomes_extractable": all(r["outcomes_extractable"] for r in completion),
        "attempts_accounted": all(r["attempts_accounted"] for r in completion),
        "pairs_meaningful": pairs_ok and all(
            r["n_expected"] and r["n_compared"] == r["n_expected"]
            for r in reproduction
        ),
    }
    gate["technically_complete"] = all(
        gate[k] for k in gate if k != "kind"
    )
    defects = [
        f"{r['tier']}: {r['n_identical']}/{r['n_compared']} reproduce"
        for r in reproduction if r["n_identical"] != r["n_compared"]
    ]
    return {
        "campaign": manifest["campaign"],
        "rules_source": "manifest joint_eval (frozen before any cell)",
        "gate": gate,
        "completion": completion,
        "rates": list(rates.values()),
        "ordering_diagnostic": diag,
        "continuation": (
            continuation(hull_states, defects)
            if gate["technically_complete"]
            else {"kind": "inferred", "continuation": None,
                  "reason": "not evaluated: bridge not technically complete"}
        ),
        "temporal_pilot": temporal,
        "joint_outcome_pilot": pilot,
        "reproduction": reproduction,
        "zero_event_convention": design["precision"]["zero_event_convention"],
    }


def render(readout: dict[str, Any]) -> str:
    gate = readout["gate"]
    lines = [
        f"# {readout['campaign']} bridge readout", "",
        "## 1. Technical completion (the gate; inferred from measured rows)",
        "",
    ]
    lines += [f"- {k}: {v}" for k, v in gate.items() if k != "kind"]
    lines += [
        "", "| tier | read/expected | inputs ok | outcomes ok | missing seeds |",
        "|---|---|---|---|---|",
    ]
    for r in readout["completion"]:
        lines.append(
            f"| {r['tier']} | {r['n_read']}/{r['n_expected']} | "
            f"{r['n_inputs_ok']} | {r['n_outcomes_ok']} | "
            f"{len(r['seeds_missing'])} |",
        )
    lines += [
        "", "## 2. Ordering diagnostic (measured rates; inferred states)", "",
        "| tier | n | posted | rate | 95% CI | 0-event upper |",
        "|---|---|---|---|---|---|",
    ]
    for r in readout["rates"]:
        rate = "-" if r["posting_rate"] is None else f"{r['posting_rate']:.3f}"
        lines.append(
            f"| {r['tier']} | {r['n']} | {r['posted']} | {rate} | "
            f"{r['posting_rate_ci95']} | {r['zero_event_upper95_one_sided']} |",
        )
    lines += ["", "| hull | epochs | state | strata |", "|---|---|---|---|"]
    for d in readout["ordering_diagnostic"]:
        lines.append(
            f"| {d['hull']} | {d['epochs']} | {d['state']} | {d['strata']} |",
        )
    lines += [
        "", f"Continuation (inferred): {readout['continuation']}", "",
        "Zero-event convention: " + readout["zero_event_convention"], "",
        "## 3. Pilots (measured)", "",
    ]
    lines += [f"- temporal {t}" for t in readout["temporal_pilot"]]
    lines += [f"- joint-outcome {p}" for p in readout["joint_outcome_pilot"]]
    lines += [f"- reproduction {r}" for r in readout["reproduction"]]
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
    parser.add_argument(
        "--reference-root", type=Path, default=None,
        help="run zips of the prior campaign the reproduction arm re-runs; "
             "fingerprints computed here replace the manifest's (empty) "
             "reference_fingerprints",
    )
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.reference_root is not None:
        for tier in manifest["tiers"].values():
            if tier["joint_eval"]["arm"] == "reproduction":
                reference = reference_fingerprints(
                    args.reference_root,
                    tier["joint_eval"]["source"].split("#", 1)[1],
                )
                tier["joint_eval"]["reference_fingerprints"] = {
                    str(s): reference[str(s)]
                    for s in tier["seeds"] if str(s) in reference
                }
    readout = build_readout(manifest, args.root)
    if args.json:
        args.json.write_text(json.dumps(readout, indent=1), encoding="utf-8")
    print(render(readout))
    return 0 if readout["gate"]["technically_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
