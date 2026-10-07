"""CREW-BERTH-01: crew berthing + work-cohort directives — graded tests.

The mechanisms are declared placement/schedule policies:
``set_crew_berthing`` re-deals crew cabins status-pure inside each
``(home_zone, berth_group)`` pool (anchor-preserving, deterministic)
and, in ``rezone`` mode, swaps working crew into the declared
``berth_zones`` block; ``set_crew_work_cohorts`` splits posted crew
Work blocks into pod turns. Neither draws RNG on any stream. The
witnesses echo through ``crew_window.crew_berthing`` /
``crew_window.crew_work_cohorts``. No hull runs — the engine methods
are bound onto a stub carrying exactly the fields the directives
read/write.
"""

from __future__ import annotations

from functools import partial
from types import SimpleNamespace

from crusher_labs.protocol_engine import (
    apply_crew_berthing,
    apply_crew_work_cohorts,
)
from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    _berth_pool_cabin_size,
)
from picard_framework.covid_boarding_screen import (
    QuarantineAttributionLedger,
    _crew_window_block,
)

CABIN_A = {"name": "CC_A", "type": "Cabin_Corridor",
           "cabin_size_by_class": {"crew_general": 2}}
CABIN_B = {"name": "CC_B", "type": "Cabin_Corridor",
           "cabin_size_by_class": {"crew_general": 2}}
WORK = "Main_Galley_Aft"


def _fresh_berth_witness():
    return {
        "applied_epoch": None, "restored_epoch": None,
        "working_count": 0, "confined_count": 0,
        "pools_redealt": 0, "cabins_formed": 0,
        "single_occupancy": 0, "keys_preserved": 0,
        "mixed_status_cabins": 0,
        "relocated_to_work_zones": 0, "relocated_out": 0,
    }


def _fresh_cohort_witness():
    return {
        "applied_epoch": None, "restored_epoch": None,
        "agents_split": 0, "work_hours_removed": 0,
    }


def _engine(*, agents=(), zones=None, epoch=0):
    """A stub carrying exactly the fields the two directives own, with
    the real KorkinShipEngine methods bound onto it."""
    eng = SimpleNamespace(
        _crew_berthing_key=None,
        _crew_berthing_last_directive=None,
        _saved_crew_berths={},
        _crew_berth_witness=_fresh_berth_witness(),
        _crew_cohorts_key=None,
        _crew_cohorts_last_directive=None,
        _saved_crew_cohort_schedules={},
        _crew_cohort_witness=_fresh_cohort_witness(),
        zones=list(zones or [CABIN_A, CABIN_B]),
        epoch=epoch,
        agents=list(agents),
    )
    for name in (
        "set_crew_berthing", "_crew_berth_apply", "_crew_berth_rezone",
        "_crew_berth_redeal_pool", "_crew_berth_restore",
        "crew_berthing_witness", "set_crew_work_cohorts",
        "_crew_cohorts_split", "_crew_cohorts_restore",
        "crew_work_cohorts_witness",
    ):
        setattr(eng, name, partial(getattr(KorkinShipEngine, name), eng))
    return eng


def _crew(agent_id, *, cls="crew_general", work_zone="", home="CC_A",
          mates=(), berth_group="", schedule=None):
    return SimpleNamespace(
        agent_id=agent_id, role="crew", agent_class=cls,
        work_zone=work_zone, home_zone=home,
        berth_group=berth_group,
        cabin_mate_ids=frozenset(mates),
        schedule=list(schedule or []),
    )


def _pair(a, b):
    a.cabin_mate_ids = frozenset({int(b.agent_id)})
    b.cabin_mate_ids = frozenset({int(a.agent_id)})


def _set_berth(eng, block, *, classes=("crew_general",), zones=(WORK,)):
    return eng.set_crew_berthing(
        block,
        exempt_classes=frozenset(classes),
        exempt_work_zones=frozenset(zones),
    )


def _set_cohorts(eng, block, *, zones=(WORK,)):
    return eng.set_crew_work_cohorts(block, zones=frozenset(zones))


# ── apply_crew_berthing (protocol_engine shim) ─────────────────────────


def test_apply_berthing_none_engine_is_noop():
    apply_crew_berthing(None, None, {"crew_berthing": {"mode": "cohort"}})


