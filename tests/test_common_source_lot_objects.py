"""Admissibility gates for FOOD-COMMON-SOURCE-02 leg 1.

``lot_mode: "object"`` — the shipped default — replaces v1's per-window
iid event draws with persistent provisioned-lot contamination OBJECTS: a
voyage-level count draw (``lot_object_probability`` + a geometric
``extra_lot_probability`` tail), one realized contamination state per
object shared by every pan it emits, and a pan count that EMERGES from
lot extent, cohort demand and window cadence — never drawn. These tests
pin the frozen spec's leg-1 invariants; v1 semantics under
``"independent"`` are pinned in test_common_source_events.py.
"""

from __future__ import annotations

import pytest

from engines.transmission_core import (
    ContactTracingMatrix,
    TransmissionCore,
)
from tests.test_common_source_events import (
    PATHOGEN,
    ZONE,
    _core,
    _diner,
    _handler,
    _profile,
)


def _object_cfg(**overrides: object) -> dict:
    """Armed object-mode cfg with the voyage gated on."""
    cs: dict[str, object] = {
        "mode": "on",
        "lot_mode": "object",
        "lot_object_probability": 1.0,
        "extra_lot_probability": 0.0,
        "handler_event_probability": 0.0,
        "diner_event_probability": 0.0,
    }
    cs.update(overrides)
    return cs


def _step_objects(
    core: TransmissionCore,
    agents: list,
    zone: str = ZONE,
    epochs: int = 30,
) -> tuple[list[dict], list[dict], list[dict], dict[int, float]]:
    """Run the pathway epoch by epoch; close the voyage on the last
    matrix so surviving objects record ``end_reason: voyage_end``."""
    core._agents_by_id = {a.agent_id: a for a in agents}
    events: list[dict] = []
    exposures: list[dict] = []
    objects: list[dict] = []
    doses: dict[int, float] = {}
    matrix = ContactTracingMatrix(epoch=0)
    for epoch in range(epochs):
        matrix = ContactTracingMatrix(epoch=epoch)
        doses_epoch: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        core._pathway_common_source(
            epoch, {zone: agents}, doses_epoch, matrix, pw,
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        events.extend(matrix.common_source_events)
        exposures.extend(matrix.common_source_exposures)
        objects.extend(matrix.common_source_objects)
    core._cs_close_voyage(epochs - 1, matrix)
    objects.extend(matrix.common_source_objects)
    return events, exposures, objects, doses


# ── Gate 1: mode: off / unarmed never provision an object ─────────────

def test_mode_off_provisions_no_objects() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(cfg_cs=_object_cfg(**{"mode": "off"}))
    events, exposures, objects, doses = _step_objects(core, agents)
    assert events == []
    assert exposures == []
    assert objects == []
    assert doses == {}
    assert core._cs_rng is None
    assert all(v == 0 for v in core.common_source_telemetry.values())


def test_an_unarmed_pathogen_provisions_no_objects_in_either_mode() -> None:
    for mode in ("object", "independent"):
        core = _core(
            cfg_cs=_object_cfg(**{"lot_mode": mode}),
            profile=_profile(armed=False),
        )
        events, _, objects, _ = _step_objects(
            core, [_diner(i) for i in range(1, 40)],
        )
        assert events == []
        assert objects == []
        assert core._cs_rng is None


def test_mode_off_leaves_the_shared_stream_bit_identical() -> None:
    core_on = _core(cfg_cs=_object_cfg())
    core_off = _core(cfg_cs=_object_cfg(**{"mode": "off"}))
    _step_objects(core_on, [_diner(i) for i in range(1, 40)])
    _step_objects(core_off, [_diner(i) for i in range(1, 40)])
    assert core_on.rng.random() == pytest.approx(core_off.rng.random())


# ── Gate 2: the voyage count comes from the count knobs ───────────────

def test_forced_zero_object_probability_provisions_nothing() -> None:
    core = _core(cfg_cs=_object_cfg(**{"lot_object_probability": 0.0}))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    assert not [
        e for e in events if e["source_kind"] == "provisioned_lot"
    ]
    assert objects == []
    assert core.common_source_telemetry["objects_provisioned_lot"] == 0


def test_forced_one_object_probability_gives_exactly_one_object() -> None:
    core = _core(cfg_cs=_object_cfg())
    _step_objects(core, [_diner(i) for i in range(1, 40)])
    assert len(core._cs_objects[PATHOGEN]) == 1
    assert core.common_source_telemetry["objects_provisioned_lot"] == 1


def test_forced_extra_tail_provisions_more_than_one_object() -> None:
    # extra_lot_probability = 1 → every extra Bernoulli lands until the
    # degenerate-config cap (zones x item lines) stops the chain — the
    # tail exists and terminates.
    core = _core(cfg_cs=_object_cfg(**{"extra_lot_probability": 1.0}))
    _step_objects(core, [_diner(i) for i in range(1, 40)])
    objects = core._cs_objects[PATHOGEN]
    assert len(objects) > 1
    assert len(objects) <= 7  # 1 Dining zone x 7 item lines


def test_the_count_knob_does_not_shape_the_pan_stream() -> None:
    # The object's extent/demand, not the voyage count, decides pans:
    # a 30-serving lot facing 59-strong demand stops at its extent in
    # the first window; the count knob only ever says how many objects.
    core = _core(cfg_cs=_object_cfg(
        **{"item_take_share": 1.0, "lot_servings": 30.0},
    ))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)], epochs=72,
    )
    assert len(core._cs_objects[PATHOGEN]) == 1
    obj = objects[0]
    assert obj["servings_served"] == obj["lot_servings"] == 30
    assert obj["end_reason"] == "exhausted"


