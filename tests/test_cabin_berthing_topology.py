"""The cabin is the night mixing unit; the corridor is a residual.

Behaviour and invariant tests for BERTH-01: cabin mates meet at full
strength inside their stateroom, hallway encounters keep the declared
corridor factor and never include a cabin mate, fomite pools split per
cabin and re-aggregate under the parent zone, and crew are berthed by
department. No golden numbers: every expectation is a relation between
two runs of the same code.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    HAND_LOAD_LOG10_GEC,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    KorkinShipEngine,
)
from engines.transmission_core import (
    CABIN_COMPARTMENT_SEPARATOR,
    TransmissionCore,
)
from orchestrator_init import assign_cabin_mates

CORRIDOR = "PC_D6_P_F"

# The symptomatic-peak hand target get_pathogen_hand_target returns
# (10**3.86 GEC); the composed direct route doses only what the donor's
# hands carry, so fixture shedders hold a reservoir of this magnitude.
HAND_LOAD = 10.0 ** HAND_LOAD_LOG10_GEC


def _agent(aid: int, loc: str, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
        a.hand_load_by_pathogen = {"_default": HAND_LOAD}
    a.current_location = loc
    return a


def _corridor(cabins: list[set[int]], shedder: int = 1) -> list[KorkinAgent]:
    """Agents in one corridor, berthed into the given cabins."""
    agents = []
    for cabin in cabins:
        for aid in sorted(cabin):
            a = _agent(aid, CORRIDOR, infected=aid == shedder)
            a.cabin_mate_ids = frozenset(cabin - {aid})
            agents.append(a)
    return agents


def _core(seed: int = 7) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={CORRIDOR: 1200.0},
        zone_types={CORRIDOR: "Cabin_Corridor"},
    )
    core.initialize_zones([CORRIDOR])
    return core


def _reset_susceptibles(agents: list[KorkinAgent], shedder: int = 1) -> None:
    """Reset per-epoch state: susceptibles stay susceptible with an empty
    hand (so each row measures one epoch's acquired load, not a carried
    residue), and the shedder's reservoir is refilled because every
    contact and the fomite arm's decay draw it down."""
    for a in agents:
        if a.agent_id != shedder:
            a.infection_status = InfectionStatus.SUSCEPTIBLE
            a.illness_status = IllnessStatus.NOT_ILL
            a.hand_load_by_pathogen = {}
        else:
            a.hand_load_by_pathogen["_default"] = HAND_LOAD


def _exposures(
    agents: list[KorkinAgent],
    epochs: int,
    seed: int = 7,
    quarantined: set[int] | None = None,
) -> list[dict]:
    core = _core(seed)
    rows: list[dict] = []
    for epoch in range(1, epochs + 1):
        matrix, _ = core.execute_transmission(
            epoch=epoch, agents=agents, zone_pathogen_mass={CORRIDOR: 0.0},
            quarantined_ids=quarantined or set(),
        )
        rows.extend(matrix.shared_room_exposures)
        _reset_susceptibles(agents)
    return rows


def _doses_from(rows: list[dict], source: int) -> list[float]:
    return [r["dose"] for r in rows if r["source_ids"] == [source]] or [0.0]


