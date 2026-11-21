#!/usr/bin/env python3
"""SEED-RING-01 readout: the declared-placement founder-pool probe.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree (``--dir``), groups cells by (theta, arm_id) and renders:

* per cell: founder yield (``seed_ring.aboard_window_acquisitions`` +
  clean bound + day-0 count + route split), ignition day (first day
  cumulative infections reach IGNITION_MASS), takeoff gate,
  recorded_onsets, before_share, and the realized placement audit
  (``seed_ring.seeded_hosts[*].dining_zone`` vs the declared buffet
  service type);
* per arm row: the frozen verdict grammar of the design's admissibility
  block — SEED-RING-LANDED / FOUNDERS-LIFTED-TIMING-SHORT /
  NULL-PLACEMENT / INSUFFICIENT-TAKEOFF-MASS — from the three legs:
  founder median >= 10, ignition median <= 9, and the verbatim
  conditional trajectory clause (q05-q95 of takeoff recorded_onsets
  contains 197 AND median before_share within 0.10 of 0.173);
* the committed-cells drift witness: the in-design D0 rows paired
  seed-for-seed against the committed refit ``dp_theta_8p50`` cells.

Verdicts come only from the design's frozen thresholds; this file adds no
fit and no post-hoc criterion.

Usage:
    python3 campaigns/covid/seed_ring_01/readout.py \
        --prefix s3://<bucket>/campaign/covid_seed_ring_01/ [--out-md md]
    python3 campaigns/covid/seed_ring_01/readout.py --dir <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    resolve_dining_service_type,
)
from picard_framework.covid_boarding_screen import (  # noqa: E402
    KEY_INDEX_ONSET_DAY,
    KEY_INDEX_SHEDDING_AT_DAY0,
    load_design,
)

_DESIGN = "picard_framework/runs/covid_seed_ring_01_design.json"
_REFIT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_theta_refit_01/"
)
_REFIT_D0_BLOCK = "dp_theta_8p50"
_PROBE_ARM = "PLACEMENT_BUFFET"
_BASELINE_ARM = "D0_declared"
_IGNITION_MASS = 50
_PLACEMENT_ECHO = {"dining_service_type": "buffet"}
_BUFFET_ZONE = "Windjammer"  # mega_cruise_5000's surge venue


def _audit_thresholds() -> dict[str, Any]:
    raw = json.loads((_REPO_ROOT / _DESIGN).read_text(encoding="utf-8"))
    thresholds = (raw.get("admissibility") or {}).get("audit_thresholds")
    if not isinstance(thresholds, dict):
        raise SystemExit(
            f"{_DESIGN} carries no admissibility.audit_thresholds block",
        )
    return thresholds


_TH = _audit_thresholds()
_FOUNDER_MIN = float(_TH["founder_yield_median_min"])
_IGN_MAX = float(_TH["ignition_day_median_max"])
_SHARE_ABS = float(_TH["share_departure_abs"])
_MIN_TAKEOFF = int(_TH["min_takeoff_cells"])
_RECORD_ONSETS = float(_TH["record_total_onsets"])
_RECORD_BEFORE_SHARE = float(_TH["record_before_share"])


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dev box has boto3
        raise SystemExit("boto3 is required for --prefix") from exc
    return boto3.client("s3")


def _split_s3(uri: str) -> tuple[str, str]:
    assert uri.startswith("s3://"), f"need s3:// uri, got {uri!r}"
    rest = uri[5:]
    bucket, _, prefix = rest.partition("/")
    return bucket, prefix.rstrip("/") + "/"


def _iter_s3_payloads(prefix: str) -> Iterable[tuple[str, dict[str, Any]]]:
    bucket, key_prefix = _split_s3(prefix)
    client = _s3_client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json") or key.endswith("design.json"):
                continue
            body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            yield key, json.loads(body)


def _iter_local_payloads(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    for path in sorted(root.rglob("cell_*.json")):
        yield str(path), json.loads(path.read_text(encoding="utf-8"))


def _payload_key(payload: dict[str, Any]) -> str:
    return str(payload["cell"]["key"])


def _obs(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("observables") or {}


def _seed_ring(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("seed_ring") or {}


def _takeoff(payload: dict[str, Any]) -> bool:
    return (
        int(_obs(payload).get("recorded_onsets") or 0)
        >= _TH_TAKEOFF_MIN
    )


_TH_TAKEOFF_MIN = 10  # design.takeoff_recorded_onsets; checked at render


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return (
        ordered[mid] if n % 2
        else 0.5 * (ordered[mid - 1] + ordered[mid])
    )


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _ignition_day(payload: dict[str, Any]) -> int | None:
    daily = {
        int(k): int(v)
        for k, v in (payload.get("acquisition_curve") or {})
        .get("total_by_day", {}).items()
    }
    cumulative = 0
    for day in sorted(daily):
        cumulative += daily[day]
        if cumulative >= _IGNITION_MASS:
            return day
    return None


def _before_share(payload: dict[str, Any]) -> float | None:
    onsets = float(_obs(payload).get("recorded_onsets") or 0)
    if onsets <= 0:
        return None
    return (
        float(_obs(payload).get("onsets_before_split_day") or 0) / onsets
    )


def _seeded_dining_zones(payload: dict[str, Any]) -> list[str]:
    return [
        str(h.get("dining_zone") or "")
        for h in (_seed_ring(payload).get("seeded_hosts") or [])
    ]


def _zones_are_buffet(payload: dict[str, Any]) -> bool:
    zones = _seeded_dining_zones(payload)
    return bool(zones) and all(
        resolve_dining_service_type({"name": z}) == "buffet" for z in zones
    )


def _quantile(sorted_values: list[float], q: float) -> float:
    idx = q * (len(sorted_values) - 1)
    lo = int(idx)
    frac = idx - lo
    return sorted_values[lo] + frac * (
        sorted_values[min(lo + 1, len(sorted_values) - 1)] - sorted_values[lo]
    )


def _trajectory_clause(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """The verbatim conditional_trajectory_clause on one arm's takeoff cells."""
    taken = [p for p in payloads if _takeoff(p)]
    if len(taken) < _MIN_TAKEOFF:
        return {"takeoff_n": len(taken), "verdict": "insufficient takeoff mass"}
    onsets = sorted(
        float(_obs(p).get("recorded_onsets") or 0) for p in taken
    )
    shares = [s for s in (_before_share(p) for p in taken)
              if s is not None]
    q05, q95 = _quantile(onsets, 0.05), _quantile(onsets, 0.95)
    before_med = _median(shares)
    ok = (
        q05 <= _RECORD_ONSETS <= q95
        and before_med is not None
        and abs(before_med - _RECORD_BEFORE_SHARE) <= _SHARE_ABS
    )
    return {
        "takeoff_n": len(taken),
        "recorded_onsets_q05": q05,
        "recorded_onsets_q95": q95,
        "before_share_median": before_med,
        "ok": ok,
        "verdict": (
            "contains 197 and within 0.10 of 0.173"
            if ok else "outside the clause"
        ),
    }


