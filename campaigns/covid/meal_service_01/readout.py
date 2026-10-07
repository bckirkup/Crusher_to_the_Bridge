#!/usr/bin/env python3
"""MEAL-SVC-01 readout: pool campaign cells and apply the frozen verdict grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree of block directories (``--dir``), pools the payloads through
``picard_framework.covid_boarding_screen.merge_screen``, and applies the
admissibility block the design froze before any cell ran:

* per arm row: takeoff-conditional medians of
  ``confined_passenger_infections_during_quarantine`` vs the >=52 bound
  (the primary surface), ``infections_during_window`` reported beside
  [150,350] (not gating), the during-window crew share vs the record's
  ~0.29 (direction), and the seed-paired deltas vs the row's in-design
  ``*_svc_base`` — then the verdict grammar CHANNEL-FOUND / DOSE-EMPTY /
  MASS-ONLY (reach echoes audited first);
* every audit invariant swept on every cell (CW-02's set carried
  unchanged) PLUS the MEAL-SVC-01 witnesses: the resolved-block direction
  echo, host-credited dose tally iff DIR, the realized
  stewards-per-confined-host structure witness, and deliveries parity;
* the CW-02 drift witness: the in-design ``*_svc_base`` rows paired
  seed-for-seed against the recorded ``covid_crew_window_02`` cells at
  2df542ff (D0_declared_svc_base vs t7p9e6_d0, zone_narrow_svc_base vs
  t7p9e6_zone_narrow).

The >=52 bound is the record-implied F13/F14 floor read from the design's
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

_DESIGN = "picard_framework/runs/covid_meal_service_01_design.json"
_CW2_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_crew_window_02/"
)
# In-design base arm -> the CW-02 block it pairs against (7.9e6 only).
_CW2_PAIR = {
    "D0_declared_svc_base": "t7p9e6_d0",
    "zone_narrow_svc_base": "t7p9e6_zone_narrow",
}

_PASSENGER_BOUND = 52.0
# "Materially toward >=52": a takeoff-conditional median at or past half
# the bound (declared before the surface is seen; the bound itself is
# 52-92 and the canary's stop rule reads the same threshold).
_CHANNEL_FOUND_MIN = 26.0
_BAND = (150.0, 350.0)
_RECORD_CREW_SHARE = 0.29
_SHIPPED_EXEMPT = ("crew_engineering", "crew_galley", "crew_general",
                   "crew_medical")
_CW2_ZONE_NARROW_N = 11
_CW2_ZONE_NARROW_EXPECTED = 11 / 34
_CREW_N = 1045
_SHIPPED_DROPLET = (0.175, 0.0)  # far_field_share, settled_share
# Deliveries parity: a *_svc_dir* row whose median departs its *_svc_base
# row's median by more than this fraction is a cadence-defect flag.
_DELIVERY_DEPARTURE_REL = 0.15
# CW-02 measured per-cell deliveries band @7.9e6 (context for parity).
_CW2_DELIVERIES = (128000, 166000)
# Section-mode structure witness bounds: a bound steward plus sticky
# re-draws should leave each confined host with ~1-2 distinct stewards;
# median beyond _SECT_MEDIAN_MAX or any host beyond _SECT_MAX_MAX means
# the binding isn't armed.
_SECT_MEDIAN_MAX = 2.0
_SECT_MAX_MAX = 6
# Uniform-mode sanity floor: with ~160k deliveries over ~700 crew the
# per-host distinct-steward count must be far above section's ~1-2.
_UNIFORM_MIN_MEDIAN = 10.0
# Passenger-acquisitions "unmoved" bound: |median - base median| under
# this absolute slack reads as unmoved (rare-count wobble).
_UNMOVED_ABS = 3.0


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


def _passenger_during(payload: dict[str, Any]) -> float:
    by_role = payload.get("during_window_by_role") or {}
    return float(by_role.get("passenger") or 0)


def _confined_pax(payload: dict[str, Any]) -> float:
    return float(
        payload.get("confined_passenger_infections_during_quarantine") or 0
    )


def _crew_window(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("crew_window") or {}


def _activation_snap(payload: dict[str, Any]) -> dict[str, Any]:
    return _crew_window(payload).get("at_activation") or {}


def _service_direction(payload: dict[str, Any]) -> Any:
    resolved = (
        ((payload.get("delivery") or {}).get("caregiver") or {})
        .get("roles") or {}
    ).get("service") or {}
    return resolved.get("direction")


def _is_dir(arm: str) -> bool:
    return arm.endswith("_svc_dir") or arm.endswith("_svc_dir_sect")


def _is_sect(arm: str) -> bool:
    return arm.endswith("_svc_dir_sect")


def _is_base(arm: str) -> bool:
    return arm.endswith("_svc_base")


def _is_zone(arm: str) -> bool:
    return arm.startswith("zone_narrow_")


def _base_arm(arm: str) -> str:
    """The in-design *_svc_base row this arm pairs against."""
    if _is_zone(arm):
        return "zone_narrow_svc_base"
    return "D0_declared_svc_base"


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
    # .get(..., -1) not `or -1`: a shipped 0.0 share is falsy but valid.
    far_got = split.get("far_field_share", -1)
    settled_got = split.get("settled_share", -1)
    if not math.isclose(float(far_got if far_got is not None else -1), far):
        violations.append(f"{tag}: droplet far_field_share")
    if not math.isclose(float(settled_got if settled_got is not None else -1),
                        settled):
        violations.append(f"{tag}: droplet settled_share")

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
        confined_n = snap.get("confined_crew_count", -1)
        working_n = snap.get("working_crew_count", -1)
        if (int(confined_n if confined_n is not None else -1)
                + int(working_n if working_n is not None else -1)) != total:
            violations.append(f"{tag}: crew_window.{when} count mismatch")
    snap = _activation_snap(payload)
    share = snap.get("realized_exempt_share")
    if _is_zone(arm):
        zones = cw.get("exempt_work_zones")
        if not isinstance(zones, list) or len(zones) != _CW2_ZONE_NARROW_N:
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
    else:
        if cw.get("exempt_work_zones") or cw.get("exempt_fraction"):
            violations.append(f"{tag}: D0 carries a CW-02 gate echo")
        if share is not None and share <= 0.9:
            violations.append(f"{tag}: D0 realized_exempt_share {share}")
    deliveries = int(cw.get("service_deliveries") or 0)
    if deliveries <= 0:
        violations.append(f"{tag}: service_deliveries zero")

    # MEAL-SVC-01 direction echo + per-direction tallies.
    direction = _service_direction(payload)
    expected_direction = "both" if _is_dir(arm) else "responder"
    if direction != expected_direction:
        violations.append(
            f"{tag}: resolved direction {direction!r} != "
            f"{expected_direction!r}",
        )
    if cw.get("service_direction") != expected_direction:
        violations.append(
            f"{tag}: crew_window.service_direction "
            f"{cw.get('service_direction')!r} != {expected_direction!r}",
        )
    host_credited = float(cw.get("service_dose_to_host_credited") or 0.0)
    # No-takeoff cells carry no shedding steward by construction, so the
    # host-credit tally is legitimately 0 there — the iff-DIR check is
    # takeoff-conditional.
    took_off = int(payload.get("infections_total") or 0) > 0
    if _is_dir(arm):
        if took_off and host_credited <= 0.0:
            violations.append(
                f"{tag}: service_dose_to_host_credited 0 on a DIR arm",
            )
    elif host_credited > 0.0:
        violations.append(
            f"{tag}: service_dose_to_host_credited {host_credited} on BASE",
        )

    # MEAL-SVC-01 structure witness.
    expected_mode = "section" if _is_sect(arm) else "uniform"
    if cw.get("service_responder_mode") != expected_mode:
        violations.append(
            f"{tag}: service_responder_mode "
            f"{cw.get('service_responder_mode')!r} != {expected_mode!r}",
        )
    stewards = cw.get("service_stewards_per_confined_host") or {}
    stew_med = stewards.get("median")
    stew_max = stewards.get("max")
    draws = int(cw.get("service_section_steward_draws") or 0)
    if _is_sect(arm):
        if draws <= 0:
            violations.append(f"{tag}: no section steward draws")
        if stew_med is None or stew_med > _SECT_MEDIAN_MAX:
            violations.append(
                f"{tag}: stewards/host median {stew_med} not collapsed",
            )
        if stew_max is not None and stew_max > _SECT_MAX_MAX:
            violations.append(
                f"{tag}: stewards/host max {stew_max} not collapsed",
            )
    else:
        if draws > 0:
            violations.append(f"{tag}: section draws on a uniform arm")
        if stew_med is not None and stew_med < _UNIFORM_MIN_MEDIAN:
            violations.append(
                f"{tag}: stewards/host median {stew_med} too low for "
                "uniform",
            )
    return violations


def _reach_echo(arm: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether the arm's mechanism provably fired, per the design's order."""
    rows = list(payloads)
    cws = [_crew_window(p) for p in rows]
    if _is_zone(arm):
        snaps = [_activation_snap(p) for p in rows]
        zones = [cw.get("exempt_work_zones") for cw in cws]
        working_inside = all(
            set((s.get("working_crew_by_posted_zone") or {}).keys())
            .issubset(set(z or ()))
            for s, z in zip(snaps, zones)
        )
        shares = [s.get("realized_exempt_share") for s in snaps]
        zone_ok = bool(
            all(zones) and working_inside
            and all(s is not None and 0.0 < s < 1.0 for s in shares)
        )
    else:
        shares = []
        zone_ok = True
    echo: dict[str, Any] = {
        "direction": _is_dir(arm),
        "zone_ok": zone_ok,
        "share_median": _median(
            [s for s in shares if s is not None] or []
        ),
        "host_credited_total": sum(
            float(cw.get("service_dose_to_host_credited") or 0.0)
            for cw in cws
        ),
        "steward_median_of_medians": _median([
            float((cw.get("service_stewards_per_confined_host") or {})
                  .get("median") or 0.0)
            for cw in cws
        ]),
    }
    fired = zone_ok
    if _is_dir(arm):
        fired = fired and echo["host_credited_total"] > 0.0
    if _is_sect(arm):
        med = echo["steward_median_of_medians"]
        fired = fired and (
            med is not None and med <= _SECT_MEDIAN_MAX
        )
    echo["reached"] = fired
    return echo


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
    confined_takeoff = [_confined_pax(p) for p in taken]
    pax_takeoff = [_passenger_during(p) for p in taken]
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
    confined_deltas = [
        _confined_pax(p)
        - _confined_pax(baseline_by_seed[
            int((p.get("cell") or {}).get("seed") or -1)])
        for p in payloads
        if int((p.get("cell") or {}).get("seed") or -1) in baseline_by_seed
    ]
    realized = [
        (_activation_snap(p).get("realized_exempt_share"))
        for p in payloads
    ]
    cws = [_crew_window(p) for p in payloads]
    deliveries = [int(cw.get("service_deliveries") or 0) for cw in cws]
    return {
        "n": len(payloads),
        "takeoff_n": len(taken),
        "during_median": _median(during),
        "during_median_takeoff": _median(during_takeoff),
        "confined_pax_median": _median(
            [_confined_pax(p) for p in payloads]
        ),
        "confined_pax_median_takeoff": _median(confined_takeoff),
        "pax_during_median_takeoff": _median(pax_takeoff),
        "confined_pax_delta_median": _median(confined_deltas),
        "before_median": _median(before),
        "before_delta_median": _median(deltas),
        "before_delta_max_abs": max((abs(d) for d in deltas), default=None),
        "crew_share_median": _median(shares),
        "realized_exempt_share_median": _median(
            [s for s in realized if s is not None] or []
        ),
        "service_deliveries_min": min(deliveries, default=None),
        "service_deliveries_median": _median(
            [float(d) for d in deliveries]
        ),
        "host_dose_credited_median": _median([
            float(cw.get("service_dose_to_host_credited") or 0.0)
            for cw in cws
        ]),
        "steward_dose_credited_median": _median([
            float(cw.get("service_dose_credited") or 0.0)
            for cw in cws
        ]),
        "stewards_per_host_median": _median([
            float((cw.get("service_stewards_per_confined_host") or {})
                  .get("median") or 0.0)
            for cw in cws
        ]),
        "route_service_to_host_total": sum(
            int((p.get("during_quarantine_by_route") or {})
                .get("service_to_host") or 0)
            for p in payloads
        ),
    }


