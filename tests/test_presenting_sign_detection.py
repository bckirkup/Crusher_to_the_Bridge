"""Unit tests for the NORO-DETECT-01 presenting-sign detection path.

The ``presenting_sign`` trigger gates a symptomatic confinement order on
the pathogen profile's declared observable sign (norwalk_gi: first
emesis) plus ``clinic_wait_epochs``; the host stays mobile through the
wait and the separate escort delay still governs order->admission.
Symptomatics on non-sign pathogens, or sign-declaring infections that
can never produce the sign (non-vomiting axis, empty schedule draw),
keep the onset-order channel. ``onset`` is the labelled baseline and
must reproduce VENUE-02 behaviour seed-for-seed.
"""

from __future__ import annotations

import numpy as np
import pytest

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from orchestrator_epoch import (
    _sign_channel_scan_agent,
    confine_agents,
    step_presenting_sign_detection,
)
from orchestrator_types import SimulationState

NORO = "norwalk_gi"
FLU = "influenza_a"
SIGN_MAP = {NORO: "emesis"}


def _syn(
    wait: int,
    trigger: str = "presenting_sign",
    escort: int = 1,
) -> SyndromicSurveillance:
    return SyndromicSurveillance(
        quarantine_compliance=1.0,
        reluctant_fraction=0.0,
        escort_delay_epochs=escort,
        symptomatic_order_trigger=trigger,
        clinic_wait_epochs=wait,
        symptom_severity_profiles={
            pid: {"observation_model": {"presenting_sign": "emesis"}}
            for pid in SIGN_MAP
        },
        rng=np.random.default_rng(0),
    )


def _agent(
    aid: int,
    *,
    illness: IllnessStatus | None = IllnessStatus.SYMPTOMATIC,
    vomiting: bool | None = True,
    pid: str = NORO,
    schedule: list[float] | None = None,
    records: list[dict] | None = None,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid, role="passenger", immune=False,
        home_zone="Cabin", dining_zone="Dining", work_zone="Crew",
        free_zone="Promenade", schedule=["Cabin"] * 24,
    )
    if illness is not None:
        inf = {"illness": illness}
        if vomiting is not None:
            inf["symptom_axes"] = {"vomiting": vomiting}
        agent.infections[pid] = inf
    if schedule is not None:
        agent.emesis_episode_schedule_by_pathogen[pid] = list(schedule)
    if records is not None:
        agent.emesis_deposition_records_by_pathogen[pid] = records
    return agent


class _Engine:
    def __init__(self, agents: list[KorkinAgent]) -> None:
        self.agents = list(agents)


def _symptomatic_dict(aid: int) -> dict:
    """Order-layer projection that flags symptomatic."""
    return {"agent_id": aid, "symptom_presentation": "symptomatic"}


class TestTriggerResolution:
    def test_unknown_trigger_rejected(self) -> None:
        with pytest.raises(ValueError, match="symptomatic_order_trigger"):
            SyndromicSurveillance(
                symptomatic_order_trigger="emisis",
                rng=np.random.default_rng(0),
            )

    def test_hours_resolve_to_epochs(self) -> None:
        from engines.sim_clock import SimClock
        clock = SimClock()
        syn = SyndromicSurveillance(
            symptomatic_order_trigger="presenting_sign",
            clinic_wait_hours=12,
            clock=clock,
            rng=np.random.default_rng(0),
        )
        assert syn.clinic_wait_epochs == clock.epochs_for_hours(12)

    def test_sign_map_from_profiles(self) -> None:
        syn = _syn(6)
        assert syn.presenting_sign_by_pathogen == {NORO: "emesis"}
        bare = SyndromicSurveillance(rng=np.random.default_rng(0))
        assert bare.presenting_sign_by_pathogen == {}


