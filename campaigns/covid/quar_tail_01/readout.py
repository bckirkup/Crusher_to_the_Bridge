#!/usr/bin/env python3
"""QUAR-TAIL-SEAM-01 readout: pool campaign cells and apply the frozen
dual-prediction verdict grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree of block directories (``--dir``), pools the payloads through
``picard_framework.covid_boarding_screen.merge_screen``, and applies the
admissibility block the design froze before any cell ran:

* per arm row: takeoff-conditional and all-seed medians of
  ``infections_during_window`` vs the record-informed band [150,350],
  takeoff-conditional median capture (``lab_confirmed_total`` /
  ``infections_total``) vs the frozen >= 0.80 rise criterion, the
  seed-paired ``infections_before_quarantine`` delta vs the in-design D0
  row, and the during-window crew share — then the verdict grammar
  SEAM-LANDED / HALF-LANDED-MASS / UNDER-DAMPED / OVER-DAMPED / UNMOVED;
* every audit invariant swept on every cell (quarantine_witness window +
  activation + shipped exempt_classes echo, index-geometry fields,
  propensity draw, delivery echoes) PLUS the realized-share witnesses and
  the crew_duty_exclusion resolved/enabled echo on DUTY arms;
* the committed-cells drift witness: the in-design D0 rows paired
  seed-for-seed against the recorded ``covid_theta_refit_01``
  ``dp_theta_8p50`` cells (CAPTURE-01 / QUAR-TAIL-01's payload set).

The band and the capture criterion are context read from the design's
admissibility block, never fit targets; nothing here moves a constant.
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

_DESIGN = "picard_framework/runs/covid_quar_tail_01_design.json"
_REFIT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_theta_refit_01/"
)
_REFIT_D0_BLOCK = "dp_theta_8p50"

def _audit_thresholds() -> dict[str, Any]:
    """The frozen decision cutoffs, read from the design (Preflight Rule A).

    Every numerical gate the verdict/audit applies lives in the design's
    ``admissibility.audit_thresholds`` block; the readout never carries a
    cutoff the frozen design does not declare.
    """
    raw = json.loads((_REPO_ROOT / _DESIGN).read_text(encoding="utf-8"))
    thresholds = (raw.get("admissibility") or {}).get("audit_thresholds")
    if not isinstance(thresholds, dict):
        raise SystemExit(
            f"{_DESIGN} carries no admissibility.audit_thresholds block",
        )
    return thresholds


_TH = _audit_thresholds()
_BAND = tuple(float(v) for v in _TH["during_band"])
_CAPTURE_RISE = float(_TH["capture_rise"])
_BEFORE_UNMOVED_MAX_ABS = float(_TH["before_unmoved_max_abs"])
_SHARE_DEPARTURE_ABS = float(_TH["share_departure_abs"])
_MIN_TAKEOFF = int(_TH["min_takeoff_cells"])
_RECORD_ONSETS = float(_TH["record_total_onsets"])
_RECORD_BEFORE_SHARE = float(_TH["record_before_share"])
_RECORD_CREW_SHARE = float(_TH["record_crew_share_whole_voyage"])
_SHIPPED_EXEMPT = ("crew_engineering", "crew_galley", "crew_general",
                   "crew_medical")
# MESSBOX arms echo the 11-zone essential exempt list verbatim.
_MESSBOX_ARMS = {"D0_declared", "MB_DUTY"}
_ZONE_EXPECTED = {"D0_declared": 11 / 34, "MB_DUTY": 11 / 34}
_FRAC_ARMS = {"FRAQMB", "FRAQMB_DUTY"}
_FRAC_PROTOCOL = {arm: "SOP-017-QUARTERMB" for arm in _FRAC_ARMS}
_DUTY_ARMS = {"MB_DUTY", "FRAQMB_DUTY"}
_BASELINE_ARM = "D0_declared"
_CREW_N = 1045
_SHIPPED_DROPLET = (0.175, 0.0)  # far_field_share, settled_share


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


def _capture(payload: dict[str, Any]) -> float | None:
    """Confirmed-per-infection capture: lab_confirmed_total / infections."""
    infections = float(payload.get("infections_total") or 0)
    if infections <= 0:
        return None
    return float(payload.get("lab_confirmed_total") or 0) / infections


def _crew_window(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("crew_window") or {}


def _activation_snap(payload: dict[str, Any]) -> dict[str, Any]:
    return _crew_window(payload).get("at_activation") or {}


def _frac_expected(arm: str) -> int | None:
    if arm not in _FRAC_ARMS:
        return None
    return int(0.25 * _CREW_N + 0.5)


def _audit_shared(payload: dict[str, Any], tag: str) -> list[str]:
    """Shared invariants: witness, index geometry, propensity, delivery."""
    violations: list[str] = []
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
    # .get(..., -1) not `or -1`: a shipped 0.0 share is falsy but valid.
    far_got = split.get("far_field_share", -1)
    settled_got = split.get("settled_share", -1)
    if not math.isclose(float(far_got if far_got is not None else -1), far):
        violations.append(f"{tag}: droplet far_field_share")
    if not math.isclose(float(settled_got if settled_got is not None else -1),
                        settled):
        violations.append(f"{tag}: droplet settled_share")
    return violations


def _audit_crew_counts(cw: dict[str, Any], tag: str) -> list[str]:
    """crew_window snapshot bookkeeping: totals and count sums."""
    violations: list[str] = []
    for when in ("at_activation", "at_end"):
        snap = cw.get(when) or {}
        total = int(snap.get("total_crew") or -1)
        if total != _CREW_N:
            violations.append(f"{tag}: crew_window.{when}.total_crew {total}")
            continue
        confined_n = snap.get("confined_crew_count", -1)
        working_n = snap.get("working_crew_count", -1)
        if (int(confined_n if confined_n is not None else -1)
                + int(working_n if working_n is not None else -1)) != total:
            violations.append(f"{tag}: crew_window.{when} count mismatch")
    return violations


def _audit_arm_echo(payload: dict[str, Any], arm: str, tag: str) -> list[str]:
    """The arm-specific confinement-gate echo and realized share."""
    violations: list[str] = []
    cw = _crew_window(payload)
    snap = _activation_snap(payload)
    share = snap.get("realized_exempt_share")
    if arm in _MESSBOX_ARMS:
        zones = cw.get("exempt_work_zones")
        if not isinstance(zones, list) or len(zones) != 11:
            violations.append(f"{tag}: exempt_work_zones echo {zones}")
        if cw.get("exempt_fraction"):
            violations.append(f"{tag}: MESSBOX arm carries a fraction echo")
        working_zones = set(
            (snap.get("working_crew_by_posted_zone") or {}).keys()
        )
        if zones and not working_zones.issubset(set(zones)):
            violations.append(
                f"{tag}: working crew outside essential list "
                f"{sorted(working_zones - set(zones))}",
            )
    elif arm in _FRAC_ARMS:
        k = _frac_expected(arm)
        drawn = (cw.get("exempt_fraction_drawn") or {}).get(
            _FRAC_PROTOCOL[arm],
        ) or {}
        got_k = drawn.get("crew_general")
        if got_k != k:
            violations.append(
                f"{tag}: exempt_fraction_drawn {got_k} != {k}",
            )
        if cw.get("exempt_work_zones"):
            violations.append(f"{tag}: FRAQMB arm carries a zone echo")
    if share is None or not 0.0 < share < 1.0:
        violations.append(f"{tag}: degenerate realized share {share}")
    return violations


def _audit_cell(payload: dict[str, Any]) -> list[str]:
    """The frozen audit invariants, swept on one cell payload."""
    cell = payload.get("cell") or {}
    arm = str(cell.get("arm_id"))
    tag = f"{arm}@{cell.get('theta'):g}s{cell.get('seed')}"

    violations = _audit_shared(payload, tag)

    duty = payload.get("crew_duty_exclusion") or {}
    enabled = bool((duty.get("resolved") or {}).get("enabled"))
    if enabled != (arm in _DUTY_ARMS):
        violations.append(
            f"{tag}: crew_duty_exclusion resolved "
            f"{'disabled' if arm in _DUTY_ARMS else 'enabled'}",
        )

    cw = _crew_window(payload)
    if not cw:
        violations.append(f"{tag}: crew_window block missing")
        return violations
    violations += _audit_crew_counts(cw, tag)
    violations += _audit_arm_echo(payload, arm, tag)
    if int(cw.get("service_deliveries") or 0) <= 0:
        violations.append(f"{tag}: service_deliveries zero")
    if not isinstance(payload.get("funnel_hosts"), list):
        violations.append(f"{tag}: funnel_hosts missing (funnel_echo armed)")
    return violations


def _reach_echo(arm: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether the arm's mechanism provably fired, per the design's order."""
    if arm in _MESSBOX_ARMS:
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
        protocol = _FRAC_PROTOCOL[arm]
        drawn_ok = all(
            (
                (_crew_window(p).get("exempt_fraction_drawn") or {})
                .get(protocol) or {}
            ).get("crew_general") == k
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
    return {"kind": "baseline", "reached": arm == _BASELINE_ARM}


def _duty_witness(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """The duty-exclusion mechanism echo on a DUTY arm row."""
    blocks = [p.get("crew_duty_exclusion") or {} for p in payloads]
    excluded = [int(b.get("excluded_hosts") or 0) for b in blocks]
    return {
        "enabled_all": all(
            bool((b.get("resolved") or {}).get("enabled")) for b in blocks
        ),
        "excluded_hosts_min": min(excluded, default=None),
        "excluded_hosts_median": _median([float(e) for e in excluded]),
    }


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
    capture_takeoff = [
        c for c in (_capture(p) for p in taken) if c is not None
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
        "capture_median_takeoff": _median(capture_takeoff),
        "realized_exempt_share_median": _median(
            [s for s in realized if s is not None] or []
        ),
        "service_deliveries_min": min(deliveries, default=None),
    }


def _verdict(
    arm: str, metrics: dict[str, Any], reach: dict[str, Any],
) -> str:
    if arm == _BASELINE_ARM:
        return "BASELINE"
    if not reach["reached"]:
        return f"UNMOVED (reach echo {reach['kind']} shows the arm never fired)"
    if metrics["takeoff_n"] < _MIN_TAKEOFF:
        return "INSUFFICIENT-TAKEOFF-MASS"
    median = metrics["during_median_takeoff"]
    capture = metrics["capture_median_takeoff"]
    if median is None:
        return "NO CELLS"
    low, high = _BAND
    in_band = low <= median <= high
    failures: list[str] = []
    notes: list[str] = []
    if capture is None or capture < _CAPTURE_RISE:
        failures.append(f"capture {_fmt(capture)} < {_CAPTURE_RISE}")
    before_moved = (
        metrics["before_delta_median"] is not None
        and (
            metrics["before_delta_median"] != 0
            or (metrics["before_delta_max_abs"] or 0)
            > _BEFORE_UNMOVED_MAX_ABS
        )
    )
    if before_moved and arm in _DUTY_ARMS:
        # Standing policy: pre-window removals are the expected reported
        # effect (design admissibility), not a failed criterion.
        notes.append("before-window moved (expected: standing duty policy)")
    elif before_moved:
        failures.append("before-window moved")
    if metrics["before_delta_median"] is None:
        notes.append("before-pairing unavailable")
    if in_band and not failures:
        verdict = "SEAM-LANDED"
        if notes:
            verdict += " (" + "; ".join(notes) + ")"
        return verdict
    if in_band:
        return "HALF-LANDED-MASS (" + "; ".join(failures + notes) + ")"
    if median < low:
        return "OVER-DAMPED"
    return "UNDER-DAMPED"


def _refit_witness(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
    refit_prefix: str,
    takeoff_min: int,
) -> list[str]:
    """Pair this design's D0 cells against the committed takeoff 8p50 cells."""
    bucket, key_prefix = _split_s3(refit_prefix)
    client = _s3_client()
    lines: list[str] = []
    for (theta, arm), new_row in sorted(rows.items()):
        if arm != _BASELINE_ARM:
            continue
        deltas, old_during, new_during = [], [], []
        old_capture, new_capture = [], []
        for seed, new in sorted(new_row.items()):
            key = f"{key_prefix}{_REFIT_D0_BLOCK}/cell_{seed}.json"
            try:
                old = json.loads(client.get_object(
                    Bucket=bucket, Key=key)["Body"].read())
            except Exception:  # noqa: BLE001 - missing cell, report count
                continue
            # The design pairs only the committed takeoff seeds.
            if not _takeoff(old, takeoff_min):
                continue
            old_during.append(float(old.get("infections_during_window") or 0))
            new_during.append(
                float(new.get("infections_during_window") or 0))
            deltas.append(new_during[-1] - old_during[-1])
            if _capture(old) is not None:
                old_capture.append(_capture(old))
            if _capture(new) is not None:
                new_capture.append(_capture(new))
        lines.append(
            f"Theta {theta:g}: n={len(deltas)} paired vs committed "
            f"dp_theta_8p50 (committed-takeoff seeds) — during median new "
            f"{_median(new_during)} vs committed {_median(old_during)}, "
            f"median paired delta {_median(deltas)}; capture new "
            f"{_fmt(_median(new_capture))} vs committed "
            f"{_fmt(_median(old_capture))}",
        )
    return lines


def _baseline_trajectory(
    payloads: list[dict[str, Any]], takeoff_min: int,
) -> dict[str, Any]:
    """The frozen conditional_trajectory_clause scored on the D0 row.

    Among takeoff seeds: q05-q95 of recorded_onsets must contain the
    record's 197 and the median before_share must sit within 0.10 of the
    record's 0.173; scored only with >= _MIN_TAKEOFF takeoff cells.
    """
    taken = [p for p in payloads if _takeoff(p, takeoff_min)]
    if len(taken) < _MIN_TAKEOFF:
        return {
            "takeoff_n": len(taken),
            "verdict": "insufficient takeoff mass",
        }
    onsets = [
        float(_obs(p).get("recorded_onsets") or 0) for p in taken
    ]
    shares = [
        float(_obs(p).get("onsets_before_split_day") or 0) / o
        for p, o in zip(taken, onsets) if o > 0
    ]
    ordered = sorted(onsets)

    def _q(q: float) -> float:
        idx = q * (len(ordered) - 1)
        lo = int(idx)
        frac = idx - lo
        return ordered[lo] + frac * (ordered[min(lo + 1, len(ordered) - 1)]
                                     - ordered[lo])

    q05, q95 = _q(0.05), _q(0.95)
    before_med = _median(shares)
    ok = (
        q05 <= _RECORD_ONSETS <= q95
        and before_med is not None
        and abs(before_med - _RECORD_BEFORE_SHARE) <= 0.10
    )
    return {
        "takeoff_n": len(taken),
        "recorded_onsets_q05": q05,
        "recorded_onsets_q95": q95,
        "before_share_median": before_med,
        "verdict": (
            "contains 197 and within 0.10 of 0.173"
            if ok else "outside the clause"
        ),
    }


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
    refit_lines: list[str],
) -> str:
    by_seed_row = _rows(payloads)
    violations = [v for p in payloads.values() for v in _audit_cell(p)]
    surface = merge_screen(design, payloads, allow_partial=True)
    coverage = surface["coverage"]
    takeoff_min = design.takeoff_recorded_onsets

    lines = [
        "# QUAR-TAIL-SEAM-01 readout",
        "",
        f"- source: `{source}`",
        f"- design: `{_DESIGN}`",
        f"- coverage: {coverage['found']}/{coverage['expected']} cells "
        f"(partial: {coverage['partial']})",
        f"- audit invariants: {len(violations)} violation(s)",
        "",
        "| theta | arm | n | takeoff | during med (all) | during med "
        "(takeoff) | capture med (takeoff) | before med | Δbefore med / "
        "max abs | crew share | realized exempt | duty excluded med | "
        "min deliveries | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    flags: list[str] = []
    for (theta, arm), seeds in sorted(by_seed_row.items()):
        baseline = by_seed_row.get((theta, _BASELINE_ARM), {})
        metrics = _row_metrics(list(seeds.values()), baseline, takeoff_min)
        reach = _reach_echo(arm, list(seeds.values()))
        verdict = _verdict(arm, metrics, reach)
        realized = metrics["realized_exempt_share_median"]
        duty = (
            _duty_witness(list(seeds.values())) if arm in _DUTY_ARMS
            else {"excluded_hosts_median": None}
        )
        lines.append(
            f"| {theta:g} | {arm} | {metrics['n']} | {metrics['takeoff_n']} "
            f"| {metrics['during_median']} | "
            f"{metrics['during_median_takeoff']} | "
            f"{_fmt(metrics['capture_median_takeoff'])} | "
            f"{metrics['before_median']} | {metrics['before_delta_median']} / "
            f"{metrics['before_delta_max_abs']} | "
            f"{_fmt(metrics['crew_share_median'])} | {_fmt(realized)} "
            f"| {_fmt(duty['excluded_hosts_median'])} "
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
        if arm in _DUTY_ARMS and not duty["excluded_hosts_median"]:
            flags.append(
                f"{arm}@{theta:g}: crew_duty_exclusion fired with "
                "excluded_hosts 0 (mechanism-didn't-fire witness)",
            )
        if arm != _BASELINE_ARM and metrics["service_deliveries_min"] == 0:
            flags.append(
                f"{arm}@{theta:g}: service_deliveries collapsed to zero "
                "on a confining arm",
            )
    lines += ["", "## Baseline trajectory clause (D0, takeoff seeds)", ""]
    for (theta, arm), seeds in sorted(by_seed_row.items()):
        if arm != _BASELINE_ARM:
            continue
        traj = _baseline_trajectory(list(seeds.values()), takeoff_min)
        if traj["takeoff_n"] < _MIN_TAKEOFF:
            lines.append(
                f"- {arm}@{theta:g}: {traj['verdict']} "
                f"(takeoff {traj['takeoff_n']} < {_MIN_TAKEOFF})",
            )
        else:
            lines.append(
                f"- {arm}@{theta:g}: recorded_onsets q05-q95 "
                f"{traj['recorded_onsets_q05']:.0f}-{traj['recorded_onsets_q95']:.0f} "
                f"(record {_RECORD_ONSETS:g}), before_share median "
                f"{_fmt(traj['before_share_median'])} (record "
                f"{_RECORD_BEFORE_SHARE}) -> {traj['verdict']}",
            )
    lines += [
        "",
        f"Record-informed band {_BAND}; capture rise criterion "
        f">= {_CAPTURE_RISE} (record ~0.85, committed D0 pooled 0.723 / "
        f"median 0.525); record crew share {_RECORD_CREW_SHARE} "
        "(whole-voyage confirmed basis — direction, not magnitude). "
        "UNMOVED reach echoes audited before the median read.",
        "",
        "## Audit-invariant violations",
        "",
    ]
    lines += [f"- {v}" for v in violations] or ["- none"]
    lines += ["", "## Report flags", ""]
    lines += [f"- {f}" for f in flags] or ["- none"]
    lines += ["", "## Committed dp_theta_8p50 drift witness", ""]
    lines += [f"- {line}" for line in refit_lines]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


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
        design.takeoff_recorded_onsets,
    )
    report = _render(design, payloads, source, refit_lines)
    if args.out_md:
        args.out_md.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