def _row_metrics(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    taken = [p for p in payloads if _takeoff(p)]
    founders = [
        float(_seed_ring(p).get("aboard_window_acquisitions") or 0)
        for p in taken
    ]
    ignitions = [
        float(d) for d in (_ignition_day(p) for p in taken)
        if d is not None
    ]
    all_founders = [
        float(_seed_ring(p).get("aboard_window_acquisitions") or 0)
        for p in payloads
    ]
    route_totals: dict[str, int] = {}
    for p in payloads:
        for route, n in (
            _seed_ring(p).get("aboard_window_by_route") or {}
        ).items():
            route_totals[route] = route_totals.get(route, 0) + int(n)
    return {
        "n": len(payloads),
        "takeoff_n": len(taken),
        "founder_median_takeoff": _median(founders),
        "founder_median_all": _median(all_founders),
        "ignition_day_median_takeoff": _median(ignitions),
        "route_totals": route_totals,
        "trajectory": _trajectory_clause(payloads),
    }


def _verdict(arm: str, metrics: dict[str, Any]) -> str:
    if arm == _BASELINE_ARM:
        return "BASELINE (drift witness)"
    if metrics["takeoff_n"] < _MIN_TAKEOFF:
        return "INSUFFICIENT-TAKEOFF-MASS"
    founder_ok = (
        (metrics["founder_median_takeoff"] or 0.0) >= _FOUNDER_MIN
    )
    ignition_ok = (
        metrics["ignition_day_median_takeoff"] is not None
        and metrics["ignition_day_median_takeoff"] <= _IGN_MAX
    )
    trajectory_ok = bool(metrics["trajectory"].get("ok"))
    if founder_ok and ignition_ok and trajectory_ok:
        return "SEED-RING-LANDED"
    if founder_ok:
        return (
            "FOUNDERS-LIFTED-TIMING-SHORT (ignition "
            f"{_fmt(metrics['ignition_day_median_takeoff'])} vs <= {_IGN_MAX:g}; "
            f"trajectory {metrics['trajectory']['verdict']})"
        )
    return (
        "NULL-PLACEMENT (founder median "
        f"{_fmt(metrics['founder_median_takeoff'])} < {_FOUNDER_MIN:g}: "
        "the embarkation-day crowd structure is under-declared)"
    )


def _audit(
    payloads: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Frozen audit invariants → violations; soft checks → flags."""
    violations: list[str] = []
    flags: list[str] = []
    for key, payload in sorted(payloads.items()):
        cell = payload["cell"]
        arm = str(cell.get("arm_id"))
        seed = cell.get("seed")
        tag = f"{arm}@{seed}"
        sr = _seed_ring(payload)
        spec = sr.get("seed_spec") or {}
        has_placement = "placement" in spec
        if arm == _PROBE_ARM:
            if not has_placement:
                violations.append(
                    f"{tag}: seed_spec carries no placement echo on the "
                    "placement arm — the declaration never reached the cell",
                )
            elif spec["placement"] != _PLACEMENT_ECHO:
                violations.append(
                    f"{tag}: seed_spec.placement {spec['placement']} != "
                    f"declared {_PLACEMENT_ECHO}",
                )
            if not _zones_are_buffet(payload):
                violations.append(
                    f"{tag}: seeded_hosts dining_zone "
                    f"{_seeded_dining_zones(payload)} does not resolve to "
                    "a buffet venue — the placement draw misfired",
                )
        elif has_placement:
            violations.append(
                f"{tag}: placement echo present on the baseline arm — "
                "the declaration leaked off its arm",
            )
        if payload.get(KEY_INDEX_ONSET_DAY) != -1.0:
            violations.append(
                f"{tag}: index_onset_day "
                f"{payload.get(KEY_INDEX_ONSET_DAY)} != -1.0",
            )
        if not payload.get(KEY_INDEX_SHEDDING_AT_DAY0):
            violations.append(
                f"{tag}: index_shedding_at_day0 false — the founder "
                "window has no emitter",
            )
        funnel = payload.get("funnel_hosts")
        if not funnel:
            violations.append(
                f"{tag}: empty funnel_hosts on a completed cell — "
                "funnel_echo did not fire",
            )
        sr_hosts = sr.get("seeded_hosts") or []
        if len(sr_hosts) != int(spec.get("count", 1) or 1):
            flags.append(
                f"{tag}: seeded_hosts {len(sr_hosts)} != declared count "
                f"{spec.get('count')}",
            )
    return violations, flags


def _refit_witness(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
    refit_prefix: str,
) -> list[str]:
    """Pair this design's D0 cells against the committed 8p50 cells."""
    bucket, key_prefix = _split_s3(refit_prefix)
    client = _s3_client()
    lines: list[str] = []
    for (theta, arm), new_row in sorted(rows.items()):
        if arm != _BASELINE_ARM:
            continue
        deltas, paired = [], 0
        for seed, new in sorted(new_row.items()):
            key = f"{key_prefix}{_REFIT_D0_BLOCK}/cell_{seed}.json"
            try:
                old = json.loads(client.get_object(
                    Bucket=bucket, Key=key)["Body"].read())
            except Exception:  # noqa: BLE001 - missing cell, report count
                continue
            paired += 1
            old_onsets = float(
                _obs(old).get("recorded_onsets") or 0)
            new_onsets = float(
                _obs(new).get("recorded_onsets") or 0)
            deltas.append(new_onsets - old_onsets)
        nonzero = sum(1 for d in deltas if d != 0)
        lines.append(
            f"Theta {theta:g}: n={paired} paired vs committed "
            f"dp_theta_8p50 — recorded_onsets paired deltas nonzero on "
            f"{nonzero}/{paired} seeds, median delta {_fmt(_median(deltas))}"
            + (" — DRIFT WITNESS CLEAN" if not nonzero else
               " — DRIFT: attribute before trusting the placement read"),
        )
    return lines


def _rows(
    payloads: dict[str, dict[str, Any]],
) -> dict[tuple[float, str], dict[int, dict[str, Any]]]:
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]] = {}
    for payload in payloads.values():
        cell = payload["cell"]
        rows.setdefault(
            (float(cell["theta"]), str(cell["arm_id"])), {},
        )[int(cell["seed"])] = payload
    return rows


