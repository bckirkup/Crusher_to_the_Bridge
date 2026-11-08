#!/usr/bin/env python3
"""Readout for the frozen Phase 2 CONTAM four-cruise contrast campaign.

Pools ``cell_*.json`` artifacts under a local tree or S3 prefix, checks
coverage against ``campaign.json``, aggregates the manifest §8 metrics per
hull x lane x arm, forms the paired seed contrasts for DC01/DC02/DC04/DC05,
tabulates the DC07 source-class x receptor responses, and evaluates the
``mega_cruise_5000_e_baseline`` pilot gate (including the 12 x Phase-1
full-panel extrapolation bounds) when the field cache is supplied. Every
quantity is report-only; the readout returns no verdict beyond the frozen
pilot thresholds.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DIR = Path(__file__).resolve().parent
DESIGN_REL = "campaigns/contam/phase2_cruise_contrasts_01/design/phase2_cruise_contrasts_design.json"
METRIC_NAMES = ("retained_final", "b_v_h", "auc_sum", "peak_concentration", "source_final_mass")
CONTRAST_METRICS = ("retained_final", "b_v_h", "auc_sum", "peak_concentration")
DC01_ORDER = ("oa_050_filter_090", "filter_090", "oa_050", "baseline")
DC02_PAIR = ("oa_050", "eq_gain_025_filter")
DC04_ARMS = {"A": "ach_150_supply", "R": "oa_080", "B": "baseline"}
MAX_LISTED_ZONES = 20

CellIndex = dict[tuple[str, str, str], dict[int, dict[str, Any]]]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _read_json_maybe_s3(location: str) -> dict[str, Any]:
    if location.startswith("s3://"):
        import boto3

        parsed = urlparse(location)
        body = boto3.client("s3").get_object(
            Bucket=parsed.netloc, Key=parsed.path.lstrip("/"),
        )["Body"].read()
        return json.loads(body)
    return _load_json(Path(location))


def _split_s3(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise SystemExit(f"need s3:// uri, got {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/").rstrip("/") + "/"


def _iter_s3_cells(prefix: str) -> Iterable[tuple[str, dict[str, Any], int]]:
    import boto3

    bucket, key_prefix = _split_s3(prefix)
    client = boto3.client("s3")
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents") or []:
            key = str(obj["Key"])
            if "/cell_" not in key or not key.endswith(".json"):
                continue
            body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            yield key, json.loads(body), int(obj.get("Size") or 0)


def _iter_local_cells(root: Path) -> Iterable[tuple[str, dict[str, Any], int]]:
    for path in sorted(root.rglob("cell_*.json")):
        yield str(path), _load_json(path), path.stat().st_size


def _iter_cells(location: str) -> Iterable[tuple[str, dict[str, Any], int]]:
    if location.startswith("s3://"):
        yield from _iter_s3_cells(location)
    else:
        yield from _iter_local_cells(Path(location))


# ── per-cell accessors ───────────────────────────────────────────────────


def _arm_of(payload: dict[str, Any]) -> str:
    return str(payload.get("arm") or "baseline")


def _cell_key(payload: dict[str, Any]) -> tuple[str, str, str, int]:
    return (str(payload["hull"]), str(payload["lane"]), _arm_of(payload), int(payload["seed"]))


def _median(values: list[float]) -> float | None:
    return None if not values else float(statistics.median(values))


def _metric(payload: dict[str, Any], name: str) -> float | None:
    value = (payload.get("metrics") or {}).get(name)
    return None if value is None else float(value)


def _final_retained(payload: dict[str, Any]) -> float | None:
    curve = (payload.get("metrics") or {}).get("retained_fraction_curve") or []
    return None if not curve else float(curve[-1])


def _cell_metrics(payload: dict[str, Any]) -> dict[str, float | None]:
    return {
        "retained_final": _final_retained(payload),
        "b_v_h": _metric(payload, "volume_weighted_concentration_burden_h"),
        "auc_sum": _metric(payload, "concentration_auc_sum_per_m3_h"),
        "peak_concentration": _metric(payload, "peak_concentration_per_m3"),
        "source_final_mass": _metric(payload, "source_zone_final_mass"),
    }


def _zone_auc(payload: dict[str, Any]) -> dict[str, float]:
    stats = (payload.get("metrics") or {}).get("zone_stats") or {}
    return {
        str(zone): float((row or {}).get("auc_concentration_per_m3_h") or 0.0)
        for zone, row in stats.items()
    }


def _index(payloads: list[dict[str, Any]]) -> CellIndex:
    index: CellIndex = {}
    for payload in payloads:
        hull, lane, arm, seed = _cell_key(payload)
        index.setdefault((hull, lane, arm), {})[seed] = payload
    return index


def _hulls(index: CellIndex) -> list[str]:
    return sorted({hull for hull, _lane, _arm in index})


def _lanes(index: CellIndex, hull: str) -> list[str]:
    return sorted({lane for h, lane, _arm in index if h == hull})


def _arms(index: CellIndex, hull: str, lane: str) -> list[str]:
    return sorted({arm for h, ln, arm in index if h == hull and ln == lane})


# ── aggregates ───────────────────────────────────────────────────────────


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"cells": len(rows)}
    for name in METRIC_NAMES:
        values = [float(row[name]) for row in rows if row[name] is not None]
        out[name] = {
            "median": _median(values),
            "mean": None if not values else float(statistics.fmean(values)),
            "min": None if not values else min(values),
            "max": None if not values else max(values),
        }
    return out


def _path_flow_aggregate(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, list[float]] = {"path_count": [], "total_flow_m3h": [], "ducted_flow_m3h": []}
    by_type: dict[str, dict[str, list[float]]] = {}
    for payload in payloads:
        summary = payload.get("path_flow_summary") or {}
        for name in totals:
            if summary.get(name) is not None:
                totals[name].append(float(summary[name]))
        for path_type, row in (summary.get("by_path_type") or {}).items():
            slot = by_type.setdefault(str(path_type), {"count": [], "flow_m3h": [], "ducted_flow_m3h": []})
            for name in slot:
                if (row or {}).get(name) is not None:
                    slot[name].append(float(row[name]))
    return {
        "cells": len(payloads),
        **{name: _median(values) for name, values in totals.items()},
        "by_path_type": {
            path_type: {name: _median(values) for name, values in sorted(rows.items())}
            for path_type, rows in sorted(by_type.items())
        },
    }


def _expected_cells(campaign: dict[str, Any]) -> dict[tuple[str, str, str], list[int]]:
    expected: dict[tuple[str, str, str], list[int]] = {}
    for block in (campaign.get("blocks") or {}).values():
        args = block.get("args") or {}
        if args.get("mode") != "trajectory":
            continue
        key = (str(args["hull"]), str(args["lane"]), str(args.get("arm") or "baseline"))
        expected[key] = [int(s) for s in block["seeds"]]
    return expected


def _coverage(payloads: list[dict[str, Any]], campaign: dict[str, Any]) -> dict[str, Any]:
    expected = _expected_cells(campaign)
    observed: dict[tuple[str, str, str], set[int]] = {}
    for payload in payloads:
        hull, lane, arm, seed = _cell_key(payload)
        observed.setdefault((hull, lane, arm), set()).add(seed)
    rows = []
    missing = 0
    for (hull, lane, arm), seeds in sorted(expected.items()):
        got = observed.get((hull, lane, arm), set())
        absent = sorted(set(seeds) - got)
        missing += len(absent)
        rows.append({
            "hull": hull, "lane": lane, "arm": arm,
            "expected": len(seeds),
            "observed": len(got & set(seeds)),
            "missing_seeds": absent,
            "extra_seeds": sorted(got - set(seeds)),
        })
    blocked = sum(1 for p in payloads if "BLOCKED" in str(p.get("field_source") or "").upper())
    return {
        "expected_cells": sum(len(v) for v in expected.values()),
        "observed_cells": len(payloads),
        "missing_cells": missing,
        "blocked_engine_fallback_count": blocked,
        "blocks": rows,
    }


# ── paired contrasts ─────────────────────────────────────────────────────


def _paired_stat(diffs: list[float]) -> dict[str, Any]:
    if not diffs:
        return {"n": 0, "mean": None, "median": None, "ci95_half_width": None, "min": None, "max": None}
    ci = None if len(diffs) < 2 else 1.96 * statistics.stdev(diffs) / math.sqrt(len(diffs))
    return {
        "n": len(diffs),
        "mean": float(statistics.fmean(diffs)),
        "median": _median(diffs),
        "ci95_half_width": ci,
        "min": min(diffs),
        "max": max(diffs),
    }


def _paired_diffs(
    left: dict[int, dict[str, Any]], right: dict[int, dict[str, Any]], name: str,
) -> dict[str, Any]:
    diffs = []
    for seed in sorted(set(left) & set(right)):
        a = _cell_metrics(left[seed]).get(name)
        b = _cell_metrics(right[seed]).get(name)
        if a is not None and b is not None:
            diffs.append(float(a) - float(b))
    return _paired_stat(diffs)


def _metric_contrast(left: dict[int, dict[str, Any]], right: dict[int, dict[str, Any]]) -> dict[str, Any]:
    return {name: _paired_diffs(left, right, name) for name in CONTRAST_METRICS}


def _lane_contrasts(index: CellIndex) -> dict[str, Any]:
    """DC05 paired N - E per hull x arm, plus P - N on the baseline arm."""
    out: dict[str, Any] = {}
    for hull in _hulls(index):
        row: dict[str, Any] = {}
        for arm in _arms(index, hull, "N"):
            n_cells = index.get((hull, "N", arm))
            e_cells = index.get((hull, "E", arm))
            if n_cells and e_cells:
                row.setdefault("N_minus_E", {})[arm] = _metric_contrast(n_cells, e_cells)
        p_cells = index.get((hull, "P", "baseline"))
        n_base = index.get((hull, "N", "baseline"))
        if p_cells and n_base:
            row["P_minus_N_baseline"] = _metric_contrast(p_cells, n_base)
        if row:
            out[hull] = row
    return out


def _arm_minus_baseline(index: CellIndex) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for (hull, lane, arm), cells in sorted(index.items()):
        base = index.get((hull, lane, "baseline"))
        if arm == "baseline" or not base:
            continue
        out.setdefault(hull, {}).setdefault(lane, {})[arm] = _metric_contrast(cells, base)
    return out


def _seed_bv(cells: dict[int, dict[str, Any]] | None) -> dict[int, float]:
    if not cells:
        return {}
    return {
        seed: float(_cell_metrics(payload)["b_v_h"])
        for seed, payload in cells.items()
        if _cell_metrics(payload)["b_v_h"] is not None
    }


def _ordering_violations(values: list[float]) -> list[int]:
    """Indices i where values[i] > values[i+1] (non-decreasing expected)."""
    return [i for i in range(len(values) - 1) if values[i] > values[i + 1]]


def _dc01_for_lane(index: CellIndex, hull: str, lane: str) -> dict[str, Any] | None:
    cells = [index.get((hull, lane, arm)) for arm in DC01_ORDER]
    if any(c is None for c in cells):
        return None
    seeds = sorted(set.intersection(*(set(c) for c in cells)))  # type: ignore[arg-type]
    bv_pass = 0
    bv_violations = []
    zone_violation_rows = []
    for seed in seeds:
        bv = [float(_cell_metrics(c[seed])["b_v_h"]) for c in cells]  # type: ignore[index]
        bad = _ordering_violations(bv)
        if bad:
            bv_violations.append({"seed": seed, "pairs": [f"{DC01_ORDER[i]}>{DC01_ORDER[i + 1]}" for i in bad]})
        else:
            bv_pass += 1
        aucs = [_zone_auc(c[seed]) for c in cells]  # type: ignore[index]
        zones = sorted(set().union(*(set(a) for a in aucs)))
        bad_zones = [z for z in zones if _ordering_violations([a.get(z, 0.0) for a in aucs])]
        if bad_zones:
            zone_violation_rows.append({"seed": seed, "count": len(bad_zones), "zones": bad_zones[:MAX_LISTED_ZONES]})
    return {
        "order": list(DC01_ORDER),
        "seeds": len(seeds),
        "b_v_ordering_pass": bv_pass,
        "b_v_ordering_violations": bv_violations,
        "per_zone_e_i_violation_seeds": len(zone_violation_rows),
        "per_zone_e_i_violations": zone_violation_rows,
    }


def _dc01(index: CellIndex) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for hull in _hulls(index):
        for lane in _lanes(index, hull):
            row = _dc01_for_lane(index, hull, lane)
            if row is not None:
                out.setdefault(hull, {})[lane] = row
    return out


def _dc02_for_lane(index: CellIndex, hull: str, lane: str) -> dict[str, Any] | None:
    o_cells = index.get((hull, lane, DC02_PAIR[0]))
    g_cells = index.get((hull, lane, DC02_PAIR[1]))
    if not o_cells or not g_cells:
        return None
    max_zone_gaps = []
    for seed in sorted(set(o_cells) & set(g_cells)):
        o_auc = _zone_auc(o_cells[seed])
        g_auc = _zone_auc(g_cells[seed])
        zones = set(o_auc) | set(g_auc)
        max_zone_gaps.append(max((abs(o_auc.get(z, 0.0) - g_auc.get(z, 0.0)) for z in zones), default=0.0))
    return {
        "pair": f"{DC02_PAIR[0]}_minus_{DC02_PAIR[1]}",
        "b_v_h": _paired_diffs(o_cells, g_cells, "b_v_h"),
        "max_abs_zone_e_i_gap": _paired_stat(max_zone_gaps),
        "exact_zero_seeds": sum(1 for gap in max_zone_gaps if gap == 0.0),
    }


def _dc02(index: CellIndex) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for hull in _hulls(index):
        for lane in _lanes(index, hull):
            row = _dc02_for_lane(index, hull, lane)
            if row is not None:
                out.setdefault(hull, {})[lane] = row
    return out


def _reductions(arm_bv: dict[int, float], base_bv: dict[int, float]) -> dict[str, Any]:
    values = [
        1.0 - arm_bv[seed] / base_bv[seed]
        for seed in sorted(set(arm_bv) & set(base_bv)) if base_bv[seed] > 0.0
    ]
    return _paired_stat(values)


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def _dc04_zone_sign_flips(
    a_cells: dict[int, dict[str, Any]], r_cells: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Per-zone dE_i(A - R) whose sign disagrees with the hull-wide dB_V(A - R)."""
    flip_counts: dict[str, int] = {}
    diffs: list[float] = []
    for seed in sorted(set(a_cells) & set(r_cells)):
        a_bv = _cell_metrics(a_cells[seed])["b_v_h"]
        r_bv = _cell_metrics(r_cells[seed])["b_v_h"]
        if a_bv is None or r_bv is None:
            continue
        hull_sign = _sign(float(a_bv) - float(r_bv))
        a_auc = _zone_auc(a_cells[seed])
        r_auc = _zone_auc(r_cells[seed])
        for zone in set(a_auc) | set(r_auc):
            delta = a_auc.get(zone, 0.0) - r_auc.get(zone, 0.0)
            diffs.append(delta)
            if delta != 0.0 and _sign(delta) != hull_sign:
                flip_counts[zone] = flip_counts.get(zone, 0) + 1
    ranked = sorted(flip_counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        "zone_delta_e_i": _paired_stat(diffs),
        "zone_delta_positive": sum(1 for d in diffs if d > 0),
        "zone_delta_negative": sum(1 for d in diffs if d < 0),
        "sign_flip_zone_count": len(flip_counts),
        "sign_flip_zones": [{"zone": z, "seeds": n} for z, n in ranked[:MAX_LISTED_ZONES]],
    }


