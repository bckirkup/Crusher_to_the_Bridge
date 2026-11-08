#!/usr/bin/env python3
"""Phase 1 tracer cell worker for the CONTAM HVAC field panel.

One array child either materializes the commissioned/committed ContamX field
cache once (``field-cache``) or runs one paired-seed tracer trajectory through
the shared ``py_contam_bridge`` propagator (``trajectory``). The worker emits a
slim JSON artifact; full hourly frames stay out of the campaign prefix unless
the pilot readout later justifies them.
"""
from __future__ import annotations

import argparse
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
    _committed_prj_path,
    _contamx_field,
    _load_platform,
)

DESIGN_REL = "campaigns/contam/phase1_hvac_tracer_01/design/phase1_hvac_tracer_design.json"
SCHEMA_CELL = "contam_phase1_hvac_tracer_cell_v1"
SCHEMA_CACHE = "contam_phase1_hvac_tracer_field_cache_v1"
CONCENTRATION_FLOOR_PER_M3 = 1e-9
FLOW_EPSILON_M3H = 1e-12
TOP_RECEPTOR_COUNT = 5
DESIGN_TRACER_MASS = 1_000_000.0
DESIGN_DECAY_RATE = 0.0
DESIGN_FILTER_EFFICIENCY = 0.5


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


def _native_engine(
    spatial: dict[str, Any], airflow: dict[str, Any], epoch_hours: float,
) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial,
        airflow,
        filter_efficiency=DESIGN_FILTER_EFFICIENCY,
        natural_decay_rate=DESIGN_DECAY_RATE,
        clock=_clock(epoch_hours),
    )


def _contamx_engine(
    spatial: dict[str, Any], airflow: dict[str, Any], field: dict[str, Any],
    epoch_hours: float,
) -> ContamXTransportEngine:
    entries = field["entries"]
    flows = {int(key): float(value) for key, value in field["flows"].items()}
    return ContamXTransportEngine(
        spatial,
        entries,
        flows,
        filter_efficiency=DESIGN_FILTER_EFFICIENCY,
        natural_decay_rate=DESIGN_DECAY_RATE,
        path_map_entries=entries,
        oa_fraction=float(airflow.get("oa_fraction", 0.2)),
        clock=_clock(epoch_hours),
    )


def _special_endpoint(zone_id: str, real_ids: set[str]) -> bool:
    return (
        zone_id in real_ids
        or zone_id == "ambient"
        or zone_id.startswith("ahs")
        or is_plenum_zone(zone_id)
    )


