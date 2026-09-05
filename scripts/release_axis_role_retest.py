#!/usr/bin/env python3
"""Two re-tests the rebuild invalidated, on one set of runs (#24, #40).

Both conclusions were drawn on a structure that no longer exists, and both
read the same runs, so they are measured together rather than twice.

1. **The faecal-release plateau** (#24). The audit
   (`docs/norovirus/norovirus_parameter_freedom_audit.md` §2) found the
   release term inert from about 8 upward under `none_true` surveillance,
   and §3.1 left open whether the plateau survives with outbreak response
   active. Since then the key was renamed to
   `environmental_release_log10_per_day` and re-declared as a *daily* amount
   converted to the epoch through `SimClock`, so the axis the plateau was
   measured on is not the axis that ships.

2. **The passenger:crew asymmetry** (#40, A5). The parity reported in
   `telemetry_buffer/observation_model/a5_role_asymmetry_diagnosis.md` was
   measured while immunity was assigned by `agent_id % 5`, which capped the
   immune share at 20% and allocated it in agent-id order — the same order
   that separates the passenger block from the crew block. Immunity is now
   sampled without replacement, so the role contrast has to be re-read.

Both arms of surveillance run: the shipped default (syndromic sick-call with
outbreak response live) and the campaign's `none_true` counterfactual, whose
overrides are read from the campaign manifest rather than restated here.

Common random numbers: the same seed set runs at every release value in both
arms, so a difference between two values is not a difference between two
seed draws.

This selects no value and scores no anchor. The VSP ratio near 2.9 appears
in the output only as a printed reference; nothing here may be tuned toward
it, and a ratio that moves the wrong way is a finding about the structure.

Usage::

    python3 scripts/release_axis_role_retest.py --out reports/c7_release_axis_role_retest.json
    python3 scripts/release_axis_role_retest.py --values 4 24 --seeds 2
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    compute_derived_metrics,
    extract_timeseries,
)
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

MANIFEST = (
    REPO_ROOT
    / "picard_framework/runs/mega_cruise_campaign/campaign_manifest.json"
)

# The release ladder: the two values the audit measured as still moving the
# attack rate (4, 6), the value it put the plateau's edge at (8), and three
# points above it. Linear in log10 grams because the field is a log10.
DEFAULT_VALUES: tuple[float, ...] = (4.0, 6.0, 8.0, 12.0, 16.0, 24.0)

SURVEILLANCE_ARMS: tuple[str, ...] = ("syndromic", "none_true")

SCORED_OUTPUTS: tuple[str, ...] = (
    "attack_rate",
    "ever_ill_attack_rate_passenger",
    "ever_ill_attack_rate_crew",
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
    "vsp_posted",
    "peak_epoch",
)

# VSP's passenger:crew ratio, printed as the reference the model is *not*
# tuned to. Source: docs/norovirus/norovirus_model_history.md §9d.
VSP_PASSENGER_CREW_RATIO = 2.9


def surveillance_overrides(arm: str) -> dict[str, object]:
    """Config overrides the campaign manifest declares for one arm."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    configs = manifest["surveillance_configs"]
    if arm not in configs:
        raise KeyError(f"manifest declares no surveillance arm {arm!r}")
    return dict(configs[arm])