class TestDirectContactUnits:
    def test_cabin_mate_meets_in_the_cabin_and_never_in_the_hallway(self) -> None:
        rows = _exposures(_corridor([{1, 2}, {3, 4}]), epochs=200)
        cabin = [r for r in rows if r["target_id"] == 2 and "compartment" in r]
        hallway = [r for r in rows if r["target_id"] == 2 and "compartment" not in r]
        assert cabin
        assert hallway
        assert all(r["compartment"].startswith(CORRIDOR + CABIN_COMPARTMENT_SEPARATOR) for r in cabin)
        assert all(r["zone"] == CORRIDOR for r in cabin + hallway)
        assert max(_doses_from(cabin, 1)) > 0
        assert all(1 not in r["source_ids"] for r in hallway)

    def test_hallway_residual_still_reaches_other_cabins(self) -> None:
        rows = _exposures(_corridor([{1, 2}, {3, 4}]), epochs=200)
        other = [r for r in rows if r["target_id"] in (3, 4)]
        assert other
        assert all("compartment" not in r for r in other)
        assert max(_doses_from(other, 1)) > 0

    def test_cabin_contact_is_full_strength_and_hallway_keeps_corridor_factor(self) -> None:
        """Same pair, same contact: cabin dose / hallway dose = 1 / corridor factor.

        Under the composed route the corridor factor scales the mouth dose,
        which is concave in the transferred load, so the realised ratio sits
        a few percent below 1/factor rather than on it; rel=0.10 at 2000
        epochs still fails if the factor is dropped (ratio -> 1) or doubled.
        """
        berthed = _exposures(_corridor([{1, 2}, {3, 4}]), epochs=2000)
        cabin_doses = [
            r["dose"] for r in berthed
            if r["target_id"] == 2 and "compartment" in r and r["source_ids"] == [1]
        ]
        unberthed = _exposures(_corridor([{1}, {2}, {3}, {4}]), epochs=2000)
        hallway_doses = [
            r["dose"] for r in unberthed
            if r["target_id"] == 2 and r["source_ids"] == [1]
        ]
        assert cabin_doses
        assert hallway_doses
        core = _core()
        ratio = np.median(cabin_doses) / np.median(hallway_doses)
        assert ratio == pytest.approx(1.0 / core.corridor_direct_contact_factor, rel=0.10)

    def test_more_berths_per_cabin_means_fewer_units_and_more_cabin_partners(self) -> None:
        agents_by_two = _corridor([{1, 2}, {3, 4}, {5, 6}])
        agents_by_three = _corridor([{1, 2, 3}, {4, 5, 6}])
        core = _core()
        units_two = core._direct_contact_units({CORRIDOR: agents_by_two})
        units_three = core._direct_contact_units({CORRIDOR: agents_by_three})
        assert len(units_two) == 3 + 1
        assert len(units_three) == 2 + 1
        assert sum(1 for _, _, hallway in units_two if hallway) == 1
        rows_two = _exposures(agents_by_two, epochs=200)
        rows_three = _exposures(agents_by_three, epochs=200)
        cabin_targets_two = {r["target_id"] for r in rows_two if "compartment" in r}
        cabin_targets_three = {r["target_id"] for r in rows_three if "compartment" in r}
        assert cabin_targets_two == {2}
        assert cabin_targets_three == {2, 3}

    def test_single_cabin_has_no_cabin_unit(self) -> None:
        core = _core()
        units = core._direct_contact_units({CORRIDOR: _corridor([{1}, {2}])})
        assert [hallway for _, _, hallway in units] == [True]

    def test_non_cabin_zone_is_one_unit(self) -> None:
        core = _core()
        agents = [_agent(1, "MainDining_L", infected=True), _agent(2, "MainDining_L")]
        units = core._direct_contact_units({"MainDining_L": agents})
        assert units == [("MainDining_L", agents, False)]

    def test_hallway_shedders_drop_cabin_mates_only(self) -> None:
        agents = _corridor([{1, 2}, {3, 4}])
        shedders = [(agents[0], 1.0), (agents[2], 0.5)]
        kept = TransmissionCore._hallway_shedders(agents[1], shedders)
        assert [s.agent_id for s, _ in kept] == [3]
        kept = TransmissionCore._hallway_shedders(agents[3], shedders)
        assert [s.agent_id for s, _ in kept] == [1]


class TestConfinementStillHolds:
    @staticmethod
    def _doses(quarantined: set[int], cabin_mates: bool) -> tuple[float, float]:
        """Median per-contact dose to agent 2 from agent 1: (cabin, hallway)."""
        cabins = [{1, 2}] if cabin_mates else [{1}, {2}]
        rows = _exposures(_corridor(cabins), epochs=2000, quarantined=quarantined)
        met = [r for r in rows if r["target_id"] == 2 and r["source_ids"] == [1]]
        cabin = [r["dose"] for r in met if "compartment" in r]
        hallway = [r["dose"] for r in met if "compartment" not in r]
        return (
            float(np.median(cabin)) if cabin else 0.0,
            float(np.median(hallway)) if hallway else 0.0,
        )

    def test_confined_shedder_still_reaches_cabin_mate_at_full_strength(self) -> None:
        free_cabin, _ = self._doses(set(), cabin_mates=True)
        confined_cabin, _ = self._doses({1}, cabin_mates=True)
        assert free_cabin > 0
        # The pair factor is exactly 1 for a mate; the medians differ only
        # because quarantining the shedder diverts the rng stream, so the
        # two arms are different realisations of one distribution.
        assert confined_cabin == pytest.approx(free_cabin, rel=0.10)

    def test_confined_shedder_is_attenuated_for_non_mates(self) -> None:
        _, free_hall = self._doses(set(), cabin_mates=False)
        _, confined_hall = self._doses({1}, cabin_mates=False)
        assert free_hall > 0
        assert confined_hall < free_hall * 0.5


