"""
crusher_labs.diagnostic_cascade
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tiered diagnostic cascade engine — manages per-agent progression
through configurable clinical evaluation tiers (Tier 0 → Tier 3).

Each tier has explicit sensitivity, specificity, turnaround, cost,
and regret level.  Tests run *sequentially per tier*, not in
parallel.  Intra-epoch multi-tier advancement is supported: an agent
can advance through all tiers whose TAT is 0 within a single epoch.

The cascade gates SOPs: each standing protocol may declare a
``required_cascade_tier``; the protocol engine only fires those SOPs
when enough agents have reached that tier.

Fleet-level escalation rules fire when N agents reach a tier
threshold across configurable agent categories or pathogens.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


# ── Tier dataclass ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class DiagnosticTier:
    """One level in the diagnostic cascade."""

    tier_id: int
    name: str
    tests: list[str]
    sensitivity: float
    specificity: float
    cost_per_agent: dict[str, Any]
    tat_epochs: int
    regret_level: str
    actions_on_positive: list[str]
    confinement_on_positive: bool
    sop_gate: list[str] | None

    @classmethod
    def from_config(cls, d: dict[str, Any]) -> DiagnosticTier:
        return cls(
            tier_id=int(d["tier_id"]),
            name=str(d.get("name", f"Tier {d['tier_id']}")),
            tests=list(d.get("tests", [])),
            sensitivity=float(d.get("sensitivity", 0.5)),
            specificity=float(d.get("specificity", 0.9)),
            cost_per_agent=dict(d.get("cost_per_agent", {})),
            tat_epochs=int(d.get("tat_epochs", 0)),
            regret_level=str(d.get("regret_level", "low")),
            actions_on_positive=list(d.get("actions_on_positive", [])),
            confinement_on_positive=bool(d.get("confinement_on_positive", False)),
            sop_gate=d.get("sop_gate"),
        )


# ── Per-agent cascade state ─────────────────────────────────────────────

@dataclass
class AgentCascadeState:
    """Mutable progression state for one agent in the cascade."""

    agent_id: int
    current_tier: int = 0
    tier_entry_epoch: dict[int, int] = field(default_factory=dict)
    tier_results: dict[int, dict[str, Any]] = field(default_factory=dict)
    pending_tier: int | None = None
    pending_available_epoch: int | None = None
    wearable_offered: bool = False
    pathogen_id: str | None = None
    confirmed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "current_tier": self.current_tier,
            "tier_entry_epoch": dict(self.tier_entry_epoch),
            "pending_tier": self.pending_tier,
            "wearable_offered": self.wearable_offered,
            "pathogen_id": self.pathogen_id,
            "confirmed": self.confirmed,
        }


# ── Fleet escalation rule ───────────────────────────────────────────────

@dataclass(frozen=True)
class FleetEscalationRule:
    """Fleet-wide SOP unlock when N agents reach a tier threshold."""

    rule_id: str
    tier_threshold: int
    agent_count: int
    category_filter: str | None
    pathogen_filter: str | None
    unlocked_sops: list[str]

    @classmethod
    def from_config(cls, d: dict[str, Any]) -> FleetEscalationRule:
        return cls(
            rule_id=str(d.get("rule_id", "")),
            tier_threshold=int(d.get("tier_threshold", 2)),
            agent_count=int(d.get("agent_count", 3)),
            category_filter=d.get("category_filter"),
            pathogen_filter=d.get("pathogen_filter"),
            unlocked_sops=list(d.get("unlocked_sops", [])),
        )


# ── Cascade epoch result ────────────────────────────────────────────────

@dataclass
class CascadeEpochResult:
    """Output of one epoch's cascade evaluation."""

    new_tier0_agents: list[int] = field(default_factory=list)
    tier_advancements: list[dict[str, Any]] = field(default_factory=list)
    tests_ordered: dict[int, list[str]] = field(default_factory=dict)
    confinements_ordered: list[int] = field(default_factory=list)
    wearable_offers: list[int] = field(default_factory=list)
    fleet_sops_unlocked: list[str] = field(default_factory=list)
    agent_states: dict[int, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_tier0_agents": self.new_tier0_agents,
            "tier_advancements": self.tier_advancements,
            "tests_ordered": self.tests_ordered,
            "confinements_ordered": self.confinements_ordered,
            "wearable_offers": self.wearable_offers,
            "fleet_sops_unlocked": self.fleet_sops_unlocked,
        }


# ── Main cascade engine ─────────────────────────────────────────────────

