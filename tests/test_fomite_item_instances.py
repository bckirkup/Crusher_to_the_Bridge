"""Behavioral guards for the per-item-instance fomite arm (NORO-TOUCH-PATCH-01).

The TOUCH-PATCH arm (``docs/norovirus/fomite_touch_patch_spec.md``)
disaggregates each item-class sub-pool once more into the discrete items a
hand's touches actually sample: deposits land on iid-drawn instances, and
each pickup touch draws one reachable instance and requests at that
instance's own areal density. The arm enumerates the ``shared`` unit
inventory only; ``pooled`` stays the bit-identical default. Sensitivity-
first per ci-test-design: graded responses on placement, consume and
coincidence, invariants on conservation and roll-up, config refusals --
no hash goldens.
"""

from __future__ import annotations

import math
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import engines.fomite_surfaces as fomite_surfaces  # noqa: E402
from engines.transmission_core import ContactTracingMatrix  # noqa: E402
from tests.test_fomite_per_surface import (  # noqa: E402
    EPOCHS,
    PATHOGEN,
    _agent,
    _core,
    _drive,
    _population,
    _sanitary_core,
    _sanitary_population,
)

ITEM_INSTANCES = {
    "fomite_representation": "item_instances",
    "fomite_item_reading": "shared",
}


class _StubRng:
    """Uniform draws from a queued fraction sequence."""

    def __init__(self, *values: float) -> None:
        self._values = deque(values)

    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        return low + self._values.popleft() * (high - low)


def _instance_state(
    **tx,
) -> fomite_surfaces.ItemInstanceFomiteState:
    cfg = fomite_surfaces.parse_per_surface_config({**ITEM_INSTANCES, **tx})
    return fomite_surfaces.ItemInstanceFomiteState(cfg)


def _cabin_inventory(
    state, unit_key: str = "cabin_u1",
) -> "fomite_surfaces.UnitInventory":
    return state.register_unit(
        unit_key, "cabin", pooled_area_m2=1.0,
        water_closets=1, zone_coverage=0.5,
    )


# ── config gate ──────────────────────────────────────────────────────


def test_item_instances_requires_shared_reading() -> None:
    for reading in ("hardware", "broad"):
        with pytest.raises(ValueError, match="fomite_item_reading"):
            fomite_surfaces.parse_per_surface_config(
                {**ITEM_INSTANCES, "fomite_item_reading": reading},
            )
    cfg = fomite_surfaces.parse_per_surface_config(ITEM_INSTANCES)
    assert cfg.representation == "item_instances"

    core = _core(ITEM_INSTANCES)
    assert isinstance(
        core._per_surface, fomite_surfaces.ItemInstanceFomiteState,
    )
    assert core.fomite_representation == "item_instances"


# ── slot enumeration and sampling ────────────────────────────────────


def test_slots_enumerate_fractional_counts() -> None:
    slots = fomite_surfaces.ItemInstanceFomiteState.slots
    assert slots(0.0) == []
    assert slots(1.0) == [(0, 1.0)]
    assert slots(2.0) == [(0, 1.0), (1, 1.0)]
    assert slots(0.5) == [(0, 0.5)]
    assert slots(2.5) == [(0, 1.0), (1, 1.0), (2, 0.5)]
    for count in (0.3, 1.7, 4.0, 20.0):
        assert sum(e for _, e in slots(count)) == pytest.approx(count)


def test_sample_touch_draws_class_by_share_then_uniform_index() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state)
    first = next(iter(inv.touch_share))
    last = next(reversed(inv.touch_share))

    key = state.sample_touch(inv, "u", PATHOGEN, _StubRng(0.0, 0.0))
    assert key == ("u", PATHOGEN, first, 0)

    key = state.sample_touch(inv, "u", PATHOGEN, _StubRng(0.9999999, 0.9999999))
    assert key[2] == last
    assert key[3] == math.ceil(inv.counts[last]) - 1


def test_instance_area_scales_with_slot_extent() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state)
    assert state.instance_area(inv, "door_lever", 2) == pytest.approx(
        inv.area_each_m2["door_lever"],
    )
    # grab_rail_m declares 0.5 of a unit, so its single slot is a half item.
    assert state.instance_area(inv, "grab_rail_m", 0) == pytest.approx(
        0.5 * inv.area_each_m2["grab_rail_m"],
    )


# ── deposit placement ────────────────────────────────────────────────


