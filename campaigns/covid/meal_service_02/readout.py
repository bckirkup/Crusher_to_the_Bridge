#!/usr/bin/env python3
"""MEAL-SVC-02 readout: pool campaign cells and apply the frozen verdict grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree of block directories (``--dir``), pools the payloads through
``picard_framework.covid_boarding_screen.merge_screen``, and applies the
admissibility block the design froze before any cell ran:

* per arm row: takeoff-conditional medians of
  ``confined_passenger_infections_during_quarantine`` vs the bound region
  (~52; record-implied pax mass ~45-160 as context), the during-window
  total reported beside [150,350] (not gating), the during-window crew
  share vs the record's ~0.29 (direction), the steward share of
  during-window crew acquisitions (the crew-side co-surface), and the
  seed-paired deltas vs the row's in-design ``*_svc_base`` — then the
  verdict grammar MAGNITUDE-LANDED / OVER-ATTENUATED / STILL-HIGH, with
  the ladder-level NONLINEAR-BREAK check on the factor-ordered medians;
* every audit invariant swept on every cell (CW-02's set carried
  unchanged) PLUS the MEAL-SVC-02 witnesses: the host-factor echo
  (``contact_factor_to_host`` + ``contact_factor_to_host_mode`` in both
  the resolved block and the crew_window block), the realized-factor
  lottery check (median/mean vs the declared spec; OFF arm all-zero),
  host-credit iff armed-and-nonzero, distinct-steward structure, and
  deliveries parity;
* the drift witnesses: the in-design ``*_svc_base`` rows paired
  seed-for-seed against the recorded ``covid_crew_window_02`` cells at
  2df542ff, and the ``cf_shipped`` row's confined-pax median reported
  beside the MEAL-SVC-01 canary's 804 at 32b11ccf.

The ~52 bound is the record-implied F13/F14 floor read from the design's
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

_DESIGN = "picard_framework/runs/covid_meal_service_02_design.json"
_CW2_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_crew_window_02/"
)
# In-design base arm -> the CW-02 block it pairs against (7.9e6 only).
_CW2_PAIR = {
    "d0_declared_svc_base": "t7p9e6_d0",
    "zone_narrow_svc_base": "t7p9e6_zone_narrow",
}
# MEAL-SVC-01 canary measured medians at 32b11ccf — the cf_shipped row's
# drift reference (reported beside, not required bit-identical).
_MS1_CANARY_CONFINED_PAX = 804.0
_MS1_CANARY_DELIVERIES = 166000.0

# The host-factor spec each arm declares (None = absent -> shared draw).
_HOST_FACTOR_DECLARED: dict[str, Any] = {
    "d0_declared_svc_base": None,
    "zone_narrow_svc_base": None,
    "zone_narrow_svc_dir_cf_shipped": None,
    "zone_narrow_svc_dir_cf_mid": [0.02, 0.08],
    "zone_narrow_svc_dir_cf_lo": [0.005, 0.02],
    "zone_narrow_svc_dir_cf_floor": 0.01,
    "zone_narrow_svc_dir_cf_off": 0.0,
    "d0_svc_dir_cf_shipped": None,
    "d0_svc_dir_cf_off": 0.0,
    "zone_narrow_svc_dir_sect_cf_lo": [0.005, 0.02],
}
# The shipped shared factor the host direction inherits when absent.
_SHIPPED_CONTACT_FACTOR = [0.05, 0.3]

_PASSENGER_BOUND = 52.0
# Bound region for MAGNITUDE-LANDED: half the >=52 floor up to the top of
# the record-implied pax-mass context band (declared before any cell ran).
_LANDED_LO = 26.0
_LANDED_HI = 160.0
# STILL-HIGH above this median.
_STILL_HIGH = 200.0
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
# Lottery tolerance: a declared uniform's realized median/mean must sit
# inside the declared window and the mean within this relative slack of
# the declared midpoint.
_LOTTERY_MEAN_REL = 0.10


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


def _service_block(payload: dict[str, Any]) -> dict[str, Any]:
    return (
        ((payload.get("delivery") or {}).get("caregiver") or {})
        .get("roles") or {}
    ).get("service") or {}


def _is_dir(arm: str) -> bool:
    return "_svc_dir_" in arm


def _is_sect(arm: str) -> bool:
    return "_sect" in arm


def _is_base(arm: str) -> bool:
    return arm.endswith("_svc_base")


def _is_zone(arm: str) -> bool:
    return arm.startswith("zone_narrow_")


def _base_arm(arm: str) -> str:
    """The in-design *_svc_base row this arm pairs against."""
    if _is_zone(arm):
        return "zone_narrow_svc_base"
    return "d0_declared_svc_base"


def _expected_host_factor_echo(arm: str) -> tuple[str, Any]:
    """(mode, echo) the resolved block must carry for this arm."""
    declared = _HOST_FACTOR_DECLARED.get(arm)
    if declared is None:
        return "shared", _SHIPPED_CONTACT_FACTOR
    return "declared", declared


def _is_off(arm: str) -> bool:
    declared = _HOST_FACTOR_DECLARED.get(arm)
    return (
        declared is not None and not isinstance(declared, list)
        and float(declared) == 0.0
    )


def _audit_host_factor(
    tag: str, arm: str, payload: dict[str, Any],
    cw: dict[str, Any],
) -> list[str]:
    """The MEAL-SVC-02 host-factor witnesses on one cell."""
    violations: list[str] = []
    mode, echo = _expected_host_factor_echo(arm)
    service = _service_block(payload)
    for label, blk in (("resolved", service), ("crew_window", cw)):
        if blk.get("contact_factor_to_host_mode") != mode:
            violations.append(
                f"{tag}: {label} contact_factor_to_host_mode "
                f"{blk.get('contact_factor_to_host_mode')!r} != {mode!r}",
            )
        if blk.get("contact_factor_to_host") != echo:
            violations.append(
                f"{tag}: {label} contact_factor_to_host "
                f"{blk.get('contact_factor_to_host')!r} != {echo!r}",
            )
    draws = cw.get("service_host_factor_draws") or {}
    n = int(draws.get("n") or 0)
    deliveries = int(cw.get("service_deliveries") or 0)
    if not _is_dir(arm):
        # Responder direction never reaches the host seam.
        if n != 0:
            violations.append(f"{tag}: {n} host-factor draws on BASE")
        return violations
    if n != deliveries:
        violations.append(
            f"{tag}: host-factor draws n={n} != deliveries {deliveries}",
        )
    if n <= 0:
        return violations
    declared = _HOST_FACTOR_DECLARED.get(arm)
    med, mean = draws.get("median"), draws.get("mean")
    f_min, f_max = draws.get("min"), draws.get("max")
    if med is None or mean is None or f_min is None or f_max is None:
        violations.append(f"{tag}: host-factor draw stats missing")
        return violations
    if declared is None:
        lo, hi = _SHIPPED_CONTACT_FACTOR
    elif isinstance(declared, list):
        lo, hi = float(declared[0]), float(declared[1])
    else:
        lo = hi = float(declared)
    if not lo <= f_min <= f_max <= hi:
        violations.append(
            f"{tag}: realized host factor [{f_min}, {f_max}] outside "
            f"declared [{lo}, {hi}]",
        )
    if lo == hi:
        if not math.isclose(med, lo, rel_tol=1e-9):
            violations.append(
                f"{tag}: scalar host factor median {med} != {lo}",
            )
    else:
        midpoint = (lo + hi) / 2.0
        if not math.isclose(
            mean, midpoint, rel_tol=_LOTTERY_MEAN_REL,
        ):
            violations.append(
                f"{tag}: realized host-factor mean {mean:.4g} departs "
                f"declared midpoint {midpoint:.4g} by "
                f">{_LOTTERY_MEAN_REL:.0%} (lottery check)",
            )
    return violations


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

    # Direction echo + per-direction tallies.
    direction = _service_block(payload).get("direction")
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
    host_delivered = float(cw.get("service_dose_to_host_delivered") or 0.0)
    # No-takeoff cells carry no shedding steward by construction, so the
    # host-credit tally is legitimately 0 there — the check is
    # takeoff-conditional. The OFF arm's zero is unconditional.
    took_off = int(payload.get("infections_total") or 0) > 0
    if _is_dir(arm):
        if _is_off(arm):
            if host_delivered > 0.0 or host_credited > 0.0:
                violations.append(
                    f"{tag}: host dose {host_delivered:.4g} delivered / "
                    f"{host_credited:.4g} credited on the OFF arm",
                )
        elif took_off and host_credited <= 0.0:
            violations.append(
                f"{tag}: service_dose_to_host_credited 0 on an armed "
                "DIR arm",
            )
        # The steward side stays on the shared draw on every DIR arm.
        if took_off and float(
            cw.get("service_dose_credited") or 0.0
        ) <= 0.0:
            violations.append(
                f"{tag}: service_dose_credited 0 on a took-off DIR cell",
            )
    elif host_credited > 0.0:
        violations.append(
            f"{tag}: service_dose_to_host_credited {host_credited} on BASE",
        )

    violations += _audit_host_factor(tag, arm, payload, cw)

    # Structure witness.
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
    draw_ns = [
        int((cw.get("service_host_factor_draws") or {}).get("n") or 0)
        for cw in cws
    ]
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
        "host_factor_draws_min": min(draw_ns, default=0),
        "steward_median_of_medians": _median([
            float((cw.get("service_stewards_per_confined_host") or {})
                  .get("median") or 0.0)
            for cw in cws
        ]),
    }
    fired = zone_ok
    if _is_dir(arm):
        # OFF arms fire by construction (zero host credit is the
        # mechanism working, not an arm failure); every other DIR arm
        # must credit something somewhere across its cells.
        fired = fired and (
            _is_off(arm) or echo["host_credited_total"] > 0.0
        )
        fired = fired and echo["host_factor_draws_min"] > 0
    if _is_sect(arm):
        med = echo["steward_median_of_medians"]
        fired = fired and (
            med is not None and med <= _SECT_MEDIAN_MAX
        )
    echo["reached"] = fired
    return echo


def _steward_share_of_crew(payload: dict[str, Any]) -> float | None:
    """Steward share of during-window crew acquisitions (co-surface)."""
    by_route = payload.get("during_quarantine_by_route") or {}
    steward = float(by_route.get("caregiver") or 0)
    crew_total = float(
        (payload.get("during_window_by_role") or {}).get("crew") or 0
    )
    return None if crew_total <= 0 else steward / crew_total


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
    steward_shares = [
        s for s in (_steward_share_of_crew(p) for p in payloads)
        if s is not None
    ]
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
    factor_medians = [
        float((cw.get("service_host_factor_draws") or {}).get("median"))
        for cw in cws
        if (cw.get("service_host_factor_draws") or {}).get("median")
        is not None
    ]
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
        "steward_share_of_crew_median": _median(steward_shares),
        "realized_exempt_share_median": _median(
            [s for s in realized if s is not None] or []
        ),
        "service_deliveries_min": min(deliveries, default=None),
        "service_deliveries_median": _median(
            [float(d) for d in deliveries]
        ),
        "host_factor_median_of_medians": _median(factor_medians),
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
    share = metrics["crew_share_median"]
    share_note = "" if share is None else f"; crew share {share:.3f}"
    if median > _STILL_HIGH:
        return (
            f"STILL-HIGH (confined-pax median {median:g} > "
            f"{_STILL_HIGH:g}{share_note})"
        )
    if _LANDED_LO <= median <= _LANDED_HI:
        return (
            f"MAGNITUDE-LANDED (confined-pax median {median:g} in the "
            f"bound region {_LANDED_LO:g}-{_LANDED_HI:g}{share_note})"
        )
    if median < _LANDED_LO:
        return (
            f"OVER-ATTENUATED (confined-pax median {median:g} toward the "
            f"responder-only floor; base {base_median}{share_note})"
        )
    return (
        f"BETWEEN (confined-pax median {median:g} above the bound "
        f"region but below {_STILL_HIGH:g}{share_note})"
    )


def _ladder_check(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
    medians: dict[str, float | None],
) -> list[str]:
    """NONLINEAR-BREAK: the ZONE_NARROW factor ladder must be monotone.

    Ordering by declared factor mean: OFF(0) <= FLOOR(0.01) <=
    LO(~0.0125) <= MID(0.05) <= SHIPPED(~0.175). A confined-pax median
    that rises as the factor falls (beyond a small wobble) is the flag.
    """
    ladder = [
        ("zone_narrow_svc_dir_cf_off", 0.0),
        ("zone_narrow_svc_dir_cf_floor", 0.01),
        ("zone_narrow_svc_dir_cf_lo", 0.0125),
        ("zone_narrow_svc_dir_cf_mid", 0.05),
        ("zone_narrow_svc_dir_cf_shipped", 0.175),
    ]
    lines: list[str] = []
    med_seq = [
        (arm, medians.get(arm)) for arm, _ in ladder
    ]
    present = [(a, m) for a, m in med_seq if m is not None]
    if len(present) < 3:
        return ["NONLINEAR-BREAK check skipped: <3 ladder arms measured"]
    inversions = [
        (present[i - 1], present[i])
        for i in range(1, len(present))
        if present[i][1] is not None
        and present[i - 1][1] is not None
        and present[i][1] < present[i - 1][1] - 1.0
    ]
    if inversions:
        lines.append(
            "NONLINEAR-BREAK: confined-pax median falls as the declared "
            "host factor rises — inversions: "
            + ", ".join(f"{a}={m:g} -> {b}={n:g}"
                        for (a, m), (b, n) in inversions)
            + " (flag for attribution, not failure)",
        )
    else:
        lines.append(
            "ladder monotone in the declared host factor "
            "(no NONLINEAR-BREAK)",
        )
    return lines


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
        old_deliveries, new_deliveries = [], []
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
            old_deliveries.append(float(
                (old.get("crew_window") or {}).get("service_deliveries")
                or 0))
            new_deliveries.append(float(
                (new.get("crew_window") or {}).get("service_deliveries")
                or 0))
        lines.append(
            f"{arm} vs CW-02 {block}: n={len(deltas)} paired — "
            f"during median new {_median(new_during)} vs CW-02 "
            f"{_median(old_during)}, median paired delta "
            f"{_median(deltas)}, nonzero {sum(1 for d in deltas if d != 0)}; "
            f"deliveries median new {_median(new_deliveries)} vs CW-02 "
            f"{_median(old_deliveries)} (parity is the binding comparison)",
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
        "# MEAL-SVC-02 readout",
        "",
        f"- source: `{source}`",
        f"- design: `{_DESIGN}`",
        f"- coverage: {coverage['found']}/{coverage['expected']} cells "
        f"(partial: {coverage['partial']})",
        f"- audit invariants: {len(violations)} violation(s)",
        "",
        "| theta | arm | n | takeoff | confined-pax med (takeoff) | "
        "Δpax vs base | pax during med | during med (takeoff) | "
        "before med | Δbefore med / max abs | crew share | steward "
        "share of crew | realized exempt | deliveries med | host f med | "
        "host dose med | stewards/host | svc_to_host acq | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        "---|",
    ]
    flags: list[str] = []
    medians: dict[str, float | None] = {}
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
        medians[arm] = metrics["confined_pax_median_takeoff"]
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
            f"{_fmt(metrics['crew_share_median'])} | "
            f"{_fmt(metrics['steward_share_of_crew_median'])} | "
            f"{_fmt(realized)} "
            f"| {metrics['service_deliveries_median']} | "
            f"{_fmt(metrics['host_factor_median_of_medians'])} | "
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
        if arm == "zone_narrow_svc_dir_cf_shipped":
            med = metrics["confined_pax_median_takeoff"]
            if med is not None:
                flags.append(
                    f"drift witness: cf_shipped confined-pax takeoff "
                    f"median {med:g} beside the MEAL-SVC-01 canary's "
                    f"{_MS1_CANARY_CONFINED_PAX:g} at 32b11ccf",
                )
    lines += [
        "",
        f"Passenger bound ~{_PASSENGER_BOUND:g} (F13/F14, primary); "
        f"MAGNITUDE-LANDED reads inside {_LANDED_LO:g}-{_LANDED_HI:g}, "
        f"OVER-ATTENUATED below, STILL-HIGH above {_STILL_HIGH:g}. "
        f"Record-informed band {_BAND} reported beside, not gating; "
        f"record crew share {_RECORD_CREW_SHARE}; CW-02 deliveries band "
        f"{_CW2_DELIVERIES}; MEAL-SVC-01 canary deliveries "
        f"{_MS1_CANARY_DELIVERIES:g}. UNARMED reach echoes audited "
        "before the median read.",
        "",
        "## Factor ladder (NONLINEAR-BREAK check)",
        "",
    ]
    lines += [f"- {line}" for line in _ladder_check(by_seed_row, medians)]
    lines += [
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
