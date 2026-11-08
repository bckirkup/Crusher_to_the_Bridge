#!/usr/bin/env python3
"""Phase 2 tracer cell worker for the CONTAM four-cruise contrasts.

One worker invocation either materializes the 32-field commissioned/committed
ContamX field cache locally (``field-cache``) or runs one paired-seed tracer
trajectory for a ``hull x lane x arm`` cell through the shared
``py_contam_bridge`` propagator (``trajectory``). Arms are
``tools/contam_fleet_compare.py`` op lists applied through ``_apply_arm_ops``
so the mutation is the same object the fleet comparison uses; every cell
records the ``edits`` log and the realized per-group settings. Batch
trajectory cells consume the uploaded cache and never need ContamX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.contamx_runner import find_contamx  # noqa: E402
from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import (  # noqa: E402
    ContamTransportEngine,
    is_plenum_zone,
)
from engines.sim_clock import SimClock  # noqa: E402
from tools.contam_fleet_compare import (  # noqa: E402
    _apply_arm_ops,
    _committed_prj_path,
    _contamx_field,
    _load_platform,
)

DESIGN_REL = "campaigns/contam/phase2_cruise_contrasts_01/design/phase2_cruise_contrasts_design.json"
SCHEMA_CELL = "contam_phase2_cruise_contrasts_cell_v1"
SCHEMA_CACHE = "contam_phase2_cruise_contrasts_field_cache_v1"
CONCENTRATION_FLOOR_PER_M3 = 1e-9
FLOW_EPSILON_M3H = 1e-12
TOP_RECEPTOR_COUNT = 5
DESIGN_TRACER_MASS = 1_000_000.0
DESIGN_DECAY_RATE = 0.0
DESIGN_FILTER_EFFICIENCY = 0.5
DESIGN_OA_FRACTION = 0.2
LANES = ("N", "E", "P")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _design_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _load_design(raw: str) -> dict[str, Any]:
    return _load_json(_design_path(raw))


def _zone_ids(spatial: dict[str, Any]) -> list[str]:
    return [str(zone["id"]) for zone in spatial.get("zones") or []]


def _zone_volumes(spatial: dict[str, Any]) -> dict[str, float]:
    return {
        str(zone["id"]): float(zone.get("volume_m3") or 0.0)
        for zone in spatial.get("zones") or []
    }


def _seed_source(
    design: dict[str, Any], hull: str, seed: int,
) -> tuple[str, str, str, int]:
    grid = design["seed_mapping"]["grid"].get(str(seed), {}).get(hull)
    if grid is None:
        raise SystemExit(f"seed {seed} has no frozen mapping for {hull}")
    pool = design["source_pools"][hull]["pool"]
    index = int(grid["pool_index"])
    item = pool[index]
    return str(item["id"]), str(grid["timing_pattern"]), str(item["category"]), index


def _clock(epoch_hours: float) -> SimClock:
    return SimClock(epoch_duration_hours=float(epoch_hours), mode="hours")


# ── arms ─────────────────────────────────────────────────────────────────


def _arm_spec(design: dict[str, Any], arm: str) -> dict[str, Any]:
    spec = (design.get("arms") or {}).get(arm)
    if spec is None:
        raise SystemExit(f"unknown arm {arm!r}; frozen arms: {sorted(design.get('arms') or {})}")
    return spec


def _check_lane_arm(design: dict[str, Any], lane: str, arm: str) -> None:
    if lane == "P" and arm not in (design.get("p_lane_arms") or ["baseline"]):
        raise SystemExit(
            f"lane P cannot represent the JSON-only mutation of arm {arm!r}; "
            "P is baseline-only (manifest §2.1)"
        )


def _group_rows(airflow: dict[str, Any]) -> list[dict[str, Any]]:
    default_duty = float(airflow.get("hvac_duty", 1.0))
    default_oa = float(airflow.get("oa_fraction", DESIGN_OA_FRACTION))
    rows = []
    for group in airflow.get("hvac_zones") or []:
        rows.append({
            "id": str(group.get("id") or ""),
            "ach": float(group.get("ach") or 0.0),
            "hvac_duty": float(group.get("hvac_duty", default_duty)),
            "oa_fraction": float(group.get("oa_fraction", default_oa)),
        })
    return rows


def _realized_groups(
    baseline: dict[str, Any], mutated: dict[str, Any],
) -> dict[str, Any]:
    before = {row["id"]: row for row in _group_rows(baseline)}
    after = _group_rows(mutated)
    changed = []
    supply_changed = 0
    duty0_changed = 0
    for row in after:
        prior = before.get(row["id"], row)
        if row != prior:
            changed.append(row["id"])
            if prior["hvac_duty"] > 0.0:
                supply_changed += 1
            else:
                duty0_changed += 1
    return {
        "groups_total": len(after),
        "supply_groups": sum(1 for row in after if row["hvac_duty"] > 0.0),
        "duty0_groups": sum(1 for row in after if row["hvac_duty"] <= 0.0),
        "groups_changed": len(changed),
        "supply_groups_changed": supply_changed,
        "duty0_groups_changed": duty0_changed,
        "groups_unchanged": len(after) - len(changed),
        "changed_group_ids": changed,
        "groups": after,
    }


def _dc04_matched_removal(
    baseline: dict[str, Any], arm_spec: dict[str, Any], filter_efficiency: float,
) -> dict[str, Any] | None:
    """r_low = 1 - alpha(1 - r_base) per supply group; fail closed outside [0, 1]."""
    alpha = float(arm_spec.get("turnover_factor", 1.0))
    if alpha == 1.0:
        return None
    r_low = []
    for row in _group_rows(baseline):
        if row["hvac_duty"] <= 0.0:
            continue
        r_base = (1.0 - row["oa_fraction"]) * (1.0 - filter_efficiency)
        r_low.append(1.0 - alpha * (1.0 - r_base))
    feasible = bool(r_low) and all(0.0 <= value <= 1.0 for value in r_low)
    result = {
        "alpha": alpha,
        "supply_groups": len(r_low),
        "r_low_min": min(r_low) if r_low else None,
        "r_low_max": max(r_low) if r_low else None,
        "feasible": feasible,
    }
    if not feasible:
        raise SystemExit(
            f"DC04 matched-removal infeasible: r_low outside [0, 1] "
            f"(min={result['r_low_min']}, max={result['r_low_max']}); never clip"
        )
    return result


def _apply_arm(
    design: dict[str, Any], airflow: dict[str, Any], volumes: dict[str, float],
    arm: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Mutated airflow plus the arm record (ops, edits, engine args, realized groups)."""
    spec = _arm_spec(design, arm)
    ops = list(spec.get("ops") or [])
    mutated, applied = _apply_arm_ops(airflow, ops, volumes)
    engine_args = dict(applied["engine_args"])
    filter_efficiency = float(engine_args.get("filter_efficiency", DESIGN_FILTER_EFFICIENCY))
    oa_fraction = float(engine_args.get("oa_fraction", airflow.get("oa_fraction", DESIGN_OA_FRACTION)))
    record = {
        "id": arm,
        "code": spec.get("code"),
        "ops": ops,
        "edits": list(applied["edits"]),
        "engine_args": engine_args,
        "filter_efficiency": filter_efficiency,
        "oa_fraction": oa_fraction,
        "declared_gain_r": spec.get("declared_gain_r"),
        "realized_gain_r_supply": _supply_gains(mutated, filter_efficiency),
        "realized_groups": _realized_groups(airflow, mutated),
        "dc04_matched_removal": _dc04_matched_removal(airflow, spec, filter_efficiency),
    }
    return mutated, record


