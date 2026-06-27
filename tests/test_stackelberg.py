"""Stackelberg utilities and information diffusion tests."""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from decision_engine.information.diffusion import InformationDiffusionEngine
from decision_engine.lived_experience import AgentLivedExperienceStore
from decision_engine.social.class_interactions import ClassInteractionMatrix
from decision_engine.social.contact_graph import ContactGraphBuilder
from decision_engine.stackelberg.round import StackelbergRound
from decision_engine.utility.features import UtilityFeatureExtractor
from decision_engine.intelligence import briefing_for_epoch, load_global_health_timeline
from decision_engine.protocol_filter import eligible_protocol_ids
from decision_engine.experience import ExperienceStore
from decision_engine.context import EpochDecisionContext


def test_information_diffusion_deterministic() -> None:
    cfg = {
        "alpha": 0.25,
        "homophily_strength": 0.1,
        "message_decay": 0.0,
        "initial_severity_belief": 0.2,
    }
    eng_a = InformationDiffusionEngine(config=cfg)
    eng_b = InformationDiffusionEngine(config=cfg)
    eng_a.initialize_agents([1, 2], {1: "a", 2: "a"})
    eng_b.initialize_agents([1, 2], {1: "a", 2: "a"})
    adj = {1: {2: 1.0}, 2: {1: 1.0}}
    r1 = eng_a.step(adj, {1: "a", 2: "a"}, "SUSPECTED", 0.0)
    r2 = eng_b.step(adj, {1: "a", 2: "a"}, "SUSPECTED", 0.0)
    assert r1["agents"]["1"]["severity_belief"] == r2["agents"]["1"]["severity_belief"]


def test_contact_graph_shared_room() -> None:
    agents = [
        {"agent_id": 0, "location": "Mess_Hall", "agent_class": "passenger_general"},
        {"agent_id": 1, "location": "Mess_Hall", "agent_class": "crew_galley"},
    ]
    tracing = {
        "shared_room_exposures": [
            {"target_agent_id": 0, "source_agent_ids": [1]},
        ],
    }
    g = ContactGraphBuilder()
    adj = g.update(agents, tracing)
    assert 1 in adj.get(0, {})


def test_global_health_briefing_cumulative() -> None:
    path = os.path.join(
        REPO_ROOT, "presidio", "data", "intelligence", "global_health_timeline.json",
    )
    timeline = load_global_health_timeline(path)
    b0 = briefing_for_epoch(timeline, 0)
    b6 = briefing_for_epoch(timeline, 6)
    assert "routine" in str(b0.get("alerts", [])).lower() or b0.get("alerts")
    assert len(b6.get("travel_advisories", [])) >= len(b0.get("travel_advisories", []))


def test_utility_feature_extractor() -> None:
    ext = UtilityFeatureExtractor()
    rep = InformationDiffusionEngine().reputation
    cmd_obs = {
        "summary": {"infected": 2, "symptomatic": 1, "susceptible": 17, "recovered": 0, "immune": 0},
        "cost_accounting": {"total_financial_usd": 1000.0},
    }
    feats = ext.command_features(cmd_obs, rep, {"biodefense_weight": 1.0})
    assert "infected_rate" in feats
    assert feats["budget_spent_usd"] == pytest.approx(1000.0)


def test_stackelberg_round_produces_envelope() -> None:
    rnd = StackelbergRound(cruise_id="0")
    store = ExperienceStore("")
    lived = AgentLivedExperienceStore()
    ctx = EpochDecisionContext()
    timeline = {"briefings": []}
    snap = {
        "epoch": 0,
        "trigger_status": "BASELINE",
        "summary": {},
        "reactive_protocols": {"stoplights": {}},
    }
    from decision_engine.information.reputation import ReputationTracker
    env = rnd.solve(
        0, snap, ctx, lived, {}, ReputationTracker(), timeline, store, [],
    )
    assert env.epoch == 0


def test_class_interaction_matrix_zone_weight() -> None:
    path = ClassInteractionMatrix.default_path(REPO_ROOT)
    m = ClassInteractionMatrix.from_json(path)
    w = m.interaction_weight("crew_galley", "passenger_general", "Galley")
    assert w > 0


def test_import_action_envelope_round_trip(tmp_path) -> None:
    import json
    from decision_engine.utility.io import import_action_envelope

    actions_path = tmp_path / "cruise_0_epoch_0002_actions.json"
    actions_path.write_text(
        json.dumps({
            "epoch": 2,
            "actions": {
                "command": [{"kind": "directive_to_medical", "parameters": {"text": "isolate"}}],
            },
        }),
        encoding="utf-8",
    )
    env = import_action_envelope(str(tmp_path), 2, "0")
    assert env is not None
    assert env.epoch == 2
    assert env.actions.get("command")


def test_stackelberg_uses_imported_envelope(tmp_path) -> None:
    import json
    from decision_engine.information.reputation import ReputationTracker

    actions_path = tmp_path / "cruise_0_epoch_0000_actions.json"
    actions_path.write_text(
        json.dumps({"epoch": 0, "actions": {"medical": [{"kind": "recommend_sop", "parameters": {"sop_id": "SOP-001"}}]}}),
        encoding="utf-8",
    )
    rnd = StackelbergRound(cruise_id="0", import_actions_dir=str(tmp_path))
    env = rnd.solve(
        0,
        {"epoch": 0, "trigger_status": "BASELINE", "summary": {}, "reactive_protocols": {"stoplights": {}}},
        EpochDecisionContext(),
        AgentLivedExperienceStore(),
        {},
        ReputationTracker(),
        {"briefings": []},
        ExperienceStore(""),
        [],
    )
    assert env.actions.get("medical")
