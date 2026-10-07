"""CREW-MESS-01: the crew meal-service directive — graded behaviour tests.

The mechanism is a declared placement policy: ``set_crew_meal_directive``
stores/activates the order-window modifier, ``_crew_meal_redirect``
reroutes crew diner placements out of the mess zones, ``staggered``
rewrites and restores Meal-token positions, and the witness echoes the
last directive through ``crew_window.crew_meal_service``. No hull runs —
the engine methods are driven on a stub carrying exactly the fields the
directive reads/writes.
"""

from __future__ import annotations

from functools import partial
from types import SimpleNamespace

from crusher_labs.protocol_engine import apply_crew_meal_service
from engines.infection_dynamics_bridge import KorkinShipEngine
from picard_framework.covid_boarding_screen import (
    QuarantineAttributionLedger,
    _crew_window_block,
)

MESS = "Crew_Mess_Fwd"


def _engine(*, agents=(), catalog=None):
    """A stub carrying exactly the crew-meal fields the directive owns,
    with the real KorkinShipEngine methods bound onto it."""
    eng = SimpleNamespace(
        _crew_dining_catalog=list(catalog or []),
        _crew_mess_zone_names=frozenset(
            str(e["name"]) for e in (catalog or [{"name": MESS}])
        ),
        _crew_mess_zone_caps={},
        _crew_meal_zone_counts={},
        _crew_meal_count_epoch=-1,
        _crew_meal_diverted=0,
        _crew_meal_active_epochs=0,
        _crew_meal_staggered_rewrites=0,
        _crew_meal_last_directive=None,
        _crew_meal_directive=None,
        _saved_crew_schedules={},
        epoch=0,
        agents=list(agents),
    )
    for name in (
        "set_crew_meal_directive", "_crew_meal_redirect",
        "_tick_crew_meal_epoch", "_crew_meal_stagger_apply",
        "_crew_meal_stagger_restore", "crew_meal_service_witness",
    ):
        setattr(eng, name, partial(getattr(KorkinShipEngine, name), eng))
    return eng


def _diner(agent_id, *, role="crew", work_zone="", home="Cabin_X",
           schedule=None, meal_seating=0):
    return SimpleNamespace(
        agent_id=agent_id, role=role, work_zone=work_zone,
        home_zone=home, schedule=list(schedule or []),
        meal_seating=meal_seating,
    )


def _set(eng, block):
    eng.set_crew_meal_directive(block)


def _redirect(eng, agent, location):
    return eng._crew_meal_redirect(agent, location)


def _witness(eng):
    return eng.crew_meal_service_witness()


# ── apply_crew_meal_service (protocol_engine shim) ──────────────────────


def test_apply_none_engine_is_noop():
    apply_crew_meal_service(None, {"crew_meal_service": {"mode": "boxed"}})


def test_apply_engine_without_setter_is_noop():
    apply_crew_meal_service(SimpleNamespace(), {"crew_meal_service": {}})


def test_apply_passes_dict_block_and_clears_on_falling_edge():
    seen = []
    eng = SimpleNamespace(set_crew_meal_directive=seen.append)
    apply_crew_meal_service(eng, {"crew_meal_service": {"mode": "boxed"}})
    apply_crew_meal_service(eng, {"crew_meal_service": "not-a-dict"})
    apply_crew_meal_service(eng, {})
    apply_crew_meal_service(eng, None)
    assert seen == [{"mode": "boxed"}, None, None, None]


# ── set_crew_meal_directive edges and counters ─────────────────────────


def test_boxed_directive_stores_and_echoes_after_release():
    eng = _engine()
    _set(eng, {"mode": "boxed"})
    _set(eng, {"mode": "boxed"})
    _set(eng, None)
    assert eng._crew_meal_directive is None
    assert eng._crew_meal_active_epochs == 2
    w = _witness(eng)
    assert w["mode"] == "boxed"
    assert w["params"] == {}
    assert w["active_epochs"] == 2
    assert w["diner_redirects"] == 0
    assert w["staggered_rewrites"] == 0


def test_capacity_directive_computes_zone_caps():
    catalog = [
        {"name": MESS, "max_occupancy": 100},
        {"name": "Crew_Mess_Aft", "max_occupancy": 60},
    ]
    eng = _engine(catalog=catalog)
    _set(eng, {"mode": "capacity", "occupancy_fraction": 0.10})
    assert eng._crew_mess_zone_caps == {MESS: 10, "Crew_Mess_Aft": 6}
    w = _witness(eng)
    assert w["mode"] == "capacity"
    assert w["params"] == {"occupancy_fraction": 0.10}


# ── _crew_meal_redirect ────────────────────────────────────────────────


