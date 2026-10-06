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


# ── CREW-WINDOW-02: activity-scoped + fractional exemption gates ──────────
#
# ``exempt_work_zones`` confines an exempt-classed agent when its posted
# ``work_zone`` is not on the order's essential list; ``exempt_fraction``
# draws a sticky exact-count exempt subset per order/class at activation.

_CREW_EXEMPT = ["crew_general", "crew_medical", "crew_engineering",
                "crew_galley"]


def _posted_agent(aid, cls, zone, symptomatic=False):
    return {**_agent(aid, cls, symptomatic=symptomatic), "work_zone": zone}


def _zone_order(protocol_id, zones, *, enforced=True, symptomatic=False):
    order = _order(protocol_id, all_quarters=True, exempt=_CREW_EXEMPT,
                   enforced=enforced)
    order["modifiers"]["exempt_work_zones"] = list(zones)
    if symptomatic:
        order["modifiers"].pop("confine_all_to_quarters")
        order["modifiers"].pop("confinement_enforced")
        order["modifiers"]["confine_symptomatic_to_quarters"] = True
    return order


def _frac_order(protocol_id, fractions, *, enforced=True):
    order = _order(protocol_id, all_quarters=True, exempt=_CREW_EXEMPT,
                   enforced=enforced)
    order["modifiers"]["exempt_fraction"] = dict(fractions)
    return order


def _run_seeded(agents, active_mods, seed, epochs=(3,)):
    state = SimulationState()
    for epoch in epochs:
        step_quarantine_confinement(
            epoch, agents, {}, STATUS_BASELINE, state, _syndromic(),
            active_mods=active_mods, run_seed=seed,
        )
    return state


def test_exempt_work_zones_confines_nonessential_posted_crew():
    agents = [
        _posted_agent(1, "crew_general", "Casino"),
        _posted_agent(2, "crew_general", "Main_Galley_Aft"),
        _posted_agent(3, "crew_general", "Crew_Mess_Main"),
        _posted_agent(4, "passenger_general", "Casino"),
    ]
    state = _run_seeded(agents, [
        _zone_order("SOP-017-NARROW", ["Main_Galley_Aft", "Crew_Mess_Main"]),
    ], seed=20200205)
    assert state.quarantined_ids == {1, 4}


def test_exempt_work_zones_holds_on_the_voluntary_path():
    agents = [
        _posted_agent(1, "crew_general", "Casino"),
        _posted_agent(2, "crew_general", "Bridge"),
    ]
    state = _run_seeded(agents, [
        _zone_order("SOP-017-NARROW", ["Bridge"], enforced=False),
    ], seed=20200205)
    assert state.quarantined_ids == {1}
    assert state.compliance_log[-1]["action"] != "enforced_confinement"


def test_exempt_work_zones_reaches_symptomatic_orders():
    agents = [
        _posted_agent(1, "crew_general", "Casino", symptomatic=True),
        _posted_agent(2, "crew_general", "Bridge", symptomatic=True),
    ]
    state = _run_seeded(agents, [
        _zone_order("SOP-017-NARROW", ["Bridge"], symptomatic=True),
    ], seed=20200205)
    assert state.quarantined_ids == {1}


def test_exempt_fraction_draws_exact_count_and_stays_sticky():
    agents = [_posted_agent(i, "crew_general", "Casino")
              for i in range(1, 13)]
    agents.append(_posted_agent(20, "passenger_general", "Casino"))
    state = _run_seeded(agents, [
        _frac_order("SOP-017-QUARTER", {"crew_general": 0.25}),
    ], seed=20200205, epochs=(3, 4, 5))
    drawn = state.exempt_fraction_draws["SOP-017-QUARTER"]["crew_general"]
    assert len(drawn) == 3
    assert state.quarantined_ids == (
        set(range(1, 13)) - set(drawn)) | {20}


def test_exempt_fraction_is_seeded_by_run_seed_not_voyage_stream():
    agents = [_posted_agent(i, "crew_general", "Casino")
              for i in range(1, 9)]
    order = _frac_order("SOP-017-QUARTER", {"crew_general": 0.5})
    a = _run_seeded(agents, [order], seed=111)
    b = _run_seeded(agents, [order], seed=111)
    c = _run_seeded(agents, [order], seed=222)
    drawn_a = a.exempt_fraction_draws["SOP-017-QUARTER"]["crew_general"]
    assert drawn_a == b.exempt_fraction_draws["SOP-017-QUARTER"]["crew_general"]
    assert drawn_a != c.exempt_fraction_draws["SOP-017-QUARTER"]["crew_general"]


def test_exempt_fraction_leaves_unnamed_exempt_classes_alone():
    agents = [
        _posted_agent(1, "crew_general", "Casino"),
        _posted_agent(2, "crew_general", "Casino"),
        _posted_agent(3, "crew_medical", "Medical_Center"),
        _posted_agent(4, "passenger_general", "Casino"),
    ]
    state = _run_seeded(agents, [
        _frac_order("SOP-017-QUARTER", {"crew_general": 0.0}),
    ], seed=20200205)
    assert state.exempt_fraction_draws == {
        "SOP-017-QUARTER": {"crew_general": []},
    }
    assert state.quarantined_ids == {1, 2, 4}


def test_zone_and_fraction_gates_intersect():
    agents = [
        _posted_agent(1, "crew_general", "Casino"),
        _posted_agent(2, "crew_general", "Casino"),
        _posted_agent(3, "crew_general", "Bridge"),
        _posted_agent(4, "crew_general", "Bridge"),
    ]
    state = _run_seeded(agents, [
        _zone_order("SOP-017-NARROW", ["Bridge"]),
        _frac_order("SOP-017-QUARTER", {"crew_general": 0.5}),
    ], seed=20200205)
    drawn = set(
        state.exempt_fraction_draws["SOP-017-QUARTER"]["crew_general"])
    zone_exempt = {3, 4}
    expected_unconfined = drawn & zone_exempt
    assert state.quarantined_ids == {1, 2, 3, 4} - expected_unconfined


def test_no_gate_modifiers_keep_the_legacy_class_gate():
    agents = [_posted_agent(1, "crew_general", "Casino"),
              _posted_agent(2, "passenger_general", "Casino")]
    state = _run_seeded(agents, [
        _order("SOP-017", all_quarters=True, exempt=_CREW_EXEMPT,
               enforced=True),
    ], seed=20200205)
    assert state.quarantined_ids == {2}
    assert state.exempt_fraction_draws == {}