def test_fallback_deposit_spreads_sharewise_over_instances() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state)
    state.deposit("u", PATHOGEN, 1e6, inv)

    total = sum(state.mass.values())
    assert total == pytest.approx(1e6, rel=1e-12)
    for item_class, share in inv.touch_share.items():
        class_mass = sum(
            mass
            for (_, _, cls, _), mass in state.mass.items()
            if cls == item_class
        )
        assert class_mass == pytest.approx(share * 1e6, rel=1e-12)
    # cleanable mirrors the share-weighted coverage.
    assert sum(state.cleanable.values()) == pytest.approx(
        1e6 * inv.mean_coverage, rel=1e-12,
    )


def test_deposit_instances_lands_all_mass_on_drawn_items() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state)
    rng = np.random.default_rng(5)
    state.deposit_instances("u", PATHOGEN, 1e6, inv, contacts=7.0, rng=rng)

    assert sum(state.mass.values()) == pytest.approx(1e6, rel=1e-12)
    for _, _, item_class, index in state.mass:
        assert item_class in inv.counts
        assert 0 <= index < math.ceil(inv.counts[item_class])
    # No touch stream draws beyond the deposits: cleanable stays within
    # the per-draw coverage envelope.
    cleanable_total = sum(state.cleanable.values())
    assert 0.0 < cleanable_total <= 1e6

    # contacts rounding to zero still lands a positive deposit once.
    state2 = _instance_state()
    inv2 = _cabin_inventory(state2)
    state2.deposit_instances(
        "u", PATHOGEN, 3e5, inv2, contacts=0.0,
        rng=np.random.default_rng(5),
    )
    assert sum(state2.mass.values()) == pytest.approx(3e5, rel=1e-12)


def test_pickup_requests_stays_unsupported_on_the_state() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state)
    with pytest.raises(NotImplementedError):
        state.pickup_requests(inv, "u", PATHOGEN, 1.0, 0.5, 0.01, 0.5)


# ── consume and witnesses ────────────────────────────────────────────


def test_consume_instances_removes_per_instance_and_floors() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state)
    state.deposit_instances(
        "u", PATHOGEN, 1e6, inv, contacts=1.0,
        rng=np.random.default_rng(3),
    )
    (key,) = state.mass
    mass_before = state.mass[key]
    cleanable_before = state.cleanable[key]

    state.consume_instances("u", PATHOGEN, {key: 0.4 * mass_before})
    assert state.mass[key] == pytest.approx(0.6 * mass_before, rel=1e-12)
    assert state.cleanable[key] == pytest.approx(
        0.6 * cleanable_before, rel=1e-12,
    )

    state.consume_instances("u", PATHOGEN, {key: mass_before})
    assert state.mass[key] == pytest.approx(0.0, abs=1e-9)
    assert state.cleanable[key] == pytest.approx(0.0, abs=1e-9)
    assert all(v >= 0.0 for v in state.mass.values())


def test_record_served_counts_distinct_coincident_recipients() -> None:
    state = _instance_state()
    key = ("u", PATHOGEN, "door_lever", 0)
    pair = ("u", PATHOGEN)

    state.record_served(key, 1)
    assert state.coincidence.get(pair, 0) == 0
    state.record_served(key, 2)
    assert state.coincidence[pair] == 1
    # A repeat delivery to an already-credited host is not a new
    # coincidence.
    state.record_served(key, 2)
    assert state.coincidence[pair] == 1
    state.record_served(key, 3)
    assert state.coincidence[pair] == 2
    assert state.served[key] == {1, 2, 3}


def test_class_rollups_over_instances() -> None:
    state = _instance_state()
    inv = _cabin_inventory(state, unit_key="u")
    state.deposit("u", PATHOGEN, 1e6, inv)

    masses = state.class_masses("u", PATHOGEN)
    assert sum(masses.values()) == pytest.approx(1e6, rel=1e-12)
    for item_class, share in inv.touch_share.items():
        assert masses[item_class] == pytest.approx(share * 1e6, rel=1e-12)

    # Shipped basis makes every class's areal density the unit mean.
    density = state.class_density_per_m2("u", PATHOGEN)
    assert density
    for value in density.values():
        assert value == pytest.approx(1e6 / inv.total_area_m2, rel=1e-9)
    assert state.class_density_per_m2("unregistered", PATHOGEN) == {}


# ── engine wiring ────────────────────────────────────────────────────


