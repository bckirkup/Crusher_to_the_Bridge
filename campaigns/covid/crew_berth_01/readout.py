#!/usr/bin/env python3
"""CREW-BERTH-01 readout: pool campaign cells and apply the frozen verdict grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree of block directories (``--dir``), pools the payloads through
``picard_framework.covid_boarding_screen.merge_screen``, and applies the
admissibility block the design froze before any cell ran
(docs/covid/covid_crew_berth_01_design.md):

* per arm row: the during-window crew share vs the declared target band
  (0.2, 0.4) beside the record's 0.29 and the boxed corner's ~0.73 class,
  takeoff-conditional confined-pax median vs the landed band [26,160],
  cabin/galley shares of during-window zone-class mass (the mechanism
  witness), and service_deliveries vs the landed ~162k (cadence parity);
* every audit invariant swept on every cell: the CW-02/MEAL-SVC-02 set
  carried (window echo, exempt classes/zones, index terms, delivery
  echoes, droplet split, steward-collapse structure) PLUS the
  berthing/work-cohort witnesses — mode + params echoed from the order,
  applied/restored epochs, re-deal tallies (``mixed_status_cabins`` must
  be 0 on armed cells), and the cohort split tallies;
* the drift witness: the ``mess_boxed_base`` row paired seed-for-seed
  against the CREW-MESS-01 boxed canary cells under ``--cm1-prefix``.

The verdict grammar is the design's frozen set: BERTH-CHANNEL-CLOSED /
CEILING-SHORT / OVER-CLOSED / UNMOVED / PAX-COLLATERAL / DRIFT, with
UNARMED when the witness shows a directive never fired. The grammar binds
on ``combined`` (the family ceiling); weaker arms read with the same
machinery for the decomposition.
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

_DESIGN = "picard_framework/runs/covid_crew_berth_01_design.json"
_CM1_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_crew_mess_01/"
)
# The in-design boxed corner pairs against this CREW-MESS-01 canary block.
_CM1_PAIR = {
    "mess_boxed_base": "sect_mess_boxed",
}
# CREW-MESS-01 boxed canary row at the campaign SHA (drift reference).
_CM1_BOXED_CONFINED_PAX = 28.0
_CM1_BOXED_CREW_SHARE = 0.727
_CM1_BOXED_DELIVERIES = 162184.5

_SHIPPED_EXEMPT = (
    "crew_engineering", "crew_galley", "crew_general", "crew_medical",
)
_CW2_ZONE_NARROW_N = 11
_CREW_N = 1045
_SHIPPED_DROPLET = (0.175, 0.0)  # far_field_share, settled_share

# Frozen scoring surface (design md §Scoring surface / §Verdict grammar).
_CREW_SHARE_BAND = (0.2, 0.4)
_RECORD_CREW_SHARE = 0.29
_LANDED_LO = 26.0
_LANDED_HI = 160.0
_DURING_BAND = (150.0, 350.0)
_DELIVERY_BAND = (
    _CM1_BOXED_DELIVERIES * 0.85,
    _CM1_BOXED_DELIVERIES * 1.15,
)
# An armed row counts as "moved" when its crew-share median departs the
# base row's by more than this; below it the verdict is UNMOVED.
_MOVED_EPSILON = 0.05

# The witness echo each arm must carry:
#   berth_mode / berth_params / relocated rule ("gt0" | "zero") /
#   cohort_mode / cohort_pods / cohort_agents rule ("gt0" | "zero").
_ARM_WITNESS = {
    "shipped_baseline": (None, {}, "zero", None, None, "zero"),
    "mess_boxed_base": (None, {}, "zero", None, None, "zero"),
    "berth_cohort": ("cohort", {}, "zero", None, None, "zero"),
    "berth_rezone": (
        "rezone",
        {"berth_zones": ["CC_D4_F", "CC_D4_M", "CC_D4_A"]},
        "gt0", None, None, "zero",
    ),
    "work_pods": (None, {}, "zero", "shift_split", 2, "gt0"),
    "combined": (
        "rezone",
        {"berth_zones": ["CC_D4_F", "CC_D4_M", "CC_D4_A"]},
        "gt0", "shift_split", 2, "gt0",
    ),
}
_BASE_ARM = "mess_boxed_base"
_SHIPPED_ARM = "shipped_baseline"
_CEILING_ARM = "combined"


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
            if not key.rsplit("/", 1)[-1].startswith("cell_"):
                continue
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


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _crew_share(payload: dict[str, Any]) -> float | None:
    by_role = payload.get("during_window_by_role") or {}
    crew = float(by_role.get("crew") or 0)
    passenger = float(by_role.get("passenger") or 0)
    total = crew + passenger
    return None if total <= 0 else crew / total


def _confined_pax(payload: dict[str, Any]) -> float:
    return float(
        payload.get("confined_passenger_infections_during_quarantine") or 0
    )


def _crew_window(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("crew_window") or {}


def _zone_class_share(payload: dict[str, Any], klass: str) -> float | None:
    by_zone = payload.get("during_window_by_zone_class") or {}
    total = sum(float(v or 0) for v in by_zone.values())
    if total <= 0:
        return None
    return float(by_zone.get(klass) or 0) / total


def _is_armed(arm: str) -> bool:
    return arm not in (_BASE_ARM, _SHIPPED_ARM)


def _audit_witness(
    tag: str, arm: str, cw: dict[str, Any],
) -> list[str]:
    """The berthing/cohort echoes: modes, params, and mechanism tallies."""
    violations: list[str] = []
    spec = _ARM_WITNESS.get(arm, (None, {}, "zero", None, None, "zero"))
    berth_mode, berth_params, moved_rule, cohort_mode, pods, split_rule = (
        spec
    )
    berth = cw.get("crew_berthing")
    if not isinstance(berth, dict):
        violations.append(f"{tag}: crew_berthing echo missing")
        return violations
    if berth.get("mode") != berth_mode:
        violations.append(
            f"{tag}: crew_berthing.mode {berth.get('mode')!r} "
            f"!= {berth_mode!r}",
        )
    got_params = berth.get("params") or {}
    for key, want in berth_params.items():
        if got_params.get(key) != want:
            violations.append(
                f"{tag}: crew_berthing.params.{key} "
                f"{got_params.get(key)!r} != {want!r}",
            )
    if berth_mode is not None:
        if berth.get("applied_epoch") is None:
            violations.append(f"{tag}: crew_berthing never applied")
        if berth.get("restored_epoch") is None:
            violations.append(f"{tag}: crew_berthing never restored")
        if int(berth.get("pools_redealt") or 0) <= 0:
            violations.append(f"{tag}: pools_redealt 0 on an armed cell")
        if int(berth.get("cabins_formed") or 0) <= 0:
            violations.append(f"{tag}: cabins_formed 0 on an armed cell")
        if int(berth.get("mixed_status_cabins") or 0) != 0:
            violations.append(
                f"{tag}: mixed_status_cabins "
                f"{berth.get('mixed_status_cabins')} — a cabin mixes "
                "confined and working crew (mechanism defect)",
            )
        relocated = int(berth.get("relocated_to_work_zones") or 0)
        if moved_rule == "gt0" and relocated <= 0:
            violations.append(f"{tag}: relocated_to_work_zones 0 on rezone")
        if moved_rule == "zero" and relocated != 0:
            violations.append(
                f"{tag}: relocated {relocated} on a non-rezone arm",
            )
    else:
        if int(berth.get("pools_redealt") or 0) != 0:
            violations.append(f"{tag}: berthing fired on {arm}")
    cohort = cw.get("crew_work_cohorts")
    if not isinstance(cohort, dict):
        violations.append(f"{tag}: crew_work_cohorts echo missing")
        return violations
    if cohort.get("mode") != cohort_mode:
        violations.append(
            f"{tag}: crew_work_cohorts.mode {cohort.get('mode')!r} "
            f"!= {cohort_mode!r}",
        )
    cohort_params = cohort.get("params") or {}
    if pods is not None and cohort_params.get("pods") != pods:
        violations.append(
            f"{tag}: crew_work_cohorts.params.pods "
            f"{cohort_params.get('pods')!r} != {pods!r}",
        )
    if cohort_mode is not None:
        if cohort.get("applied_epoch") is None:
            violations.append(f"{tag}: crew_work_cohorts never applied")
        if cohort.get("restored_epoch") is None:
            violations.append(f"{tag}: crew_work_cohorts never restored")
        split = int(cohort.get("agents_split") or 0)
        if split_rule == "gt0" and split <= 0:
            violations.append(f"{tag}: agents_split 0 on an armed cell")
        if int(cohort.get("work_hours_removed") or 0) <= 0:
            violations.append(f"{tag}: work_hours_removed 0 on pods")
    else:
        if int(cohort.get("agents_split") or 0) != 0:
            violations.append(f"{tag}: cohorts fired on {arm}")
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
    delivery = payload.get("delivery") or {}
    if (delivery.get("caregiver") or {}).get("mode") != "on":
        violations.append(f"{tag}: caregiver.mode")
    split = delivery.get("droplet_field_split") or {}
    far, settled = _SHIPPED_DROPLET
    far_got = split.get("far_field_share", -1)
    settled_got = split.get("settled_share", -1)
    if not math.isclose(float(far_got if far_got is not None else -1), far):
        violations.append(f"{tag}: droplet far_field_share")
    if not math.isclose(
        float(settled_got if settled_got is not None else -1), settled,
    ):
        violations.append(f"{tag}: droplet settled_share")

    cw = _crew_window(payload)
    if not cw:
        violations.append(f"{tag}: crew_window block missing")
        return violations
    snap = cw.get("at_activation") or {}
    if int(snap.get("total_crew") or -1) != _CREW_N:
        violations.append(f"{tag}: crew_window.at_activation.total_crew")
    zones = cw.get("exempt_work_zones")
    if arm == _SHIPPED_ARM:
        if zones:
            violations.append(
                f"{tag}: exempt_work_zones {zones} on shipped SOP-017",
            )
    elif not isinstance(zones, list) or len(zones) != _CW2_ZONE_NARROW_N:
        violations.append(f"{tag}: exempt_work_zones echo {zones}")

    meal = cw.get("crew_meal_service") or {}
    if arm == _SHIPPED_ARM:
        if meal.get("mode") is not None:
            violations.append(
                f"{tag}: meal-service mode {meal.get('mode')!r} "
                "on shipped SOP-017 (messes open)",
            )
    else:
        if meal.get("mode") != "boxed":
            violations.append(
                f"{tag}: crew_meal_service.mode {meal.get('mode')!r} "
                "!= 'boxed' (boxed rides every armed arm)",
            )
        if int(meal.get("diner_redirects") or 0) <= 0:
            violations.append(
                f"{tag}: diner_redirects 0 (boxed must fire)",
            )

    violations += _audit_witness(tag, arm, cw)

    deliveries = int(cw.get("service_deliveries") or 0)
    if deliveries <= 0:
        violations.append(f"{tag}: service_deliveries zero")
    if arm == _SHIPPED_ARM:
        if cw.get("service_responder_mode") != "uniform":
            violations.append(
                f"{tag}: service_responder_mode "
                f"{cw.get('service_responder_mode')!r} != 'uniform'",
            )
    else:
        if cw.get("service_responder_mode") != "section":
            violations.append(
                f"{tag}: service_responder_mode "
                f"{cw.get('service_responder_mode')!r} != 'section'",
            )
        if int(cw.get("service_section_steward_draws") or 0) <= 0:
            violations.append(f"{tag}: no section steward draws")
    return violations


def _row_metrics(
    payloads: list[dict[str, Any]], takeoff_min: int,
) -> dict[str, Any]:
    took = [p for p in payloads if _takeoff(p, takeoff_min)]
    confined = sorted(_confined_pax(p) for p in took)
    mid = len(confined) // 2
    confined_med = (
        confined[mid] if len(confined) % 2
        else (confined[mid - 1] + confined[mid]) / 2
    ) if confined else None
    shares = [s for s in (_crew_share(p) for p in payloads) if s is not None]
    cabin = [
        s for s in (
            _zone_class_share(p, "cabin") for p in payloads
        ) if s is not None
    ]
    galley = [
        s for s in (
            _zone_class_share(p, "galley") for p in payloads
        ) if s is not None
    ]
    during = [float(p.get("infections_during_window") or 0) for p in payloads]
    deliveries = [
        float(_crew_window(p).get("service_deliveries") or 0)
        for p in payloads
    ]
    return {
        "n": len(payloads),
        "takeoff_n": len(took),
        "confined_pax_median_takeoff": confined_med,
        "crew_share_median": _median(shares),
        "cabin_share_median": _median(cabin),
        "galley_share_median": _median(galley),
        "during_median": _median(during),
        "deliveries_median": _median(deliveries),
    }


def _verdict(
    arm: str,
    metrics: dict[str, Any],
    base_share: float | None,
    armed: bool,
) -> str:
    if arm == _SHIPPED_ARM:
        return "BASELINE (shipped SOP-017 corner)"
    if arm == _BASE_ARM:
        return "BASELINE (boxed corner verbatim)"
    if not armed:
        return "UNARMED (berthing/cohort echo shows no firing)"
    share = metrics["crew_share_median"]
    pax = metrics["confined_pax_median_takeoff"]
    if pax is not None and not _LANDED_LO <= pax <= _LANDED_HI:
        return (
            f"PAX-COLLATERAL (confined-pax median {pax:g} outside the "
            f"landed band {_LANDED_LO:g}-{_LANDED_HI:g}; shared-zone "
            "defect)"
        )
    if share is None:
        return "NO CELLS"
    moved = base_share is None or abs(share - base_share) > _MOVED_EPSILON
    if _CREW_SHARE_BAND[0] <= share <= _CREW_SHARE_BAND[1]:
        label = (
            "BERTH-CHANNEL-CLOSED" if arm == _CEILING_ARM
            else "IN-BAND"
        )
        return f"{label} (crew share {share:.3f} in the band)"
    if share < _CREW_SHARE_BAND[0]:
        return f"OVER-CLOSED (crew share {share:.3f} below the band)"
    if not moved:
        return (
            f"UNMOVED (crew share {share:.3f} within {_MOVED_EPSILON:g} "
            f"of base {_fmt(base_share)})"
        )
    if arm == _CEILING_ARM:
        return (
            f"CEILING-SHORT (crew share {share:.3f} > "
            f"{_CREW_SHARE_BAND[1]:g}; the family is exhausted — "
            "residual rides a channel outside berthing+occupational)"
        )
    return (
        f"STILL-HIGH (crew share {share:.3f} > {_CREW_SHARE_BAND[1]:g}; "
        "this arm alone can't reach — read against the ceiling)"
    )


def _armed_echo(payloads: list[dict[str, Any]], arm: str) -> bool:
    """Whether every cell in the row shows the mechanism fired."""
    spec = _ARM_WITNESS.get(arm, (None, {}, "zero", None, None, "zero"))
    berth_mode, _, _, cohort_mode, _, _ = spec
    for payload in payloads:
        cw = _crew_window(payload)
        berth = cw.get("crew_berthing") or {}
        cohort = cw.get("crew_work_cohorts") or {}
        if berth_mode is not None and int(
            berth.get("pools_redealt") or 0
        ) <= 0:
            return False
        if cohort_mode is not None and int(
            cohort.get("agents_split") or 0
        ) <= 0:
            return False
    return bool(payloads)


def _cm1_witness(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
    cm1_prefix: str,
) -> list[str]:
    """Pair the boxed base against the CREW-MESS-01 canary cells."""
    bucket, key_prefix = _split_s3(cm1_prefix)
    client = _s3_client()
    lines: list[str] = []
    for arm, block in sorted(_CM1_PAIR.items()):
        new_row = next(
            (seeds for (theta, a), seeds in rows.items() if a == arm),
            {},
        )
        old_share, new_share = [], []
        old_pax, new_pax = [], []
        old_del, new_del = [], []
        for seed, new in sorted(new_row.items()):
            key = f"{key_prefix}{block}/cell_{seed}.json"
            try:
                old = json.loads(client.get_object(
                    Bucket=bucket, Key=key)["Body"].read())
            except Exception:  # noqa: BLE001 - missing cell, report count
                continue
            o_s, n_s = _crew_share(old), _crew_share(new)
            if o_s is not None and n_s is not None:
                old_share.append(o_s)
                new_share.append(n_s)
            old_pax.append(_confined_pax(old))
            new_pax.append(_confined_pax(new))
            old_del.append(float(
                (old.get("crew_window") or {}).get("service_deliveries")
                or 0))
            new_del.append(float(
                _crew_window(new).get("service_deliveries") or 0))
        lines.append(
            f"{arm} vs CREW-MESS-01 {block}: n={len(old_pax)} paired — "
            f"crew share median new {_fmt(_median(new_share))} vs "
            f"{_fmt(_median(old_share))}; confined-pax median new "
            f"{_fmt(_median(new_pax))} vs {_fmt(_median(old_pax))}; "
            f"deliveries median new {_fmt(_median(new_del))} vs "
            f"{_fmt(_median(old_del))} (same arm definition — "
            "departures beyond seed-paired noise report DRIFT)",
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
    cm1_lines: list[str],
) -> str:
    by_seed_row = _rows(payloads)
    violations = [v for p in payloads.values() for v in _audit_cell(p)]
    surface = merge_screen(design, payloads, allow_partial=True)
    coverage = surface["coverage"]
    takeoff_min = design.takeoff_recorded_onsets

    lines = [
        "# CREW-BERTH-01 readout",
        "",
        f"- source: `{source}`",
        f"- design: `{_DESIGN}`",
        f"- coverage: {coverage['found']}/{coverage['expected']} cells "
        f"(partial: {coverage['partial']})",
        f"- audit invariants: {len(violations)} violation(s)",
        "",
        "| theta | arm | n | takeoff | confined-pax med (takeoff) | "
        "crew share med | cabin share med | galley share med | "
        "during med | deliveries med | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    flags: list[str] = []
    for (theta, arm), seeds in sorted(by_seed_row.items()):
        metrics = _row_metrics(list(seeds.values()), takeoff_min)
        base_row = by_seed_row.get((theta, _BASE_ARM), {})
        base_metrics = _row_metrics(list(base_row.values()), takeoff_min)
        armed = (
            _armed_echo(list(seeds.values()), arm) if _is_armed(arm)
            else True
        )
        verdict = _verdict(
            arm, metrics, base_metrics["crew_share_median"], armed,
        )
        lines.append(
            f"| {theta:g} | {arm} | {metrics['n']} | {metrics['takeoff_n']} "
            f"| {_fmt(metrics['confined_pax_median_takeoff'])} | "
            f"{_fmt(metrics['crew_share_median'])} | "
            f"{_fmt(metrics['cabin_share_median'])} | "
            f"{_fmt(metrics['galley_share_median'])} | "
            f"{_fmt(metrics['during_median'])} | "
            f"{_fmt(metrics['deliveries_median'])} | {verdict} |",
        )
        del_med = metrics["deliveries_median"]
        if (
            del_med is not None
            and not _DELIVERY_BAND[0] <= del_med <= _DELIVERY_BAND[1]
        ):
            flags.append(
                f"{arm}@{theta:g}: deliveries median {del_med:g} outside "
                f"the parity band {_DELIVERY_BAND[0]:g}-"
                f"{_DELIVERY_BAND[1]:g} (cadence defect)",
            )
    lines += [
        "",
        f"Crew-share target band {_CREW_SHARE_BAND} (record "
        f"{_RECORD_CREW_SHARE}); confined-pax guard "
        f"[{_LANDED_LO:g},{_LANDED_HI:g}] (CREW-MESS-01 boxed medians: "
        f"confined-pax {_CM1_BOXED_CONFINED_PAX:g}, crew share "
        f"{_CM1_BOXED_CREW_SHARE}); deliveries parity "
        f"{_DELIVERY_BAND[0]:g}-{_DELIVERY_BAND[1]:g} vs the boxed row's "
        f"{_CM1_BOXED_DELIVERIES:g}; during-window total reported "
        f"beside {_DURING_BAND} — not gating. UNARMED witness echoes "
        "audited before the share read. The verdict grammar binds on "
        "`combined` (the family ceiling); other arms read with the same "
        "machinery for the decomposition.",
        "",
        "## Audit-invariant violations",
        "",
    ]
    lines += [f"- {v}" for v in violations] or ["- none"]
    lines += ["", "## Report flags", ""]
    lines += [f"- {f}" for f in flags] or ["- none"]
    lines += ["", "## CREW-MESS-01 drift witness", ""]
    lines += [f"- {line}" for line in cm1_lines]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prefix", help="s3:// campaign prefix")
    group.add_argument(
        "--dir", type=Path, help="local tree of block directories",
    )
    parser.add_argument(
        "--cm1-prefix", default=_CM1_PREFIX,
        help="CREW-MESS-01 cell prefix for the drift witness; "
             "empty string skips it",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="write the readout markdown here",
    )
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
    cm1_lines = (
        _cm1_witness(_rows(payloads), args.cm1_prefix)
        if args.cm1_prefix else ["(skipped)"]
    )
    text = _render(design, payloads, source, cm1_lines)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"WROTE {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
