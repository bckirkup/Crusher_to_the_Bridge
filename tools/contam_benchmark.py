#!/usr/bin/env python3
"""
contam_benchmark.py – native vs ContamX transport divergence report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs a platform's airflow/contaminant transport through both the native
pure-Python ``ContamTransportEngine`` and the opt-in ``ContamXTransportEngine``
(real NIST ContamX solver), injecting an identical pathogen mass and
comparing per-zone concentrations epoch-by-epoch.

This is the "demonstrate Crusher against real CONTAM" harness: it quantifies
how the native heuristic airflow field diverges from the reference solver.

When the ContamX binary (or a runnable project) is unavailable, the tool
reports that ContamX could not run and prints the native trajectory only,
so it is always useful offline.

Usage::

    python tools/contam_benchmark.py \\
        --platform data/platforms/destroyer_baseline \\
        --epochs 12 --inject Bridge:1e6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_runner import ContamXUnavailable  # noqa: E402
from engines.contamx_transport import build_contamx_engine  # noqa: E402
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
# resolve_repo_path used for bundled ContamW PRJ discovery

_SPATIAL_LAYOUT_JSON = "spatial_layout.json"
_AIR_FLOW_PATHS_JSON = "air_flow_paths.json"


def _load_platform(platform_dir: str) -> tuple[dict[str, Any], dict[str, Any]]:
    platform_dir = resolve_repo_path(REPO_ROOT, platform_dir)
    spatial_path = os.path.join(platform_dir, _SPATIAL_LAYOUT_JSON)
    airflow_path = os.path.join(platform_dir, _AIR_FLOW_PATHS_JSON)
    with validated_open(
        spatial_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        spatial = json.load(fh)
    with validated_open(
        airflow_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        airflow = json.load(fh)
    return spatial, airflow


def _initial_mass(
    spatial: dict[str, Any], injections: dict[str, float],
) -> dict[str, float]:
    mass = {z["id"]: 0.0 for z in spatial.get("zones", [])}
    for zone_id, amount in injections.items():
        if zone_id not in mass:
            raise SystemExit(
                f"Injection zone '{zone_id}' not found in spatial layout; "
                f"valid zones: {sorted(mass)}"
            )
        mass[zone_id] = amount
    return mass


def _run_trajectory(
    engine: ContamTransportEngine,
    initial_mass: dict[str, float],
    epochs: int,
) -> list[dict[str, float]]:
    """Return per-epoch zone concentrations [copies/m³]."""
    mass = dict(initial_mass)
    trajectory: list[dict[str, float]] = []
    for _ in range(epochs):
        mass = engine.transport_step(mass)
        concentrations = {}
        for zone_id, m in mass.items():
            node = engine.zone_nodes.get(zone_id)
            concentrations[zone_id] = node.concentration(m) if node else 0.0
        trajectory.append(concentrations)
    return trajectory


def _divergence(
    native: list[dict[str, float]],
    contamx: list[dict[str, float]],
) -> list[dict[str, float]]:
    report = []
    for n_frame, x_frame in zip(native, contamx, strict=True):
        zones = set(n_frame) | set(x_frame)
        diffs = [abs(n_frame.get(z, 0.0) - x_frame.get(z, 0.0)) for z in zones]
        report.append({
            "l1": sum(diffs),
            "linf": max(diffs) if diffs else 0.0,
        })
    return report


def _parse_injections(specs: list[str] | None) -> dict[str, float]:
    injections: dict[str, float] = {}
    for spec in specs or []:
        if ":" not in spec:
            raise SystemExit(f"--inject expects ZONE:AMOUNT, got '{spec}'")
        zone_id, _, amount = spec.partition(":")
        injections[zone_id] = float(amount)
    return injections


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark native vs ContamX transport for a platform.",
    )
    parser.add_argument(
        "--platform", required=True,
        help="Platform directory (e.g. data/platforms/destroyer_baseline).",
    )
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument(
        "--inject", action="append", metavar="ZONE:AMOUNT",
        help="Initial pathogen mass to inject (repeatable).",
    )
    parser.add_argument("--filter-efficiency", type=float, default=0.50)
    parser.add_argument("--natural-decay-rate", type=float, default=0.10)
    args = parser.parse_args(argv)

    spatial, airflow = _load_platform(args.platform)
    injections = _parse_injections(args.inject)
    if not injections:
        # Default: seed the first zone.
        zones = spatial.get("zones", [])
        if zones:
            injections = {zones[0]["id"]: 1.0e6}
    initial_mass = _initial_mass(spatial, injections)

    native = ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
        filter_efficiency=args.filter_efficiency,
        natural_decay_rate=args.natural_decay_rate,
    )
    native_traj = _run_trajectory(native, initial_mass, args.epochs)

    # Prefer bundled ContamW 3.4 PRJ beside the platform when present.
    platform_dir = resolve_repo_path(REPO_ROOT, args.platform)
    bundled_prj = os.path.join(platform_dir, "contam", "platform.prj")
    hvac_cfg: dict[str, Any] = {
        "filter_efficiency": args.filter_efficiency,
        "natural_decay_rate": args.natural_decay_rate,
        "contamx": {},
    }
    if os.path.isfile(bundled_prj):
        hvac_cfg["contamx"]["prj_path"] = os.path.relpath(bundled_prj, REPO_ROOT)

    cfg = {
        "ship_graph": {
            "spatial_layout": os.path.join(args.platform, _SPATIAL_LAYOUT_JSON),
            "air_flow_paths": os.path.join(args.platform, _AIR_FLOW_PATHS_JSON),
        },
        "hvac": hvac_cfg,
    }

    print(f"Platform: {args.platform}")
    if hvac_cfg["contamx"].get("prj_path"):
        print(f"ContamX PRJ: {hvac_cfg['contamx']['prj_path']}")
    print(f"Injections: {injections}")
    print(f"Epochs: {args.epochs}\n")

    try:
        contamx = build_contamx_engine(REPO_ROOT, cfg)
    except ContamXUnavailable as exc:
        print(f"ContamX unavailable ({exc}).")
        print("Reporting native trajectory only:\n")
        final = native_traj[-1] if native_traj else {}
        for zone_id in sorted(final):
            print(f"  {zone_id:>16}: {final[zone_id]:.4g} copies/m^3")
        return

    contamx_traj = _run_trajectory(contamx, initial_mass, args.epochs)
    divergence = _divergence(native_traj, contamx_traj)

    print(f"{'epoch':>6} {'L1 divergence':>16} {'Linf divergence':>16}")
    for epoch, d in enumerate(divergence):
        print(f"{epoch:>6} {d['l1']:>16.4g} {d['linf']:>16.4g}")


if __name__ == "__main__":
    main()
