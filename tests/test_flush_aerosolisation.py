"""Toilet-flush aerosolisation (FLUSH-AERO-01): graded sensitivity and
invariants for the default-off swept route.

Per ci-test-design: no golden dose values. Expectations are bit-identity
of the off arm (agent doses, not just totals), the refusal band on the
swept fraction, linearity of emission and delivered dose in the
fraction, the venue-kind dose formulas (dwell share and ventilation on a
head, whole-epoch emesis treatment in a cabin), and the telemetry
witness's internal consistency.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    DEFAULT_ROUTE_EFFICIENCY,
    FLUSH_STOOL_MASS_G,
    PATHWAY_EFFICIENCY_KEYS,
    SANITARY_CEILING_HEIGHT_M,
    SANITARY_EXHAUST_M3H_PER_WC,
    SANITARY_FLOOR_AREA_M2_PER_WC,
    ContactTracingMatrix,
    TransmissionCore,
    _parse_flush_aerosol_fraction,
    _parse_flush_cabin_emission,
)

PATHOGEN = "norwalk_gi"
HEAD = "HD_5T_M"
THEATER = "TheaterLng"
CABIN_ZONE = "PC_D5_P_F"
COMPARTMENT = f"{CABIN_ZONE}::cabin1"


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "symptom_onset_day": 0.0,
        "recovery_day": 5,
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "stool_events_per_day": {"baseline": 5.63, "diarrhoeal": 5.63},
        "dose_response": {"model": "exponential", "k": 0.01},
    }
    profile.update(overrides)
    return profile


def _core(
    fraction: float | None = None,
    *,
    cabin_emission: bool | None = None,
    mode: str = "dwell_weighted",
    seed: int = 11,
) -> TransmissionCore:
    tx: dict[str, object] = {"sanitary_visit_mode": mode}
    if fraction is not None:
        tx["flush_aerosol_fraction"] = fraction
    if cabin_emission is not None:
        tx["flush_cabin_emission"] = cabin_emission
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={HEAD: 30.0, THEATER: 4000.0, CABIN_ZONE: 800.0},
        zone_types={
            HEAD: "Sanitary",
            THEATER: "Free",
            CABIN_ZONE: "Cabin_Corridor",
        },
        zone_floor_areas={HEAD: 27.0},
        sanitary_zone_map={THEATER: {"male": HEAD}},
        pathogen_profiles={PATHOGEN: _profile()},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": tx},
    )
    return core


def _agent(aid: int, location: str, gender: str = "male") -> KorkinAgent:
    agent = KorkinAgent(
        aid, "passenger", False, CABIN_ZONE, "MainDining", THEATER,
        "Casino", ["Free"] * 24, gender=gender,
    )
    agent.current_location = location
    agent.cabin_mate_ids = frozenset()
    return agent


def _shedder(core: TransmissionCore, aid: int = 1,
             location: str = THEATER) -> KorkinAgent:
    """An infected agent shedding at its symptomatic-curve plateau."""
    agent = _agent(aid, location)
    agent.clock = core.clock
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.hand_load_by_pathogen[PATHOGEN] = 10.0
    return agent


def _force_stool_event(core: TransmissionCore, agent: KorkinAgent,
                       zone_name: str) -> None:
    core._stool_event_occurs = lambda rate: True
    core._replenish_hand(
        agent, PATHOGEN, core.pathogen_profiles[PATHOGEN],
        zone_name=zone_name,
    )


def _flush_dose_rows(matrix: ContactTracingMatrix) -> list[dict]:
    return list(matrix.flush_aerosol_exposures)


def _pathway(
    core: TransmissionCore,
    zone_occupants: dict[str, list[KorkinAgent]],
    epoch: int = 0,
) -> tuple[ContactTracingMatrix, dict[int, float]]:
    matrix = ContactTracingMatrix(epoch=epoch)
    agent_doses: dict[int, float] = {}
    core._pathway_flush_aerosol(
        zone_occupants, agent_doses, matrix, {}, PATHOGEN,
    )
    return matrix, agent_doses


# ── Parsing: the refusal band and the off state ──────────────────────


def test_fraction_parse_off_zero_and_absent() -> None:
    assert _parse_flush_aerosol_fraction({}) == 0.0
    assert _parse_flush_aerosol_fraction({"flush_aerosol_fraction": 0.0}) == 0.0
    assert _core().flush_aerosol_fraction == 0.0
    assert _core(0.0).flush_aerosol_fraction == 0.0


@pytest.mark.parametrize("bad", [1e-12, 1e-2, float("nan"), float("inf"), -1e-6])
def test_fraction_parse_refuses_out_of_band(bad: float) -> None:
    with pytest.raises(ValueError, match="flush_aerosol_fraction"):
        _parse_flush_aerosol_fraction({"flush_aerosol_fraction": bad})


@pytest.mark.parametrize("good", [1e-9, 1e-6, 1e-3])
def test_fraction_parse_accepts_the_span(good: float) -> None:
    assert _parse_flush_aerosol_fraction(
        {"flush_aerosol_fraction": good},
    ) == pytest.approx(good)


def test_cabin_emission_defaults_on_and_parses() -> None:
    assert _parse_flush_cabin_emission({}) is True
    assert _parse_flush_cabin_emission({"flush_cabin_emission": False}) is False
    assert _core().flush_cabin_emission is True
    assert _core(cabin_emission=False).flush_cabin_emission is False


# ── Route registration ──────────────────────────────────────────────


def test_route_key_is_registered_everywhere_routes_are_enumerated() -> None:
    assert DEFAULT_ROUTE_EFFICIENCY["flush_aerosol"] == 1.0
    assert PATHWAY_EFFICIENCY_KEYS["flush_aerosol"] == "flush_aerosol"
    from engines.non_pharmaceutical_interventions import NPI_ROUTE_KEYS
    assert "flush_aerosol" in NPI_ROUTE_KEYS


# ── Bit-identity of the off arm ─────────────────────────────────────


def test_off_arm_is_bit_identical_to_absent_key_on_agent_doses() -> None:
    """flush off is the same engine: identical per-agent route doses and
    identical rng tails under dwell_weighted (rng-neutrality of moving
    the venue resolution out of the visit-mode gate)."""

    def fingerprint(cfg_extra: dict | None) -> tuple[dict, dict, list[float]]:
        tx = {"sanitary_visit_mode": "dwell_weighted"}
        if cfg_extra:
            tx.update(cfg_extra)
        core = TransmissionCore(
            rng=np.random.default_rng(99),
            zone_volumes={HEAD: 30.0, THEATER: 4000.0, CABIN_ZONE: 800.0},
            zone_types={
                HEAD: "Sanitary",
                THEATER: "Free",
                CABIN_ZONE: "Cabin_Corridor",
            },
            zone_floor_areas={HEAD: 27.0},
            sanitary_zone_map={THEATER: {"male": HEAD}},
            pathogen_profiles={PATHOGEN: _profile()},
            clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
            cfg={"transmission": tx},
        )
        agents = [_shedder(core, 1), _agent(2, THEATER), _agent(3, THEATER)]
        route_doses = []
        for epoch in range(3):
            core.execute_transmission(
                epoch=epoch, agents=agents,
                zone_pathogen_mass={HEAD: 0.0, THEATER: 0.0},
            )
            route_doses.append(
                {
                    aid: dict(pw)
                    for aid, pw in core._last_pathogen_route_doses.get(
                        PATHOGEN, {},
                    ).items()
                },
            )
        hand = {
            a.agent_id: a.hand_load_by_pathogen.get(PATHOGEN, 0.0)
            for a in agents
        }
        tail = [float(core.rng.random()) for _ in range(5)]
        return route_doses, hand, tail

    baseline = fingerprint(None)
    explicit_off = fingerprint({"flush_aerosol_fraction": 0.0})
    assert baseline == explicit_off


# ── Emission ────────────────────────────────────────────────────────


def test_emission_scales_linearly_with_the_fraction() -> None:
    """f_aero enters the load multiplicatively and deterministically:
    same seed, same shedder, so emitted copies are in the fraction
    ratio, not merely ordered."""
    emitted = []
    for frac in (1e-9, 1e-6, 1e-3):
        core = _core(frac, seed=7)
        shedder = _shedder(core)
        _force_stool_event(core, shedder, THEATER)
        emitted.append(core.sanitary_telemetry["flush_aerosol_emitted"])
        assert core.sanitary_telemetry["flush_events"] == 1
    assert emitted[0] > 0.0
    assert emitted[1] == pytest.approx(emitted[0] * 1e3, rel=1e-9)
    assert emitted[2] == pytest.approx(emitted[0] * 1e6, rel=1e-9)


def test_emission_carries_the_stool_mass_and_titre() -> None:
    """Emitted load = 10^titre x multipliers x FLUSH_STOOL_MASS_G x f."""
    core = _core(1e-6, seed=7)
    shedder = _shedder(core)
    titre = shedder.get_pathogen_stool_titre_log10(
        PATHOGEN, core.pathogen_profiles[PATHOGEN],
    )
    _force_stool_event(core, shedder, THEATER)
    expected = (
        10.0 ** titre * FLUSH_STOOL_MASS_G * 1e-6
    )
    assert core.sanitary_telemetry[
        "flush_aerosol_emitted"
    ] == pytest.approx(expected, rel=1e-9)
    pending = core.drain_flush_aerosol(PATHOGEN)
    assert pending.get(HEAD, 0.0) == pytest.approx(expected, rel=1e-9)
    assert core.drain_flush_aerosol(PATHOGEN) == {}


def test_no_stool_event_no_emission_and_non_shedder_no_emission() -> None:
    core = _core(1e-3, seed=7)
    shedder = _shedder(core)
    core._stool_event_occurs = lambda rate: False
    core._replenish_hand(
        shedder, PATHOGEN, core.pathogen_profiles[PATHOGEN],
        zone_name=THEATER,
    )
    assert core.sanitary_telemetry["flush_events"] == 0
    # A susceptible agent's stool event emits nothing (no infection).
    susceptible = _agent(2, THEATER)
    susceptible.hand_load_by_pathogen[PATHOGEN] = 10.0
    _force_stool_event(core, susceptible, THEATER)
    assert core.sanitary_telemetry["flush_events"] == 0


def test_cabin_emission_flag_zeroes_only_cabin_venues() -> None:
    """Same seed, one event at home and one at the served head: the flag
    removes the cabin emission and leaves the sanitary one untouched."""
    emitted = {}
    for flag in (True, False):
        core = _core(1e-6, cabin_emission=flag, seed=7)
        # At home the venue is the cabin compartment itself.
        home = _shedder(core, aid=1, location=CABIN_ZONE)
        home.home_zone = CABIN_ZONE
        _force_stool_event(core, home, COMPARTMENT)
        away = _shedder(core, aid=2, location=THEATER)
        _force_stool_event(core, away, THEATER)
        emitted[flag] = dict(
            core._flush_aerosol_emitted_by_pathogen.get(PATHOGEN, {}),
        )
    assert set(emitted[False]) == {HEAD}
    assert set(emitted[True]) == {HEAD, COMPARTMENT}
    cabin_load = sum(m for _, m in emitted[True][COMPARTMENT])
    assert cabin_load > 0.0
    assert sum(m for _, m in emitted[False][HEAD]) == pytest.approx(
        sum(m for _, m in emitted[True][HEAD]), rel=1e-12,
    )


# ── Sanitary venue dose ─────────────────────────────────────────────


def _emitted_sanitary_core(
    seed: int = 11, n_visits: int = 1,
) -> tuple[TransmissionCore, KorkinAgent, KorkinAgent]:
    """Core with one emitted flush at HEAD and one susceptible visitor."""
    core = _core(1e-6, seed=seed)
    shedder = _shedder(core, aid=1)
    visitor = _agent(2, THEATER)
    load = 1e6
    core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
        HEAD: [(shedder, load)],
    }
    core._sanitary_epoch = 0
    core._sanitary_visits = {2: [HEAD] * n_visits}
    return core, shedder, visitor


def test_f_vent_at_code_ach_is_about_52_milli() -> None:
    core = _core(1e-6)
    ach = core._sanitary_exhaust_ach(HEAD)
    assert ach == pytest.approx(
        SANITARY_EXHAUST_M3H_PER_WC
        / (SANITARY_FLOOR_AREA_M2_PER_WC * SANITARY_CEILING_HEIGHT_M),
        rel=1e-9,
    )
    assert ach == pytest.approx(19.2, abs=0.1)
    x = ach * core.clock.hours_per_epoch
    f_vent = (1.0 - math.exp(-x)) / x
    assert f_vent == pytest.approx(0.052, abs=1e-3)


def test_sanitary_dose_scales_with_dwell_share_and_inverse_volume() -> None:
    """Two visits double the dwell share and double the dose; doubling
    the head volume halves the dose. Both axes are exact, not
    statistical."""
    doses = []
    for n_visits in (1, 2):
        core, _, visitor = _emitted_sanitary_core(n_visits=n_visits)
        matrix, agent_doses = _pathway(
            core, {THEATER: [visitor], HEAD: []},
        )
        doses.append(agent_doses[2])
    assert doses[0] > 0.0
    assert doses[1] == pytest.approx(2.0 * doses[0], rel=1e-9)

    dose_by_volume = []
    for volume in (30.0, 60.0):
        core, _, visitor = _emitted_sanitary_core()
        core.zone_volumes[HEAD] = volume
        matrix, agent_doses = _pathway(
            core, {THEATER: [visitor], HEAD: []},
        )
        dose_by_volume.append(agent_doses[2])
    assert dose_by_volume[1] == pytest.approx(
        dose_by_volume[0] / 2.0, rel=1e-9,
    )


def test_sanitary_flush_doses_only_visitors_of_that_head() -> None:
    core, shedder, visitor = _emitted_sanitary_core()
    bystander = _agent(3, THEATER)  # never visits HEAD this epoch
    matrix, agent_doses = _pathway(
        core, {THEATER: [visitor, bystander], HEAD: []},
    )
    assert agent_doses.get(2, 0.0) > 0.0
    assert agent_doses.get(3, 0.0) == 0.0
    rows = _flush_dose_rows(matrix)
    assert {r["target_id"] for r in rows} == {2}
    assert rows[0]["venue_kind"] == "sanitary"


def test_sanitary_dose_uses_the_visit_and_stool_venue_caches() -> None:
    """The shedder's own stool venue is a visitor entry too, so a second
    susceptible whose stool event resolved to the same head is dosed."""
    core, shedder, visitor = _emitted_sanitary_core()
    stool_visitor = _agent(4, THEATER)
    core._sanitary_stool_venues = {PATHOGEN: {4: HEAD}}
    matrix, agent_doses = _pathway(
        core, {THEATER: [visitor, stool_visitor], HEAD: []},
    )
    assert agent_doses.get(4, 0.0) == pytest.approx(
        agent_doses.get(2, 0.0), rel=1e-9,
    )


def test_no_visits_no_sanitary_dose() -> None:
    """A head flush with visits off emits into a room no one enters."""
    core = _core(1e-6, mode="none")
    shedder = _shedder(core, aid=1)
    core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
        HEAD: [(shedder, 1e6)],
    }
    visitor = _agent(2, THEATER)
    matrix, agent_doses = _pathway(core, {THEATER: [visitor]})
    assert agent_doses == {}
    assert _flush_dose_rows(matrix) == []


# ── Cabin venue dose (emesis treatment) ─────────────────────────────


def test_cabin_venue_doses_compartment_occupants_whole_epoch() -> None:
    core = _core(1e-6, seed=11)
    shedder = _shedder(core, aid=1, location=CABIN_ZONE)
    shedder.cabin_mate_ids = frozenset({2})
    mate = _agent(2, CABIN_ZONE)
    mate.cabin_mate_ids = frozenset({1})
    mass = 1e6
    core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
        COMPARTMENT: [(shedder, mass)],
    }
    matrix, agent_doses = _pathway(
        core, {CABIN_ZONE: [shedder, mate]},
    )
    assert agent_doses.get(2, 0.0) > 0.0
    row = _flush_dose_rows(matrix)[0]
    assert row["venue_kind"] == "cabin"
    # Emesis treatment: no f_vent, whole-epoch inhaled volume, the
    # compartment's air-unit volume. No berthing plan is registered here,
    # so the unit falls back to the declared block volume (AERO-CABIN-02).
    expected = (
        mass / 800.0 * core.inhaled_air_volume_m3_per_epoch
    )
    assert agent_doses[2] == pytest.approx(expected, rel=1e-6)
    # The shedder itself is not susceptible and takes no dose.
    assert agent_doses.get(1, 0.0) == pytest.approx(0.0)


def test_cabin_flush_dose_scales_linearly_with_fraction() -> None:
    doses = []
    for frac in (1e-9, 1e-6, 1e-3):
        core = _core(frac, seed=11)
        shedder = _shedder(core, aid=1, location=CABIN_ZONE)
        shedder.cabin_mate_ids = frozenset({2})
        mate = _agent(2, CABIN_ZONE)
        mate.cabin_mate_ids = frozenset({1})
        core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
            COMPARTMENT: [(shedder, 1e6 * frac / 1e-6)],
        }
        matrix, agent_doses = _pathway(
            core, {CABIN_ZONE: [shedder, mate]},
        )
        doses.append(agent_doses[2])
    assert doses[1] == pytest.approx(doses[0] * 1e3, rel=1e-9)
    assert doses[2] == pytest.approx(doses[0] * 1e6, rel=1e-9)


def test_cabin_dose_scales_with_berth_share_of_block() -> None:
    """A 4-berth stateroom's air share is twice a 2-berth's in the same
    block, so equal emitted mass doses its occupants at exactly half."""
    core = _core(1e-6, seed=11)
    shedder = _shedder(core, aid=9, location=CABIN_ZONE)
    two = [_agent(1, CABIN_ZONE), _agent(2, CABIN_ZONE)]
    four = [_agent(i, CABIN_ZONE) for i in (3, 4, 5, 6)]
    for agent in two:
        agent.cabin_mate_ids = frozenset({1, 2} - {agent.agent_id})
    for agent in four:
        agent.cabin_mate_ids = frozenset({3, 4, 5, 6} - {agent.agent_id})
    core.register_cabin_berths(two + four)
    mass = 1e6
    core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
        f"{CABIN_ZONE}::cabin1": [(shedder, mass)],
        f"{CABIN_ZONE}::cabin3": [(shedder, mass)],
    }
    matrix, agent_doses = _pathway(
        core, {CABIN_ZONE: two + four + [shedder]},
    )
    # V_2berth = 800 x 2/6, V_4berth = 800 x 4/6 -> dose2 = 2 x dose4.
    assert agent_doses[1] == pytest.approx(2.0 * agent_doses[3], rel=1e-9)
    # And it is the berth share, not the retired 100 m3 fallback.
    expected = (
        mass / (800.0 * 2 / 6) * core.inhaled_air_volume_m3_per_epoch
    )
    assert agent_doses[1] == pytest.approx(expected, rel=1e-9)


def test_cabin_dose_scales_inversely_with_block_volume() -> None:
    doses = []
    for volume in (800.0, 1600.0):
        core = _core(1e-6, seed=11)
        core.zone_volumes[CABIN_ZONE] = volume
        shedder = _shedder(core, aid=1, location=CABIN_ZONE)
        shedder.cabin_mate_ids = frozenset({2})
        mate = _agent(2, CABIN_ZONE)
        mate.cabin_mate_ids = frozenset({1})
        core.register_cabin_berths([shedder, mate])
        core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
            f"{CABIN_ZONE}::cabin1": [(shedder, 1e6)],
        }
        _, agent_doses = _pathway(core, {CABIN_ZONE: [shedder, mate]})
        doses.append(agent_doses[2])
    assert doses[0] == pytest.approx(2.0 * doses[1], rel=1e-9)


def test_unregistered_berthing_plan_falls_back_to_block_volume() -> None:
    """No registered berthing plan dilutes into the parent block, the
    pre-AERO-CABIN-01 treatment — not the retired 100 m3 number."""
    core = _core(1e-6, seed=11)
    shedder = _shedder(core, aid=1, location=CABIN_ZONE)
    shedder.cabin_mate_ids = frozenset({2})
    mate = _agent(2, CABIN_ZONE)
    mate.cabin_mate_ids = frozenset({1})
    core._flush_aerosol_emitted_by_pathogen[PATHOGEN] = {
        COMPARTMENT: [(shedder, 1e6)],
    }
    _, agent_doses = _pathway(core, {CABIN_ZONE: [shedder, mate]})
    expected = 1e6 / 800.0 * core.inhaled_air_volume_m3_per_epoch
    assert agent_doses[2] == pytest.approx(expected, rel=1e-9)


def test_sanitary_dose_ignores_the_berthing_plan() -> None:
    """The Sanitary branch does not read cabin berths: registering a plan
    leaves a head's flush dose bit-identical."""
    doses = []
    for register in (False, True):
        core = _core(1e-6, seed=7)
        shedder = _shedder(core)
        _force_stool_event(core, shedder, THEATER)
        visitor = _agent(2, THEATER)
        core._sanitary_epoch = 0
        core._sanitary_visits = {2: [HEAD]}
        if register:
            mate = _agent(3, CABIN_ZONE)
            mate.cabin_mate_ids = frozenset({2})
            visitor.cabin_mate_ids = frozenset({3})
            core.register_cabin_berths([visitor, mate])
        _, agent_doses = _pathway(
            core, {THEATER: [visitor], HEAD: []},
        )
        doses.append(agent_doses[2])
    assert doses[0] > 0.0
    assert doses[0] == pytest.approx(doses[1], rel=0.0)


