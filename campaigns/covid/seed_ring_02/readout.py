#!/usr/bin/env python3
"""SEED-RING-02 readout: the voyage-stage contact declaration probe.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree (``--dir``), groups cells by (theta, arm_id) and renders:

* per cell: founder yield (``seed_ring.aboard_window_acquisitions`` +
  clean bound + day-0 count + route split), ignition day (first day
  cumulative infections reach IGNITION_MASS), takeoff gate, day-15
  cumulative infections (pre-quarantine), recorded_onsets, before_share,
  and the resolved voyage-layer echo
  (``delivery.voyage.effects_enabled`` / day types / embarkation
  contact multiplier);
* per arm row: leg 1 — founder median >= 10 AND ignition median <= 9 on
  takeoff cells (early establishment); leg 2 — d15 cumulative-infections
  median <= 960 on record-timed cells (ign <= 9; the routine field does
  not over-produce);
* the campaign verdict across arms — WINDOW-LANDED / FOUNDERS-ONLY /
  SPLIT-STAGE / NULL-WINDOW per the design's frozen grammar — plus the
  committed-cells drift witness: the in-design D0 rows paired
  seed-for-seed against the committed refit ``dp_theta_8p50`` cells.

Verdicts come only from the design's frozen thresholds; this file adds no
fit and no post-hoc criterion.

Usage:
    python3 campaigns/covid/seed_ring_02/readout.py \
        --prefix s3://<bucket>/campaign/covid_seed_ring_02/ [--out-md md]
    python3 campaigns/covid/seed_ring_02/readout.py --dir <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.transmission_core import (  # noqa: E402
    DEFAULT_DROPLET_FIELD_SPLIT_FAR_SHARE,
    DEFAULT_DROPLET_FIELD_SPLIT_MODE,
    DEFAULT_DROPLET_FIELD_SPLIT_SETTLED_SHARE,
)
from picard_framework.covid_boarding_screen import (  # noqa: E402
    KEY_INDEX_ONSET_DAY,
    KEY_INDEX_SHEDDING_AT_DAY0,
    load_design,
)

_DESIGN = "picard_framework/runs/covid_seed_ring_02_design.json"
_REFIT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_theta_refit_01/"
)
_REFIT_D0_BLOCK = "dp_theta_8p50"
_BASELINE_ARM = "D0_declared"
_IGNITION_MASS = 50
_PREQUAR_DAY = 15  # quarantine opens day 16; the pre-quarantine landmark
_DEPARTURE_DAY = 5
_EPOCHS_PER_DAY = 24  # DP replay clock: 1-hour epochs
_QUAR_WINDOW = [16, 30]
_ARM_RE = re.compile(r"^WINDOW_W(?P<w>\d+)_A(?P<a>\d+)$")


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
_D15_MAX = float(_TH["d15_cum_infections_median_max"])
_RECORD_TIMED_IGN_MAX = int(_TH["ignition_day_record_timed_max"])
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


def _daily_infections(payload: dict[str, Any]) -> dict[int, int]:
    return {
        int(k): int(v)
        for k, v in (payload.get("acquisition_curve") or {})
        .get("total_by_day", {}).items()
    }


def _ignition_day(payload: dict[str, Any]) -> int | None:
    daily = _daily_infections(payload)
    cumulative = 0
    for day in sorted(daily):
        cumulative += daily[day]
        if cumulative >= _IGNITION_MASS:
            return day
    return None


def _cum_through(payload: dict[str, Any], day: int) -> int:
    return sum(
        n for d, n in _daily_infections(payload).items() if d <= day
    )


def _before_share(payload: dict[str, Any]) -> float | None:
    onsets = float(_obs(payload).get("recorded_onsets") or 0)
    if onsets <= 0:
        return None
    return (
        float(_obs(payload).get("onsets_before_split_day") or 0) / onsets
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
        and abs(before_med - _RECORD_BEFORE_SHARE) <= 0.10
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
    # Censored median: a takeoff cell that never reaches IGNITION_MASS
    # counts as +inf, so >50% non-ignition yields an infinite median
    # rather than a median over a small ignited survivor subset.
    ignitions = [
        float(d) if d is not None else float("inf")
        for d in (_ignition_day(p) for p in taken)
    ]
    all_founders = [
        float(_seed_ring(p).get("aboard_window_acquisitions") or 0)
        for p in payloads
    ]
    # Leg 2's basis: record-timed cells (ign <= the frozen landmark)
    record_timed = [
        p for p in payloads
        if (d := _ignition_day(p)) is not None
        and d <= _RECORD_TIMED_IGN_MAX
    ]
    d15 = [float(_cum_through(p, _PREQUAR_DAY)) for p in record_timed]
    route_totals: dict[str, int] = {}
    for p in payloads:
        for route, n in (
            _seed_ring(p).get("aboard_window_by_route") or {}
        ).items():
            route_totals[route] = route_totals.get(route, 0) + int(n)
    return {
        "n": len(payloads),
        "takeoff_n": len(taken),
        "ignited_n": sum(1 for d in ignitions if d != float("inf")),
        "record_timed_n": len(record_timed),
        "founder_median_takeoff": _median(founders),
        "founder_median_all": _median(all_founders),
        "ignition_day_median_takeoff": _median(ignitions),
        "d15_median_record_timed": _median(d15),
        "route_totals": route_totals,
        "trajectory": _trajectory_clause(payloads),
    }


def _arm_verdicts(
    rows: dict[tuple[float, str], dict[int, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Leg 1 + leg 2 per arm; the campaign verdict across arms."""
    out: dict[str, dict[str, Any]] = {}
    for (_theta, arm), seeds in sorted(rows.items()):
        metrics = _row_metrics(list(seeds.values()))
        if arm == _BASELINE_ARM:
            out[arm] = {"metrics": metrics, "verdict": "BASELINE (drift witness)"}
            continue
        if metrics["takeoff_n"] < _MIN_TAKEOFF:
            out[arm] = {"metrics": metrics,
                        "verdict": "INSUFFICIENT-TAKEOFF-MASS"}
            continue
        leg1 = (
            (metrics["founder_median_takeoff"] or 0.0) >= _FOUNDER_MIN
            and (metrics["ignition_day_median_takeoff"] or float("inf"))
            <= _IGN_MAX
        )
        leg2 = (
            metrics["record_timed_n"] > 0
            and (metrics["d15_median_record_timed"] or float("inf"))
            <= _D15_MAX
        )
        out[arm] = {"metrics": metrics, "leg1": leg1, "leg2": leg2,
                    "verdict": f"leg1 {'pass' if leg1 else 'fail'} / "
                               f"leg2 {'pass' if leg2 else 'fail'}"}
    return out