class DiagnosticCascadeEngine:
    """Manages per-agent progression through diagnostic tiers."""

    def __init__(
        self,
        tiers: list[DiagnosticTier],
        fleet_rules: list[FleetEscalationRule] | None = None,
    ) -> None:
        self.tiers = sorted(tiers, key=lambda t: t.tier_id)
        self.tier_map: dict[int, DiagnosticTier] = {t.tier_id: t for t in self.tiers}
        self.fleet_rules = fleet_rules or []
        self.agent_states: dict[int, AgentCascadeState] = {}
        self.cascade_log: list[dict[str, Any]] = []

    @property
    def max_tier(self) -> int:
        return max(t.tier_id for t in self.tiers) if self.tiers else 0

    def get_tier(self, tier_id: int) -> DiagnosticTier | None:
        return self.tier_map.get(tier_id)

    def _get_or_create_state(self, agent_id: int) -> AgentCascadeState:
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = AgentCascadeState(agent_id=agent_id)
        return self.agent_states[agent_id]

    def enter_tier0(
        self,
        agent_id: int,
        epoch: int,
        reason: str = "sick_call",
    ) -> None:
        """Register an agent entering the cascade at Tier 0."""
        state = self._get_or_create_state(agent_id)
        if 0 in state.tier_entry_epoch:
            return
        state.current_tier = 0
        state.tier_entry_epoch[0] = epoch
        self.cascade_log.append({
            "epoch": epoch,
            "agent_id": agent_id,
            "event": "TIER_ENTRY",
            "tier": 0,
            "reason": reason,
        })

    def _advance_agent(
        self,
        state: AgentCascadeState,
        to_tier: int,
        epoch: int,
        test_results: dict[str, Any] | None = None,
    ) -> None:
        """Advance an agent to a new tier."""
        state.current_tier = to_tier
        state.tier_entry_epoch[to_tier] = epoch
        if test_results:
            state.tier_results[to_tier] = test_results
        state.pending_tier = None
        state.pending_available_epoch = None
        self.cascade_log.append({
            "epoch": epoch,
            "agent_id": state.agent_id,
            "event": "TIER_ADVANCE",
            "tier": to_tier,
        })

    def _determine_test_outcome(
        self,
        agent: dict[str, Any],
        test_results: dict[str, Any],
        tier: DiagnosticTier,
    ) -> bool:
        """Determine whether test results at this tier are positive.

        Checks instrument-specific result fields for any positive signal.
        """
        if not test_results:
            return tier.tests == []

        for test_key, result in test_results.items():
            if isinstance(result, dict):
                if result.get("positive"):
                    return True
                if result.get("detected"):
                    return True
                disruption = result.get("microflora_disruption_level", 0.0)
                if disruption >= 0.6:
                    return True

        return False

    def evaluate_epoch(
        self,
        epoch: int,
        sick_call_ids: list[int],
        wearable_red_ids: list[int],
        agents: list[dict[str, Any]],
        test_runner: _CascadeTestRunner | None = None,
        monitored_agent_ids: set[int] | None = None,
    ) -> CascadeEpochResult:
        """Run one epoch of cascade evaluation.

        1. Enter new agents at Tier 0 from sick-call and wearable alerts.
        2. Resolve pending tiers whose TAT has completed.
        3. For each agent at a tier, run tests and advance if positive.
        4. Support intra-epoch multi-tier advancement (loop until stable).
        5. Evaluate fleet escalation rules.
        """
        result = CascadeEpochResult()
        monitored = monitored_agent_ids or set()
        agent_map = {a["agent_id"]: a for a in agents}

        for aid in sick_call_ids:
            if aid not in self.agent_states or 0 not in self.agent_states[aid].tier_entry_epoch:
                self.enter_tier0(aid, epoch, reason="sick_call")
                result.new_tier0_agents.append(aid)

        for aid in wearable_red_ids:
            if aid not in self.agent_states or 0 not in self.agent_states[aid].tier_entry_epoch:
                self.enter_tier0(aid, epoch, reason="wearable_alert")
                result.new_tier0_agents.append(aid)

        for state in list(self.agent_states.values()):
            if state.pending_tier is not None and state.pending_available_epoch is not None:
                if epoch >= state.pending_available_epoch:
                    pending_results = state.tier_results.get(state.pending_tier, {})
                    tier = self.get_tier(state.pending_tier)
                    if tier is not None:
                        agent = agent_map.get(state.agent_id, {})
                        positive = self._determine_test_outcome(agent, pending_results, tier)
                        if positive:
                            next_tier_id = state.pending_tier + 1
                            if next_tier_id <= self.max_tier:
                                self._advance_agent(state, next_tier_id, epoch, pending_results)
                                result.tier_advancements.append({
                                    "agent_id": state.agent_id,
                                    "from_tier": state.pending_tier,
                                    "to_tier": next_tier_id,
                                    "epoch": epoch,
                                    "reason": "pending_tat_resolved",
                                })
                            else:
                                state.confirmed = True
                                state.pending_tier = None
                                state.pending_available_epoch = None
                        else:
                            state.pending_tier = None
                            state.pending_available_epoch = None

        changed = True
        iterations = 0
        max_iterations = self.max_tier + 2
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for state in list(self.agent_states.values()):
                if state.confirmed or state.pending_tier is not None:
                    continue

                current_tier = self.get_tier(state.current_tier)
                if current_tier is None:
                    continue

                agent = agent_map.get(state.agent_id, {})

                if current_tier.tests and test_runner is not None:
                    if state.current_tier not in state.tier_results:
                        test_results = test_runner.run_tier_tests(
                            state.agent_id, agent, current_tier,
                        )
                        state.tier_results[state.current_tier] = test_results
                        result.tests_ordered.setdefault(state.agent_id, []).extend(
                            current_tier.tests,
                        )

                        if current_tier.tat_epochs > 0:
                            state.pending_tier = state.current_tier
                            state.pending_available_epoch = epoch + current_tier.tat_epochs
                            continue

                tier_results = state.tier_results.get(state.current_tier, {})
                positive = self._determine_test_outcome(agent, tier_results, current_tier)

                if not positive and current_tier.tests:
                    continue

                if current_tier.confinement_on_positive and positive:
                    result.confinements_ordered.append(state.agent_id)

                for action in current_tier.actions_on_positive:
                    if action == "offer_wearable" and not state.wearable_offered:
                        if state.agent_id not in monitored:
                            state.wearable_offered = True
                            result.wearable_offers.append(state.agent_id)

                next_tier_id = state.current_tier + 1
                if next_tier_id <= self.max_tier:
                    next_tier_actions = [
                        a for a in current_tier.actions_on_positive
                        if a.startswith("advance_to_tier_")
                    ]
                    if next_tier_actions or not current_tier.tests:
                        self._advance_agent(state, next_tier_id, epoch)
                        result.tier_advancements.append({
                            "agent_id": state.agent_id,
                            "from_tier": state.current_tier - 1,
                            "to_tier": next_tier_id,
                            "epoch": epoch,
                            "reason": "intra_epoch",
                        })
                        changed = True
                elif positive:
                    state.confirmed = True

        result.fleet_sops_unlocked = self._evaluate_fleet_rules(agents)
        result.agent_states = {
            aid: s.to_dict() for aid, s in self.agent_states.items()
        }
        return result

    def _evaluate_fleet_rules(
        self,
        agents: list[dict[str, Any]],
    ) -> list[str]:
        """Check fleet escalation rules and return unlocked SOP IDs."""
        agent_map = {a["agent_id"]: a for a in agents}
        unlocked: list[str] = []

        for rule in self.fleet_rules:
            matching = 0
            for state in self.agent_states.values():
                if state.current_tier < rule.tier_threshold:
                    continue

                agent = agent_map.get(state.agent_id, {})
                if rule.category_filter:
                    agent_class = agent.get("agent_class", "")
                    if not agent_class.startswith(rule.category_filter):
                        continue

                if rule.pathogen_filter and state.pathogen_id:
                    if rule.pathogen_filter not in (state.pathogen_id or ""):
                        continue

                matching += 1

            if matching >= rule.agent_count:
                unlocked.extend(rule.unlocked_sops)

        return list(dict.fromkeys(unlocked))

    def get_sop_gate(self, tier_id: int) -> list[str]:
        """Return SOP IDs unlocked at this tier level."""
        tier = self.get_tier(tier_id)
        if tier is None or tier.sop_gate is None:
            return []
        return list(tier.sop_gate)

    def get_all_unlocked_sops(self) -> list[str]:
        """Return all SOP IDs unlocked by any agent's current tier."""
        unlocked: list[str] = []
        reached_tiers: set[int] = set()
        for state in self.agent_states.values():
            reached_tiers.add(state.current_tier)
        for tid in reached_tiers:
            unlocked.extend(self.get_sop_gate(tid))
        return list(dict.fromkeys(unlocked))

    def agents_at_tier(self, tier_id: int) -> list[int]:
        """Return agent IDs currently at or above the given tier."""
        return [
            s.agent_id for s in self.agent_states.values()
            if s.current_tier >= tier_id
        ]

    def tier_distribution(self) -> dict[int, int]:
        """Count of agents at each tier (for telemetry)."""
        dist: dict[int, int] = {}
        for state in self.agent_states.values():
            dist[state.current_tier] = dist.get(state.current_tier, 0) + 1
        return dist

    def generate_cascade_summary(self) -> dict[str, Any]:
        """Produce a summary for reporting / telemetry."""
        return {
            "total_agents_in_cascade": len(self.agent_states),
            "tier_distribution": self.tier_distribution(),
            "confirmed_agents": [
                s.agent_id for s in self.agent_states.values() if s.confirmed
            ],
            "all_unlocked_sops": self.get_all_unlocked_sops(),
            "event_log": self.cascade_log,
        }