def test_delivered_dose_scales_with_fraction_end_to_end() -> None:
    """Emission and pathway together: same seed, same shedder, same
    visitor, so the credited dose is in the fraction ratio."""
    doses = []
    for frac in (1e-9, 1e-6, 1e-3):
        core = _core(frac, seed=7)
        shedder = _shedder(core)
        _force_stool_event(core, shedder, THEATER)
        visitor = _agent(2, THEATER)
        core._sanitary_epoch = 0
        core._sanitary_visits = {2: [HEAD]}
        matrix, agent_doses = _pathway(
            core, {THEATER: [visitor], HEAD: []},
        )
        doses.append(agent_doses[2])
    assert doses[0] > 0.0
    assert doses[1] == pytest.approx(doses[0] * 1e3, rel=1e-9)
    assert doses[2] == pytest.approx(doses[0] * 1e6, rel=1e-9)


# ── Titre accessor ──────────────────────────────────────────────────


def test_stool_titre_is_not_offset_by_environmental_release() -> None:
    """The bowl deposit is the stool itself: changing the release mass
    must not move the titre the flush route reads."""
    core = _core(1e-6)
    shedder = _shedder(core)
    for release_log10 in (4.0, 9.0):
        profile = _profile(
            environmental_release_log10_per_day=release_log10,
        )
        assert shedder.get_pathogen_stool_titre_log10(
            PATHOGEN, profile,
        ) == pytest.approx(11.0)


