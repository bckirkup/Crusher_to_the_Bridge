"""Per-cruise decision runtime state for ShipSimulation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from decision_engine.agent_profile import (
    AgentProfile,
    build_profiles_for_agents,
    default_bundle_path,
    load_agent_profile_bundle,
)
from decision_engine.context import EpochDecisionContext
from decision_engine.information.diffusion import InformationDiffusionEngine
from decision_engine.lived_experience import AgentLivedExperienceStore
from decision_engine.social.class_interactions import ClassInteractionMatrix
from decision_engine.social.contact_graph import ContactGraphBuilder
from decision_engine.intelligence import default_timeline_path, load_global_health_timeline
from decision_engine.policy import build_policies_from_config
from decision_engine.stackelberg.round import StackelbergRound
from simulation_utils.paths import resolve_repo_path


@dataclass
class DecisionRuntime:
    repo_root: str
    social_config: dict[str, Any] = field(default_factory=dict)
    profiles: dict[int, AgentProfile] = field(default_factory=dict)
    contact_graph: ContactGraphBuilder = field(default_factory=ContactGraphBuilder)
    lived_store: AgentLivedExperienceStore = field(default_factory=AgentLivedExperienceStore)
    information_engine: InformationDiffusionEngine = field(
        default_factory=InformationDiffusionEngine,
    )
    decision_ctx: EpochDecisionContext = field(default_factory=EpochDecisionContext)
    class_matrix: ClassInteractionMatrix | None = None
    global_health_timeline: dict[str, Any] = field(default_factory=dict)
    stackelberg: StackelbergRound | None = None
    all_protocol_ids: list[str] = field(default_factory=list)
    sop_events_buffer: list[dict[str, Any]] = field(default_factory=list)
    agent_granularity: str = "per_agent"
    decision_detail_telemetry: bool = False

    @staticmethod
    def _resolve_social_config(run_spec: Any) -> dict[str, Any]:
        social = getattr(run_spec, "social_config", None) or {}
        if not social and hasattr(run_spec, "legacy_cfg"):
            social = run_spec.legacy_cfg.get("social", {})
        return social

    @staticmethod
    def _load_agent_profiles(
        run_spec: Any,
        engine: Any,
        profile_path: str,
    ) -> dict[int, AgentProfile]:
        if not os.path.isfile(profile_path):
            return {}
        bundle = load_agent_profile_bundle(profile_path)
        wm = run_spec.legacy_cfg.get("wearable_monitoring", {})
        raw_map = wm.get("class_device_map", {})
        device_map: dict[str, str] = {}
        if isinstance(raw_map, dict):
            device_map = raw_map
        elif isinstance(raw_map, list):
            for entry in raw_map:
                if isinstance(entry, dict):
                    device_map[str(entry.get("agent_class", ""))] = str(
                        entry.get("device_id", ""),
                    )
        mp = run_spec.legacy_cfg.get("multi_pathogen", {})
        imm_frac = float(mp.get("immunocompromised_fraction", 0.0))
        return build_profiles_for_agents(
            engine.agents, bundle, np.random.default_rng(run_spec.random_seed),
            class_device_map=device_map,
            immunocompromised_fraction=imm_frac,
        )

    @staticmethod
    def _load_json_if_exists(repo: str, path_key: str, default_path_fn: Any) -> str | None:
        resolved = resolve_repo_path(repo, path_key or default_path_fn(repo))
        return resolved if os.path.isfile(resolved) else None

    @classmethod
    def from_run_spec(cls, run_spec: Any, engine: Any, proto_ctx: Any) -> DecisionRuntime:
        repo = run_spec.repo_root
        social = cls._resolve_social_config(run_spec)
        rt = cls(repo_root=repo, social_config=social)

        profile_path = resolve_repo_path(
            repo, social.get("agent_profile_bundle") or default_bundle_path(repo),
        )
        rt.profiles = cls._load_agent_profiles(run_spec, engine, profile_path)

        ci_path = cls._load_json_if_exists(
            repo, social.get("class_interactions"), ClassInteractionMatrix.default_path,
        )
        if ci_path:
            rt.class_matrix = ClassInteractionMatrix.from_json(ci_path)

        diff_path = cls._load_json_if_exists(
            repo, social.get("information_diffusion"), InformationDiffusionEngine.default_path,
        )
        if diff_path:
            rt.information_engine = InformationDiffusionEngine.from_config_path(diff_path)

        gh_path = cls._load_json_if_exists(
            repo, social.get("global_health_timeline"), default_timeline_path,
        )
        if gh_path:
            rt.global_health_timeline = load_global_health_timeline(gh_path)

        rt.all_protocol_ids = [
            p.protocol_id for p in proto_ctx.standing_protocols
        ]

        agent_ids = [a.agent_id for a in engine.agents]
        classes = {a.agent_id: a.agent_class for a in engine.agents}
        rt.information_engine.initialize_agents(
            agent_ids, classes, social.get("initial_beliefs"),
        )

        telem = social.get("telemetry", {})
        rt.decision_detail_telemetry = bool(telem.get("decision_detail", False))
        rt.agent_granularity = str(social.get("agent_granularity", "per_agent"))

        incentives = getattr(run_spec, "incentives", {}) or {}
        econ_path = social.get("economics_weights_path")
        economics_weights: dict[str, Any] = {}
        if econ_path:
            ep = resolve_repo_path(repo, econ_path)
            if os.path.isfile(ep):
                with open(ep, encoding="utf-8") as fh:
                    economics_weights = json.load(fh).get("reward_weights", {})

        export_dir = social.get("export_utility_dir")
        import_dir = social.get("import_actions_dir")
        cmd_pol, med_pol, pop_pol = build_policies_from_config(
            run_spec.legacy_cfg if hasattr(run_spec, "legacy_cfg") else {},
        )
        rt.stackelberg = StackelbergRound(
            command_policy=cmd_pol,
            medical_policy=med_pol,
            population_policy=pop_pol,
            export_utility_dir=export_dir,
            import_actions_dir=import_dir,
            cruise_id=str(social.get("cruise_id", "0")),
            incentives=incentives,
            economics_weights=economics_weights,
            all_protocol_ids=rt.all_protocol_ids,
            agent_granularity=rt.agent_granularity,
        )
        return rt

    def capture_sop_events(self, protocol_engine: Any, epoch: int) -> list[dict[str, Any]]:
        events = [
            e for e in protocol_engine.protocol_log
            if e.get("epoch") == epoch
        ]
        self.sop_events_buffer = events
        return events
