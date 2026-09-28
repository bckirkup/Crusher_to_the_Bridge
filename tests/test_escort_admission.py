"""Unit tests for the NORO-VENUE-02 escort-latency admission path.

The escort delay splits order -> admission: a compliant host stays mobile
for ``escort_delay_epochs`` epochs after the confinement order before the
escorted admission lands. k=0 must be a byte-identical instant-admission
baseline; k>0 leaves the host un-confined during the window and admits it
at the due epoch via ``step_escort_admissions``.
"""

from __future__ import annotations

import numpy as np

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from orchestrator_epoch import (
    _escort_delay_epochs,
    step_escort_admissions,
    step_fred_compliance,
    try_admit_to_quarantine,
)
from orchestrator_types import SimulationState


def _syn(delay_epochs: int, compliance: float = 1.0) -> SyndromicSurveillance:
    return SyndromicSurveillance(
        quarantine_compliance=compliance,
        reluctant_fraction=0.0,
        escort_delay_epochs=delay_epochs,
        rng=np.random.default_rng(0),
    )


class _BareModality:
    """A syndromic-like object without the escort attribute (pre-VENUE-02)."""


class TestEscortDelayResolution:
    def test_missing_attribute_reads_zero(self) -> None:
        assert _escort_delay_epochs(_BareModality()) == 0

    def test_params_epoch_and_hours(self) -> None:
        syn = _syn(3)
        assert syn.escort_delay_epochs == 3
        from engines.sim_clock import SimClock
        clock = SimClock()
        syn_h = SyndromicSurveillance(
            quarantine_compliance=1.0,
            escort_delay_hours=2,
            clock=clock,
            rng=np.random.default_rng(0),
        )
        assert syn_h.escort_delay_epochs == clock.epochs_for_hours(2)


class TestTryAdmitEscort:
    def test_zero_delay_is_instant_baseline(self) -> None:
        state = SimulationState()
        syn = _syn(0)
        assert try_admit_to_quarantine(
            10, 7, state, syn,
            action_ok="immediate_compliance", action_refuse="refused",
        ) is True
        assert 7 in state.quarantined_ids
        assert 7 not in state.escort_pending
        assert state.compliance_log[-1]["action"] == "immediate_compliance"

    def test_delay_queues_escort_not_admission(self) -> None:
        state = SimulationState()
        syn = _syn(2)
        assert try_admit_to_quarantine(
            10, 7, state, syn,
            action_ok="immediate_compliance", action_refuse="refused",
        ) is False
        assert state.escort_pending == {7: 12}
        assert 7 not in state.quarantined_ids
        entry = state.compliance_log[-1]
        assert entry["action"] == "escort_order"
        assert entry["escort_due_epoch"] == 12
        assert entry["compliance_class"] == "compliant"
        assert state.compliance_class_by_agent[7] == "compliant"

    def test_pending_host_not_reordered(self) -> None:
        state = SimulationState()
        syn = _syn(2)
        try_admit_to_quarantine(
            10, 7, state, syn, action_ok="ok", action_refuse="ref",
        )
        n_log = len(state.compliance_log)
        assert try_admit_to_quarantine(
            11, 7, state, syn, action_ok="ok", action_refuse="ref",
        ) is False
        assert len(state.compliance_log) == n_log
        assert state.escort_pending == {7: 12}

    def test_refusal_unaffected_by_delay(self) -> None:
        state = SimulationState()
        syn = _syn(2, compliance=0.0)
        assert try_admit_to_quarantine(
            10, 7, state, syn,
            action_ok="ok", action_refuse="refused_quarantine",
        ) is False
        assert 7 in state.quarantine_refusers
        assert state.quarantine_order_epoch[7] == 10
        assert 7 not in state.escort_pending
        assert state.compliance_log[-1]["action"] == "refused_quarantine"


class TestStepEscortAdmissions:
    def test_admits_only_at_due_epoch(self) -> None:
        state = SimulationState()
        syn = _syn(2)
        try_admit_to_quarantine(
            10, 7, state, syn, action_ok="ok", action_refuse="ref",
        )
        step_escort_admissions(11, state)
        assert 7 not in state.quarantined_ids
        assert 7 in state.escort_pending
        step_escort_admissions(12, state)
        assert 7 in state.quarantined_ids
        assert 7 not in state.escort_pending
        assert state.compliance_log[-1]["action"] == "escorted_admission"
        assert state.compliance_log[-1]["epoch"] == 12
        assert state.compliance_log[-1]["compliance_class"] == "compliant"

    def test_multi_host_due_ordering(self) -> None:
        state = SimulationState()
        syn = _syn(1)
        for aid in (9, 4, 7):
            try_admit_to_quarantine(
                5, aid, state, syn, action_ok="ok", action_refuse="ref",
            )
        step_escort_admissions(6, state)
        assert state.quarantined_ids == {4, 7, 9}
        admits = [
            e["agent_id"] for e in state.compliance_log
            if e["action"] == "escorted_admission"
        ]
        assert admits == [4, 7, 9]


class TestDelayedComplianceEscort:
    def test_delayed_compliance_queues_escort(self) -> None:
        state = SimulationState()
        syn = _syn(2, compliance=0.0)
        # Refuse the first order; then flip to compliant for the recheck.
        try_admit_to_quarantine(
            10, 7, state, syn, action_ok="ok", action_refuse="ref",
        )
        assert 7 in state.quarantine_refusers
        syn._compliance_class[7] = "compliant"
        state.quarantine_order_epoch[7] = 10
        step_fred_compliance(14, state, syn)
        assert 7 not in state.quarantine_refusers
        assert state.escort_pending == {7: 16}
        assert 7 not in state.quarantined_ids
        step_escort_admissions(16, state)
        assert 7 in state.quarantined_ids

    def test_delayed_compliance_zero_delay_admits(self) -> None:
        state = SimulationState()
        syn = _syn(0, compliance=0.0)
        try_admit_to_quarantine(
            10, 7, state, syn, action_ok="ok", action_refuse="ref",
        )
        syn._compliance_class[7] = "compliant"
        state.quarantine_order_epoch[7] = 10
        step_fred_compliance(14, state, syn)
        assert 7 in state.quarantined_ids
        assert 7 not in state.escort_pending
