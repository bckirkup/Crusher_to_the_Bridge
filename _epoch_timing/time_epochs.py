"""Per-epoch wall-time harness for cruise / campaign run specs.

Ported from orphaned ``cursor/epoch-timing-harness`` and extended so
cabin-corridor platforms (expedition / classic / spirit / mega) can be
timed without going through the mega-cruise campaign matrix.

Examples::

    # Direct platform (new models)
    python3 _epoch_timing/time_epochs.py --platform expedition_cruise_450 \\
        --num-agents 450 --epochs 24 --label expedition_n450

    # Mega campaign tier (original mode)
    python3 _epoch_timing/time_epochs.py --tier t1 --epochs 21 --num-agents 2000 \\
        --label n2000

    # Compare all cabin-corridor cruise classes (short budget)
    python3 _epoch_timing/time_epochs.py --compare-cruise --epochs 12 --budget 90
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402

CRUISE_COMPARE_DEFAULTS: tuple[dict[str, Any], ...] = (
    {"platform": "expedition_cruise_450", "num_agents": 450, "label": "expedition_n450"},
    {"platform": "classic_cruise_1900", "num_agents": 1910, "label": "classic_n1910"},
    {"platform": "spirit_cruise_3000", "num_agents": 3000, "label": "spirit_n3000"},
    {"platform": "mega_cruise_5000", "num_agents": 5000, "label": "mega_n5000"},
)


def _build_platform_spec(
    platform_id: str,
    *,
    epochs: int,
    num_agents: int,
    seed: int = 42,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "catalog": {
            "platform_id": platform_id,
            "pathogen_bundle_id": "active_profiles",
        },
        "run": {
            "random_seed": seed,
            "num_epochs": epochs,
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "config_overrides": {"ship_graph": {"num_agents": num_agents}},
        "actors": [],
        "incentives": {},
    }


def resolve_campaign_spec(
    tier: str,
    index: int,
    epochs: int | None,
    num_agents: int | None,
    match: str | None = None,
) -> tuple[str, dict[str, Any]]:
    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        generate_tier_runs,
        load_manifest,
    )

    manifest = load_manifest()
    tier_id = next(t for t in manifest["tiers"] if t.split("_", 1)[0] == tier)
    runs = generate_tier_runs(
        manifest,
        tier_id,
        epochs_override=epochs,
        num_agents_override=num_agents,
    )
    for i, (run_id, spec) in enumerate(runs):
        if match is not None:
            if match in run_id:
                return run_id, spec
        elif i == index:
            return run_id, spec
    raise SystemExit(f"tier {tier}: no run matching index={index} match={match}")


def time_spec(
    *,
    label: str,
    run_id: str,
    spec: dict[str, Any],
    epochs: int,
    budget: float,
) -> dict[str, Any]:
    """Step ``epochs-1`` times (matching original harness loop) under ``budget``."""
    HERE.mkdir(parents=True, exist_ok=True)
    spec = dict(spec)
    spec["run"] = dict(spec.get("run") or {})
    spec["run"].setdefault("history_retention", "compact")
    spec["run"].setdefault("write_ground_truth", False)
    spec["run"]["num_epochs"] = epochs

    spec_path = HERE / f"{label}.spec.json"
    # Simulation run-spec JSON only (no credentials); retained for harness replay.
    # codeql[py/clear-text-storage-sensitive-data]
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    agents_hint = (
        (spec.get("config_overrides") or {}).get("ship_graph", {}).get("num_agents")
    )
    print(
        f"[{label}] run_id={run_id} epochs={epochs} agents={agents_hint}",
        flush=True,
    )
    t0 = time.perf_counter()
    picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
    sim = ShipSimulation(picard_spec, display=False)
    sim.initialize()
    init_s = time.perf_counter() - t0
    n_agents = len(sim.engine.agents) if sim.engine else 0
    print(f"[{label}] init={init_s:.1f}s agents={n_agents}", flush=True)

    rows: list[dict[str, Any]] = []
    loop0 = time.perf_counter()
    epoch = 0
    while epoch + 1 < epochs:
        e0 = time.perf_counter()
        sim.step()
        dt = time.perf_counter() - e0
        epoch += 1
        hist = sim.state.simulation_history[-1] if sim.state.simulation_history else {}
        summ = hist.get("summary", {}) or {}
        infected = summ.get("infected", summ.get("total_infected"))
        rows.append({"epoch": epoch, "seconds": round(dt, 4), "infected": infected})
        elapsed = time.perf_counter() - loop0
        if epoch % 5 == 0 or epoch < 5:
            print(
                f"[{label}] epoch={epoch:4d} dt={dt:7.3f}s "
                f"cum={elapsed:8.1f}s infected={infected}",
                flush=True,
            )
        if elapsed > budget:
            print(f"[{label}] budget {budget}s reached at epoch {epoch}", flush=True)
            break

    total = time.perf_counter() - loop0
    mean_s = total / max(epoch, 1)
    out = {
        "label": label,
        "run_id": run_id,
        "platform_id": (spec.get("catalog") or {}).get("platform_id"),
        "num_agents": n_agents,
        "epochs_requested": epochs,
        "epochs_done": epoch,
        "init_seconds": round(init_s, 3),
        "loop_seconds": round(total, 3),
        "mean_seconds_per_epoch": round(mean_s, 4),
        "per_epoch": rows,
    }
    out_path = HERE / f"{label}.timing.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(
        f"[{label}] DONE epochs={epoch} loop={total:.1f}s "
        f"mean={mean_s:.3f}s/epoch -> {out_path.name}",
        flush=True,
    )
    return out


def compare_cruise(*, epochs: int, budget: float) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for entry in CRUISE_COMPARE_DEFAULTS:
        spec = _build_platform_spec(
            entry["platform"],
            epochs=epochs,
            num_agents=int(entry["num_agents"]),
        )
        results.append(
            time_spec(
                label=entry["label"],
                run_id=f"compare_{entry['platform']}",
                spec=spec,
                epochs=epochs,
                budget=budget,
            )
        )

    summary_rows = []
    for r in results:
        summary_rows.append({
            "label": r["label"],
            "platform_id": r["platform_id"],
            "num_agents": r["num_agents"],
            "epochs_done": r["epochs_done"],
            "init_seconds": r["init_seconds"],
            "mean_seconds_per_epoch": r["mean_seconds_per_epoch"],
            "loop_seconds": r["loop_seconds"],
            "projected_240_epoch_hours": round(
                (r["init_seconds"] + 239 * r["mean_seconds_per_epoch"]) / 3600.0, 3,
            ),
        })

    summary = {
        "mode": "compare_cruise",
        "epochs_requested": epochs,
        "budget_seconds_per_platform": budget,
        "rows": summary_rows,
    }
    if len(summary_rows) >= 2:
        means = [row["mean_seconds_per_epoch"] for row in summary_rows]
        summary["mean_of_means"] = round(statistics.fmean(means), 4)
    path = HERE / "compare_cruise.summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n=== cruise compare summary ===", flush=True)
    for row in summary_rows:
        print(
            f"  {row['platform_id']:24s} n={row['num_agents']:5d} "
            f"mean={row['mean_seconds_per_epoch']:7.3f}s/ep "
            f"~240ep={row['projected_240_epoch_hours']:6.2f}h",
            flush=True,
        )
    print(f"Wrote {path}", flush=True)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", default=None, help="Catalog platform_id (direct mode)")
    ap.add_argument("--tier", default="t1", help="Campaign tier prefix (campaign mode)")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--match", default=None, help="substring of campaign run_id")
    ap.add_argument("--epochs", type=int, default=24)
    ap.add_argument("--num-agents", type=int, default=None)
    ap.add_argument("--budget", type=float, default=1e9, help="stop after N seconds")
    ap.add_argument("--label", default="run")
    ap.add_argument(
        "--compare-cruise",
        action="store_true",
        help="Time expedition/classic/spirit/mega at class populations",
    )
    args = ap.parse_args(argv)

    if args.compare_cruise:
        compare_cruise(epochs=args.epochs, budget=args.budget)
        return 0

    if args.platform:
        if args.num_agents is None:
            print(
                "--num-agents is required with --platform",
                file=sys.stderr,
            )
            return 2
        spec = _build_platform_spec(
            args.platform, epochs=args.epochs, num_agents=args.num_agents,
        )
        time_spec(
            label=args.label,
            run_id=f"platform_{args.platform}",
            spec=spec,
            epochs=args.epochs,
            budget=args.budget,
        )
        return 0

    run_id, spec = resolve_campaign_spec(
        args.tier, args.index, args.epochs, args.num_agents, args.match,
    )
    time_spec(
        label=args.label,
        run_id=run_id,
        spec=spec,
        epochs=args.epochs,
        budget=args.budget,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