def test_apply_berthing_engine_without_setter_is_noop():
    apply_crew_berthing(SimpleNamespace(), None, {"crew_berthing": {}})


def test_apply_berthing_passes_block_and_exempt_sets():
    seen = []
    eng = SimpleNamespace(set_crew_berthing=lambda b, **kw: seen.append(
        (b, kw["exempt_classes"], kw["exempt_work_zones"])) or False)
    apply_crew_berthing(eng, None, {
        "crew_berthing": {"mode": "cohort"},
        "exempt_classes": ["crew_galley"],
        "exempt_work_zones": ["Main_Galley_Aft"],
    })
    apply_crew_berthing(eng, None, {"crew_berthing": "not-a-dict"})
    apply_crew_berthing(eng, None, {})
    assert seen[0][0] == {"mode": "cohort"}
    assert seen[0][1] == frozenset({"crew_galley"})
    assert seen[0][2] == frozenset({"Main_Galley_Aft"})
    assert seen[1] == (None, frozenset(), frozenset())
    assert seen[2] == (None, frozenset(), frozenset())


def test_apply_berthing_registers_berths_only_on_change():
    calls = []
    tx = SimpleNamespace(
        register_cabin_berths=lambda agents: calls.append(list(agents)))
    roster = [_crew(1)]
    eng = SimpleNamespace(
        agents=roster,
        set_crew_berthing=lambda b, **kw: bool(b),
    )
    apply_crew_berthing(eng, tx, {"crew_berthing": {"mode": "cohort"}})
    apply_crew_berthing(eng, tx, {})  # unchanged -> no re-register
    assert calls == [roster]
    # Falling edge that reports a change also re-registers.
    eng.set_crew_berthing = lambda b, **kw: True
    apply_crew_berthing(eng, tx, {})
    assert calls == [roster, roster]


def test_apply_berthing_tx_core_without_register_is_fine():
    eng = SimpleNamespace(
        agents=[], set_crew_berthing=lambda b, **kw: True)
    apply_crew_berthing(eng, SimpleNamespace(),
                        {"crew_berthing": {"mode": "cohort"}})


# ── apply_crew_work_cohorts (protocol_engine shim) ─────────────────────


def test_apply_cohorts_none_engine_is_noop():
    apply_crew_work_cohorts(None, {"crew_work_cohorts": {"pods": 2}})


def test_apply_cohorts_engine_without_setter_is_noop():
    apply_crew_work_cohorts(SimpleNamespace(), {"crew_work_cohorts": {}})


def test_apply_cohorts_zone_resolution_and_falling_edge():
    seen = []
    eng = SimpleNamespace(
        set_crew_work_cohorts=lambda b, **kw: seen.append(
            (b, kw["zones"])) or False)
    # zones inside the block win over the order's exempt_work_zones.
    apply_crew_work_cohorts(eng, {
        "crew_work_cohorts": {"mode": "shift_split", "zones": ["Laundry"]},
        "exempt_work_zones": [WORK],
    })
    # zones absent resolves to the order's merged exempt_work_zones.
    apply_crew_work_cohorts(eng, {
        "crew_work_cohorts": {"mode": "shift_split"},
        "exempt_work_zones": [WORK],
    })
    apply_crew_work_cohorts(eng, {"crew_work_cohorts": "not-a-dict"})
    apply_crew_work_cohorts(eng, {})
    assert seen[0] == ({"mode": "shift_split", "zones": ["Laundry"]},
                       frozenset({"Laundry"}))
    assert seen[1] == ({"mode": "shift_split"}, frozenset({WORK}))
    assert seen[2] == (None, frozenset())
    assert seen[3] == (None, frozenset())


# ── set_crew_berthing: cohort re-deal ──────────────────────────────────


