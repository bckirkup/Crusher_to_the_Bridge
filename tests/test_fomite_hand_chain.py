"""Behavioral guards for the measured fomite hand-transfer chain."""

from __future__ import annotations

import numpy as np
import pytest

import engines.transmission_core as transmission_core
from engines.infection_dynamics_bridge import (
    HAND_LOAD_LOG10_GEC,
    HAND_LOAD_REFERENCE_PEAK_LOG10,
    IllnessStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    ContactTracingMatrix,
    TransmissionCore,
)

PATHOGEN = "test_pathogen"
ZONE = "Public_Lounge"


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
    }
    profile.update(overrides)
    return profile


def _agent(
    agent_id: int = 1,
    *,
    schedule: list[str] | None = None,
    infected: bool = False,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=schedule or ["Free"] * 24,
    )
    agent.current_location = ZONE
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    zone: str = ZONE,
    zone_type: str = "Free",
    profile: dict | None = None,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={zone: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={zone: zone_type},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([zone])
    return core


def test_preferred_and_legacy_release_keys_are_bitwise_equivalent() -> None:
    agent = _agent(infected=True)
    old = _profile(dose_adjustment=4.0)
    new = _profile(environmental_faecal_release_log10_g_per_epoch=4.0)
    assert agent.get_pathogen_shedding(PATHOGEN, old) == (
        agent.get_pathogen_shedding(PATHOGEN, new)
    )


def test_pickup_is_bounded_and_monotonic_in_surface_pool() -> None:
    requests = []
    for pool in (1.0, 10.0, 100.0):
        core = _core()
        requests.append(core._fomite_pickup_request(
            _agent(), ZONE, pool, 0,
        ))
    assert requests == sorted(requests)
    assert all(0.0 <= value <= pool for value, pool in zip(
        requests, (1.0, 10.0, 100.0),
    ))


def test_pickup_is_monotonic_in_shared_surface_touch_frequency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = []
    for frequency in (2.0, 6.0, 12.0):
        monkeypatch.setattr(
            transmission_core,
            "SURFACE_CONTACTS_PER_HOUR",
            {**transmission_core.SURFACE_CONTACTS_PER_HOUR, "public": frequency},
        )
        core = _core(seed=13)
        values.append(core._fomite_pickup_request(_agent(), ZONE, 10.0, 0))
    assert values == sorted(values)


def test_zero_hand_load_delivers_zero_mouth_dose() -> None:
    core = _core()
    target = _agent()
    assert core._hand_to_mouth_dose(target, 0, 0.0) == pytest.approx(
        0.0, abs=0.0,
    )


def test_eating_context_increases_mouth_contact_dose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _core()
    target = _agent(schedule=["Meal:Lunch"] * 24)
    monkeypatch.setattr(
        core, "_fomite_mouth_contacts",
        lambda _target, _epoch: 7.7,
    )
    eating = core._hand_to_mouth_dose(target, 0, 100.0)
    target.schedule = ["Free"] * 24
    monkeypatch.setattr(
        core, "_fomite_mouth_contacts",
        lambda _target, _epoch: 2.9,
    )
    non_eating = core._hand_to_mouth_dose(target, 0, 100.0)
    assert eating > non_eating


def test_mouth_dose_is_monotonic_in_mouth_contact_frequency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = []
    target = _agent()
    for frequency in (1.0, 3.0, 8.0):
        core = _core(seed=17)
        monkeypatch.setattr(
            core,
            "_fomite_mouth_contacts",
            lambda _target, _epoch, n=frequency: n,
        )
        values.append(core._hand_to_mouth_dose(target, 0, 100.0))
    assert values == sorted(values)


def test_hand_relaxation_uses_sim_clock_hourly_rate() -> None:
    hourly = _core(seed=23)
    half_hour = _core(
        seed=23,
    )
    hourly.clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
    half_hour.clock = SimClock(epoch_duration_hours=0.5, mode=HOURS)
    first = _agent(infected=True)
    second = _agent(infected=True)
    first.hand_load_by_pathogen[PATHOGEN] = 1.0
    second.hand_load_by_pathogen[PATHOGEN] = 1.0
    first.hand_inactivation_rate_by_pathogen[PATHOGEN] = 1.0
    second.hand_inactivation_rate_by_pathogen[PATHOGEN] = 1.0
    hourly._replenish_hand(first, PATHOGEN, _profile())
    half_hour._replenish_hand(second, PATHOGEN, _profile())
    half_hour._replenish_hand(second, PATHOGEN, _profile())
    assert first.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        second.hand_load_by_pathogen[PATHOGEN],
    )


