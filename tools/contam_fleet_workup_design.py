#!/usr/bin/env python3
"""Pre-results design generator for the fleet native-vs-ContamX workup.

Ledger ``CONTAM-FLEET-WORKUP-PROTOCOL-01``. Reads the hull inputs from git at
one pinned commit (never the working tree) and writes, byte-reproducibly:

* ``input_manifest.json`` — repository/tree SHAs and per-file SHA-256
* ``coverage.csv`` — one roster row per platform, exclusions included
* ``run_matrix.csv`` — one pre-expanded row per hull x lane x setting
* ``protocol.json`` — frozen levels, runtime protocol, output data dictionary
* ``dry_run_summary.json`` — exact planned counts and timing workload
* ``SHA256SUMS`` — checksums of the five files above

Nothing here solves a field, times a solver or reads a result. Modes::

    python3 tools/contam_fleet_workup_design.py --write
    python3 tools/contam_fleet_workup_design.py --verify-only   # needs the pin
    python3 tools/contam_fleet_workup_design.py --check-artifacts  # offline
    python3 tools/contam_fleet_workup_design.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from collections import Counter
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.contam_fleet_workup_protocol import PROTOCOL  # noqa: E402

DESIGN_ID = "CONTAM-FLEET-WORKUP-PROTOCOL-01"
INPUT_PIN = "d5d50d3a7bc30d50231e6f27b5083925f26c9c23"
OUT_REL = "docs/audits/2026-11-19_contam_fleet_workup_protocol/evidence"
PLATFORMS = "data/platforms"
PACK = "data/contam_hobbyist"
EXPECTED_PLATFORMS = 82
EXPECTED_BUNDLES = 77
# Bundle = both files present; the per-hull manifest hashes all five inputs.
BUNDLE_FILES = ("contam/platform.prj", "contam/path_map.json")
HULL_FILES = (
    "spatial_layout.json",
    "air_flow_paths.json",
    "contam/hobbyist_overrides.json",
) + BUNDLE_FILES
# Code on the export/solve/import path, hashed at the input pin for reference.
# The runner commit of an execution stage is recorded by that stage.
TOOL_PATH_FILES = (
    "engines/contamx_runner.py",
    "engines/contamx_transport.py",
    "engines/py_contam_bridge.py",
    "tools/contam_hobbyist.py",
    "tools/contam_prj_bridge.py",
    "tools/contamw34_prj.py",
    "tools/diag/contam_paired_diagnostic.py",
    "tools/diag/contam_pressure_balance_diagnostic.py",
    "pyproject.toml",
    "uv.lock",
)
EXCLUSION_REASONS = {
    "expedition_cruise_300": "legacy platform; no committed Contam bundle",
}
DEFAULT_EXCLUSION = "no committed Contam bundle at the input pin"
# Defaults of tools/contam_hobbyist.resolve_relative_wind at the pin.
DEFAULT_WIND_SPEED_M_S = 1.0
DEFAULT_WIND_DIRECTION_DEG = 0.0
PACK_DEFAULT_OA = 0.2
OA_TOLERANCE = 1e-12
REFERENCE_HULLS = ("destroyer_baseline", "expedition_cruise_450")

LANE_NATIVE = "native_prescribed"
LANE_COMMISSIONED = "contamx_commissioned_export"
LANE_AUTHORED = "contamx_authored_bundle"
LANE_AS_COMMITTED = "contamx_commissioned_export_as_committed"
BLOCK_COMPARATIVE = "comparative"
BLOCK_AUTHORED = "authored_baseline"
BLOCK_AS_COMMITTED = "as_committed_export_baseline"

EXECUTE = "planned_execute"
NONRESPONSE = "structural_nonresponse"
NOT_APPLICABLE = "not_applicable"

WARMUP_REPS = 1
MEASURED_REPS = 5
CACHED_REPS = 5
SOLVE_TIMEOUT_S = 300.0

_TEST_LEVEL = "engineering_test_level"
PARAM_DUTY = "supply_group_hvac_duty"
PARAM_ACH = "supply_group_ach"
PARAM_OA = "recirculating_supply_group_oa_fraction"
PARAM_RECIRC = "recirculating_supply_group_recirculated_fraction"
_OA_PARAMETERS = frozenset({PARAM_OA, PARAM_RECIRC})
# (setting_id, family, parameter, unit, level_kind, level)
SETTINGS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("baseline", "baseline", "none", "none", "none", ""),
    ("wind_speed_0", "weather", "relative_wind_speed", "m/s", "absolute", "0"),
    ("wind_speed_5", "weather", "relative_wind_speed", "m/s", "absolute", "5"),
    ("wind_speed_10", "weather", "relative_wind_speed", "m/s", "absolute", "10"),
    ("wind_heading_90", "weather", "relative_wind_direction", "deg",
     "absolute", "90"),
    ("wind_heading_180", "weather", "relative_wind_direction", "deg",
     "absolute", "180"),
    ("wind_speed_10_heading_90", "weather_interaction",
     "relative_wind_speed+relative_wind_direction", "m/s+deg", "absolute",
     "10+90"),
    ("wind_speed_10_heading_180", "weather_interaction",
     "relative_wind_speed+relative_wind_direction", "m/s+deg", "absolute",
     "10+180"),
    ("supply_duty_x0p5", "operational", PARAM_DUTY, "1", "factor", "0.5"),
    ("supply_duty_x1p5", "operational", PARAM_DUTY, "1", "factor", "1.5"),
    ("supply_ach_x1p5", "operational_redundancy_check", PARAM_ACH, "1/h",
     "factor", "1.5"),
    ("supply_oa_x0p5", "operational", PARAM_OA, "1", "factor", "0.5"),
    ("supply_recirc_x0p5", "operational", PARAM_RECIRC, "1", "factor", "0.5"),
)
_WEATHER_FAMILIES = frozenset({"weather", "weather_interaction"})
_OPERATIONAL_FAMILIES = frozenset(
    {"operational", "operational_redundancy_check"}
)

MATRIX_COLUMNS = (
    "row_id", "hull", "block", "lane", "setting_id", "family", "parameter",
    "unit", "level_kind", "level", "level_source", "contrast_type",
    "planned_status", "reason", "warmup_reps", "measured_reps",
    "cached_reps", "contamx_solves_planned",
)
COVERAGE_COLUMNS = (
    "platform", "in_scope", "exclusion_reason", "platform_git_tree",
    "zone_count", "hvac_group_count", "supply_group_count",
    "duty0_group_count", "recirculating_supply_group_count",
    "export_oa_differs_group_count", "ambient_opening_count",
    "cross_ventilated_opening_count", "cross_zone_link_count",
    "adjacency_count", "authored_wind_speed_m_s",
    "authored_wind_direction_deg", "life_support_plenum",
    "wall_azimuth_basis", "weather_coverage", "operational_coverage",
    "rows_total", "rows_planned_execute", "rows_structural_nonresponse",
    "rows_not_applicable", "canary",
)
ARTIFACTS = (
    "input_manifest.json", "coverage.csv", "run_matrix.csv",
    "protocol.json", "dry_run_summary.json",
)
SUMS_NAME = "SHA256SUMS"


class DesignError(RuntimeError):
    """The pin, roster or committed artifacts do not reconcile."""


# ── git access (pinned commit only) ───────────────────────────────────────

def _git(*args: str) -> bytes:
    done = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", *args], cwd=REPO_ROOT, capture_output=True, check=False,
    )
    if done.returncode != 0:
        raise DesignError(
            f"git {' '.join(args[:2])} failed: "
            f"{done.stderr.decode(errors='replace').strip()[:300]}"
        )
    return done.stdout


def _rev(spec: str) -> str:
    return _git("rev-parse", "--verify", spec).decode().strip()


def _blob(pin: str, path: str) -> bytes:
    return _git("cat-file", "blob", f"{pin}:{path}")


def _listing(pin: str, prefix: str) -> dict[str, str]:
    """``path -> git blob sha1`` for every file under *prefix* at *pin*."""
    out = _git("ls-tree", "-r", "-z", "--full-tree", pin, "--", prefix)
    files: dict[str, str] = {}
    for record in out.decode().split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        files[path] = meta.split()[2]
    return files


def _file_entry(pin: str, path: str, blob_sha1: str) -> dict[str, Any]:
    data = _blob(pin, path)
    return {
        "path": path,
        "git_blob_sha1": blob_sha1,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


# ── pure planning (no git, no filesystem) ─────────────────────────────────

def classify_roster(listing: dict[str, str]) -> tuple[list[str], list[str]]:
    """``(platforms, bundled)`` from a ``data/platforms`` file listing."""
    platforms = sorted({
        p.split("/")[2] for p in listing if p.count("/") >= 3
    })
    bundled = [
        h for h in platforms
        if all(f"{PLATFORMS}/{h}/{name}" in listing for name in HULL_FILES)
    ]
    return platforms, bundled


def _azimuth_basis(explicit: int, zones: int) -> str:
    if explicit <= 0:
        return "display_coordinate_heuristic"
    return "declared_per_zone" if explicit >= zones else "mixed"


def _export_oa(group_id: str, overrides: dict[str, Any], pack_oa: float) -> float:
    """OA fraction the hobbyist export resolves for one group at the pin."""
    oa_map = overrides.get("oa_fraction") or {}
    return float(oa_map.get(group_id, oa_map.get("_default", pack_oa)))


def _group_facts(
    airflow: dict[str, Any], overrides: dict[str, Any], pack_oa: float,
) -> dict[str, int]:
    default_duty = float(airflow.get("hvac_duty", 1.0))
    default_oa = float(airflow.get("oa_fraction", 0.2))
    groups = airflow.get("hvac_zones") or []
    supply = [
        g for g in groups if float(g.get("hvac_duty", default_duty)) > 0.0
    ]
    declared = [float(g.get("oa_fraction", default_oa)) for g in supply]
    exported = [_export_oa(str(g["id"]), overrides, pack_oa) for g in supply]
    return {
        "hvac_group_count": len(groups),
        "supply_group_count": len(supply),
        "duty0_group_count": len(groups) - len(supply),
        "recirculating_supply_group_count": sum(oa < 1.0 for oa in declared),
        "export_oa_differs_group_count": sum(
            abs(a - b) > OA_TOLERANCE
            for a, b in zip(declared, exported, strict=True)
        ),
    }


def hull_facts(
    spatial: dict[str, Any], airflow: dict[str, Any],
    overrides: dict[str, Any], pack_oa: float = PACK_DEFAULT_OA,
) -> dict[str, Any]:
    """Aggregate, non-identifying static facts that decide coverage."""
    openings = airflow.get("ambient_openings") or []
    zones = len(spatial.get("zones") or [])
    speed = overrides.get("relative_wind_speed_m_s")
    direction = overrides.get("relative_wind_direction_deg")
    plenum = overrides.get("life_support_plenum")
    if isinstance(plenum, dict):
        plenum = plenum.get("enabled", True)
    return {
        "zone_count": zones,
        **_group_facts(airflow, overrides, pack_oa),
        "ambient_opening_count": len(openings),
        "cross_ventilated_opening_count": sum(
            float(r.get("wind_speed_m_s") or 0.0) > 0.0 for r in openings
        ),
        "cross_zone_link_count": len(airflow.get("cross_zone_links") or []),
        "adjacency_count": len(airflow.get("adjacency") or []),
        "authored_wind_speed_m_s": (
            DEFAULT_WIND_SPEED_M_S if speed is None else float(speed)
        ),
        "authored_wind_direction_deg": (
            DEFAULT_WIND_DIRECTION_DEG if direction is None
            else float(direction)
        ),
        "life_support_plenum": bool(plenum),
        "wall_azimuth_basis": _azimuth_basis(
            len(overrides.get("wall_azimuth_deg") or {}), zones,
        ),
    }


def _weather_status(lane: str, facts: dict[str, Any]) -> tuple[str, str, str]:
    """``(planned_status, contrast_type, reason)`` of one weather row."""
    if facts["life_support_plenum"]:
        return (
            NOT_APPLICABLE, "none",
            "sealed life-support hull authored at calm: no relative wind "
            "exists for this platform in either lane",
        )
    if lane == LANE_NATIVE:
        return (
            NONRESPONSE, "one_sided_structural",
            "the native prescribed-flow engine has no weather input; the "
            "baseline value is carried by reference, not re-run",
        )
    return EXECUTE, "one_sided_structural", ""


def _operational_status(
    parameter: str, facts: dict[str, Any],
) -> tuple[str, str, str]:
    if facts["supply_group_count"] <= 0:
        return (
            NOT_APPLICABLE, "none",
            "no HVAC group with positive duty; the supply-group parameter "
            "does not exist on this hull",
        )
    if parameter in _OA_PARAMETERS and facts["recirculating_supply_group_count"] <= 0:
        return (
            NOT_APPLICABLE, "none",
            "every positive-duty group is declared once-through (outdoor-air "
            "fraction 1.0); there is no recirculated share to vary",
        )
    return EXECUTE, "matched_perturbation", ""


def _row_status(
    lane: str, family: str, parameter: str, facts: dict[str, Any],
) -> tuple[str, str, str]:
    if family == "baseline":
        return EXECUTE, "baseline", ""
    if family in _WEATHER_FAMILIES:
        return _weather_status(lane, facts)
    return _operational_status(parameter, facts)


def _matrix_row(
    hull: str, block: str, lane: str, setting: tuple[str, ...],
    facts: dict[str, Any],
) -> dict[str, Any]:
    setting_id, family, parameter, unit, level_kind, level = setting
    status, contrast, reason = _row_status(lane, family, parameter, facts)
    execute = status == EXECUTE
    reps = WARMUP_REPS + MEASURED_REPS
    return {
        "row_id": f"{hull}|{lane}|{setting_id}",
        "hull": hull,
        "block": block,
        "lane": lane,
        "setting_id": setting_id,
        "family": family,
        "parameter": parameter,
        "unit": unit,
        "level_kind": level_kind,
        "level": level,
        "level_source": "as_committed" if family == "baseline" else _TEST_LEVEL,
        "contrast_type": contrast,
        "planned_status": status,
        "reason": reason,
        "warmup_reps": WARMUP_REPS if execute else 0,
        "measured_reps": MEASURED_REPS if execute else 0,
        "cached_reps": CACHED_REPS if execute else 0,
        "contamx_solves_planned": (
            reps if execute and lane != LANE_NATIVE else 0
        ),
    }


def plan_rows(hull: str, facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Every planned row of one hull: comparative arms, then authored."""
    rows = [
        _matrix_row(hull, BLOCK_COMPARATIVE, lane, setting, facts)
        for setting in SETTINGS
        for lane in (LANE_NATIVE, LANE_COMMISSIONED)
    ]
    rows.append(_matrix_row(
        hull, BLOCK_AS_COMMITTED, LANE_AS_COMMITTED, SETTINGS[0], facts,
    ))
    rows.append(
        _matrix_row(hull, BLOCK_AUTHORED, LANE_AUTHORED, SETTINGS[0], facts)
    )
    return rows