def test_instance_drive_reconciles_pool_and_fires_requests() -> None:
    core = _core(ITEM_INSTANCES, seed=11)
    history = _drive(core, _population())
    state = core._per_surface

    for zone, pool in core.surface_pools_by_pathogen[PATHOGEN].items():
        if pool > 0.0:
            assert state.total(zone, PATHOGEN) == pytest.approx(
                pool, rel=1e-9,
            )
    # Instance keys partition the unit pools (4-tuples, not class keys).
    assert all(len(key) == 4 for key in state.mass)

    touches = sum(s["touches"] for s in state.touch_stats.values())
    hits = sum(s["hits"] for s in state.touch_stats.values())
    assert touches > 0
    assert hits > 0
    assert any(
        h["doses"] for h in history
    ), "no fomite dose delivered across the drive"


def test_instance_delivery_never_exceeds_instance_mass() -> None:
    core = _core(ITEM_INSTANCES, seed=11)
    state = core._per_surface
    pooled = core._fomite_surface_area_pooled("Lounge_A")
    inv = core._per_surface_inventory("Lounge_A", pooled)
    state.deposit_instances(
        "Lounge_A", PATHOGEN, 1e6, inv, contacts=1.0,
        rng=np.random.default_rng(3),
    )
    (key,) = [k for k in state.mass if k[0] == "Lounge_A"]

    targets = [_agent(900, "Lounge_A"), _agent(901, "Lounge_A")]
    doses: dict[int, float] = {}
    delivered = core._deliver_fomite_requests_by_instance(
        [(target, {key: 2e6}) for target in targets],
        "Lounge_A",
        surface_mass=1e6,
        epoch=0,
        prev_occupant_ids=set(),
        prev_shedders=[],
        agent_doses=doses,
        matrix=ContactTracingMatrix(epoch=0),
        agent_pathway_doses=None,
        pathogen_id=PATHOGEN,
        surface_attribution=None,
    )
    # Two targets each asked for 2x the instance mass; the instance
    # empties exactly and the recipients are coincidence-witnessed.
    assert delivered[key] == pytest.approx(1e6, rel=1e-12)
    # Hands hold delivered-minus-ingested mass; together they cannot
    # exceed the instance's supply.
    hands = [
        t.hand_load_by_pathogen[PATHOGEN] for t in targets
    ]
    assert sum(hands) <= 1e6 * (1.0 + 1e-9)
    assert all(h > 0.0 for h in hands)
    assert state.served[key] == {900, 901}
    assert state.coincidence.get(("Lounge_A", PATHOGEN)) == 1

    state.consume_instances("Lounge_A", PATHOGEN, delivered)
    assert state.mass[key] == pytest.approx(0.0, abs=1e-9)


def test_confined_target_out_of_scope_requests_nothing() -> None:
    core = _core(ITEM_INSTANCES, seed=11)
    target = _agent(900, "Cabin_A")
    core._quarantined_ids.add(target.agent_id)
    core.cabin_confined_fomite = "off"
    assert core._fomite_pickup_requests_by_instance(
        target, "Lounge_A", 0, PATHOGEN,
    ) is None


def test_zone_item_class_state_rolls_up_instances() -> None:
    core = _core(ITEM_INSTANCES, seed=11)
    core._deposit_surface_mass(PATHOGEN, "Lounge_A", 1e6)
    state = core.zone_item_class_state("Lounge_A", PATHOGEN)
    assert state
    assert sum(s["mass"] for s in state.values()) == pytest.approx(
        1e6, rel=1e-9,
    )
    # The fallback (no placement) spread is share-weighted like the
    # by-class arm: uniform density across classes under shipped basis.
    densities = [s["density_per_m2"] for s in state.values()]
    for density in densities:
        assert density == pytest.approx(densities[0], rel=1e-9)


def test_sanitary_venue_pickup_runs_per_instance() -> None:
    core = _sanitary_core(ITEM_INSTANCES, seed=11)
    occupants = _sanitary_population()
    for venue in ("HD_5T_M", "HD_5T_F"):
        core._deposit_surface_mass(PATHOGEN, venue, 1e9)
    _drive(core, occupants)

    assert core.sanitary_telemetry["recipients"] > 0
    assert core.sanitary_telemetry["dose_delivered"] > 0.0
    state = core._per_surface
    for venue, pool in core.surface_pools_by_pathogen[PATHOGEN].items():
        if pool > 0.0:
            assert state.total(venue, PATHOGEN) == pytest.approx(
                pool, rel=1e-9,
            )
