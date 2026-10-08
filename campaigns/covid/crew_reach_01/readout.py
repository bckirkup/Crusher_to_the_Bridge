#!/usr/bin/env python3
"""CREW-REACH-01 readout: pool campaign cells and apply the frozen grammar.

Reads every ``cell_*.json`` under the campaign prefix (``--prefix s3://``)
or a local tree (``--dir``) and scores the design's declared primaries:
pooled lab_confirmed per arm vs the boxed_declared baseline, crew share
of lab_confirmed pooled and DP-scale-conditioned (the honesty test),
asymptomatic-at-specimen share of confirmed vs ~0.49 (bound ~0.4), and
the shipped-channel dated share direction. The audit sweep checks the
specimen_channel witness echoes and the MESSBOX base; ``--parent-prefix``
pairs boxed_declared cells against the landed sect_mess_boxed cells on
the through-day-31 slice (bit-identity clause).
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

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)

_DESIGN = "picard_framework/runs/covid_crew_reach_01_design.json"
_PARENT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_crew_mess_01/sect_mess_boxed/"
)

_RECORD_CONFIRMED = 712
_RECORD_CREW_SHARE = 0.29
_RECORD_ASYM_SHARE = 0.49
_ASYM_HONEST_BOUND = 0.40
_CONFINED_PAX_BAND = (26.0, 160.0)
_DELIVERY_REF = 162447.0
_DELIVERY_BAND = (_DELIVERY_REF * 0.85, _DELIVERY_REF * 1.15)
_DP_SCALE_MIN = 100
_CREW_SHARE_HOT = 0.5
_IDENTITY_FIELDS = (
    "infections_total",
    "aboard_total",
    "infections_during_window",
    "confined_passenger_infections_during_quarantine",
)
_EXPECTED = {
    "boxed_declared": {"sweep": False, "waves": []},
    "boxed_s1": {"sweep": True, "waves": []},
    "boxed_s2": {"sweep": False, "waves": ["crew_wave"]},
    "boxed_s1s2": {"sweep": True, "waves": ["crew_wave"]},
}


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("boto3 is required for --prefix") from exc
    return boto3.client("s3")


def _split_s3(uri: str) -> tuple[str, str]:
    assert uri.startswith("s3://"), f"need s3:// uri, got {uri!r}"
    bucket, _, key = uri[5:].partition("/")
    return bucket, key


def _iter_s3_payloads(prefix: str) -> Iterable[tuple[str, dict[str, Any]]]:
    bucket, key_prefix = _split_s3(prefix)
    client = _s3_client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("cell_*.json".replace("*", "")) or (
                "cell_" in key and key.endswith(".json")
            ):
                body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
                yield key, json.loads(body)


def _iter_local_payloads(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    for path in sorted(root.rglob("cell_*.json")):
        yield str(path), json.loads(path.read_text(encoding="utf-8"))


def _confirmed(payload: dict[str, Any]) -> int:
    return int(payload.get("lab_confirmed_total") or 0)


def _crew_share(payload: dict[str, Any]) -> float | None:
    counts = payload.get("lab_confirmed_by_role") or {}
    total = sum(int(v) for v in counts.values())
    if not total:
        return None
    return int(counts.get("crew") or 0) / total


def _asym_share(payload: dict[str, Any]) -> tuple[int, int]:
    """Confirmed hosts whose presented onset postdates (or never reaches) the
    confirming specimen — funnel_hosts carrying the ASYM-CONF-01 metric."""
    hosts = (payload.get("funnel_hosts") or {}).values()
    confirmed = [h for h in hosts if h.get("confirmed_day") is not None]
    asym = [
        h for h in confirmed
        if h.get("presented_day") is None
        or int(h["presented_day"]) > int(h["confirmed_day"])
    ]
    return len(asym), len(confirmed)


def _dated_share(payload: dict[str, Any]) -> float | None:
    confirmed = _confirmed(payload)
    if not confirmed:
        return None
    obs = payload.get("observables") or {}
    recorded = float(obs.get("recorded_onsets") or payload.get("recorded_onsets") or 0)
    return recorded / confirmed


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _fmt(value: float | None, nd: int = 3) -> str:
    return "—" if value is None else f"{value:.{nd}f}"


def _audit_cell(payload: dict[str, Any]) -> list[str]:
    """Invariant violations on one cell; empty list is clean."""
    problems: list[str] = []
    arm = (payload.get("cell") or {}).get("arm_id")
    expected = _EXPECTED.get(arm)
    channel = payload.get("specimen_channel") or {}
    if expected is None:
        problems.append(f"unknown arm {arm!r}")
        return problems
    if bool(channel.get("retest_negatives_on_sweep")) != expected["sweep"]:
        problems.append("retest_negatives_on_sweep echo mismatches arm")
    if list(channel.get("campaign_waves") or []) != expected["waves"]:
        problems.append("campaign_waves echo mismatches arm")
    if not expected["sweep"] and int(
        channel.get("campaign_specimen_retests") or 0
    ):
        problems.append("retests on an unarmed arm — specimen-bar breach")
    wave_spec = (channel.get("campaign_specimens_by_wave") or {})
    if not expected["waves"] and wave_spec:
        problems.append("wave specimens on an unarmed arm")
    witness = payload.get("quarantine_witness") or {}
    if str(witness.get("protocol_id")) != "SOP-017-MESSBOX":
        problems.append("base_overrides did not resolve (protocol_id)")
    if payload.get("lab_confirmed_total") is None:
        problems.append("lab_confirmed_total missing")
    if "funnel_hosts" not in payload or "campaign_specimen_log" not in payload:
        problems.append("funnel echo missing")
    return problems


def _arm_rows(
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    total = sum(_confirmed(p) for p in payloads)
    crews = [c for c in (_crew_share(p) for p in payloads) if c is not None]
    dp_cells = [p for p in payloads if _confirmed(p) >= _DP_SCALE_MIN]
    dp_shares = [
        c for c in (_crew_share(p) for p in dp_cells) if c is not None
    ]
    pooled_crew = sum(
        int((p.get("lab_confirmed_by_role") or {}).get("crew") or 0)
        for p in payloads
    )
    pooled_share = pooled_crew / total if total else None
    dp_pooled_crew = sum(
        int((p.get("lab_confirmed_by_role") or {}).get("crew") or 0)
        for p in dp_cells
    )
    dp_total = sum(_confirmed(p) for p in dp_cells)
    asym_n = sum(_asym_share(p)[0] for p in payloads)
    conf_n = sum(_asym_share(p)[1] for p in payloads)
    dated = [d for d in (_dated_share(p) for p in payloads) if d is not None]
    retests = sum(
        int((p.get("specimen_channel") or {}).get(
            "campaign_specimen_retests") or 0)
        for p in payloads
    )
    retest_confirmed = sum(
        int((p.get("specimen_channel") or {}).get(
            "campaign_confirmed_retests") or 0)
        for p in payloads
    )
    wave_spec = sum(
        int(((p.get("specimen_channel") or {}).get(
            "campaign_specimens_by_wave") or {}).get("crew_wave") or 0)
        for p in payloads
    )
    wave_conf = sum(
        int(((p.get("specimen_channel") or {}).get(
            "campaign_confirmed_by_wave") or {}).get("crew_wave") or 0)
        for p in payloads
    )
    deliveries = [
        float((p.get("attribution") or {}).get("service_deliveries")
              or p.get("service_deliveries") or 0)
        for p in payloads
    ]
    return {
        "n_cells": len(payloads),
        "lab_confirmed_pooled": total,
        "lab_confirmed_median": _median(
            [float(_confirmed(p)) for p in payloads],
        ),
        "dp_scale_cells": [int((p.get("cell") or {}).get("seed") or 0)
                           for p in dp_cells],
        "crew_share_pooled": pooled_share,
        "crew_share_dp_scale": (
            dp_pooled_crew / dp_total if dp_total else None
        ),
        "crew_share_dp_cells_median": _median(dp_shares),
        "crew_share_median": _median(crews),
        "asym_share_pooled": (asym_n / conf_n if conf_n else None),
        "dated_share_pooled": (
            sum(_dated_share(p) or 0 for p in payloads) / len(payloads)
            if payloads else None
        ),
        "dated_share_median": _median(dated),
        "retest_specimens": retests,
        "retest_confirmed": retest_confirmed,
        "wave_specimens": wave_spec,
        "wave_confirmed": wave_conf,
        "deliveries_median": _median(deliveries),
    }


def _verdict(base: dict[str, Any], arm_id: str, row: dict[str, Any]) -> str:
    delta = row["lab_confirmed_pooled"] - base["lab_confirmed_pooled"]
    dp_share = row["crew_share_dp_scale"]
    if arm_id in ("boxed_s2", "boxed_s1s2") and (
        dp_share is not None and dp_share > _CREW_SHARE_HOT
    ):
        return "HONESTY-POSITIVE (crew genuinely hot — report immediately)"
    if delta >= 50:
        return "MOVES-TOWARD-RECORD"
    if delta < 50 and arm_id != "boxed_declared":
        return "NO-MOVE"
    return "BASELINE" if arm_id == "boxed_declared" else "MOVES-TOWARD-RECORD"


def _render(
    rows: dict[str, dict[str, Any]],
    problems: dict[str, list[str]],
    identity: list[str],
) -> str:
    base = rows.get("boxed_declared") or {}
    lines = [
        "# CREW-REACH-01 canary readout",
        "",
        f"Record: lab_confirmed {_RECORD_CONFIRMED}/voyage; crew share "
        f"{_RECORD_CREW_SHARE}; asymptomatic-at-specimen ~"
        f"{_RECORD_ASYM_SHARE} (honest bound ~{_ASYM_HONEST_BOUND}).",
        "",
        "| arm | cells | pooled lab_conf | Δ vs declared | DP-scale seeds "
        "| crew share pooled | crew share DP-scale | asym share | dated share "
        "| retest spec/conf | wave spec/conf | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, row in rows.items():
        delta = row["lab_confirmed_pooled"] - base.get(
            "lab_confirmed_pooled", 0,
        )
        lines.append(
            f"| {arm} | {row['n_cells']} | {row['lab_confirmed_pooled']} "
            f"| {'+' if delta >= 0 else ''}{delta} "
            f"| {row['dp_scale_cells']} "
            f"| {_fmt(row['crew_share_pooled'])} "
            f"| {_fmt(row['crew_share_dp_scale'])} "
            f"| {_fmt(row['asym_share_pooled'])} "
            f"| {_fmt(row['dated_share_pooled'])} "
            f"| {row['retest_specimens']}/{row['retest_confirmed']} "
            f"| {row['wave_specimens']}/{row['wave_confirmed']} "
            f"| {_verdict(base, arm, row)} |"
        )
    lines += ["", "## Audit", ""]
    for key, errs in problems.items():
        lines.append(f"- {key}: {'; '.join(errs) if errs else 'clean'}")
    if identity:
        lines += ["", "## Bit-identity (day<=31 slice)", ""] + [
            f"- {line}" for line in identity
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", help="s3:// campaign prefix")
    parser.add_argument("--dir", help="local directory of cell_*.json")
    parser.add_argument("--parent-prefix", default=None,
                        help="s3:// prefix of the parent's baseline cells "
                             "for the day<=31 bit-identity slice")
    parser.add_argument("--out", help="write the markdown readout here")
    args = parser.parse_args(argv)

    if args.prefix:
        items = list(_iter_s3_payloads(args.prefix))
    elif args.dir:
        items = list(_iter_local_payloads(Path(args.dir)))
    else:
        parser.error("pass --prefix or --dir")

    design = load_design(str(_REPO_ROOT / _DESIGN))
    expected_cells = {
        (cell.arm_id, cell.seed) for cell in enumerate_cells(design)
    }
    by_arm: dict[str, list[dict[str, Any]]] = {}
    problems: dict[str, list[str]] = {}
    seen: set[tuple[str, int]] = set()
    for key, payload in items:
        arm = (payload.get("cell") or {}).get("arm_id")
        seed = int((payload.get("cell") or {}).get("seed") or 0)
        if (arm, seed) not in expected_cells:
            problems.setdefault("coverage", []).append(
                f"{key}: cell ({arm}, {seed}) not in design",
            )
            continue
        seen.add((arm, seed))
        by_arm.setdefault(arm, []).append(payload)
        errs = _audit_cell(payload)
        if errs:
            problems.setdefault(f"{arm}/{seed}", []).extend(errs)
    missing = sorted(expected_cells - seen)
    if missing:
        problems.setdefault("coverage", []).append(
            f"{len(missing)} cells missing: {missing[:8]}",
        )

    rows = {arm: _arm_rows(ps) for arm, ps in sorted(by_arm.items())}

    identity: list[str] = []
    if args.parent_prefix:
        parent = {
            int((p.get("cell") or {}).get("seed") or 0): p
            for _k, p in _iter_s3_payloads(args.parent_prefix)
        }
        for p in by_arm.get("boxed_declared", []):
            seed = int((p.get("cell") or {}).get("seed") or 0)
            ref = parent.get(seed)
            if ref is None:
                identity.append(f"seed {seed}: no parent cell")
                continue
            diffs = [
                f for f in _IDENTITY_FIELDS
                if p.get(f) != ref.get(f)
            ]
            identity.append(
                f"seed {seed}: {'MATCH' if not diffs else 'DIFF ' + str(diffs)}",
            )

    report = _render(rows, problems, identity)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
