#!/usr/bin/env python3
"""MEGA-IMPACT-01 fleet readout — the mechanism-attribution factorial.

Reads ``summary.json`` (and ``rss_samples.json``) off the run zips by S3
ranged member GETs — no full downloads — for every tier of the 2x2
factorial declared in ``docs/norovirus/noro_mega_impact_01_design.md``:

- ``a0`` — the existing NORO-MEGA-01 zips at
  ``campaign/noro_mega_01/fl_mega_12d_scr`` (caregiver on / food off),
  seeds 8000-8287 at bp25c7 (288 zips; the bp32.5 siblings are excluded).
- ``a1`` — ``fl_mega_impact_a1`` (caregiver on / food on), seeds
  8000-8287 — per-seed paired to a0 (the 0xF00D dedicated stream makes
  food-ON the identical voyage plus injected events).
- ``a2`` — ``fl_mega_impact_a2`` (caregiver off / food off), seeds
  8000-8149 — distributional caregiver baseline.
- ``a3`` — ``fl_mega_impact_a3`` (caregiver off / food on), seeds
  8000-8149 — food-without-caregiver + interaction.
- ``a1_bp40c30`` — ``fl_mega_impact_a1_bp40c30``, seeds 8000-8049 —
  optional distributional slice (no a0 exists at bp40c30).

With ``--census`` the food arms additionally fetch the
``growth_census.json.gz`` member and tail-decode the ``common_source``
block (telemetry counters + per-event witness rows: source_kind mix,
servings, cohort sizes, per-serving doses). Census members decompress to
~1 GB on mega — keep ``--census-workers`` small.

Per arm the report carries the design's frozen readout list: report-count
distributions vs the ceil(3%) channel wires with the >=80/90/95/100%
reach counts, burst12, still-climbing, peak/detection epochs, the
ever-infected -> ever-ill -> reported funnel (with the caregiver split),
the aboard-acquisition pathway mix, mechanism counters, and — for a1 —
per-seed paired deltas vs a0 plus the lot-event-positive voyage split.

Reads only; fits nothing.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_source_readout import (  # noqa: E402
    _cs_fields,
    _tail_fields,
)
from mega_baseline_reanalysis import (  # noqa: E402
    _quantiles,
    _window_share,
)
from outbreak_anchor_readout import (  # noqa: E402
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
)
from tools.diag.readout_common import emit_report_outputs  # noqa: E402

_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_A0_PREFIX = "campaign/noro_mega_01/fl_mega_12d_scr"
_IMPACT_PREFIX = "campaign/noro_mega_impact_01"

# arm -> (tier directory under the impact prefix, caregiver, food)
_ARMS = {
    "a1": ("fl_mega_impact_a1", True, True),
    "a2": ("fl_mega_impact_a2", False, False),
    "a3": ("fl_mega_impact_a3", False, True),
    "a1_bp40c30": ("fl_mega_impact_a1_bp40c30", True, True),
}
_A0_BP_TOKEN = "bp25c7"

_SEED_RE = re.compile(r"_s(\d+)\.zip$")


def _seed_of_key(key: str) -> int | None:
    m = _SEED_RE.search(key)
    return int(m.group(1)) if m else None


def _list_keys(client, bucket: str, prefix: str) -> list[str]:
    return [
        obj["Key"]
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix.rstrip("/") + "/",
        )
        for obj in page.get("Contents", [])
        if obj["Key"].endswith(".zip")
    ]


def _json_member(client, bucket: str, key: str, member: str) -> Any:
    try:
        blob = _s3_member_blob(client, bucket, key, member)
    except Exception:
        return None
    if blob is None:
        return None
    try:
        return json.loads(blob)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _voyage_row(summary: dict[str, Any], key: str) -> dict[str, Any]:
    """One voyage's readout row from its summary.json."""
    row = _row_from_summary(summary, key.rsplit("/", 1)[-1])
    anchor = row["anchor_row"]
    body = summary.get("summary") or {}
    mech = summary.get("mechanisms") or {}
    params = summary.get("parameters") or {}
    pax_comp = int(anchor["passenger_complement"])
    crew_comp = int(anchor["crew_complement"])
    thr_pax = math.ceil(A9_POSTING_THRESHOLD * pax_comp)
    thr_crew = math.ceil(A9_POSTING_THRESHOLD * crew_comp)
    rep_pax = round(
        float(anchor["reported_case_attack_rate_passenger"]) * pax_comp
    )
    rep_crew = round(
        float(anchor["reported_case_attack_rate_crew"]) * crew_comp
    )
    ts = summary.get("timeseries") or []
    new_infect = [int(e.get("new_infections", 0) or 0) for e in ts]
    num_epochs = int(params.get("num_epochs") or len(new_infect) or 0)
    last_inf = row.get("last_infecting_epoch")
    routes = body.get("infections_by_dominant_route") or {}
    shares = body.get("infection_dose_share_by_route") or {}
    pax_rate = float(anchor["reported_case_attack_rate_passenger"])
    crew_rate = float(anchor["reported_case_attack_rate_crew"])
    # Pre-mechanisms images (the a0 baseline) carry no `mechanisms`
    # block — keep those counters None so they render absent, not zero.
    has_mech = summary.get("mechanisms") is not None
    return {
        "run_id": row["run_id"],
        "seed": _seed_of_key(key) or row["seed"],
        "ignited": row["ignited"],
        "n_imports": row["n_imports"],
        "n_acquired": row["n_acquired"],
        "rep_pax": rep_pax,
        "rep_crew": rep_crew,
        "thr_pax": thr_pax,
        "thr_crew": thr_crew,
        "pax_ratio": rep_pax / thr_pax if thr_pax else 0.0,
        "crew_ratio": rep_crew / thr_crew if thr_crew else 0.0,
        "posted": _posted(anchor),
        "posted_pax": pax_rate >= A9_POSTING_THRESHOLD,
        "posted_crew": crew_rate >= A9_POSTING_THRESHOLD,
        "vsp_trigger_epoch": row.get("vsp_trigger_epoch"),
        "detection_epoch": row.get("detection_epoch"),
        "peak_epoch": row.get("peak_epoch"),
        "peak_prevalence": row.get("peak_prevalence"),
        "onset_epoch": row.get("onset_epoch"),
        "num_epochs": num_epochs,
        "still_climbing": bool(
            last_inf is not None and num_epochs
            and last_inf >= num_epochs - 2
        ),
        "burst12_share": _window_share(new_infect),
        "outbreak_occurred": bool(
            (summary.get("derived") or {}).get("outbreak_occurred")
        ),
        "ever_infected_pax": int(
            body.get("cumulative_ever_infected_passenger", 0) or 0
        ),
        "ever_infected_crew": int(
            body.get("cumulative_ever_infected_crew", 0) or 0
        ),
        "ever_ill_pax": int(body.get("cumulative_ever_ill_passenger", 0) or 0),
        "ever_ill_crew": int(body.get("cumulative_ever_ill_crew", 0) or 0),
        "symptomatic_final": int(body.get("symptomatic", 0) or 0),
        "sick_call_count": int(body.get("sick_call_count", 0) or 0),
        "quarantined_final": int(body.get("quarantined", 0) or 0),
        "quarantine_refusers": int(
            body.get("quarantine_refusers", 0) or 0
        ),
        "inf_ar_pax": float(
            body.get("infection_attack_rate_passenger", 0.0) or 0.0
        ),
        "inf_ar_crew": float(
            body.get("infection_attack_rate_crew", 0.0) or 0.0
        ),
        "routes": {k: int(v) for k, v in routes.items()},
        "dose_shares": {k: float(v) for k, v in shares.items()},
        "cs_food_infections": int(routes.get("common_source_food", 0) or 0),
        "cs_food_dose_share": float(
            shares.get("common_source_food", 0.0) or 0.0
        ),
        "cs_events_summary": (
            int(mech.get("common_source_events") or 0) if has_mech else None
        ),
        "cs_takers_summary": (
            int(mech.get("common_source_takers") or 0) if has_mech else None
        ),
        "cg_responses": (
            int(mech.get("caregiver_responses") or 0) if has_mech else None
        ),
        "cg_reports": (
            int(mech.get("caregiver_reports") or 0) if has_mech else None
        ),
        "payload_profile": mech.get("payload_profile"),
        "rss_mb": summary.get("rss_mb") or {},
    }