def select_canary(facts_by_hull: dict[str, dict[str, Any]]) -> list[str]:
    """Rule-based canary set, fixed before any result exists."""
    hulls = sorted(facts_by_hull)
    by_size = sorted(hulls, key=lambda h: (facts_by_hull[h]["zone_count"], h))
    plenum = [h for h in hulls if facts_by_hull[h]["life_support_plenum"]]
    chosen = [h for h in REFERENCE_HULLS if h in facts_by_hull]
    chosen += by_size[:1] + by_size[-1:] + plenum[:1]
    return sorted(set(chosen))


def _family_coverage(rows: list[dict[str, Any]], families: frozenset[str]) -> str:
    statuses = sorted({
        r["planned_status"] for r in rows if r["family"] in families
    })
    return "+".join(statuses)


def coverage_row(
    hull: str, tree: str, facts: dict[str, Any],
    rows: list[dict[str, Any]], canary: bool,
) -> dict[str, Any]:
    counts = Counter(r["planned_status"] for r in rows)
    return {
        "platform": hull,
        "in_scope": 1,
        "exclusion_reason": "",
        "platform_git_tree": tree,
        **facts,
        "life_support_plenum": int(facts["life_support_plenum"]),
        "weather_coverage": _family_coverage(rows, _WEATHER_FAMILIES),
        "operational_coverage": _family_coverage(
            rows, _OPERATIONAL_FAMILIES,
        ),
        "rows_total": len(rows),
        "rows_planned_execute": counts[EXECUTE],
        "rows_structural_nonresponse": counts[NONRESPONSE],
        "rows_not_applicable": counts[NOT_APPLICABLE],
        "canary": int(canary),
    }


