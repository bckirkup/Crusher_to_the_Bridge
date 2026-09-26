#!/usr/bin/env python3
"""Readout for the NORO-ROUTE-ATTR-01 block.

Aggregation only: reads the per-seed ``*.json.gz`` dumps that
``per_host_dose_challenge.py`` wrote for the triad -- ``per_surface``
with ``areal`` touch shares (base), ``per_surface`` with the ``declared``
table (arm), and ``pooled`` as the DISAGG-01 identity witness -- and
scores the six statistics the ledger (``docs/ledger/NORO-ROUTE-ATTR-01.md``
§2) froze before the block ran. It re-derives nothing, fits nothing and
changes no constant.

The measured quantity is route attribution at infection level: each
recorded acquisition carries ``acquired_particles_by_route`` (the
post-challenge ledger the engine stored on the infection record) and
``dominant_route`` (the max-key of that ledger). ``acquisitions`` covers
non-resident acquisitions only -- resident imports are not in the map --
so every count below is a count of secondaries. Every dose quantity is a
paired share or ratio, never an absolute dose result
(``docs/norovirus/norovirus_open_ledger.md`` §1).

The verdict is a finding, not a failure: exit is 0.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)

DOMINANT_KEYS = (
    "fomite",
    "droplet",
    "direct_contact",
    "emesis_aerosol",
    "hvac_airborne",
    "food",
)


def load_arm(directory: Path, tag: str) -> dict[int, dict[str, Any]]:
    """The per-seed cells one arm wrote, keyed by seed."""
    cells = {}
    for path in sorted(
        directory.glob(f"per_host_dose_challenge_{tag}_seed*.json.gz"),
    ):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            cell = json.load(handle)
        cells[int(cell["seed"])] = cell
    return cells


def _acquisitions(cell: dict[str, Any]) -> list[dict[str, Any]]:
    return list((cell.get("transmission") or {}).get("acquisitions") or [])


def _secondaries(cell: dict[str, Any]) -> int:
    return int((cell.get("transmission") or {}).get("secondaries") or 0)


def _dominant_map(cell: dict[str, Any]) -> dict[int, str]:
    """agent_id -> dominant_route for every recorded acquisition."""
    return {
        int(a["agent_id"]): str(a.get("dominant_route") or "unknown")
        for a in _acquisitions(cell)
    }


def _fomite_dose_share(cell: dict[str, Any]) -> float:
    """Fomite share of infection-route dose, recomputed ledger (exact)."""
    route = (
        (cell.get("transmission") or {})
        .get("route_attribution", {})
        .get("recomputed", {})
        .get("infection_dose_share_by_route", {})
    )
    return float(route.get("fomite") or 0.0)


def wilson_interval(k: int, n: int, z: float = 1.959964) -> dict[str, float]:
    """Wilson 95% interval for a binomial proportion."""
    if n <= 0:
        return {"p": 0.0, "lo": 0.0, "hi": 0.0, "n": 0, "k": 0}
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {
        "p": p,
        "lo": max(0.0, centre - half),
        "hi": min(1.0, centre + half),
        "n": n,
        "k": k,
    }


def _log_binom(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def sign_test_pvalue(positive: int, negative: int) -> float:
    """Exact two-sided sign test on the nonzero pairs."""
    n = positive + negative
    if n == 0:
        return 1.0
    k = min(positive, negative)
    tail = sum(math.exp(_log_binom(n, i) - n * math.log(2.0)) for i in range(k + 1))
    return min(1.0, 2.0 * tail)


def jaccard(a: set[int], b: set[int]) -> tuple[float, bool]:
    """Jaccard with the vacuous 0/0 -> 1.0 convention (flagged)."""
    if not a and not b:
        return 1.0, True
    union = a | b
    if not union:
        return 1.0, True
    return len(a & b) / len(union), False


def _route_composition(cells: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Ledger readout item 1: dominant-route counts and fomite share."""
    counts: Counter[str] = Counter()
    total = 0
    informative_seeds = 0
    for cell in cells.values():
        dom = _dominant_map(cell)
        if dom:
            informative_seeds += 1
        counts.update(dom.values())
        total += len(dom)
    fomite = counts.get("fomite", 0)
    return {
        "total_secondaries": total,
        "informative_seeds": informative_seeds,
        "dominant_route_counts": dict(
            sorted(counts.items(), key=lambda kv: -kv[1]),
        ),
        "fomite_share": wilson_interval(fomite, total),
    }