def test_stool_titre_matches_the_curve_at_known_age() -> None:
    core = _core(1e-6)
    shedder = _shedder(core)
    curve = [9.0, 10.0, 11.0] + [8.0] * 9
    profile = _profile(shedding_curve_log10=curve)
    # Day-1 shedding age reads curve[1].
    shedder.infections[PATHOGEN]["time_infected"] = 24
    assert shedder.get_pathogen_stool_titre_log10(
        PATHOGEN, profile,
    ) == pytest.approx(10.0)


def test_stool_titre_none_for_a_non_shedder() -> None:
    core = _core(1e-6)
    susceptible = _agent(9, THEATER)
    susceptible.clock = core.clock
    assert susceptible.get_pathogen_stool_titre_log10(
        PATHOGEN, _profile(),
    ) is None
    # A recovered host no longer sheds either.
    shedder = _shedder(core, aid=5)
    shedder.infections[PATHOGEN]["status"] = InfectionStatus.RECOVERED
    assert shedder.get_pathogen_stool_titre_log10(
        PATHOGEN, _profile(),
    ) is None


# ── Telemetry witness ───────────────────────────────────────────────


FLUSH_KEYS = (
    "flush_events",
    "flush_aerosol_emitted",
    "flush_recipients",
    "flush_dose_delivered",
)


