"""Per-order confinement exemptions in step_quarantine_confinement.

Exemptions belong to the order that declares them: an agent is confined when
ANY active order confines it under THAT order's own ``exempt_classes``. This
is what lets a counterfactual all-hands quarantine (exempt_classes = [])
confine crew while a coexisting order still exempts them.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from orchestrator_epoch import step_quarantine_confinement
from orchestrator_types import (
    STATUS_ALERT,
    STATUS_BASELINE,
    SimulationState,
)
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC,
    agent_axes_dict,
)

_SUSCEPTIBLE_AXES = agent_axes_dict(
    INFECTION_SUSCEPTIBLE, PRESENTATION_ASYMPTOMATIC, COMPLIANCE_COMPLIANT,
)
_SYMPTOMATIC_AXES = agent_axes_dict(
    INFECTION_INFECTED, PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT,
)


def _order(protocol_id, *, all_quarters=False, symptomatic=False,
           exempt=(), enforced=False):
    modifiers = {}
    if all_quarters:
        modifiers["confine_all_to_quarters"] = True
        modifiers["confinement_enforced"] = enforced
    if symptomatic:
        modifiers["confine_symptomatic_to_quarters"] = True
    modifiers["exempt_classes"] = list(exempt)
    return {"protocol_id": protocol_id, "modifiers": modifiers}


def _syndromic(compliant=True):
    syn = MagicMock()
    syn.check_quarantine_compliance.return_value = compliant
    syn._compliance_class = {}
    return syn


def _agent(aid, cls, symptomatic=False):
    return {
        "agent_id": aid,
        "agent_class": cls,
        **(_SYMPTOMATIC_AXES if symptomatic else _SUSCEPTIBLE_AXES),
    }


def _run(agents, active_mods, merged_mods=None, status=STATUS_BASELINE,
         syndromic=None):
    state = SimulationState()
    step_quarantine_confinement(
        3, agents, merged_mods or {}, status, state,
        syndromic or _syndromic(), active_mods=active_mods,
    )
    return state


def test_whole_body_exemptions_are_per_order_intersection():
    agents = [
        _agent(1, "class_A"), _agent(2, "class_B"), _agent(3, "class_C"),
    ]
    state = _run(agents, [
        _order("SOP-X", all_quarters=True, exempt=["class_A", "class_B"]),
        _order("SOP-Y", all_quarters=True, exempt=["class_B", "class_C"]),
    ])
    # B is exempt under BOTH orders; A and C each confined by the other order.
    assert state.quarantined_ids == {1, 3}


def test_empty_exempt_order_confines_everyone_despite_exempt_sibling():
    agents = [_agent(1, "passenger_general"), _agent(2, "crew_general")]
    state = _run(agents, [
        _order("SOP-017-ALLHANDS", all_quarters=True, exempt=[]),
        _order("SOP-011", symptomatic=True,
               exempt=["crew_general", "crew_medical",
                       "crew_engineering", "crew_galley"]),
    ])
    assert state.quarantined_ids == {1, 2}


def test_enforced_order_admits_before_voluntary_regardless_of_list_order():
    for active_mods in (
        [
            _order("SOP-A", all_quarters=True, enforced=False),
            _order("SOP-B", all_quarters=True, enforced=True),
        ],
        [
            _order("SOP-B", all_quarters=True, enforced=True),
            _order("SOP-A", all_quarters=True, enforced=False),
        ],
    ):
        state = _run([_agent(1, "passenger_general")], active_mods)
        assert 1 in state.quarantined_ids
        assert state.compliance_log[-1]["action"] == "enforced_confinement"


def test_symptomatic_orders_confine_under_their_own_exemptions():
    agents = [
        _agent(1, "passenger_general", symptomatic=True),
        _agent(2, "crew_general", symptomatic=True),
    ]
    state = _run(agents, [
        _order("SOP-008", symptomatic=True),
        _order("SOP-011", symptomatic=True, exempt=["crew_general"]),
    ])
    # The unexempted order confines the symptomatic crew member.
    assert state.quarantined_ids == {1, 2}


def test_active_mods_none_keeps_the_legacy_merged_behaviour():
    agents = [_agent(1, "passenger_general"), _agent(2, "crew_general")]
    merged = {
        "confine_all_to_quarters": True,
        "exempt_classes": ["crew_general"],
    }
    state = _run(agents, None, merged_mods=merged)
    assert state.quarantined_ids == {1}
    assert 2 not in state.quarantined_ids


def test_status_driven_symptomatic_path_still_uses_merged_exempt():
    agents = [
        _agent(1, "passenger_general", symptomatic=True),
        _agent(2, "crew_general", symptomatic=True),
    ]
    state = _run(
        agents, [], merged_mods={"exempt_classes": ["crew_general"]},
        status=STATUS_ALERT,
    )
    assert state.quarantined_ids == {1}