def _field_audit(
    engine: Any, field: dict[str, Any] | None, real_ids: set[str],
) -> dict[str, Any]:
    if field is None:
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
    entries = list(field.get("entries") or [])
    flows = {int(key): float(value) for key, value in field.get("flows", {}).items()}
    skipped = 0
    zero_flow = 0
    dropped = 0
    unknown = 0
    alias = 0
    for entry in entries:
        src = str(entry.get("from_zone") or "")
        dst = str(entry.get("to_zone") or "")
        kind = str(entry.get("kind") or "")
        flow = flows.get(int(entry.get("path_nr", 0)), 0.0)
        if src == dst and src not in {"ambient"} and not src.startswith("ahs"):
            alias += 1
        if not _special_endpoint(src, real_ids):
            unknown += 1
        if not _special_endpoint(dst, real_ids):
            unknown += 1
        if kind.startswith("ahs_") or kind == "envelope_leak":
            skipped += 1
            continue
        if abs(flow) < FLOW_EPSILON_M3H:
            zero_flow += 1
            continue
        a, b = (src, dst) if flow > 0 else (dst, src)
        if a not in set(engine.zone_nodes) or b not in set(engine.zone_nodes):
            dropped += 1
    path_nrs = [int(entry.get("path_nr", 0)) for entry in entries]
    return {
        "field_source": "contamx_solver",
        "entries_total": len(entries),
        "flows_total": len(flows),
        "skipped_kind_count": skipped,
        "zero_flow_count": zero_flow,
        "dropped_endpoint_count": dropped,
        "unknown_real_zone_count": unknown,
        "alias_collision_count": alias,
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


def _trajectory_metrics(
    stats: dict[str, dict[str, float]], retained: list[float],
    source_zone: str, epoch_hours: float,
) -> dict[str, Any]:
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
    b_v = sum(
        row["volume_m3"] * row["auc_concentration_per_m3_h"]
        for row in stats.values()
    ) / DESIGN_TRACER_MASS
    source_auc = stats[source_zone]["auc_concentration_per_m3_h"]
    contrasts = _source_contrasts(stats, source_zone, source_auc)
    peak_zone, peak_row = max(stats.items(), key=lambda item: item[1]["peak_concentration_per_m3"])
    return {
        "retained_fraction_curve": retained,
        "volume_weighted_concentration_burden_h": _sig(b_v),
        "concentration_auc_sum_per_m3_h": _sig(sum(row["auc_concentration_per_m3_h"] for row in stats.values())),
        "peak_concentration_per_m3": peak_row["peak_concentration_per_m3"],
        "peak_concentration_zone": peak_zone,
        "peak_concentration_epoch": peak_row["peak_epoch"],
        "peak_concentration_hour": (
            None if int(peak_row["peak_epoch"]) < 0
            else _sig((int(peak_row["peak_epoch"]) + 1) * epoch_hours)
        ),
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
    rows = []
    for zone_id, row in stats.items():
        if zone_id == source_zone:
            continue
        rows.append({
            "zone_id": zone_id,
            "auc_ratio_to_source": _sig(row["auc_concentration_per_m3_h"] / source_auc),
            "peak_ratio_to_source": _sig(row["peak_concentration_per_m3"] / stats[source_zone]["peak_concentration_per_m3"]) if stats[source_zone]["peak_concentration_per_m3"] > 0 else None,
            "auc_concentration_per_m3_h": row["auc_concentration_per_m3_h"],
        })
    rows.sort(key=lambda item: item["auc_ratio_to_source"], reverse=True)
    return rows[:TOP_RECEPTOR_COUNT]


def _rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _solve_field(hull: str, lane: str, tmp_root: str, binary: str) -> dict[str, Any]:
    spatial, airflow = _load_platform(hull)
    prj_rel = None if lane == "E" else _committed_prj_path(hull)
    if lane == "P" and not (ROOT / prj_rel).is_file():
        raise SystemExit(f"lane P requested for {hull}, but {prj_rel} is absent")
    started = time.perf_counter()
    field = _contamx_field(
        spatial,
        airflow,
        tmp_dir=tempfile.mkdtemp(dir=tmp_root),
        binary=binary,
        prj_rel=prj_rel,
        filter_efficiency=DESIGN_FILTER_EFFICIENCY,
    )
    return {
        "hull": hull,
        "lane": lane,
        "entries": field["entries"],
        "flows": {str(key): float(value) for key, value in field["flows"].items()},
        "field_seconds": time.perf_counter() - started,
    }


def _cache_key(hull: str, lane: str) -> str:
    return f"{hull}:{lane}"


def run_field_cache(design: dict[str, Any], out_dir: Path, binary: str | None) -> Path:
    if binary is None:
        raise SystemExit("ContamX binary unavailable; field-cache requires ContamX")
    fields: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="contam_phase1_fields_") as tmp_root:
        for hull in design["hulls"]:
            lanes = ["E"] if hull == "fletcher_class_destroyer" else ["E", "P"]
            for lane in lanes:
                solved = _solve_field(hull, lane, tmp_root, binary)
                fields[_cache_key(hull, lane)] = solved
    payload = {
        "schema": SCHEMA_CACHE,
        "design_id": design["design_id"],
        "filter_efficiency": DESIGN_FILTER_EFFICIENCY,
        "natural_decay_rate": DESIGN_DECAY_RATE,
        "fields": fields,
    }
    artifact = out_dir / "field_cache.json"
    _write_json(artifact, payload)
    print(f"WROTE {artifact} fields={len(fields)}")
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


def _field_from_cache(cache: str, hull: str, lane: str) -> dict[str, Any]:
    doc = _read_cache(cache)
    key = _cache_key(hull, lane)
    field = (doc.get("fields") or {}).get(key)
    if field is None:
        raise SystemExit(f"field cache {cache} has no {key}; submit field_cache first")
    return field


def _load_field(
    hull: str, lane: str, args: argparse.Namespace, tmp_root: str,
) -> tuple[dict[str, Any] | None, float, str]:
    if lane == "N":
        return None, 0.0, "native_layout"
    cache = args.field_cache_uri or args.field_cache_path
    if cache:
        started = time.perf_counter()
        field = _field_from_cache(cache, hull, lane)
        return field, time.perf_counter() - started, "field_cache"
    if not args.inline_field:
        raise SystemExit("E/P lanes require --field-cache-uri/--field-cache-path or --inline-field")
    binary = args.binary or find_contamx()
    if binary is None:
        raise SystemExit("ContamX binary unavailable and --inline-field was requested")
    started = time.perf_counter()
    field = _solve_field(hull, lane, tmp_root, binary)
    return field, time.perf_counter() - started, "inline_solve"


def _build_engine(
    hull: str, lane: str, field: dict[str, Any] | None, epoch_hours: float,
) -> tuple[Any, dict[str, Any], dict[str, Any], list[str], dict[str, float]]:
    spatial, airflow = _load_platform(hull)
    zone_ids = _zone_ids(spatial)
    volumes = _zone_volumes(spatial)
    if lane == "N":
        engine = _native_engine(spatial, airflow, epoch_hours)
    else:
        if field is None:
            raise SystemExit(f"lane {lane} for {hull} has no ContamX field")
        engine = _contamx_engine(spatial, airflow, field, epoch_hours)
    return engine, spatial, airflow, zone_ids, volumes


def run_trajectory(
    design: dict[str, Any], hull: str, lane: str, seed: int,
    epochs: int, epoch_hours: float, out_dir: Path, args: argparse.Namespace,
) -> Path:
    if hull not in design["hulls"]:
        raise SystemExit(f"unknown hull {hull!r}")
    if lane not in {"N", "E", "P"}:
        raise SystemExit(f"unknown lane {lane!r}")
    source_zone, timing, category, pool_index = _seed_source(design, hull, seed)
    started = time.perf_counter()
    rss_start = _rss_mib()
    with tempfile.TemporaryDirectory(prefix="contam_phase1_cell_") as tmp_root:
        field, field_seconds, field_source = _load_field(hull, lane, args, tmp_root)
        engine, _spatial, _airflow, zone_ids, volumes = _build_engine(
            hull, lane, field, epoch_hours,
        )
        if source_zone not in set(zone_ids):
            raise SystemExit(f"source zone {source_zone!r} is not a real zone for {hull}")
        metrics = _run_trajectory(engine, zone_ids, volumes, source_zone, timing, epochs, epoch_hours)
    real_ids = set(zone_ids)
    payload = {
        "schema": SCHEMA_CELL,
        "design_id": design["design_id"],
        "hull": hull,
        "lane": lane,
        "seed": seed,
        "source_zone": source_zone,
        "source_category": category,
        "pool_index": pool_index,
        "timing_pattern": timing,
        "epochs": epochs,
        "epoch_hours": epoch_hours,
        "tracer_mass": DESIGN_TRACER_MASS,
        "natural_decay_rate": DESIGN_DECAY_RATE,
        "filter_efficiency": DESIGN_FILTER_EFFICIENCY,
        "metrics": metrics,
        "path_flow_summary": _path_flow_summary(engine),
        "field_audit": _field_audit(engine, field, real_ids),
        "field_source": field_source,
        "timing": {
            "trajectory_seconds": time.perf_counter() - started,
            "field_seconds": field_seconds,
            "peak_rss_mib": _rss_mib(),
            "rss_start_mib": rss_start,
        },
        "engine": {
            "class": type(engine).__name__,
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
    parser.add_argument("--lane", choices=("N", "E", "P"), default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--epoch-hours", type=float, default=1.0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--field-cache-uri", default=None)
    parser.add_argument("--field-cache-path", default=None)
    parser.add_argument("--inline-field", action="store_true")
    parser.add_argument("--binary", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    design = _load_design(args.design)
    out_dir = Path(args.out)
    if args.mode == "field-cache":
        run_field_cache(design, out_dir, args.binary or find_contamx())
        return 0
    if not args.hull or not args.lane or args.seed is None:
        raise SystemExit("trajectory mode requires --hull, --lane, and --seed")
    run_trajectory(
        design, args.hull, args.lane, args.seed, args.epochs,
        args.epoch_hours, out_dir, args,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
