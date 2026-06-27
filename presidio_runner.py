#!/usr/bin/env python3
"""
presidio_runner.py – Fleet-level meta-simulation entry point (Presidio).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decision_engine import DecisionRound, ExperienceStore, RuleBasedPolicy
from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.run_spec import TelemetryPaths
from presidio.run_spec import PresidioRunSpec
from simulation_utils.paths import prepare_output_directory, resolve_child_path, resolve_repo_path


def _compute_rewards(
    history: list[dict],
    incentives: dict[str, float],
) -> dict[str, float]:
    """Compute per-cruise reward signal for the Presidio experience store.

    This is a reduced-order model (ROM) — a lightweight linear proxy of
    the full multi-objective utility surface.  External optimizers should
    consume the richer utility observation bundles exported via
    ``--export-utility-dir`` rather than relying on this scalar alone.

    Reward components:
        biodefense   = -(infected + symptomatic)          [weighted by biodefense_weight]
        budget       = -0.001 * total_financial_usd       [weighted by budget_weight]
        recovery     = +recovered                         [weighted by recovery_weight]
        ois_penalty  = -ois_cumulative                    [weighted by ois_weight]

    Weights come from ``presidio/data/economics/fleet_economics.json``
    via ``PresidioRunSpec.incentives``.  Defaults: biodefense=1.0,
    budget=0.1, recovery=0.05, ois=0.02.
    """
    if not history:
        return {"fleet": 0.0}
    last = history[-1]
    summary = last.get("summary", {})
    cost = last.get("cost_accounting", {})

    biodefense = -float(summary.get("infected", 0)) - float(summary.get("symptomatic", 0))
    budget_penalty = -0.001 * float(cost.get("total_financial_usd", 0.0))
    recovery_bonus = float(summary.get("recovered", 0))
    ois_penalty = -float(cost.get("operational_impact_cumulative", 0.0))

    w_bio = float(incentives.get("biodefense_weight", 1.0))
    w_cost = float(incentives.get("budget_weight", 0.1))
    w_recovery = float(incentives.get("recovery_weight", 0.05))
    w_ois = float(incentives.get("ois_weight", 0.02))

    fleet_reward = (
        w_bio * biodefense
        + w_cost * budget_penalty
        + w_recovery * recovery_bonus
        + w_ois * ois_penalty
    )
    return {"fleet": fleet_reward, "commanding_officer": fleet_reward * 0.5}


def run(fleet_spec: PresidioRunSpec, *, display: bool = False) -> None:
    experience = ExperienceStore(fleet_spec.experience_store_path)
    experience.load()

    decision_round = DecisionRound(
        actor_roster=fleet_spec.actors or [
            {"actor_id": "command", "role": "commanding_officer"},
            {"actor_id": "medical", "role": "medical_officer"},
        ],
        policies={
            "command": RuleBasedPolicy(),
            "medical": RuleBasedPolicy(),
        },
    )

    prepare_output_directory(
        fleet_spec.output_root,
        allowed_roots=(fleet_spec.repo_root,),
    )

    for cruise_id in range(fleet_spec.num_cruises):
        base_spec = PicardRunSpec.from_picard_json(
            fleet_spec.repo_root,
            fleet_spec.picard_run_spec_path,
        )
        cfg = base_spec.inject_into_cfg()
        merged_social = dict(fleet_spec.picard_run_spec.get("social", {}))
        merged_social.update(fleet_spec.social_config if hasattr(fleet_spec, "social_config") else {})
        if not hasattr(base_spec, "social_config"):
            base_spec.social_config = merged_social
        else:
            base_spec.social_config = merged_social
        cruise_dir = resolve_child_path(
            fleet_spec.output_root,
            f"cruise_{cruise_id:03d}",
        )
        prepare_output_directory(
            cruise_dir,
            allowed_roots=(fleet_spec.repo_root,),
        )

        cruise_social = dict(merged_social)
        cruise_social["cruise_id"] = f"{cruise_id:03d}"

        picard_spec = PicardRunSpec(
            repo_root=base_spec.repo_root,
            random_seed=fleet_spec.seed_base + cruise_id,
            num_epochs=base_spec.num_epochs,
            platform_id=base_spec.platform_id,
            spatial_layout=base_spec.spatial_layout,
            air_flow_paths=base_spec.air_flow_paths,
            pathogen_bundle_id=base_spec.pathogen_bundle_id,
            pathogen_profiles_path=base_spec.pathogen_profiles_path,
            pathogen_profiles=dict(base_spec.pathogen_profiles),
            protocols_path=base_spec.protocols_path,
            resource_costs_path=base_spec.resource_costs_path,
            logging_profile_path=base_spec.logging_profile_path,
            legacy_cfg=cfg,
            actors=fleet_spec.actors,
            incentives=fleet_spec.incentives,
            social_config=cruise_social,
            telemetry=TelemetryPaths(
                repo_root=fleet_spec.repo_root,
                ground_truth=resolve_child_path(cruise_dir, "ground_truth.json"),
                simulation_history=resolve_child_path(cruise_dir, "simulation_history.json"),
                lab_notebook=resolve_child_path(cruise_dir, "artificial_lab_notebook.json"),
            ),
        )

        sim = ShipSimulation(picard_spec, display=display, repo_root=fleet_spec.repo_root)
        sim.initialize()

        for _ in range(picard_spec.num_epochs):
            public: dict = {"epoch": sim.epoch + 1}
            if sim.state and sim.state.simulation_history:
                last = sim.state.simulation_history[-1]
                public = {
                    "epoch": sim.epoch + 1,
                    "agents": last.get("agents", []),
                    "summary": last.get("summary", {}),
                    "stoplights": last.get("reactive_protocols", {}).get("stoplights", {}),
                    "trigger_status": last.get("trigger_status"),
                    "cost_accounting": last.get("cost_accounting", {}),
                    "observation_engine": last.get("observation_engine", {}),
                }
            envelope = decision_round.solve(sim.epoch + 1, public, experience)
            sim.step(envelope)

        sim.finalize(display=display)
        history = sim.state.simulation_history if sim.state else []
        rewards = _compute_rewards(history, fleet_spec.incentives)
        experience.record_cruise(
            cruise_id,
            rewards,
            metadata={"cruise_dir": cruise_dir, "seed": picard_spec.random_seed},
        )
        if display:
            print(f"  Cruise {cruise_id} reward: {rewards}")

    experience.save()
    summary_path = resolve_child_path(fleet_spec.output_root, "fleet_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "num_cruises": fleet_spec.num_cruises,
                "experience_store": fleet_spec.experience_store_path,
                "records": experience.records,
            },
            fh,
            indent=2,
        )
    print(f"Presidio fleet run complete. Summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Presidio fleet meta-simulation")
    parser.add_argument("--fleet-config", default=None)
    parser.add_argument("--cruises", type=int, default=None)
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--export-utility-dir", default=None)
    parser.add_argument("--import-actions-dir", default=None)
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.abspath(__file__))
    if args.fleet_config:
        fleet_spec = PresidioRunSpec.from_fleet_json(
            repo_root,
            resolve_repo_path(repo_root, args.fleet_config),
        )
    else:
        fleet_spec = PresidioRunSpec.default(repo_root)
    if args.cruises is not None:
        fleet_spec.num_cruises = args.cruises

    social_cli: dict = dict(getattr(fleet_spec, "social_config", {}) or {})
    if args.export_utility_dir:
        social_cli["export_utility_dir"] = resolve_repo_path(
            repo_root, args.export_utility_dir,
        )
    if args.import_actions_dir:
        social_cli["import_actions_dir"] = resolve_repo_path(
            repo_root, args.import_actions_dir,
        )
    if social_cli:
        fleet_spec.social_config = social_cli
    run(fleet_spec, display=args.display)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        print(f"\n[ERROR] Missing file: {exc}", file=sys.stderr)
        print("  Hint: verify --fleet-config path and data/ directory contents.", file=sys.stderr)
        sys.exit(1)
    except (KeyError, ValueError) as exc:
        print(f"\n[ERROR] Configuration problem: {exc}", file=sys.stderr)
        print("  Hint: run 'python tools/sanity_checker.py --from-config' to validate.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"\n[ERROR] Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