def _dc04_for_lane(index: CellIndex, hull: str, lane: str) -> dict[str, Any] | None:
    cells = {code: index.get((hull, lane, arm)) for code, arm in DC04_ARMS.items()}
    if any(c is None for c in cells.values()):
        return None
    a_cells, r_cells, b_cells = cells["A"], cells["R"], cells["B"]
    a_bv, r_bv, b_bv = _seed_bv(a_cells), _seed_bv(r_cells), _seed_bv(b_cells)
    r_a = {s: 1.0 - a_bv[s] / b_bv[s] for s in set(a_bv) & set(b_bv) if b_bv[s] > 0}
    r_r = {s: 1.0 - r_bv[s] / b_bv[s] for s in set(r_bv) & set(b_bv) if b_bv[s] > 0}
    gap = [r_a[s] - r_r[s] for s in sorted(set(r_a) & set(r_r))]
    return {
        "arms": dict(DC04_ARMS),
        "A_minus_R": _metric_contrast(a_cells, r_cells),  # type: ignore[arg-type]
        "A_minus_B": _metric_contrast(a_cells, b_cells),  # type: ignore[arg-type]
        "R_minus_B": _metric_contrast(r_cells, b_cells),  # type: ignore[arg-type]
        "reduction_R_A": _reductions(a_bv, b_bv),
        "reduction_R_R": _reductions(r_bv, b_bv),
        "reduction_gap_A_minus_R": _paired_stat(gap),
        "edison_tie_band_5pp_report_only": {
            "within_band_seeds": sum(1 for g in gap if abs(g) <= 0.05),
            "n": len(gap),
            "selector": False,
        },
        "per_zone": _dc04_zone_sign_flips(a_cells, r_cells),  # type: ignore[arg-type]
    }