def test_replenishment_reaches_the_liu_hand_target() -> None:
    core = _core(seed=29)
    agent = _agent(infected=True)
    profile = _profile(hand_inactivation_rate_per_hour=1.155)
    target = agent.get_pathogen_hand_target(PATHOGEN, profile)

    for _ in range(24):
        core._replenish_hand(agent, PATHOGEN, profile)

    assert agent.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        target,
        rel=0.02,
    )


def test_hand_target_is_the_liu_load_at_the_reference_peak() -> None:
    """The hand route's absolute level is Liu's measurement, not a free scale.

    Change detector: the shipped curve peaks at the reference peak, so the
    target must land on 10^3.86 GEC per hand exactly. If either constant
    moves, the hand route stops reproducing the only study that has measured
    a hand load in infected hosts.
    """
    agent = _agent(infected=True)
    profile = _profile(
        shedding_curve_log10=[HAND_LOAD_REFERENCE_PEAK_LOG10] * 12,
    )
    assert agent.get_pathogen_hand_target(PATHOGEN, profile) == pytest.approx(
        10.0 ** HAND_LOAD_LOG10_GEC,
    )


@pytest.mark.parametrize("peak", [7.0, 8.0, 9.1, 10.0])
def test_a_peak_shift_moves_the_faecal_and_hand_routes_by_one_factor(
    peak: float,
) -> None:
    """A curve-peak change is one exposure scale across both enteric routes.

    Both the environmental emission and the hand target read the same curve
    index, so replacing the GI.1 peak with a GII peak multiplies each by the
    same 10^(peak - reference). It cannot be adopted for the faecal route
    alone, and it relocates Liu's measured hand load by that factor.
    """
    agent = _agent(infected=True)
    reference = _profile(
        shedding_curve_log10=[HAND_LOAD_REFERENCE_PEAK_LOG10] * 12,
        dose_adjustment=4.0,
    )
    shifted = _profile(
        shedding_curve_log10=[peak] * 12,
        dose_adjustment=4.0,
    )
    factor = 10.0 ** (peak - HAND_LOAD_REFERENCE_PEAK_LOG10)

    assert agent.get_pathogen_shedding(PATHOGEN, shifted) == pytest.approx(
        agent.get_pathogen_shedding(PATHOGEN, reference) * factor,
    )
    assert agent.get_pathogen_hand_target(PATHOGEN, shifted) == pytest.approx(
        agent.get_pathogen_hand_target(PATHOGEN, reference) * factor,
    )


def test_replenishment_is_invariant_to_one_hour_or_half_hour_epochs() -> None:
    profile = _profile(hand_inactivation_rate_per_hour=1.155)
    hourly = _core(seed=31)
    half_hour = _core(seed=31)
    hourly.clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
    half_hour.clock = SimClock(epoch_duration_hours=0.5, mode=HOURS)
    first = _agent(infected=True)
    second = _agent(infected=True)

    for _ in range(24):
        hourly._replenish_hand(first, PATHOGEN, profile)
    for _ in range(48):
        half_hour._replenish_hand(second, PATHOGEN, profile)

    assert first.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        second.hand_load_by_pathogen[PATHOGEN],
        rel=1e-9,
    )
    target = first.get_pathogen_hand_target(PATHOGEN, profile)
    assert first.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        target,
        rel=0.02,
    )