def test_redirect_passthrough_without_directive_or_for_passengers():
    eng = _engine()
    assert _redirect(eng, _diner(1), MESS) == MESS
    _set(eng, {"mode": "boxed"})
    assert _redirect(eng, _diner(2, role="passenger"), MESS) == MESS
    assert _redirect(eng, _diner(3), "Corridor_05") == "Corridor_05"
    # Mess-posted staff keep their posting (the kitchen still cooks).
    posted = _diner(4, work_zone=MESS)
    assert _redirect(eng, posted, MESS) == MESS
    assert eng._crew_meal_diverted == 0


def test_boxed_redirect_diverts_diner_to_home_zone():
    eng = _engine()
    _set(eng, {"mode": "boxed"})
    diner = _diner(7, home="Cabin_Q")
    assert _redirect(eng, diner, MESS) == "Cabin_Q"
    assert _redirect(eng, diner, MESS) == "Cabin_Q"
    assert eng._crew_meal_diverted == 2


def test_capacity_redirect_admits_to_cap_then_diverts_and_resets():
    eng = _engine(catalog=[{"name": MESS, "max_occupancy": 20}])
    _set(eng, {"mode": "capacity", "occupancy_fraction": 0.10})
    diners = [_diner(i) for i in range(4)]
    admitted = [_redirect(eng, d, MESS) for d in diners]
    assert admitted[:2] == [MESS, MESS]  # cap = 2
    assert admitted[2:] == ["Cabin_X", "Cabin_X"]
    assert eng._crew_meal_diverted == 2
    # A new epoch resets the per-(zone, epoch) counters.
    eng.epoch = 1
    assert _redirect(eng, diners[0], MESS) == MESS
    eng.epoch = 2
    assert _redirect(eng, diners[0], "Other") == "Other"


def test_staggered_directive_needs_no_redirect():
    eng = _engine()
    _set(eng, {"mode": "staggered", "seatings": 4})
    assert _redirect(eng, _diner(1), MESS) == MESS


# ── staggered seatings rewrite + verbatim restore ───────────────────────


def test_stagger_swaps_meal_tokens_and_restores_verbatim():
    mover = _diner(6, schedule=["Wake", "Meal", "Work", "Watch", "Sleep"])
    still = _diner(8, schedule=["Wake", "Meal", "Work", "Watch", "Sleep"])
    eng = _engine(agents=[mover, still])
    _set(eng, {"mode": "staggered", "seatings": 4})
    # agent 6 → seat 2: Meal moves from index 1 to index 3.
    assert mover.schedule == ["Wake", "Watch", "Work", "Meal", "Sleep"]
    assert mover.meal_seating == 2
    # agent 8 → seat 0 keeps the dealt position and is not saved.
    assert still.schedule[1] == "Meal"
    assert eng._crew_meal_staggered_rewrites == 1
    assert _witness(eng)["schedules_held"] == 1
    # Falling edge restores the dealt schedule verbatim.
    _set(eng, None)
    assert mover.schedule == ["Wake", "Meal", "Work", "Watch", "Sleep"]
    assert mover.meal_seating == 0
    assert _witness(eng)["staggered_rewrites"] == 1


def test_stagger_is_noop_for_seatings_below_two():
    mover = _diner(6, schedule=["Wake", "Meal", "Work"])
    eng = _engine(agents=[mover])
    _set(eng, {"mode": "staggered", "seatings": 1})
    assert mover.schedule == ["Wake", "Meal", "Work"]
    assert eng._crew_meal_staggered_rewrites == 0


def test_stagger_skips_non_crew_and_meal_blocked_targets():
    pax = _diner(6, role="passenger", schedule=["Wake", "Meal", "Port"])
    blocked = _diner(7, schedule=["Wake", "Meal", "Meal", "Watch"])
    eng = _engine(agents=[pax, blocked])
    _set(eng, {"mode": "staggered", "seatings": 4})
    # seat 3 for agent 7 lands on another Meal token — no swap, still saved.
    assert blocked.meal_seating == 3
    assert blocked.schedule[1] == "Meal"
    assert eng._crew_meal_staggered_rewrites == 1


# ── witness + crew_window emission ──────────────────────────────────────


def test_witness_zero_state_before_any_directive():
    w = _witness(_engine())
    assert w == {
        "mode": None, "params": {}, "active_epochs": 0,
        "diner_redirects": 0, "staggered_rewrites": 0,
        "schedules_held": 0,
    }


def test_crew_window_block_echoes_meal_service_witness():
    eng = _engine()
    sim = SimpleNamespace(
        engine=eng,
        tx_core=SimpleNamespace(caregiver_telemetry={}, _cg_service={}),
    )
    ledger = QuarantineAttributionLedger()
    # Zero state echoes a mode-None witness, not a missing key.
    block = _crew_window_block(sim, ledger)["crew_meal_service"]
    assert block["mode"] is None
    assert block["active_epochs"] == 0
    _set(eng, {"mode": "boxed"})
    _set(eng, None)
    block = _crew_window_block(sim, ledger)["crew_meal_service"]
    assert block["mode"] == "boxed"
    assert block["active_epochs"] == 1