def _dc04(index: CellIndex) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for hull in _hulls(index):
        for lane in _lanes(index, hull):
            row = _dc04_for_lane(index, hull, lane)
            if row is not None:
                out.setdefault(hull, {})[lane] = row
    return out


def _arm_effect_parity(index: CellIndex, hull: str, arm: str) -> dict[str, Any] | None:
    """DC05: does dB_V(arm - B) agree in sign and magnitude between N and E?"""
    n_arm, n_base = _seed_bv(index.get((hull, "N", arm))), _seed_bv(index.get((hull, "N", "baseline")))
    e_arm, e_base = _seed_bv(index.get((hull, "E", arm))), _seed_bv(index.get((hull, "E", "baseline")))
    seeds = sorted(set(n_arm) & set(n_base) & set(e_arm) & set(e_base))
    if not seeds:
        return None
    d_n = [n_arm[s] - n_base[s] for s in seeds]
    d_e = [e_arm[s] - e_base[s] for s in seeds]
    return {
        "n": len(seeds),
        "sign_agreement": sum(1 for a, b in zip(d_n, d_e) if _sign(a) == _sign(b)),
        "delta_b_v_N": _paired_stat(d_n),
        "delta_b_v_E": _paired_stat(d_e),
        "N_effect_minus_E_effect": _paired_stat([a - b for a, b in zip(d_n, d_e)]),
    }