def excluded_row(platform: str, tree: str) -> dict[str, Any]:
    row: dict[str, Any] = dict.fromkeys(COVERAGE_COLUMNS, "")
    row.update({
        "platform": platform,
        "in_scope": 0,
        "exclusion_reason": EXCLUSION_REASONS.get(platform, DEFAULT_EXCLUSION),
        "platform_git_tree": tree,
        "rows_total": 0,
        "rows_planned_execute": 0,
        "rows_structural_nonresponse": 0,
        "rows_not_applicable": 0,
        "canary": 0,
    })
    return row


def summarize(
    matrix: list[dict[str, Any]], coverage: list[dict[str, Any]],
) -> dict[str, Any]:
    """Exact dry-run counts and projected timing workload."""
    executed = [r for r in matrix if r["planned_status"] == EXECUTE]
    canary = {c["platform"] for c in coverage if c["canary"]}
    cold = sum(r["warmup_reps"] + r["measured_reps"] for r in executed)
    solves = sum(r["contamx_solves_planned"] for r in matrix)
    return {
        "design_id": DESIGN_ID,
        "platforms_at_pin": len(coverage),
        "hulls_in_scope": sum(c["in_scope"] for c in coverage),
        "platforms_excluded": sorted(
            c["platform"] for c in coverage if not c["in_scope"]
        ),
        "settings": len(SETTINGS),
        "rows_total": len(matrix),
        "rows_by_planned_status": dict(sorted(
            Counter(r["planned_status"] for r in matrix).items()
        )),
        "rows_by_lane_and_status": dict(sorted(Counter(
            f"{r['lane']}|{r['planned_status']}" for r in matrix
        ).items())),
        "rows_by_family_and_status": dict(sorted(Counter(
            f"{r['family']}|{r['planned_status']}" for r in matrix
        ).items())),
        "timing_workload": {
            "cold_cell_executions_total": cold,
            "cold_cell_executions_warmup": sum(
                r["warmup_reps"] for r in executed
            ),
            "cold_cell_executions_measured": sum(
                r["measured_reps"] for r in executed
            ),
            "cached_cell_executions": sum(r["cached_reps"] for r in executed),
            "contamx_solver_invocations": solves,
            "native_constructions": cold - solves,
            "rows_not_timed": len(matrix) - len(executed),
            "solver_timeout_s": SOLVE_TIMEOUT_S,
            "solver_time_upper_bound_h": solves * SOLVE_TIMEOUT_S / 3600.0,
        },
        "canary": {
            "hulls": sorted(canary),
            "rows_total": sum(r["hull"] in canary for r in matrix),
            "rows_planned_execute": sum(
                r["hull"] in canary for r in executed
            ),
            "contamx_solver_invocations": sum(
                r["contamx_solves_planned"] for r in matrix
                if r["hull"] in canary
            ),
        },
    }


