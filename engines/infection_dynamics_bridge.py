"""
engines.infection_dynamics_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python bridge to the Korkin Lab ``infection-dynamics`` ABM.

Faithfully re-implements the core mathematical structures from the Java
source (``NorwalkVirus/Source/CruiseShipModel/``) so that the orchestrator
can initialise the real agent graph at t=0 and advance it each epoch.

Key parameters extracted from the Java source
----------------------------------------------
- **Person.java**: Norwalk shedding curves (log10 copies/g, days 0-14),
  dose-response infection probability P(inf) = 1 - (1+dose/β)^{-α},
  illness probability P(ill) = 1 - (1+η·dose)^{-γ}.
- **Agent.java**: 24-hour behavior schedule (Sleep/Meal/Free/Work),
  spatial node assignments (home, dining, free, work, boarding).
- **Ship.java**: Population structure (1888 passengers + 814 crew),
  zone types (Room, Dining, Free, Boarding), containment flags
  (vspIsolation, selfIsolation, diningRestricted).
- **Passenger.java / StrucCrew.java**: Role-specific behavior schedules.
- **Compartmental-models**: SEIQR parameters (R0=2.1, σ=0.20, γ=0.091).

The bridge outputs agent states compatible with ``telemetry_buffer.schema``.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

import numpy as np


# ── Korkin Lab parameters (from Person.java) ─────────────────────────────

# RT-PCR shedding values: log10(copies/g), indexed by day post-infection.
# Source: "Norwalk Virus Shedding after Experimental Human Infection" Fig 1C/E.
SYMPTOMATIC_SHEDDING = [7.75, 9.0, 11.0, 11.0, 11.0, 10.0, 10.0, 9.5, 9.0, 9.0, 8.0, 8.0, 8.0, 8.0, 8.0]
ASYMPTOMATIC_SHEDDING = [7.75, 9.5, 10.5, 10.0, 9.0, 8.0, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75]
DOSE_ADJUSTMENT = 4.0

# Dose-response coefficients: "Norwalk virus: How infectious is it?" Table III.
ALPHA = 0.111
BETA = 32.81
ETA = 0.508
GAMMA = 0.095

# Population parameters (from Ship.java)
DEFAULT_NUM_PASSENGERS = 1888
DEFAULT_NUM_CREW = 814
IMMUNE_RATIO = 0.2

# Containment threshold (from Agent.java)
VSP_THRESHOLD_FRACTION = 0.03

# Recovery threshold (from Person.java)
RECOVERY_DAY = 3

# Environmental deposition: fraction of shedding that deposits on surfaces
# (ViralParticle.java: particles survive 86400 steps = 1 day)
SURFACE_DEPOSITION_FRACTION = 1e-4
ENV_DECAY_RATE = 0.5  # legacy flat daily decay (unused when CONTAM transport is active)

# SEIQR compartmental parameters (from compartmental-models/SEIQR-SCM-diamond.Rmd)
SEIQR_R0 = 2.1
SEIQR_BETA = 0.19
SEIQR_SIGMA = 0.20
SEIQR_GAMMA_RATE = 0.091
SEIQR_INCUBATION_DAYS = 5
SEIQR_INFECTIOUS_DAYS = 11


# ── Enumerations ─────────────────────────────────────────────────────────

class InfectionStatus(Enum):
    SUSCEPTIBLE = 0
    INFECTED = 1
    RECOVERED = 2
    DEAD = 3
    IMMUNE = 4


class IllnessStatus(Enum):
    NOT_ILL = 0
    SYMPTOMATIC = 1
    RECOVERED = 2


# ── Zone definitions (from Ship.java room/dining/free types) ─────────────

DEFAULT_ZONES = [
    {"name": "Berthing_Passenger", "type": "Room",    "capacity": "high"},
    {"name": "Berthing_Crew",     "type": "Room",    "capacity": "medium"},
    {"name": "Mess_Hall",         "type": "Dining",  "capacity": "high"},
    {"name": "Galley",            "type": "Dining",  "capacity": "high"},
    {"name": "Bridge",            "type": "Free",    "capacity": "low"},
    {"name": "Engine_Room",       "type": "Free",    "capacity": "medium"},
    {"name": "MedBay",            "type": "Free",    "capacity": "low"},
    {"name": "Recreation",        "type": "Free",    "capacity": "medium"},
]

# Passenger 24-hour behavior schedule (from Passenger.java)
PASSENGER_SCHEDULE = [
    "Sleep", "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep", "Sleep",
    "Meal:Breakfast", "Meal:Breakfast",
    "Free",
    "Meal:Lunch", "Meal:Lunch",
    "Free", "Free", "Free", "Free",
    "Meal:Dinner", "Meal:Dinner",
    "Free", "Free", "Free", "Free",
]

# Structured crew 24-hour behavior schedule (from StrucCrew.java)
CREW_SCHEDULE = [
    "Work", "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep",
    "Meal:Breakfast",
    "Work", "Work", "Work", "Work",
    "Meal:Lunch",
    "Work", "Work", "Work", "Work", "Work",
    "Meal:Dinner",
    "Work", "Work", "Work", "Work",
]


# ── Dose-response functions (from Person.java) ──────────────────────────

def infection_probability(dose: float) -> float:
    """P(inf) = 1 - (1 + dose/β)^{-α}.  (Person.java line 166)"""
    if dose <= 0:
        return 0.0
    return 1.0 - math.pow(1.0 + dose / BETA, -ALPHA)


def illness_probability(dose: float) -> float:
    """P(ill) = 1 - (1 + η·dose)^{-γ}.  (Person.java line 193)"""
    if dose <= 0:
        return 0.0
    return 1.0 - math.pow(1.0 + ETA * dose, -GAMMA)


def shedding_value(day_post_infection: int, is_symptomatic: bool) -> float:
    """Compute shedding as 10^(log10_rate - doseAdjustment).

    Clamps to day index 14 if past the shedding curve length.
    (Person.java lines 321-332)
    """
    curve = SYMPTOMATIC_SHEDDING if is_symptomatic else ASYMPTOMATIC_SHEDDING
    idx = min(day_post_infection, len(curve) - 1)
    return max(1.0, math.pow(10, curve[idx] - DOSE_ADJUSTMENT))


# ── Agent class ──────────────────────────────────────────────────────────

class KorkinAgent:
    """Single agent in the Korkin Lab infection-dynamics model.

    Attributes mirror the Java ``Person`` + ``Agent`` classes:
    - infection_status, illness_status, immune
    - shedding, acquired_particles, time_infected (epoch)
    - role (passenger/crew), home_zone, schedule
    - current_location (zone name)
    """

    __slots__ = (
        "agent_id", "role", "immune",
        "infection_status", "illness_status",
        "time_infected", "acquired_particles",
        "home_zone", "dining_zone", "work_zone", "free_zone",
        "current_location", "schedule",
    )

    def __init__(
        self,
        agent_id: int,
        role: str,
        immune: bool,
        home_zone: str,
        dining_zone: str,
        work_zone: str,
        free_zone: str,
        schedule: list[str],
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.immune = immune
        self.infection_status = InfectionStatus.IMMUNE if immune else InfectionStatus.SUSCEPTIBLE
        self.illness_status = IllnessStatus.NOT_ILL
        self.time_infected: int | None = None
        self.acquired_particles: float = 0.0
        self.home_zone = home_zone
        self.dining_zone = dining_zone
        self.work_zone = work_zone
        self.free_zone = free_zone
        self.current_location = home_zone
        self.schedule = list(schedule)

    @property
    def days_post_infection(self) -> int:
        """Days since infection (0-indexed).  -1 if not infected."""
        if self.time_infected is None:
            return -1
        return self.time_infected

    @property
    def is_infected(self) -> bool:
        return self.infection_status == InfectionStatus.INFECTED

    @property
    def is_symptomatic(self) -> bool:
        return self.illness_status == IllnessStatus.SYMPTOMATIC

    @property
    def is_recovered(self) -> bool:
        return self.infection_status == InfectionStatus.RECOVERED

    @property
    def current_shedding(self) -> float:
        """Active shedding value (0 if not infected or recovered)."""
        if not self.is_infected:
            return 0.0
        dpi = self.days_post_infection
        if dpi < 0:
            return 0.0
        return shedding_value(dpi, self.is_symptomatic)

    def get_location_for_hour(self, hour: int, randomness: float = 0.0) -> str:
        """Determine where this agent should be at the given hour.

        Mirrors Agent.getProjectedDestination() in the Java source.
        """
        adjusted_hour = int((hour + randomness + 24.0) % 24.0)
        activity = self.schedule[adjusted_hour]
        if activity == "Sleep":
            return self.home_zone
        if activity.startswith("Meal"):
            return self.dining_zone
        if activity == "Free":
            return self.free_zone
        if activity == "Work":
            return self.work_zone
        return self.home_zone

    def to_schema_dict(self) -> dict[str, Any]:
        """Export agent state in telemetry_buffer.schema format."""
        if self.infection_status == InfectionStatus.INFECTED:
            if self.is_symptomatic:
                symptom_status = "symptomatic"
            else:
                symptom_status = "asymptomatic_shedding"
        elif self.is_recovered:
            symptom_status = "recovered"
        elif self.immune:
            symptom_status = "immune"
        else:
            symptom_status = "asymptomatic"

        return {
            "agent_id": self.agent_id,
            "symptom_status": symptom_status,
            "shedding_rate": round(self.current_shedding, 2),
            "location": self.current_location,
            "role": self.role,
            "days_post_infection": self.days_post_infection if self.is_infected else None,
        }


# ── Ship simulation engine ──────────────────────────────────────────────

class KorkinShipEngine:
    """Python bridge to the Korkin Lab infection-dynamics ABM.

    Initialises the agent graph from the real model parameters and
    advances the simulation one epoch (= one day) at a time.
    """

    def __init__(
        self,
        num_passengers: int = DEFAULT_NUM_PASSENGERS,
        num_crew: int = DEFAULT_NUM_CREW,
        initial_infected: int = 1,
        zones: list[dict[str, str]] | None = None,
        immune_ratio: float = IMMUNE_RATIO,
        vsp_isolation: bool = True,
        seed: int = 42,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.zones = zones or DEFAULT_ZONES
        self.num_passengers = num_passengers
        self.num_crew = num_crew
        self.initial_infected = initial_infected
        self.immune_ratio = immune_ratio
        self.vsp_isolation = vsp_isolation

        self._dining_zones = [z["name"] for z in self.zones if z["type"] == "Dining"]
        self._free_zones = [z["name"] for z in self.zones if z["type"] == "Free"]
        self._room_zones = [z["name"] for z in self.zones if z["type"] == "Room"]
        self._all_zone_names = [z["name"] for z in self.zones]

        self.agents: list[KorkinAgent] = []
        self.epoch: int = 0
        self.vsp_triggered: bool = False
        self.isolated_ids: set[int] = set()

        self._zone_pathogen_mass: dict[str, float] = {z["name"]: 0.0 for z in self.zones}
        self._external_transport: bool = False
        self._external_transmission: bool = False

        self._initialize_agents()

    def _initialize_agents(self) -> None:
        """Create the full agent population (infection-dynamics ``agentAdder`` pattern)."""
        total = self.num_passengers + self.num_crew
        immune_remaining = int(total * self.immune_ratio)
        infected_remaining = self.initial_infected
        agent_id = 0

        # Passengers
        for _ in range(self.num_passengers):
            immune = False
            if immune_remaining > 0 and (agent_id % 5 == 0):
                immune = True
                immune_remaining -= 1

            home = self.rng.choice([z for z in self._room_zones if "Passenger" in z or "Berthing" in z]
                                   if any("Passenger" in z for z in self._room_zones)
                                   else self._room_zones)
            dining = self.rng.choice(self._dining_zones)
            free = self.rng.choice(self._free_zones)
            work = self.rng.choice(self._free_zones)
            randomness = self.rng.uniform(-2.0, 2.0)
            schedule = [s for s in PASSENGER_SCHEDULE]

            agent = KorkinAgent(
                agent_id=agent_id, role="passenger", immune=immune,
                home_zone=home, dining_zone=dining,
                work_zone=work, free_zone=free, schedule=schedule,
            )

            if not immune and infected_remaining > 0:
                agent.infection_status = InfectionStatus.INFECTED
                agent.illness_status = IllnessStatus.SYMPTOMATIC
                agent.time_infected = 1
                agent.acquired_particles = math.pow(10, SYMPTOMATIC_SHEDDING[1] - DOSE_ADJUSTMENT)
                infected_remaining -= 1

            self.agents.append(agent)
            agent_id += 1

        # Crew
        for _ in range(self.num_crew):
            immune = False
            if immune_remaining > 0 and (agent_id % 5 == 0):
                immune = True
                immune_remaining -= 1

            home = self.rng.choice([z for z in self._room_zones if "Crew" in z or "Berthing" in z]
                                   if any("Crew" in z for z in self._room_zones)
                                   else self._room_zones)
            dining = self.rng.choice(self._dining_zones)
            free = self.rng.choice(self._free_zones)
            work = self.rng.choice(self._free_zones + self._dining_zones)
            schedule = [s for s in CREW_SCHEDULE]

            agent = KorkinAgent(
                agent_id=agent_id, role="crew", immune=immune,
                home_zone=home, dining_zone=dining,
                work_zone=work, free_zone=free, schedule=schedule,
            )

            if not immune and infected_remaining > 0:
                agent.infection_status = InfectionStatus.INFECTED
                agent.illness_status = IllnessStatus.SYMPTOMATIC
                agent.time_infected = 1
                agent.acquired_particles = math.pow(10, SYMPTOMATIC_SHEDDING[1] - DOSE_ADJUSTMENT)
                infected_remaining -= 1

            self.agents.append(agent)
            agent_id += 1

    def step(self) -> dict[str, Any]:
        """Advance the simulation by one epoch (≈ one day).

        Performs, in order:
        1. Update agent locations based on hour-of-day schedules
        2. Infection transmission (proximity-based, zone-colocation)
        3. Illness progression (incubation → symptomatic)
        4. Recovery check
        5. VSP isolation check
        6. Zone pathogen mass accumulation from shedders
        7. Export full state as telemetry schema payload

        Returns the ground-truth payload dict.
        """
        self.epoch += 1

        # Representative hour for this epoch (midday activity peak)
        hour = 12

        # 1. Update agent locations
        for agent in self.agents:
            if agent.agent_id in self.isolated_ids:
                agent.current_location = "Isolated_In_Quarters"
                continue
            randomness = self.rng.uniform(-1.0, 1.0)
            agent.current_location = agent.get_location_for_hour(hour, randomness)

        # 2. Infection transmission
        # When TransmissionCore is active (_external_transmission=True),
        # this step is skipped — the orchestrator calls TransmissionCore
        # which handles all four pathways (direct, droplet, HVAC, fomite).
        if not self._external_transmission:
            zone_occupants: dict[str, list[KorkinAgent]] = {z: [] for z in self._all_zone_names}
            zone_occupants["Isolated_In_Quarters"] = []
            for agent in self.agents:
                loc = agent.current_location
                if loc in zone_occupants:
                    zone_occupants[loc].append(agent)

            for zone_name, occupants in zone_occupants.items():
                if zone_name == "Isolated_In_Quarters":
                    continue

                shedders = [a for a in occupants if a.is_infected and a.current_shedding > 0]
                susceptible = [a for a in occupants
                               if a.infection_status == InfectionStatus.SUSCEPTIBLE]

                if not shedders or not susceptible:
                    continue

                total_shedding = sum(s.current_shedding for s in shedders)

                avg_r_pool = [1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2]
                for target in susceptible:
                    r0_draw = int(self.rng.choice(avg_r_pool))
                    contact_shedding = total_shedding / max(len(occupants), 1) * r0_draw
                    inf_prob = infection_probability(contact_shedding)
                    if self.rng.random() < inf_prob:
                        target.infection_status = InfectionStatus.INFECTED
                        target.illness_status = IllnessStatus.NOT_ILL
                        target.time_infected = 0
                        target.acquired_particles = contact_shedding

        # 3. Illness progression
        for agent in self.agents:
            if not agent.is_infected:
                continue
            if agent.time_infected is not None:
                agent.time_infected += 1
            dpi = agent.days_post_infection
            if dpi >= 1 and agent.illness_status == IllnessStatus.NOT_ILL:
                ill_prob = illness_probability(agent.acquired_particles)
                if ill_prob > 0.3:
                    agent.illness_status = IllnessStatus.SYMPTOMATIC

        # 4. Recovery (Person.java: dpi >= 3)
        for agent in self.agents:
            if agent.is_infected and agent.days_post_infection >= RECOVERY_DAY:
                agent.infection_status = InfectionStatus.RECOVERED
                agent.illness_status = IllnessStatus.RECOVERED

        # 5. VSP isolation check (Agent.java: 3% threshold)
        total_pop = len(self.agents)
        total_ill = sum(1 for a in self.agents if a.is_symptomatic)
        vsp_threshold = int(VSP_THRESHOLD_FRACTION * total_pop)
        if self.vsp_isolation and total_ill >= vsp_threshold and not self.vsp_triggered:
            self.vsp_triggered = True

        if self.vsp_triggered:
            for agent in self.agents:
                if agent.is_symptomatic and agent.agent_id not in self.isolated_ids:
                    self.isolated_ids.add(agent.agent_id)

        # 6. Zone pathogen mass: new deposits from shedders
        # NOTE: Decay is now handled externally by the CONTAM transport
        # engine (py_contam_bridge) when available.  If no transport engine
        # is configured, the orchestrator falls back to the legacy flat
        # decay rate (ENV_DECAY_RATE).
        if not self._external_transport:
            for zname in self._all_zone_names:
                self._zone_pathogen_mass[zname] *= ENV_DECAY_RATE

        for agent in self.agents:
            if agent.is_infected and agent.current_shedding > 0:
                loc = agent.current_location
                if loc in self._zone_pathogen_mass:
                    deposited = agent.current_shedding * SURFACE_DEPOSITION_FRACTION
                    self._zone_pathogen_mass[loc] += deposited

        # 7. Export payload
        return self._export_payload()

    def _export_payload(self) -> dict[str, Any]:
        """Build the telemetry schema payload from current state."""
        agents_out = [a.to_schema_dict() for a in self.agents]
        spaces_out = {}
        for zone in self.zones:
            zname = zone["name"]
            spaces_out[zname] = {
                "pathogen_mass": round(self._zone_pathogen_mass.get(zname, 0.0), 3),
                "microbiome_id": f"profile_{zname.lower()}",
            }
        return {
            "epoch": self.epoch,
            "agents": agents_out,
            "spaces": spaces_out,
        }

    @property
    def zone_pathogen_mass(self) -> dict[str, float]:
        """Read/write access to per-zone pathogen mass for CONTAM transport."""
        return self._zone_pathogen_mass

    @zone_pathogen_mass.setter
    def zone_pathogen_mass(self, value: dict[str, float]) -> None:
        self._zone_pathogen_mass = value

    def enable_external_transport(self) -> None:
        """Disable internal flat decay — transport handled externally."""
        self._external_transport = True

    def enable_external_transmission(self) -> None:
        """Disable internal monolithic transmission — handled by TransmissionCore."""
        self._external_transmission = True

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the current population state."""
        total = len(self.agents)
        susceptible = sum(1 for a in self.agents if a.infection_status == InfectionStatus.SUSCEPTIBLE)
        infected = sum(1 for a in self.agents if a.is_infected)
        symptomatic = sum(1 for a in self.agents if a.is_symptomatic)
        recovered = sum(1 for a in self.agents if a.is_recovered)
        immune = sum(1 for a in self.agents if a.immune)
        isolated = len(self.isolated_ids)

        return {
            "epoch": self.epoch,
            "total": total,
            "susceptible": susceptible,
            "infected": infected,
            "symptomatic": symptomatic,
            "recovered": recovered,
            "immune": immune,
            "isolated": isolated,
            "vsp_triggered": self.vsp_triggered,
        }