def _dc05(index: CellIndex) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for hull in _hulls(index):
        for arm in _arms(index, hull, "N"):
            if arm == "baseline":
                continue
            row = _arm_effect_parity(index, hull, arm)
            if row is not None:
                out.setdefault(hull, {})[arm] = row
    return out


def _ahs_flow_tables(index: CellIndex) -> dict[str, Any]:
    """Realized per-AHS flows from one E/P cell per hull x lane x arm (identical across seeds)."""
    out: dict[str, Any] = {}
    for (hull, lane, arm), cells in sorted(index.items()):
        if lane == "N" or not cells:
            continue
        first = cells[min(cells)]
        table = first.get("ahs_flow_table")
        if table:
            out[f"{hull}:{lane}:{arm}"] = table
    return out


# ── DC07 source-class x receptor responses ───────────────────────────────


def _platform_neighbourhood(hull: str) -> tuple[dict[str, str], dict[str, set[str]]]:
    airflow = _load_json(ROOT / "data" / "platforms" / hull / "air_flow_paths.json")
    group_of: dict[str, str] = {}
    for group in airflow.get("hvac_zones") or []:
        for room in group.get("rooms") or []:
            group_of.setdefault(str(room), str(group.get("id") or ""))
    neighbours: dict[str, set[str]] = {}
    for edge in airflow.get("adjacency") or []:
        src, dst = str(edge.get("from") or ""), str(edge.get("to") or "")
        neighbours.setdefault(src, set()).add(dst)
        neighbours.setdefault(dst, set()).add(src)
    return group_of, neighbours