def test_flush_witness_keys_present_and_zero_when_off() -> None:
    core = _core()  # fraction absent -> off
    for key in FLUSH_KEYS:
        assert key in core.sanitary_telemetry
        assert core.sanitary_telemetry[key] == 0


def test_flush_witness_positive_and_consistent_when_on() -> None:
    core, shedder, visitor = _emitted_sanitary_core()
    matrix = ContactTracingMatrix(epoch=0)
    agent_doses: dict[int, float] = {}
    core._pathway_flush_aerosol(
        {THEATER: [visitor], HEAD: []}, agent_doses, matrix, {},
        PATHOGEN,
    )
    tel = core.sanitary_telemetry
    assert tel["flush_recipients"] > 0
    assert tel["flush_dose_delivered"] > 0.0
    # Recipients count exactly the positive-dose exposure records.
    assert tel["flush_recipients"] == len(matrix.flush_aerosol_exposures)
    assert tel["flush_dose_delivered"] == pytest.approx(
        sum(r["dose"] for r in matrix.flush_aerosol_exposures), rel=1e-6,
    )


def test_emit_updates_events_and_emitted_mass() -> None:
    core = _core(1e-6, seed=7)
    shedder = _shedder(core)
    _force_stool_event(core, shedder, THEATER)
    assert core.sanitary_telemetry["flush_events"] == 1
    assert core.sanitary_telemetry["flush_aerosol_emitted"] > 0.0


