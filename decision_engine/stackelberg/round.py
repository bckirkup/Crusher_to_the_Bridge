"""Stackelberg-ordered decision round: population → observations → command/medical."""

from __future__ import annotations

from typing import Any

from decision_engine.actions import Action, ActionEnvelope
from decision_engine.context import EpochDecisionContext
from decision_engine.experience import ExperienceStore
from decision_engine.lived_experience import AgentLivedExperienceStore
from decision_engine.observation.command import build_command_observation
from decision_engine.observation.medical import build_medical_observation
from decision_engine.policy import Policy, RuleBasedPolicy
from decision_engine.utility.features import UtilityFeatureExtractor
from decision_engine.utility.io import export_utility_bundle, import_action_envelope
from decision_engine.views import ObservationModel
from telemetry_buffer.agent_axes import agent_has_symptomatic_presentation


class StackelbergRound:
    """Three-stage decision pass with optional utility export."""

    def __init__(
        self,
        command_policy: Policy | None = None,
        medical_policy: Policy | None = None,
        population_policy: Policy | None = None,
        export_utility_dir: str | None = None,
        import_actions_dir: str | None = None,
        cruise_id: str = "0",
        incentives: dict[str, float] | None = None,
        economics_weights: dict[str, float] | None = None,
        all_protocol_ids: list[str] | None = None,
        agent_granularity: str = "per_agent",
    ) -> None:
        self.command_policy = command_policy or RuleBasedPolicy()
        self.medical_policy = medical_policy or RuleBasedPolicy()
        self.population_policy = population_policy or RuleBasedPolicy()
        self.export_utility_dir = export_utility_dir
        self.import_actions_dir = import_actions_dir
        self.cruise_id = cruise_id
        self.incentives = incentives or {}
        self.economics_weights = economics_weights or {}
        self.all_protocol_ids = all_protocol_ids or []
        self.agent_granularity = agent_granularity
        self.feature_extractor = UtilityFeatureExtractor()
        self.last_bundle: dict[str, Any] | None = None

    def solve_population(
        self,
        epoch: int,
        epoch_snapshot: dict[str, Any],
        information_state: dict[str, Any],
        experience: ExperienceStore,
    ) -> ActionEnvelope:
        """Pre-syndromic population decisions (per-agent or aggregate)."""
        envelope = ActionEnvelope(epoch=epoch)
        agents = epoch_snapshot.get("agents", [])
        agent_info = (
            information_state.get("agents", information_state)
            if isinstance(information_state, dict)
            else {}
        )
        public = {
            **epoch_snapshot,
            "epoch": epoch,
            "information_state": agent_info,
        }

        if self.agent_granularity == "per_agent":
            pop_actions: list[Action] = []
            for ag in agents:
                if agent_has_symptomatic_presentation(ag):
                    role = (
                        "passenger_agent"
                        if ag.get("role") == "passenger"
                        else "crew_agent"
                    )
                    view = ObservationModel.build(
                        public, str(ag["agent_id"]), role,
                    )
                    acts = self.population_policy.decide(view, experience)
                    pop_actions.extend(acts)
            if pop_actions:
                envelope.actions["population"] = pop_actions
        else:
            pop_view = ObservationModel.build(public, "population", "crew_agent")
            pop_actions = self.population_policy.decide(pop_view, experience)
            if pop_actions:
                envelope.actions["population"] = pop_actions

        return envelope

    def solve_command_medical(
        self,
        epoch: int,
        epoch_snapshot: dict[str, Any],
        decision_ctx: EpochDecisionContext,
        lived_store: AgentLivedExperienceStore,
        information_state: dict[str, Any],
        reputation: Any,
        global_health_timeline: dict[str, Any],
        experience: ExperienceStore,
        stoplight_eligible_sop_ids: list[str],
    ) -> ActionEnvelope:
        """Post-stoplight command and medical decisions."""
        decision_ctx.epoch = epoch
        public = {
            **epoch_snapshot,
            "epoch": epoch,
            "information_state": information_state,
            "stoplight_eligible_sop_ids": stoplight_eligible_sop_ids,
        }

        command_obs = build_command_observation(
            epoch,
            epoch_snapshot,
            reputation,
            self.all_protocol_ids,
            stoplight_eligible_sop_ids,
            self.economics_weights,
        )
        cmd_view = ObservationModel.build(public, "command", "commanding_officer")
        cmd_actions = self.command_policy.decide(cmd_view, experience)
        self._apply_command_actions(cmd_actions, decision_ctx)

        medical_obs = build_medical_observation(
            epoch, epoch_snapshot, decision_ctx, global_health_timeline,
        )
        med_view = ObservationModel.build(
            {**public, **medical_obs}, "medical", "medical_officer",
        )
        med_actions = self.medical_policy.decide(med_view, experience)
        self._apply_medical_actions(med_actions, decision_ctx)

        envelope = ActionEnvelope(epoch=epoch)
        if cmd_actions:
            envelope.actions["command"] = cmd_actions
        if med_actions:
            envelope.actions["medical"] = med_actions

        if self.export_utility_dir:
            bundle = self.feature_extractor.build_bundle(
                epoch=epoch,
                cruise_id=self.cruise_id,
                command_obs=command_obs,
                medical_obs=medical_obs,
                reputation=reputation,
                lived=lived_store,
                information_state=information_state,
                incentives=self.incentives,
                economics_weights=self.economics_weights,
            )
            self.last_bundle = bundle
            export_utility_bundle(bundle, self.export_utility_dir, epoch, self.cruise_id)

        if self.import_actions_dir:
            imported = import_action_envelope(
                self.import_actions_dir, epoch, self.cruise_id,
            )
            if imported is not None:
                return imported

        return envelope

    def solve(
        self,
        epoch: int,
        epoch_snapshot: dict[str, Any],
        decision_ctx: EpochDecisionContext,
        lived_store: AgentLivedExperienceStore,
        information_state: dict[str, Any],
        reputation: Any,
        global_health_timeline: dict[str, Any],
        experience: ExperienceStore,
        stoplight_eligible_sop_ids: list[str],
    ) -> ActionEnvelope:
        """Full round: population then command/medical (for tests and legacy callers)."""
        pop_env = self.solve_population(
            epoch, epoch_snapshot, information_state, experience,
        )
        cmd_env = self.solve_command_medical(
            epoch,
            epoch_snapshot,
            decision_ctx,
            lived_store,
            information_state,
            reputation,
            global_health_timeline,
            experience,
            stoplight_eligible_sop_ids,
        )
        return pop_env.merge(cmd_env)

    def _apply_command_actions(
        self,
        actions: list[Action],
        ctx: EpochDecisionContext,
    ) -> None:
        for act in actions:
            kind = act.get("kind", "")
            if kind == "directive_to_medical":
                ctx.command_directives.append(act.get("directive", act))
            elif kind == "authorize_sop_subset":
                ids = act.get("protocol_ids")
                if isinstance(ids, list):
                    ctx.authorized_sop_ids = [str(x) for x in ids]
            elif kind == "corporate_communication_stance":
                ctx.corporate_communication_stance = float(
                    act.get("stance", 0.0),
                )

    def _apply_medical_actions(
        self,
        actions: list[Action],
        ctx: EpochDecisionContext,
    ) -> None:
        for act in actions:
            kind = act.get("kind", "")
            if kind == "issue_crew_instruction":
                msg = act.get("message", "")
                if msg:
                    ctx.medical_announcements.append(msg)
                    ctx.sop_announcements.append(msg)