def _is_local(
    source: str, zone: str, group_of: dict[str, str], neighbours: dict[str, set[str]],
) -> bool:
    same_group = bool(group_of.get(source)) and group_of.get(source) == group_of.get(zone)
    return same_group or zone in neighbours.get(source, set())


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return float(ordered[idx])


def _response_summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "max": None if not values else max(values),
    }


def _receptor_rows(payload: dict[str, Any], group_of: dict[str, str], neighbours: dict[str, set[str]]) -> dict[str, Any]:
    source = str(payload.get("source_zone") or "")
    mass = float(payload.get("tracer_mass") or 1.0)
    stats = (payload.get("metrics") or {}).get("zone_stats") or {}
    rows: dict[str, list[float]] = {"local": [], "remote": [], "time_to_peak_h": [], "first_arrival_h": []}
    never = 0
    for zone, row in stats.items():
        if zone == source:
            continue
        exposure = float((row or {}).get("auc_concentration_per_m3_h") or 0.0) / mass
        rows["local" if _is_local(source, zone, group_of, neighbours) else "remote"].append(exposure)
        if (row or {}).get("first_above_floor_h") is None:
            never += 1
            continue
        rows["first_arrival_h"].append(float(row["first_above_floor_h"]))
        if (row or {}).get("time_to_peak_h") is not None:
            rows["time_to_peak_h"].append(float(row["time_to_peak_h"]))
    return {**rows, "never_reached": never}