def run_point(
    release: float,
    *,
    arm: str,
    seed: int,
    pathogen_id: str,
    bundle: str,
    platform: str,
    epochs: int,
    num_agents: int,
    initial_infected: int,
) -> dict[str, float]:
    """Run one release value, one surveillance arm, one seed."""
    overrides = surveillance_overrides(arm)
    ship_graph = dict(overrides.get("ship_graph") or {})
    ship_graph["num_agents"] = int(num_agents)
    overrides["ship_graph"] = ship_graph
    spec = {
        "schema_version": "1.0.0",
        "description": f"release_axis_role_retest_{arm}",
        "catalog": {"platform_id": platform, "pathogen_bundle_id": bundle},
        "run": {
            "random_seed": int(seed),
            "num_epochs": int(epochs),
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [],
        "incentives": {},
        "config_overrides": overrides,
        "pathogen_overrides": {
            pathogen_id: {
                "environmental_release_log10_per_day": float(release),
                "initial_infected": int(initial_infected),
            },
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
        result = ShipSimulation(picard_spec, display=False).run()
    derived = compute_derived_metrics(extract_timeseries(result.history), num_agents)
    scored = {
        name: float(derived.get(name, 0.0) or 0.0)
        for name in SCORED_OUTPUTS
        if name != "vsp_posted"
    }
    scored["vsp_posted"] = 1.0 if derived.get("vsp_trigger_epoch") is not None else 0.0
    return scored


def summarise(draws: Sequence[dict[str, float]]) -> dict[str, dict[str, float]]:
    """Mean, seed spread and raw draws of each output at one design point."""
    return {
        name: {
            "mean": statistics.fmean([draw[name] for draw in draws]),
            "sd": statistics.stdev([draw[name] for draw in draws])
            if len(draws) > 1
            else 0.0,
            "values": [draw[name] for draw in draws],
        }
        for name in SCORED_OUTPUTS
    }


def role_ratio(point: dict[str, dict[str, float]]) -> dict[str, float | None]:
    """Passenger:crew ratio at one point, on illness and on reports.

    Ratios are taken on the seed means rather than per seed: a seed whose
    crew arm is empty has no ratio, and dropping it would bias what is left.
    ``None`` where the crew mean is zero, which is a measurement about the
    denominator and not a ratio of zero.
    """
    ratios: dict[str, float | None] = {}
    for level in ("ever_ill", "reported_case"):
        passenger = point[f"{level}_attack_rate_passenger"]["mean"]
        crew = point[f"{level}_attack_rate_crew"]["mean"]
        ratios[level] = passenger / crew if crew > 0.0 else None
    return ratios


def plateau_report(
    per_value: dict[str, dict[str, dict[str, float]]],
    edge: float,
) -> dict[str, dict[str, float]]:
    """Whether the axis is flat above the audit's plateau edge.

    Reported as the span of the means above the edge against the seed
    spread at the highest value: a span below one SD is a plateau this
    design cannot distinguish from noise, not a proof of inertness. The
    audit's claim was stronger than that — byte-identical output — so any
    non-zero span already contradicts it.
    """
    above = [key for key in per_value if float(key) >= edge]
    if not above:
        return {}
    top = max(above, key=float)
    report: dict[str, dict[str, float]] = {}
    for name in SCORED_OUTPUTS:
        means = [per_value[key][name]["mean"] for key in above]
        span = max(means) - min(means)
        floor = per_value[top][name]["sd"]
        report[name] = {
            "low": min(means),
            "high": max(means),
            "span": span,
            "top_seed_sd": floor,
            "span_over_floor": (span / floor) if floor > 0.0 else 0.0,
            "identical": span == 0.0,
        }
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command line for the re-test."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--values", type=float, nargs="+", default=None)
    parser.add_argument("--arms", nargs="+", default=list(SURVEILLANCE_ARMS))
    parser.add_argument("--plateau-edge", type=float, default=8.0)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--bundle", default="active_profiles")
    parser.add_argument("--platform", default="expedition_cruise_450")
    parser.add_argument("--num-agents", type=int, default=450)
    parser.add_argument("--initial-infected", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--seed-base", type=int, default=500)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def sweep_arm(
    arm: str,
    values: Sequence[float],
    seeds: Sequence[int],
    run_kwargs: dict[str, object],
) -> dict[str, dict[str, dict[str, float]]]:
    """Every release value at one surveillance arm, over the shared seeds."""
    return {
        f"{value:g}": summarise([
            run_point(value, arm=arm, seed=seed, **run_kwargs)  # type: ignore[arg-type]
            for seed in seeds
        ])
        for value in values
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run both arms of the re-test and write the result as JSON."""
    args = parse_args(argv)
    values = list(args.values) if args.values else list(DEFAULT_VALUES)
    seeds = [args.seed_base + i for i in range(args.seeds)]
    run_kwargs = {
        "pathogen_id": args.pathogen_id,
        "bundle": args.bundle,
        "platform": args.platform,
        "epochs": args.epochs,
        "num_agents": args.num_agents,
        "initial_infected": args.initial_infected,
    }
    arms: dict[str, object] = {}
    for arm in args.arms:
        per_value = sweep_arm(arm, values, seeds, run_kwargs)
        arms[arm] = {
            "per_value": per_value,
            "plateau_above_edge": plateau_report(per_value, args.plateau_edge),
            "role_ratio": {
                key: role_ratio(point) for key, point in per_value.items()
            },
        }
    payload = {
        "factor": "environmental_release_log10_per_day",
        "values": values,
        "plateau_edge": args.plateau_edge,
        "seeds": seeds,
        "run": run_kwargs,
        "vsp_passenger_crew_ratio_reference": VSP_PASSENGER_CREW_RATIO,
        "arms": arms,
    }
    report = json.dumps(payload, indent=2)
    if args.out is not None:
        destination = resolve_repo_path(str(REPO_ROOT), str(args.out))
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        with validated_open(
            destination,
            "w",
            allowed_roots=(str(REPO_ROOT),),
            encoding="utf-8",
        ) as handle:
            handle.write(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
