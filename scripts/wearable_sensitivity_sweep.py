#!/usr/bin/env python3
"""
wearable_sensitivity_sweep.py — Parametric wearable detection sensitivity sweep.

Varies ``wearable_monitoring.detection_sensitivity_scale`` across a configured
range (default 0.2–0.9) and runs short Picard simulations to compare fleet
wearable alert rates.  Useful when empirical per-pathogen GI accuracy is unknown.

Usage::

    python3 scripts/wearable_sensitivity_sweep.py
    python3 scripts/wearable_sensitivity_sweep.py --values 0.3 0.5 0.7 --epochs 6
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)


def _default_values(cfg: dict) -> list[float]:
    sweep = cfg.get("wearable_monitoring", {}).get("detection_sensitivity_sweep", {})
    raw = sweep.get("values", [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    return [float(v) for v in raw]


def _summarize_wearables(history: list[dict]) -> dict:
    fever_epochs = 0
    anomaly_epochs = 0
    red_epochs = 0
    for rec in history:
        obs = rec.get("observation_engine", {})
        wear = obs.get("wearable_physiological_monitor", {})
        if not wear:
            continue
        summary = wear.get("fleet_summary", {})
        if summary.get("fever_count", 0) > 0:
            fever_epochs += 1
        if summary.get("anomaly_count", 0) > 0:
            anomaly_epochs += 1
        if wear.get("stoplight") == "RED":
            red_epochs += 1
    return {
        "epochs_with_fever": fever_epochs,
        "epochs_with_anomalies": anomaly_epochs,
        "epochs_red_stoplight": red_epochs,
    }


def run_sweep(
    values: list[float],
    *,
    num_epochs: int,
    repo_root: str,
) -> list[dict]:
    cfg = load_config(os.path.join(repo_root, "crusher_labs", "config.yaml"))
    base_epochs = int(
        cfg.get("wearable_monitoring", {})
        .get("detection_sensitivity_sweep", {})
        .get("num_epochs", num_epochs),
    )
    epochs = num_epochs or base_epochs

    results: list[dict] = []
    for scale in values:
        spec = PicardRunSpec.from_legacy_yaml(repo_root=repo_root, num_epochs=epochs)
        wm = spec.legacy_cfg.setdefault("wearable_monitoring", {})
        wm["detection_sensitivity_scale"] = scale

        sim = ShipSimulation(spec, display=False, repo_root=repo_root)
        run_result = sim.run(n_epochs=epochs)
        summary = _summarize_wearables(run_result.history)
        results.append({
            "detection_sensitivity_scale": scale,
            "num_epochs": epochs,
            **summary,
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parametric wearable detection sensitivity sweep",
    )
    parser.add_argument(
        "--values",
        type=float,
        nargs="+",
        default=None,
        help="Sensitivity scale values in [0.2, 0.9] (default: config sweep list)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=0,
        help="Epochs per run (default: config detection_sensitivity_sweep.num_epochs or 6)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output path for sweep results",
    )
    args = parser.parse_args()

    cfg = load_config(os.path.join(REPO_ROOT, "crusher_labs", "config.yaml"))
    values = args.values if args.values else _default_values(cfg)
    results = run_sweep(values, num_epochs=args.epochs, repo_root=REPO_ROOT)

    print(json.dumps(results, indent=2))
    if args.output:
        out_path = resolve_repo_path(REPO_ROOT, args.output)
        prepare_output_directory(os.path.dirname(out_path), allowed_roots=(REPO_ROOT,))
        with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
            fh.write("\n")
        print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
