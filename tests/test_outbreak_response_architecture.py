"""
Tests for outbreak response architecture (SOPs / decision latency / compliance).

Covers the three systems separated after Campaign v4:
1. Attack-rate escalation + SOP min_escalation_status gates
2. Decision latency (pending transitions + per-SOP activation delay)
3. Bimodal compliance classes (compliant / reluctant / defiant)
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.cost_ledger import CostLedger
from crusher_labs.modalities.syndromic import SyndromicSurveillance
from crusher_labs.protocol_engine import ProtocolEngine, StandingProtocol
from decision_engine.actions import ActionEnvelope
from engines.sim_clock import HOURS, SimClock
from orchestrator_init import (
    apply_escalation_latency,
    check_escalation,
    pathogen_profiles_are_respiratory,
    propose_escalation_level,
)
from orchestrator_types import (
    STATUS_ALERT,
    STATUS_BASELINE,
    STATUS_CONFIRMED,
    STATUS_LOCKDOWN,
    STATUS_RANK,
    STATUS_SUSPECTED,
)
from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    generate_tier_runs,
    load_manifest,
)


def test_respiratory_mode_detection() -> None:
    assert pathogen_profiles_are_respiratory({
        "x": {"clinical_presentation": {"syndromes": ["respiratory"]}},
    })
    assert not pathogen_profiles_are_respiratory({
        "x": {"clinical_presentation": {"syndromes": ["gastrointestinal"]}},
    })


def test_propose_respiratory_alert_on_one_confirmed() -> None:
    cfg = {
        "escalation": {
            "alert_sick_call_threshold": 99,
            "respiratory_overrides": {"alert_confirmed_cases": 1},
        },
    }
    proposed = propose_escalation_level(
        STATUS_BASELINE, {"sick_call_count": 0}, cfg,
        cumulative_confirmed_cases=1, respiratory_mode=True,
    )
    assert proposed == STATUS_ALERT


@pytest.mark.timeout(240)
def test_hourly_reporting_drives_autonomous_escalation() -> None:
    """Integration coverage: hourly reporting reaches the ladder without forcing calls.

    Rebaselined for the dose-pathway dimensional fix: corrected airborne and
    ingestion doses delay detection, so this integration run spans seven days
    rather than four while retaining the original escalation bound.
    """
    epochs = 168
    spec = PicardRunSpec.from_legacy_yaml(REPO_ROOT, num_epochs=epochs)
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    sim.initialize()

    true_positive_events: list[int] = []
    syndromic = sim.modalities["syndromic"]
    original_query = syndromic.query_ground_truth

    def capture_query(*args, **kwargs):
        result = original_query(*args, **kwargs)
        true_positive_events.extend(result.get("true_positive_ids", []))
        return result

    syndromic.query_ground_truth = capture_query
    statuses: list[str] = []
    for epoch in range(epochs):
        statuses.append(
            sim.step(ActionEnvelope(epoch=epoch, actions={})).trigger_status,
        )

    first_suspected = next(
        (
            epoch for epoch, status in enumerate(statuses)
            if status in {STATUS_SUSPECTED, STATUS_CONFIRMED, STATUS_LOCKDOWN}
        ),
        None,
    )

    assert true_positive_events, "hourly reporting produced no true-positive call"
    assert sim.state is not None
    assert sim.state.cumulative_confirmed_case_ids, (
        "reported case did not produce a confirmed clinical case"
    )
    assert first_suspected is not None
    # Lower common norovirus shedding variance delays this integration path,
    # while the onset-based contract still bounds escalation within five days.
    assert 24 <= first_suspected <= 120
    assert [STATUS_RANK[status] for status in statuses] == sorted(
        STATUS_RANK[status] for status in statuses
    )


def test_sop_min_escalation_gate() -> None:
    proto = StandingProtocol({
        "protocol_id": "SOP-009",
        "name": "Lockdown",
        "trigger": {
            "instrument_class": "clinical_qpcr",
            "stoplight_level": "RED",
            "min_agents_affected": 1,
        },
        "modifiers": {"confine_all_to_quarters": True},
        "min_escalation_status": "LOCKDOWN",
    })
    lights = {"clinical_qpcr": {"1": "RED", "2": "RED", "3": "RED"}}
    assert proto.is_triggered(lights, trigger_status=STATUS_CONFIRMED) is False
    assert proto.is_triggered(lights, trigger_status=STATUS_LOCKDOWN) is True


def test_sop_activation_delay() -> None:
    proto = StandingProtocol({
        "protocol_id": "SOP-008",
        "name": "Confine symptomatic",
        "trigger": {
            "instrument_class": "clinical_rdt",
            "stoplight_level": "RED",
            "min_agents_affected": 1,
        },
        "modifiers": {"confine_symptomatic_to_quarters": True},
        "activation_delay_epochs": 2,
    })
    ledger = CostLedger()
    engine = ProtocolEngine([proto], ledger)
    lights = {"clinical_rdt": {"1": "RED", "2": "RED"}}

    mods0 = engine.evaluate_epoch(0, lights)
    assert mods0 == []
    mods1 = engine.evaluate_epoch(1, lights)
    assert mods1 == []
    mods2 = engine.evaluate_epoch(2, lights)
    assert len(mods2) == 1
    assert mods2[0]["protocol_id"] == "SOP-008"


def test_activation_delay_hours_grades_protocol_activation() -> None:
    first_activation: list[int] = []
    for delay in (0, 6, 24, 72):
        proto = StandingProtocol({
            "protocol_id": "SOP-008",
            "name": "Confine symptomatic",
            "trigger": {
                "instrument_class": "clinical_rdt",
                "stoplight_level": "RED",
                "min_agents_affected": 1,
            },
            "modifiers": {"confine_symptomatic_to_quarters": True},
            "activation_delay_hours": delay,
        })
        engine = ProtocolEngine([proto], CostLedger())
        lights = {"clinical_rdt": {"1": "RED"}}
        activation = next(
            epoch for epoch in range(80)
            if engine.evaluate_epoch(epoch, lights)
        )
        first_activation.append(activation)
    assert first_activation == sorted(first_activation)
    assert min(
        later - earlier
        for earlier, later in zip(first_activation, first_activation[1:])
    ) >= 6


def test_reluctant_delay_hours_grades_compliance_timing() -> None:
    first_compliance: list[int] = []
    for delay in (0, 6, 24, 72):
        syn = SyndromicSurveillance(
            quarantine_compliance=0.0,
            reluctant_fraction=1.0,
            reluctant_delay_hours=delay,
            clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
            rng=np.random.default_rng(7),
        )
        first_compliance.append(
            next(
                epoch for epoch in range(80)
                if syn.check_quarantine_compliance(1, epoch)
            )
        )
    assert first_compliance == [0, 6, 24, 72]


def test_apply_escalation_latency_sensitivity() -> None:
    """Config sensitivity: delay 0 vs 2 changes when status takes effect."""
    cfg0 = {"escalation": {"decision_latency": {"alert_delay_epochs": 0}}}
    cfg2 = {"escalation": {"decision_latency": {"alert_delay_epochs": 2}}}
    eff0, pend0 = apply_escalation_latency(
        STATUS_BASELINE, STATUS_ALERT, 0, None, cfg0,
    )
    eff2, pend2 = apply_escalation_latency(
        STATUS_BASELINE, STATUS_ALERT, 0, None, cfg2,
    )
    assert eff0 == STATUS_ALERT
    assert pend0 is None
    assert eff2 == STATUS_BASELINE
    assert pend2 is not None


def test_compliance_by_class_sensitivity() -> None:
    """Config sensitivity: crew vs passenger_young compliance class draw."""
    syn_crew = SyndromicSurveillance(
        quarantine_compliance=0.5,
        compliance_by_class={"crew": 1.0, "passenger_young": 0.0},
        reluctant_fraction=1.0,
        reluctant_delay_epochs=99,
        rng=np.random.default_rng(0),
    )
    syn_young = SyndromicSurveillance(
        quarantine_compliance=0.5,
        compliance_by_class={"crew": 1.0, "passenger_young": 0.0},
        reluctant_fraction=1.0,
        reluctant_delay_epochs=99,
        rng=np.random.default_rng(0),
    )
    assert syn_crew.check_quarantine_compliance(
        1, 0, agent_class="crew_general",
    ) is True
    assert syn_young.check_quarantine_compliance(
        2, 0, agent_class="passenger_general",
    ) is False


def test_t15_sop_threshold_generator() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t15_sop_threshold_sweep"))
    assert len(runs) == (
        4 * 4 * 4 * 5  # pathogens × suspect × lockdown × seeds
    )
    sample = next(s for rid, s in runs if "larnever" in rid)
    assert sample["config_overrides"]["escalation"]["lockdown_attack_rate"] is None
    assert sample["campaign_parameters"]["lockdown_attack_rate"] == "never"


def test_t16_reluctant_generator() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t16_reluctant_fraction_sweep"))
    assert len(runs) == 4 * 3 * 4 * 5
    sample = next(s for rid, s in runs if "rf75" in rid and "rd48" in rid)
    fred = sample["config_overrides"]["fred_behavior"]
    assert fred["reluctant_fraction"] == pytest.approx(0.75)
    assert fred["reluctant_delay_hours"] == 48


def test_t11_decision_latency_generator() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t11_intervention_timing"))
    assert any("lat24" in rid for rid, _ in runs)
    sample = next(s for rid, s in runs if "lat24" in rid)
    lat = sample["config_overrides"]["escalation"]["decision_latency"]
    assert lat["confirmed_delay_hours"] == 24
    assert sample["campaign_parameters"]["decision_latency_epochs"] == 24


def test_check_escalation_attack_rate_sensitivity() -> None:
    """Config sensitivity: changing suspect_attack_rate changes proposed level."""
    agents = [
        {
            "agent_id": i, "role": "passenger",
            "infection_state": "infected" if i < 2 else "susceptible",
            "symptom_presentation": "symptomatic" if i < 2 else "asymptomatic",
        }
        for i in range(100)  # 2%
    ]
    syn = {"sick_call_count": 5}
    low = {"escalation": {"suspect_attack_rate": 0.01}}
    high = {"escalation": {"suspect_attack_rate": 0.05}}
    s_low, _, _ = check_escalation(STATUS_ALERT, syn, None, low, agents=agents)
    s_high, _, _ = check_escalation(STATUS_ALERT, syn, None, high, agents=agents)
    assert s_low == STATUS_SUSPECTED
    assert s_high == STATUS_ALERT


def test_refuse_quarantine_forces_defiant_forever() -> None:
    syn = SyndromicSurveillance(
        quarantine_compliance=1.0,
        reluctant_delay_epochs=1,
        rng=np.random.default_rng(0),
    )
    assert syn.check_quarantine_compliance(
        11, 0, behavioral_override="refuse_quarantine",
    ) is False
    assert syn.check_quarantine_compliance(
        11, 100, behavioral_override="refuse_quarantine",
    ) is False
    assert syn._compliance_class[11] == "defiant"


def test_confinement_scope_alert_symptomatic_only() -> None:
    from unittest.mock import MagicMock

    from orchestrator_epoch import step_quarantine_confinement
    from orchestrator_types import (
        SYMPTOM_ASYMPTOMATIC,
        SYMPTOM_SYMPTOMATIC,
        SimulationState,
    )

    state = SimulationState()
    agents = [
        {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC},
        {"agent_id": 1, "symptom_status": SYMPTOM_SYMPTOMATIC},
    ]
    mock = MagicMock()
    mock.check_quarantine_compliance.return_value = True
    step_quarantine_confinement(3, agents, {}, STATUS_ALERT, state, mock)
    assert 1 in state.quarantined_ids
    assert 0 not in state.quarantined_ids


def test_confinement_scope_confirmed_includes_cabin_contacts() -> None:
    from unittest.mock import MagicMock

    from orchestrator_epoch import step_quarantine_confinement
    from orchestrator_types import (
        SYMPTOM_ASYMPTOMATIC,
        SYMPTOM_SYMPTOMATIC,
        SimulationState,
    )

    state = SimulationState()
    state.cumulative_confirmed_case_ids.add(1)
    agents = [
        {
            "agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC,
            "cabin_mate_ids": [1],
        },
        {
            "agent_id": 1, "symptom_status": SYMPTOM_SYMPTOMATIC,
            "cabin_mate_ids": [0],
        },
        {"agent_id": 2, "symptom_status": SYMPTOM_ASYMPTOMATIC},
    ]
    mock = MagicMock()
    mock.check_quarantine_compliance.return_value = True
    step_quarantine_confinement(3, agents, {}, STATUS_CONFIRMED, state, mock)
    assert 0 in state.quarantined_ids  # cabin contact of confirmed
    assert 1 in state.quarantined_ids
    assert 2 not in state.quarantined_ids


def test_campaign_injects_lockdown_attack_rate_default() -> None:
    manifest = load_manifest()
    _rid, sample = next(generate_tier_runs(manifest, "t1_pathogen_baselines"))
    esc = sample["config_overrides"]["escalation"]
    assert esc["lockdown_attack_rate"] == pytest.approx(0.05)
    assert esc["suspect_attack_rate"] == pytest.approx(0.02)


def test_sop009_blocked_until_lockdown_in_engine() -> None:
    """Config sensitivity: SOP-009 absent at CONFIRMED, present at LOCKDOWN."""
    proto = StandingProtocol({
        "protocol_id": "SOP-009",
        "name": "Lockdown",
        "trigger": {
            "instrument_class": "clinical_qpcr",
            "stoplight_level": "RED",
            "min_agents_affected": 1,
        },
        "modifiers": {"confine_all_to_quarters": True},
        "min_escalation_status": "LOCKDOWN",
    })
    ledger = CostLedger()
    engine = ProtocolEngine([proto], ledger)
    lights = {"clinical_qpcr": {"1": "RED", "2": "RED", "3": "RED"}}

    mods_confirmed = engine.evaluate_epoch(
        0, lights, trigger_status=STATUS_CONFIRMED,
    )
    assert mods_confirmed == []

    mods_lockdown = engine.evaluate_epoch(
        1, lights, trigger_status=STATUS_LOCKDOWN,
    )
    assert len(mods_lockdown) == 1
    assert mods_lockdown[0]["modifiers"]["confine_all_to_quarters"] is True
