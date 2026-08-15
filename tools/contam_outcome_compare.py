#!/usr/bin/env python3
"""
contam_outcome_compare.py – native vs ContamX full-simulation outcomes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs matched Picard ship simulations with ``hvac.transport_engine`` set to
``native`` and ``contamx``, then reports epidemic / operational deltas.

Degrades cleanly when ContamX is unavailable (prints native-only summary).

Usage::

    python3 tools/contam_outcome_compare.py \\
        --platform destroyer_baseline --epochs 6 --seed 42
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_runner import ContamXUnavailable, find_contamx  # noqa: E402
from picard_framework.catalog.registry import CatalogRegistry  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)


def _build_spec(
    platform_id: str,
    *,
    epochs: int,
    seed: int,
    transport_engine: str,
    prj_path: str = "",
) -> PicardRunSpec:
    safe_platform = validate_path_component(platform_id, label="platform id")
    reg = CatalogRegistry.from_repo(REPO_ROOT)
    if safe_platform not in reg.platforms:
        raise SystemExit(
            f"Unknown platform '{safe_platform}'. "
            f"Known: {sorted(reg.platforms)}"
        )
    platform = reg.platforms[safe_platform]

    spec = PicardRunSpec.from_legacy_yaml(REPO_ROOT, num_epochs=epochs)
    spec.random_seed = seed
    spec.num_epochs = epochs
    spec.platform_id = safe_platform
    spec.spatial_layout = platform.spatial_layout
    spec.air_flow_paths = platform.air_flow_paths

    cfg = copy.deepcopy(spec.legacy_cfg)
    cfg["random_seed"] = seed
    cfg["num_epochs"] = epochs
    cfg.setdefault("hvac", {})
    cfg["hvac"]["transport_engine"] = transport_engine
    cfg["hvac"].setdefault("contamx", {})
    if prj_path:
        # Containment-checked relative/absolute path under the repo root.
        cfg["hvac"]["contamx"]["prj_path"] = os.path.relpath(
            resolve_repo_path(REPO_ROOT, prj_path), REPO_ROOT,
        )
    else:
        bundled_rel = os.path.join(
            "data", "platforms", safe_platform, "contam", "platform.prj",
        )
        bundled = resolve_repo_path(REPO_ROOT, bundled_rel)
        if os.path.isfile(bundled):
            cfg["hvac"]["contamx"]["prj_path"] = bundled_rel
    spec.legacy_cfg = cfg
    return spec


def _summarize(sim: ShipSimulation, result: Any, engine_label: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "transport_engine": engine_label,
        "num_epochs": result.num_epochs,
        "final_trigger_status": result.final_trigger_status,
    }

    engine = sim.engine
    if engine is not None and getattr(engine, "agents", None):
        agents = engine.agents
        n = len(agents)
        infected = 0
        for ag in agents:
            status = str(getattr(ag, "infection_status", "") or "").lower()
            if status and status not in ("susceptible", "s", "none"):
                infected += 1
        summary["n_agents"] = n
        summary["n_infected"] = infected
        summary["attack_rate"] = infected / n if n else 0.0

    state = sim.state
    if state is not None:
        cost = getattr(state, "cost_accounting", None)
        if isinstance(cost, dict):
            summary["operational_impact_score"] = cost.get("operational_impact_score")

    hvac_exposures = 0
    for epoch in result.history or []:
        if not isinstance(epoch, dict):
            continue
        tx = epoch.get("transmission_summary") or epoch.get("transmission") or {}
        if isinstance(tx, dict):
            hvac_exposures += len(tx.get("hvac_downstream_exposures", []) or [])
        # Also scan nested exposure lists
        for key in ("hvac_downstream_exposures", "exposures"):
            val = epoch.get(key)
            if isinstance(val, list):
                hvac_exposures += len(val)
    summary["hvac_downstream_exposure_events"] = hvac_exposures

    contam = sim.contam_engine
    if contam is not None:
        summary["contam_engine_class"] = type(contam).__name__
        summary["n_airflow_paths"] = len(getattr(contam, "airflow_paths", []) or [])

    return summary


def _run_once(
    platform_id: str,
    *,
    epochs: int,
    seed: int,
    transport_engine: str,
    prj_path: str = "",
) -> dict[str, Any]:
    spec = _build_spec(
        platform_id,
        epochs=epochs,
        seed=seed,
        transport_engine=transport_engine,
        prj_path=prj_path,
    )
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    result = sim.run(n_epochs=epochs)
    return _summarize(sim, result, transport_engine)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare full-sim outcomes: native vs ContamX transport.",
    )
    parser.add_argument(
        "--platform", default="destroyer_baseline",
        help="Platform id under data/platforms/ (default: destroyer_baseline).",
    )
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--prj-path", default="",
        help="Optional ContamW 3.4 .prj override for ContamX path.",
    )
    parser.add_argument(
        "--json-out", default="",
        help="Optional path to write the comparison JSON report.",
    )
    args = parser.parse_args(argv)

    print(f"Platform: {args.platform}")
    print(f"Epochs: {args.epochs}  seed: {args.seed}")

    native = _run_once(
        args.platform, epochs=args.epochs, seed=args.seed,
        transport_engine="native",
    )
    print("\nNative engine outcomes:")
    print(json.dumps(native, indent=2, default=str))

    report: dict[str, Any] = {"native": native, "contamx": None, "delta": None}

    try:
        if find_contamx() is None:
            raise ContamXUnavailable("No ContamX binary on PATH / config")
        contamx = _run_once(
            args.platform, epochs=args.epochs, seed=args.seed,
            transport_engine="contamx",
            prj_path=args.prj_path,
        )
        print("\nContamX engine outcomes:")
        print(json.dumps(contamx, indent=2, default=str))
        report["contamx"] = contamx
        delta: dict[str, Any] = {}
        for key in (
            "attack_rate", "n_infected",
            "hvac_downstream_exposure_events", "operational_impact_score",
        ):
            nv, xv = native.get(key), contamx.get(key)
            if nv is not None and xv is not None:
                try:
                    delta[key] = xv - nv
                except TypeError:
                    # Omit deltas for fields that cannot be subtracted.
                    pass
        report["delta"] = delta
        print("\nDelta (contamx - native):")
        print(json.dumps(delta, indent=2, default=str))
    except ContamXUnavailable as exc:
        print(f"\nContamX unavailable ({exc}). Native-only report above.")
        report["contamx_error"] = str(exc)

    if args.json_out:
        # Sonar pythonsecurity:S8707 — constrain CLI output path to the repo.
        out = resolve_repo_path(REPO_ROOT, args.json_out)
        parent = os.path.dirname(out)
        if parent:
            prepare_output_directory(parent, allowed_roots=(REPO_ROOT,))
        with validated_open(
            out, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, default=str)
            fh.write("\n")
        print(f"\nWrote {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