def _reach_counts(rows: list[dict[str, Any]]) -> dict[float, int]:
    return {
        bound: sum(
            1 for r in rows
            if max(r["pax_ratio"], r["crew_ratio"]) >= bound
        )
        for bound in (0.80, 0.90, 0.95, 1.0)
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in rows if r["n_acquired"] > 0]
    detected = [r for r in rows if r["detection_epoch"] is not None]
    near = _reach_counts(rows)
    routes: Counter = Counter()
    dose: dict[str, float] = defaultdict(float)
    for r in rows:
        routes.update(r["routes"])
        for k, v in r["dose_shares"].items():
            dose[k] += v
    burst = [r["burst12_share"] for r in active
             if r["burst12_share"] is not None]
    fun = _funnel(rows)
    return {
        "n": len(rows),
        "ignited": sum(1 for r in rows if r["ignited"]),
        "acquired_pos": len(active),
        "posted": sum(1 for r in rows if r["posted"]),
        "posted_pax": sum(1 for r in rows if r["posted_pax"]),
        "posted_crew": sum(1 for r in rows if r["posted_crew"]),
        "vsp_triggered": sum(
            1 for r in rows if r["vsp_trigger_epoch"] is not None
        ),
        "detected": len(detected),
        "rep_pax": _quantiles([float(r["rep_pax"]) for r in rows]),
        "rep_crew": _quantiles([float(r["rep_crew"]) for r in rows]),
        "pax_ratio": _quantiles([r["pax_ratio"] for r in rows]),
        "crew_ratio": _quantiles([r["crew_ratio"] for r in rows]),
        "within_threshold_share": near,
        "burst12_share": _quantiles([float(b) for b in burst]),
        "burst12_gt_half": sum(1 for b in burst if b > 0.5),
        "still_climbing": sum(1 for r in rows if r["still_climbing"]),
        "peak_epoch": _quantiles(
            [float(r["peak_epoch"]) for r in rows
             if r["peak_epoch"] is not None],
        ),
        "detection_epoch": _quantiles(
            [float(r["detection_epoch"]) for r in detected],
        ),
        "n_acquired": _quantiles([float(r["n_acquired"]) for r in rows]),
        "ever_ill_pax": _quantiles(
            [float(r["ever_ill_pax"]) for r in rows]
        ),
        "inf_ar_pax": _quantiles([r["inf_ar_pax"] for r in rows]),
        "routes_total": dict(
            sorted(routes.items(), key=lambda kv: -kv[1])
        ),
        "dose_share_total": dict(
            sorted(dose.items(), key=lambda kv: -kv[1])
        ),
        "cs_food_infections": sum(r["cs_food_infections"] for r in rows),
        "cs_food_voyages": sum(
            1 for r in rows if r["cs_food_infections"] > 0
        ),
        "cs_events": sum(r["cs_events_summary"] or 0 for r in rows),
        "cs_takers": sum(r["cs_takers_summary"] or 0 for r in rows),
        "cg_responses": sum(r["cg_responses"] or 0 for r in rows),
        "cg_reports": sum(r["cg_reports"] or 0 for r in rows),
        "funnel": fun,
        "peak_rss_mb": _quantiles(
            [float(r["rss_peak_mb"]) for r in rows
             if r.get("rss_peak_mb")],
        ),
    }