def protocol_document() -> dict[str, Any]:
    """Frozen levels, runtime protocol and the output data dictionary."""
    frozen = json.loads(json.dumps(PROTOCOL))
    frozen["design_id"] = DESIGN_ID
    frozen["input_pin"] = INPUT_PIN
    frozen["settings"] = [
        dict(zip(("setting_id", "family", "parameter", "unit", "level_kind",
                  "level"), s, strict=True))
        for s in SETTINGS
    ]
    frozen["repetitions"] = {
        "warmup_per_executed_row": WARMUP_REPS,
        "measured_per_executed_row": MEASURED_REPS,
        "cached_per_executed_row": CACHED_REPS,
        "solver_timeout_s": SOLVE_TIMEOUT_S,
    }
    return frozen


# ── build from the pin ────────────────────────────────────────────────────

def _pack_default_oa(pin: str) -> float:
    pack = json.loads(_blob(pin, f"{PACK}/schedule_templates.json"))
    return float(pack.get("defaults", {}).get("oa_fraction", PACK_DEFAULT_OA))


def _load_hull(pin: str, hull: str, pack_oa: float) -> dict[str, Any]:
    base = f"{PLATFORMS}/{hull}"
    return hull_facts(
        json.loads(_blob(pin, f"{base}/spatial_layout.json")),
        json.loads(_blob(pin, f"{base}/air_flow_paths.json")),
        json.loads(_blob(pin, f"{base}/contam/hobbyist_overrides.json")),
        pack_oa,
    )