def _supply_gains(airflow: dict[str, Any], filter_efficiency: float) -> list[float]:
    gains = {
        round((1.0 - row["oa_fraction"]) * (1.0 - filter_efficiency), 12)
        for row in _group_rows(airflow) if row["hvac_duty"] > 0.0
    }
    return sorted(gains)


# ── engines ──────────────────────────────────────────────────────────────


def _native_engine(
    spatial: dict[str, Any], airflow: dict[str, Any], epoch_hours: float,
    filter_efficiency: float = DESIGN_FILTER_EFFICIENCY,
) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial,
        airflow,
        filter_efficiency=filter_efficiency,
        natural_decay_rate=DESIGN_DECAY_RATE,
        clock=_clock(epoch_hours),
    )


def _contamx_engine(
    spatial: dict[str, Any], field: dict[str, Any], epoch_hours: float,
    filter_efficiency: float, oa_fraction: float,
) -> ContamXTransportEngine:
    entries = field["entries"]
    flows = {int(key): float(value) for key, value in field["flows"].items()}
    return ContamXTransportEngine(
        spatial,
        entries,
        flows,
        filter_efficiency=filter_efficiency,
        natural_decay_rate=DESIGN_DECAY_RATE,
        path_map_entries=entries,
        oa_fraction=oa_fraction,
        clock=_clock(epoch_hours),
    )