def _dc07(index: CellIndex) -> dict[str, Any]:
    out: dict[str, Any] = {}
    neighbourhoods: dict[str, tuple[dict[str, str], dict[str, set[str]]]] = {}
    for (hull, lane, arm), cells in sorted(index.items()):
        if hull not in neighbourhoods:
            neighbourhoods[hull] = _platform_neighbourhood(hull)
        group_of, neighbours = neighbourhoods[hull]
        by_class: dict[str, dict[str, Any]] = {}
        for payload in cells.values():
            cls = str(payload.get("source_category") or "unknown")
            slot = by_class.setdefault(cls, {"cells": 0, "local": [], "remote": [], "time_to_peak_h": [], "first_arrival_h": [], "never_reached": 0})
            rows = _receptor_rows(payload, group_of, neighbours)
            slot["cells"] += 1
            for name in ("local", "remote", "time_to_peak_h", "first_arrival_h"):
                slot[name].extend(rows[name])
            slot["never_reached"] += rows["never_reached"]
        out[f"{hull}:{lane}:{arm}"] = {
            cls: {
                "cells": slot["cells"],
                "local_e_i_per_emitted": _response_summary(slot["local"]),
                "remote_e_i_per_emitted": _response_summary(slot["remote"]),
                "time_to_peak_h": _response_summary(slot["time_to_peak_h"]),
                "first_arrival_h": _response_summary(slot["first_arrival_h"]),
                "never_reached_receptors": slot["never_reached"],
            }
            for cls, slot in sorted(by_class.items())
        }
    return out


# ── pilot gate ───────────────────────────────────────────────────────────


def _pilot_rows(payloads: list[dict[str, Any]], design: dict[str, Any]) -> list[dict[str, Any]]:
    pilot = design.get("pilot") or {}
    return [
        p for p in payloads
        if p.get("hull") == pilot.get("hull") and p.get("lane") == pilot.get("lane")
        and _arm_of(p) == str(pilot.get("arm") or "baseline")
    ]


def _timing(rows: list[dict[str, Any]], name: str) -> list[float]:
    return [float((p.get("timing") or {}).get(name) or 0.0) for p in rows]


def _field_seconds(field_cache: dict[str, Any] | None, key: str) -> tuple[float | None, float | None]:
    if not field_cache:
        return None, None
    fields = field_cache.get("fields") or {}
    pilot_field = (fields.get(key) or {}).get("field_seconds")
    all_seconds = [float(f.get("field_seconds") or 0.0) for f in fields.values()]
    return (
        None if pilot_field is None else float(pilot_field),
        max(all_seconds) if all_seconds else None,
    )


def _pilot_gate(
    payloads: list[dict[str, Any]], sizes: dict[tuple[str, str, str, int], int],
    field_cache: dict[str, Any] | None, array_wall_clock_minutes: float | None,
    design: dict[str, Any],
) -> dict[str, Any]:
    pilot = design.get("pilot") or {}
    thresholds = design.get("thresholds") or {}
    total = int((design.get("matrix") or {}).get("total_trajectories") or 0)
    rows = _pilot_rows(payloads, design)
    key = f"{pilot.get('hull')}:{pilot.get('lane')}:{pilot.get('arm', 'baseline')}"
    pilot_field, max_field = _field_seconds(field_cache, key)
    trajectory_seconds = _timing(rows, "trajectory_seconds")
    bytes_total = sum(sizes.get(_cell_key(p), 0) for p in rows) if rows else None
    mean_seconds = statistics.fmean(trajectory_seconds) if trajectory_seconds else None
    checks: dict[str, Any] = {
        "cell_count": len(rows),
        "expected_cell_count": len(pilot.get("seeds") or []),
        "seeds_complete": len(rows) == len(pilot.get("seeds") or []) and bool(rows),
        "blocked_engine_fallback_count": sum(1 for p in rows if "BLOCKED" in str(p.get("field_source") or "").upper()),
        "commissioned_field_solve_seconds": pilot_field,
        "max_field_solve_seconds_all_fields": max_field,
        "trajectory_wall_p95_seconds": _percentile(trajectory_seconds, 0.95),
        "trajectory_mean_seconds": mean_seconds,
        "array_wall_clock_minutes": array_wall_clock_minutes,
        "estimated_cpu_hours": None if pilot_field is None else (sum(trajectory_seconds) + pilot_field) / 3600.0,
        "peak_rss_mib": max(_timing(rows, "peak_rss_mib") or [0.0]),
        "artifact_bytes_total": bytes_total,
        "full_panel_cpu_hours_extrapolated": None if mean_seconds is None else total * mean_seconds / 3600.0,
        "full_panel_artifact_bytes_extrapolated": None if not rows or bytes_total is None else total * bytes_total / len(rows),
    }
    for name in ("dropped_endpoint_count", "unknown_real_zone_count", "alias_collision_count"):
        checks[name] = max([int(((p.get("field_audit") or {}).get(name)) or 0) for p in rows] or [0])
    checks["limits"] = {
        "blocked_engine_fallback_count": thresholds.get("blocked_engine_fallback_count", 0),
        "commissioned_field_solve_seconds": thresholds.get("commissioned_field_solve_seconds_max"),
        "max_field_solve_seconds_all_fields": thresholds.get("commissioned_field_solve_seconds_max"),
        "trajectory_wall_p95_seconds": thresholds.get("trajectory_wall_p95_seconds_max"),
        "array_wall_clock_minutes": thresholds.get("array_wall_clock_minutes_max"),
        "estimated_cpu_hours": thresholds.get("cpu_hours_max"),
        "peak_rss_mib": thresholds.get("peak_rss_mib_max"),
        "artifact_bytes_total": thresholds.get("artifact_bytes_max"),
        "full_panel_cpu_hours_extrapolated": thresholds.get("full_panel_cpu_hours_extrapolated_max"),
        "full_panel_artifact_bytes_extrapolated": thresholds.get("full_panel_artifact_bytes_extrapolated_max"),
        "dropped_endpoint_count": thresholds.get("dropped_endpoint_count", 0),
        "unknown_real_zone_count": thresholds.get("unknown_real_zone_count", 0),
        "alias_collision_count": thresholds.get("alias_collision_count", 0),
    }
    _refresh_pilot_gate(checks)
    return {"hull": pilot.get("hull"), "lane": pilot.get("lane"), "arm": pilot.get("arm", "baseline"), "block": pilot.get("trajectory_block"), "checks": checks}