# ── Manifest builder: staged-sweep plumbing ──────────────────────────

import importlib.util  # noqa: E402


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_flush_sweep_v1_manifest",
        REPO_ROOT / "scripts" / "build_flush_sweep_v1_manifest.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seeds_is_a_prefix_of_the_matched_block() -> None:
    mod = _builder()
    full = mod.build(arm="1e-7", cabin_emission=True, seeds=200)
    staged = mod.build(arm="1e-7", cabin_emission=True, seeds=100)
    for tier_id in full["tiers"]:
        full_seeds = full["tiers"][tier_id]["seeds"]
        stage_seeds = staged["tiers"][tier_id]["seeds"]
        assert stage_seeds == full_seeds[:100]
        assert stage_seeds == mod.MATCHED_SEEDS[:100]
        # Same block, run-for-run: no resample, no offset.
        assert stage_seeds[0] == full_seeds[0]


def test_seeds_refuses_out_of_range() -> None:
    mod = _builder()
    for bad in (0, -1, len(mod.MATCHED_SEEDS) + 1):
        with pytest.raises(ValueError, match="--seeds"):
            mod.build(arm="1e-7", cabin_emission=True, seeds=bad)


def test_stage_tag_refusal_and_nocab_composition() -> None:
    mod = _builder()
    for bad in ("S1", "s-1", "stage 1", "", "s.1"):
        with pytest.raises(ValueError, match="--stage-tag"):
            mod.build(
                arm="1e-7", cabin_emission=True, stage_tag=bad,
            )
    tag = mod._arm_tag("1e-7", False, "s1")
    assert tag == "1e-7_s1_nocab"


