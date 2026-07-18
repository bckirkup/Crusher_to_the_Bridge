#!/usr/bin/env python3
"""
contam_flow_compare.py – native ACH vs ContamX SIM per-path diagnostic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Explains transport divergence between ``ContamTransportEngine`` (prescribed
ACH digraph) and ``ContamXTransportEngine`` (ContamX SIM flows + AHS bridge).

Always dumps:

- Native Crusher airflow links (from/to/m³/h/type)
- Contam ``path_map`` entries with keep/skip fate under ContamX filter rules
- Zone connectivity degree for injection zone(s)

With ContamX available (or a pre-run ``.SIM``):

- Joins SIM ``Flow0`` volumetric flows onto ``path_map`` by ``path_nr``
- Lists surviving real↔real edges + synthesized AHS recirculation

Usage::

    python3 tools/contam_flow_compare.py --platform destroyer_baseline
    python3 tools/contam_flow_compare.py --platform destroyer_baseline \\
        --inject Bridge:1000000 --output telemetry_buffer/contam_flow_destroyer.json
    python3 tools/contam_flow_compare.py --platform destroyer_baseline \\
        --sim data/platforms/destroyer_baseline/contam/platform.sim
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_ahs_bridge import synthesize_ahs_recirculation_paths  # noqa: E402
from engines.contamx_runner import (  # noqa: E402
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.contamx_transport import (  # noqa: E402
    _FLOW_EPSILON_M3H,
    _normalize_path_map_entries,
)
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)


def _load_json(rel: str) -> Any:
    path = resolve_repo_path(REPO_ROOT, rel)
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _platform_files(platform_id: str) -> dict[str, str]:
    safe = validate_path_component(platform_id, label="platform id")
    base = os.path.join("data", "platforms", safe)
    return {
        "spatial": os.path.join(base, "spatial_layout.json"),
        "airflow": os.path.join(base, "air_flow_paths.json"),
        "prj": os.path.join(base, "contam", "platform.prj"),
        "path_map": os.path.join(base, "contam", "path_map.json"),
    }


def classify_contamx_path_fate(
    entry: dict[str, Any],
    path_flows_m3h: dict[int, float] | None,
    known_zones: set[str],
) -> dict[str, Any]:
    """Return keep/skip classification for one Contam path_map entry."""
    kind = str(entry.get("kind", ""))
    pnr = int(entry["path_nr"])
    from_z = entry["from_zone"]
    to_z = entry["to_zone"]
    flow = float((path_flows_m3h or {}).get(pnr, 0.0)) if path_flows_m3h else None
    row: dict[str, Any] = {
        "path_nr": pnr,
        "kind": kind,
        "from_zone": from_z,
        "to_zone": to_z,
        "ahs_nr": int(entry.get("ahs_nr") or 0),
        "crusher_transfer": bool(entry.get("crusher_transfer")),
        "is_hvac_ducted": bool(entry.get("is_hvac_ducted")),
        "sim_flow_m3h": flow,
    }
    if kind.startswith("ahs_") or kind == "envelope_leak":
        row["fate"] = "bridge_input" if kind.startswith("ahs_") else "skipped"
        row["reason"] = (
            "AHS bookkeeping — feeds synthesize_ahs_recirculation_paths"
            if kind.startswith("ahs_")
            else "envelope_leak skipped by ContamX→Crusher filter"
        )
        return row
    if path_flows_m3h is None:
        row["fate"] = "unknown"
        row["reason"] = "no SIM flows loaded"
        return row
    if abs(flow or 0.0) < _FLOW_EPSILON_M3H:
        row["fate"] = "skipped"
        row["reason"] = "SIM |flow| below epsilon (pressure-driven orifice/fan ~0?)"
        return row
    if from_z not in known_zones or to_z not in known_zones:
        row["fate"] = "skipped"
        row["reason"] = "endpoint not a real Crusher zone"
        return row
    row["fate"] = "kept"
    row["reason"] = "real↔real Contam path with non-zero SIM flow"
    return row


def native_links_report(
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    *,
    filter_efficiency: float = 0.5,
    natural_decay_rate: float = 0.1,
) -> dict[str, Any]:
    """Build native ContamTransportEngine link dump + per-zone degree."""
    eng = ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
        filter_efficiency=filter_efficiency,
        natural_decay_rate=natural_decay_rate,
    )
    links = [
        {
            "path_id": p.path_id,
            "from_zone": p.from_zone,
            "to_zone": p.to_zone,
            "flow_m3h": p.flow_rate_m3h,
            "path_type": p.path_type,
            "is_hvac_ducted": p.is_hvac_ducted,
        }
        for p in eng.airflow_paths
    ]
    degree: dict[str, dict[str, float]] = defaultdict(
        lambda: {"out_m3h": 0.0, "in_m3h": 0.0, "out_edges": 0, "in_edges": 0},
    )
    for link in links:
        degree[link["from_zone"]]["out_m3h"] += link["flow_m3h"]
        degree[link["from_zone"]]["out_edges"] += 1
        degree[link["to_zone"]]["in_m3h"] += link["flow_m3h"]
        degree[link["to_zone"]]["in_edges"] += 1
    return {
        "n_paths": len(links),
        "by_path_type": dict(Counter(l["path_type"] for l in links)),
        "links": sorted(links, key=lambda r: (-r["flow_m3h"], r["path_id"])),
        "zone_degree": {z: dict(v) for z, v in sorted(degree.items())},
    }


def contamx_flow_report(
    path_map: list[dict[str, Any]],
    path_flows_m3h: dict[int, float] | None,
    known_zones: set[str],
) -> dict[str, Any]:
    """Classify path_map fates and synthesize AHS edges when flows exist."""
    classified = [
        classify_contamx_path_fate(e, path_flows_m3h, known_zones)
        for e in sorted(path_map, key=lambda e: int(e["path_nr"]))
    ]
    fate_counts = dict(Counter(r["fate"] for r in classified))
    kept = [r for r in classified if r["fate"] == "kept"]
    zero_real = [
        r for r in classified
        if r["fate"] == "skipped"
        and not str(r["kind"]).startswith("ahs_")
        and r["kind"] != "envelope_leak"
    ]
    synth: list[dict[str, Any]] = []
    if path_flows_m3h is not None:
        for p in synthesize_ahs_recirculation_paths(
            path_map, path_flows_m3h, known_zones,
        ):
            synth.append({
                "path_id": p.path_id,
                "from_zone": p.from_zone,
                "to_zone": p.to_zone,
                "flow_m3h": p.flow_rate_m3h,
                "path_type": p.path_type,
                "is_hvac_ducted": p.is_hvac_ducted,
            })
    degree: dict[str, dict[str, float]] = defaultdict(
        lambda: {"out_m3h": 0.0, "in_m3h": 0.0, "out_edges": 0, "in_edges": 0},
    )
    for link in kept + synth:
        degree[link["from_zone"]]["out_m3h"] += float(link["flow_m3h"])
        degree[link["from_zone"]]["out_edges"] += 1
        degree[link["to_zone"]]["in_m3h"] += float(link["flow_m3h"])
        degree[link["to_zone"]]["in_edges"] += 1
    return {
        "n_path_map": len(path_map),
        "fate_counts": fate_counts,
        "n_kept_real_paths": len(kept),
        "n_synth_ahs_paths": len(synth),
        "n_crusher_paths": len(kept) + len(synth),
        "n_zero_flow_real_candidates": len(zero_real),
        "classified_paths": classified,
        "kept_links": kept,
        "synth_ahs_links": synth,
        "zero_flow_real_candidates": zero_real,
        "zone_degree": {z: dict(v) for z, v in sorted(degree.items())},
        "sim_flows_loaded": path_flows_m3h is not None,
    }


def connectivity_gap(
    native: dict[str, Any],
    contamx: dict[str, Any],
    focus_zones: list[str],
) -> list[dict[str, Any]]:
    """Compare out-degree for focus zones (e.g. injection site)."""
    rows: list[dict[str, Any]] = []
    n_deg = native.get("zone_degree") or {}
    c_deg = contamx.get("zone_degree") or {}
    for z in focus_zones:
        nd = n_deg.get(z, {})
        cd = c_deg.get(z, {})
        rows.append({
            "zone": z,
            "native_out_edges": int(nd.get("out_edges", 0)),
            "native_out_m3h": float(nd.get("out_m3h", 0.0)),
            "contamx_out_edges": int(cd.get("out_edges", 0)),
            "contamx_out_m3h": float(cd.get("out_m3h", 0.0)),
            "bridge_isolated": int(cd.get("out_edges", 0)) == 0 and int(nd.get("out_edges", 0)) > 0,
        })
    return rows


def load_sim_flows(sim_path: str) -> dict[int, float]:
    full = resolve_repo_path(REPO_ROOT, sim_path)
    return SimResults(full).path_volumetric_flow_m3h()


def run_contamx_for_flows(platform_id: str) -> dict[int, float]:
    """Run ContamX on bundled platform.prj and return path_nr → m³/h."""
    files = _platform_files(platform_id)
    prj = resolve_repo_path(REPO_ROOT, files["prj"])
    binary = find_contamx({})
    if binary is None:
        raise ContamXUnavailable("ContamX binary not found")
    if not os.path.isfile(prj):
        raise ContamXUnavailable(f"Missing PRJ: {files['prj']}")
    sim_path = run_contamx(prj, binary, config={})
    return SimResults(sim_path).path_volumetric_flow_m3h()


def build_flow_compare_report(
    platform_id: str,
    *,
    path_flows_m3h: dict[int, float] | None = None,
    inject_zones: list[str] | None = None,
    filter_efficiency: float = 0.5,
    natural_decay_rate: float = 0.1,
) -> dict[str, Any]:
    """Assemble full native vs ContamX flow diagnostic report."""
    files = _platform_files(platform_id)
    spatial = _load_json(files["spatial"])
    airflow = _load_json(files["airflow"])
    path_map = _normalize_path_map_entries(_load_json(files["path_map"]))
    known = {z["id"] for z in spatial.get("zones", [])}
    native = native_links_report(
        spatial, airflow,
        filter_efficiency=filter_efficiency,
        natural_decay_rate=natural_decay_rate,
    )
    contamx = contamx_flow_report(path_map, path_flows_m3h, known)
    focus = inject_zones or sorted(known)[:1]
    return {
        "platform": platform_id,
        "files": files,
        "native": native,
        "contamx": contamx,
        "connectivity_gap": connectivity_gap(native, contamx, focus),
        "hypotheses": _hypotheses(native, contamx, focus),
    }


def _hypotheses(
    native: dict[str, Any],
    contamx: dict[str, Any],
    focus: list[str],
) -> list[str]:
    notes: list[str] = []
    notes.append(
        f"Native Crusher graph has {native['n_paths']} prescribed links; "
        f"ContamX Crusher graph has {contamx['n_crusher_paths']} "
        f"({contamx['n_kept_real_paths']} kept SIM + "
        f"{contamx['n_synth_ahs_paths']} AHS synth)."
    )
    if contamx["n_zero_flow_real_candidates"] and contamx["sim_flows_loaded"]:
        notes.append(
            f"{contamx['n_zero_flow_real_candidates']} real↔real Contam paths "
            "have near-zero SIM flow (orifices/fans dropped by filter)."
        )
    for gap in connectivity_gap(native, contamx, focus):
        if gap["bridge_isolated"]:
            notes.append(
                f"Zone {gap['zone']!r} is ContamX-isolated "
                f"(native out_edges={gap['native_out_edges']}, "
                f"out_m3h={gap['native_out_m3h']:.2f}) — injectate cannot leave "
                "via ContamX Crusher edges."
            )
    if not contamx["sim_flows_loaded"]:
        notes.append(
            "SIM flows not loaded — re-run with ContamX binary or --sim PATH "
            "to confirm zero-flow orifices/fans."
        )
    return notes


def _print_summary(report: dict[str, Any]) -> None:
    native = report["native"]
    cx = report["contamx"]
    print(f"platform: {report['platform']}")
    print(
        f"native paths: {native['n_paths']}  "
        f"by_type={native['by_path_type']}"
    )
    print(
        f"contamx path_map: {cx['n_path_map']}  "
        f"fates={cx['fate_counts']}  "
        f"crusher_paths={cx['n_crusher_paths']} "
        f"(kept={cx['n_kept_real_paths']} + synth={cx['n_synth_ahs_paths']})"
    )
    if cx["sim_flows_loaded"]:
        print(f"zero-flow real candidates: {cx['n_zero_flow_real_candidates']}")
        zeros = cx["zero_flow_real_candidates"][:12]
        for z in zeros:
            print(
                f"  p{z['path_nr']:03d} {z['kind']:22s} "
                f"{z['from_zone']}->{z['to_zone']}  "
                f"flow={z['sim_flow_m3h']:.4g}"
            )
        if cx["synth_ahs_links"]:
            print("AHS synth links (top):")
            for s in sorted(
                cx["synth_ahs_links"], key=lambda r: -r["flow_m3h"],
            )[:8]:
                print(
                    f"  {s['path_id']:40s} "
                    f"{s['from_zone']}->{s['to_zone']}  "
                    f"{s['flow_m3h']:.2f} m3/h"
                )
    print("connectivity gap:")
    for g in report["connectivity_gap"]:
        print(
            f"  {g['zone']}: native_out={g['native_out_edges']} "
            f"({g['native_out_m3h']:.1f} m3/h)  "
            f"contamx_out={g['contamx_out_edges']} "
            f"({g['contamx_out_m3h']:.1f} m3/h)  "
            f"isolated={g['bridge_isolated']}"
        )
    print("hypotheses:")
    for h in report["hypotheses"]:
        print(f"  - {h}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Native ACH vs ContamX SIM per-path flow diagnostic",
    )
    parser.add_argument("--platform", required=True, help="Platform id")
    parser.add_argument(
        "--inject",
        action="append",
        default=[],
        help="ZONE focus for connectivity gap (repeatable); default first zone",
    )
    parser.add_argument(
        "--sim",
        default=None,
        help="Optional pre-run ContamX .SIM path (skips live ContamX)",
    )
    parser.add_argument(
        "--run-contamx",
        action="store_true",
        help="Shell out to ContamX on bundled platform.prj when available",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write full JSON report under this path",
    )
    parser.add_argument("--filter-efficiency", type=float, default=0.5)
    parser.add_argument("--natural-decay-rate", type=float, default=0.1)
    args = parser.parse_args(argv)

    inject_zones = []
    for spec in args.inject:
        zone = spec.split(":", 1)[0]
        inject_zones.append(zone)

    flows: dict[int, float] | None = None
    if args.sim:
        flows = load_sim_flows(args.sim)
    elif args.run_contamx:
        try:
            flows = run_contamx_for_flows(args.platform)
        except ContamXUnavailable as exc:
            print(f"ContamX unavailable: {exc}", file=sys.stderr)
            print("Continuing with path_map topology only (no SIM flows).")

    report = build_flow_compare_report(
        args.platform,
        path_flows_m3h=flows,
        inject_zones=inject_zones or None,
        filter_efficiency=args.filter_efficiency,
        natural_decay_rate=args.natural_decay_rate,
    )
    _print_summary(report)

    if args.output:
        out = resolve_repo_path(REPO_ROOT, args.output)
        prepare_output_directory(os.path.dirname(out) or ".", allowed_roots=(REPO_ROOT,))
        with validated_open(
            out, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2)
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