def _refresh_pilot_gate(checks: dict[str, Any]) -> None:
    passed = []
    for name, limit in checks["limits"].items():
        value = checks.get(name)
        passed.append(None if value is None or limit is None else bool(value <= limit))
    checks["pass"] = passed
    if checks.get("seeds_complete") is not True:
        checks["go"] = False
    elif any(p is None for p in passed):
        checks["go"] = None
    else:
        checks["go"] = all(passed)


# ── report ───────────────────────────────────────────────────────────────


def build_report(
    cells: list[tuple[str, dict[str, Any], int]], campaign: dict[str, Any],
    design: dict[str, Any], field_cache: dict[str, Any] | None = None,
    array_wall_clock_minutes: float | None = None,
) -> dict[str, Any]:
    payloads = [payload for _key, payload, _size in cells]
    sizes = {_cell_key(p): size for _k, p, size in cells}
    index = _index(payloads)
    return {
        "design_id": design.get("design_id"),
        "coverage": _coverage(payloads, campaign),
        "metrics_by_hull_lane_arm": {
            f"{hull}:{lane}:{arm}": _aggregate([_cell_metrics(p) for p in rows.values()])
            for (hull, lane, arm), rows in sorted(index.items())
        },
        "path_flow_by_hull_lane_arm": {
            f"{hull}:{lane}:{arm}": _path_flow_aggregate(list(rows.values()))
            for (hull, lane, arm), rows in sorted(index.items())
        },
        "lane_contrasts": _lane_contrasts(index),
        "arm_minus_baseline": _arm_minus_baseline(index),
        "dc01_ordering_control": _dc01(index),
        "dc02_equal_gain_control": _dc02(index),
        "dc04_matched_removal": _dc04(index),
        "dc05_arm_effect_parity": _dc05(index),
        "dc05_realized_ahs_flows": _ahs_flow_tables(index),
        "dc07_source_receptor_responses": _dc07(index),
        "phase1_field_control": (field_cache or {}).get("phase1_control"),
        "pilot_gate": _pilot_gate(payloads, sizes, field_cache, array_wall_clock_minutes, design),
        "report_only_diagnostics": design.get("report_only_diagnostics") or [],
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _markdown_metrics(report: dict[str, Any]) -> list[str]:
    lines = ["## Metrics", "", "| hull:lane:arm | cells | retained_final med | B_V med | AUC med | peak med |", "|---|---:|---:|---:|---:|---:|"]
    for key, row in report["metrics_by_hull_lane_arm"].items():
        lines.append(
            f"| {key} | {row['cells']} | {_fmt(row['retained_final']['median'])} | "
            f"{_fmt(row['b_v_h']['median'])} | {_fmt(row['auc_sum']['median'])} | "
            f"{_fmt(row['peak_concentration']['median'])} |"
        )
    return lines


def _markdown_contrasts(report: dict[str, Any]) -> list[str]:
    lines = ["## Paired lane contrasts (DC05)", ""]
    for hull, row in report["lane_contrasts"].items():
        for arm, metrics in (row.get("N_minus_E") or {}).items():
            stat = metrics["b_v_h"]
            lines.append(f"- {hull} N−E {arm} B_V: n={stat['n']} mean={_fmt(stat['mean'])} ci95={_fmt(stat['ci95_half_width'])}")
        if "P_minus_N_baseline" in row:
            stat = row["P_minus_N_baseline"]["b_v_h"]
            lines.append(f"- {hull} P−N baseline B_V: n={stat['n']} mean={_fmt(stat['mean'])} ci95={_fmt(stat['ci95_half_width'])}")
    lines += ["", "## DC01 ordering control", ""]
    for hull, lanes in report["dc01_ordering_control"].items():
        for lane, row in lanes.items():
            lines.append(f"- {hull} {lane}: B_V ordering pass {row['b_v_ordering_pass']}/{row['seeds']}; per-zone violation seeds {row['per_zone_e_i_violation_seeds']}")
    lines += ["", "## DC02 equal-gain control", ""]
    for hull, lanes in report["dc02_equal_gain_control"].items():
        for lane, row in lanes.items():
            lines.append(f"- {hull} {lane}: O−G B_V mean={_fmt(row['b_v_h']['mean'])}; max|ΔE_i| mean={_fmt(row['max_abs_zone_e_i_gap']['mean'])}; exact-zero seeds {row['exact_zero_seeds']}")
    lines += ["", "## DC04 matched removal", ""]
    for hull, lanes in report["dc04_matched_removal"].items():
        for lane, row in lanes.items():
            lines.append(
                f"- {hull} {lane}: A−R B_V mean={_fmt(row['A_minus_R']['b_v_h']['mean'])}; "
                f"R_A={_fmt(row['reduction_R_A']['mean'])} R_R={_fmt(row['reduction_R_R']['mean'])} gap={_fmt(row['reduction_gap_A_minus_R']['mean'])}; "
                f"sign-flip zones {row['per_zone']['sign_flip_zone_count']}"
            )
    return lines


def _markdown(report: dict[str, Any]) -> str:
    cov = report["coverage"]
    lines = [
        f"# {report['design_id']} readout",
        "",
        "## Coverage",
        f"- expected cells: {cov['expected_cells']}",
        f"- observed cells: {cov['observed_cells']}",
        f"- missing cells: {cov['missing_cells']}",
        f"- BLOCKED_ENGINE_FALLBACK: {cov['blocked_engine_fallback_count']}",
        "",
    ]
    lines += _markdown_metrics(report)
    lines += [""]
    lines += _markdown_contrasts(report)
    lines += ["", "## Pilot gate", ""]
    checks = report["pilot_gate"]["checks"]
    lines += [f"- {name}: {_fmt(value)}" for name, value in checks.items() if name not in {"limits", "pass"}]
    lines += ["", "## Report-only diagnostics", ""]
    lines += [f"- {item}" for item in report["report_only_diagnostics"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("location", help="local directory or s3:// prefix containing cell_*.json")
    parser.add_argument("--campaign-json", default=str(CAMPAIGN_DIR / "campaign.json"))
    parser.add_argument("--design", default=DESIGN_REL)
    parser.add_argument("--field-cache", default=None, help="field_cache.json path or s3 URI")
    parser.add_argument("--array-wall-clock-minutes", type=float, default=None)
    parser.add_argument("--out", default=None, help="optional markdown output path")
    parser.add_argument("--json-out", default=None, help="optional JSON report path")
    args = parser.parse_args(argv)
    design_path = Path(args.design)
    design = _read_json_maybe_s3(str(design_path if design_path.is_absolute() else ROOT / design_path))
    campaign = _load_json(Path(args.campaign_json))
    cells = list(_iter_cells(args.location))
    field_cache = _read_json_maybe_s3(args.field_cache) if args.field_cache else None
    report = build_report(cells, campaign, design, field_cache, args.array_wall_clock_minutes)
    if args.out:
        Path(args.out).write_text(_markdown(report), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