def _campaign_verdict(
    verdicts: dict[str, dict[str, Any]],
) -> str:
    window = {
        arm: v for arm, v in verdicts.items()
        if _ARM_RE.match(arm) and "leg1" in v
    }
    if not window:
        return "UNREAD — no window arm scored"
    landed = [a for a, v in window.items() if v["leg1"] and v["leg2"]]
    if landed:
        return f"WINDOW-LANDED on {sorted(landed)}"
    leg1_any = any(v["leg1"] for v in window.values())
    leg2_any = any(v["leg2"] for v in window.values())
    if leg1_any and leg2_any:
        return (
            "SPLIT-STAGE — legs land at different alpha and no arm lands "
            "both; read as FOUNDERS-ONLY (the routine field is the "
            "residual)"
        )
    if leg1_any and not leg2_any:
        return (
            "FOUNDERS-ONLY — the window lands establishment but the "
            "routine field over-produces; next seam is the routine stage "
            "(Pung mapping + activity_contacts), not theta"
        )
    a8 = [
        a for a, v in window.items()
        if _ARM_RE.match(a) and _ARM_RE.match(a).group("a") == "8"
    ]
    if a8:
        return (
            "NULL-WINDOW — leg 1 fails at alpha=8; the founder channel "
            "is narrower than voyage-stage mixing (Arm-B continuation)"
        )
    return "UNREAD — leg 1 untested at the band top"


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
        delivery = payload.get("delivery") or {}
        voyage = delivery.get("voyage") or {}
        spec = sr.get("seed_spec") or {}
        match = _ARM_RE.match(arm)
        if match:
            want_days = {
                str(d): "embarkation"
                for d in range(1, int(match.group("w")) + 1)
            }
            got_days = voyage.get("itinerary_day_types") or {}
            if voyage.get("effects_enabled") is not True:
                violations.append(
                    f"{tag}: delivery.voyage.effects_enabled "
                    f"{voyage.get('effects_enabled')!r} != true — the "
                    "stage declaration never reached the cell",
                )
            if got_days != want_days:
                violations.append(
                    f"{tag}: voyage itinerary day types {got_days} != "
                    f"declared {want_days}",
                )
            want_a = float(match.group("a"))
            got_a = voyage.get("embarkation_contact_rate_multiplier")
            if got_a != want_a:
                violations.append(
                    f"{tag}: embarkation contact_rate_multiplier "
                    f"{got_a!r} != declared {want_a:g}",
                )
        elif arm == _BASELINE_ARM:
            if voyage.get("effects_enabled") is not False:
                violations.append(
                    f"{tag}: voyage effects_enabled "
                    f"{voyage.get('effects_enabled')!r} on the baseline "
                    "arm — the declaration leaked off its arm",
                )
        if "placement" in spec:
            violations.append(
                f"{tag}: placement echo present — no arm in this design "
                "declares a seed placement",
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
        _audit_replay_echoes(payload, tag, violations)
    return violations, flags


def _audit_replay_echoes(
    payload: dict[str, Any], tag: str, violations: list[str],
) -> None:
    """The frozen replay echo invariants (design audit_invariants): seed
    geometry, quarantine witness, propensity/delivery."""
    departed = payload.get("index_departed_epoch")
    if (
        departed is None
        or int(departed) // _EPOCHS_PER_DAY != _DEPARTURE_DAY
    ):
        violations.append(
            f"{tag}: index_departed_epoch {departed} is not a day-"
            f"{_DEPARTURE_DAY} departure",
        )
    witness = payload.get("quarantine_witness") or {}
    if (
        witness.get("window_days") != _QUAR_WINDOW
        or witness.get("activated") is not True
    ):
        violations.append(
            f"{tag}: quarantine_witness window "
            f"{witness.get('window_days')} activated "
            f"{witness.get('activated')} != {_QUAR_WINDOW} true",
        )
    propensity = payload.get("propensity_draw") or {}
    if int(propensity.get("units_drawn") or 0) <= 0:
        violations.append(
            f"{tag}: propensity_draw.units_drawn "
            f"{propensity.get('units_drawn')} <= 0",
        )
    delivery = payload.get("delivery") or {}
    expected = {
        "presentation_draw_mode": "once_per_course",
        "hand_reservoir_mode": "hygiene_cycle",
    }
    for field, want in expected.items():
        if delivery.get(field) != want:
            violations.append(
                f"{tag}: delivery.{field} "
                f"{delivery.get(field)!r} != {want!r}",
            )
    if (delivery.get("caregiver") or {}).get("mode") != "on":
        violations.append(
            f"{tag}: delivery.caregiver.mode "
            f"{(delivery.get('caregiver') or {}).get('mode')!r} != 'on'",
        )
    split = delivery.get("droplet_field_split") or {}
    if (
        split.get("mode") != DEFAULT_DROPLET_FIELD_SPLIT_MODE
        or split.get("far_field_share")
        != DEFAULT_DROPLET_FIELD_SPLIT_FAR_SHARE
        or split.get("settled_share")
        != DEFAULT_DROPLET_FIELD_SPLIT_SETTLED_SHARE
        or split.get("declared") != {}
        or not split.get("active")
    ):
        violations.append(
            f"{tag}: delivery.droplet_field_split "
            f"{json.dumps(split, sort_keys=True)} is not the shipped "
            "partition",
        )


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
        if paired < len(new_row):
            verdict = (
                "DRIFT WITNESS UNVERIFIED — "
                f"paired {paired}/{len(new_row)} D0 cells; do not "
                "trust the baseline read"
            )
        elif nonzero:
            verdict = "DRIFT: attribute before trusting the window read"
        else:
            verdict = "DRIFT WITNESS CLEAN"
        lines.append(
            f"Theta {theta:g}: n={paired} paired vs committed "
            f"dp_theta_8p50 — recorded_onsets paired deltas nonzero on "
            f"{nonzero}/{paired} seeds, median delta "
            f"{_fmt(_median(deltas))} — {verdict}",
        )
    return lines


def _per_cell_lines(seeds: dict[int, dict[str, Any]]) -> list[str]:
    """One evidence row per cell: the founder-vs-timing-vs-mass diagnostic."""
    lines = [
        "| seed | founders | clean | d0 | routes | ign | takeoff | "
        "d15 | onsets | before_share | voyage |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for seed, payload in sorted(seeds.items()):
        sr = _seed_ring(payload)
        routes = ",".join(
            f"{k}:{v}"
            for k, v in (sr.get("aboard_window_by_route") or {}).items()
        ) or "-"
        ign = _ignition_day(payload)
        voyage = (payload.get("delivery") or {}).get("voyage") or {}
        voyage_tag = (
            f"eff:{voyage.get('effects_enabled')} "
            f"a:{voyage.get('embarkation_contact_rate_multiplier')}"
        )
        lines.append(
            f"| {seed} "
            f"| {sr.get('aboard_window_acquisitions')!r} "
            f"| {sr.get('aboard_window_clean_bound')!r} "
            f"| {(sr.get('aboard_window_by_day') or {}).get('0', 0)} "
            f"| {routes} "
            f"| {ign if ign is not None else '-'} "
            f"| {'yes' if _takeoff(payload) else 'no'} "
            f"| {_cum_through(payload, _PREQUAR_DAY)} "
            f"| {_obs(payload).get('recorded_onsets')!r} "
            f"| {_fmt(_before_share(payload))} "
            f"| {voyage_tag} |",
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
    verdicts = _arm_verdicts(rows)
    campaign = _campaign_verdict(verdicts)
    lines = [
        f"# {design.design_id} readout — {source}",
        "",
        f"## Campaign verdict: **{campaign}**",
        "",
        "## Arm legs",
        "",
    ]
    for (theta, arm), seeds in sorted(rows.items()):
        entry = verdicts[arm]
        metrics = entry["metrics"]
        traj = metrics["trajectory"]
        lines.append(
            f"- {arm}@{theta:g}: **{entry['verdict']}** — n={metrics['n']} "
            f"(takeoff {metrics['takeoff_n']}); founder median "
            f"{_fmt(metrics['founder_median_takeoff'])} takeoff-conditional "
            f"({_fmt(metrics['founder_median_all'])} all cells); ignition "
            f"median {_fmt(metrics['ignition_day_median_takeoff'])} "
            f"(ignited {metrics['ignited_n']}/{metrics['takeoff_n']}); "
            f"record-timed {metrics['record_timed_n']} cells, d15 median "
            f"{_fmt(metrics['d15_median_record_timed'])} vs <= {_D15_MAX:g}; "
            f"routes {metrics['route_totals']}",
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
            "", f"### {arm}@{theta:g} — per-cell", "",
            *_per_cell_lines(seeds), "",
        ]
    lines += [
        "",
        f"Frozen legs: leg 1 founder median >= {_FOUNDER_MIN:g} AND "
        f"ignition median <= {_IGN_MAX:g} (takeoff cells); leg 2 d15 "
        f"cumulative infections median <= {_D15_MAX:g} on record-timed "
        f"cells (ign <= {_RECORD_TIMED_IGN_MAX}). Min takeoff "
        f"{_MIN_TAKEOFF} cells. Grammar: WINDOW-LANDED / FOUNDERS-ONLY / "
        "SPLIT-STAGE / NULL-WINDOW.",
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
