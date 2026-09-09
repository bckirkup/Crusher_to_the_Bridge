"""A table-service diner meets its table; a buffet diner meets the room.

Behaviour and invariant tests for DINE-PARTY-01: table-service venues seat
each sitting at fixed tables, a seated diner's direct-contact draw lands on
its table party by ``dining_party_contact_share``, buffet and crew-mess
diners and staff on shift keep the venue-wide draw, and a share of 0 is the
pre-party model. No golden numbers: every expectation is a relation between
runs of the same code or a declared bound.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    DEFAULT_DINING_TABLE_SIZE,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import (
    DEFAULT_DINING_PARTY_CONTACT_SHARE,
    TransmissionCore,
)
from orchestrator_init import assign_dining_parties

MDR = "MainDining"
BUFFET = "LidoBuffet"
MESS = "CrewMess"

ZONES = [
    {"name": MDR, "type": "Dining", "dining_service_type": "mdr"},
    {"name": "Grill", "type": "Dining", "dining_service_type": "specialty", "dining_table_size": 4},
    {"name": BUFFET, "type": "Dining", "dining_service_type": "buffet"},
    {"name": MESS, "type": "Dining", "dining_service_type": "crew_mess"},
    {"name": "Unnamed", "type": "Dining"},
]


def _agent(
    aid: int,
    dining: str,
    role: str = "passenger",
    seating: int = 0,
    infected: bool = False,
    at: str | None = None,
) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid, role=role, immune=False,
        home_zone="PC_D6", dining_zone=dining,
        work_zone=MDR if role == "crew" else "Pool",
        free_zone="Pool", schedule=["Meal:Dinner"] * 24,
    )
    a.meal_seating = seating
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = at or dining
    return a


class TestAssignDiningParties:
    def test_table_service_sittings_are_dealt_to_tables(self) -> None:
        agents = [_agent(i, MDR, seating=i % 2) for i in range(26)]
        assign_dining_parties(agents, ZONES)
        by_id = {a.agent_id: a for a in agents}
        for a in agents:
            assert 1 <= len(a.dining_party_ids) + 1 <= DEFAULT_DINING_TABLE_SIZE
            for m in a.dining_party_ids:
                assert by_id[m].dining_zone == MDR
                assert by_id[m].meal_seating == a.meal_seating
                assert a.agent_id in by_id[m].dining_party_ids
        # 13 per sitting at tables of 6 -> 6, 6, 1: the remainder sits alone.
        sizes = sorted(len(a.dining_party_ids) + 1 for a in agents if a.meal_seating == 0)
        assert sizes.count(6) == 12
        assert sizes.count(1) == 1

    def test_declared_table_size_and_name_fallback(self) -> None:
        grill = [_agent(i, "Grill") for i in range(9)]
        unnamed = [_agent(100 + i, "Unnamed") for i in range(7)]
        assign_dining_parties(grill + unnamed, ZONES)
        assert max(len(a.dining_party_ids) + 1 for a in grill) == 4
        assert max(len(a.dining_party_ids) + 1 for a in unnamed) == DEFAULT_DINING_TABLE_SIZE

    def test_buffet_and_crew_mess_diners_have_no_party(self) -> None:
        agents = [_agent(i, BUFFET) for i in range(12)]
        agents += [_agent(50 + i, MESS, role="crew") for i in range(12)]
        assign_dining_parties(agents, ZONES)
        assert all(not a.dining_party_ids for a in agents)

    def test_cabin_shares_a_table_when_in_the_same_sitting(self) -> None:
        agents = [_agent(i, MDR) for i in range(12)]
        agents[0].cabin_mate_ids = frozenset({11})
        agents[11].cabin_mate_ids = frozenset({0})
        assign_dining_parties(agents, ZONES)
        assert 11 in agents[0].dining_party_ids
        assert 0 in agents[11].dining_party_ids

    def test_assignment_is_deterministic_and_idempotent(self) -> None:
        def parties() -> list[frozenset[int]]:
            agents = [_agent(i, MDR, seating=i % 3) for i in range(40)]
            assign_dining_parties(agents, ZONES)
            assign_dining_parties(agents, ZONES)
            return [a.dining_party_ids for a in agents]

        assert parties() == parties()


def _core(share: float | None, seed: int = 11) -> TransmissionCore:
    cfg = {"transmission": {}} if share is None else {
        "transmission": {"dining_party_contact_share": share},
    }
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={MDR: 2000.0, BUFFET: 2000.0},
        zone_types={MDR: "Dining", BUFFET: "Dining"},
        cfg=cfg,
    )
    core.initialize_zones([MDR, BUFFET])
    return core


def _room(
    venue: str, tables: list[set[int]], shedders: set[int], staff: set[int] = frozenset(),
) -> list[KorkinAgent]:
    """A dining room at one sitting: seated tables plus staff without a seat."""
    agents = []
    for table in tables:
        for aid in sorted(table):
            a = _agent(aid, venue, infected=aid in shedders)
            a.dining_party_ids = frozenset(table - {aid})
            agents.append(a)
    for aid in sorted(staff):
        a = _agent(aid, MESS, role="crew", infected=aid in shedders, at=venue)
        agents.append(a)
    return agents


def _partner_rows(core: TransmissionCore, agents: list[KorkinAgent], epochs: int) -> list[dict]:
    rows: list[dict] = []
    shedders = {a.agent_id for a in agents if a.is_infected}
    for epoch in range(1, epochs + 1):
        matrix, _ = core.execute_transmission(
            epoch=epoch, agents=agents,
            zone_pathogen_mass={MDR: 0.0, BUFFET: 0.0},
            quarantined_ids=set(),
        )
        rows.extend(matrix.shared_room_exposures)
        for a in agents:
            if a.agent_id not in shedders:
                a.infection_status = InfectionStatus.SUSCEPTIBLE
                a.illness_status = IllnessStatus.NOT_ILL
    return rows


def _party_fraction(rows: list[dict], target: int, party: set[int]) -> float:
    picked = [s for r in rows if r["target_id"] == target for s in r["source_ids"]]
    assert picked, "no partners sampled"
    return sum(1 for s in picked if s in party) / len(picked)


# Table {1..6} with shedder 1 at target 2's table; tables {7..12}, {13..18}
# each carry one shedder on the floor, so the venue-wide draw is 1:2 party:floor.
TABLES = [{1, 2, 3, 4, 5, 6}, {7, 8, 9, 10, 11, 12}, {13, 14, 15, 16, 17, 18}]
SHEDDERS = {1, 7, 13}


class TestSeatedPartnerDraw:
    def test_default_share_is_the_sourced_constant(self) -> None:
        assert _core(None).dining_party_contact_share == DEFAULT_DINING_PARTY_CONTACT_SHARE

    @pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan")])
    def test_share_outside_unit_interval_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError):
            _core(bad)

    def test_party_share_grades_who_a_diner_meets(self) -> None:
        fractions = []
        for share in (0.0, 0.5, 1.0):
            rows = _partner_rows(_core(share), _room(MDR, TABLES, SHEDDERS), epochs=150)
            fractions.append(_party_fraction(rows, 2, {1}))
        assert fractions[0] < fractions[1] < fractions[2]
        assert fractions[2] == pytest.approx(1.0)
        # share 0 is the room-wide draw: the party shedder is one of three.
        assert 0.15 < fractions[0] < 0.55

    def test_full_share_never_reaches_across_tables(self) -> None:
        rows = _partner_rows(_core(1.0), _room(MDR, TABLES, SHEDDERS), epochs=150)
        for target, own_shedder in ((2, 1), (8, 7), (14, 13)):
            picked = {s for r in rows if r["target_id"] == target for s in r["source_ids"]}
            assert picked == {own_shedder}

    def test_contact_count_is_conserved_by_the_split(self) -> None:
        """The draw is who, not how many: the split never adds a contact, and
        only the table's own headcount can remove one."""
        for share in (0.0, 0.5, 1.0):
            rows = _partner_rows(_core(share), _room(MDR, TABLES, SHEDDERS), epochs=60)
            assert rows
            for r in rows:
                assert r["n_contacts"] <= r["r0_draw"]
                if r["r0_draw"] <= 1:
                    assert r["n_contacts"] == r["r0_draw"]

    def test_staff_on_shift_and_buffet_diners_keep_the_room_draw(self) -> None:
        staff_rows = _partner_rows(
            _core(1.0), _room(MDR, TABLES, SHEDDERS, staff={30}), epochs=150,
        )
        picked = {s for r in staff_rows if r["target_id"] == 30 for s in r["source_ids"]}
        assert picked == SHEDDERS

        buffet = _room(BUFFET, TABLES, SHEDDERS)
        for a in buffet:
            a.dining_party_ids = frozenset()
        buffet_rows = _partner_rows(_core(1.0), buffet, epochs=150)
        assert 0.15 < _party_fraction(buffet_rows, 2, {1}) < 0.55

    def test_a_seated_diner_elsewhere_keeps_the_room_draw(self) -> None:
        """The party is a venue fact: at another zone the same host mixes freely."""
        agents = _room(MDR, TABLES, SHEDDERS)
        for a in agents:
            a.current_location = BUFFET
        rows = _partner_rows(_core(1.0), agents, epochs=150)
        assert 0.15 < _party_fraction(rows, 2, {1}) < 0.55

    def test_share_zero_is_bit_identical_to_a_partyless_room(self) -> None:
        seated = _partner_rows(_core(0.0, seed=3), _room(MDR, TABLES, SHEDDERS), epochs=40)
        partyless = _room(MDR, TABLES, SHEDDERS)
        for a in partyless:
            a.dining_party_ids = frozenset()
        bare = _partner_rows(_core(1.0, seed=3), partyless, epochs=40)
        assert seated == bare