def _reconcile(pin: str, platforms: list[str], bundled: list[str]) -> None:
    if _rev(f"{pin}^{{commit}}") != pin:
        raise DesignError(f"input pin {pin} is not a full commit id here")
    if (len(platforms), len(bundled)) != (EXPECTED_PLATFORMS, EXPECTED_BUNDLES):
        raise DesignError(
            f"roster does not reconcile at {pin}: {len(platforms)} platforms "
            f"and {len(bundled)} bundles, expected {EXPECTED_PLATFORMS} and "
            f"{EXPECTED_BUNDLES}"
        )


def _manifest(
    pin: str, bundled: list[str], trees: dict[str, str],
    listing: dict[str, str],
) -> dict[str, Any]:
    pack = _listing(pin, PACK)
    tool = _listing(pin, ".")
    return {
        "design_id": DESIGN_ID,
        "input_commit": pin,
        "input_root_tree": _rev(f"{pin}^{{tree}}"),
        "platforms_tree": _rev(f"{pin}:{PLATFORMS}"),
        "hobbyist_pack_tree": _rev(f"{pin}:{PACK}"),
        "hash_algorithms": {
            "sha256": "SHA-256 of the file bytes as stored in git",
            "git_blob_sha1": "git object id of the same bytes",
        },
        "hulls": {
            h: {
                "platform_git_tree": trees[h],
                "files": [
                    _file_entry(pin, f"{PLATFORMS}/{h}/{name}",
                                listing[f"{PLATFORMS}/{h}/{name}"])
                    for name in HULL_FILES
                ],
            }
            for h in bundled
        },
        "shared_inputs": [
            _file_entry(pin, path, sha) for path, sha in sorted(pack.items())
        ],
        "tool_path_at_input_pin": [
            _file_entry(pin, path, tool[path]) for path in TOOL_PATH_FILES
        ],
    }