def _verdict(
    arm: str, metrics: dict[str, Any], reach: dict[str, Any],
    base_median: float | None,
) -> str:
    if _is_base(arm):
        return "BASELINE"
    if not reach["reached"]:
        return ("UNARMED (reach echo shows the arm never fired: "
                f"{json.dumps(reach, default=str)[:160]})")
    median = metrics["confined_pax_median_takeoff"]
    if metrics["takeoff_n"] < 5:
        median = metrics["confined_pax_median"]
    if median is None:
        return "NO CELLS"
    moved = median >= _CHANNEL_FOUND_MIN
    host_dose = metrics["host_dose_credited_median"] or 0.0
    if moved:
        return (
            f"CHANNEL-FOUND (confined-pax takeoff median {median:g} "
            f"vs bound >={_PASSENGER_BOUND:g}; base {base_median})"
        )
    if host_dose > 0.0:
        return (
            f"DOSE-EMPTY (host-credited dose median {host_dose:.4g} > 0 "
            f"but confined-pax median {median:g} unmoved vs base "
            f"{base_median})"
        )
    return (
        f"MASS-ONLY (host-credited dose ~0; confined-pax median "
        f"{median:g} vs base {base_median})"
    )


def _cw02_witness(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
    cw2_prefix: str,
) -> list[str]:
    """Pair this design's *_svc_base cells against the CW-02 cells."""
    bucket, key_prefix = _split_s3(cw2_prefix)
    client = _s3_client()
    lines: list[str] = []
    for arm, block in sorted(_CW2_PAIR.items()):
        new_row = next(
            (seeds for (theta, a), seeds in rows.items() if a == arm),
            {},
        )
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
            f"{arm} vs CW-02 {block}: n={len(deltas)} paired — "
            f"during median new {_median(new_during)} vs CW-02 "
            f"{_median(old_during)}, median paired delta {_median(deltas)}, "
            f"nonzero {sum(1 for d in deltas if d != 0)}",
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
    cw2_lines: list[str],
) -> str:
    by_seed_row = _rows(payloads)
    violations = [v for p in payloads.values() for v in _audit_cell(p)]
    surface = merge_screen(design, payloads, allow_partial=True)
    coverage = surface["coverage"]
    takeoff_min = design.takeoff_recorded_onsets

    lines = [
        "# MEAL-SVC-01 readout",
        "",
        f"- source: `{source}`",
        f"- design: `{_DESIGN}`",
        f"- coverage: {coverage['found']}/{coverage['expected']} cells "
        f"(partial: {coverage['partial']})",
        f"- audit invariants: {len(violations)} violation(s)",
        "",
        "| theta | arm | n | takeoff | confined-pax med (takeoff) | "
        "Δpax vs base | pax during med | during med (takeoff) | "
        "before med | Δbefore med / max abs | crew share | realized "
        "exempt | deliveries med | host dose med | stewards/host | "
        "svc_to_host acq | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    flags: list[str] = []
    for (theta, arm), seeds in sorted(by_seed_row.items()):
        baseline = by_seed_row.get((theta, _base_arm(arm)), {})
        metrics = _row_metrics(list(seeds.values()), baseline, takeoff_min)
        reach = _reach_echo(arm, list(seeds.values()))
        base_metrics = _row_metrics(
            list(baseline.values()), baseline, takeoff_min,
        )
        verdict = _verdict(
            arm, metrics, reach,
            base_metrics["confined_pax_median_takeoff"],
        )
        realized = metrics["realized_exempt_share_median"]
        lines.append(
            f"| {theta:g} | {arm} | {metrics['n']} | {metrics['takeoff_n']} "
            f"| {metrics['confined_pax_median_takeoff']} | "
            f"{metrics['confined_pax_delta_median']} | "
            f"{metrics['pax_during_median_takeoff']} | "
            f"{metrics['during_median_takeoff']} | "
            f"{metrics['before_median']} "
            f"| {metrics['before_delta_median']} / "
            f"{metrics['before_delta_max_abs']} | "
            f"{_fmt(metrics['crew_share_median'])} | {_fmt(realized)} "
            f"| {metrics['service_deliveries_median']} | "
            f"{_fmt(metrics['host_dose_credited_median'])} | "
            f"{_fmt(metrics['stewards_per_host_median'])} | "
            f"{metrics['route_service_to_host_total']} | {verdict} |",
        )
        if _is_zone(arm) and realized is not None:
            if abs(realized - _CW2_ZONE_NARROW_EXPECTED) > 0.10:
                flags.append(
                    f"{arm}@{theta:g}: realized exempt share "
                    f"{realized:.3f} departs lottery expectation "
                    f"{_CW2_ZONE_NARROW_EXPECTED:.3f} by >0.10",
                )
        if metrics["service_deliveries_min"] == 0:
            flags.append(
                f"{arm}@{theta:g}: service_deliveries collapsed to zero "
                "on a confining arm (R3 starved)",
            )
        if not _is_base(arm):
            base_del = base_metrics["service_deliveries_median"]
            row_del = metrics["service_deliveries_median"]
            if (
                base_del is not None and row_del is not None
                and abs(row_del - base_del) > _DELIVERY_DEPARTURE_REL * base_del
            ):
                flags.append(
                    f"{arm}@{theta:g}: deliveries median {row_del:g} "
                    f"departs base {base_del:g} by "
                    f">{_DELIVERY_DEPARTURE_REL:.0%} (cadence defect)",
                )
            if (
                metrics["confined_pax_median_takeoff"] is not None
                and metrics["confined_pax_median_takeoff"]
                >= _CHANNEL_FOUND_MIN
            ):
                flags.append(
                    f"{arm}@{theta:g}: CHANNEL-FOUND neighbourhood — "
                    f"confined-pax takeoff median "
                    f"{metrics['confined_pax_median_takeoff']:g} "
                    f">= {_CHANNEL_FOUND_MIN:g}",
                )
    lines += [
        "",
        f"Passenger bound >={_PASSENGER_BOUND:g} (F13/F14, primary); "
        f"CHANNEL-FOUND reads at >={_CHANNEL_FOUND_MIN:g}. Record-informed "
        f"band {_BAND} reported beside, not gating; record crew share "
        f"{_RECORD_CREW_SHARE}; CW-02 deliveries band {_CW2_DELIVERIES}. "
        "UNARMED reach echoes audited before the median read.",
        "",
        "## Audit-invariant violations",
        "",
    ]
    lines += [f"- {v}" for v in violations] or ["- none"]
    lines += ["", "## Report flags", ""]
    lines += [f"- {f}" for f in flags] or ["- none"]
    lines += ["", "## CW-02 drift witness", ""]
    lines += [f"- {line}" for line in cw2_lines]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prefix", help="s3:// campaign prefix")
    group.add_argument("--dir", type=Path,
                       help="local tree of block directories")
    parser.add_argument("--cw2-prefix", default=_CW2_PREFIX,
                        help="CW-02 cell prefix for the drift witness; "
                             "empty string skips it")
    parser.add_argument("--out", type=Path, default=None,
                        help="write the readout markdown here")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / _DESIGN))
    if args.prefix:
        source_iter = _iter_s3_payloads(args.prefix)
        source = args.prefix
    else:
        source_iter = _iter_local_payloads(args.dir)
        source = str(args.dir)
    payloads = {
        _payload_key(p): p for _, p in source_iter
    }
    if not payloads:
        raise SystemExit(f"no cell payloads under {source}")
    cw2_lines = (
        _cw02_witness(_rows(payloads), args.cw2_prefix)
        if args.cw2_prefix else ["(skipped)"]
    )
    text = _render(design, payloads, source, cw2_lines)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"WROTE {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