# ── Gate 3: the object witness records what the spec requires ─────────

def test_object_rows_carry_the_frozen_schema() -> None:
    core = _core(cfg_cs=_object_cfg(**{"extra_lot_probability": 1.0}))
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    assert objects
    for row in objects:
        assert row["object_id"].startswith(f"cso-{PATHOGEN}-")
        assert row["pathogen_id"] == PATHOGEN
        assert row["source_kind"] == "provisioned_lot"
        assert row["source_agent_id"] is None
        assert row["zone"] == ZONE
        assert row["item_label"] in {
            "shellfish", "salad_leaf", "fresh_produce", "deli",
            "bakery", "dairy", "garnish",
        }
        assert row["end_reason"] in {
            "exhausted", "perished", "source_excluded",
            "shedding_ended", "voyage_end",
        }
        assert row["strain_id"] == row["strain_id"]  # present
        assert row["servings_served"] <= row["lot_servings"]


# ── Gate 4: pan count emerges — never drawn ───────────────────────────

def test_pan_count_emerges_from_extent_demand_and_cadence() -> None:
    # Cohort demand 59 > pan_servings 10 → the object fills several pans
    # per window: the count comes out of the arithmetic, not a draw.
    core = _core(cfg_cs=_object_cfg(**{
        "item_take_share": 1.0,
        "lot_servings": 600.0,
        "pan_servings": 10,
    }))
    events, _, _, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)],
    )
    lot_pans = [
        e for e in events if e["source_kind"] == "provisioned_lot"
    ]
    assert lot_pans
    by_window: dict[tuple, list] = {}
    for e in lot_pans:
        by_window.setdefault((e["meal"], e["start_epoch"]), []).append(e)
    assert any(len(pans) > 1 for pans in by_window.values())
    assert core.common_source_telemetry["multi_pan_windows"] >= 1
    assert (
        core.common_source_telemetry["pans_emitted"] == len(lot_pans)
    )
    for pans in by_window.values():
        assert len(pans) == -(-sum(
            p["servings_taken"] for p in pans
        ) // 10)


# ── Gate 5: one realized draw per object shared across its pans ───────

def test_all_pans_of_an_object_share_its_one_contamination_state() -> None:
    core = _core(cfg_cs=_object_cfg(**{
        "extra_lot_probability": 1.0,
        "item_take_share": 1.0,
        "lot_servings": 600.0,
        "pan_servings": 10,
    }))
    events, _, _, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)],
    )
    lot_pans = [
        e for e in events if e["source_kind"] == "provisioned_lot"
    ]
    assert len({e["object_id"] for e in lot_pans}) > 1
    titres: dict[str, set] = {}
    for e in lot_pans:
        titres.setdefault(e["object_id"], set()).add(
            e["lot_titre_gec_per_g"],
        )
        assert e["pan_serial"] is not None
    # Same object → one titre across every pan; different objects →
    # independent realizations.
    assert all(len(t) == 1 for t in titres.values())
    assert len({next(iter(t)) for t in titres.values()}) > 1