def build(pin: str | None = None) -> dict[str, bytes]:
    """All artifacts as bytes, derived only from git objects at *pin*."""
    pin = INPUT_PIN if pin is None else pin
    listing = _listing(pin, PLATFORMS)
    platforms, bundled = classify_roster(listing)
    _reconcile(pin, platforms, bundled)
    trees = {p: _rev(f"{pin}:{PLATFORMS}/{p}") for p in platforms}
    pack_oa = _pack_default_oa(pin)
    facts = {h: _load_hull(pin, h, pack_oa) for h in bundled}
    canary = set(select_canary(facts))
    matrix: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for platform in platforms:
        if platform not in facts:
            coverage.append(excluded_row(platform, trees[platform]))
            continue
        rows = plan_rows(platform, facts[platform])
        matrix.extend(rows)
        coverage.append(coverage_row(
            platform, trees[platform], facts[platform], rows,
            platform in canary,
        ))
    return {
        "input_manifest.json": _json_bytes(
            _manifest(pin, bundled, trees, listing)
        ),
        "coverage.csv": _csv_bytes(COVERAGE_COLUMNS, coverage),
        "run_matrix.csv": _csv_bytes(MATRIX_COLUMNS, matrix),
        "protocol.json": _json_bytes(protocol_document()),
        "dry_run_summary.json": _json_bytes(summarize(matrix, coverage)),
    }