def _special_endpoint(zone_id: str, real_ids: set[str]) -> bool:
    return (
        zone_id in real_ids
        or zone_id == "ambient"
        or zone_id.startswith("ahs")
        or is_plenum_zone(zone_id)
    )


def _blank_audit() -> dict[str, Any]:
    return {
        "field_source": "native_layout",
        "entries_total": 0,
        "flows_total": 0,
        "skipped_kind_count": 0,
        "zero_flow_count": 0,
        "dropped_endpoint_count": 0,
        "unknown_real_zone_count": 0,
        "alias_collision_count": 0,
        "duplicate_path_nr_count": 0,
    }


def _field_audit(
    engine: Any, field: dict[str, Any] | None, real_ids: set[str],
) -> dict[str, Any]:
    if field is None:
        return _blank_audit()
    entries = list(field.get("entries") or [])
    flows = {int(key): float(value) for key, value in field.get("flows", {}).items()}
    nodes = set(engine.zone_nodes)
    counts = {"skipped": 0, "zero_flow": 0, "dropped": 0, "unknown": 0, "alias": 0}
    for entry in entries:
        src = str(entry.get("from_zone") or "")
        dst = str(entry.get("to_zone") or "")
        kind = str(entry.get("kind") or "")
        flow = flows.get(int(entry.get("path_nr", 0)), 0.0)
        if src == dst and src != "ambient" and not src.startswith("ahs"):
            counts["alias"] += 1
        counts["unknown"] += int(not _special_endpoint(src, real_ids))
        counts["unknown"] += int(not _special_endpoint(dst, real_ids))
        if kind.startswith("ahs_") or kind == "envelope_leak":
            counts["skipped"] += 1
            continue
        if abs(flow) < FLOW_EPSILON_M3H:
            counts["zero_flow"] += 1
            continue
        a, b = (src, dst) if flow > 0 else (dst, src)
        if a not in nodes or b not in nodes:
            counts["dropped"] += 1
    path_nrs = [int(entry.get("path_nr", 0)) for entry in entries]
    return {
        "field_source": "contamx_solver",
        "entries_total": len(entries),
        "flows_total": len(flows),
        "skipped_kind_count": counts["skipped"],
        "zero_flow_count": counts["zero_flow"],
        "dropped_endpoint_count": counts["dropped"],
        "unknown_real_zone_count": counts["unknown"],
        "alias_collision_count": counts["alias"],
        "duplicate_path_nr_count": len(path_nrs) - len(set(path_nrs)),
    }


def _path_flow_summary(engine: Any) -> dict[str, Any]:
    by_type: dict[str, dict[str, float]] = {}
    total = 0.0
    ducted_total = 0.0
    for path in engine.airflow_paths:
        path_type = str(getattr(path, "path_type", "unknown") or "unknown")
        flow = float(getattr(path, "flow_rate_m3h", 0.0) or 0.0)
        row = by_type.setdefault(path_type, {"count": 0.0, "flow_m3h": 0.0, "ducted_flow_m3h": 0.0})
        row["count"] += 1.0
        row["flow_m3h"] += flow
        total += flow
        if bool(getattr(path, "is_hvac_ducted", False)):
            row["ducted_flow_m3h"] += flow
            ducted_total += flow
    return {
        "path_count": len(engine.airflow_paths),
        "total_flow_m3h": total,
        "ducted_flow_m3h": ducted_total,
        "by_path_type": {
            key: {name: round(value, 6) for name, value in row.items()}
            for key, row in sorted(by_type.items())
        },
    }


