#!/usr/bin/env python3
"""PLATFORM-FIDELITY-01b readout: the corrected DP hull-fidelity contrast.

Pairs the 20 reused PLATFORM-FIDELITY-01 proxy cells (the proven-inert
baseline, addendum §3) with the 20 PLATFORM-FIDELITY-01b dedicated cells
(function-matched union ``exempt_work_zones``) on seed, and computes the
frozen PF-01 metrics plus the corrections binding from
``docs/covid/covid_platform_fidelity_01b_addendum.md`` §6:

- q05-q95 ranges are SEEDWISE SPREADS, not confidence intervals;
- unconditional onset burden (median and total recorded_onsets over all 20
  seeds regardless of the takeoff gate) is reported alongside P(takeoff)
  and the takeoff-conditional paired endpoint (with its n);
- no platform-equivalence conclusion may be drawn from an interval
  crossing zero.

Also audits the 01b preflight witnesses per dedicated cell (addendum §5):
working-crew band at quarantine activation, posted zones restricted to the
7 hull-native essential IDs, boxed crew-meal service active, fired protocol
ids, close_zones flag, and the protocols SHA-256 of the 01b file.

Usage:
    python3 campaigns/covid/platform_fidelity_01b/readout.py \
        --proxy-prefix s3://.../campaign/covid_platform_fidelity_01/dp_t7e6_proxy/ \
        --dedicated-prefix s3://.../campaign/covid_platform_fidelity_01b/dp_t7e6_dedicated/
    python3 campaigns/covid/platform_fidelity_01b/readout.py \
        --proxy-dir out/pf01_proxy --dedicated-dir out/pf01b_dedicated
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DEFAULT_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_DEFAULT_PROXY_PREFIX = (
    f"s3://{_DEFAULT_BUCKET}/campaign/covid_platform_fidelity_01/dp_t7e6_proxy/"
)
_DEFAULT_DEDICATED_PREFIX = (
    f"s3://{_DEFAULT_BUCKET}/campaign/covid_platform_fidelity_01b/dp_t7e6_dedicated/"
)
_PROTOCOLS_REL = "data/config/protocols_covid_pf_dp_01b.json"
_TAKEOFF = 10
_THETA = 7900000.0
# Addendum §3.3: dedicated exempt crew at boarding 98-135 per seed; the
# activation-epoch witness allows the 0-1 pre-activation isolation effect.
_WORKING_CREW_BAND = (95, 140)
_DP_ESSENTIAL_ZONES = {
    "Bridge", "MainGalley", "Engine_Room", "Stores", "Laundry",
    "CrewMess", "CrewMessOff",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_s3(prefix: str) -> Iterable[tuple[str, dict[str, Any]]]:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dev box has boto3
        raise SystemExit("boto3 is required for --prefix") from exc
    assert prefix.startswith("s3://"), f"need s3:// uri, got {prefix!r}"
    bucket, _, key_prefix = prefix[5:].partition("/")
    key_prefix = key_prefix.rstrip("/") + "/"
    client = boto3.client("s3")
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents", []):
            if not obj["Key"].endswith(".json"):
                continue
            body = client.get_object(Bucket=bucket, Key=obj["Key"])["Body"]
            try:
                yield obj["Key"], json.loads(body.read())
            except json.JSONDecodeError:
                continue


def _iter_dir(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    for path in sorted(root.rglob("cell_*.json")):
        try:
            yield str(path), json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue


def _load_cells(
    prefix: str | None, directory: str | None,
) -> dict[int, dict[str, Any]]:
    """seed -> normalized cell from one source (proxy or dedicated)."""
    iterator = (_iter_dir(Path(directory)) if directory
                else _iter_s3(prefix or ""))
    cells: dict[int, dict[str, Any]] = {}
    for key, payload in iterator:
        cell = payload.get("cell") or {}
        seed = cell.get("seed")
        if seed is None:
            continue
        cells[int(seed)] = {
            "key": key,
            "design_id": payload.get("design_id"),
            "theta": cell.get("theta"),
            "seed": int(seed),
            "arm_id": cell.get("arm_id"),
            "obs": payload.get("observables") or {},
            "pf": payload.get("platform_fidelity") or {},
            "crew_window": payload.get("crew_window") or {},
            "quarantine_witness": payload.get("quarantine_witness") or {},
        }
    return cells


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return float("nan")
    return cov / math.sqrt(vx * vy)


def _asym_share(cells: list[dict[str, Any]]) -> float:
    pos = sum(c["obs"].get("campaign_positives", 0) for c in cells)
    asym = sum(c["obs"].get("campaign_asymptomatic_positives", 0)
               for c in cells)
    return (asym / pos) if pos else float("nan")


def _witness_audit(cell: dict[str, Any], protocols_sha: str) -> list[str]:
    """Addendum §5 witness checks for one dedicated cell; [] = clean."""
    problems: list[str] = []
    pf = cell["pf"]
    if pf.get("resolved_platform_id") != "diamond_princess":
        problems.append(f"resolved_platform_id={pf.get('resolved_platform_id')}")
    if pf.get("fired_protocol_ids") != ["SOP-017-MESSBOX"]:
        problems.append(f"fired={pf.get('fired_protocol_ids')}")
    if pf.get("close_zones_fired_flag"):
        problems.append("close_zones fired")
    hashes = pf.get("input_hashes") or {}
    if hashes.get("protocols_sha256") != protocols_sha:
        problems.append("protocols_sha256 mismatch vs 01b file")
    at_activation = (cell["crew_window"].get("at_activation") or {})
    working = at_activation.get("working_crew_count")
    if working is None or not (_WORKING_CREW_BAND[0] <= working
                               <= _WORKING_CREW_BAND[1]):
        problems.append(f"working_crew_count={working} outside band")
    posted = set((at_activation.get("working_crew_by_posted_zone") or {}))
    foreign = posted - _DP_ESSENTIAL_ZONES
    if foreign:
        problems.append(f"foreign posted zones: {sorted(foreign)}")
    meal = (cell["crew_window"].get("crew_meal_service") or {})
    if meal.get("mode") != "boxed" or not meal.get("active_epochs"):
        problems.append(f"boxed service not active: {meal}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy-prefix", default=_DEFAULT_PROXY_PREFIX)
    parser.add_argument("--dedicated-prefix", default=_DEFAULT_DEDICATED_PREFIX)
    parser.add_argument("--proxy-dir", default=None)
    parser.add_argument("--dedicated-dir", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    proxy = _load_cells(args.proxy_prefix, args.proxy_dir)
    dedicated = _load_cells(args.dedicated_prefix, args.dedicated_dir)
    seeds = sorted(set(proxy) & set(dedicated))

    protocols_sha = _sha256_file(_REPO_ROOT / _PROTOCOLS_REL)

    proxy_obs = [proxy[s]["obs"] for s in seeds]
    dedicated_obs = [dedicated[s]["obs"] for s in seeds]
    proxy_onsets = [int(o.get("recorded_onsets", 0)) for o in proxy_obs]
    dedicated_onsets = [int(o.get("recorded_onsets", 0)) for o in dedicated_obs]

    both = [s for s in seeds
            if proxy_onsets[seeds.index(s)] >= _TAKEOFF
            and dedicated_onsets[seeds.index(s)] >= _TAKEOFF]
    deltas = [int(dedicated[s]["obs"]["recorded_onsets"])
              - int(proxy[s]["obs"]["recorded_onsets"]) for s in both]
    rho = _pearson(
        [float(proxy[s]["obs"]["recorded_onsets"]) for s in both],
        [float(dedicated[s]["obs"]["recorded_onsets"]) for s in both],
    )
    proxy_takeoff = [s for s in seeds if proxy[s]["obs"].get(
        "recorded_onsets", 0) >= _TAKEOFF]
    dedicated_takeoff = [s for s in seeds if dedicated[s]["obs"].get(
        "recorded_onsets", 0) >= _TAKEOFF]

    witness = {
        str(s): _witness_audit(dedicated[s], protocols_sha) for s in seeds
    }
    witness_failures = {k: v for k, v in witness.items() if v}

    failed_comparisons = [
        d["key"] for d in dedicated.values()
        if d["pf"].get("close_zones_fired_flag")
    ]
    missing_echo = [
        d["key"] for d in dedicated.values()
        if not d["pf"].get("resolved_platform_id")
    ]
    missing_cells = sorted(set(range(20200205, 20200225)) - set(seeds))
    n_in_scope = len(seeds)
    failure_rate = (len(missing_cells) + len(failed_comparisons)) / max(
        n_in_scope, 1)

    summary = {
        "campaign": "covid_platform_fidelity_01b",
        "note": ("q05-q95 are seedwise spreads, NOT confidence intervals; "
                 "unconditional onset burden reported alongside the "
                 "takeoff-conditional endpoint; no platform-equivalence "
                 "conclusion from an interval crossing zero (addendum §6)."),
        "proxy_source": args.proxy_dir or args.proxy_prefix,
        "dedicated_source": args.dedicated_dir or args.dedicated_prefix,
        "n_seeds_paired": len(seeds),
        "row": {
            "P_takeoff_proxy": (len(proxy_takeoff) / len(seeds)
                                if seeds else float("nan")),
            "P_takeoff_dedicated": (len(dedicated_takeoff) / len(seeds)
                                    if seeds else float("nan")),
            "n_both_takeoff": len(both),
            "paired_delta_median": _quantile(deltas, 0.5) if deltas
            else float("nan"),
            "paired_delta_q05": _quantile(deltas, 0.05) if deltas
            else float("nan"),
            "paired_delta_q95": _quantile(deltas, 0.95) if deltas
            else float("nan"),
            "crn_rho": rho,
            "unpaired_declared": bool(rho == rho and rho < 0.3),
            "asym_share_proxy": _asym_share(
                [proxy[s] for s in proxy_takeoff]),
            "asym_share_dedicated": _asym_share(
                [dedicated[s] for s in dedicated_takeoff]),
            "onsets_median_proxy_all_seeds": _quantile(proxy_onsets, 0.5),
            "onsets_median_dedicated_all_seeds": _quantile(
                dedicated_onsets, 0.5),
            "onsets_total_proxy_all_seeds": sum(proxy_onsets),
            "onsets_total_dedicated_all_seeds": sum(dedicated_onsets),
        },
        "audit": {
            "witness_failures": witness_failures,
            "failed_comparisons_close_zones": failed_comparisons,
            "missing_platform_echo": missing_echo,
            "missing_cells": missing_cells,
            "technical_failure_rate": failure_rate,
            "stop_rule_breached": failure_rate > 0.10,
        },
    }
    text = json.dumps(summary, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"WROTE {args.out}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