def test_cohort_redeal_is_status_pure_and_anchor_preserving():
    # Six crew in one pool, dealt pairs (1,2) (3,4) (5,6); odds posted
    # to the exempt work zone, evens confined.
    agents = []
    for i in range(1, 7):
        agents.append(_crew(i, work_zone=WORK if i % 2 else ""))
    _pair(agents[0], agents[1])
    _pair(agents[2], agents[3])
    _pair(agents[4], agents[5])
    eng = _engine(agents=agents, epoch=385)
    assert _set_berth(eng, {"mode": "cohort"}) is True
    wit = eng._crew_berth_witness
    assert wit["applied_epoch"] == 385
    assert wit["restored_epoch"] is None
    assert wit["working_count"] == 3
    assert wit["confined_count"] == 3
    assert wit["pools_redealt"] == 1
    assert wit["mixed_status_cabins"] == 0
    # Every cabin groups a single status.
    cabins = {}
    for a in agents:
        ids = frozenset(set(a.cabin_mate_ids) | {int(a.agent_id)})
        cabins.setdefault(ids, ids)
    for ids in cabins:
        statuses = {i in {1, 3, 5} for i in ids}
        assert len(statuses) == 1
    # The three min-id anchors each held a compartment key.
    assert wit["keys_preserved"] == 3
    assert eng.crew_berthing_witness()["berths_held"] == 6
    # Identical call is a no-op edge.
    assert _set_berth(eng, {"mode": "cohort"}) is False


def test_cohort_falling_edge_restores_verbatim():
    agents = []
    for i in range(1, 5):
        agents.append(_crew(i, work_zone=WORK if i % 2 else ""))
    _pair(agents[0], agents[1])
    _pair(agents[2], agents[3])
    saved = {int(a.agent_id): a.cabin_mate_ids for a in agents}
    eng = _engine(agents=agents, epoch=385)
    _set_berth(eng, {"mode": "cohort"})
    eng.epoch = 744
    assert _set_berth(eng, None) is True
    for a in agents:
        assert a.cabin_mate_ids == saved[int(a.agent_id)]
    assert eng._saved_crew_berths == {}
    wit = eng.crew_berthing_witness()
    assert wit["restored_epoch"] == 744
    assert wit["berths_held"] == 0
    # Second falling edge is a no-op.
    assert _set_berth(eng, None) is False


def test_redeal_groups_by_berth_group_and_skips_small_cabins():
    # Pool A: four crew with explicit berth_group; pool B: two crew in a
    # non-cabin zone (cabin_size None -> skipped); passengers ignored.
    a1, a2 = _crew(1, work_zone=WORK, berth_group="g1"), _crew(
        2, berth_group="g1")
    a3, a4 = _crew(3, work_zone=WORK, berth_group="g1"), _crew(
        4, berth_group="g1")
    for a, b in ((a1, a2), (a3, a4)):
        _pair(a, b)
    solo1 = _crew(5, home="Open_Deck", work_zone=WORK)
    solo2 = _crew(6, home="Open_Deck")
    _pair(solo1, solo2)
    pax = SimpleNamespace(agent_id=7, role="passenger",
                          home_zone="CC_A", cabin_mate_ids=frozenset())
    zones = [CABIN_A, CABIN_B, {"name": "Open_Deck", "type": "Outdoor"}]
    eng = _engine(agents=[a1, a2, a3, a4, solo1, solo2, pax],
                  zones=zones)
    _set_berth(eng, {"mode": "cohort"})
    wit = eng._crew_berth_witness
    assert wit["pools_redealt"] == 1  # Open_Deck pool skipped
    assert wit["working_count"] == 3
    assert wit["mixed_status_cabins"] == 0
    # Passenger never entered a pool nor the saved-berths map.
    assert int(pax.agent_id) not in eng._saved_crew_berths


# ── set_crew_berthing: rezone swap ─────────────────────────────────────


def test_rezone_swaps_working_in_and_confined_out():
    w1 = _crew(1, work_zone=WORK, home="CC_A")
    w2 = _crew(3, work_zone=WORK, home="CC_B")
    c1 = _crew(2, home="CC_B")
    c2 = _crew(4, home="CC_B")
    agents = [w1, w2, c1, c2]
    _pair(w1, w2)
    _pair(c1, c2)
    eng = _engine(agents=agents)
    _set_berth(eng, {"mode": "rezone", "berth_zones": ["CC_B"]})
    assert w1.home_zone == "CC_B"     # working crew moved into the block
    assert c1.home_zone == "CC_A"     # confined occupants swapped out
    assert c2.home_zone == "CC_A"
    wit = eng._crew_berth_witness
    assert wit["relocated_to_work_zones"] == 1
    assert wit["relocated_out"] == 2