class TestCabinCompartments:
    def test_compartments_partition_the_corridor(self) -> None:
        core = _core()
        agents = _corridor([{1, 2}, {3, 4, 5}, {6}])
        split = core._cabin_compartments({CORRIDOR: agents, "MainDining_L": []})
        cabin_keys = [k for k in split if k.startswith(CORRIDOR)]
        assert len(cabin_keys) == 3
        assert sorted(a.agent_id for k in cabin_keys for a in split[k]) == [1, 2, 3, 4, 5, 6]
        assert all(core.compartment_parent(k) == CORRIDOR for k in cabin_keys)
        assert all(core.zone_types[k] == "Cabin_Corridor" for k in cabin_keys)
        assert "MainDining_L" in split

    def test_compartment_key_is_stable_across_cabin_mates(self) -> None:
        core = _core()
        agents = _corridor([{7, 3, 11}])
        keys = {core._cabin_compartment_key(CORRIDOR, a) for a in agents}
        assert keys == {f"{CORRIDOR}{CABIN_COMPARTMENT_SEPARATOR}3"}

    def test_zone_surface_mass_pools_cabins_under_the_parent(self) -> None:
        core = _core()
        cabin_a = f"{CORRIDOR}{CABIN_COMPARTMENT_SEPARATOR}1"
        cabin_b = f"{CORRIDOR}{CABIN_COMPARTMENT_SEPARATOR}3"
        core.surface_pools = {CORRIDOR: 1.0, cabin_a: 2.0, cabin_b: 4.0, "MainDining_L": 8.0}
        core.surface_pools_by_pathogen = {"norwalk_gi": {cabin_a: 2.0, cabin_b: 4.0}}
        assert core.zone_surface_mass(CORRIDOR) == pytest.approx(7.0)
        assert core.zone_surface_mass(CORRIDOR, "norwalk_gi") == pytest.approx(6.0)
        assert core.zone_surface_mass("MainDining_L") == pytest.approx(8.0)
        assert set(core.zone_surface_keys(CORRIDOR)) == {CORRIDOR, cabin_a, cabin_b}

    def test_prev_occupancy_tracks_both_corridor_and_cabins(self) -> None:
        core = _core()
        agents = _corridor([{1, 2}, {3, 4}])
        core._update_prev_occupancy({CORRIDOR: agents})
        assert core._prev_zone_occupants[CORRIDOR] == {1, 2, 3, 4}
        cabin_keys = [k for k in core._prev_zone_occupants if CABIN_COMPARTMENT_SEPARATOR in k]
        assert sorted(sorted(core._prev_zone_occupants[k]) for k in cabin_keys) == [[1, 2], [3, 4]]


class _Berthed:
    def __init__(self, agent_id: int, home_zone: str, agent_class: str) -> None:
        self.agent_id = agent_id
        self.home_zone = home_zone
        self.agent_class = agent_class
        self.cabin_mate_ids: frozenset[int] = frozenset()


