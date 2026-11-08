#!/usr/bin/env python3
"""Readout for the frozen Phase 1 CONTAM tracer campaign.

Pools ``cell_*.json`` artifacts under a local tree or S3 prefix, checks coverage
against ``campaign.json``, aggregates the manifest §8 metrics, forms paired
seed contrasts, and can evaluate the Missouri lane-E pilot gate when the field
cache artifact is supplied.
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
DESIGN_REL = "campaigns/contam/phase1_hvac_tracer_01/design/phase1_hvac_tracer_design.json"


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


def _cell_key(payload: dict[str, Any]) -> tuple[str, str, int]:
    return (str(payload["hull"]), str(payload["lane"]), int(payload["seed"]))


def _median(values: list[float]) -> float | None:
    return None if not values else float(statistics.median(values))


def _metric(payload: dict[str, Any], name: str) -> float | None:
    metrics = payload.get("metrics") or {}
    value = metrics.get(name)
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


def _group_payloads(
    payloads: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for payload in payloads:
        grouped.setdefault((str(payload["hull"]), str(payload["lane"])), []).append(payload)
    return grouped


def _median_value(values: list[float]) -> float | None:
    return _median([float(value) for value in values])


def _path_flow_aggregate(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, list[float]] = {
        "path_count": [],
        "total_flow_m3h": [],
        "ducted_flow_m3h": [],
    }
    by_type: dict[str, dict[str, list[float]]] = {}
    for payload in payloads:
        summary = payload.get("path_flow_summary") or {}
        for name in totals:
            value = summary.get(name)
            if value is not None:
                totals[name].append(float(value))
        for path_type, row in (summary.get("by_path_type") or {}).items():
            slot = by_type.setdefault(str(path_type), {
                "count": [],
                "flow_m3h": [],
                "ducted_flow_m3h": [],
            })
            for name in slot:
                value = (row or {}).get(name)
                if value is not None:
                    slot[name].append(float(value))
    return {
        "cells": len(payloads),
        **{name: _median_value(values) for name, values in totals.items()},
        "by_path_type": {
            path_type: {name: _median_value(values) for name, values in sorted(rows.items())}
            for path_type, rows in sorted(by_type.items())
        },
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"cells": len(rows)}
    for name in ("retained_final", "b_v_h", "auc_sum", "peak_concentration", "source_final_mass"):
        values = [row[name] for row in rows if row[name] is not None]
        out[name] = {
            "median": _median([float(v) for v in values]),
            "mean": None if not values else float(statistics.fmean(float(v) for v in values)),
            "min": None if not values else float(min(float(v) for v in values)),
            "max": None if not values else float(max(float(v) for v in values)),
        }
    return out


def _expected_cells(campaign: dict[str, Any]) -> dict[tuple[str, str], list[int]]:
    expected: dict[tuple[str, str], list[int]] = {}
    for name, block in (campaign.get("blocks") or {}).items():
        args = block.get("args") or {}
        if args.get("mode") != "trajectory":
            continue
        expected[(str(args["hull"]), str(args["lane"]))] = [int(s) for s in block["seeds"]]
    return expected


def _coverage(cells: list[dict[str, Any]], campaign: dict[str, Any]) -> dict[str, Any]:
    expected = _expected_cells(campaign)
    observed: dict[tuple[str, str], set[int]] = {}
    for payload in cells:
        observed.setdefault(_cell_key(payload)[:2], set()).add(int(payload["seed"]))
    rows = []
    missing = 0
    for (hull, lane), seeds in sorted(expected.items()):
        got = observed.get((hull, lane), set())
        absent = sorted(set(seeds) - got)
        extra = sorted(got - set(seeds))
        missing += len(absent)
        rows.append({
            "hull": hull,
            "lane": lane,
            "expected": len(seeds),
            "observed": len(got & set(seeds)),
            "missing_seeds": absent,
            "extra_seeds": extra,
        })
    return {
        "expected_cells": sum(len(v) for v in expected.values()),
        "observed_cells": len(cells),
        "missing_cells": missing,
        "blocks": rows,
    }


def _paired_diffs(left: dict[int, dict[str, float | None]], right: dict[int, dict[str, float | None]], name: str) -> dict[str, Any]:
    diffs = []
    for seed in sorted(set(left) & set(right)):
        a = left[seed].get(name)
        b = right[seed].get(name)
        if a is not None and b is not None:
            diffs.append(float(a) - float(b))
    if not diffs:
        return {"n": 0, "mean": None, "median": None, "ci95_half_width": None}
    mean = float(statistics.fmean(diffs))
    ci = None
    if len(diffs) > 1:
        ci = 1.96 * statistics.stdev(diffs) / math.sqrt(len(diffs))
    return {"n": len(diffs), "mean": mean, "median": _median(diffs), "ci95_half_width": ci}


def _contrasts(cells: list[dict[str, Any]]) -> dict[str, Any]:
    by_hull_lane: dict[tuple[str, str], dict[int, dict[str, float | None]]] = {}
    for payload in cells:
        key = (str(payload["hull"]), str(payload["lane"]))
        by_hull_lane.setdefault(key, {})[int(payload["seed"])] = _cell_metrics(payload)
    out: dict[str, Any] = {}
    hulls = sorted({hull for hull, _lane in by_hull_lane})
    for hull in hulls:
        lanes = {lane for h, lane in by_hull_lane if h == hull}
        row: dict[str, Any] = {}
        if {"N", "E"} <= lanes:
            row["N_minus_E"] = {
                name: _paired_diffs(by_hull_lane[(hull, "N")], by_hull_lane[(hull, "E")], name)
                for name in ("retained_final", "b_v_h", "auc_sum", "peak_concentration")
            }
        if "P" in lanes and "N" in lanes:
            row["P_minus_N"] = {
                name: _paired_diffs(by_hull_lane[(hull, "P")], by_hull_lane[(hull, "N")], name)
                for name in ("retained_final", "b_v_h", "auc_sum", "peak_concentration")
            }
        if row:
            out[hull] = row
    return out


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return float(ordered[idx])


def _pilot_gate(
    cells: list[dict[str, Any]], field_cache: dict[str, Any] | None,
    array_wall_clock_minutes: float | None, design: dict[str, Any],
) -> dict[str, Any]:
    pilot = design.get("pilot") or {}
    hull = str(pilot.get("hull") or "missouri_bb63")
    lane = str(pilot.get("lane") or "E")
    rows = [p for p in cells if p.get("hull") == hull and p.get("lane") == lane]
    thresholds = design.get("thresholds") or {}
    checks: dict[str, Any] = {}
    checks["cell_count"] = len(rows)
    checks["blocked_engine_fallback_count"] = sum(
        1 for p in rows if "BLOCKED" in str(p.get("field_source") or "").upper()
    )
    field_seconds = None
    if field_cache:
        field = ((field_cache.get("fields") or {}).get(f"{hull}:{lane}") or {})
        field_seconds = field.get("field_seconds")
    checks["commissioned_field_solve_seconds"] = field_seconds
    checks["trajectory_wall_p95_seconds"] = _percentile(
        [float((p.get("timing") or {}).get("trajectory_seconds") or 0.0) for p in rows], 0.95,
    )
    checks["array_wall_clock_minutes"] = array_wall_clock_minutes
    checks["estimated_cpu_hours"] = (
        None if field_seconds is None else sum(
            float((p.get("timing") or {}).get("trajectory_seconds") or 0.0) for p in rows
        ) / 3600.0 + float(field_seconds) / 3600.0
    )
    checks["peak_rss_mib"] = max(
        [float((p.get("timing") or {}).get("peak_rss_mib") or 0.0) for p in rows] or [0.0]
    )
    checks["artifact_bytes_total"] = None
    audit_names = ("dropped_endpoint_count", "unknown_real_zone_count", "alias_collision_count")
    checks.update({
        name: max([int(((p.get("field_audit") or {}).get(name)) or 0) for p in rows] or [0])
        for name in audit_names
    })
    expected_cells = len(pilot.get("seeds") or [])
    checks["expected_cell_count"] = expected_cells
    checks["seeds_complete"] = len(rows) == expected_cells
    limits = {
        "blocked_engine_fallback_count": thresholds.get("blocked_engine_fallback_count", 0),
        "commissioned_field_solve_seconds": thresholds.get("commissioned_field_solve_seconds_max"),
        "trajectory_wall_p95_seconds": thresholds.get("trajectory_wall_p95_seconds_max"),
        "array_wall_clock_minutes": thresholds.get("array_wall_clock_minutes_max"),
        "estimated_cpu_hours": thresholds.get("cpu_hours_max"),
        "peak_rss_mib": thresholds.get("peak_rss_mib_max"),
        "artifact_bytes_total": thresholds.get("artifact_bytes_max"),
        "dropped_endpoint_count": thresholds.get("dropped_endpoint_count", 0),
        "unknown_real_zone_count": thresholds.get("unknown_real_zone_count", 0),
        "alias_collision_count": thresholds.get("alias_collision_count", 0),
    }
    checks["limits"] = limits
    return {"hull": hull, "lane": lane, "checks": checks}


def _refresh_pilot_gate(pilot: dict[str, Any]) -> None:
    checks = pilot["checks"]
    limits = checks.get("limits") or {}
    passed = []
    for name, limit in limits.items():
        value = checks.get(name)
        if value is None or limit is None:
            passed.append(None)
        else:
            passed.append(value <= limit)
    checks["pass"] = passed
    if checks.get("seeds_complete") is not True:
        checks["go"] = False
    elif any(p is None for p in passed):
        checks["go"] = None
    else:
        checks["go"] = all(passed)


def build_report(
    cells: list[tuple[str, dict[str, Any], int]], campaign: dict[str, Any],
    design: dict[str, Any], field_cache: dict[str, Any] | None = None,
    array_wall_clock_minutes: float | None = None,
) -> dict[str, Any]:
    payloads = [payload for _key, payload, _size in cells]
    sizes = {(str(p["hull"]), str(p["lane"]), int(p["seed"])): size for _k, p, size in cells}
    pilot_cells = [p for p in payloads if p.get("hull") == (design.get("pilot") or {}).get("hull") and p.get("lane") == (design.get("pilot") or {}).get("lane")]
    pilot = _pilot_gate(payloads, field_cache, array_wall_clock_minutes, design)
    if pilot_cells:
        pilot["checks"]["artifact_bytes_total"] = sum(
            sizes.get((str(p["hull"]), str(p["lane"]), int(p["seed"])), 0) for p in pilot_cells
        )
        pilot["checks"]["limits"]["artifact_bytes_total"] = (design.get("thresholds") or {}).get("artifact_bytes_max")
    _refresh_pilot_gate(pilot)
    by_key = _group_payloads(payloads)
    return {
        "design_id": design.get("design_id"),
        "coverage": _coverage(payloads, campaign),
        "metrics_by_hull_lane": {
            f"{hull}:{lane}": _aggregate([_cell_metrics(p) for p in rows])
            for (hull, lane), rows in sorted(by_key.items())
        },
        "path_flow_by_hull_lane": {
            f"{hull}:{lane}": _path_flow_aggregate(rows)
            for (hull, lane), rows in sorted(by_key.items())
        },
        "paired_contrasts": _contrasts(payloads),
        "pilot_gate": pilot,
        "report_only_diagnostics": design.get("report_only_diagnostics") or [],
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['design_id']} readout",
        "",
        "## Coverage",
        f"- expected cells: {report['coverage']['expected_cells']}",
        f"- observed cells: {report['coverage']['observed_cells']}",
        f"- missing cells: {report['coverage']['missing_cells']}",
        "",
        "| hull | lane | expected | observed | missing |",
        "|---|---:|---:|---:|---|",
    ]
    for row in report["coverage"]["blocks"]:
        lines.append(f"| {row['hull']} | {row['lane']} | {row['expected']} | {row['observed']} | {len(row['missing_seeds'])} |")
    lines += ["", "## Metrics", "", "| hull:lane | cells | retained_final med | B_V med | AUC med | peak med |", "|---|---:|---:|---:|---:|---:|"]
    for key, row in report["metrics_by_hull_lane"].items():
        lines.append(
            f"| {key} | {row['cells']} | {_fmt((row['retained_final'] or {}).get('median'))} | "
            f"{_fmt((row['b_v_h'] or {}).get('median'))} | {_fmt((row['auc_sum'] or {}).get('median'))} | "
            f"{_fmt((row['peak_concentration'] or {}).get('median'))} |"
        )
    lines += ["", "## Path flow summaries", "", "| hull:lane | cells | paths | total flow m3/h | ducted flow m3/h |", "|---|---:|---:|---:|---:|"]
    for key, row in report["path_flow_by_hull_lane"].items():
        lines.append(
            f"| {key} | {row['cells']} | {_fmt(row.get('path_count'))} | "
            f"{_fmt(row.get('total_flow_m3h'))} | {_fmt(row.get('ducted_flow_m3h'))} |"
        )
    lines += ["", "## Paired contrasts", ""]
    for hull, contrasts in report["paired_contrasts"].items():
        for contrast_name, metrics in contrasts.items():
            for metric_name, stat in metrics.items():
                lines.append(f"- {hull} {contrast_name} {metric_name}: n={stat['n']} mean={_fmt(stat['mean'])} ci95={_fmt(stat['ci95_half_width'])}")
    lines += ["", "## Pilot gate", ""]
    checks = report["pilot_gate"]["checks"]
    for name, value in checks.items():
        if name in {"limits", "pass"}:
            continue
        lines.append(f"- {name}: {_fmt(value)}")
    lines.append(f"- go: {_fmt(checks.get('go'))}")
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