# ── Test runner interface ────────────────────────────────────────────────

class _CascadeTestRunner:
    """Interface for running tier-specific diagnostic tests.

    Wraps the observation engine's clinical instruments so the cascade
    engine can request tests for individual agents at specific tiers.
    """

    def __init__(self, obs: Any) -> None:
        self.obs = obs

    def run_tier_tests(
        self,
        agent_id: int,
        agent: dict[str, Any],
        tier: DiagnosticTier,
    ) -> dict[str, Any]:
        """Run all tests defined for this tier on the given agent."""
        from telemetry_buffer.agent_axes import resolve_agent_axes

        results: dict[str, Any] = {}
        infection, presentation, compliance = resolve_agent_axes(agent)

        for test_key in tier.tests:
            if test_key == "clinical_rdt":
                from telemetry_buffer.agent_axes import agent_is_infected

                result = self.obs.clin_rdt.test_agent(
                    agent_id,
                    agent.get("shedding_rate", 0.0),
                    agent_is_infected(agent),
                    infection,
                    presentation,
                    compliance,
                    agent.get("location", "unknown"),
                )
                results[test_key] = result

            elif test_key == "clinical_multiplex_panel":
                from telemetry_buffer.agent_axes import agent_is_infected

                result = self.obs.clin_rdt.test_agent(
                    agent_id,
                    agent.get("shedding_rate", 0.0),
                    agent_is_infected(agent),
                    infection,
                    presentation,
                    compliance,
                    agent.get("location", "unknown"),
                )
                results[test_key] = result

            elif test_key == "clinical_qpcr":
                result = self.obs.clin_qpcr.test_agent(
                    agent_id,
                    agent.get("shedding_rate", 0.0),
                    infection,
                    presentation,
                    compliance,
                    agent.get("location", "unknown"),
                )
                results[test_key] = result

            elif test_key == "clinical_microbiology":
                result = self.obs.clin_microbio.test_agent(
                    agent_id,
                    agent.get("microflora_disruption", 0.0),
                    infection,
                    presentation,
                    compliance,
                    agent.get("location", "unknown"),
                    agent.get("pathogen_infections"),
                )
                results[test_key] = result

        return results


