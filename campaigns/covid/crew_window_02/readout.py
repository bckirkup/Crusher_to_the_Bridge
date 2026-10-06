#!/usr/bin/env python3
"""CREW-WINDOW-02 readout: pool campaign cells and apply the frozen verdict grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree of block directories (``--dir``), pools the payloads through
``picard_framework.covid_boarding_screen.merge_screen``, and applies the
admissibility block the design froze before any cell ran:

* per arm row (theta x arm): takeoff-conditional and all-seed medians of
  ``infections_during_window``, the seed-paired ``infections_before_quarantine``
  delta vs the in-design D0 row, and the during-window crew share vs the
  record's ~0.29 — then the verdict grammar CHANNEL-LANDED /
  UNDER-ATTENUATED / OVER-ATTENUATED / UNMOVED (reach echoes audited first);
* every audit invariant swept on every cell (quarantine_witness window +
  activation + shipped exempt_classes echo, index-geometry fields,
  propensity draw, delivery echoes) PLUS the CW-02 realized-share
  witnesses: crew_window counts, the declared gate echoes, the
  sticky-drawn exempt sets, and service_deliveries;
* the CW-01 drift witness: the in-design D0 rows paired seed-for-seed
  against the recorded ``covid_crew_window_01`` D0 cells at ea9550ef.

The record-informed band [150, 350] is context read from the design's
admissibility block, never a fit target; nothing here moves a constant.
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
    load_design,
    merge_screen,
)

_DESIGN = "picard_framework/runs/covid_crew_window_02_design.json"
_CW1_PREFIX = "campaign/covid_crew_window_01/"
_CW1_D0_BLOCKS = {1000000.0: "t1e6_d0", 7900000.0: "t7p9e6_d0"}

_BAND = (150.0, 350.0)
_RECORD_CREW_SHARE = 0.29
_SHIPPED_EXEMPT = ("crew_engineering", "crew_galley", "crew_general",
                   "crew_medical")
_ZONE_ARMS = {"ZONE_NARROW", "ZONE_WIDE"}
_ZONE_EXPECTED = {"ZONE_NARROW": 11 / 34, "ZONE_WIDE": 19 / 34}
_FRAC_ARMS = {"FRAC_25": 0.25, "FRAC_50": 0.5, "FRAC_75": 0.75}
_CREW_N = 1045
_SHIPPED_DROPLET = (0.175, 0.0)  # far_field_share, settled_share
# "Before mass seed-paired unmoved": every |delta| under this bound counts
# as unmoved (RNG reorder wobble); a material move is reported, not scored.
_BEFORE_UNMOVED_MAX_ABS = 5
# ZONE-arm realized-share report threshold: departure from the lottery
# expectation beyond this absolute share is flagged in the readout.
_SHARE_DEPARTURE_ABS = 0.10


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


def _takeoff(payload: dict[str, Any], threshold: int) -> bool:
    return int(_obs(payload).get("recorded_onsets") or 0) >= threshold


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2)


def _crew_share(payload: dict[str, Any]) -> float | None:
    by_role = payload.get("during_window_by_role") or {}
    crew = float(by_role.get("crew") or 0)
    passenger = float(by_role.get("passenger") or 0)
    total = crew + passenger
    return None if total <= 0 else crew / total


def _crew_window(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("crew_window") or {}


def _activation_snap(payload: dict[str, Any]) -> dict[str, Any]:
    return _crew_window(payload).get("at_activation") or {}


def _frac_expected(arm: str) -> int | None:
    frac = _FRAC_ARMS.get(arm)
    return None if frac is None else int(frac * _CREW_N + 0.5)


def _audit_cell(payload: dict[str, Any]) -> list[str]:
    """The frozen audit invariants, swept on one cell payload."""
    violations: list[str] = []
    cell = payload.get("cell") or {}
    arm = str(cell.get("arm_id"))
    seed = cell.get("seed")
    tag = f"{arm}@{cell.get('theta'):g}s{seed}"

    witness = payload.get("quarantine_witness") or {}
    if witness.get("window_days") != [16, 30] or not witness.get("activated"):
        violations.append(f"{tag}: quarantine_witness window/activation")
    got = tuple(sorted(witness.get("exempt_classes") or ()))
    if got != _SHIPPED_EXEMPT:
        violations.append(
            f"{tag}: exempt_classes {list(got)} != {list(_SHIPPED_EXEMPT)}",
        )
    if payload.get("index_onset_day") != -1.0:
        violations.append(f"{tag}: index_onset_day")
    if payload.get("index_shedding_at_day0") is not True:
        violations.append(f"{tag}: index_shedding_at_day0")
    if int((payload.get("propensity_draw") or {}).get("units_drawn") or 0) <= 0:
        violations.append(f"{tag}: propensity_draw.units_drawn")
    delivery = payload.get("delivery") or {}
    if (delivery.get("caregiver") or {}).get("mode") != "on":
        violations.append(f"{tag}: caregiver.mode")
    if delivery.get("presentation_draw_mode") != "once_per_course":
        violations.append(f"{tag}: presentation_draw_mode")
    if delivery.get("hand_reservoir_mode") != "hygiene_cycle":
        violations.append(f"{tag}: hand_reservoir_mode")
    split = delivery.get("droplet_field_split") or {}
    far, settled = _SHIPPED_DROPLET
    if not math.isclose(float(split.get("far_field_share") or -1), far):
        violations.append(f"{tag}: droplet far_field_share")
    if not math.isclose(float(split.get("settled_share") or -1), settled):
        violations.append(f"{tag}: droplet settled_share")

    # CREW-WINDOW-02 realized-share witnesses.
    cw = _crew_window(payload)
    if not cw:
        violations.append(f"{tag}: crew_window block missing")
        return violations
    for when in ("at_activation", "at_end"):
        snap = cw.get(when) or {}
        total = int(snap.get("total_crew") or -1)
        if total != _CREW_N:
            violations.append(f"{tag}: crew_window.{when}.total_crew {total}")
            continue
        if (int(snap.get("confined_crew_count") or -1)
                + int(snap.get("working_crew_count") or -1)) != total:
            violations.append(f"{tag}: crew_window.{when} count mismatch")
    snap = _activation_snap(payload)
    share = snap.get("realized_exempt_share")
    if arm == "D0_declared":
        if cw.get("exempt_work_zones") or cw.get("exempt_fraction"):
            violations.append(f"{tag}: D0 carries a CW-02 gate echo")
        if share is not None and share <= 0.9:
            violations.append(f"{tag}: D0 realized_exempt_share {share}")
    elif arm in _ZONE_ARMS:
        zones = cw.get("exempt_work_zones")
        expected_n = 11 if arm == "ZONE_NARROW" else 19
        if not isinstance(zones, list) or len(zones) != expected_n:
            violations.append(f"{tag}: exempt_work_zones echo {zones}")
        working_zones = set(
            (snap.get("working_crew_by_posted_zone") or {}).keys()
        )
        if zones and not working_zones.issubset(set(zones)):
            violations.append(
                f"{tag}: working crew outside essential list "
                f"{sorted(working_zones - set(zones))}",
            )
        if share is None or not 0.0 < share < 1.0:
            violations.append(f"{tag}: degenerate realized share {share}")
    elif arm in _FRAC_ARMS:
        k = _frac_expected(arm)
        drawn = (cw.get("exempt_fraction_drawn") or {}).get(
            "SOP-017-" + {"FRAC_25": "QUARTER", "FRAC_50": "HALF",
                          "FRAC_75": "THREEQ"}[arm],
        ) or {}
        got_k = drawn.get("crew_general")
        if got_k != k:
            violations.append(
                f"{tag}: exempt_fraction_drawn {got_k} != {k}",
            )
        if share is None or not 0.0 < share < 1.0:
            violations.append(f"{tag}: degenerate realized share {share}")
    if int(cw.get("service_deliveries") or 0) <= 0:
        violations.append(f"{tag}: service_deliveries zero")
    return violations


def _reach_echo(arm: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether the arm's mechanism provably fired, per the design's order."""
    if arm in _ZONE_ARMS:
        snaps = [_activation_snap(p) for p in payloads]
        zones = [
            _crew_window(p).get("exempt_work_zones") for p in payloads
        ]
        working_inside = all(
            set((s.get("working_crew_by_posted_zone") or {}).keys())
            .issubset(set(z or ()))
            for s, z in zip(snaps, zones)
        )
        shares = [s.get("realized_exempt_share") for s in snaps]
        return {
            "kind": "crew_window.exempt_work_zones + realized share",
            "per_seed_share": shares,
            "share_median": _median(
                [s for s in shares if s is not None] or []
            ),
            "lottery_expectation": _ZONE_EXPECTED[arm],
            "reached": bool(
                all(zones) and working_inside
                and all(s is not None and 0.0 < s < 1.0 for s in shares)
            ),
        }
    if arm in _FRAC_ARMS:
        k = _frac_expected(arm)
        snaps = [_activation_snap(p) for p in payloads]
        drawn_ok = all(
            any(
                drawn.get("crew_general") == k
                for drawn in (
                    _crew_window(p).get("exempt_fraction_drawn") or {}
                ).values()
            )
            for p in payloads
        )
        shares = [s.get("realized_exempt_share") for s in snaps]
        return {
            "kind": "crew_window.exempt_fraction_drawn",
            "expected_k": k,
            "per_seed_share": shares,
            "share_median": _median(
                [s for s in shares if s is not None] or []
            ),
            "reached": bool(
                drawn_ok
                and all(s is not None and 0.0 < s < 1.0 for s in shares)
            ),
        }
    return {"kind": "baseline", "reached": True}