def _funnel(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pooled ever-infected -> ever-ill -> reported rung ratios."""
    inf = sum(
        r["ever_infected_pax"] + r["ever_infected_crew"] for r in rows
    )
    ill = sum(r["ever_ill_pax"] + r["ever_ill_crew"] for r in rows)
    rep = sum(r["rep_pax"] + r["rep_crew"] for r in rows)
    cg_rows = [r["cg_reports"] for r in rows if r["cg_reports"] is not None]
    cg = sum(cg_rows) if cg_rows else None
    return {
        "ever_infected": inf,
        "ever_ill": ill,
        "reported": rep,
        "ill_per_infected": ill / inf if inf else None,
        "rep_per_ill": rep / ill if ill else None,
        "rep_per_infected": rep / inf if inf else None,
        "caregiver_reports": cg,
        "caregiver_share_of_reports": (
            cg / rep if (rep and cg is not None) else None
        ),
    }


def _paired(a0_rows: list[dict], a1_rows: list[dict]) -> dict[str, Any]:
    """Per-seed A1-vs-A0 deltas (food rides a dedicated RNG stream)."""
    a0 = {r["seed"]: r for r in a0_rows}
    pairs = [(a0[r["seed"]], r) for r in a1_rows if r["seed"] in a0]
    fields = (
        "rep_pax", "rep_crew", "n_acquired", "ever_ill_pax",
        "ever_ill_crew", "inf_ar_pax", "inf_ar_crew",
    )
    deltas: dict[str, list[float]] = {f: [] for f in fields}
    transitions = {"gained": 0, "lost": 0, "same": 0}
    burst_d: list[float] = []
    for old, new in pairs:
        for f in fields:
            deltas[f].append(float(new[f]) - float(old[f]))
        if new["burst12_share"] is not None and old["burst12_share"] is not None:
            burst_d.append(new["burst12_share"] - old["burst12_share"])
        if new["posted"] and not old["posted"]:
            transitions["gained"] += 1
        elif old["posted"] and not new["posted"]:
            transitions["lost"] += 1
        else:
            transitions["same"] += 1
    out: dict[str, Any] = {"n_pairs": len(pairs), "transitions": transitions}
    for f, vals in deltas.items():
        q = _quantiles(vals)
        out[f] = {
            "median_delta": q["median"],
            "p90_delta": q["p90"],
            "share_positive": (
                sum(1 for v in vals if v > 0) / len(vals) if vals else None
            ),
        }
    q = _quantiles(burst_d)
    out["burst12_delta"] = {"median": q["median"], "p90": q["p90"]}
    return out


def _census_row(client, bucket: str, key: str) -> dict[str, Any]:
    """Tail-decode the census member's ``common_source`` block."""
    raw = _s3_member_blob(client, bucket, key, "growth_census.json.gz")
    if raw is None:
        return {"key": key, "census": None}
    try:
        text = gzip.decompress(raw)
    except (OSError, EOFError):
        return {"key": key, "census": None}
    cs = _tail_fields(text)
    del text
    telemetry, events, _exposures = _cs_fields(cs)
    arms: Counter = Counter()
    servings = 0
    zero_dose = 0
    max_cohort = 0
    max_dose = 0.0
    for e in events:
        kind = e.get("source_kind") or "unknown"
        arms[kind] += 1
        servings += int(e.get("servings_taken", 0) or 0)
        max_cohort = max(max_cohort, int(e.get("cohort_size", 0) or 0))
        dose = e.get("per_serving_dose")
        if dose:
            max_dose = max(max_dose, float(dose))
        else:
            zero_dose += 1
    return {
        "key": key,
        "census": {
            "telemetry": telemetry,
            "n_event_rows": len(events),
            "arms": dict(arms),
            "servings": servings,
            "zero_dose_events": zero_dose,
            "max_cohort_size": max_cohort,
            "max_per_serving_dose": max_dose,
        },
    }


def _census_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-kind event mix + event magnitudes over census-read rows."""
    seen = [r for r in rows if r.get("census_cs")]
    if not seen:
        return {}
    arms: Counter = Counter()
    takers = servings = zero_dose = n_events = lot_pos = 0
    dose_credited = 0.0
    max_cohort = 0
    max_dose = 0.0
    for r in seen:
        blk = r["census_cs"]
        tel = blk.get("telemetry") or {}
        n_events += int(
            sum(v for k, v in tel.items() if k.startswith("events_"))
        )
        for k, v in (blk.get("arms") or {}).items():
            arms[k] += int(v)
        takers += int(tel.get("takers_served", 0) or 0)
        dose_credited += float(tel.get("dose_credited", 0.0) or 0.0)
        servings += blk.get("servings", 0)
        zero_dose += blk.get("zero_dose_events", 0)
        max_cohort = max(max_cohort, blk.get("max_cohort_size", 0))
        max_dose = max(max_dose, blk.get("max_per_serving_dose", 0.0))
        if int(tel.get("events_provisioned_lot", 0) or 0) > 0:
            lot_pos += 1
    return {
        "n": len(seen),
        "events": n_events,
        "events_per_voyage_med": _quantiles(
            [float(r["cs_telemetry_events"]) for r in seen]
        )["median"],
        "arms": dict(arms),
        "takers": takers,
        "servings": servings,
        "zero_dose": zero_dose,
        "zero_dose_share": zero_dose / n_events if n_events else None,
        "dose_credited": dose_credited,
        "max_cohort": max_cohort,
        "max_dose": max_dose,
        "lot_positive_voyages": lot_pos,
    }


def _split_side(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "rep_pax_med": _quantiles(
            [float(r["rep_pax"]) for r in rows]
        )["median"],
        "rep_crew_med": _quantiles(
            [float(r["rep_crew"]) for r in rows]
        )["median"],
        "best_ratio_max": max(
            (max(r["pax_ratio"], r["crew_ratio"]) for r in rows),
            default=None,
        ),
        "burst12_med": _quantiles(
            [r["burst12_share"] for r in rows
             if r["burst12_share"] is not None]
        )["median"],
        "acquired_med": _quantiles(
            [float(r["n_acquired"]) for r in rows]
        )["median"],
        "cs_food_inf_med": _quantiles(
            [float(r["cs_food_infections"]) for r in rows]
        )["median"],
    }


def _excursion_split(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Voyage outcomes split on cs_food conversion (the excursion set).

    Excursion = voyage carrying >=1 dominant-route common_source_food
    infection — the FOOD-01 definition; on mega this rides the per-voyage
    provisioned-lot draw plus rare handler/diner conversions.
    """
    seen = [r for r in rows if r.get("census_cs") is not None]
    pos = [r for r in seen if r["cs_food_infections"] > 0]
    neg = [r for r in seen if not r["cs_food_infections"]]
    out = {
        "excursion": _split_side(pos),
        "rest": _split_side(neg),
        "lot_positive": sum(
            1 for r in seen if r.get("lot_events", 0) > 0
        ),
        "n_census": len(seen),
    }
    return out


def _merge_census(rows: list[dict], census: dict[str, dict]) -> None:
    for r in rows:
        blk = (census.get(r["_key"]) or {}).get("census")
        r["census_cs"] = blk
        tel = (blk or {}).get("telemetry") or {}
        r["lot_events"] = int(tel.get("events_provisioned_lot", 0) or 0)
        r["cs_telemetry_events"] = int(
            sum(v for k, v in tel.items() if k.startswith("events_"))
        )


def _collect_summary_arm(
    client, bucket: str, keys: list[str],
) -> list[dict[str, Any]]:
    def one(key: str) -> dict[str, Any] | None:
        blob = _s3_member_blob(client, bucket, key, "summary.json")
        if blob is None:
            return None
        try:
            summary = json.loads(blob)
            row = _voyage_row(summary, key)
        except (json.JSONDecodeError, KeyError, RuntimeError, TypeError):
            return None
        rss = _json_member(client, bucket, key, "rss_samples.json")
        row["rss_peak_mb"] = (rss or {}).get("peak_rss_mb")
        row["_key"] = key
        return row

    with ThreadPoolExecutor(max_workers=32) as pool:
        return [r for r in pool.map(one, keys) if r is not None]


def _collect_census(
    client, bucket: str, keys: list[str], workers: int,
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, res in enumerate(pool.map(
            lambda k: _census_row(client, bucket, k), keys,
        )):
            out[res["key"]] = res
            if (i + 1) % 25 == 0:
                print(f"  census {i + 1}/{len(keys)}", flush=True)
    return out


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _fmt_num(value: Any) -> str:
    return "—" if value is None else f"{float(value):.0f}"


def _arm_summary_table(aggregates: dict[str, dict]) -> list[str]:
    lines = [
        "| arm | n | posted | pax | crew | VSP | detected | med rep pax"
        " (ratio) | med rep crew (ratio) | max ratio | >=80% | >=90% |"
        " >=95% |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, a in aggregates.items():
        lines.append(
            f"| {arm} | {a['n']} | {a['posted']} | {a['posted_pax']}"
            f" | {a['posted_crew']} | {a['vsp_triggered']} |"
            f" {a['detected']} | {_fmt_num(a['rep_pax']['median'])}"
            f" ({_fmt(a['pax_ratio']['median'])})"
            f" | {_fmt_num(a['rep_crew']['median'])}"
            f" ({_fmt(a['crew_ratio']['median'])})"
            f" | {_fmt(max(a['pax_ratio']['max'] or 0, a['crew_ratio']['max'] or 0))}"
            f" | {a['within_threshold_share'][0.8]}"
            f" | {a['within_threshold_share'][0.9]}"
            f" | {a['within_threshold_share'][0.95]} |"
        )
    return lines


def _arm_shape_table(aggregates: dict[str, dict]) -> list[str]:
    lines = [
        "| arm | burst12 med | p90 | max | >0.5 | still climbing |"
        " peak_ep med | det_ep med | med acquired | med ever-ill pax |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, a in aggregates.items():
        b, p, d = a["burst12_share"], a["peak_epoch"], a["detection_epoch"]
        lines.append(
            f"| {arm} | {_fmt(b['median'])} | {_fmt(b['p90'])}"
            f" | {_fmt(b['max'])} | {a['burst12_gt_half']}"
            f" | {a['still_climbing']}/{a['n']} | {_fmt(p['median'], 0)}"
            f" | {_fmt(d['median'], 0)}"
            f" | {_fmt_num(a['n_acquired']['median'])}"
            f" | {_fmt_num(a['ever_ill_pax']['median'])} |"
        )
    return lines


def _routes_cell(routes: dict[str, int]) -> str:
    total = sum(routes.values())
    if not total:
        return "-"
    parts = [
        f"{k} {100.0 * v / total:.1f}%" for k, v in routes.items() if v
    ]
    return ", ".join(parts)


def _arm_route_table(aggregates: dict[str, dict]) -> list[str]:
    lines = [
        "| arm | aboard pathway mix (share of acquisitions) |"
        " cs_food infections | voyages w/ cs_food |",
        "|---|---|---|---|",
    ]
    for arm, a in aggregates.items():
        lines.append(
            f"| {arm} | {_routes_cell(a['routes_total'])}"
            f" | {a['cs_food_infections']} | {a['cs_food_voyages']} |"
        )
    return lines


def _arm_cell(arms: dict[str, int]) -> str:
    total = sum(arms.values())
    if not total:
        return "-"
    order = ("provisioned_lot", "ill_handler", "ill_diner")
    parts = [
        f"{name.split('_', 1)[-1][0].upper()}{100.0 * arms.get(name, 0) / total:.0f}"
        for name in order
    ]
    rest = total - sum(arms.get(n, 0) for n in order)
    if rest:
        parts.append(f"?{100.0 * rest / total:.0f}")
    return "/".join(parts)


def _arm_mech_table(aggregates: dict[str, dict]) -> list[str]:
    lines = [
        "| arm | cs events | cs takers | cg responses | cg reports |"
        " cg share of reports | ill/inf | rep/ill |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for arm, a in aggregates.items():
        f = a["funnel"]
        lines.append(
            f"| {arm} | {a['cs_events']} | {a['cs_takers']}"
            f" | {a['cg_responses']} | {a['cg_reports']}"
            f" | {_fmt(f['caregiver_share_of_reports'])}"
            f" | {_fmt(f['ill_per_infected'])}"
            f" | {_fmt(f['rep_per_ill'])} |"
        )
    return lines


def _render(report: dict[str, Any]) -> str:
    lines = [
        "# MEGA-IMPACT-01 fleet readout",
        "",
        "Status: measured — fleet arm comparison per "
        "`noro_mega_impact_01_design.md`. Tool: "
        "`tools/noro_diag/mega_impact_fleet_readout.py` (regenerates this "
        "file). Baseline A0 = the NORO-MEGA-01 zips re-read through the "
        "same row extractor.",
        "",
        "## Arm table",
        "",
    ]
    lines += _arm_summary_table(report["aggregates"])
    lines += ["", "## Onset shape / progression", ""]
    lines += _arm_shape_table(report["aggregates"])
    lines += ["", "## Pathway mix + funnel + mechanisms", ""]
    lines += _arm_route_table(report["aggregates"])
    lines += [""]
    lines += _arm_mech_table(report["aggregates"])
    paired = report.get("paired") or {}
    if paired.get("n_pairs"):
        lines += ["", "## Paired A1-vs-A0 deltas (food mechanism)", ""]
        lines.append(f"Paired seeds: {paired['n_pairs']}.")
        lines.append("")
        lines.append("| field | median delta | p90 delta | share >0 |")
        lines.append("|---|---|---|---|")
        for f, q in paired.items():
            if f in ("n_pairs", "transitions") or not isinstance(q, dict):
                continue
            share = q.get("share_positive")
            med = q.get("median_delta", q.get("median"))
            lines.append(
                f"| {f} | {_fmt(med)} | {_fmt(q.get('p90_delta', q.get('p90')))}"
                f" | {_fmt(share)} |"
            )
        t = paired["transitions"]
        lines += [
            "",
            f"Posting transitions: +{t['gained']} / -{t['lost']}"
            f" / {t['same']} unchanged.",
        ]
    census_aggs = report.get("census_aggregates") or {}
    if census_aggs:
        lines += ["", "## Food mechanism (census witness)", ""]
        lines.append(
            "| arm | zips read | events | ev/voy med | arm L/H/D % |"
            " takers | zero-dose | dose credited | max cohort |"
            " lot-positive |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for arm, c in census_aggs.items():
            lines.append(
                f"| {arm} | {c['n']} | {c['events']}"
                f" | {_fmt_num(c['events_per_voyage_med'])}"
                f" | {_arm_cell(c['arms'])}"
                f" | {c['takers']} | {c['zero_dose']}"
                f" | {c['dose_credited']:.3g} | {c['max_cohort']}"
                f" | {c['lot_positive_voyages']} |"
            )
    splits = report.get("excursion_splits") or {}
    if splits:
        lines += ["", "## Excursion-voyage split (cs_food infection > 0)", ""]
        lines.append(
            "| arm | set | n | rep pax med | rep crew med | max ratio |"
            " burst12 med | acquired med | cs_food inf med |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for arm, s in splits.items():
            for label, side in (
                ("excursion", s["excursion"]), ("rest", s["rest"]),
            ):
                lines.append(
                    f"| {arm} | {label} | {side['n']}"
                    f" | {_fmt_num(side['rep_pax_med'])}"
                    f" | {_fmt_num(side['rep_crew_med'])}"
                    f" | {_fmt(side['best_ratio_max'])}"
                    f" | {_fmt(side['burst12_med'])}"
                    f" | {_fmt_num(side['acquired_med'])}"
                    f" | {_fmt(side['cs_food_inf_med'], 1)} |"
                )
        lines.append("")
        lines.append(
            "Lot-positive voyages (telemetry events_provisioned_lot > 0): "
            + ", ".join(
                f"{arm} {s['lot_positive']}/{s['n_census']}"
                for arm, s in splits.items()
            )
            + "."
        )
    lines += [
        "",
        "Measured at the fleet image SHA; no parameters were fitted.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=_BUCKET)
    parser.add_argument("--a0-prefix", default=_A0_PREFIX)
    parser.add_argument("--impact-prefix", default=_IMPACT_PREFIX)
    parser.add_argument(
        "--census", action="store_true",
        help="tail-decode common_source census blocks on the food arms",
    )
    parser.add_argument("--census-workers", type=int, default=4)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    client = _s3_client()
    arms_rows: dict[str, list[dict[str, Any]]] = {}

    a0_keys = [
        k for k in _list_keys(client, args.bucket, args.a0_prefix)
        if _A0_BP_TOKEN in k
    ]
    arms_rows["a0"] = _collect_summary_arm(client, args.bucket, a0_keys)
    print(f"a0: {len(arms_rows['a0'])} summaries", flush=True)

    for arm, (tier, _cg, _food) in _ARMS.items():
        keys = _list_keys(
            client, args.bucket, f"{args.impact_prefix}/{tier}",
        )
        arms_rows[arm] = _collect_summary_arm(client, args.bucket, keys)
        print(f"{arm}: {len(arms_rows[arm])} summaries", flush=True)

    census: dict[str, dict] = {}
    if args.census:
        food_keys = [
            r["_key"] for arm, (_t, _cg, food) in _ARMS.items() if food
            for r in arms_rows[arm]
        ]
        print(f"census pass on {len(food_keys)} food-arm zips", flush=True)
        census = _collect_census(
            client, args.bucket, food_keys, args.census_workers,
        )
    for arm in _ARMS:
        _merge_census(arms_rows[arm], census)

    aggregates = {
        arm: _aggregate(rows) for arm, rows in arms_rows.items()
    }
    report = {
        "rows": arms_rows,
        "aggregates": aggregates,
        "paired": _paired(arms_rows["a0"], arms_rows["a1"]),
        "census": census,
        "census_aggregates": {
            arm: _census_aggregate(arms_rows[arm]) for arm in _ARMS
            if _ARMS[arm][2]
        },
        "excursion_splits": {
            arm: _excursion_split(arms_rows[arm]) for arm in _ARMS
            if _ARMS[arm][2]
        },
    }
    emit_report_outputs(report, _render(report), args.md_out, args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