def _ahs_flow_table(field: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Realized per-AHS flows from the solved E/P field (DC05 realized-vs-declared)."""
    if field is None:
        return []
    flows = {int(key): float(value) for key, value in field.get("flows", {}).items()}
    table: dict[int, dict[str, Any]] = {}
    for entry in field.get("entries") or []:
        kind = str(entry.get("kind") or "")
        if not kind.startswith("ahs_"):
            continue
        ahs_nr = int(entry.get("ahs_nr") or 0)
        row = table.setdefault(ahs_nr, {"ahs_nr": ahs_nr, "declared_oa_fraction": entry.get("declared_oa_fraction")})
        row[f"{kind}_m3h"] = round(row.get(f"{kind}_m3h", 0.0) + abs(flows.get(int(entry.get("path_nr", 0)), 0.0)), 6)
    return [table[key] for key in sorted(table)]


# ── trajectory ───────────────────────────────────────────────────────────


def _sig(value: float, digits: int = 6) -> float:
    if not math.isfinite(value):
        return value
    return float(f"{value:.{digits}g}")


def _initial_mass(zone_ids: list[str], source_zone: str, timing: str) -> dict[str, float]:
    mass = dict.fromkeys(zone_ids, 0.0)
    mass[source_zone] = DESIGN_TRACER_MASS if timing == "t0_pulse" else DESIGN_TRACER_MASS / 2.0
    return mass


def _blank_zone_stats(volumes: dict[str, float]) -> dict[str, dict[str, float]]:
    return {
        zone_id: {
            "volume_m3": _sig(volume),
            "final_mass": 0.0,
            "peak_concentration_per_m3": 0.0,
            "peak_epoch": -1,
            "auc_concentration_per_m3_h": 0.0,
            "final_concentration_per_m3": 0.0,
            "time_above_floor_epochs": 0,
            "first_above_floor_epoch": -1,
        }
        for zone_id, volume in volumes.items()
    }


def _observe_epoch(
    mass: dict[str, float], volumes: dict[str, float], stats: dict[str, dict[str, float]],
    epoch: int, epoch_hours: float,
) -> float:
    total_mass = 0.0
    for zone_id, zone_mass in mass.items():
        volume = volumes.get(zone_id, 0.0)
        concentration = zone_mass / volume if volume > 0.0 else 0.0
        row = stats[zone_id]
        row["final_mass"] = _sig(zone_mass)
        row["final_concentration_per_m3"] = _sig(concentration)
        row["auc_concentration_per_m3_h"] += concentration * epoch_hours
        if concentration > row["peak_concentration_per_m3"]:
            row["peak_concentration_per_m3"] = _sig(concentration)
            row["peak_epoch"] = epoch
        if concentration >= CONCENTRATION_FLOOR_PER_M3:
            row["time_above_floor_epochs"] += 1
            if row["first_above_floor_epoch"] < 0:
                row["first_above_floor_epoch"] = epoch
        total_mass += zone_mass
    return total_mass


def _run_trajectory(
    engine: Any, zone_ids: list[str], volumes: dict[str, float],
    source_zone: str, timing: str, epochs: int, epoch_hours: float,
) -> dict[str, Any]:
    mass = _initial_mass(zone_ids, source_zone, timing)
    stats = _blank_zone_stats(volumes)
    retained: list[float] = []
    for epoch in range(epochs):
        mass = engine.transport_step(mass, natural_decay_rate=DESIGN_DECAY_RATE)
        mass = {zone_id: float(mass.get(zone_id, 0.0)) for zone_id in zone_ids}
        if timing == "t0_t1_split" and epoch == 0:
            mass[source_zone] += DESIGN_TRACER_MASS / 2.0
        total_mass = _observe_epoch(mass, volumes, stats, epoch, epoch_hours)
        retained.append(_sig(total_mass / DESIGN_TRACER_MASS))
    return _trajectory_metrics(stats, retained, source_zone, epoch_hours)


def _enrich_zone_stats(
    stats: dict[str, dict[str, float]], epoch_hours: float,
) -> dict[str, dict[str, Any]]:
    zone_stats = {}
    for zone_id, row in stats.items():
        enriched = {
            key: _sig(value) if isinstance(value, float) else value
            for key, value in row.items()
        }
        peak_epoch = int(row["peak_epoch"])
        first_floor_epoch = int(row["first_above_floor_epoch"])
        enriched["time_to_peak_h"] = (
            None if peak_epoch < 0 else _sig((peak_epoch + 1) * epoch_hours)
        )
        enriched["first_above_floor_h"] = (
            None if first_floor_epoch < 0 else _sig((first_floor_epoch + 1) * epoch_hours)
        )
        zone_stats[zone_id] = enriched
    return zone_stats


def _trajectory_metrics(
    stats: dict[str, dict[str, float]], retained: list[float],
    source_zone: str, epoch_hours: float,
) -> dict[str, Any]:
    zone_stats = _enrich_zone_stats(stats, epoch_hours)
    b_v = sum(
        row["volume_m3"] * row["auc_concentration_per_m3_h"]
        for row in stats.values()
    ) / DESIGN_TRACER_MASS
    source_auc = stats[source_zone]["auc_concentration_per_m3_h"]
    contrasts = _source_contrasts(stats, source_zone, source_auc)
    peak_zone, peak_row = max(stats.items(), key=lambda item: item[1]["peak_concentration_per_m3"])
    peak_epoch = int(peak_row["peak_epoch"])
    return {
        "retained_fraction_curve": retained,
        "volume_weighted_concentration_burden_h": _sig(b_v),
        "concentration_auc_sum_per_m3_h": _sig(sum(row["auc_concentration_per_m3_h"] for row in stats.values())),
        "peak_concentration_per_m3": peak_row["peak_concentration_per_m3"],
        "peak_concentration_zone": peak_zone,
        "peak_concentration_epoch": peak_epoch,
        "peak_concentration_hour": None if peak_epoch < 0 else _sig((peak_epoch + 1) * epoch_hours),
        "source_zone": source_zone,
        "source_zone_final_mass": stats[source_zone]["final_mass"],
        "source_zone_auc_concentration_per_m3_h": _sig(source_auc),
        "top_receptor_contrasts": contrasts,
        "zone_stats": zone_stats,
    }


def _source_contrasts(
    stats: dict[str, dict[str, float]], source_zone: str, source_auc: float,
) -> list[dict[str, Any]]:
    if source_auc <= CONCENTRATION_FLOOR_PER_M3:
        return []
    source_peak = stats[source_zone]["peak_concentration_per_m3"]
    rows = []
    for zone_id, row in stats.items():
        if zone_id == source_zone:
            continue
        rows.append({
            "zone_id": zone_id,
            "auc_ratio_to_source": _sig(row["auc_concentration_per_m3_h"] / source_auc),
            "peak_ratio_to_source": _sig(row["peak_concentration_per_m3"] / source_peak) if source_peak > 0 else None,
            "auc_concentration_per_m3_h": row["auc_concentration_per_m3_h"],
        })
    rows.sort(key=lambda item: item["auc_ratio_to_source"], reverse=True)
    return rows[:TOP_RECEPTOR_COUNT]


def _rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ── field cache ──────────────────────────────────────────────────────────


def _cache_key(hull: str, lane: str, arm: str) -> str:
    return f"{hull}:{lane}:{arm}"


def _field_sha256(entries: list[dict[str, Any]], flows: dict[str, float]) -> str:
    blob = json.dumps({"entries": entries, "flows": flows}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _solve_field(
    design: dict[str, Any], hull: str, lane: str, arm: str, tmp_root: str, binary: str,
) -> dict[str, Any]:
    _check_lane_arm(design, lane, arm)
    spatial, airflow = _load_platform(hull)
    volumes = _zone_volumes(spatial)
    mutated, arm_record = _apply_arm(design, airflow, volumes, arm)
    prj_rel = None if lane == "E" else _committed_prj_path(hull)
    if lane == "P" and not (ROOT / prj_rel).is_file():
        raise SystemExit(f"lane P requested for {hull}, but {prj_rel} is absent")
    started = time.perf_counter()
    field = _contamx_field(
        spatial,
        mutated,
        tmp_dir=tempfile.mkdtemp(dir=tmp_root),
        binary=binary,
        prj_rel=prj_rel,
        filter_efficiency=arm_record["filter_efficiency"],
    )
    flows = {str(key): float(value) for key, value in field["flows"].items()}
    return {
        "hull": hull,
        "lane": lane,
        "arm": arm,
        "ops": arm_record["ops"],
        "edits": arm_record["edits"],
        "filter_efficiency": arm_record["filter_efficiency"],
        "oa_fraction": arm_record["oa_fraction"],
        "realized_groups": arm_record["realized_groups"]["groups"],
        "entries": field["entries"],
        "flows": flows,
        "field_sha256": _field_sha256(field["entries"], flows),
        "field_seconds": time.perf_counter() - started,
    }


def _binary_sha256(binary: str) -> str:
    return hashlib.sha256(Path(binary).read_bytes()).hexdigest()


def _planned_fields(design: dict[str, Any], only: list[str] | None) -> list[dict[str, Any]]:
    plan = design["execution"]["field_cache_prestage"]["fields"]
    if not only:
        return list(plan)
    wanted = set(only)
    chosen = [row for row in plan if row["key"] in wanted]
    missing = wanted - {row["key"] for row in chosen}
    if missing:
        raise SystemExit(f"--only names fields outside the frozen plan: {sorted(missing)}")
    return chosen


def _phase1_control(
    fields: dict[str, Any], design: dict[str, Any], phase1_cache: str | None,
) -> dict[str, Any] | None:
    """Report-only byte comparison of the reusable expedition fields with Phase 1."""
    prestage = design["execution"]["field_cache_prestage"]
    if not phase1_cache:
        return None
    doc = _read_cache(phase1_cache)
    rows = []
    for key in prestage["phase1_reusable_fields"]:
        hull, lane, _arm = key.split(":")
        ours = fields.get(key)
        theirs = (doc.get("fields") or {}).get(f"{hull}:{lane}")
        if ours is None or theirs is None:
            rows.append({"key": key, "compared": False})
            continue
        theirs_sha = _field_sha256(theirs["entries"], {str(k): float(v) for k, v in theirs["flows"].items()})
        rows.append({"key": key, "compared": True, "identical": theirs_sha == ours["field_sha256"]})
    return {"phase1_cache": phase1_cache, "fields": rows}


def run_field_cache(
    design: dict[str, Any], out_dir: Path, binary: str | None,
    only: list[str] | None = None, phase1_cache: str | None = None,
) -> Path:
    if binary is None:
        raise SystemExit("ContamX binary unavailable; field-cache requires ContamX")
    expected_sha = design["execution"]["field_cache_prestage"]["contamx"]["binary_sha256"]
    binary_sha = _binary_sha256(binary)
    if binary_sha != expected_sha:
        raise SystemExit(f"ContamX binary SHA256 {binary_sha} != frozen {expected_sha}")
    planned = _planned_fields(design, only)
    fields: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="contam_phase2_fields_") as tmp_root:
        for row in planned:
            solved = _solve_field(design, row["hull"], row["lane"], row["arm"], tmp_root, binary)
            fields[_cache_key(row["hull"], row["lane"], row["arm"])] = solved
    payload = {
        "schema": SCHEMA_CACHE,
        "design_id": design["design_id"],
        "partial": bool(only),
        "planned_field_count": len(design["execution"]["field_cache_prestage"]["fields"]),
        "filter_efficiency_baseline": DESIGN_FILTER_EFFICIENCY,
        "natural_decay_rate": DESIGN_DECAY_RATE,
        "contamx": {
            "binary": str(binary),
            "binary_sha256": binary_sha,
            "version": design["execution"]["field_cache_prestage"]["contamx"]["version"],
        },
        "max_field_seconds": max((f["field_seconds"] for f in fields.values()), default=0.0),
        "phase1_control": _phase1_control(fields, design, phase1_cache),
        "fields": fields,
    }
    artifact = out_dir / "field_cache.json"
    _write_json(artifact, payload)
    print(f"WROTE {artifact} fields={len(fields)} partial={bool(only)}")
    return artifact


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise SystemExit(f"field cache URI must be s3://..., got {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/")


def _read_cache(cache: str) -> dict[str, Any]:
    if cache.startswith("s3://"):
        import boto3

        bucket, key = _parse_s3_uri(cache)
        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
        return json.loads(body)
    return _load_json(Path(cache))


def _field_from_cache(
    cache: str, hull: str, lane: str, arm: str, arm_record: dict[str, Any],
) -> dict[str, Any]:
    doc = _read_cache(cache)
    key = _cache_key(hull, lane, arm)
    field = (doc.get("fields") or {}).get(key)
    if field is None:
        raise SystemExit(
            f"field cache {cache} has no {key}; run and upload the local "
            "field-cache prestage first"
        )
    _check_field_matches_arm(field, key, arm_record)
    return field


def _check_field_matches_arm(field: dict[str, Any], key: str, arm_record: dict[str, Any]) -> None:
    """A cached field is usable only if it was solved under this arm's dependencies."""
    if field.get("ops") != arm_record["ops"]:
        raise SystemExit(f"stale field {key}: cached ops {field.get('ops')} != arm ops {arm_record['ops']}")
    if float(field.get("filter_efficiency", -1.0)) != arm_record["filter_efficiency"]:
        raise SystemExit(f"stale field {key}: filter efficiency at export differs from the arm")
    if field.get("realized_groups") != arm_record["realized_groups"]["groups"]:
        raise SystemExit(f"stale field {key}: realized per-group settings differ from the arm")


def _load_field(
    design: dict[str, Any], hull: str, lane: str, arm: str, arm_record: dict[str, Any],
    args: argparse.Namespace, tmp_root: str,
) -> tuple[dict[str, Any] | None, float, str]:
    if lane == "N":
        return None, 0.0, "native_layout"
    cache = args.field_cache_uri or args.field_cache_path
    if cache:
        started = time.perf_counter()
        field = _field_from_cache(cache, hull, lane, arm, arm_record)
        return field, time.perf_counter() - started, "field_cache"
    if not args.inline_field:
        raise SystemExit("E/P lanes require --field-cache-uri/--field-cache-path or --inline-field")
    binary = args.binary or find_contamx()
    if binary is None:
        raise SystemExit("ContamX binary unavailable and --inline-field was requested")
    started = time.perf_counter()
    field = _solve_field(design, hull, lane, arm, tmp_root, binary)
    return field, time.perf_counter() - started, "inline_solve"


def _build_engine(
    spatial: dict[str, Any], mutated: dict[str, Any], lane: str,
    field: dict[str, Any] | None, arm_record: dict[str, Any], epoch_hours: float,
) -> Any:
    if lane == "N":
        return _native_engine(spatial, mutated, epoch_hours, arm_record["filter_efficiency"])
    if field is None:
        raise SystemExit(f"lane {lane} has no ContamX field")
    return _contamx_engine(
        spatial, field, epoch_hours, arm_record["filter_efficiency"], arm_record["oa_fraction"],
    )


def run_trajectory(
    design: dict[str, Any], hull: str, lane: str, arm: str, seed: int,
    epochs: int, epoch_hours: float, out_dir: Path, args: argparse.Namespace,
) -> Path:
    if hull not in design["hulls"]:
        raise SystemExit(f"unknown hull {hull!r}")
    if lane not in LANES:
        raise SystemExit(f"unknown lane {lane!r}")
    _check_lane_arm(design, lane, arm)
    source_zone, timing, category, pool_index = _seed_source(design, hull, seed)
    started = time.perf_counter()
    rss_start = _rss_mib()
    spatial, airflow = _load_platform(hull)
    zone_ids = _zone_ids(spatial)
    volumes = _zone_volumes(spatial)
    mutated, arm_record = _apply_arm(design, airflow, volumes, arm)
    with tempfile.TemporaryDirectory(prefix="contam_phase2_cell_") as tmp_root:
        field, field_seconds, field_source = _load_field(
            design, hull, lane, arm, arm_record, args, tmp_root,
        )
        engine = _build_engine(spatial, mutated, lane, field, arm_record, epoch_hours)
        if source_zone not in set(zone_ids):
            raise SystemExit(f"source zone {source_zone!r} is not a real zone for {hull}")
        metrics = _run_trajectory(engine, zone_ids, volumes, source_zone, timing, epochs, epoch_hours)
    real_ids = set(zone_ids)
    payload = {
        "schema": SCHEMA_CELL,
        "design_id": design["design_id"],
        "hull": hull,
        "lane": lane,
        "arm": arm,
        "seed": seed,
        "source_zone": source_zone,
        "source_category": category,
        "pool_index": pool_index,
        "timing_pattern": timing,
        "epochs": epochs,
        "epoch_hours": epoch_hours,
        "tracer_mass": DESIGN_TRACER_MASS,
        "natural_decay_rate": DESIGN_DECAY_RATE,
        "filter_efficiency": arm_record["filter_efficiency"],
        "arm_record": arm_record,
        "metrics": metrics,
        "path_flow_summary": _path_flow_summary(engine),
        "ahs_flow_table": _ahs_flow_table(field),
        "field_audit": _field_audit(engine, field, real_ids),
        "field_source": field_source,
        "field_sha256": None if field is None else field.get("field_sha256"),
        "timing": {
            "trajectory_seconds": time.perf_counter() - started,
            "field_seconds": field_seconds,
            "peak_rss_mib": _rss_mib(),
            "rss_start_mib": rss_start,
        },
        "engine": {
            "class": type(engine).__name__,
            "filter_efficiency": float(engine.filter_efficiency),
            "natural_decay_rate": float(engine.natural_decay_rate),
            "zone_node_count": len(engine.zone_nodes),
            "airflow_path_count": len(engine.airflow_paths),
            "real_zone_count": len(zone_ids),
        },
    }
    payload["field_audit"]["field_source"] = field_source
    artifact = out_dir / f"cell_{seed}.json"
    _write_json(artifact, payload)
    print(f"WROTE {artifact}")
    return artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("field-cache", "trajectory"), required=True)
    parser.add_argument("--design", default=DESIGN_REL)
    parser.add_argument("--hull", default=None)
    parser.add_argument("--lane", choices=LANES, default=None)
    parser.add_argument("--arm", default="baseline")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--epoch-hours", type=float, default=1.0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--field-cache-uri", default=None)
    parser.add_argument("--field-cache-path", default=None)
    parser.add_argument("--inline-field", action="store_true")
    parser.add_argument("--binary", default=None)
    parser.add_argument(
        "--only", action="append", default=None,
        help="field-cache mode: restrict to these <hull>:<lane>:<arm> keys (local smoke; marks the cache partial)",
    )
    parser.add_argument("--phase1-field-cache", default=None,
                        help="field-cache mode: Phase 1 cache for the report-only byte comparison")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    design = _load_design(args.design)
    out_dir = Path(args.out)
    if args.mode == "field-cache":
        run_field_cache(
            design, out_dir, args.binary or find_contamx(),
            only=args.only, phase1_cache=args.phase1_field_cache,
        )
        return 0
    if not args.hull or not args.lane or args.seed is None:
        raise SystemExit("trajectory mode requires --hull, --lane, and --seed")
    run_trajectory(
        design, args.hull, args.lane, args.arm, args.seed, args.epochs,
        args.epoch_hours, out_dir, args,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
