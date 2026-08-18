"""Tests for Picard action envelope application."""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from decision_engine.actions import ActionEnvelope
from decision_engine.context import EpochDecisionContext
from orchestrator_types import SimulationState
from picard_framework.simulation.action_applier import (
    _ACTION_HANDLERS,
    _NEEDS_CTX,
    apply_action_envelope,
)


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


class TestActionDispatchBoundary:
    def test_every_ctx_required_kind_has_a_handler(self) -> None:
        missing = _NEEDS_CTX - set(_ACTION_HANDLERS)
        assert missing == set()

    def test_unknown_kind_does_not_mutate_state(self) -> None:
        state = SimulationState()
        cfg: dict = {}
        env = ActionEnvelope(
            epoch=1,
            actions={"command": [{"kind": "not_a_real_action", "sop_id": "SOP-099"}]},
        )
        applied = apply_action_envelope(env, state, cfg, EpochDecisionContext())
        assert applied == {"by_actor": {}}
        assert "SOP-099" not in state.forced_protocol_ids

    def test_ctx_required_kinds_no_op_without_context(self) -> None:
        state = SimulationState()
        cfg: dict = {}
        env = ActionEnvelope(
            epoch=1,
            actions={
                "command": [
                    {
                        "kind": "authorize_sop_subset",
                        "protocol_ids": ["SOP-001"],
                    },
                    {"kind": "corporate_communication_stance", "stance": 0.8},
                ],
            },
        )
        applied = apply_action_envelope(env, state, cfg, decision_ctx=None)
        assert applied == {"by_actor": {}}

    def test_isolation_threshold_scale_grades(self) -> None:
        scales = [0.5, 1.0, 2.0]
        seen = []
        for scale in scales:
            cfg: dict = {}
            env = ActionEnvelope(
                epoch=1,
                actions={
                    "medical": [
                        {"kind": "set_isolation_posture", "threshold_scale": scale},
                    ],
                },
            )
            apply_action_envelope(env, SimulationState(), cfg, EpochDecisionContext())
            seen.append(cfg["_picard_epoch_overrides"]["isolation_threshold_scale"])
        assert seen == scales

    def test_stance_grades_on_decision_context(self) -> None:
        stances = [-1.0, 0.0, 1.0]
        seen = []
        for stance in stances:
            ctx = EpochDecisionContext()
            env = ActionEnvelope(
                epoch=1,
                actions={
                    "command": [
                        {"kind": "corporate_communication_stance", "stance": stance},
                    ],
                },
            )
            apply_action_envelope(env, SimulationState(), {}, ctx)
            seen.append(ctx.corporate_communication_stance)
        assert seen == stances

    def test_hide_symptoms_does_not_move_pcr_cadence(self) -> None:
        cfg: dict = {}
        env = ActionEnvelope(
            epoch=1,
            actions={
                "population": [{"kind": "hide_symptoms", "agent_id": 7}],
                "command": [{"kind": "set_surveillance_cadence", "pcr_cadence": 4}],
            },
        )
        apply_action_envelope(env, SimulationState(), cfg, EpochDecisionContext())
        assert cfg["_picard_epoch_overrides"]["pcr_cadence"] == 4
        behavior_only = {}
        apply_action_envelope(
            ActionEnvelope(
                epoch=1,
                actions={"population": [{"kind": "hide_symptoms", "agent_id": 8}]},
            ),
            SimulationState(),
            behavior_only,
            EpochDecisionContext(),
        )
        assert "pcr_cadence" not in behavior_only.get("_picard_epoch_overrides", {})
