"""
test_diagnostic_cascade.py – Unit tests for the diagnostic cascade engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.diagnostic_cascade import (
    AgentCascadeState,
    CascadeEpochResult,
    DiagnosticCascadeEngine,
    DiagnosticTier,
    FleetEscalationRule,
    _CascadeTestRunner,
    build_cascade_engine,
    load_diagnostic_cascade,
)
from crusher_labs.protocol_engine import StandingProtocol


# ── Helpers ──────────────────────────────────────────────────────────────

def _default_tiers() -> list[DiagnosticTier]:
    """Minimal 4-tier cascade for testing."""
    return [
        DiagnosticTier(
            tier_id=0, name="Triage", tests=[],
            sensitivity=0.7, specificity=0.6,
            cost_per_agent={}, tat_epochs=0,
            regret_level="low",
            actions_on_positive=["advance_to_tier_1"],
            confinement_on_positive=False, sop_gate=None,
            implicit_positive=False,
        ),
        DiagnosticTier(
            tier_id=1, name="RDT Screen", tests=["clinical_rdt"],
            sensitivity=0.8, specificity=0.97,
            cost_per_agent={"financial_usd": 12},
            tat_epochs=0, regret_level="low",
            actions_on_positive=["advance_to_tier_2", "offer_wearable"],
            confinement_on_positive=False,
            sop_gate=["SOP-006"],
        ),
        DiagnosticTier(
            tier_id=2, name="Confirmatory", tests=["clinical_qpcr"],
            sensitivity=0.95, specificity=0.99,
            cost_per_agent={"financial_usd": 85},
            tat_epochs=0, regret_level="medium",
            actions_on_positive=["advance_to_tier_3"],
            confinement_on_positive=True,
            sop_gate=["SOP-008"],
        ),
        DiagnosticTier(
            tier_id=3, name="Full Cascade", tests=[],
            sensitivity=0.99, specificity=0.999,
            cost_per_agent={}, tat_epochs=0,
            regret_level="high",
            actions_on_positive=[],
            confinement_on_positive=True,
            sop_gate=["SOP-009"],
        ),
    ]


def _make_agent(
    agent_id: int,
    infected: bool = False,
    shedding: float = 0.0,
    location: str = "MedBay",
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "infection_state": "infected" if infected else "susceptible",
        "symptom_presentation": "symptomatic" if infected else "asymptomatic",
        "compliance_status": "compliant",
        "shedding_rate": shedding,
        "location": location,
        "microflora_disruption": 0.5 if infected else 0.0,
        "agent_class": "crew_general",
    }


class _StubTestRunner:
    """Deterministic test runner for cascade unit tests."""

    def __init__(self, positive_agents: set[int] | None = None) -> None:
        self.positive_agents = positive_agents or set()
        self.tests_run: list[tuple[int, str]] = []

    def run_tier_tests(
        self,
        agent_id: int,
        agent: dict[str, Any],
        tier: DiagnosticTier,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for test_key in tier.tests:
            positive = agent_id in self.positive_agents
            results[test_key] = {"positive": positive, "detected": positive}
            self.tests_run.append((agent_id, test_key))
        return results


# ── DiagnosticTier ───────────────────────────────────────────────────────

class TestDiagnosticTier:
    def test_from_config(self) -> None:
        cfg = {
            "tier_id": 1,
            "name": "Test Tier",
            "tests": ["clinical_rdt"],
            "sensitivity": 0.8,
            "specificity": 0.97,
            "cost_per_agent": {"financial_usd": 12},
            "tat_epochs": 0,
            "regret_level": "low",
            "actions_on_positive": ["advance_to_tier_2"],
            "confinement_on_positive": False,
            "sop_gate": ["SOP-006"],
        }
        tier = DiagnosticTier.from_config(cfg)
        assert tier.tier_id == 1
        assert tier.name == "Test Tier"
        assert tier.tests == ["clinical_rdt"]
        assert tier.sensitivity == pytest.approx(0.8)
        assert tier.sop_gate == ["SOP-006"]

    def test_from_config_defaults(self) -> None:
        tier = DiagnosticTier.from_config({"tier_id": 0})
        assert tier.name == "Tier 0"
        assert tier.tests == []
        assert tier.sensitivity == pytest.approx(0.5)
        assert tier.sop_gate is None


# ── AgentCascadeState ────────────────────────────────────────────────────

class TestAgentCascadeState:
    def test_to_dict(self) -> None:
        state = AgentCascadeState(agent_id=42, current_tier=2)
        state.tier_entry_epoch = {0: 0, 1: 0, 2: 1}
        state.confirmed = True
        d = state.to_dict()
        assert d["agent_id"] == 42
        assert d["current_tier"] == 2
        assert d["confirmed"] is True


# ── DiagnosticCascadeEngine ──────────────────────────────────────────────

class TestDiagnosticCascadeEngine:
    def test_enter_tier0(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        engine.enter_tier0(1, epoch=0, reason="sick_call")
        assert 1 in engine.agent_states
        assert engine.agent_states[1].current_tier == 0
        assert engine.agent_states[1].tier_entry_epoch[0] == 0

    def test_enter_tier0_idempotent(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        engine.enter_tier0(1, epoch=0)
        engine.enter_tier0(1, epoch=1)
        assert engine.agent_states[1].tier_entry_epoch[0] == 0

    def test_full_cascade_positive_agent(self) -> None:
        """A positive agent should advance Tier 0 → 3 in one epoch."""
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        result = engine.evaluate_epoch(
            epoch=0,
            sick_call_ids=[1],
            wearable_red_ids=[],
            agents=agents,
            test_runner=runner,
        )

        state = engine.agent_states[1]
        assert state.current_tier == 3
        assert state.confirmed is True
        assert 1 in result.confinements_ordered
        assert len(result.tier_advancements) >= 2

    def test_negative_rdt_stops_cascade(self) -> None:
        """A negative RDT at Tier 1 should stop advancement."""
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents=set())
        agents = [_make_agent(1, infected=False)]

        result = engine.evaluate_epoch(
            epoch=0,
            sick_call_ids=[1],
            wearable_red_ids=[],
            agents=agents,
            test_runner=runner,
        )

        state = engine.agent_states[1]
        assert state.current_tier == 1
        assert state.confirmed is False
        assert 1 not in result.confinements_ordered

    def test_wearable_alert_enters_cascade(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents=set())
        agents = [_make_agent(5)]

        result = engine.evaluate_epoch(
            epoch=0,
            sick_call_ids=[],
            wearable_red_ids=[5],
            agents=agents,
            test_runner=runner,
        )

        assert 5 in result.new_tier0_agents
        assert 5 in engine.agent_states

    def test_wearable_offer(self) -> None:
        """Agents reaching Tier 1+ should be offered a wearable if not monitored."""
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        result = engine.evaluate_epoch(
            epoch=0,
            sick_call_ids=[1],
            wearable_red_ids=[],
            agents=agents,
            test_runner=runner,
            monitored_agent_ids=set(),
        )

        assert 1 in result.wearable_offers

    def test_wearable_not_offered_if_already_monitored(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        result = engine.evaluate_epoch(
            epoch=0,
            sick_call_ids=[1],
            wearable_red_ids=[],
            agents=agents,
            test_runner=runner,
            monitored_agent_ids={1},
        )

        assert 1 not in result.wearable_offers

    def test_tier_distribution(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [
            _make_agent(1, infected=True, shedding=500.0),
            _make_agent(2, infected=False),
        ]

        engine.evaluate_epoch(
            epoch=0,
            sick_call_ids=[1, 2],
            wearable_red_ids=[],
            agents=agents,
            test_runner=runner,
        )

        dist = engine.tier_distribution()
        assert dist.get(3, 0) == 1  # agent 1 reached tier 3
        assert dist.get(1, 0) == 1  # agent 2 stopped at tier 1

    def test_sop_gate(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        assert engine.get_sop_gate(1) == ["SOP-006"]
        assert engine.get_sop_gate(2) == ["SOP-008"]
        assert engine.get_sop_gate(3) == ["SOP-009"]
        assert engine.get_sop_gate(99) == []

    def test_get_all_unlocked_sops(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )

        unlocked = engine.get_all_unlocked_sops()
        assert "SOP-009" in unlocked

    def test_cascade_summary(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )

        summary = engine.generate_cascade_summary()
        assert summary["total_agents_in_cascade"] == 1
        assert 1 in summary["confirmed_agents"]

    def test_agents_at_tier(self) -> None:
        engine = DiagnosticCascadeEngine(_default_tiers())
        runner = _StubTestRunner(positive_agents={1, 2})
        agents = [
            _make_agent(1, infected=True, shedding=500.0),
            _make_agent(2, infected=True, shedding=500.0),
            _make_agent(3, infected=False),
        ]

        engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1, 2, 3], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )

        at_tier2 = engine.agents_at_tier(2)
        assert 1 in at_tier2
        assert 2 in at_tier2
        assert 3 not in at_tier2


# ── TAT-delayed tiers ───────────────────────────────────────────────────

class TestCascadeTATDelay:
    def _delayed_tiers(self) -> list[DiagnosticTier]:
        """Tier 2 with 2-epoch TAT to simulate microbiology delay."""
        tiers = _default_tiers()
        delayed_tier2 = DiagnosticTier(
            tier_id=2, name="Confirmatory (delayed)",
            tests=["clinical_qpcr"],
            sensitivity=0.95, specificity=0.99,
            cost_per_agent={"financial_usd": 85},
            tat_epochs=2, regret_level="medium",
            actions_on_positive=["advance_to_tier_3"],
            confinement_on_positive=True,
            sop_gate=["SOP-008"],
        )
        tiers[2] = delayed_tier2
        return tiers

    def test_delayed_tier_waits_for_tat(self) -> None:
        """Tier 2 with TAT=2 should not advance until 2 epochs later."""
        engine = DiagnosticCascadeEngine(self._delayed_tiers())
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        # Epoch 0: enters cascade, reaches Tier 2, but TAT pending
        result0 = engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )
        state = engine.agent_states[1]
        assert state.current_tier == 2
        assert state.pending_tier == 2
        assert state.pending_available_epoch == 2

        # Epoch 1: still pending
        result1 = engine.evaluate_epoch(
            epoch=1, sick_call_ids=[], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )
        assert engine.agent_states[1].current_tier == 2

        # Epoch 2: TAT resolved, should advance to Tier 3
        result2 = engine.evaluate_epoch(
            epoch=2, sick_call_ids=[], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )
        assert engine.agent_states[1].current_tier == 3
        assert engine.agent_states[1].confirmed is True


# ── Fleet escalation rules ───────────────────────────────────────────────

class TestFleetEscalationRules:
    def test_fleet_rule_fires(self) -> None:
        rule = FleetEscalationRule(
            rule_id="test_rule",
            tier_threshold=2,
            agent_count=2,
            category_filter=None,
            pathogen_filter=None,
            unlocked_sops=["SOP-009"],
        )
        engine = DiagnosticCascadeEngine(_default_tiers(), fleet_rules=[rule])
        runner = _StubTestRunner(positive_agents={1, 2})
        agents = [
            _make_agent(1, infected=True, shedding=500.0),
            _make_agent(2, infected=True, shedding=500.0),
        ]

        result = engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1, 2], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )

        assert "SOP-009" in result.fleet_sops_unlocked

    def test_fleet_rule_category_filter(self) -> None:
        rule = FleetEscalationRule(
            rule_id="crew_rule",
            tier_threshold=2,
            agent_count=2,
            category_filter="passenger",
            pathogen_filter=None,
            unlocked_sops=["SOP-011"],
        )
        engine = DiagnosticCascadeEngine(_default_tiers(), fleet_rules=[rule])
        runner = _StubTestRunner(positive_agents={1, 2})
        agents = [
            _make_agent(1, infected=True, shedding=500.0),
            _make_agent(2, infected=True, shedding=500.0),
        ]

        result = engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1, 2], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )

        assert "SOP-011" not in result.fleet_sops_unlocked

    def test_fleet_rule_not_enough_agents(self) -> None:
        rule = FleetEscalationRule(
            rule_id="test_rule",
            tier_threshold=2,
            agent_count=5,
            category_filter=None,
            pathogen_filter=None,
            unlocked_sops=["SOP-009"],
        )
        engine = DiagnosticCascadeEngine(_default_tiers(), fleet_rules=[rule])
        runner = _StubTestRunner(positive_agents={1})
        agents = [_make_agent(1, infected=True, shedding=500.0)]

        result = engine.evaluate_epoch(
            epoch=0, sick_call_ids=[1], wearable_red_ids=[],
            agents=agents, test_runner=runner,
        )

        assert "SOP-009" not in result.fleet_sops_unlocked


# ── Cascade-gated protocol triggering ────────────────────────────────────

class TestCascadeGatedProtocols:
    def test_protocol_blocked_by_cascade_tier(self) -> None:
        """Protocol with required_cascade_tier should not fire without cascade context."""
        proto = StandingProtocol({
            "protocol_id": "SOP-TEST",
            "name": "Test Confinement",
            "trigger": {
                "instrument_class": "clinical_rdt",
                "stoplight_level": "RED",
                "min_agents_affected": 1,
            },
            "required_cascade_tier": 2,
        })
        stoplights = {"clinical_rdt": {"1": "RED"}}

        cascade_ctx = {
            "unlocked_sops": [],
            "fleet_sops_unlocked": [],
            "tier_distribution": {0: 1},
        }
        assert proto.is_triggered(stoplights, cascade_ctx) is False

    def test_protocol_allowed_by_cascade_tier(self) -> None:
        proto = StandingProtocol({
            "protocol_id": "SOP-TEST",
            "name": "Test Confinement",
            "trigger": {
                "instrument_class": "clinical_rdt",
                "stoplight_level": "RED",
                "min_agents_affected": 1,
            },
            "required_cascade_tier": 2,
        })
        stoplights = {"clinical_rdt": {"1": "RED"}}

        cascade_ctx = {
            "unlocked_sops": [],
            "fleet_sops_unlocked": [],
            "tier_distribution": {2: 1, 3: 1},
        }
        assert proto.is_triggered(stoplights, cascade_ctx) is True

    def test_protocol_allowed_by_sop_unlock(self) -> None:
        proto = StandingProtocol({
            "protocol_id": "SOP-TEST",
            "name": "Test",
            "trigger": {
                "instrument_class": "clinical_rdt",
                "stoplight_level": "RED",
                "min_agents_affected": 1,
            },
            "required_cascade_tier": 3,
        })
        stoplights = {"clinical_rdt": {"1": "RED"}}

        cascade_ctx = {
            "unlocked_sops": ["SOP-TEST"],
            "fleet_sops_unlocked": [],
            "tier_distribution": {0: 1},
        }
        assert proto.is_triggered(stoplights, cascade_ctx) is True

    def test_protocol_without_cascade_tier_unaffected(self) -> None:
        proto = StandingProtocol({
            "protocol_id": "SOP-001",
            "name": "Enhanced Ventilation",
            "trigger": {
                "instrument_class": "continuous_air_sampler",
                "stoplight_level": "RED",
                "min_zones_affected": 1,
            },
        })
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}

        cascade_ctx = {
            "unlocked_sops": [],
            "fleet_sops_unlocked": [],
            "tier_distribution": {},
        }
        assert proto.is_triggered(stoplights, cascade_ctx) is True

    def test_protocol_with_null_cascade_tier_unaffected(self) -> None:
        proto = StandingProtocol({
            "protocol_id": "SOP-001",
            "name": "Enhanced Ventilation",
            "trigger": {
                "instrument_class": "continuous_air_sampler",
                "stoplight_level": "RED",
                "min_zones_affected": 1,
            },
            "required_cascade_tier": None,
        })
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        assert proto.is_triggered(stoplights, cascade_context={}) is True


# ── Config loading ───────────────────────────────────────────────────────

class TestCascadeConfigLoading:
    def test_load_diagnostic_cascade(self) -> None:
        tiers, rules, entry = load_diagnostic_cascade(repo_root=REPO_ROOT)
        assert len(tiers) >= 4
        assert len(rules) >= 1
        assert entry.sick_call_tier == 1
        assert tiers[0].tier_id == 0
        assert tiers[3].tier_id == 3
        assert len(rules) >= 1

    def test_build_cascade_engine_disabled(self) -> None:
        cfg = {"diagnostic_cascade": {"enabled": False}}
        engine = build_cascade_engine(cfg, repo_root=REPO_ROOT)
        assert engine is None

    def test_build_cascade_engine_enabled(self) -> None:
        cfg = {
            "diagnostic_cascade": {
                "enabled": True,
                "config_path": "data/config/diagnostic_cascade.json",
            },
        }
        engine = build_cascade_engine(cfg, repo_root=REPO_ROOT)
        assert engine is not None
        assert len(engine.tiers) == 4


# ── CascadeEpochResult ──────────────────────────────────────────────────

class TestCascadeEpochResult:
    def test_to_dict(self) -> None:
        result = CascadeEpochResult(
            new_tier0_agents=[1, 2],
            confinements_ordered=[3],
            fleet_sops_unlocked=["SOP-009"],
        )
        d = result.to_dict()
        assert d["new_tier0_agents"] == [1, 2]
        assert d["confinements_ordered"] == [3]
        assert d["fleet_sops_unlocked"] == ["SOP-009"]


# ── Protocols.json has required_cascade_tier ─────────────────────────────

class TestProtocolsJsonCascadeTier:
    def test_all_protocols_have_cascade_tier_field(self) -> None:
        protocols_path = os.path.join(
            REPO_ROOT, "data", "config", "protocols.json",
        )
        with open(protocols_path) as fh:
            data = json.load(fh)
        for proto in data["protocols"]:
            assert "required_cascade_tier" in proto, (
                f"{proto['protocol_id']} missing required_cascade_tier"
            )

    def test_cascade_tier_values_valid(self) -> None:
        protocols_path = os.path.join(
            REPO_ROOT, "data", "config", "protocols.json",
        )
        with open(protocols_path) as fh:
            data = json.load(fh)
        for proto in data["protocols"]:
            tier = proto["required_cascade_tier"]
            if tier is not None:
                assert isinstance(tier, int)
                assert 0 <= tier <= 3


# ── diagnostic_cascade.json data contract ────────────────────────────────

class TestDiagnosticCascadeJsonContract:
    def test_tier_ids_sequential(self) -> None:
        tiers, _, _ = load_diagnostic_cascade(repo_root=REPO_ROOT)
        ids = [t.tier_id for t in tiers]
        assert ids == list(range(len(ids)))

    def test_sop_gates_reference_valid_sops(self) -> None:
        protocols_path = os.path.join(
            REPO_ROOT, "data", "config", "protocols.json",
        )
        with open(protocols_path) as fh:
            protocol_ids = {p["protocol_id"] for p in json.load(fh)["protocols"]}

        tiers, rules, _ = load_diagnostic_cascade(repo_root=REPO_ROOT)

        for tier in tiers:
            if tier.sop_gate:
                for sop_id in tier.sop_gate:
                    assert sop_id in protocol_ids, (
                        f"Tier {tier.tier_id} sop_gate references unknown {sop_id}"
                    )

        for rule in rules:
            for sop_id in rule.unlocked_sops:
                assert sop_id in protocol_ids, (
                    f"Fleet rule {rule.rule_id} references unknown {sop_id}"
                )

    def test_regret_levels_valid(self) -> None:
        tiers, _, _ = load_diagnostic_cascade(repo_root=REPO_ROOT)
        valid = {"low", "medium", "high"}
        for tier in tiers:
            assert tier.regret_level in valid

    def test_tat_non_negative(self) -> None:
        tiers, _, _ = load_diagnostic_cascade(repo_root=REPO_ROOT)
        for tier in tiers:
            assert tier.tat_epochs >= 0


class TestMultiplexCascadeConfig:
    def test_multiplex_tier1_uses_clinical_multiplex_panel(self) -> None:
        tiers, _, _ = load_diagnostic_cascade(
            os.path.join(REPO_ROOT, "data/config/diagnostic_cascade_multiplex.json"),
            repo_root=REPO_ROOT,
        )
        assert tiers[1].tests == ["clinical_multiplex_panel"]


class TestCascadeCostAccounting:
    def test_step_cascade_cost_accounting_debits_multiplex_panel(self) -> None:
        from orchestrator_epoch import step_cascade_cost_accounting
        from orchestrator_init import init_protocol_engine
        from crusher_labs import load_config

        cfg = load_config()
        proto_ctx = init_protocol_engine(cfg, None)
        cascade_result = {
            "tests_ordered": {
                1: ["clinical_multiplex_panel"],
                2: ["clinical_multiplex_panel", "clinical_qpcr"],
            },
        }
        step_cascade_cost_accounting(0, proto_ctx, cascade_result)
        sources = [e.source for e in proto_ctx.cost_ledger.entries]
        assert "test:clinical_multiplex_panel" in sources
        assert "test:clinical_qpcr" in sources
        multiplex_entry = next(
            e for e in proto_ctx.cost_ledger.entries
            if e.source == "test:clinical_multiplex_panel"
        )
        assert multiplex_entry.description == "2x clinical_multiplex_panel"
