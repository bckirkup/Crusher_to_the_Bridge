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
from decision_engine.stackelberg.round import StackelbergRound


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

    @classmethod
    def from_run_spec(cls, run_spec: Any, engine: Any, proto_ctx: Any) -> DecisionRuntime:
        repo = run_spec.repo_root
        social = getattr(run_spec, "social_config", None) or {}
        if not social:
            social = run_spec.legacy_cfg.get("social", {}) if hasattr(run_spec, "legacy_cfg") else {}

        rt = cls(repo_root=repo, social_config=social)

        profile_path = social.get("agent_profile_bundle")
        if not profile_path:
            profile_path = default_bundle_path(repo)
        elif not os.path.isabs(profile_path):
            profile_path = os.path.join(repo, profile_path)

        if os.path.isfile(profile_path):
            bundle = load_agent_profile_bundle(profile_path)
            wm = run_spec.legacy_cfg.get("wearable_monitoring", {})
            raw_map = wm.get("class_device_map", {})
            device_map: dict[str, str] = {}
            if isinstance(raw_map, dict):
                device_map = raw_map
            elif isinstance(raw_map, list):
                for entry in raw_map:
                    if isinstance(entry, dict):
                        device_map[str(entry.get("agent_class", ""))] = str(entry.get("device_id", ""))
            mp = run_spec.legacy_cfg.get("multi_pathogen", {})
            imm_frac = float(mp.get("immunocompromised_fraction", 0.0))
            rt.profiles = build_profiles_for_agents(
                engine.agents, bundle, np.random.default_rng(run_spec.random_seed),
                class_device_map=device_map,
                immunocompromised_fraction=imm_frac,
            )

        ci_path = social.get("class_interactions")
        if not ci_path:
            ci_path = ClassInteractionMatrix.default_path(repo)
        elif not os.path.isabs(ci_path):
            ci_path = os.path.join(repo, ci_path)
        if os.path.isfile(ci_path):
            rt.class_matrix = ClassInteractionMatrix.from_json(ci_path)

        diff_path = social.get("information_diffusion")
        if not diff_path:
            diff_path = InformationDiffusionEngine.default_path(repo)
        elif not os.path.isabs(diff_path):
            diff_path = os.path.join(repo, diff_path)
        if os.path.isfile(diff_path):
            rt.information_engine = InformationDiffusionEngine.from_config_path(diff_path)

        gh_path = social.get("global_health_timeline")
        if not gh_path:
            gh_path = default_timeline_path(repo)
        elif not os.path.isabs(gh_path):
            gh_path = os.path.join(repo, gh_path)
        if os.path.isfile(gh_path):
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
            ep = econ_path if os.path.isabs(econ_path) else os.path.join(repo, econ_path)
            if os.path.isfile(ep):
                with open(ep, encoding="utf-8") as fh:
                    economics_weights = json.load(fh).get("reward_weights", {})

        export_dir = social.get("export_utility_dir")
        import_dir = social.get("import_actions_dir")
        rt.stackelberg = StackelbergRound(
            export_utility_dir=export_dir,
            import_actions_dir=import_dir,
            cruise_id=str(social.get("cruise_id", "0")),
            incentives=incentives,
            economics_weights=economics_weights,
            all_protocol_ids=rt.all_protocol_ids,
        )
        return rt

    def capture_sop_events(self, protocol_engine: Any, epoch: int) -> list[dict[str, Any]]:
        events = [
            e for e in protocol_engine.protocol_log
            if e.get("epoch") == epoch
        ]
        self.sop_events_buffer = events
        return events