def _row_metrics(
    payloads: list[dict[str, Any]],
    baseline_by_seed: dict[int, dict[str, Any]],
    takeoff_min: int,
) -> dict[str, Any]:
    during = [float(p.get("infections_during_window") or 0) for p in payloads]
    before = [float(p.get("infections_before_quarantine") or 0)
              for p in payloads]
    taken = [p for p in payloads if _takeoff(p, takeoff_min)]
    during_takeoff = [
        float(p.get("infections_during_window") or 0) for p in taken
    ]
    shares = [s for s in (_crew_share(p) for p in payloads)
              if s is not None]
    deltas = [
        float(p.get("infections_before_quarantine") or 0)
        - float((baseline_by_seed.get(
            int((p.get("cell") or {}).get("seed") or -1)) or {})
            .get("infections_before_quarantine") or 0)
        for p in payloads
        if int((p.get("cell") or {}).get("seed") or -1) in baseline_by_seed
    ]
    realized = [
        (_activation_snap(p).get("realized_exempt_share"))
        for p in payloads
    ]
    deliveries = [
        int(_crew_window(p).get("service_deliveries") or 0)
        for p in payloads
    ]
    return {
        "n": len(payloads),
        "takeoff_n": len(taken),
        "during_median": _median(during),
        "during_median_takeoff": _median(during_takeoff),
        "before_median": _median(before),
        "before_delta_median": _median(deltas),
        "before_delta_max_abs": max((abs(d) for d in deltas), default=None),
        "before_delta_nonzero": sum(1 for d in deltas if d != 0),
        "crew_share_median": _median(shares),
        "realized_exempt_share_median": _median(
            [s for s in realized if s is not None] or []
        ),
        "service_deliveries_min": min(deliveries, default=None),
    }