def test_rezone_noops_on_empty_or_unknown_block():
    a1 = _crew(1, work_zone=WORK, home="CC_A")
    a2 = _crew(2, home="CC_A")
    eng = _engine(agents=[a1, a2])
    _set_berth(eng, {"mode": "rezone"})                    # no berth_zones
    _set_berth(eng, {"mode": "rezone",
                     "berth_zones": ["No_Such_Zone"]})     # all filtered
    assert a1.home_zone == "CC_A"
    wit = eng._crew_berth_witness
    assert wit["relocated_to_work_zones"] == 0
    assert wit["relocated_out"] == 0


def test_rezone_noop_when_no_outside_corridor():
    a1 = _crew(1, work_zone=WORK, home="CC_B")
    a2 = _crew(2, home="CC_B")
    eng = _engine(agents=[a1, a2], zones=[CABIN_B])
    _set_berth(eng, {"mode": "rezone", "berth_zones": ["CC_B"]})
    assert eng._crew_berth_witness["relocated_to_work_zones"] == 0


# ── _berth_pool_cabin_size edges ───────────────────────────────────────


def test_cabin_size_declared_and_fallbacks():
    assert _berth_pool_cabin_size(
        "CC_A", "crew_general", "crew_general", CABIN_A) == 2
    assert _berth_pool_cabin_size(
        "CC_A", "g1", "crew_general", CABIN_A) == 2
    # Non-cabin-corridor zones never pool.
    assert _berth_pool_cabin_size(
        "Open_Deck", "g", "crew_general", {"type": "Outdoor"}) is None
    # Prefix defaults.
    assert _berth_pool_cabin_size(
        "CC_X", "g", "crew_general", {"type": "Cabin_Corridor"}) == 3
    assert _berth_pool_cabin_size(
        "OC_X", "g", "crew_general", {"type": "Cabin_Corridor"}) == 1
    assert _berth_pool_cabin_size(
        "FC_X", "g", "crew_general", {"type": "Cabin_Corridor"}) == 4
    assert _berth_pool_cabin_size(
        "Pax_Deck", "g", "crew_general",
        {"type": "Cabin_Corridor"}) == 2
    # hot_bunk_ratio multiplies; cabin_size < 1 never pools.
    assert _berth_pool_cabin_size(
        "CC_X", "g", "crew_general",
        {"type": "Cabin_Corridor", "hot_bunk_ratio": 2}) == 6
    assert _berth_pool_cabin_size(
        "CC_X", "g", "crew_general",
        {"type": "Cabin_Corridor", "cabin_size": 0}) is None


# ── set_crew_work_cohorts: shift_split ─────────────────────────────────


def test_shift_split_halves_work_runs_and_restores():
    a10 = _crew(10, work_zone=WORK,
                schedule=["Sleep", "Work", "Work", "Work", "Work",
                          "Sleep"])
    a11 = _crew(11, work_zone=WORK,
                schedule=["Sleep", "Work", "Work", "Work", "Work",
                          "Sleep"])
    eng = _engine(agents=[a10, a11], epoch=385)
    assert _set_cohorts(eng, {"mode": "shift_split", "pods": 2}) is True
    # pod = agent_id % 2: 10 keeps the first half, 11 the second.
    assert a10.schedule == ["Sleep", "Work", "Work", "Rest", "Rest",
                            "Sleep"]
    assert a11.schedule == ["Sleep", "Rest", "Rest", "Work", "Work",
                            "Sleep"]
    wit = eng._crew_cohort_witness
    assert wit["applied_epoch"] == 385
    assert wit["agents_split"] == 2
    assert wit["work_hours_removed"] == 4
    assert eng.crew_work_cohorts_witness()["schedules_held"] == 2
    # Identical call is a no-op edge; falling edge restores verbatim.
    assert _set_cohorts(eng, {"mode": "shift_split", "pods": 2}) is False
    eng.epoch = 744
    assert _set_cohorts(eng, None) is True
    assert a10.schedule == ["Sleep", "Work", "Work", "Work", "Work",
                            "Sleep"]
    assert a11.schedule == ["Sleep", "Work", "Work", "Work", "Work",
                            "Sleep"]
    assert eng.crew_work_cohorts_witness()["restored_epoch"] == 744
    assert _set_cohorts(eng, None) is False


