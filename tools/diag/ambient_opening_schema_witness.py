#!/usr/bin/env python3
"""Fleet byte-identity witness for CONTAM-AMBIENT-OPENING-SCHEMA-01.

Hashes, for every platform under ``data/platforms/`` that carries an
``air_flow_paths.json``, the in-memory ContamW 3.4 export (PRJ text and
path_map) in each export lane and the native engine's path list in each
topology mode. Run it on the tree before and after a change that must not
move any hull and compare the two reports: the ``fleet_sha256`` values are
equal only when every export and every native path is byte-identical.

The path fingerprint deliberately covers the fields that existed before the
schema stage (id, endpoints, flow, type, ducted, filtered, sink), so the same
script runs unchanged on the pre-change tree.

Nothing is written into ``data/``; the report goes under ``telemetry_buffer/``.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
from typing import Any

_SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPT_ROOT)

from engines.py_contam_bridge import (  # noqa: E402
    DUTY0_TERMINAL_MODES,
    PASSIVE_LINK_MODES,
    ContamTransportEngine,
)
from simulation_utils.paths import (  # noqa: E402
    REPO_ROOT,
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contamw34_prj import export_contamw34  # noqa: E402

_PLATFORMS_REL = os.path.join("data", "platforms")
_AIRFLOW_NAME = "air_flow_paths.json"
_SPATIAL_NAME = "spatial_layout.json"
_AMBIENT_OPENINGS_KEY = "ambient_openings"
# (label, hobbyist, ahs_terminal_mode)
EXPORT_LANES = (
    ("skeleton_design", False, "design"),
    ("skeleton_commissioned", False, "commissioned"),
    ("hobbyist_design", True, "design"),
    ("hobbyist_commissioned", True, "commissioned"),
)
_WITNESS_FILTER_EFFICIENCY = 0.5


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(rel_path: str) -> Any:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def fleet_platforms() -> list[str]:
    """Platform ids that carry both layout files."""
    root = resolve_repo_path(REPO_ROOT, _PLATFORMS_REL)
    return sorted(
        name
        for name in os.listdir(root)
        if os.path.isfile(os.path.join(root, name, _AIRFLOW_NAME))
        and os.path.isfile(os.path.join(root, name, _SPATIAL_NAME))
    )


def _export_hashes(
    spatial: dict[str, Any], airflow: dict[str, Any], overrides: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for label, hobbyist, mode in EXPORT_LANES:
        prj_text, path_map = export_contamw34(
            spatial,
            airflow,
            hobbyist=hobbyist,
            overrides=overrides if hobbyist else None,
            ahs_terminal_mode=mode,
        )
        out[label] = {
            "prj_sha256": _sha(prj_text),
            "path_map_sha256": _sha(
                json.dumps(path_map, indent=2, ensure_ascii=False)
            ),
            "n_paths": len(path_map),
        }
    return out


def _native_hashes(
    spatial: dict[str, Any], airflow: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for duty0, passive in itertools.product(DUTY0_TERMINAL_MODES, PASSIVE_LINK_MODES):
        engine = ContamTransportEngine(
            spatial_layout=spatial,
            air_flow_paths=airflow,
            filter_efficiency=_WITNESS_FILTER_EFFICIENCY,
            duty0_terminal_mode=duty0,
            passive_link_mode=passive,
        )
        rows = [
            [
                p.path_id, p.from_zone, p.to_zone,
                float(p.flow_rate_m3h).hex(), p.path_type,
                bool(p.is_hvac_ducted), bool(p.filtered), bool(p.sink),
            ]
            for p in engine.airflow_paths
        ]
        out[f"{duty0}_{passive}"] = {
            "paths_sha256": _sha(json.dumps(rows)),
            "n_paths": len(rows),
        }
    return out


def platform_report(platform: str) -> dict[str, Any]:
    """Export and native-path fingerprints for one hull."""
    base = os.path.join(_PLATFORMS_REL, platform)
    spatial = _load_json(os.path.join(base, _SPATIAL_NAME))
    airflow = _load_json(os.path.join(base, _AIRFLOW_NAME))
    overrides = load_hobbyist_overrides(resolve_repo_path(REPO_ROOT, base))
    return {
        "declared_ambient_openings": len(airflow.get(_AMBIENT_OPENINGS_KEY) or []),
        "export": _export_hashes(spatial, airflow, overrides),
        "native": _native_hashes(spatial, airflow),
    }


def build_report(platforms: list[str]) -> dict[str, Any]:
    """Per-hull fingerprints plus one fleet digest over all of them."""
    hulls = {platform: platform_report(platform) for platform in platforms}
    return {
        "n_platforms": len(hulls),
        "n_export_fingerprints": sum(len(h["export"]) for h in hulls.values()),
        "n_native_fingerprints": sum(len(h["native"]) for h in hulls.values()),
        "n_declared_ambient_openings": sum(
            h["declared_ambient_openings"] for h in hulls.values()
        ),
        "fleet_sha256": _sha(json.dumps(hulls, sort_keys=True)),
        "platforms": hulls,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hull", action="append")
    parser.add_argument(
        "--out",
        default="telemetry_buffer/ambient_opening_schema_witness/report.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_report(args.hull or fleet_platforms())
    out_path = resolve_repo_path(REPO_ROOT, args.out)
    prepare_output_directory(os.path.dirname(out_path), allowed_roots=(REPO_ROOT,))
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(
        f"platforms={report['n_platforms']} "
        f"export_fingerprints={report['n_export_fingerprints']} "
        f"native_fingerprints={report['n_native_fingerprints']} "
        f"declared_ambient_openings={report['n_declared_ambient_openings']} "
        f"fleet_sha256={report['fleet_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
