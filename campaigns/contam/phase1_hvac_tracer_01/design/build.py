#!/usr/bin/env python3
"""Build the frozen Phase 1 CONTAM tracer campaign design artifacts.

The design is deterministic and anchor-free: source pools use only platform
metadata (zone type, volume, HVAC service, duty, and adjacency degree), and the
seed mapping is the manifest's paired-seed rule. Running this script rewrites
``design/phase1_hvac_tracer_design.json``, ``source_pools.json``, and the
campaign-root ``campaign.json`` from the six platform layouts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN_DIR = ROOT / "campaigns" / "contam" / "phase1_hvac_tracer_01"
DESIGN_PATH = CAMPAIGN_DIR / "design" / "phase1_hvac_tracer_design.json"
POOLS_PATH = CAMPAIGN_DIR / "source_pools.json"
CAMPAIGN_JSON_PATH = CAMPAIGN_DIR / "campaign.json"

HULLS = [
    "destroyer_baseline",
    "expedition_cruise_450",
    "fletcher_class_destroyer",
    "lexington_cv2",
    "saratoga_cv3",
    "missouri_bb63",
]
BUNDLED_HULLS = [hull for hull in HULLS if hull != "fletcher_class_destroyer"]
LANES = ["N", "E", "P"]
PRIMARY_LANES = ["N", "E"]
SEEDS = list(range(1, 21))
EPOCHS = 12
EPOCH_HOURS = 1.0
TRACER_MASS = 1_000_000.0
NATURAL_DECAY_RATE = 0.0
FILTER_EFFICIENCY = 0.5

LARGE_VENUE_TYPES = {"Dining", "Free", "Cabin_Corridor", "Medical"}
CATEGORY_LIMITS = {"large_venue": 4, "sanitary_branch": 3, "remote_weak": 3}
CATEGORY_ORDER = ["large_venue", "sanitary_branch", "remote_weak"]

PILOT = {
    "hull": "missouri_bb63",
    "lane": "E",
    "seeds": SEEDS,
    "epochs": EPOCHS,
    "epoch_hours": EPOCH_HOURS,
    "vcpu": 1,
    "memory_mib": 2048,
    "field_cache_block": "field_cache",
    "trajectory_block": "missouri_bb63_e",
}

THRESHOLDS = {
    "blocked_engine_fallback_count": 0,
    "commissioned_field_solve_seconds_max": 30.0,
    "trajectory_wall_p95_seconds_max": 60.0,
    "array_wall_clock_minutes_max": 30.0,
    "cpu_hours_max": 1.0,
    "peak_rss_mib_max": 1792,
    "artifact_bytes_max": 25 * 1024 * 1024,
    "dropped_endpoint_count": 0,
    "unknown_real_zone_count": 0,
    "alias_collision_count": 0,
}

REPORT_ONLY = [
    "retained_fraction_curve_12h",
    "per_zone_concentration_stats",
    "source_to_receptor_contrasts",
    "path_type_flow_summaries",
    "wall_clock_and_rss_telemetry",
]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _platform_paths(hull: str) -> tuple[Path, Path]:
    base = ROOT / "data" / "platforms" / hull
    return base / "spatial_layout.json", base / "air_flow_paths.json"


def _volume(zone: dict[str, Any]) -> float:
    return float(zone.get("volume_m3") or 0.0)


def _occupancy(zone: dict[str, Any]) -> float:
    return float(zone.get("max_occupancy") or 0.0)


def _hvac_groups(airflow: dict[str, Any]) -> list[dict[str, Any]]:
    return list(airflow.get("hvac_zones") or [])


def _service_map(airflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    service: dict[str, dict[str, Any]] = {}
    for group in _hvac_groups(airflow):
        for room in group.get("rooms") or []:
            service.setdefault(str(room), group)
    return service


def _adjacency_degree(airflow: dict[str, Any], zone_ids: set[str]) -> dict[str, int]:
    degree = {zone_id: 0 for zone_id in zone_ids}
    for edge in airflow.get("adjacency") or []:
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if src in zone_ids:
            degree[src] += 1
        if dst in zone_ids:
            degree[dst] += 1
    return degree


def _zone_info(hull: str) -> dict[str, dict[str, Any]]:
    spatial_path, airflow_path = _platform_paths(hull)
    spatial = _load_json(spatial_path)
    airflow = _load_json(airflow_path)
    zone_ids = {str(zone["id"]) for zone in spatial.get("zones") or []}
    service = _service_map(airflow)
    degree = _adjacency_degree(airflow, zone_ids)
    default_duty = float(airflow.get("hvac_duty") or 1.0)
    info: dict[str, dict[str, Any]] = {}
    for zone in spatial.get("zones") or []:
        zone_id = str(zone["id"])
        group = service.get(zone_id)
        duty = default_duty
        group_id = ""
        if group is not None:
            group_id = str(group.get("id") or "")
            duty = float(group.get("hvac_duty", default_duty))
        info[zone_id] = {
            "id": zone_id,
            "type": str(zone.get("type") or ""),
            "volume_m3": _volume(zone),
            "occupancy": _occupancy(zone),
            "served": group is not None,
            "hvac_group_id": group_id,
            "hvac_duty": duty,
            "adjacency_degree": degree.get(zone_id, 0),
        }
    return info


def _remote_key(item: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
    _zone_id, info = item
    duty = info["hvac_duty"] if info["served"] else 1.0
    return (
        info["served"],
        info["adjacency_degree"],
        duty,
        info["volume_m3"],
        info["id"],
    )


def _large_key(item: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
    _zone_id, info = item
    return (-info["occupancy"], -info["volume_m3"], info["id"])


def _sanitary_key(item: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
    _zone_id, info = item
    return (-info["volume_m3"], info["id"])


def _take(
    candidates: list[tuple[str, dict[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    return [info for _zone_id, info in candidates[:limit]]


def _select_pool(info: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected: set[str] = set()
    remote = sorted(
        (
            (zone_id, zone_info)
            for zone_id, zone_info in info.items()
            if zone_info["type"] != "Sanitary"
            and (not zone_info["served"] or zone_info["adjacency_degree"] <= 1)
        ),
        key=_remote_key,
    )
    remote_pool = _take(remote, CATEGORY_LIMITS["remote_weak"])
    selected.update(item["id"] for item in remote_pool)

    sanitary = sorted(
        (
            (zone_id, zone_info)
            for zone_id, zone_info in info.items()
            if zone_info["type"] == "Sanitary" and zone_id not in selected
        ),
        key=_sanitary_key,
    )
    sanitary_pool = _take(sanitary, CATEGORY_LIMITS["sanitary_branch"])
    selected.update(item["id"] for item in sanitary_pool)

    large = sorted(
        (
            (zone_id, zone_info)
            for zone_id, zone_info in info.items()
            if zone_info["type"] in LARGE_VENUE_TYPES
            and zone_id not in selected
        ),
        key=_large_key,
    )
    large_pool = _take(large, CATEGORY_LIMITS["large_venue"])

    by_category = {
        "large_venue": large_pool,
        "sanitary_branch": sanitary_pool,
        "remote_weak": remote_pool,
    }
    pool: list[dict[str, Any]] = []
    for category in CATEGORY_ORDER:
        for item in by_category[category]:
            pool.append({"category": category, **item})
    return pool


def _source_pools() -> dict[str, dict[str, Any]]:
    pools: dict[str, dict[str, Any]] = {}
    for hull in HULLS:
        info = _zone_info(hull)
        pool = _select_pool(info)
        counts = {category: 0 for category in CATEGORY_ORDER}
        for item in pool:
            counts[item["category"]] += 1
        pools[hull] = {
            "pool": pool,
            "counts": counts,
            "zone_count": len(info),
        }
    return pools


def _seed_realization(seed: int, pool_length: int) -> dict[str, Any]:
    k = seed - 1
    index = (k // 2) % pool_length
    return {
        "seed": seed,
        "k": k,
        "timing_pattern": "t0_pulse" if k % 2 == 0 else "t0_t1_split",
        "pool_index": index,
    }


def _seed_grid(pool_lengths: dict[str, int]) -> dict[str, Any]:
    return {
        str(seed): {
            hull: _seed_realization(seed, pool_lengths[hull])
            for hull in HULLS
        }
        for seed in SEEDS
    }


def _lane_block_name(hull: str, lane: str) -> str:
    return f"{hull}_{lane.lower()}"


def _trajectory_blocks() -> dict[str, Any]:
    blocks: dict[str, Any] = {}
    for hull in HULLS:
        lanes = PRIMARY_LANES if hull == "fletcher_class_destroyer" else LANES
        for lane in lanes:
            name = _lane_block_name(hull, lane)
            blocks[name] = {
                "worker": "campaigns/contam/phase1_hvac_tracer_01/cell.py",
                "artifact": "cell_{seed}.json",
                "args": {
                    "mode": "trajectory",
                    "hull": hull,
                    "lane": lane,
                },
                "seeds": SEEDS,
            }
    return blocks


def _campaign_spec() -> dict[str, Any]:
    blocks = {
        "field_cache": {
            "worker": "campaigns/contam/phase1_hvac_tracer_01/cell.py",
            "artifact": "field_cache.json",
            "args": {"mode": "field_cache"},
            "seeds": [1],
        },
    }
    blocks.update(_trajectory_blocks())
    return {
        "name": "contam_phase1_hvac_tracer_01",
        "pathogen": "contam",
        "manifest": "campaigns/contam/phase1_hvac_tracer_01/design/phase1_hvac_tracer_design.json",
        "pathogen_id": None,
        "s3_prefix": "campaign/contam_phase1_hvac_tracer_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "contam-phase1-hvac-tracer-01",
        "epochs": EPOCHS,
        "epoch_hours": EPOCH_HOURS,
        "resources": {"vcpu": "1", "memory": "2048"},
        "readout": "campaigns/contam/phase1_hvac_tracer_01/readout.py",
        "blocks": blocks,
    }


def build_design() -> dict[str, Any]:
    source_pools = _source_pools()
    pool_lengths = {
        hull: len(payload["pool"]) for hull, payload in source_pools.items()
    }
    trajectory_cells = sum(
        len(block["seeds"])
        for block in _trajectory_blocks().values()
    )
    return {
        "design_id": "contam_phase1_hvac_tracer_01",
        "status": "frozen_before_first_cell",
        "manifest": "docs/proposals/contam_phase1_scope_manifest.md",
        "manifest_pr": 1172,
        "phase": "phase1_tracer_only_hvac_field_panel",
        "excluded": [
            "stochastic_agents",
            "pathogen_coupling",
            "epidemiological_constants",
            "vsp_park_attack_rate_anchors",
            "lane_s_stock_contamx_contaminant",
            "ship_x",
        ],
        "hulls": HULLS,
        "bundled_p_lane_hulls": BUNDLED_HULLS,
        "lanes": {
            "N": "native heuristic HVAC + passive/cross-zone flows",
            "E": "fresh commissioned ContamX export + AHS synthesis",
            "P": "committed contam/platform.prj + path_map.json baseline",
        },
        "tracer": {
            "mass_per_seed": TRACER_MASS,
            "normalization": "emitted_mass",
            "natural_decay_rate": NATURAL_DECAY_RATE,
            "filter_efficiency": FILTER_EFFICIENCY,
            "timing_patterns": {
                "t0_pulse": "1e6 at t=0h",
                "t0_t1_split": "500000 at t=0h and 500000 after first hourly step",
            },
        },
        "matrix": {
            "primary": "6 hulls x N/E x 20 paired seeds x 12 epochs x 1h",
            "primary_trajectories": 240,
            "p_contrast_trajectories": 100,
            "total_trajectories": 340,
            "hourly_steps": 4080,
            "seeds": SEEDS,
            "epochs": EPOCHS,
            "epoch_hours": EPOCH_HOURS,
        },
        "source_pool_rule": {
            "selection_order": ["remote_weak", "sanitary_branch", "large_venue"],
            "pool_order": CATEGORY_ORDER,
            "limits": CATEGORY_LIMITS,
            "remote_weak_candidates": "non-Sanitary and (HVAC-unserved or adjacency_degree <= 1)",
            "remote_weak_key": [
                "served ascending (unserved first)",
                "adjacency_degree ascending",
                "hvac_duty ascending (unserved duty=1.0)",
                "volume_m3 ascending",
                "zone_id ascending",
            ],
            "sanitary_branch_key": ["volume_m3 descending", "zone_id ascending"],
            "large_venue_key": [
                "max_occupancy descending (missing=0)",
                "volume_m3 descending",
                "zone_id ascending",
            ],
            "large_venue_types": sorted(LARGE_VENUE_TYPES),
            "metadata_only": True,
            "anchor_free": True,
            "fletcher_note": "N/E only; no committed contam bundle, P unavailable by design.",
        },
        "source_pools": source_pools,
        "seed_mapping": {
            "rule": "k=seed-1; timing=k mod 2; pool_index=(k//2) mod pool_length",
            "timing_codes": {"0": "t0_pulse", "1": "t0_t1_split"},
            "grid": _seed_grid(pool_lengths),
        },
        "execution": {
            "submit_path": "scripts/campaign submit contam/phase1_hvac_tracer_01 --block <block>",
            "field_cache_block": "field_cache",
            "field_cache_artifact": "campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json",
            "trajectory_blocks": len(_trajectory_blocks()),
            "trajectory_array_children": trajectory_cells,
            "field_cache_children": 1,
            "total_array_children": trajectory_cells + 1,
            "submit_order": [
                "field_cache",
                "missouri_bb63_e pilot/canary",
                "remaining blocks after user decision",
            ],
            "resources": {"vcpu": 1, "memory_mib": 2048},
            "aws_profile": "picard",
            "queue": "picard-campaign-queue",
        },
        "pilot": PILOT,
        "thresholds": THRESHOLDS,
        "acceptance_gates": {
            "geometry_seed_gate": "all source zones exist; seed mapping deterministic; paired seeds use identical source realization across lanes",
            "local_smoke": "campaign worker writes the declared artifact and lane reaches the transport engine locally",
            "dry_run": "scripts/campaign describe/submit dry-run counts equal this design",
            "canary": "missouri_bb63 lane E 20 paired seeds read out before any full panel submit",
            "stop_after_canary": True,
        },
        "report_only_diagnostics": REPORT_ONLY,
        "return": {
            "bucket": "crusherbucket-994254241749-us-east-1-an",
            "prefix": "campaign/contam_phase1_hvac_tracer_01/",
            "slim_artifacts": True,
            "full_frames_optional_only_if_pilot_threshold_passes": True,
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="build and validate without writing")
    args = parser.parse_args(argv)
    design = build_design()
    pools = {hull: payload["pool"] for hull, payload in design["source_pools"].items()}
    spec = _campaign_spec()
    trajectory_cells = design["execution"]["trajectory_array_children"]
    if trajectory_cells != 340:
        raise SystemExit(f"trajectory cell count {trajectory_cells} != 340")
    if design["execution"]["total_array_children"] != 341:
        raise SystemExit("array child count must be 341")
    if len(pools) != len(HULLS):
        raise SystemExit("source pools missing a hull")
    if args.check:
        print(f"OK design={design['design_id']} trajectories={trajectory_cells} array_children=341")
        return 0
    _write_json(DESIGN_PATH, design)
    _write_json(POOLS_PATH, {"design_id": design["design_id"], "source_pools": pools})
    _write_json(CAMPAIGN_JSON_PATH, spec)
    print(f"WROTE {DESIGN_PATH}")
    print(f"WROTE {POOLS_PATH}")
    print(f"WROTE {CAMPAIGN_JSON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