# ── serialization, checks, CLI ────────────────────────────────────────────

def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=1, sort_keys=True) + "\n").encode()


def _csv_bytes(columns: tuple[str, ...], rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def sums_bytes(artifacts: dict[str, bytes]) -> bytes:
    return "".join(
        f"{hashlib.sha256(artifacts[name]).hexdigest()}  {name}\n"
        for name in ARTIFACTS
    ).encode()


def _out_path(name: str) -> str:
    return resolve_repo_path(REPO_ROOT, os.path.join(OUT_REL, name))


def read_committed() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for name in (*ARTIFACTS, SUMS_NAME):
        with validated_open(_out_path(name), "rb",
                            allowed_roots=(REPO_ROOT,)) as fh:
            out[name] = fh.read()
    return out


def write(artifacts: dict[str, bytes]) -> None:
    prepare_output_directory(
        resolve_repo_path(REPO_ROOT, OUT_REL), allowed_roots=(REPO_ROOT,),
    )
    for name, data in {**artifacts, SUMS_NAME: sums_bytes(artifacts)}.items():
        with validated_open(_out_path(name), "wb",
                            allowed_roots=(REPO_ROOT,)) as fh:
            fh.write(data)


def check_matrix(matrix: list[dict[str, str]], summary: dict[str, Any]) -> None:
    """Uniqueness and count checks on a parsed matrix (offline)."""
    ids = [r["row_id"] for r in matrix]
    if len(set(ids)) != len(ids):
        raise DesignError("run matrix has duplicate row_id values")
    if len(ids) != summary["rows_total"]:
        raise DesignError("run matrix row count differs from the summary")
    counts = dict(sorted(Counter(r["planned_status"] for r in matrix).items()))
    if counts != summary["rows_by_planned_status"]:
        raise DesignError("planned-status counts differ from the summary")
    per_hull = Counter(r["hull"] for r in matrix)
    expected = 2 * len(SETTINGS) + 2
    if len(per_hull) != EXPECTED_BUNDLES or set(per_hull.values()) != {expected}:
        raise DesignError(f"each of {EXPECTED_BUNDLES} hulls needs {expected} rows")


def check_artifacts(committed: dict[str, bytes]) -> None:
    """Offline integrity of the committed files; needs no git and no solver."""
    if committed[SUMS_NAME] != sums_bytes(committed):
        raise DesignError("SHA256SUMS does not match the committed artifacts")
    summary = json.loads(committed["dry_run_summary.json"])
    matrix = list(csv.DictReader(io.StringIO(committed["run_matrix.csv"].decode())))
    check_matrix(matrix, summary)
    coverage = list(csv.DictReader(io.StringIO(committed["coverage.csv"].decode())))
    in_scope = [c["platform"] for c in coverage if c["in_scope"] == "1"]
    if len(coverage) != EXPECTED_PLATFORMS or len(in_scope) != EXPECTED_BUNDLES:
        raise DesignError("coverage roster is not 82 platforms / 77 hulls")
    manifest = json.loads(committed["input_manifest.json"])
    if manifest["input_commit"] != INPUT_PIN or sorted(manifest["hulls"]) != in_scope:
        raise DesignError("manifest pin or hull set differs from the roster")


def verify_against_pin() -> None:
    first, second = build(), build()
    if first != second:
        raise DesignError("two consecutive builds are not byte-identical")
    committed = read_committed()
    expected = {**first, SUMS_NAME: sums_bytes(first)}
    stale = sorted(n for n, data in expected.items() if committed.get(n) != data)
    if stale:
        raise DesignError(f"committed artifacts differ from the pin: {stale}")
    check_artifacts(committed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--check-artifacts", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.write:
            write(build())
        elif args.verify_only:
            verify_against_pin()
        elif args.check_artifacts:
            check_artifacts(read_committed())
        summary = json.loads(
            build()["dry_run_summary.json"] if args.dry_run
            else read_committed()["dry_run_summary.json"]
        )
    except DesignError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