# ── Factory ──────────────────────────────────────────────────────────────

def load_diagnostic_cascade(
    config_path: str | None = None,
    repo_root: str | None = None,
) -> tuple[list[DiagnosticTier], list[FleetEscalationRule]]:
    """Load tier definitions and fleet rules from JSON config."""
    if config_path is None:
        root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(root, "data", "config", "diagnostic_cascade.json")

    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    tiers = [DiagnosticTier.from_config(t) for t in cfg.get("tiers", [])]
    rules = [FleetEscalationRule.from_config(r) for r in cfg.get("fleet_escalation_rules", [])]
    return tiers, rules


def build_cascade_engine(
    cfg: dict[str, Any],
    repo_root: str | None = None,
) -> DiagnosticCascadeEngine | None:
    """Build cascade engine from config.yaml if enabled."""
    cascade_cfg = cfg.get("diagnostic_cascade", {})
    if not cascade_cfg.get("enabled", False):
        return None

    config_path = cascade_cfg.get(
        "config_path", "data/config/diagnostic_cascade.json",
    )
    root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isabs(config_path):
        config_path = os.path.join(root, config_path)

    tiers, rules = load_diagnostic_cascade(config_path, repo_root=root)
    return DiagnosticCascadeEngine(tiers, rules)


def build_test_runner(obs: Any) -> _CascadeTestRunner:
    """Create a test runner wrapping the observation engine."""
    return _CascadeTestRunner(obs)