class TestAssignCabinMates:
    ZONES = [
        {"name": "CC_D2_F", "type": "Cabin_Corridor", "cabin_size": 2,
         "cabin_size_by_class": {"crew_galley": 4}},
        {"name": "PC_D6_P_F", "type": "Cabin_Corridor", "cabin_size": 2},
        {"name": "MainDining_L", "type": "Dining"},
    ]

    @staticmethod
    def _cabins(agents: list[_Berthed]) -> set[frozenset[int]]:
        return {frozenset(a.cabin_mate_ids | {a.agent_id}) for a in agents}

    def test_cabins_never_mix_departments(self) -> None:
        agents = [_Berthed(i, "CC_D2_F", "crew_general" if i % 2 else "crew_engineering") for i in range(8)]
        assign_cabin_mates(agents, self.ZONES)
        by_id = {a.agent_id: a for a in agents}
        for a in agents:
            assert len(a.cabin_mate_ids) == 1
            assert all(by_id[m].agent_class == a.agent_class for m in a.cabin_mate_ids)

    def test_class_override_changes_berths_per_cabin(self) -> None:
        galley = [_Berthed(i, "CC_D2_F", "crew_galley") for i in range(8)]
        general = [_Berthed(100 + i, "CC_D2_F", "crew_general") for i in range(8)]
        assign_cabin_mates(galley + general, self.ZONES)
        assert {len(c) for c in self._cabins(galley)} == {4}
        assert {len(c) for c in self._cabins(general)} == {2}

    def test_passengers_and_non_cabin_zones(self) -> None:
        pax = [_Berthed(i, "PC_D6_P_F", "passenger_standard") for i in range(5)]
        diners = [_Berthed(50 + i, "MainDining_L", "passenger_standard") for i in range(3)]
        assign_cabin_mates(pax + diners, self.ZONES)
        assert sorted(len(c) for c in self._cabins(pax)) == [1, 2, 2]
        assert all(a.cabin_mate_ids == frozenset() for a in diners)


class TestDepartmentBerthing:
    ZONES = [
        {"name": "CC_D2_F", "type": "Cabin_Corridor", "cabin_size": 2},
        {"name": "CC_D2_A", "type": "Cabin_Corridor", "cabin_size": 2},
        {"name": "CC_D3_F", "type": "Cabin_Corridor", "cabin_size": 2},
        {"name": "PC_D6_P_F", "type": "Cabin_Corridor", "cabin_size": 2},
        {"name": "PC_D6_S_F", "type": "Cabin_Corridor", "cabin_size": 2},
        {"name": "Engine_Room", "type": "Free", "max_occupancy": 100},
        {"name": "Galley", "type": "Dining", "dining_service_type": "galley"},
        {"name": "Medical_Center", "type": "Free", "max_occupancy": 20},
        {"name": "Pool_Deck", "type": "Free", "max_occupancy": 300},
        {"name": "MainDining", "type": "Dining"},
    ]
    CLASSES = [
        {"class_id": "passenger", "role_group": "passenger", "fraction": 0.5,
         "home_zone_preference": "PC_", "duty_zone": ""},
        {"class_id": "crew_engineering", "role_group": "crew", "fraction": 0.2,
         "home_zone_preference": "CC_", "duty_zone": "Engine"},
        {"class_id": "crew_galley", "role_group": "crew", "fraction": 0.2,
         "home_zone_preference": "CC_", "duty_zone": "Galley"},
        {"class_id": "crew_medical", "role_group": "crew", "fraction": 0.1,
         "home_zone_preference": "CC_", "duty_zone": "Medical"},
    ]

    def _engine(self, seed: int) -> KorkinShipEngine:
        return KorkinShipEngine(
            num_passengers=60, num_crew=60, initial_infected=0,
            zones=self.ZONES, agent_classes=self.CLASSES, seed=seed,
        )

    @pytest.mark.parametrize("seed", [3, 11])
    def test_a_department_shares_one_corridor_and_never_a_passenger_one(self, seed: int) -> None:
        engine = self._engine(seed)
        crew = [a for a in engine.agents if a.role == "crew"]
        assert crew
        homes_by_work: dict[str, set[str]] = {}
        for a in crew:
            homes_by_work.setdefault(a.work_zone, set()).add(a.home_zone)
        assert all(len(homes) == 1 for homes in homes_by_work.values())
        assert all(h.startswith("CC_") for homes in homes_by_work.values() for h in homes)
        assert len({next(iter(h)) for h in homes_by_work.values()}) == 3

    def test_passengers_still_spread_over_their_corridors(self) -> None:
        engine = self._engine(5)
        pax_homes = {a.home_zone for a in engine.agents if a.role == "passenger"}
        assert pax_homes == {"PC_D6_P_F", "PC_D6_S_F"}
