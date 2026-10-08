#!/usr/bin/env python3
"""ONSET-REC-01 readout: pool campaign cells and apply the frozen verdict grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree (``--dir``) and scores the design's declared primary:
dated share of lab_confirmed (recorded_onsets / lab_confirmed_total),
pooled and per-cell median, vs the record's 0.277 with the declared
expectation band [0.43, 0.55] and the verdict grammar RECORD-MATCHED /
CHANNEL-INSUFFICIENT / OVER-CLOSED. Secondaries reported beside, never
thresholded: lab_confirmed_total vs 712, crew share of lab_confirmed
(pooled + DP-scale conditioned, n_confirmed >= 100), confined-pax
takeoff median vs [26,160], deliveries parity vs ~162k.

The audit sweep checks the channel echo (null on boxed_declared, the
declared block on boxed_period), the MESSBOX base echo, the boxed meal
witness, index geometry, droplet split and delivery cadence. With
``--parent-prefix`` the boxed_declared cells are paired seed-for-seed
against the landed sect_mess_boxed cells for the bit-identity witness
(voyage event counts must match).
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

_DESIGN = "picard_framework/runs/covid_onset_rec_01_design.json"
_PARENT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_crew_mess_01/sect_mess_boxed/"
)

_RECORD_DATED_SHARE = 0.277
_RECORD_BAND = (0.227, 0.327)
_EXPECTED_BAND = (0.43, 0.55)
_CONFINED_PAX_BAND = (26.0, 160.0)
_DELIVERY_REF = 162447.0
_DELIVERY_BAND = (_DELIVERY_REF * 0.85, _DELIVERY_REF * 1.15)
_DP_SCALE_MIN = 100
_DECLARED_CHANNEL = {
    "symptomatic_at_confirmation_required": True,
    "report_probability": 0.56,
}
_SHIPPED_EXEMPT = (
    "crew_engineering", "crew_galley", "crew_general", "crew_medical",
)
_SHIPPED_DROPLET = (0.175, 0.0)

# Voyage-derived fields the bit-identity clause compares per seed.
_IDENTITY_FIELDS = (
    "infections_total",
    "aboard_total",
    "lab_confirmed_total",
    "infections_during_window",
    "confined_passenger_infections_during_quarantine",
)


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("boto3 is required for --prefix") from exc
    return boto3.client("s3")


def _split_s3(uri: str) -> tuple[str, str]:
    assert uri.startswith("s3://"), f"need s3:// uri, got {uri!r}"
    bucket, _, prefix = uri[5:].partition("/")
    return bucket, prefix.rstrip("/") + "/"


def _iter_s3_payloads(prefix: str) -> Iterable[tuple[str, dict[str, Any]]]:
    bucket, key_prefix = _split_s3(prefix)
    client = _s3_client()
    for page in client.get_paginator("list_objects_v2").paginate(
        Bucket=bucket, Prefix=key_prefix,
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json") or not key.rsplit("/", 1)[
                -1
            ].startswith("cell_"):
                continue
            body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            yield key, json.loads(body)


def _iter_local_payloads(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    for path in sorted(root.rglob("cell_*.json")):
        yield str(path), json.loads(path.read_text(encoding="utf-8"))


def _obs(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("observables") or {}


def _recorded(payload: dict[str, Any]) -> float:
    return float(_obs(payload).get("recorded_onsets") or 0)


def _confirmed(payload: dict[str, Any]) -> float:
    return float(payload.get("lab_confirmed_total") or 0)


def _dated_share(payload: dict[str, Any]) -> float | None:
    conf = _confirmed(payload)
    return None if conf <= 0 else _recorded(payload) / conf


def _crew_share(payload: dict[str, Any]) -> float | None:
    curve = payload.get("onset_curve") or {}
    crew = pax = 0.0
    for roles in curve.values():
        crew += float((roles or {}).get("crew") or 0)
        pax += float((roles or {}).get("passenger") or 0)
    total = crew + pax
    return None if total <= 0 else crew / total


def _lab_confirmed_crew_share(payload: dict[str, Any]) -> float | None:
    """Crew share of lab confirmations, from the payload role echo."""
    roles = payload.get("lab_confirmed_by_role") or {}
    crew = float(roles.get("crew") or 0)
    total = crew + float(roles.get("passenger") or 0)
    return None if total <= 0 else crew / total


def _symptomatic_at_specimen(payload: dict[str, Any]) -> float | None:
    """Share of campaign positives symptomatic at specimen (the gate)."""
    obs = _obs(payload)
    pos = float(obs.get("campaign_positives") or 0)
    if pos <= 0:
        return None
    asymp = float(obs.get("campaign_asymptomatic_positives") or 0)
    return (pos - asymp) / pos


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return float(
        ordered[mid] if len(ordered) % 2
        else (ordered[mid - 1] + ordered[mid]) / 2
    )


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _confined_pax(payload: dict[str, Any]) -> float:
    return float(
        payload.get("confined_passenger_infections_during_quarantine") or 0
    )


def _takeoff(payload: dict[str, Any], threshold: int) -> bool:
    return _recorded(payload) >= threshold


def _audit_cell(payload: dict[str, Any]) -> list[str]:
    """The frozen audit invariants, swept on one cell payload."""
    violations: list[str] = []
    cell = payload.get("cell") or {}
    arm = str(cell.get("arm_id"))
    tag = f"{arm}@{cell.get('theta'):g}s{cell.get('seed')}"

    witness = payload.get("quarantine_witness") or {}
    if witness.get("protocol_id") != "SOP-017-MESSBOX":
        violations.append(
            f"{tag}: protocol_id {witness.get('protocol_id')!r} "
            "!= 'SOP-017-MESSBOX' (base_overrides did not resolve)",
        )
    if witness.get("window_days") != [16, 30] or not witness.get(
        "activated"
    ):
        violations.append(f"{tag}: quarantine_witness window/activation")
    if tuple(sorted(witness.get("exempt_classes") or ())) != _SHIPPED_EXEMPT:
        violations.append(f"{tag}: exempt_classes echo")

    cw = payload.get("crew_window") or {}
    meal = cw.get("crew_meal_service") or {}
    if meal.get("mode") != "boxed":
        violations.append(f"{tag}: crew_meal_service.mode not 'boxed'")
    if int(meal.get("diner_redirects") or 0) <= 0:
        violations.append(f"{tag}: diner_redirects 0 on a boxed cell")

    echo = payload.get("onset_recording")
    if arm == "boxed_declared":
        if echo is not None:
            violations.append(
                f"{tag}: onset_recording echo {echo!r} on the declared arm",
            )
    elif arm == "boxed_period":
        if echo != _DECLARED_CHANNEL:
            violations.append(
                f"{tag}: onset_recording echo {echo!r} "
                f"!= {_DECLARED_CHANNEL!r}",
            )
    if payload.get("lab_confirmed_total") is None:
        violations.append(f"{tag}: lab_confirmed_total missing")

    if payload.get("index_onset_day") != -1.0:
        violations.append(f"{tag}: index_onset_day")
    if payload.get("index_shedding_at_day0") is not True:
        violations.append(f"{tag}: index_shedding_at_day0")
    delivery = payload.get("delivery") or {}
    if (delivery.get("caregiver") or {}).get("mode") != "on":
        violations.append(f"{tag}: caregiver.mode")
    split = delivery.get("droplet_field_split") or {}
    far, settled = _SHIPPED_DROPLET
    far_val = split.get("far_field_share")
    if far_val is None or not math.isclose(float(far_val), far):
        violations.append(f"{tag}: droplet far_field_share")
    settled_val = split.get("settled_share")
    if settled_val is None or not math.isclose(
        float(settled_val), settled,
    ):
        violations.append(f"{tag}: droplet settled_share")
    deliveries = int(cw.get("service_deliveries") or 0)
    if deliveries <= 0:
        violations.append(f"{tag}: service_deliveries zero")
    return violations


def _verdict(arm: str, pooled_share: float | None) -> str:
    if arm == "boxed_declared":
        return "BASELINE (bit-identity control)"
    if pooled_share is None:
        return "NO CELLS"
    if _RECORD_BAND[0] <= pooled_share <= _RECORD_BAND[1]:
        return (
            f"RECORD-MATCHED (dated share {pooled_share:.3f} inside "
            f"{_RECORD_BAND})"
        )
    if pooled_share < _RECORD_BAND[0]:
        return (
            f"OVER-CLOSED (dated share {pooled_share:.3f} below "
            f"{_RECORD_BAND[0]:g})"
        )
    return (
        f"CHANNEL-INSUFFICIENT (dated share {pooled_share:.3f} > "
        f"{_RECORD_BAND[1]:g}; expected band {_EXPECTED_BAND})"
    )


def _row_metrics(payloads: list[dict[str, Any]], takeoff_min: int) -> dict:
    took = [p for p in payloads if _takeoff(p, takeoff_min)]
    shares = [s for s in (_dated_share(p) for p in payloads) if s is not None]
    conf = [_confirmed(p) for p in payloads]
    pooled_conf = sum(conf)
    pooled_rec = sum(_recorded(p) for p in payloads)
    pooled_share = pooled_rec / pooled_conf if pooled_conf else None
    rec_shares = [
        s for s in (_lab_confirmed_crew_share(p) for p in payloads)
        if s is not None
    ]
    crew = sum(
        float((p.get("lab_confirmed_by_role") or {}).get("crew") or 0)
        for p in payloads
    )
    pax = sum(
        float((p.get("lab_confirmed_by_role") or {}).get("passenger") or 0)
        for p in payloads
    )
    pooled_crew_share = crew / (crew + pax) if crew + pax else None
    dp_cells = [p for p in payloads if _confirmed(p) >= _DP_SCALE_MIN]
    dp_crew = sum(
        float((p.get("lab_confirmed_by_role") or {}).get("crew") or 0)
        for p in dp_cells
    )
    dp_pax = sum(
        float((p.get("lab_confirmed_by_role") or {}).get("passenger") or 0)
        for p in dp_cells
    )
    dp_pooled_crew_share = (
        dp_crew / (dp_crew + dp_pax) if dp_crew + dp_pax else None
    )
    symp = [
        s for s in (_symptomatic_at_specimen(p) for p in payloads)
        if s is not None
    ]
    confined = [_confined_pax(p) for p in took]
    deliveries = [
        float((p.get("crew_window") or {}).get("service_deliveries") or 0)
        for p in payloads
    ]
    return {
        "n": len(payloads),
        "takeoff_n": len(took),
        "pooled_conf": pooled_conf,
        "pooled_rec": pooled_rec,
        "pooled_dated_share": pooled_share,
        "dated_share_median": _median(shares),
        "lab_confirmed_median": _median(conf),
        "lab_confirmed_crew_share_median": _median(rec_shares),
        "lab_confirmed_crew_share_pooled": pooled_crew_share,
        "dp_scale_n": len(dp_cells),
        "dp_scale_crew_share_pooled": dp_pooled_crew_share,
        "confined_pax_median_takeoff": _median(confined),
        "deliveries_median": _median(deliveries),
        "symptomatic_at_specimen_median": _median(symp),
    }


def _rows(
    payloads: dict[str, dict[str, Any]],
) -> dict[str, dict[int, dict[str, Any]]]:
    rows: dict[str, dict[int, dict[str, Any]]] = {}
    for payload in payloads.values():
        cell = payload["cell"]
        rows.setdefault(str(cell["arm_id"]), {})[int(cell["seed"])] = payload
    return rows


def _identity_witness(
    rows: dict[str, dict[int, dict[str, Any]]], parent_prefix: str,
) -> list[str]:
    """Pair boxed_declared cells vs landed sect_mess_boxed cells."""
    bucket, key_prefix = _split_s3(parent_prefix)
    client = _s3_client()
    lines: list[str] = []
    for seed, new in sorted(rows.get("boxed_declared", {}).items()):
        key = f"{key_prefix}cell_{seed}.json"
        try:
            old = json.loads(client.get_object(
                Bucket=bucket, Key=key)["Body"].read())
        except Exception as exc:  # noqa: BLE001
            lines.append(f"seed {seed}: parent cell unreadable ({exc})")
            continue
        diffs = [
            f"{f}={old.get(f)!r}->{new.get(f)!r}"
            for f in _IDENTITY_FIELDS
            if old.get(f) != new.get(f)
        ]
        rec_old = _recorded(old)
        rec_new = _recorded(new)
        del_old = (old.get("crew_window") or {}).get("service_deliveries")
        del_new = (new.get("crew_window") or {}).get("service_deliveries")
        if rec_old != rec_new:
            diffs.append(f"recorded_onsets={rec_old!r}->{rec_new!r}")
        if del_old != del_new:
            diffs.append(f"service_deliveries={del_old!r}->{del_new!r}")
        lines.append(
            f"seed {seed}: {'IDENTICAL' if not diffs else 'DIFFERS: ' + '; '.join(diffs)}"
        )
    return lines


def _render(
    design: Any, payloads: dict[str, dict[str, Any]], source: str,
    identity_lines: list[str],
) -> str:
    rows = _rows(payloads)
    violations = [v for p in payloads.values() for v in _audit_cell(p)]
    expected = len(enumerate_cells(design))
    found = len(payloads)
    takeoff_min = design.takeoff_recorded_onsets

    lines = [
        "# ONSET-REC-01 readout",
        "",
        f"- source: `{source}`",
        f"- design: `{_DESIGN}`",
        f"- coverage: {found}/{expected} cells "
        f"(partial: {found < expected})",
        f"- audit invariants: {len(violations)} violation(s)",
        "",
        "| arm | n | takeoff | lab_conf med | pooled conf | pooled rec | "
        "dated share (pooled / med) | lab_conf crew share (pooled / "
        "DP-scale pooled) | symp@specimen med | confined-pax med | "
        "deliveries med | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm in sorted(rows):
        m = _row_metrics(list(rows[arm].values()), takeoff_min)
        verdict = _verdict(arm, m["pooled_dated_share"])
        lines.append(
            f"| {arm} | {m['n']} | {m['takeoff_n']} | "
            f"{_fmt(m['lab_confirmed_median'])} | {m['pooled_conf']:g} | "
            f"{m['pooled_rec']:g} | {_fmt(m['pooled_dated_share'])} / "
            f"{_fmt(m['dated_share_median'])} | "
            f"{_fmt(m['lab_confirmed_crew_share_pooled'])} / "
            f"{_fmt(m['dp_scale_crew_share_pooled'])} "
            f"(n={m['dp_scale_n']}) | "
            f"{_fmt(m['symptomatic_at_specimen_median'])} | "
            f"{_fmt(m['confined_pax_median_takeoff'])} | "
            f"{_fmt(m['deliveries_median'])} | {verdict} |",
        )
    lines += [
        "",
        f"Record dated share {_RECORD_DATED_SHARE} (197/712); record band "
        f"{_RECORD_BAND}; declared expectation band {_EXPECTED_BAND}; "
        f"confined-pax guard {_CONFINED_PAX_BAND}; deliveries parity "
        f"{_DELIVERY_BAND[0]:g}-{_DELIVERY_BAND[1]:g}; DP-scale "
        f"conditioning n_confirmed >= {_DP_SCALE_MIN}.",
        "",
        "## Audit-invariant violations",
        "",
    ]
    lines += [f"- {v}" for v in violations] or ["- none"]
    lines += ["", "## Bit-identity witness (boxed_declared vs landed "
              "sect_mess_boxed)", ""]
    lines += [f"- {line}" for line in identity_lines] or ["- not run"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prefix", help="s3:// campaign prefix")
    group.add_argument("--dir", help="local cell tree")
    parser.add_argument("--parent-prefix", default=None,
                        help="s3:// prefix of the parent's landed "
                             "sect_mess_boxed cells for the bit-identity "
                             "witness")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    if args.prefix:
        source = args.prefix
        payloads = {
            key: payload
            for key, payload in _iter_s3_payloads(args.prefix)
        }
    else:
        source = str(args.dir)
        payloads = {
            key: payload
            for key, payload in _iter_local_payloads(Path(args.dir))
        }

    design = load_design(str(_REPO_ROOT / _DESIGN))
    identity_lines: list[str] = []
    if args.parent_prefix:
        identity_lines = _identity_witness(
            _rows(payloads), args.parent_prefix,
        )
    text = _render(design, payloads, source, identity_lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
