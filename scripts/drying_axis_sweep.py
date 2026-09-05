#!/usr/bin/env python3
"""One-factor sweep of the hand-to-surface drying axis (#42).

`hand_to_surface_drying_multiplier` ships neutral (1.0) over a sourced
interval [0.008, 1.0] whose low end is Tuladhar 2013's dried/immediate
transfer ratio. Which drying state applies to a hand that is continuously
recontaminated by its own shedding is not measured, so the register carries
the axis rather than a value. This sweep reports what the axis *does*: the
span it opens on the scored outputs, against the seed-to-seed spread at the
shipped endpoint.

It is not the Morris screen (#36) and not the admissible-region gate (#37).
One factor moves; every other parameter stays at its shipped profile value,
so the comparison is against what ships rather than against a box centre. It
selects no value, and nothing it prints may be written back into a profile:
an axis that moves an output is not thereby licensed, and one that does not
is not thereby freezable.

Common random numbers: the same seed set runs at every value, so the
difference between two values is not a difference between two seed draws.

Usage::

    python3 scripts/drying_axis_sweep.py --out reports/drying_axis_sweep.json
    python3 scripts/drying_axis_sweep.py --values 0.008 1.0 --seeds 4
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

# The sourced interval, log-spaced: the low end is a ratio of transfer
# efficiencies, so the decades between the ends are the axis, not the
# arithmetic distance.
DEFAULT_VALUES: tuple[float, ...] = (0.008, 0.0268, 0.0894, 0.299, 1.0)

SCORED_OUTPUTS: tuple[str, ...] = (
    "attack_rate",
    "ever_ill_attack_rate_passenger",
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
    "vsp_posted",
    "peak_epoch",
)


def run_point(
    multiplier: float,
    *,
    seed: int,
    pathogen_id: str,
    bundle: str,
    platform: str,
    epochs: int,
    num_agents: int,
) -> dict[str, float]:
    """Run one drying value at one seed and return the scored outputs."""
    spec = {
        "schema_version": "1.0.0",
        "description": "drying_axis_sweep",
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
        "config_overrides": {"ship_graph": {"num_agents": int(num_agents)}},
        "pathogen_overrides": {
            pathogen_id: {"hand_to_surface_drying_multiplier": float(multiplier)},
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


def sweep_value(
    multiplier: float,
    seeds: Sequence[int],
    **run_kwargs: object,
) -> dict[str, dict[str, float]]:
    """Mean and seed spread of each scored output at one drying value."""
    draws = [
        run_point(multiplier, seed=seed, **run_kwargs)  # type: ignore[arg-type]
        for seed in seeds
    ]
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


def _ratio(span: float, floor: float) -> float:
    """Span in floor units. An unmoved output is 0 even where the floor is 0."""
    if span == 0.0:
        return 0.0
    return span / floor if floor > 0.0 else float("inf")


def axis_span(
    per_value: dict[str, dict[str, dict[str, float]]],
    shipped_key: str,
) -> dict[str, dict[str, float]]:
    """Span each output opens across the axis, against the shipped seed spread.

    `span_over_floor` below 1 means the whole sourced interval moves the
    output less than re-seeding it does at the shipped endpoint. That is a
    statement about this design's resolution, not a licence to freeze the
    axis.
    """
    report: dict[str, dict[str, float]] = {}
    for name in SCORED_OUTPUTS:
        means = [per_value[key][name]["mean"] for key in per_value]
        floor = per_value[shipped_key][name]["sd"]
        span = max(means) - min(means)
        report[name] = {
            "low": min(means),
            "high": max(means),
            "span": span,
            "shipped_seed_sd": floor,
            "span_over_floor": _ratio(span, floor),
        }
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command line for the sweep."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--values", type=float, nargs="+", default=None)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--bundle", default="active_profiles")
    parser.add_argument("--platform", default="mega_cruise_5000")
    parser.add_argument("--num-agents", type=int, default=450)
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--seed-base", type=int, default=500)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the sweep and write the result as JSON."""
    args = parse_args(argv)
    values = list(args.values) if args.values else list(DEFAULT_VALUES)
    seeds = [args.seed_base + i for i in range(args.seeds)]
    run_kwargs = {
        "pathogen_id": args.pathogen_id,
        "bundle": args.bundle,
        "platform": args.platform,
        "epochs": args.epochs,
        "num_agents": args.num_agents,
    }
    per_value = {
        f"{value:g}": sweep_value(value, seeds, **run_kwargs) for value in values
    }
    payload = {
        "factor": "hand_to_surface_drying_multiplier",
        "interval": [0.008, 1.0],
        "values": values,
        "seeds": seeds,
        "run": run_kwargs,
        "per_value": per_value,
        "axis_span": axis_span(per_value, f"{values[-1]:g}"),
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