# ── Gate 6: lifecycle — exhaustion, perishability, voyage end ─────────

def test_an_empty_demand_window_leaves_the_lot_intact() -> None:
    # take_share 0 → demand is zero every window: the object stays
    # alive, emits nothing, and outlives empty service until it
    # perishes or the voyage ends.
    core = _core(cfg_cs=_object_cfg(**{"item_take_share": 0.0}))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    obj = objects[0]
    assert obj["pans_emitted"] == 0
    assert obj["servings_served"] == 0
    assert not [
        e for e in events if e["source_kind"] == "provisioned_lot"
    ]
    # It lived: it covered every Lunch window its shelf life allowed.
    assert obj["windows_covered"] > 0
    assert obj["end_reason"] in {"perished", "voyage_end"}


def test_a_lot_perishes_after_its_shelf_life() -> None:
    # Start day forced to day 0, shelf 1: the lot serves days 0-1 and
    # perishes when day 2's service begins (day > start + shelf).
    core = _core(cfg_cs=_object_cfg(**{
        "item_take_share": 0.0,
        "lot_shelf_life_days": 1,
        "embarkation_lot_window_days": 1,
    }))
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)], epochs=72,
    )
    obj = objects[0]
    assert obj["end_reason"] == "perished"
    assert obj["exhausted_epoch"] is not None
    assert core.common_source_telemetry["objects_perished"] == 1


def test_a_surviving_lot_closes_at_voyage_end() -> None:
    # Shelf life 4 days > the 48-epoch run's two days of service: the
    # lot is still live when the voyage stops.
    core = _core(cfg_cs=_object_cfg(**{
        "item_take_share": 0.0,
        "lot_shelf_life_days": 4,
        "embarkation_lot_window_days": 1,
    }))
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)], epochs=48,
    )
    obj = objects[0]
    assert obj["end_reason"] == "voyage_end"
    assert obj["exhausted_epoch"] is None
    assert obj["seeded_epoch"] == 0
    assert obj["windows_covered"] > 0


def test_an_exhausted_lot_records_its_close_epoch() -> None:
    core = _core(cfg_cs=_object_cfg(**{
        "item_take_share": 1.0,
        "lot_servings": 30.0,
    }))
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)],
    )
    obj = objects[0]
    assert obj["end_reason"] == "exhausted"
    assert obj["exhausted_epoch"] is not None
    assert core.common_source_telemetry["objects_exhausted"] == 1


# ── Gate 7: mass conservation at object scope ─────────────────────────

def test_credited_dose_never_exceeds_the_lot_mass() -> None:
    core = _core(cfg_cs=_object_cfg(**{
        "item_take_share": 1.0,
        "lot_servings": 600.0,
        "pan_servings": 10,
    }))
    events, exposures, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)], epochs=72,
    )
    assert events and objects
    for event in events:
        credited = sum(
            e["dose"] for e in exposures
            if e["event_id"] == event["event_id"]
        )
        # Rounded witness fields vs float accumulation — compare at
        # rounding tolerance, not machine epsilon.
        assert credited <= event["pan_mass"] + 1e-3
    for obj in objects:
        # The whole object can't serve more than it provisioned.
        assert obj["dose_credited"] <= (
            obj["lot_titre_gec_per_g"] * 250.0 * obj["lot_servings"]
            + 1e-6
        )


# ── Gate 8: cohort integrity ──────────────────────────────────────────

def test_one_serving_per_agent_per_pan_but_pans_may_re_dose() -> None:
    core = _core(cfg_cs=_object_cfg(**{
        "extra_lot_probability": 1.0,
        "item_take_share": 1.0,
        "lot_servings": 600.0,
        "pan_servings": 10,
    }))
    events, exposures, _, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)],
    )
    lot_events = {
        e["event_id"]: e for e in events
        if e["source_kind"] == "provisioned_lot"
    }
    assert lot_events
    for event in lot_events.values():
        # A taker appears once on each pan's roll.
        assert len(event["taker_ids"]) == len(set(event["taker_ids"]))
    event_objects = {
        eid: e["object_id"] for eid, e in lot_events.items()
    }
    for row in exposures:
        if row["event_id"] in event_objects:
            assert row["object_id"] == event_objects[row["event_id"]]