def _paired_deltas(
    base: dict[int, dict[str, Any]], arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Ledger readout item 2: per-seed secondaries delta and sign test."""
    seeds = sorted(set(base) & set(arm))
    deltas = [_secondaries(arm[s]) - _secondaries(base[s]) for s in seeds]
    positive = sum(1 for d in deltas if d > 0)
    negative = sum(1 for d in deltas if d < 0)
    return {
        "seeds": seeds,
        "deltas": deltas,
        "positive": positive,
        "negative": negative,
        "zero": sum(1 for d in deltas if d == 0),
        "median": statistics.median(deltas) if deltas else 0.0,
        "sign_test_p_two_sided": sign_test_pvalue(positive, negative),
    }


def _fomite_set_jaccard(
    base: dict[int, dict[str, Any]], arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Ledger readout item 3: fomite-attributed host-set Jaccard."""
    seeds = sorted(set(base) & set(arm))
    values: list[float] = []
    vacuous: list[int] = []
    differing_sets: list[int] = []
    for seed in seeds:
        a_set = {
            agent for agent, route in _dominant_map(base[seed]).items()
            if route == "fomite"
        }
        b_set = {
            agent for agent, route in _dominant_map(arm[seed]).items()
            if route == "fomite"
        }
        value, is_vacuous = jaccard(a_set, b_set)
        values.append(value)
        if is_vacuous:
            vacuous.append(seed)
        if a_set != b_set:
            differing_sets.append(seed)
    infected_differ = [
        s for s in seeds
        if set(_dominant_map(base[s])) != set(_dominant_map(arm[s]))
    ]
    return {
        "jaccard_by_seed": dict(zip(seeds, values)),
        "median_jaccard": statistics.median(values) if values else 1.0,
        "vacuous_seeds": vacuous,
        "fomite_set_differs": differing_sets,
        "infected_set_differs": infected_differ,
    }


def _dose_share_deltas(
    base: dict[int, dict[str, Any]], arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Ledger readout item 4: per-seed fomite dose-share delta (D - A)."""
    seeds = [
        s for s in sorted(set(base) & set(arm))
        if _secondaries(base[s]) or _secondaries(arm[s])
    ]
    deltas = {s: _fomite_dose_share(arm[s]) - _fomite_dose_share(base[s])
              for s in seeds}
    return {
        "informative_seeds": seeds,
        "fomite_share_delta_by_seed": deltas,
        "median_delta": (
            statistics.median(deltas.values()) if deltas else 0.0
        ),
    }


def _discordant(
    base: dict[int, dict[str, Any]], arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Ledger readout item 5: acquisitions discordant across the arms."""
    seeds = sorted(set(base) & set(arm))
    only_in_arm: list[dict[str, Any]] = []
    route_differs: list[dict[str, Any]] = []
    for seed in seeds:
        a_map = _dominant_map(base[seed])
        d_map = _dominant_map(arm[seed])
        for agent in sorted(set(a_map) ^ set(d_map)):
            only_in_arm.append({
                "seed": seed,
                "agent_id": agent,
                "in_areal": agent in a_map,
                "in_declared": agent in d_map,
                "areal_route": a_map.get(agent),
                "declared_route": d_map.get(agent),
            })
        for agent in sorted(set(a_map) & set(d_map)):
            if a_map[agent] != d_map[agent]:
                route_differs.append({
                    "seed": seed,
                    "agent_id": agent,
                    "areal_route": a_map[agent],
                    "declared_route": d_map[agent],
                })
    return {
        "infected_one_arm_only": only_in_arm,
        "dominant_route_differs": route_differs,
        "n_one_arm_only": len(only_in_arm),
        "n_route_differs": len(route_differs),
    }


def _disagg_witness(
    base: dict[int, dict[str, Any]], pooled: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Areal-vs-pooled identity re-check on the rebuilt image.

    Identity is the acquisition event set -- (agent_id, epoch) pairs --
    which is the granularity DISAGG-01 witnessed. Last-ulp drift in
    ``dose_read`` is a pre-existing float artifact (set-iteration order
    under randomized hashing), present in the ``411b0dbe`` block too;
    it is counted separately, not an identity break.
    """
    seeds = sorted(set(base) & set(pooled))
    mismatched = []
    ulp_drift = []

    def _key(acq: dict[str, Any]) -> tuple[Any, ...]:
        return (acq.get("agent_id"), acq.get("epoch"))

    for seed in seeds:
        if sorted(map(_key, _acquisitions(base[seed]))) != sorted(
            map(_key, _acquisitions(pooled[seed]))
        ):
            mismatched.append(seed)
            continue
        paired = zip(
            _acquisitions(base[seed]), _acquisitions(pooled[seed]),
        )
        if any(a.get("dose_read") != p.get("dose_read") for a, p in paired):
            ulp_drift.append(seed)
    return {
        "seeds_checked": len(seeds),
        "mismatched_seeds": mismatched,
        "ulp_drift_seeds": ulp_drift,
    }


def readout(
    areal_dir: Path,
    declared_dir: Path,
    pooled_dir: Path,
) -> dict[str, Any]:
    """All six frozen readout items over the paired seed set."""
    areal = load_arm(areal_dir, "per_surface_areal")
    declared = load_arm(declared_dir, "per_surface_declared")
    pooled = load_arm(pooled_dir, "pooled")
    return {
        "n_seeds_areal": len(areal),
        "n_seeds_declared": len(declared),
        "n_seeds_pooled": len(pooled),
        "route_composition": {
            "areal": _route_composition(areal),
            "declared": _route_composition(declared),
            "pooled": _route_composition(pooled),
        },
        "paired_secondaries_delta": _paired_deltas(areal, declared),
        "fomite_set_jaccard": _fomite_set_jaccard(areal, declared),
        "fomite_dose_share_delta": _dose_share_deltas(areal, declared),
        "discordant_acquisitions": _discordant(areal, declared),
        "disagg01_witness": _disagg_witness(areal, pooled),
    }


def _print(result: dict[str, Any]) -> None:
    comp = result["route_composition"]
    for tag in ("areal", "declared", "pooled"):
        c = comp[tag]
        share = c["fomite_share"]
        print(
            f"{tag}: {c['total_secondaries']} secondaries on "
            f"{c['informative_seeds']} seeds; dominant routes "
            f"{c['dominant_route_counts']}; fomite share "
            f"{share['p']:.3f} [{share['lo']:.3f}, {share['hi']:.3f}]",
        )
    delta = result["paired_secondaries_delta"]
    print(
        f"paired secondaries D-A: +{delta['positive']} / -{delta['negative']}"
        f" / 0:{delta['zero']}, median {delta['median']}, "
        f"sign p={delta['sign_test_p_two_sided']:.4f}",
    )
    jac = result["fomite_set_jaccard"]
    print(
        f"fomite-set Jaccard median {jac['median_jaccard']}; "
        f"set differs on {len(jac['fomite_set_differs'])} seeds "
        f"({len(jac['vacuous_seeds'])} vacuous); infected set differs on "
        f"{len(jac['infected_set_differs'])} seeds",
    )
    share = result["fomite_dose_share_delta"]
    print(
        f"fomite dose-share D-A: {len(share['informative_seeds'])} "
        f"informative seeds, median {share['median_delta']:.4f}",
    )
    disc = result["discordant_acquisitions"]
    print(
        f"discordant: {disc['n_one_arm_only']} infected one arm only, "
        f"{disc['n_route_differs']} dominant route differs",
    )
    wit = result["disagg01_witness"]
    print(
        f"DISAGG-01 witness: {wit['seeds_checked']} seeds checked, "
        f"{len(wit['mismatched_seeds'])} mismatched",
    )


def _safe_path(path: str) -> str:
    """Canonicalise a CLI-derived target and refuse anything outside the repo."""
    resolved = Path(os.path.realpath(path))
    if Path(os.path.realpath(str(REPO_ROOT))) not in (
        resolved, *resolved.parents,
    ):
        raise ValueError(f"path {path!r} is outside the allowed directory")
    return str(resolved)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--areal-dir", type=Path, required=True)
    parser.add_argument("--declared-dir", type=Path, required=True)
    parser.add_argument("--pooled-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = readout(args.areal_dir, args.declared_dir, args.pooled_dir)
    out_dir = prepare_output_directory(
        str(args.out), allowed_roots=(str(REPO_ROOT),),
    )
    path = _safe_path(resolve_child_path(
        str(out_dir), "route_attribution_readout.json",
    ))
    Path(path).write_text(
        json.dumps(result, indent=1, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _print(result)
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