def test_stage_tag_propagates_to_campaign_and_filename() -> None:
    mod = _builder()
    manifest = mod.build(
        arm="1e-7", cabin_emission=True, seeds=100, stage_tag="s1",
    )
    assert manifest["campaign"] == "flush_sweep_v1_1e-7_s1"
    assert mod._arm_tag("1e-7", True, "s1") == "1e-7_s1"
    # Untagged arm at the same fraction is a different label.
    plain = mod.build(arm="1e-7", cabin_emission=True)
    assert plain["campaign"] != manifest["campaign"]


@pytest.mark.parametrize("stage_tag", ["s2r", "s2e"])
def test_built_arms_pin_the_air_model_and_share_one_seed_block(
    stage_tag: str,
) -> None:
    mod = _builder()
    arms = ["off", "3e-9", "1e-8", "3e-8", "1e-7"]
    seed_blocks = set()
    for arm in arms:
        manifest = mod.build(arm=arm, cabin_emission=True, stage_tag=stage_tag)
        for tier in manifest["tiers"].values():
            overrides = tier["config_overrides"]
            assert overrides["transmission"]["cabin_air_mode"] == (
                "cabin_compartment"
            )
            assert overrides["hvac"]["pathogen_pool_transport"] == "airflow"
            seed_blocks.add(tuple(tier["seeds"]))
    assert len(seed_blocks) == 1


def test_half_decade_spellings_parse_inside_the_band() -> None:
    mod = _builder()
    new_arms = {"3e-9", "3e-8", "3e-7", "3e-6", "3e-5", "3e-4"}
    assert new_arms <= set(mod.FRACTION_ARMS)
    for spelling in new_arms:
        parsed = _parse_flush_aerosol_fraction(
            {"flush_aerosol_fraction": float(spelling)},
        )
        # The spelling round-trips: tag string -> float -> archived value.
        assert parsed == float(spelling)
        manifest = mod.build(arm=spelling, cabin_emission=True)
        tx = manifest["tiers"]["fl_cls_7d"]["config_overrides"]["transmission"]
        assert tx["flush_aerosol_fraction"] == float(spelling)
        assert float(manifest["campaign"].split("_")[-1]) == float(spelling)
