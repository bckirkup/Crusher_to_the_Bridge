"""Tests for Picard action envelope application."""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from decision_engine.actions import ActionEnvelope
from decision_engine.context import EpochDecisionContext
from orchestrator_types import SimulationState
from picard_framework.simulation.action_applier import apply_action_envelope


class TestActionApplier:
    def test_activate_sop_and_verification(self) -> None:
        state = SimulationState()
        ctx = EpochDecisionContext()
        cfg: dict = {}
        env = ActionEnvelope(
            epoch=1,
            actions={
                "command": [
                    {"kind": "activate_sop", "sop_id": "SOP-015"},
                    {"kind": "order_verification_test", "zone": "Galley"},
                ],
                "population": [
                    {"kind": "hide_symptoms", "agent_id": 3},
                ],
            },
        )
        applied = apply_action_envelope(
            env, state, cfg, ctx, valid_zones={"Galley", "Bridge"},
        )
        assert "SOP-015" in state.forced_protocol_ids
        assert len(state.verification_test_queue) == 1
        assert state.agent_behavioral_overrides[3] == "hide_symptoms"
        assert "command" in applied["by_actor"]