def _verdict(
    arm: str, metrics: dict[str, Any], reach: dict[str, Any],
    d0_share: float | None,
) -> str:
    if arm == "D0_declared":
        return "BASELINE"
    if not reach["reached"]:
        return f"UNMOVED (reach echo {reach['kind']} shows the arm never fired)"
    median = metrics["during_median_takeoff"]
    if metrics["takeoff_n"] < 5:
        median = metrics["during_median"]
    if median is None:
        return "NO CELLS"
    low, high = _BAND
    before_ok = (
        metrics["before_delta_median"] == 0
        and (metrics["before_delta_max_abs"] or 0) <= _BEFORE_UNMOVED_MAX_ABS
    )
    share = metrics["crew_share_median"]
    toward = share is not None and d0_share is not None and share < d0_share
    if median < low:
        return "OVER-ATTENUATED"
    if median > high:
        return "UNDER-ATTENUATED"
    if before_ok and toward:
        return "CHANNEL-LANDED"
    reasons = []
    if not before_ok:
        reasons.append("before-window moved")
    if not toward:
        reasons.append("crew share not toward the record")
    return "IN-BAND-INCOMPLETE (median in band; " + "; ".join(reasons) + ")"


def _cw1_witness(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
    cw1_prefix: str,
) -> list[str]:
    """Pair this design's D0 cells against the recorded CW-01 D0 cells."""
    bucket, key_prefix = _split_s3(cw1_prefix)
    client = _s3_client()
    lines: list[str] = []
    for theta, block in sorted(_CW1_D0_BLOCKS.items()):
        new_row = rows.get((theta, "D0_declared"), {})
        deltas, old_during, new_during = [], [], []
        for seed, new in sorted(new_row.items()):
            key = f"{key_prefix}{block}/cell_{seed}.json"
            try:
                old = json.loads(client.get_object(
                    Bucket=bucket, Key=key)["Body"].read())
            except Exception:  # noqa: BLE001 - missing cell, report count
                continue
            old_during.append(float(old.get("infections_during_window") or 0))
            new_during.append(
                float(new.get("infections_during_window") or 0))
            deltas.append(new_during[-1] - old_during[-1])
        lines.append(
            f"Theta {theta:g}: n={len(deltas)} paired vs CW-01 D0 — "
            f"during median new {_median(new_during)} vs CW-01 "
            f"{_median(old_during)}, median paired delta {_median(deltas)}",
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
    design: Any, payloads: dict[str, dict[str, Any]], source: str,
    cw1_lines: list[str],
) -> str:
    by_seed_row = _rows(payloads)
    violations = [v for p in payloads.values() for v in _audit_cell(p)]
    surface = merge_screen(design, payloads, allow_partial=True)
    coverage = surface["coverage"]
    takeoff_min = design.takeoff_recorded_onsets

    lines = [
        "# CREW-WINDOW-02 readout",
        "",
        f"- source: `{source}`",
        f"- design: `{_DESIGN}`",
        f"- coverage: {coverage['found']}/{coverage['expected']} cells "
        f"(partial: {coverage['partial']})",
        f"- audit invariants: {len(violations)} violation(s)",
        "",
        "| theta | arm | n | takeoff | during med (all) | during med "
        "(takeoff) | before med | Δbefore med / max abs | crew share | "
        "realized exempt | min deliveries | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    flags: list[str] = []
    for (theta, arm), seeds in sorted(by_seed_row.items()):
        baseline = by_seed_row.get((theta, "D0_declared"), {})
        metrics = _row_metrics(list(seeds.values()), baseline, takeoff_min)
        reach = _reach_echo(arm, list(seeds.values()))
        d0_metrics = _row_metrics(list(baseline.values()), baseline,
                                  takeoff_min)
        verdict = _verdict(
            arm, metrics, reach, d0_metrics["crew_share_median"],
        )
        realized = metrics["realized_exempt_share_median"]
        lines.append(
            f"| {theta:g} | {arm} | {metrics['n']} | {metrics['takeoff_n']} "
            f"| {metrics['during_median']} | "
            f"{metrics['during_median_takeoff']} | {metrics['before_median']} "
            f"| {metrics['before_delta_median']} / "
            f"{metrics['before_delta_max_abs']} | "
            f"{_fmt(metrics['crew_share_median'])} | {_fmt(realized)} "
            f"| {metrics['service_deliveries_min']} | {verdict} |",
        )
        if arm in _ZONE_EXPECTED and realized is not None:
            expected = _ZONE_EXPECTED[arm]
            if abs(realized - expected) > _SHARE_DEPARTURE_ABS:
                flags.append(
                    f"{arm}@{theta:g}: realized exempt share "
                    f"{realized:.3f} departs lottery expectation "
                    f"{expected:.3f} by >{_SHARE_DEPARTURE_ABS}",
                )
        if arm != "D0_declared" and metrics["service_deliveries_min"] == 0:
            flags.append(
                f"{arm}@{theta:g}: service_deliveries collapsed to zero "
                "on a confining arm (R3 starved)",
            )
    lines += [
        "",
        f"Record-informed band {_BAND} (context only); record crew share "
        f"{_RECORD_CREW_SHARE}. UNMOVED reach echoes audited before the "
        "median read.",
        "",
        "## Audit-invariant violations",
        "",
    ]
    lines += [f"- {v}" for v in violations] or ["- none"]
    lines += ["", "## Report flags", ""]
    lines += [f"- {f}" for f in flags] or ["- none"]
    lines += ["", "## CW-01 drift witness", ""]
    lines += [f"- {line}" for line in cw1_lines]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prefix", help="s3:// campaign prefix")
    group.add_argument("--dir", type=Path,
                       help="local tree of cell_*.json (block dirs or flat)")
    parser.add_argument("--cw1-prefix", default=None,
                        help=f"CW-01 recorded prefix (default {_CW1_PREFIX})")
    parser.add_argument("--no-cw1", action="store_true")
    parser.add_argument("--out-md", type=Path, default=None,
                        help="also write the markdown report here")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / _DESIGN))
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
    cw1_lines = [] if args.no_cw1 else _cw1_witness(
        _rows(payloads), args.cw1_prefix or _CW1_PREFIX,
    )
    report = _render(design, payloads, source, cw1_lines)
    if args.out_md:
        args.out_md.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
