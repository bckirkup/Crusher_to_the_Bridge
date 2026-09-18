"""Invariants for the localized emesis footprint (EMESIS-FOOTPRINT-01).

Part 1 makes the touchable share of an emesis bolus the high-touch areal
fraction of the room it lands in; Part 2 keeps that mass inside the bolus
footprint instead of the zone-wide surface pool. These are invariants and
graded response checks, not goldens -- no value here is re-derived from a
target metric.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.strain_dose_ledger import ReservoirComposition
from engines.transmission_core import (
    EMESIS_DEPOSITION_AREA_M2,
    SURFACE_RESERVOIR,
    ContactTracingMatrix,
    EmesisPatch,
    TransmissionCore,
)

PATHOGEN = "norwalk_gi"
ZONE = "Theater"


def _profile() -> dict:
    return {
        "symptom_onset_day": 0.0,
        "recovery_day": 5,
        "clinical_presentation": {
            "phases": [
                {
                    "name": "acute",
                    "dpi_min": 0,
                    "dpi_max": 2,
                    "features": ["vomiting"],
                }
            ],
        },
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "dose_response": {"model": "exponential", "k": 0.01},
    }


def _core(
    *,
    zone: str = ZONE,
    zone_type: str = "Public",
    zone_volumes: dict[str, float] | None = None,
    zone_floor_areas: dict[str, float] | None = None,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=zone_volumes or {zone: 5000.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={zone: zone_type},
        zone_floor_areas=zone_floor_areas or {},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([zone])
    return core


def _emitter(zone: str = ZONE) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=1,
        role="passenger",
        immune=False,
        home_zone=zone,
        dining_zone=zone,
        work_zone=zone,
        free_zone=zone,
        schedule=["Free"] * 24,
    )
    agent.current_location = zone
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    return agent


def _susceptible(agent_id: int, zone: str = ZONE) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=zone,
        dining_zone=zone,
        work_zone=zone,
        free_zone=zone,
        schedule=["Free"] * 24,
    )
    agent.current_location = zone
    return agent


def _emit_one(core: TransmissionCore, zone: str = ZONE) -> dict:
    agent = _emitter(zone)
    agent.clock = core.clock
    core._deposit_emesis(agent, PATHOGEN, zone, 0, _profile())
    records = agent.emesis_deposition_records_by_pathogen[PATHOGEN]
    return records[0]


# ── Part 1: touchable share is an areal fraction of the floor ────────


def test_touchable_fraction_strictly_decreasing_in_floor_area() -> None:
    """Fixed high-touch inventory over larger floors -> smaller share."""
    fractions = []
    for volume in (280.0, 2800.0, 28000.0):  # 100, 1000, 10000 m2 at 2.8 m
        core = _core(zone_volumes={ZONE: volume})
        record = _emit_one(core)
        fractions.append(record["touchable_fraction"])
    assert fractions[0] > fractions[1] > fractions[2]
    # Live knob: the span is orders of magnitude, not noise.
    assert fractions[0] / fractions[2] > 10.0


def test_touchable_fraction_matches_legacy_when_floor_below_footprint() -> None:
    """A room smaller than the bolus footprint keeps the old value."""
    tiny = _core(
        zone="Closet",
        zone_type="Public",
        zone_floor_areas={"Closet": 1.0},
    )
    record = _emit_one(tiny, zone="Closet")
    high_touch = tiny._fomite_surface_area("Closet")
    assert record["touchable_fraction"] == pytest.approx(
        min(1.0, high_touch / EMESIS_DEPOSITION_AREA_M2),
    )


def test_stateroom_share_exceeds_theatre_share() -> None:
    """The sign that was inverted: a small room, a larger share."""
    stateroom = _core(
        zone="Stateroom", zone_type="Cabin_Corridor",
        zone_volumes={"Stateroom": 43.0},
    )
    theatre = _core(
        zone="Theatre", zone_type="Public",
        zone_volumes={"Theatre": 5000.0},
    )
    assert (
        _emit_one(stateroom, zone="Stateroom")["touchable_fraction"]
        > _emit_one(theatre, zone="Theatre")["touchable_fraction"]
    )


def test_floor_area_helper_prefers_declared_then_volume_then_footprint() -> None:
    core = _core(zone_floor_areas={ZONE: 2.7}, zone_volumes={ZONE: 5000.0})
    assert core._zone_floor_area_m2(ZONE) == pytest.approx(2.7)
    core = _core(zone_volumes={ZONE: 280.0})
    assert core._zone_floor_area_m2(ZONE) == pytest.approx(100.0)
    core = _core(zone_volumes={ZONE: 0.0})
    assert core._zone_floor_area_m2(ZONE) == pytest.approx(
        EMESIS_DEPOSITION_AREA_M2,
    )


# ── Part 2: patch mass conservation and bounds ───────────────────────


def test_episode_partition_and_patch_mass_conserve() -> None:
    core = _core()
    record = _emit_one(core)
    assert (
        record["pool_gain"] + record["non_touchable"] + record["aerosol_load"]
    ) == pytest.approx(record["episode_load"], rel=1e-12)
    patches = core.emesis_patch_pools_by_pathogen[PATHOGEN][ZONE]
    assert len(patches) == 1
    # Patch mass ever created equals the episode's touchable share and
    # never exceeds it.
    assert 0.0 < patches[0].mass <= record["pool_gain"]
    assert patches[0].mass == pytest.approx(record["pool_gain"])
    # None of it joined the zone-wide pool.
    assert core.surface_pools_by_pathogen[PATHOGEN].get(ZONE, 0.0) == 0.0


def test_patch_mass_visible_to_surface_mass_observer() -> None:
    core = _core()
    _emit_one(core)
    patch = core.emesis_patch_pools_by_pathogen[PATHOGEN][ZONE][0]
    assert core.zone_surface_mass(ZONE, PATHOGEN) >= patch.mass


# ── Part 2: localization of the exposed set ──────────────────────────


def _run_patch_pickup(
    core: TransmissionCore,
    patch: EmesisPatch,
    n_susceptible: int,
    zone: str = ZONE,
) -> list[KorkinAgent]:
    occupants = [_susceptible(1000 + i, zone) for i in range(n_susceptible)]
    core.emesis_patch_pools_by_pathogen.setdefault(PATHOGEN, {})[zone] = [
        patch
    ]
    matrix = ContactTracingMatrix(epoch=0)
    core._emesis_patch_pickup(
        0, {zone: occupants}, PATHOGEN, {}, matrix, None, None,
    )
    return occupants


def test_exposed_set_is_strict_subset_scaled_by_occupant_share() -> None:
    core = _core()
    n = 200
    occupants = _run_patch_pickup(
        core,
        EmesisPatch(
            mass=1.0e8,
            high_touch_area_m2=0.03,
            occupant_share=0.1,
            epoch=0,
        ),
        n,
    )
    gained = [a for a in occupants if a.hand_load_by_pathogen.get(PATHOGEN)]
    # Expected ~n * occupant_share, loosely bounded.
    assert len(gained) < n
    assert abs(len(gained) - n * 0.1) < n * 0.1


def test_patch_delivery_never_exceeds_patch_mass() -> None:
    core = _core()
    patch = EmesisPatch(
        mass=50.0, high_touch_area_m2=0.03, occupant_share=1.0, epoch=0,
    )
    _run_patch_pickup(core, patch, 50)
    leftover = core.emesis_patch_pools_by_pathogen[PATHOGEN][ZONE]
    remaining = leftover[0].mass if leftover else 0.0
    assert 0.0 <= remaining <= 50.0


def test_patch_pickup_bounds_dose_and_hand_load() -> None:
    core = _core()
    occupants = _run_patch_pickup(
        core,
        EmesisPatch(
            mass=1.0e6,
            high_touch_area_m2=0.03,
            occupant_share=0.5,
            epoch=0,
        ),
        30,
    )
    for agent in occupants:
        load = agent.hand_load_by_pathogen.get(PATHOGEN, 0.0)
        assert np.isfinite(load)
        assert load >= 0.0


def test_patch_pickup_scales_composition_by_unit_total() -> None:
    """A nearly-consumed patch must not zero the unit's composition bucket.

    The bucket keyed by (surface, pathogen, unit) holds the zone pool's
    deposits as well as the patch's, so consumption scales it by the
    delivered share of the unit's total surface mass, not of the patch.
    """
    core = _core()
    pool_mass, patch_mass = 400.0, 5.0
    core.surface_pools_by_pathogen[PATHOGEN][ZONE] = pool_mass
    key = ReservoirComposition.key(SURFACE_RESERVOIR, PATHOGEN, ZONE)
    core._reservoir.deposit(key, ("strainA", 1), pool_mass + patch_mass)
    before = sum(core._reservoir.contributors(key).values())
    patch = EmesisPatch(
        mass=patch_mass,
        high_touch_area_m2=0.03,
        occupant_share=1.0,
        epoch=0,
    )
    occupants = _run_patch_pickup(core, patch, 50)
    assert occupants  # sanity: the patch actually delivered
    delivered = patch_mass - patch.mass
    assert delivered > 0.0
    total = pool_mass + patch_mass
    after = sum(core._reservoir.contributors(key).values())
    assert after == pytest.approx(before * (total - delivered) / total)
    # and the zone pool's share of the bucket is preserved, not wiped out
    assert after > 0.9 * before


def test_zero_emesis_draws_no_rng() -> None:
    """A unit with no patches must be bit-identical in the RNG stream."""
    core = _core()
    occupants = [_susceptible(2000 + i) for i in range(5)]
    state_before = core.rng.bit_generator.state.copy()
    core._emesis_patch_pickup(
        0, {ZONE: occupants}, PATHOGEN, {},
        ContactTracingMatrix(epoch=0), None, None,
    )
    assert core.rng.bit_generator.state == state_before


def test_patch_decays_with_zone_survival() -> None:
    core = _core()
    _emit_one(core)
    patch = core.emesis_patch_pools_by_pathogen[PATHOGEN][ZONE][0]
    before = patch.mass
    survival = core._surface_survival(_profile())
    core._update_surface_pools({ZONE: []})
    assert patch.mass == pytest.approx(before * survival)