def _render(
    design: Any,
    payloads: dict[str, dict[str, Any]],
    source: str,
    refit_lines: list[str],
) -> str:
    violations, flags = _audit(payloads)
    rows = _rows(payloads)
    lines = [
        f"# {design.design_id} readout — {source}",
        "",
        "## Arm verdicts",
        "",
    ]
    for (theta, arm), seeds in sorted(rows.items()):
        metrics = _row_metrics(list(seeds.values()))
        traj = metrics["trajectory"]
        verdict = _verdict(arm, metrics)
        lines.append(
            f"- {arm}@{theta:g}: **{verdict}** — n={metrics['n']} "
            f"(takeoff {metrics['takeoff_n']}); founder median "
            f"{_fmt(metrics['founder_median_takeoff'])} takeoff-conditional "
            f"({_fmt(metrics['founder_median_all'])} all cells; committed "
            f"drawn median 2.5); ignition median "
            f"{_fmt(metrics['ignition_day_median_takeoff'])}; routes "
            f"{metrics['route_totals']}",
        )
        if traj.get("recorded_onsets_q05") is not None:
            lines.append(
                f"  trajectory: recorded_onsets q05-q95 "
                f"{traj['recorded_onsets_q05']:.0f}-"
                f"{traj['recorded_onsets_q95']:.0f} (record "
                f"{_RECORD_ONSETS:g}), before_share median "
                f"{_fmt(traj['before_share_median'])} (record "
                f"{_RECORD_BEFORE_SHARE}) -> {traj['verdict']}",
            )
        else:
            lines.append(f"  trajectory: {traj['verdict']}")
    lines += [
        "",
        f"Frozen legs: founder median >= {_FOUNDER_MIN:g}, ignition "
        f"median <= {_IGN_MAX:g}, trajectory clause (contains "
        f"{_RECORD_ONSETS:g}, within {_SHARE_ABS} of "
        f"{_RECORD_BEFORE_SHARE}). Min takeoff {_MIN_TAKEOFF} cells.",
        "",
        "## Audit-invariant violations",
        "",
    ]
    lines += [f"- {v}" for v in violations] or ["- none"]
    lines += ["", "## Report flags", ""]
    lines += [f"- {f}" for f in flags] or ["- none"]
    lines += ["", "## Committed dp_theta_8p50 drift witness", ""]
    lines += [f"- {line}" for line in refit_lines] or ["- skipped (--no-refit)"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prefix", help="s3:// campaign prefix")
    group.add_argument("--dir", type=Path,
                       help="local tree of cell_*.json (block dirs or flat)")
    parser.add_argument("--refit-prefix", default=None,
                        help=f"committed refit prefix (default {_REFIT_PREFIX})")
    parser.add_argument("--no-refit", action="store_true")
    parser.add_argument("--out-md", type=Path, default=None,
                        help="also write the markdown report here")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / _DESIGN))
    global _TH_TAKEOFF_MIN
    _TH_TAKEOFF_MIN = int(design.takeoff_recorded_onsets)
    if args.prefix:
        source = args.prefix
        items = _iter_s3_payloads(args.prefix)
    else:
        source = str(args.dir)
        items = _iter_local_payloads(args.dir)
    payloads = {
        _payload_key(p): p for _, p in items if p.get("cell")
    }
    if not payloads:
        raise SystemExit(f"no cell payloads under {source}")
    refit_lines = [] if args.no_refit else _refit_witness(
        _rows(payloads), args.refit_prefix or _REFIT_PREFIX,
    )
    report = _render(design, payloads, source, refit_lines)
    if args.out_md:
        args.out_md.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
