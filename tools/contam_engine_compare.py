#!/usr/bin/env python3
"""
contam_engine_compare.py – native vs ContamX results + speed suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs the Contam comparison jobs under ``data/config/contam_compare/``:

- **transport** — identical pathogen injection; concentration L1/L∞ and
  wall-clock for native vs ContamX transport engines.
- **full_sim** — matched Picard runs; attack-rate / infected / HVAC exposure
  deltas plus wall-clock.

ContamX is optional: when the binary is missing, native-only timing and
results are still reported (exit 0) so CI and offline operators can run the
suite. With ContamX installed under ``third_party/contamx/`` (or via
``CONTAMX_BINARY``), both engines are compared.

Usage::

    python3 tools/contam_engine_compare.py \\
        --suite data/config/contam_compare/suite.json

    python3 tools/contam_engine_compare.py \\
        --job data/config/contam_compare/jobs/destroyer_transport.json

    # Windows operators: run_contam_compare.bat

For per-path SIM vs native ACH diagnosis (why concentrations diverge)::

    python3 tools/contam_flow_compare.py --platform destroyer_baseline \\
        --inject Bridge --run-contamx
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_runner import ContamXUnavailable, find_contamx  # noqa: E402
from engines.contamx_transport import build_contamx_engine  # noqa: E402
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)

_SPATIAL = "spatial_layout.json"
_AIRFLOW = "air_flow_paths.json"


def _load_json(path: str) -> dict[str, Any]:
    full = resolve_repo_path(REPO_ROOT, path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _platform_paths(platform_id: str) -> tuple[str, str, str]:
    safe = validate_path_component(platform_id, label="platform id")
    base = os.path.join("data", "platforms", safe)
    return (
        os.path.join(base, _SPATIAL),
        os.path.join(base, _AIRFLOW),
        os.path.join(base, "contam", "platform.prj"),
    )


def _load_platform(platform_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    spatial_rel, airflow_rel, _prj = _platform_paths(platform_id)
    spatial = _load_json(spatial_rel)
    airflow = _load_json(airflow_rel)
    return spatial, airflow


def _parse_injections(specs: list[str] | None) -> dict[str, float]:
    injections: dict[str, float] = {}
    for spec in specs or []:
        if ":" not in spec:
            raise ValueError(f"inject expects ZONE:AMOUNT, got {spec!r}")
        zone_id, _, amount = spec.partition(":")
        injections[zone_id] = float(amount)
    return injections


def _initial_mass(
    spatial: dict[str, Any], injections: dict[str, float],
) -> dict[str, float]:
    mass = {z["id"]: 0.0 for z in spatial.get("zones", [])}
    for zone_id, amount in injections.items():
        if zone_id not in mass:
            raise ValueError(
                f"Injection zone {zone_id!r} not in platform; "
                f"valid: {sorted(mass)[:20]}…"
            )
        mass[zone_id] = amount
    return mass


def _run_transport_trajectory(
    engine: ContamTransportEngine,
    initial_mass: dict[str, float],
    epochs: int,
) -> list[dict[str, float]]:
    mass = dict(initial_mass)
    traj: list[dict[str, float]] = []
    for _ in range(epochs):
        mass = engine.transport_step(mass)
        frame = {
            zid: (engine.zone_nodes[zid].concentration(m) if zid in engine.zone_nodes else 0.0)
            for zid, m in mass.items()
        }
        traj.append(frame)
    return traj


def _divergence(
    native: list[dict[str, float]],
    contamx: list[dict[str, float]],
) -> dict[str, Any]:
    per_epoch: list[dict[str, float]] = []
    for n_frame, x_frame in zip(native, contamx, strict=True):
        zones = set(n_frame) | set(x_frame)
        diffs = [abs(n_frame.get(z, 0.0) - x_frame.get(z, 0.0)) for z in zones]
        per_epoch.append({
            "l1": sum(diffs),
            "linf": max(diffs) if diffs else 0.0,
        })
    return {
        "per_epoch": per_epoch,
        "final_l1": per_epoch[-1]["l1"] if per_epoch else 0.0,
        "final_linf": per_epoch[-1]["linf"] if per_epoch else 0.0,
        "mean_l1": statistics.fmean(e["l1"] for e in per_epoch) if per_epoch else 0.0,
    }


def _path_inventory(
    engine: ContamTransportEngine,
    injections: dict[str, float],
    *,
    max_edges: int = 24,
) -> dict[str, Any]:
    """Summarize Crusher airflow edges so sparse ContamX graphs are visible.

    When ContamX drops zero-SIM real↔real paths, ``n_paths`` alone is
    ambiguous (AHS synth vs residual fans). This inventory lists path types,
    injection-zone out-degree, and a capped edge sample.
    """
    by_type = Counter(p.path_type for p in engine.airflow_paths)
    out_m3h: dict[str, float] = defaultdict(float)
    out_degree: dict[str, int] = defaultdict(int)
    edges: list[dict[str, Any]] = []
    for path in engine.airflow_paths:
        out_degree[path.from_zone] += 1
        out_m3h[path.from_zone] += float(path.flow_rate_m3h)
        edges.append({
            "path_id": path.path_id,
            "from": path.from_zone,
            "to": path.to_zone,
            "m3h": round(float(path.flow_rate_m3h), 6),
            "type": path.path_type,
            "ducted": bool(path.is_hvac_ducted),
        })
    edges.sort(key=lambda e: (-e["m3h"], e["from"], e["to"], e["path_id"]))

    inject_zones = sorted(injections)
    connectivity: list[dict[str, Any]] = []
    for zone in inject_zones:
        degree = int(out_degree.get(zone, 0))
        connectivity.append({
            "zone": zone,
            "out_degree": degree,
            "out_m3h": round(float(out_m3h.get(zone, 0.0)), 6),
            "isolated": degree == 0,
        })

    return {
        "n_paths": len(engine.airflow_paths),
        "by_type": dict(sorted(by_type.items())),
        "injection_connectivity": connectivity,
        "edges_sample": edges[:max_edges],
        "edges_truncated": max(0, len(edges) - max_edges),
    }


def _time_calls(fn, repeats: int) -> dict[str, float]:
    samples: list[float] = []
    result: Any = None
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - t0)
    return {
        "repeats": len(samples),
        "seconds_mean": statistics.fmean(samples),
        "seconds_min": min(samples),
        "seconds_max": max(samples),
        "seconds_stdev": statistics.pstdev(samples) if len(samples) > 1 else 0.0,
        "_result": result,
    }


def _hvac_cfg(job: dict[str, Any], platform_id: str) -> dict[str, Any]:
    _spatial_rel, _airflow_rel, prj_rel = _platform_paths(platform_id)
    cfg: dict[str, Any] = {
        "filter_efficiency": float(job.get("filter_efficiency", 0.50)),
        "natural_decay_rate": float(job.get("natural_decay_rate", 0.10)),
        "contamx": {},
    }
    prj_full = resolve_repo_path(REPO_ROOT, prj_rel)
    if os.path.isfile(prj_full):
        cfg["contamx"]["prj_path"] = prj_rel
    binary = find_contamx({"hvac": cfg})
    if binary:
        # Prefer discovered path so ContamXTransportEngine uses the same binary.
        cfg["contamx"]["binary_path"] = binary
    return cfg


def run_transport_job(job: dict[str, Any]) -> dict[str, Any]:
    platform_id = job["platform"]
    epochs = int(job.get("epochs", 12))
    repeats = int(job.get("repeats", 3))
    spatial, airflow = _load_platform(platform_id)
    injections = _parse_injections(job.get("inject"))
    if not injections:
        zones = spatial.get("zones", [])
        if zones:
            injections = {zones[0]["id"]: 1.0e6}
    initial_mass = _initial_mass(spatial, injections)
    hvac = _hvac_cfg(job, platform_id)

    def _native_once():
        eng = ContamTransportEngine(
            spatial_layout=spatial,
            air_flow_paths=airflow,
            filter_efficiency=hvac["filter_efficiency"],
            natural_decay_rate=hvac["natural_decay_rate"],
        )
        return _run_transport_trajectory(eng, initial_mass, epochs)

    native_timing = _time_calls(_native_once, repeats)
    native_traj = native_timing.pop("_result")

    report: dict[str, Any] = {
        "id": job.get("id", platform_id),
        "mode": "transport",
        "platform": platform_id,
        "epochs": epochs,
        "injections": injections,
        "native": {
            "timing": native_timing,
            "final_concentrations": native_traj[-1] if native_traj else {},
            "n_paths": None,
        },
        "contamx": None,
        "divergence": None,
        "contamx_available": False,
    }
    # Path count from a fresh native engine
    native_eng = ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
        filter_efficiency=hvac["filter_efficiency"],
        natural_decay_rate=hvac["natural_decay_rate"],
    )
    report["native"]["n_paths"] = len(native_eng.airflow_paths)
    report["native"]["path_inventory"] = _path_inventory(native_eng, injections)

    cfg = {
        "ship_graph": {
            "spatial_layout": _platform_paths(platform_id)[0],
            "air_flow_paths": _platform_paths(platform_id)[1],
        },
        "hvac": {**hvac, "transport_engine": "contamx"},
    }

    try:
        def _contamx_once():
            eng = build_contamx_engine(REPO_ROOT, cfg)
            return _run_transport_trajectory(eng, initial_mass, epochs), eng

        cx_timing = _time_calls(_contamx_once, repeats)
        contamx_traj, eng = cx_timing.pop("_result")
        report["contamx_available"] = True
        report["contamx"] = {
            "timing": cx_timing,
            "final_concentrations": contamx_traj[-1] if contamx_traj else {},
            "n_paths": len(eng.airflow_paths),
            "path_inventory": _path_inventory(eng, injections),
            "binary": find_contamx(cfg),
        }
        report["divergence"] = _divergence(native_traj, contamx_traj)
        nt = native_timing["seconds_mean"]
        ct = cx_timing["seconds_mean"]
        report["speedup_native_over_contamx"] = (ct / nt) if nt > 0 else None
        # Highlight ContamX injection isolation (common after zero-SIM drops).
        cx_conn = report["contamx"]["path_inventory"]["injection_connectivity"]
        report["contamx_injection_isolated"] = any(
            c.get("isolated") for c in cx_conn
        )
    except ContamXUnavailable as exc:
        report["contamx_error"] = str(exc)

    return report


def run_full_sim_job(job: dict[str, Any]) -> dict[str, Any]:
    from tools.contam_outcome_compare import _build_spec, _summarize
    from picard_framework.simulation.ship_simulation import ShipSimulation

    platform_id = job["platform"]
    epochs = int(job.get("epochs", 12))
    seed = int(job.get("seed", 42))
    repeats = int(job.get("repeats", 2))

    def _run(engine_name: str) -> tuple[dict[str, Any], float]:
        spec = _build_spec(
            platform_id,
            epochs=epochs,
            seed=seed,
            transport_engine=engine_name,
        )
        t0 = time.perf_counter()
        sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
        result = sim.run(n_epochs=epochs)
        elapsed = time.perf_counter() - t0
        summary = _summarize(sim, result, engine_name)
        return summary, elapsed

    native_samples: list[float] = []
    native_summary: dict[str, Any] | None = None
    for _ in range(max(1, repeats)):
        summary, elapsed = _run("native")
        native_samples.append(elapsed)
        native_summary = summary

    report: dict[str, Any] = {
        "id": job.get("id", platform_id),
        "mode": "full_sim",
        "platform": platform_id,
        "epochs": epochs,
        "seed": seed,
        "native": {
            "summary": native_summary,
            "timing": {
                "repeats": len(native_samples),
                "seconds_mean": statistics.fmean(native_samples),
                "seconds_min": min(native_samples),
                "seconds_max": max(native_samples),
                "seconds_stdev": (
                    statistics.pstdev(native_samples) if len(native_samples) > 1 else 0.0
                ),
            },
        },
        "contamx": None,
        "delta": None,
        "contamx_available": False,
    }

    if find_contamx() is None:
        report["contamx_error"] = "No ContamX binary found"
        return report

    try:
        cx_samples: list[float] = []
        cx_summary: dict[str, Any] | None = None
        for _ in range(max(1, repeats)):
            summary, elapsed = _run("contamx")
            # ContamX may have fallen back silently under transport_engine=contamx
            if summary.get("contam_engine_class") == "ContamTransportEngine":
                raise ContamXUnavailable(
                    "ContamX requested but native engine was used (binary/prj failed)"
                )
            cx_samples.append(elapsed)
            cx_summary = summary
        report["contamx_available"] = True
        report["contamx"] = {
            "summary": cx_summary,
            "timing": {
                "repeats": len(cx_samples),
                "seconds_mean": statistics.fmean(cx_samples),
                "seconds_min": min(cx_samples),
                "seconds_max": max(cx_samples),
                "seconds_stdev": (
                    statistics.pstdev(cx_samples) if len(cx_samples) > 1 else 0.0
                ),
            },
        }
        delta: dict[str, Any] = {}
        assert native_summary is not None and cx_summary is not None
        for key in (
            "attack_rate", "n_infected",
            "hvac_downstream_exposure_events", "operational_impact_score",
        ):
            nv, xv = native_summary.get(key), cx_summary.get(key)
            if nv is not None and xv is not None:
                try:
                    delta[key] = xv - nv
                except TypeError:
                    pass
        report["delta"] = delta
        nt = report["native"]["timing"]["seconds_mean"]
        ct = report["contamx"]["timing"]["seconds_mean"]
        report["speedup_native_over_contamx"] = (ct / nt) if nt > 0 else None
    except ContamXUnavailable as exc:
        report["contamx_error"] = str(exc)

    return report


def run_job(job: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = {**(defaults or {}), **job}
    mode = str(merged.get("mode", "transport")).lower()
    if mode == "transport":
        return run_transport_job(merged)
    if mode in ("full_sim", "fullsim", "picard"):
        return run_full_sim_job(merged)
    raise ValueError(f"Unknown job mode {mode!r}")


def load_suite(suite_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suite = _load_json(suite_path)
    suite_dir = os.path.dirname(resolve_repo_path(REPO_ROOT, suite_path))
    jobs: list[dict[str, Any]] = []
    for entry in suite.get("jobs", []):
        if isinstance(entry, str):
            job_path = entry if os.path.isabs(entry) else os.path.join(
                os.path.relpath(suite_dir, REPO_ROOT), entry,
            )
            # Normalize to repo-relative
            job_path = os.path.normpath(job_path)
            job = _load_json(job_path)
        elif isinstance(entry, dict):
            job = entry
        else:
            raise ValueError(f"Invalid suite job entry: {entry!r}")
        jobs.append(job)
    return suite, jobs


def _print_job_summary(report: dict[str, Any]) -> None:
    print(f"\n=== {report.get('id')} ({report.get('mode')}) "
          f"platform={report.get('platform')} ===")
    native = report.get("native") or {}
    n_time = (native.get("timing") or {}).get("seconds_mean")
    print(f"  native  mean wall time: {n_time:.4f}s" if n_time is not None else "  native: n/a")
    if report.get("contamx_available") and report.get("contamx"):
        c_time = (report["contamx"].get("timing") or {}).get("seconds_mean")
        print(f"  contamx mean wall time: {c_time:.4f}s" if c_time is not None else "")
        speed = report.get("speedup_native_over_contamx")
        if speed is not None:
            print(f"  native is {speed:.2f}x ContamX wall time "
                  f"(>1 means ContamX slower)")
        if report.get("mode") == "transport" and report.get("divergence"):
            div = report["divergence"]
            print(f"  final L1={div['final_l1']:.4g}  L∞={div['final_linf']:.4g}  "
                  f"mean L1={div['mean_l1']:.4g}")
            n_paths = (native.get("n_paths"),
                       (report.get("contamx") or {}).get("n_paths"))
            print(f"  n_paths native/contamx: {n_paths[0]}/{n_paths[1]}")
            inv = (report.get("contamx") or {}).get("path_inventory") or {}
            if inv.get("by_type"):
                print(f"  ContamX path types: {inv['by_type']}")
            for conn in inv.get("injection_connectivity") or []:
                flag = " ISOLATED" if conn.get("isolated") else ""
                print(
                    f"  ContamX inject {conn['zone']}: "
                    f"out_degree={conn['out_degree']} "
                    f"out_m3h={conn['out_m3h']}{flag}"
                )
        if report.get("delta"):
            print(f"  outcome delta (contamx-native): {report['delta']}")
    else:
        print(f"  ContamX skipped: {report.get('contamx_error', 'unavailable')}")
        inv = (native.get("path_inventory") or {})
        if inv.get("by_type"):
            print(f"  native path types: {inv['by_type']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare native vs ContamX engines (results + speed).",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--suite", help="Path to suite.json")
    src.add_argument("--job", help="Path to a single job JSON")
    parser.add_argument(
        "--output-dir", default="",
        help="Override report output directory (default from suite or "
             "telemetry_buffer/contam_compare).",
    )
    parser.add_argument(
        "--json-out", default="",
        help="Optional explicit report file path under the repo.",
    )
    args = parser.parse_args(argv)

    binary = find_contamx()
    print(f"Repo: {REPO_ROOT}")
    print(f"ContamX binary: {binary or '(not found — native-only runs)'}")

    defaults: dict[str, Any] = {}
    jobs: list[dict[str, Any]]
    suite_meta: dict[str, Any] = {}
    if args.suite:
        suite_meta, jobs = load_suite(args.suite)
        defaults = dict(suite_meta.get("defaults") or {})
        out_dir = args.output_dir or suite_meta.get(
            "output_dir", "telemetry_buffer/contam_compare",
        )
    else:
        jobs = [_load_json(args.job)]
        out_dir = args.output_dir or "telemetry_buffer/contam_compare"

    reports = [run_job(job, defaults) for job in jobs]
    for report in reports:
        _print_job_summary(report)

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contamx_binary": binary,
        "suite": args.suite or None,
        "jobs": reports,
    }

    if args.json_out:
        out_path = resolve_repo_path(REPO_ROOT, args.json_out)
        parent = os.path.dirname(out_path)
        if parent:
            prepare_output_directory(parent, allowed_roots=(REPO_ROOT,))
    else:
        out_dir_full = resolve_repo_path(REPO_ROOT, out_dir)
        prepare_output_directory(out_dir_full, allowed_roots=(REPO_ROOT,))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(out_dir_full, f"compare_{stamp}.json")

    with validated_open(
        out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        json.dump(bundle, fh, indent=2, default=str)
        fh.write("\n")
    print(f"\nWrote report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