class TestScanAgent:
    def test_vomiting_symptomatic_is_gated(self) -> None:
        agent = _agent(1, schedule=[0.5, 3.0])
        gated, onset, epochs = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert gated
        assert not onset
        assert epochs == []

    def test_sign_epoch_from_first_record(self) -> None:
        agent = _agent(1, schedule=[0.5], records=[{"epoch": 9}])
        gated, onset, epochs = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert gated
        assert not onset
        assert epochs == [9]

    def test_non_vomiting_axis_keeps_onset_channel(self) -> None:
        agent = _agent(1, vomiting=False)
        gated, onset, epochs = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert not gated
        assert onset
        assert epochs == []

    def test_empty_schedule_keeps_onset_channel(self) -> None:
        agent = _agent(1, schedule=[])
        gated, onset, _ = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert not gated
        assert onset

    def test_non_sign_pathogen_keeps_onset_channel(self) -> None:
        agent = _agent(1, pid=FLU)
        gated, onset, _ = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert not gated
        assert onset

    def test_coinfection_prefers_onset_channel(self) -> None:
        agent = _agent(1, schedule=[1.0])
        agent.infections[FLU] = {"illness": IllnessStatus.SYMPTOMATIC}
        gated, onset, _ = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert gated
        assert onset

    def test_asymptomatic_infection_neither_channel(self) -> None:
        agent = _agent(1, illness=IllnessStatus.NOT_ILL)
        gated, onset, _ = _sign_channel_scan_agent(agent, SIGN_MAP)
        assert not gated
        assert not onset


class TestScanStep:
    def test_onset_trigger_is_noop(self) -> None:
        state = SimulationState()
        syn = _syn(0, trigger="onset")
        agent = _agent(1, schedule=[1.0], records=[{"epoch": 3}])
        step_presenting_sign_detection(5, _Engine([agent]), state, syn)
        assert not state.sign_gated_ids
        assert not state.presenting_sign_epoch

    def test_gated_then_due_at_sign_plus_wait(self) -> None:
        state = SimulationState()
        syn = _syn(6)
        agent = _agent(1, schedule=[1.0])
        engine = _Engine([agent])
        step_presenting_sign_detection(10, engine, state, syn)
        assert state.sign_gated_ids == {1}
        assert 1 not in state.presenting_sign_epoch
        assert 1 not in state.sign_order_due_epoch
        # First emesis lands at epoch 10.
        agent.emesis_deposition_records_by_pathogen[NORO] = [{"epoch": 10}]
        step_presenting_sign_detection(10, engine, state, syn)
        assert state.presenting_sign_epoch[1] == 10
        assert state.sign_order_due_epoch[1] == 16

    def test_sign_epoch_latches_earliest(self) -> None:
        state = SimulationState()
        syn = _syn(1)
        agent = _agent(1, schedule=[1.0], records=[{"epoch": 4}, {"epoch": 7}])
        step_presenting_sign_detection(9, _Engine([agent]), state, syn)
        assert state.presenting_sign_epoch[1] == 4
        assert state.sign_order_due_epoch[1] == 5


class TestConfineGate:
    def test_sign_gated_host_not_ordered_before_sign(self) -> None:
        state = SimulationState()
        syn = _syn(2)
        agent = _agent(7, schedule=[1.0])
        step_presenting_sign_detection(10, _Engine([agent]), state, syn)
        confine_agents(10, [_symptomatic_dict(7)], state, syn, False)
        assert not state.compliance_log  # no order written while gated

    def test_order_lands_at_sign_plus_wait(self) -> None:
        state = SimulationState()
        syn = _syn(6)
        agent = _agent(7, schedule=[1.0], records=[{"epoch": 10}])
        engine = _Engine([agent])
        step_presenting_sign_detection(10, engine, state, syn)
        confine_agents(15, [_symptomatic_dict(7)], state, syn, False)
        assert not state.compliance_log  # wait not elapsed at 15
        confine_agents(16, [_symptomatic_dict(7)], state, syn, False)
        assert state.compliance_log[-1]["action"] == "escort_order"
        assert state.compliance_log[-1]["detection_channel"] == "sign"
        assert state.compliance_log[-1]["escort_due_epoch"] == 17

    def test_non_vomiting_symptomatic_ordered_via_onset(self) -> None:
        state = SimulationState()
        syn = _syn(6)
        agent = _agent(8, vomiting=False)
        step_presenting_sign_detection(10, _Engine([agent]), state, syn)
        assert 8 not in state.sign_gated_ids
        confine_agents(10, [_symptomatic_dict(8)], state, syn, False)
        entry = state.compliance_log[-1]
        assert entry["action"] == "escort_order"
        assert entry["detection_channel"] == "onset"

    def test_onset_trigger_ignores_gate(self) -> None:
        state = SimulationState()
        syn = _syn(6, trigger="onset")
        confine_agents(10, [_symptomatic_dict(9)], state, syn, False)
        assert state.compliance_log[-1]["action"] == "escort_order"
        assert state.compliance_log[-1]["detection_channel"] == "onset"