def test_quarantined_and_non_dining_agents_never_take_a_serving() -> None:
    agents = [_diner(i) for i in range(1, 60)]
    quarantined = _diner(100)
    ashore = _diner(101)
    ashore.ashore = True
    agents.extend([quarantined, ashore])
    core = _core(cfg_cs=_object_cfg(**{
        "item_take_share": 1.0, "lot_servings": 600.0,
    }))
    core._quarantined_ids = {100}
    events, _, _, _ = _step_objects(core, agents)
    assert events
    for event in events:
        assert 100 not in event["taker_ids"]
        assert 101 not in event["taker_ids"]


# ── Gate 9: posture only enters the seeding draws ─────────────────────

def test_posture_is_bit_identical_across_the_object_path() -> None:
    # With lot_posture_coupling off (the shipped default), posture only
    # multiplies handler/diner rates — those are zero here, so the whole
    # object path is invariant under the posture value.
    def run(posture: float):
        core = _core(
            cfg_cs=_object_cfg(),
            seed=31,
            food_safety_posture=posture,
        )
        return _step_objects(
            core, [_diner(i) for i in range(1, 60)], epochs=72,
        )[:3]

    flat = run(1.0)
    low = run(0.1)
    high = run(5.0)
    # The recorded posture is a witness field and rightly varies; every
    # other draw and record is invariant across the object path.
    def scrub(rows):
        return [
            {k: v for k, v in r.items()
             if k != "food_safety_posture"}
            for r in rows
        ]
    assert scrub(flat[0]) == scrub(low[0]) == scrub(high[0])
    assert flat[1:] == low[1:] == high[1:]
    assert flat[0][0]["food_safety_posture"] == pytest.approx(1.0)
    assert low[0][0]["food_safety_posture"] == pytest.approx(0.1)


def test_posture_coupling_scales_the_object_seed_draw_only() -> None:
    # With the documented knob armed, posture multiplies the
    # lot_object_probability draw — posture 0 gates the voyage closed.
    core = _core(cfg_cs=_object_cfg(**{
        "lot_posture_coupling": True,
    }), food_safety_posture=0.0)
    _step_objects(core, [_diner(i) for i in range(1, 40)])
    assert core._cs_objects.get(PATHOGEN, []) == []
    assert core.common_source_telemetry["objects_provisioned_lot"] == 0


# ── Gate 10: determinism ──────────────────────────────────────────────

def test_the_same_seed_reproduces_the_same_objects_and_pans() -> None:
    def run():
        core = _core(cfg_cs=_object_cfg(**{
            "extra_lot_probability": 0.5,
        }), seed=23)
        return _step_objects(
            core, [_diner(i) for i in range(1, 60)], epochs=72,
        )[:3]

    assert run() == run()


# ── Gate 11: the labelled baseline still spells v1 ────────────────────

def test_independent_mode_emits_the_v1_witness_shape() -> None:
    core = _core(cfg_cs={
        "mode": "on",
        "lot_mode": "independent",
        "lot_event_probability": 1.0,
        "handler_event_probability": 0.0,
        "diner_event_probability": 0.0,
    })
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)],
    )
    lots = [e for e in events if e["source_kind"] == "provisioned_lot"]
    # v1 semantics: at most one event per voyage, no object attachment.
    assert len(lots) == 1
    assert lots[0]["object_id"] is None
    assert lots[0]["pan_serial"] is None
    assert objects == []
    assert core.common_source_telemetry["objects_provisioned_lot"] == 0


def test_handler_and_diner_arms_still_fire_under_object_mode() -> None:
    # Leg 2 is untouched: the v1 arms keep their per-window Bernoulli
    # semantics alongside lot objects — and "first fired wins" still
    # applies between them, so each arm is exercised on its own run.
    for kind, cfg in (
        ("ill_handler", {"handler_event_probability": 1.0}),
        ("ill_diner", {"diner_event_probability": 1.0}),
    ):
        agents = [_handler(1)] + [_diner(i, infected=(i == 3))
                                  for i in range(2, 60)]
        core = _core(cfg_cs=_object_cfg(**cfg))
        events, _, objects, _ = _step_objects(
            core, agents, epochs=72,
        )
        kinds = {e["source_kind"] for e in events}
        assert "provisioned_lot" in kinds
        assert kind in kinds
        assert objects