def test_empty_fomite_step_is_a_no_op() -> None:
    core = _core()
    before = dict(core.surface_pools)
    core._pathway_fomite(
        0,
        {ZONE: []},
        {},
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    assert core.surface_pools == before


def test_surface_pool_hand_pool_and_dose_do_not_create_mass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _core()
    target = _agent()
    core.surface_pools[ZONE] = 100.0
    core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 100.0
    monkeypatch.setattr(
        core, "_fomite_pickup_request",
        lambda _target, _zone, _pool, _epoch: 10.0,
    )
    before = 100.0
    doses: dict[int, float] = {}
    core._pathway_fomite(
        0,
        {ZONE: [target]},
        doses,
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    hand = target.hand_load_by_pathogen.get(PATHOGEN, 0.0)
    surface = core.surface_pools_by_pathogen[PATHOGEN][ZONE]
    dose = doses[target.agent_id]
    assert surface + hand + dose <= before + 1e-9
    assert surface <= before
    assert hand >= 0.0
    assert dose >= 0.0


def test_fomite_delivery_is_per_capita_invariant_to_occupancy() -> None:
    results = []
    for count in (1, 2, 4):
        core = _core(seed=11)
        targets = [_agent(i) for i in range(count)]
        core.surface_pools[ZONE] = 100.0
        core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 100.0
        core._fomite_pickup_request = (
            lambda _target, _zone, _pool, _epoch: 1.0
        )
        core._hand_to_mouth_dose = (
            lambda _target, _epoch, hand_load: hand_load * 0.01
        )
        doses: dict[int, float] = {}
        core._pathway_fomite(
            0,
            {ZONE: targets},
            doses,
            ContactTracingMatrix(epoch=0),
            [],
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        results.append(sum(doses.values()) / count)
    assert results[0] == pytest.approx(results[1])
    assert results[1] == pytest.approx(results[2])


# ── transmission.high_touch_area_scale (NORO-HIGH-TOUCH-AREA-01) ──────────
#
# The sweep axis multiplies ``_fomite_surface_area``'s single choke point, so
# the pickup denominator, the emesis ``touchable_fraction``, the EmesisPatch
# area and the swab-density denominator all move together. Absent or ``1.0``
# must be bit-identical to the shipped declaration -- the multiply is exact
# and the parser draws nothing.

_SCALE_ZONES = {
    "Cabin_A": "Cabin_Corridor",
    "Diner_A": "Dining",
    "Lounge_A": "Free",
    "Galley_M": "Free",
    "CrewMess_A": "Free",
    "Head_A": "Sanitary",
}


def _core_with_scale(
    scale: float | None,
    *,
    seed: int = 7,
    by_class: dict[str, float] | None = None,
) -> TransmissionCore:
    """A core spanning every zone class, with the sweep axis declared."""
    cfg: dict[str, object] = {}
    tx: dict[str, object] = {}
    if scale is not None:
        tx["high_touch_area_scale"] = scale
    if by_class is not None:
        tx["high_touch_area_scale_by_zone_class"] = by_class
    if tx:
        cfg = {"transmission": tx}
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(_SCALE_ZONES, 50.0),
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types=dict(_SCALE_ZONES),
        zone_floor_areas={
            "Head_A": 2 * transmission_core.SANITARY_FLOOR_AREA_M2_PER_WC,
        },
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg=cfg,
    )
    core.initialize_zones(list(_SCALE_ZONES))
    return core


def test_scale_default_and_one_are_bit_identical() -> None:
    absent = _core_with_scale(None)
    declared = _core_with_scale(1.0)
    for zone in _SCALE_ZONES:
        assert absent._fomite_surface_area(zone) == pytest.approx(
            declared._fomite_surface_area(zone), rel=0.0, abs=0.0,
        )


@pytest.mark.parametrize("scale", [0.25, 0.5, 1.0, 2.0, 4.0])
def test_surface_area_is_exactly_proportional(scale: float) -> None:
    base = _core_with_scale(1.0)
    swept = _core_with_scale(scale)
    for zone in _SCALE_ZONES:
        assert swept._fomite_surface_area(zone) == pytest.approx(
            base._fomite_surface_area(zone) * scale,
            rel=1e-15,
        )


def test_sanitary_branch_scales_through_the_per_wc_path() -> None:
    # Head_A declares 2 WC floor areas, so the per-WC constant branch
    # applies: area = 0.5 * 2 * scale.
    swept = _core_with_scale(3.0)
    assert swept._fomite_surface_area("Head_A") == pytest.approx(3.0)


def test_swab_denominator_scales_with_the_area() -> None:
    base = _core_with_scale(1.0)
    swept = _core_with_scale(2.0)
    for zone in _SCALE_ZONES:
        assert swept.zone_high_touch_area_cm2(zone) == pytest.approx(
            base.zone_high_touch_area_cm2(zone) * 2.0,
            rel=1e-15,
        )


@pytest.mark.parametrize("scale", [0.25, 0.5, 2.0, 4.0])
def test_pickup_request_is_monotone_in_inverse_scale(scale: float) -> None:
    # Same seed, and the scale parser draws nothing, so both cores make the
    # same draws: the uncapped request is exactly 1/scale of the declared
    # arm's request. A tiny pool keeps ``min(surface_mass, ...)`` from
    # binding.
    surface_mass = 1e-30
    base = _core_with_scale(1.0, seed=13)
    swept = _core_with_scale(scale, seed=13)
    target = _agent()
    base_request = base._fomite_pickup_request_for_area(
        target, "Lounge_A", surface_mass,
        base._fomite_surface_area("Lounge_A"), 0,
    )
    swept_request = swept._fomite_pickup_request_for_area(
        target, "Lounge_A", surface_mass,
        swept._fomite_surface_area("Lounge_A"), 0,
    )
    assert base_request < surface_mass
    assert swept_request < surface_mass
    assert swept_request == pytest.approx(base_request / scale, rel=1e-12)


@pytest.mark.parametrize(
    "scale", [0.0, -1.0, float("nan"), float("inf"), 0.001, 1000.0],
)
def test_scale_refusal_band_rejects_bad_arms(scale: float) -> None:
    with pytest.raises(ValueError, match="high_touch_area_scale"):
        _core_with_scale(scale)


def test_class_map_absent_and_empty_are_bit_identical() -> None:
    absent = _core_with_scale(None)
    empty = _core_with_scale(None, by_class={})
    for zone in _SCALE_ZONES:
        assert absent._fomite_surface_area(zone) == pytest.approx(
            empty._fomite_surface_area(zone), rel=0.0, abs=0.0,
        )


def test_class_map_scales_only_its_own_class() -> None:
    base = _core_with_scale(None)
    swept = _core_with_scale(
        None, by_class={"cabin": 0.5, "dining": 3.5},
    )
    for zone in _SCALE_ZONES:
        zone_class = base._fomite_zone_class(zone)
        expected = base._fomite_surface_area(zone)
        if zone_class in ("cabin", "dining"):
            expected *= 0.5 if zone_class == "cabin" else 3.5
        assert swept._fomite_surface_area(zone) == pytest.approx(
            expected, rel=0.0, abs=0.0,
        )


def test_class_map_composes_with_the_global_scalar() -> None:
    base = _core_with_scale(1.0)
    swept = _core_with_scale(2.0, by_class={"public": 0.5})
    for zone in _SCALE_ZONES:
        expected = base._fomite_surface_area(zone) * 2.0
        if base._fomite_zone_class(zone) == "public":
            expected *= 0.5
        assert swept._fomite_surface_area(zone) == pytest.approx(
            expected, rel=0.0, abs=0.0,
        )


def test_class_map_scales_the_sanitary_per_wc_branch() -> None:
    # Head_A declares 2 WC floor areas: 0.5 * 2 * class scale.
    swept = _core_with_scale(None, by_class={"sanitary": 3.0})
    assert swept._fomite_surface_area("Head_A") == pytest.approx(3.0)


def test_swab_denominator_reflects_the_composed_scale() -> None:
    base = _core_with_scale(1.0)
    swept = _core_with_scale(2.0, by_class={"galley": 0.25})
    for zone in _SCALE_ZONES:
        expected = base.zone_high_touch_area_cm2(zone) * 2.0
        if base._fomite_zone_class(zone) == "galley":
            expected *= 0.25
        assert swept.zone_high_touch_area_cm2(zone) == pytest.approx(
            expected, rel=1e-15,
        )


def test_class_map_rejects_unknown_zone_class() -> None:
    with pytest.raises(ValueError, match="unknown zone class"):
        _core_with_scale(None, by_class={"not_a_class": 1.0})


def test_class_map_rejects_non_mapping() -> None:
    with pytest.raises(ValueError, match="must be a mapping"):
        _core_with_scale(None, by_class=4)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [0.0, -1.0, float("nan"), float("inf"), 0.001, 1000.0, "half"],
)
def test_class_map_refusal_band_rejects_bad_arms(value: object) -> None:
    with pytest.raises(ValueError, match="high_touch_area_scale"):
        _core_with_scale(
            None,
            by_class={"cabin": value},  # type: ignore[dict-item]
        )
