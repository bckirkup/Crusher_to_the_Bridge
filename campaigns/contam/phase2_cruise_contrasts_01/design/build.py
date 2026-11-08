#!/usr/bin/env python3
"""Build the frozen Phase 2 CONTAM four-cruise contrast campaign design.

The design is deterministic and anchor-free: source pools reuse the Phase 1
selector verbatim (zone type, volume, ``max_occupancy``, HVAC service and
duty, adjacency degree; tie-break by zone id), the seed mapping is the
manifest's paired-seed rule, and the seven named arms are
``tools/contam_fleet_compare.py`` op lists. Running this script rewrites
``design/phase2_cruise_contrasts_design.json``, ``source_pools.json``, and the
campaign-root ``campaign.json`` from the four cruise platform layouts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN_REL = "campaigns/contam/phase2_cruise_contrasts_01"
CAMPAIGN_DIR = ROOT / CAMPAIGN_REL
DESIGN_REL = f"{CAMPAIGN_REL}/design/phase2_cruise_contrasts_design.json"
DESIGN_PATH = ROOT / DESIGN_REL
POOLS_PATH = CAMPAIGN_DIR / "source_pools.json"
CAMPAIGN_JSON_PATH = CAMPAIGN_DIR / "campaign.json"

DESIGN_ID = "contam_phase2_cruise_contrasts_01"
MANIFEST_REL = "docs/proposals/contam_phase2_scope_manifest.md"
MANIFEST_PR = 1183
MANIFEST_AMENDMENT_PR = 1185
SCALE_ACH_SCOPE_PR = 1187
REGISTRY_BASELINE_SHA = "f5d32477"
REPINNED_MAIN_SHA = "71dd32ec5fd79803adf1b07fffb59cd2a481544a"

HULLS = [
    "expedition_cruise_450",
    "classic_cruise_1900",
    "spirit_cruise_3000",
    "mega_cruise_5000",
]
LANES = ["N", "E", "P"]
PRIMARY_LANES = ["N", "E"]
P_LANE_ARMS = ["baseline"]
SEEDS = list(range(1, 21))
EPOCHS = 12
EPOCH_HOURS = 1.0
TRACER_MASS = 1_000_000.0
NATURAL_DECAY_RATE = 0.0
FILTER_EFFICIENCY = 0.5
BASELINE_OA_FRACTION = 0.2
DC04_ALPHA = 1.5

S3_BUCKET = "crusherbucket-994254241749-us-east-1-an"
S3_PREFIX = f"campaign/{DESIGN_ID}/"
FIELD_CACHE_S3_URI = f"s3://{S3_BUCKET}/{S3_PREFIX}field_cache/field_cache.json"
FIELD_CACHE_SCHEMA = "contam_phase2_cruise_contrasts_field_cache_v1"
PHASE1_FIELD_CACHE_SHA256 = (
    "b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5"
)
PHASE1_FIELD_CACHE_S3_URI = (
    f"s3://{S3_BUCKET}/campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json"
)
PHASE1_REUSABLE_FIELDS = [
    "expedition_cruise_450:E:baseline",
    "expedition_cruise_450:P:baseline",
]
CONTAMX_VERSION = "3.4.0.3 64 bit"
CONTAMX_BINARY = "third_party/contamx/contamx3"
CONTAMX_BINARY_SHA256 = (
    "d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b"
)
CONTAMX_DOWNLOAD_URL = (
    "https://www.nist.gov/document/contam-x-3403-linux-64bittargz"
)
CONTAMX_TARBALL = "contam-x-3.4.0.3-Linux-64bit.tar.gz"
CONTAMX_TARBALL_SHA256 = (
    "3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa"
)
CONTAMX_LICENSE_NOTICE = (
    "NIST Contam is U.S. public domain (17 U.S.C. §105); the official NIST "
    "tarball is redistributable with notice."
)
IMAGE_TAG = "contam-phase2-cruise-contrasts-01"

# Manifest §2.2: fleet-compare op grammar; ``baseline`` is the anchor and the
# only P-lane arm. Gains are r = (1 - f)(1 - eta) on the supply groups.
ARMS: dict[str, dict[str, Any]] = {
    "baseline": {
        "code": "B",
        "ops": [],
        "supply_oa_fraction": 0.2,
        "filter_efficiency": 0.5,
        "declared_gain_r": 0.40,
        "turnover_factor": 1.0,
        "serves": ["anchor", "DC01", "DC02", "DC04", "DC05", "DC07"],
        "description": "Shipped airflow and engine parameters; anchor for every contrast; the only P-lane arm.",
    },
    "oa_050": {
        "code": "O",
        "ops": [{"op": "set_oa", "value": 0.5, "scope": "supply_groups"}],
        "supply_oa_fraction": 0.5,
        "filter_efficiency": 0.5,
        "declared_gain_r": 0.25,
        "turnover_factor": 1.0,
        "serves": ["DC01", "DC02"],
        "description": "Outdoor-air fraction 0.5 on the supply groups; duty-0 exhaust branches keep declared OA 1.0.",
    },
    "filter_090": {
        "code": "F",
        "ops": [{"op": "set_filter", "value": 0.9}],
        "supply_oa_fraction": 0.2,
        "filter_efficiency": 0.9,
        "declared_gain_r": 0.08,
        "turnover_factor": 1.0,
        "serves": ["DC01"],
        "description": "Filter efficiency 0.5 -> 0.9 (fleet arm filter_merv13 figure); engine-level on both lanes.",
    },
    "oa_050_filter_090": {
        "code": "OF",
        "ops": [
            {"op": "set_oa", "value": 0.5, "scope": "supply_groups"},
            {"op": "set_filter", "value": 0.9},
        ],
        "supply_oa_fraction": 0.5,
        "filter_efficiency": 0.9,
        "declared_gain_r": 0.05,
        "turnover_factor": 1.0,
        "serves": ["DC01"],
        "description": "Combined OA 0.5 and filter 0.9; the strongest fixed-field removal arm of the DC01 ordering.",
    },
    "eq_gain_025_filter": {
        "code": "G",
        "ops": [{"op": "set_filter", "value": 0.6875}],
        "supply_oa_fraction": 0.2,
        "filter_efficiency": 0.6875,
        "declared_gain_r": 0.25,
        "turnover_factor": 1.0,
        "serves": ["DC02"],
        "description": "Equal-gain partner of oa_050: filter 0.6875 at OA 0.2 gives r = 0.25 on every supply group.",
    },
    "ach_150_supply": {
        "code": "A",
        "ops": [{"op": "scale_ach", "factor": 1.5, "scope": "supply_groups"}],
        "supply_oa_fraction": 0.2,
        "filter_efficiency": 0.5,
        "declared_gain_r": 0.40,
        "turnover_factor": 1.5,
        "serves": ["DC04"],
        "description": "High-turnover arm: ach x1.5 restricted to supply groups (PR #1187 scope); duty-0 exhausts unchanged.",
    },
    "oa_080": {
        "code": "R",
        "ops": [{"op": "set_oa", "value": 0.8, "scope": "supply_groups"}],
        "supply_oa_fraction": 0.8,
        "filter_efficiency": 0.5,
        "declared_gain_r": 0.10,
        "turnover_factor": 1.0,
        "serves": ["DC04"],
        "description": "Matched-removal partner of ach_150_supply: OA 0.8 at baseline turnover gives r_low = 0.1 on every supply group.",
    },
}
ARM_ORDER = list(ARMS)

LARGE_VENUE_TYPES = {"Dining", "Free", "Cabin_Corridor", "Medical"}
CATEGORY_LIMITS = {"large_venue": 4, "sanitary_branch": 3, "remote_weak": 3}
CATEGORY_ORDER = ["large_venue", "sanitary_branch", "remote_weak"]

PILOT_HULL = "mega_cruise_5000"
PILOT = {
    "hull": PILOT_HULL,
    "lane": "E",
    "arm": "baseline",
    "seeds": SEEDS,
    "epochs": EPOCHS,
    "epoch_hours": EPOCH_HOURS,
    "vcpu": 1,
    "memory_mib": 2048,
    "trajectory_block": f"{PILOT_HULL}_e_baseline",
}

PHASE1_FULL_PANEL_TRAJECTORY_CPU_HOURS = 0.141446
PHASE1_FULL_PANEL_ARTIFACT_BYTES = 10_505_015
THRESHOLDS = {
    "pilot_succeeded_cells": 20,
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
    "full_panel_cpu_hours_extrapolated_max": 12 * PHASE1_FULL_PANEL_TRAJECTORY_CPU_HOURS,
    "full_panel_artifact_bytes_extrapolated_max": 12 * PHASE1_FULL_PANEL_ARTIFACT_BYTES,
}

REPORT_ONLY = [
    "retained_fraction_curve_12h",
    "per_zone_concentration_stats",
    "source_to_receptor_contrasts",
    "path_type_flow_summaries",
    "wall_clock_and_rss_telemetry",
    "field_solve_seconds",
    "field_audit_counts",
    "injection_connectivity",
    "phase1_field_cache_byte_comparison",
    "edison_practical_tie_band_5pp",
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


def _group_settings(airflow: dict[str, Any]) -> dict[str, Any]:
    default_duty = float(airflow.get("hvac_duty", 1.0))
    default_oa = float(airflow.get("oa_fraction", BASELINE_OA_FRACTION))
    supply = []
    duty0 = []
    for group in _hvac_groups(airflow):
        duty = float(group.get("hvac_duty", default_duty))
        row = {
            "id": str(group.get("id") or ""),
            "ach": float(group.get("ach") or 0.0),
            "hvac_duty": duty,
            "oa_fraction": float(group.get("oa_fraction", default_oa)),
        }
        (supply if duty > 0.0 else duty0).append(row)
    return {"supply": supply, "duty0": duty0}


def _hull_panel() -> dict[str, dict[str, Any]]:
    """Manifest §3 declaration facts, recomputed from the platform JSONs."""
    panel: dict[str, dict[str, Any]] = {}
    for hull in HULLS:
        spatial_path, airflow_path = _platform_paths(hull)
        spatial = _load_json(spatial_path)
        airflow = _load_json(airflow_path)
        path_map = _load_json(ROOT / "data" / "platforms" / hull / "contam" / "path_map.json")
        zones = list(spatial.get("zones") or [])
        groups = _group_settings(airflow)
        supply_oa = sorted({row["oa_fraction"] for row in groups["supply"]})
        r_base = [round((1.0 - oa) * (1.0 - FILTER_EFFICIENCY), 12) for oa in supply_oa]
        panel[hull] = {
            "zones": len(zones),
            "volume_m3": round(sum(_volume(zone) for zone in zones), 2),
            "path_map_entries": len(path_map),
            "hvac_groups": len(groups["supply"]) + len(groups["duty0"]),
            "supply_groups": len(groups["supply"]),
            "duty0_groups": len(groups["duty0"]),
            "sanitary_zones": sum(1 for zone in zones if zone.get("type") == "Sanitary"),
            "supply_oa_fractions": supply_oa,
            "supply_ach_values": sorted({row["ach"] for row in groups["supply"]}),
            "duty0_oa_fractions": sorted({row["oa_fraction"] for row in groups["duty0"]}),
            "duty0_ach_values": sorted({row["ach"] for row in groups["duty0"]}),
            "r_base": r_base,
            "dc04_r_low": [round(1.0 - DC04_ALPHA * (1.0 - r), 12) for r in r_base],
            "committed_prj": (ROOT / "data" / "platforms" / hull / "contam" / "platform.prj").is_file(),
        }
    return panel


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


def block_name(hull: str, lane: str, arm: str) -> str:
    return f"{hull}_{lane.lower()}_{arm}"


def _lane_arms(lane: str) -> list[str]:
    return P_LANE_ARMS if lane == "P" else ARM_ORDER


def _trajectory_blocks() -> dict[str, Any]:
    blocks: dict[str, Any] = {}
    for hull in HULLS:
        for lane in LANES:
            for arm in _lane_arms(lane):
                blocks[block_name(hull, lane, arm)] = {
                    "worker": f"{CAMPAIGN_REL}/cell.py",
                    "artifact": "cell_{seed}.json",
                    "args": {
                        "mode": "trajectory",
                        "hull": hull,
                        "lane": lane,
                        "arm": arm,
                    },
                    "seeds": SEEDS,
                }
    return blocks


def field_key(hull: str, lane: str, arm: str) -> str:
    return f"{hull}:{lane}:{arm}"


def field_plan() -> list[dict[str, Any]]:
    """The 32 ContamX fields of the Option A pre-stage (manifest §4/§6)."""
    fields: list[dict[str, Any]] = []
    for hull in HULLS:
        for lane in ("E", "P"):
            for arm in _lane_arms(lane):
                key = field_key(hull, lane, arm)
                fields.append({
                    "key": key,
                    "hull": hull,
                    "lane": lane,
                    "arm": arm,
                    "source": "committed_prj" if lane == "P" else "commissioned_export",
                    "ops": ARMS[arm]["ops"],
                    "filter_efficiency_at_export": ARMS[arm]["filter_efficiency"],
                    "fresh_solve_required": True,
                    "phase1_reusable_control": key in PHASE1_REUSABLE_FIELDS,
                })
    return fields


def _campaign_spec() -> dict[str, Any]:
    blocks = _trajectory_blocks()
    return {
        "name": DESIGN_ID,
        "pathogen": "contam",
        "manifest": DESIGN_REL,
        "pathogen_id": None,
        "s3_prefix": S3_PREFIX,
        "queue": "picard-campaign-queue",
        "image_tag": IMAGE_TAG,
        "epochs": EPOCHS,
        "epoch_hours": EPOCH_HOURS,
        "resources": {"vcpu": "1", "memory": "2048"},
        "readout": f"{CAMPAIGN_REL}/readout.py",
        "blocks": blocks,
    }


def _field_cache_prestage() -> dict[str, Any]:
    fields = field_plan()
    return {
        "mode": "local_only",
        "aws_submit": False,
        "producer": (
            f"python3 {CAMPAIGN_REL}/cell.py --mode field-cache --design "
            f"{DESIGN_REL} --out <local-dir>"
        ),
        "artifact": "field_cache.json",
        "schema": FIELD_CACHE_SCHEMA,
        "field_count": len(fields),
        "fresh_solve_count": len(fields),
        "phase1_reusable_fields": PHASE1_REUSABLE_FIELDS,
        "phase1_field_cache_s3_uri": PHASE1_FIELD_CACHE_S3_URI,
        "phase1_field_cache_sha256": PHASE1_FIELD_CACHE_SHA256,
        "phase1_byte_comparison": "report-only reproducibility control; never a selector",
        "key_rule": "<hull>:<lane>:<arm>; every field records the ops, edits, realized per-group ach/hvac_duty/oa_fraction and the filter efficiency used at export",
        "fields": fields,
        "s3_uri": FIELD_CACHE_S3_URI,
        "trajectory_consumer_arg": "--field-cache-uri",
        "contamx": {
            "version": CONTAMX_VERSION,
            "binary": CONTAMX_BINARY,
            "binary_sha256": CONTAMX_BINARY_SHA256,
            "download_url": CONTAMX_DOWNLOAD_URL,
            "tarball": CONTAMX_TARBALL,
            "tarball_sha256": CONTAMX_TARBALL_SHA256,
            "license_notice": CONTAMX_LICENSE_NOTICE,
        },
    }


def _matrix(blocks: dict[str, Any]) -> dict[str, Any]:
    primary = sum(
        len(block["seeds"]) for block in blocks.values()
        if block["args"]["lane"] in PRIMARY_LANES
    )
    p_lane = sum(
        len(block["seeds"]) for block in blocks.values()
        if block["args"]["lane"] == "P"
    )
    total = primary + p_lane
    return {
        "primary": "4 hulls x N/E x 7 arms x 20 paired seeds x 12 epochs x 1h",
        "primary_trajectories": primary,
        "p_contrast": "4 hulls x P x baseline x 20 paired seeds",
        "p_contrast_trajectories": p_lane,
        "total_trajectories": total,
        "hourly_steps": total * EPOCHS,
        "blocks": len(blocks),
        "primary_blocks": sum(1 for b in blocks.values() if b["args"]["lane"] in PRIMARY_LANES),
        "p_blocks": sum(1 for b in blocks.values() if b["args"]["lane"] == "P"),
        "array_size_per_block": len(SEEDS),
        "seeds": SEEDS,
        "epochs": EPOCHS,
        "epoch_hours": EPOCH_HOURS,
    }


def _contrasts() -> dict[str, Any]:
    return {
        "DC01": {
            "kind": "monotonicity / ordered-gain control",
            "arms": ["baseline", "oa_050", "filter_090", "oa_050_filter_090"],
            "lanes": PRIMARY_LANES,
            "prediction": "B_V(OF) <= B_V(F) <= B_V(O) <= B_V(B) per seed per lane; per-zone E_i(12h) ordering",
            "readout": "ordering pass counts and violation lists; control, not a result",
        },
        "DC02": {
            "kind": "equal-gain equivalence control",
            "arms": ["oa_050", "eq_gain_025_filter"],
            "lanes": PRIMARY_LANES,
            "readout": "paired O - G on B_V and max_i |E_i(O) - E_i(G)|; exact zero in N means gain-only operator",
        },
        "DC03": {
            "kind": "exact mean-loss / different-mixing control",
            "arms": [],
            "trajectories": 0,
            "fixture": "tests/test_contam_analytic_fixtures.py::TestDC03ExactMeanLossDifferentMixing",
            "cases": [
                {"ach": 1.8, "oa": 0.2, "eta": 0.5, "r": 0.4},
                {"ach": 1.2, "oa": 0.8, "eta": 0.5, "r": 0.1},
            ],
        },
        "DC04": {
            "kind": "feasible group-matched removal (hull level)",
            "arms": ["ach_150_supply", "oa_080", "baseline"],
            "lanes": PRIMARY_LANES,
            "alpha": DC04_ALPHA,
            "r_low_rule": "r_low = 1 - alpha * (1 - r_base), must lie in [0, 1] on every supply group; the arm fails closed otherwise",
            "readout": "paired A - R, A - B, R - B on B_V; reductions R_a = 1 - B_a/B_B with pairwise gap; per-zone dE_i distribution and sign-flip zones",
        },
        "DC05": {
            "kind": "paired N/E field adequacy",
            "arms": ARM_ORDER,
            "lanes": PRIMARY_LANES,
            "readout": "paired N - E per arm; arm-effect parity between lanes; realized vs declared per-AHS flows from the E field",
        },
        "DC07": {
            "kind": "selected source / receptor responses",
            "arms": ARM_ORDER,
            "lanes": LANES,
            "readout": "per hull x lane x arm x source class: receptor E_i(12h)/emitted mass, local vs remote, p50/p95/max, time-to-peak, first arrival, never-reached count",
        },
    }


def build_design() -> dict[str, Any]:
    source_pools = _source_pools()
    pool_lengths = {
        hull: len(payload["pool"]) for hull, payload in source_pools.items()
    }
    blocks = _trajectory_blocks()
    matrix = _matrix(blocks)
    prestage = _field_cache_prestage()
    return {
        "design_id": DESIGN_ID,
        "status": "frozen_before_first_cell",
        "manifest": MANIFEST_REL,
        "manifest_pr": MANIFEST_PR,
        "manifest_amendment_pr": MANIFEST_AMENDMENT_PR,
        "scale_ach_scope_pr": SCALE_ACH_SCOPE_PR,
        "baseline_sha": {
            "registry_baseline_sha": REGISTRY_BASELINE_SHA,
            "repinned_main_sha": REPINNED_MAIN_SHA,
            "note": "manifest §11.7: decisive_contrasts.csv baseline_sha re-pinned to origin/main at design freeze",
        },
        "phase": "phase2_four_cruise_transport_contrasts",
        "excluded": [
            "stochastic_agents",
            "pathogen_coupling",
            "epidemiological_constants",
            "vsp_park_attack_rate_anchors",
            "lane_s_stock_contamx_contaminant",
            "ship_x",
            "passenger_circulation_source_class",
            "lambda_0_1_sensitivity",
            "DC06", "DC08", "DC09", "DC10", "DC11", "DC12",
        ],
        "hulls": HULLS,
        "hull_panel": _hull_panel(),
        "bundled_p_lane_hulls": HULLS,
        "lanes": {
            "N": "native heuristic HVAC + passive/cross-zone flows from the arm-mutated air_flow_paths.json",
            "E": "fresh commissioned ContamX export of the arm-mutated JSON + AHS synthesis",
            "P": "committed contam/platform.prj + path_map.json, baseline arm only",
        },
        "p_lane_arms": P_LANE_ARMS,
        "arms": ARMS,
        "arm_order": ARM_ORDER,
        "arm_application": "tools.contam_fleet_compare._apply_arm_ops on a copy of the platform air_flow_paths.json; edits log and realized per-group settings recorded in every cell",
        "contrasts": _contrasts(),
        "tracer": {
            "mass_per_seed": TRACER_MASS,
            "normalization": "emitted_mass",
            "natural_decay_rate": NATURAL_DECAY_RATE,
            "filter_efficiency": FILTER_EFFICIENCY,
            "baseline_oa_fraction": BASELINE_OA_FRACTION,
            "timing_patterns": {
                "t0_pulse": "1e6 at t=0h",
                "t0_t1_split": "500000 at t=0h and 500000 after first hourly step",
            },
            "unchanged_from_phase1": True,
        },
        "matrix": matrix,
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
            "phase1_selector_verbatim": True,
        },
        "source_pools": source_pools,
        "seed_mapping": {
            "rule": "k=seed-1; timing=k mod 2; pool_index=(k//2) mod pool_length",
            "timing_codes": {"0": "t0_pulse", "1": "t0_t1_split"},
            "pairing": "seed s selects the same source realization in every lane and every arm of a hull",
            "grid": _seed_grid(pool_lengths),
        },
        "execution": {
            "submit_path": "scripts/campaign submit contam/phase2_cruise_contrasts_01 --block <block>",
            "block_name_rule": "<hull>_<lane>_<arm>",
            "field_cache_prestage": prestage,
            "trajectory_blocks": len(blocks),
            "trajectory_array_children": matrix["total_trajectories"],
            "total_array_children": matrix["total_trajectories"],
            "submit_order": [
                "field_cache_prestage_local_upload (not a Batch block)",
                f"{PILOT['trajectory_block']} pilot/canary",
                "remaining 59 blocks after user decision",
            ],
            "resources": {"vcpu": 1, "memory_mib": 2048},
            "aws_profile": "picard",
            "queue": "picard-campaign-queue",
            "image_tag": IMAGE_TAG,
            "image_digest_pinned": False,
            "pin_image_digest_before_submit": True,
        },
        "pilot": PILOT,
        "thresholds": THRESHOLDS,
        "threshold_basis": {
            "phase1_full_panel_trajectory_cpu_hours": PHASE1_FULL_PANEL_TRAJECTORY_CPU_HOURS,
            "phase1_full_panel_artifact_bytes": PHASE1_FULL_PANEL_ARTIFACT_BYTES,
            "extrapolation_rule": "predicted full panel = total_trajectories x pilot mean per-trajectory CPU (or bytes); bound is 12 x the measured Phase 1 full panel",
            "frozen": "thresholds are never adjusted after a measurement",
        },
        "acceptance_gates": {
            "geometry_seed_gate": "all source zones exist; seed mapping deterministic; paired seeds use identical source realization across lanes and arms",
            "local_smoke": "campaign worker writes the declared artifact; each arm's op reaches the engine (edits log and realized settings differ from baseline exactly as declared); output contract unchanged",
            "dry_run": "scripts/campaign describe/submit dry-run counts equal this design (60 blocks, arrayProperties.size=20 each)",
            "field_prestage": "32 fields solved locally, every solve <= 30 s, uploaded with SHA256 recorded",
            "canary": f"{PILOT['trajectory_block']} 20 paired seeds read out before any further submit",
            "phase1_bridge": "expedition_cruise_450 baseline N/E/P cells reproduce Phase 1 cell_{seed}.json metrics seed-for-seed",
            "stop_after_canary": True,
        },
        "report_only_diagnostics": REPORT_ONLY,
        "return": {
            "bucket": S3_BUCKET,
            "prefix": S3_PREFIX,
            "slim_artifacts": True,
            "schema_confirmation": "Phase 4",
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate(design: dict[str, Any], spec: dict[str, Any]) -> None:
    matrix = design["matrix"]
    if matrix["total_trajectories"] != 1200:
        raise SystemExit(f"trajectory cell count {matrix['total_trajectories']} != 1200")
    if matrix["primary_trajectories"] != 1120 or matrix["p_contrast_trajectories"] != 80:
        raise SystemExit("N/E must be 1120 trajectories and P 80")
    if len(spec["blocks"]) != 60:
        raise SystemExit(f"campaign block count {len(spec['blocks'])} != 60")
    if any(len(block["seeds"]) != 20 for block in spec["blocks"].values()):
        raise SystemExit("every block must be an array of 20")
    if design["execution"]["field_cache_prestage"]["field_count"] != 32:
        raise SystemExit("field pre-stage must enumerate 32 fields")
    if len(design["source_pools"]) != len(HULLS):
        raise SystemExit("source pools missing a hull")
    if any(len(payload["pool"]) != 10 for payload in design["source_pools"].values()):
        raise SystemExit("every cruise pool must have exactly 10 zones")
    if PILOT["trajectory_block"] not in spec["blocks"]:
        raise SystemExit("pilot block missing from campaign spec")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="build and validate without writing")
    args = parser.parse_args(argv)
    design = build_design()
    spec = _campaign_spec()
    _validate(design, spec)
    pools = {hull: payload["pool"] for hull, payload in design["source_pools"].items()}
    trajectory_cells = design["execution"]["trajectory_array_children"]
    if args.check:
        print(
            f"OK design={design['design_id']} trajectories={trajectory_cells} "
            f"array_children={trajectory_cells} blocks={len(spec['blocks'])} "
            f"fields={design['execution']['field_cache_prestage']['field_count']}"
        )
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