def test_shift_split_handles_multiple_runs_and_skips():
    # Two separate Work blocks in one schedule; a passenger and a crew
    # member posted outside the cohort zones are untouched.
    a1 = _crew(1, work_zone=WORK,
               schedule=["Work", "Work", "Meal", "Work", "Work"])
    a2 = _crew(2, work_zone="Laundry_Main",
               schedule=["Work", "Work"])
    pax = SimpleNamespace(agent_id=3, role="passenger",
                          work_zone=WORK, schedule=["Work"])
    empty = _crew(4, work_zone=WORK, schedule=[])
    eng = _engine(agents=[a1, a2, pax, empty])
    _set_cohorts(eng, {"mode": "shift_split", "pods": 2})
    # pod 1 keeps the second turn of each two-hour Work run.
    assert a1.schedule == ["Rest", "Work", "Meal", "Rest", "Work"]
    assert a2.schedule == ["Work", "Work"]
    assert pax.schedule == ["Work"]
    wit = eng._crew_cohort_witness
    assert wit["agents_split"] == 1
    assert wit["work_hours_removed"] == 2


def test_shift_split_pods_one_is_noop_and_other_modes_skip():
    a = _crew(1, work_zone=WORK, schedule=["Work", "Work"])
    eng = _engine(agents=[a])
    _set_cohorts(eng, {"mode": "shift_split", "pods": 1})
    assert a.schedule == ["Work", "Work"]
    assert eng._crew_cohort_witness["agents_split"] == 0
    # A mode that isn't shift_split stores the directive but splits
    # nothing.
    eng2 = _engine(agents=[_crew(1, work_zone=WORK,
                                 schedule=["Work", "Work"])])
    _set_cohorts(eng2, {"mode": "other"})
    assert eng2.agents[0].schedule == ["Work", "Work"]
    assert eng2._crew_cohort_witness["applied_epoch"] is None


# ── witnesses + crew_window emission ───────────────────────────────────


def test_witnesses_zero_state_before_any_directive():
    eng = _engine()
    assert eng.crew_berthing_witness() == {
        "mode": None, "params": {}, "berths_held": 0,
        **_fresh_berth_witness(),
    }
    assert eng.crew_work_cohorts_witness() == {
        "mode": None, "params": {}, "schedules_held": 0,
        **_fresh_cohort_witness(),
    }


def test_witnesses_echo_mode_and_params():
    eng = _engine(agents=[_crew(1, work_zone=WORK)])
    _set_berth(eng, {"mode": "rezone", "berth_zones": ["CC_B"]})
    w = eng.crew_berthing_witness()
    assert w["mode"] == "rezone"
    assert w["params"] == {"berth_zones": ["CC_B"]}
    _set_cohorts(eng, {"mode": "shift_split", "pods": 3})
    w = eng.crew_work_cohorts_witness()
    assert w["mode"] == "shift_split"
    assert w["params"] == {"pods": 3}


def test_crew_window_block_echoes_berth_and_cohort_witnesses():
    eng = _engine(agents=[_crew(1, work_zone=WORK)])
    sim = SimpleNamespace(
        engine=eng,
        tx_core=SimpleNamespace(caregiver_telemetry={}, _cg_service={}),
    )
    ledger = QuarantineAttributionLedger()
    block = _crew_window_block(sim, ledger)
    assert block["crew_berthing"]["mode"] is None
    assert block["crew_berthing"]["pools_redealt"] == 0
    assert block["crew_work_cohorts"]["mode"] is None
    _set_berth(eng, {"mode": "cohort"})
    _set_cohorts(eng, {"mode": "shift_split", "pods": 2})
    block = _crew_window_block(sim, ledger)
    assert block["crew_berthing"]["mode"] == "cohort"
    assert block["crew_berthing"]["applied_epoch"] == 0
    assert block["crew_work_cohorts"]["mode"] == "shift_split"


def test_crew_window_block_none_when_engine_lacks_witnesses():
    sim = SimpleNamespace(
        engine=SimpleNamespace(),
        tx_core=SimpleNamespace(caregiver_telemetry={}, _cg_service={}),
    )
    block = _crew_window_block(sim, QuarantineAttributionLedger())
    assert block["crew_berthing"] is None
    assert block["crew_work_cohorts"] is None
