"""INFO-SUPPRESS-V1: the recognition-keyed suppression channel.

Covers the spec resolver, the trigger latch, the per-channel
application (self-isolation, venue cancellation, route scalars) and the
default-OFF stream-neutrality contract.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.infection_dynamics_bridge import KorkinShipEngine  # noqa: E402
from orchestrator_epoch import step_self_isolation  # noqa: E402
from orchestrator_types import SimulationState  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.info_suppression import (  # noqa: E402
    InfoSuppressionSpec,
)
from picard_framework.simulation.ship_simulation import (  # noqa: E402
    ShipSimulation,
)


def _spec_block(**over: object) -> dict:
    block = {
        "enabled": True,
        "trigger_status": "suspected",
        "response_delay_hours": 0.0,
        "self_isolation_scope": "passengers",
        "closed_zones": ["Mess_Hall", "Recreation"],
        "route_scalars": {"direct_contact_scalar": 0.5},
    }
    block.update(over)
    return block


class TestSpecParsing:
    def test_absent_block_disables(self) -> None:
        spec = InfoSuppressionSpec.from_config(None)
        assert spec.enabled is False

    def test_disabled_block_parses(self) -> None:
        spec = InfoSuppressionSpec.from_config({"enabled": False})
        assert spec.enabled is False

    def test_full_block_resolves(self) -> None:
        spec = InfoSuppressionSpec.from_config(_spec_block(
            response_delay_hours=3.0,
        ))
        assert spec.enabled is True
        assert spec.trigger_status == "suspected"
        assert spec.scope_role == "passenger"
        assert spec.closed_zones == ("Mess_Hall", "Recreation")
        assert spec.route_scalars == {"direct_contact_scalar": 0.5}
        assert spec.response_delay_epochs == 3

    @pytest.mark.parametrize("delay_hours, epochs", [
        (0.0, 0), (6.0, 6), (0.4, 0), (25.0, 25),
    ])
    def test_response_delay_converts_hours_to_epochs(
        self, delay_hours: float, epochs: int,
    ) -> None:
        spec = InfoSuppressionSpec.from_config(_spec_block(
            response_delay_hours=delay_hours,
        ))
        assert spec.response_delay_epochs == epochs

    @pytest.mark.parametrize("status", ["alert", "suspected", "confirmed"])
    def test_trigger_rank_grades_across_statuses(self, status: str) -> None:
        spec = InfoSuppressionSpec.from_config(_spec_block(
            trigger_status=status,
        ))
        expected = {"alert": 1, "suspected": 2, "confirmed": 3}
        assert spec.trigger_rank == expected[status]

    def test_unknown_trigger_status_rejected(self) -> None:
        block = _spec_block(trigger_status="quarantine")
        with pytest.raises(ValueError, match="trigger_status"):
            InfoSuppressionSpec.from_config(block)

    def test_unknown_scope_rejected(self) -> None:
        block = _spec_block(self_isolation_scope="galley")
        with pytest.raises(ValueError, match="self_isolation_scope"):
            InfoSuppressionSpec.from_config(block)

    @pytest.mark.parametrize("scope, role", [
        ("passengers", "passenger"), ("crew", "crew"), ("all", "all"),
    ])
    def test_scope_maps_to_role(self, scope: str, role: str | None) -> None:
        spec = InfoSuppressionSpec.from_config(_spec_block(
            self_isolation_scope=scope,
        ))
        assert spec.scope_role == role

    def test_unknown_scalar_channel_rejected(self) -> None:
        block = _spec_block(route_scalars={"aerosol_scalar": 0.5})
        with pytest.raises(ValueError, match="route_scalars"):
            InfoSuppressionSpec.from_config(block)

    @pytest.mark.parametrize("value", [0.0, -0.1, 1.5])
    def test_scalar_out_of_unit_range_rejected(self, value: float) -> None:
        block = _spec_block(route_scalars={"fomite_scalar": value})
        with pytest.raises(ValueError, match="route_scalars"):
            InfoSuppressionSpec.from_config(block)

    def test_negative_delay_rejected(self) -> None:
        block = _spec_block(response_delay_hours=-2.0)
        with pytest.raises(ValueError, match="response_delay"):
            InfoSuppressionSpec.from_config(block)


def _agent(agent_id: int, role: str = "passenger", **kw: object) -> dict:
    agent = {
        "agent_id": agent_id,
        "role": role,
        "agent_class": f"{role}_general",
        "symptom_presentation": "asymptomatic",
    }
    agent.update(kw)
    return agent


class TestSelfIsolation:
    def _state(self) -> SimulationState:
        return SimulationState()

    def _agents(self) -> list[dict]:
        return [_agent(1), _agent(2), _agent(3, role="crew")]

    def test_compliant_agent_admitted(self) -> None:
        state = self._state()
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        syndromic._compliance_class = {1: "compliant"}
        admitted = step_self_isolation(
            5, [_agent(1)], state, syndromic, "passenger", 0,
        )
        assert admitted == 1
        assert 1 in state.quarantined_ids
        assert 1 in state.info_suppression_admitted_ids
        assert state.compliance_log[-1]["action"] == "self_isolation"

    def test_declining_agent_never_marks_refuser(self) -> None:
        state = self._state()
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = False
        syndromic._compliance_class = {}
        admitted = step_self_isolation(
            5, [_agent(1)], state, syndromic, "passenger", 0,
        )
        assert admitted == 0
        assert 1 not in state.quarantine_refusers
        assert 1 not in state.quarantined_ids

    def test_existing_refuser_is_skipped(self) -> None:
        state = self._state()
        state.quarantine_refusers.add(1)
        syndromic = MagicMock()
        step_self_isolation(
            5, [_agent(1)], state, syndromic, "passenger", 0,
        )
        syndromic.check_quarantine_compliance.assert_not_called()
        assert 1 not in state.quarantined_ids

    def test_confined_and_escort_pending_skipped(self) -> None:
        state = self._state()
        state.quarantined_ids.add(1)
        state.isolated_ids.add(2)
        state.escort_pending[3] = 99
        syndromic = MagicMock()
        agents = [_agent(1), _agent(2), _agent(3)]
        admitted = step_self_isolation(
            5, agents, state, syndromic, "all", 0,
        )
        assert admitted == 0
        syndromic.check_quarantine_compliance.assert_not_called()

    def test_scope_filters_role(self) -> None:
        state = self._state()
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        syndromic._compliance_class = {}
        admitted = step_self_isolation(
            5, self._agents(), state, syndromic, "passenger", 0,
        )
        assert admitted == 2
        assert state.quarantined_ids == {1, 2}
        assert state.info_suppression_admitted_ids == {1, 2}

    def test_all_scope_admits_crew_too(self) -> None:
        state = self._state()
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        syndromic._compliance_class = {}
        admitted = step_self_isolation(
            5, self._agents(), state, syndromic, "all", 0,
        )
        assert admitted == 3

    def test_offer_age_passes_to_compliance_check(self) -> None:
        state = self._state()
        syndromic = MagicMock()
        step_self_isolation(
            30, [_agent(1)], state, syndromic, "passenger", 12,
        )
        assert syndromic.check_quarantine_compliance.call_args[0][1] == 12

    def test_symptomatic_agent_uses_confinement_path(self) -> None:
        state = self._state()
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        syndromic._compliance_class = {}
        agent = _agent(1, symptom_presentation="symptomatic")
        step_self_isolation(
            5, [agent], state, syndromic, "passenger", 0,
        )
        assert syndromic.check_quarantine_compliance.call_args[1][
            "is_symptomatic"
        ] is True


class TestCancelVenues:
    def _engine(self) -> KorkinShipEngine:
        return KorkinShipEngine(
            num_passengers=120, num_crew=30, initial_infected=0, seed=5,
        )

    def test_catalog_filtered(self) -> None:
        engine = self._engine()
        target = "Mess_Hall"
        closed = engine.cancel_venues({target})
        assert target in closed
        assert target in engine.closed_venue_ids
        for catalog in (
            engine._dining_catalog,
            engine._crew_dining_catalog,
            engine._passenger_dining_catalog,
            engine._leisure_catalog,
        ):
            assert all(row["name"] != target for row in catalog)

    def test_agents_repointed_home(self) -> None:
        engine = self._engine()
        targets = {"Mess_Hall", "Recreation", "Galley"}
        moved = {
            a.agent_id: (a.dining_zone, a.free_zone)
            for a in engine.agents
        }
        engine.cancel_venues(targets)
        for agent in engine.agents:
            assert agent.dining_zone not in targets
            assert agent.free_zone not in targets
            assert agent.current_location not in targets
        # Something actually changed for agents held in closed venues.
        assert any(
            agent.dining_zone != moved[agent.agent_id][0]
            or agent.free_zone != moved[agent.agent_id][1]
            for agent in engine.agents
        )

    def test_union_across_calls_and_unknown_zones_dropped(self) -> None:
        engine = self._engine()
        first = engine.cancel_venues({"Mess_Hall", "NO_SUCH_ZONE"})
        second = engine.cancel_venues({"Recreation"})
        assert "NO_SUCH_ZONE" not in first
        assert engine.closed_venue_ids == {"Mess_Hall", "Recreation"}
        assert second == {"Recreation"}

    def test_empty_cancel_is_noop(self) -> None:
        engine = self._engine()
        assert engine.cancel_venues([]) == set()
        assert engine.cancel_venues(set()) == set()
        assert engine.closed_venue_ids == set()


def _armed_sim(info_block: dict | None) -> ShipSimulation:
    """A one-epoch sim whose info_suppression block is armed in cfg."""
    spec = PicardRunSpec.from_legacy_yaml(
        str(REPO_ROOT), num_epochs=4,
    )
    if info_block is not None:
        spec.legacy_cfg["info_suppression"] = info_block
    sim = ShipSimulation(spec, display=False, repo_root=str(REPO_ROOT))
    sim.initialize()
    return sim


def _work(sim: ShipSimulation, epoch: int, **kw: object) -> SimpleNamespace:
    work = SimpleNamespace(
        epoch=epoch,
        state=sim.state,
        cfg=sim.cfg,
        syndromic=MagicMock(),
        agents=[],
    )
    for key, value in kw.items():
        setattr(work, key, value)
    return work


class TestStepInfoSuppression:
    def test_disabled_never_fires(self) -> None:
        sim = _armed_sim({"enabled": False})
        before = sim.tx_core.direct_contact_scalar
        sim.state.trigger_status = "CONFIRMED"
        sim._step_info_suppression(_work(sim, 5))
        assert sim.state.info_recognition_epoch is None
        assert sim.state.info_suppression_epoch is None
        assert sim.tx_core.direct_contact_scalar == before

    def test_below_trigger_rank_does_not_fire(self) -> None:
        sim = _armed_sim(_spec_block())
        sim.state.trigger_status = "ALERT"
        sim._step_info_suppression(_work(sim, 5))
        assert sim.state.info_recognition_epoch is None
        assert sim.tx_core.direct_contact_scalar == pytest.approx(1.0)

    def test_trigger_latches_and_applies_channels(self) -> None:
        sim = _armed_sim(_spec_block())
        sim.state.trigger_status = "SUSPECTED"
        sim._step_info_suppression(_work(sim, 5))
        assert sim.state.info_recognition_epoch == 5
        assert sim.state.info_suppression_epoch == 5
        assert sim.tx_core.direct_contact_scalar == pytest.approx(0.5)
        assert sim.state.info_suppression_closed_zones == sorted(
            {"Mess_Hall", "Recreation"} & sim.engine.closed_venue_ids
        )

    def test_confirmed_status_fires_suspected_trigger(self) -> None:
        sim = _armed_sim(_spec_block())
        sim.state.trigger_status = "CONFIRMED"
        sim._step_info_suppression(_work(sim, 5))
        assert sim.state.info_recognition_epoch == 5

    def test_scalar_reapplied_each_epoch_without_compounding(self) -> None:
        sim = _armed_sim(_spec_block())
        sim.state.trigger_status = "SUSPECTED"
        for epoch in (5, 6, 7):
            sim.tx_core.direct_contact_scalar = 1.0
            sim._step_info_suppression(_work(sim, epoch))
            assert sim.tx_core.direct_contact_scalar == pytest.approx(0.5)

    def test_response_delay_gates_arming(self) -> None:
        sim = _armed_sim(_spec_block(response_delay_hours=3.0))
        sim.state.trigger_status = "SUSPECTED"
        sim._step_info_suppression(_work(sim, 5))
        assert sim.state.info_recognition_epoch == 5
        assert sim.state.info_suppression_epoch is None
        sim._step_info_suppression(_work(sim, 8))
        assert sim.state.info_suppression_epoch == 8

    def test_arming_is_one_shot(self) -> None:
        sim = _armed_sim(_spec_block())
        sim.state.trigger_status = "SUSPECTED"
        sim._step_info_suppression(_work(sim, 5))
        sim._step_info_suppression(_work(sim, 9))
        assert sim.state.info_recognition_epoch == 5
        assert sim.state.info_suppression_epoch == 5

    def test_self_isolation_runs_while_armed(self) -> None:
        sim = _armed_sim(_spec_block(closed_zones=[]))
        sim.state.trigger_status = "SUSPECTED"
        agents = [_agent(1), _agent(2)]
        work = _work(sim, 5, agents=agents)
        work.syndromic.check_quarantine_compliance.return_value = True
        sim._step_info_suppression(work)
        assert sim.state.info_suppression_admitted_ids == {1, 2}
        assert sim.state.quarantined_ids >= {1, 2}

    def test_isolation_only_when_scope_declared(self) -> None:
        spec = _spec_block(self_isolation_scope=None)
        sim = _armed_sim(spec)
        sim.state.trigger_status = "SUSPECTED"
        work = _work(sim, 5, agents=[_agent(1)])
        sim._step_info_suppression(work)
        work.syndromic.check_quarantine_compliance.assert_not_called()


class TestStreamNeutrality:
    def test_absent_and_disabled_blocks_are_identical(self) -> None:
        """The opt-out path consumes no draws: identical trajectories."""
        epochs = 8
        disabled_spec = PicardRunSpec.from_legacy_yaml(
            str(REPO_ROOT), num_epochs=epochs,
        )
        disabled_spec.legacy_cfg["info_suppression"] = {"enabled": False}
        absent_spec = PicardRunSpec.from_legacy_yaml(
            str(REPO_ROOT), num_epochs=epochs,
        )
        disabled = ShipSimulation(
            disabled_spec, display=False, repo_root=str(REPO_ROOT),
        ).run(n_epochs=epochs)
        absent = ShipSimulation(
            absent_spec, display=False, repo_root=str(REPO_ROOT),
        ).run(n_epochs=epochs)
        for d_rec, a_rec in zip(disabled.history, absent.history):
            assert d_rec["summary"] == a_rec["summary"]
            assert d_rec["trigger_status"] == a_rec["trigger_status"]
            assert (
                d_rec["infection_counters"]
                == a_rec["infection_counters"]
            )
