#!/usr/bin/env python3
"""PLATFORM-FIDELITY-01 readout: the paired hull-fidelity contrast.

Pools every ``cell_*.json`` under the campaign prefix (or a local tree) and
computes, per event pair and theta row, the pre-registered metrics from
``docs/covid/covid_platform_fidelity_prereg_v1.md``:

- P(takeoff) per hull (recorded_onsets >= the design's takeoff gate);
- the paired hull delta: per-seed dedicated - proxy recorded_onsets over
  seeds where BOTH arms take off, median with q05-q95;
- the CRN pairing diagnostic (Pearson rho on recorded_onsets over
  both-takeoff seeds; rho < 0.3 declares the unpaired analysis);
- takeoff-conditional asymptomatic share of lab_confirmed per hull;
- the failed-comparison audit: any cell whose protocol engine fired a
  close_zones protocol is a FAILED COMPARISON (reported, never deleted),
  and technical failures are counted against the >10% stop rule.

Cells pair across arms on (design_id, theta, seed); the proxy arm is the
one whose resolved platform_id equals the scenario's declared platform, so
the pairing is self-auditing against the payloads' own echoes.

Usage:
    python3 campaigns/covid/platform_fidelity_01/readout.py \
        --prefix s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/
    python3 campaigns/covid/platform_fidelity_01/readout.py --dir out/covid_platform_fidelity_01
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)

_DESIGNS = {
    "covid-platform-fidelity-dp":
        "picard_framework/runs/covid_platform_fidelity_dp_design.json",
    "covid-platform-fidelity-gm":
        "picard_framework/runs/covid_platform_fidelity_gm_design.json",
}
_DEFAULT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_platform_fidelity_01/"
)


def _expected_cells() -> dict[tuple[str, float], set[tuple[int, str]]]:
    """(design_id, theta) -> {(seed, arm_id)} the design declares."""
    expected: dict[tuple[str, float], set[tuple[int, str]]] = {}
    for design_id, rel in _DESIGNS.items():
        design = load_design(str(_REPO_ROOT / rel))
        for cell in enumerate_cells(design):
            expected.setdefault((design_id, cell.theta), set()).add(
                (cell.seed, str(cell.arm_id))
            )
    return expected


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


def _row_summary(pairs: dict[int, dict[str, dict[str, Any]]],
                 takeoff: int) -> dict[str, Any]:
    """One (design, theta) row: per-arm takeoff, paired delta, shares."""
    arm_ids = sorted({arm for by_arm in pairs.values() for arm in by_arm})
    if len(arm_ids) != 2:
        return {"status": f"expected 2 arms, found {arm_ids}"}
    # Identify proxy vs dedicated from the payloads' own echoes: the proxy
    # arm resolves to the scenario's declared platform; the dedicated arm
    # resolves to the event-faithful hull (a different platform_id).
    def _is_proxy(arm: str) -> bool:
        for by_arm in pairs.values():
            cell = by_arm.get(arm)
            if cell is not None:
                pf = cell["pf"]
                return (pf.get("resolved_platform_id")
                        == pf.get("scenario_declared_platform_id"))
        return False

    proxy_id = next(a for a in arm_ids if _is_proxy(a))
    dedicated_id = next(a for a in arm_ids if a != proxy_id)

    # Seed-explicit pairing: a seed contributes only when BOTH arms took off.
    per_seed: list[tuple[dict[str, Any], dict[str, Any]]] = []
    proxy_cells: list[dict[str, Any]] = []
    dedicated_cells: list[dict[str, Any]] = []
    for seed in sorted(pairs):
        by_arm = pairs[seed]
        p = by_arm.get(proxy_id)
        d = by_arm.get(dedicated_id)
        if p is None or d is None:
            continue
        proxy_cells.append(p)
        dedicated_cells.append(d)
        if (p["obs"].get("recorded_onsets", 0) >= takeoff
                and d["obs"].get("recorded_onsets", 0) >= takeoff):
            per_seed.append((p, d))

    def _takeoff(cell: dict[str, Any]) -> bool:
        return cell["obs"].get("recorded_onsets", 0) >= takeoff

    proxy_t = [c for c in proxy_cells if _takeoff(c)]
    dedicated_t = [c for c in dedicated_cells if _takeoff(c)]
    deltas = [d["obs"]["recorded_onsets"] - p["obs"]["recorded_onsets"]
              for p, d in per_seed]
    rho = _pearson(
        [p["obs"]["recorded_onsets"] for p, _ in per_seed],
        [d["obs"]["recorded_onsets"] for _, d in per_seed],
    )
    n = len(proxy_cells)
    return {
        "n_seeds": n,
        "proxy_arm": proxy_id,
        "dedicated_arm": dedicated_id,
        "P_takeoff_proxy": len(proxy_t) / n if n else float("nan"),
        "P_takeoff_dedicated": len(dedicated_t) / n if n else float("nan"),
        "n_both_takeoff": len(per_seed),
        "paired_delta_median": (
            _quantile(deltas, 0.5) if deltas else float("nan")
        ),
        "paired_delta_q05": _quantile(deltas, 0.05) if deltas else float("nan"),
        "paired_delta_q95": _quantile(deltas, 0.95) if deltas else float("nan"),
        "crn_rho": rho,
        "unpaired_declared": bool(rho == rho and rho < 0.3),
        "asym_share_proxy": _asym_share(proxy_t),
        "asym_share_dedicated": _asym_share(dedicated_t),
        "recorded_onsets_proxy_median": _quantile(
            [c["obs"]["recorded_onsets"] for c in proxy_t], 0.5,
        ) if proxy_t else float("nan"),
        "recorded_onsets_dedicated_median": _quantile(
            [c["obs"]["recorded_onsets"] for c in dedicated_t], 0.5,
        ) if dedicated_t else float("nan"),
    }


def _asym_share(cells: list[dict[str, Any]]) -> float:
    pos = sum(c["obs"].get("campaign_positives", 0) for c in cells)
    asym = sum(c["obs"].get("campaign_asymptomatic_positives", 0)
               for c in cells)
    return (asym / pos) if pos else float("nan")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default=_DEFAULT_PREFIX,
                        help="s3:// prefix to scan (default: the campaign prefix)")
    parser.add_argument("--dir", default=None,
                        help="local tree of block dirs instead of --prefix")
    parser.add_argument("--out", default=None,
                        help="write the JSON summary here (default: stdout only)")
    args = parser.parse_args(argv)

    iterator = (_iter_dir(Path(args.dir)) if args.dir
                else _iter_s3(args.prefix))
    cells: list[dict[str, Any]] = []
    for key, payload in iterator:
        cell = payload.get("cell") or {}
        obs = payload.get("observables") or {}
        pf = payload.get("platform_fidelity") or {}
        cells.append({
            "key": key,
            "design_id": payload.get("design_id"),
            "theta": cell.get("theta"),
            "seed": cell.get("seed"),
            "arm_id": cell.get("arm_id"),
            "obs": obs,
            "pf": pf,
        })

    # Pair on (design_id, theta, seed, arm); arms distinguished by arm_id.
    pairs: dict[tuple[str, float], dict[int, dict[str, dict[str, Any]]]] = {}
    for cell in cells:
        if cell["design_id"] is None or cell["theta"] is None:
            continue
        row = pairs.setdefault((cell["design_id"], cell["theta"]), {})
        row.setdefault(int(cell["seed"]), {})[str(cell["arm_id"])] = cell

    takeoff_gates = {
        design_id: load_design(str(_REPO_ROOT / rel)).takeoff_recorded_onsets
        for design_id, rel in _DESIGNS.items()
    }

    rows: dict[str, Any] = {}
    for (design_id, theta), by_seed in sorted(
        pairs.items(), key=lambda kv: (kv[0][0], kv[0][1]),
    ):
        gate = takeoff_gates.get(design_id, 10)
        rows[f"{design_id} @ theta={theta}"] = _row_summary(by_seed, gate)

    # Audits. Arm-aware: a row is in scope once ANY of its cells has landed,
    # so a staged campaign (canary before the full array) does not count
    # unsubmitted rows as missing. Unexpected cells are checked against the
    # full design enumeration.
    failed_comparisons = [
        c["key"] for c in cells
        if (c["pf"].get("close_zones_fired_flag"))
    ]
    missing_echo = [c["key"] for c in cells if not c["pf"].get("resolved_platform_id")]
    expected = _expected_cells()
    all_expected = {
        (design_id, theta, seed, arm)
        for (design_id, theta), cells_ in expected.items()
        for seed, arm in cells_
    }
    found = {
        (c["design_id"], c["theta"], c["seed"], str(c["arm_id"]))
        for c in cells
        if c["design_id"] is not None and c["theta"] is not None
    }
    found_rows = {(c["design_id"], c["theta"]) for c in cells
                  if c["design_id"] is not None and c["theta"] is not None}
    in_scope_expected = {
        (design_id, theta, seed, arm)
        for (design_id, theta) in found_rows
        for seed, arm in expected.get((design_id, theta), set())
    }
    missing = sorted(in_scope_expected - found)
    extra = sorted(found - all_expected)
    n_in_scope = len(in_scope_expected)
    failure_rate = (len(missing) + len(failed_comparisons)) / max(n_in_scope, 1)

    summary = {
        "campaign": "covid_platform_fidelity_01",
        "prefix": args.prefix if not args.dir else f"dir:{args.dir}",
        "n_cells_found": len(cells),
        "n_cells_expected_in_scope": n_in_scope,
        "n_cells_expected_total": len(all_expected),
        "rows": rows,
        "audit": {
            "failed_comparisons_close_zones": failed_comparisons,
            "missing_platform_echo": missing_echo,
            "missing_cells": missing,
            "unexpected_cells": extra,
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
