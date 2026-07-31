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

# Crew behavior schedule meal tokens (shared across class schedules)
MEAL_BREAKFAST = "Meal:Breakfast"
MEAL_LUNCH = "Meal:Lunch"
MEAL_DINNER = "Meal:Dinner"

# Passenger 24-hour behavior schedule (from Passenger.java)
PASSENGER_SCHEDULE = [
    "Sleep", "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep", "Sleep",
    MEAL_BREAKFAST, MEAL_BREAKFAST,
    "Free",
    MEAL_LUNCH, MEAL_LUNCH,
    "Free", "Free", "Free", "Free",
    MEAL_DINNER, MEAL_DINNER,
    "Free", "Free", "Free", "Free",
]

# Structured crew 24-hour behavior schedule (from StrucCrew.java)
CREW_SCHEDULE = [
    "Work", "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep",
    MEAL_BREAKFAST,
    "Work", "Work", "Work", "Work",
    MEAL_LUNCH,
    "Work", "Work", "Work", "Work", "Work",
    MEAL_DINNER,
    "Work", "Work", "Work", "Work",
]

# ── Extended agent class schedules ───────────────────────────────────────

# Medical crew: duty station = MedBay; on-call overnight
MEDICAL_CREW_SCHEDULE = [
    "Work", "Work", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep",
    MEAL_BREAKFAST,
    "Work", "Work", "Work", "Work",
    MEAL_LUNCH,
    "Work", "Work", "Work", "Work", "Work",
    MEAL_DINNER,
    "Work", "Work", "Free", "Work",
]

# Engineering crew: 3-section watchbill, heavy work hours
ENGINEERING_CREW_SCHEDULE = [
    "Work", "Work", "Work", "Work", "Sleep", "Sleep",
    "Sleep", "Sleep",
    MEAL_BREAKFAST,
    "Work", "Work", "Work", "Work",
    MEAL_LUNCH,
    "Work", "Work", "Work", "Free",
    MEAL_DINNER,
    "Work", "Work", "Sleep", "Sleep",
]

# Galley crew: early starts for meal prep, split shifts
GALLEY_CREW_SCHEDULE = [
    "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Work", "Work", "Work",
    "Work",
    "Work", "Work", "Free", "Free",
    "Work",
    "Work", "Free", "Free", "Work", "Work",
    "Work",
    "Work", "Sleep", "Sleep", "Sleep",
]

# Elderly passenger: more rest, fewer free circulation hours
PASSENGER_ELDERLY_SCHEDULE = [
    "Sleep", "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep", "Sleep",
    MEAL_BREAKFAST, MEAL_BREAKFAST,
    "Free",
    MEAL_LUNCH, MEAL_LUNCH,
    "Sleep", "Free", "Free", "Free",
    MEAL_DINNER, MEAL_DINNER,
    "Free", "Sleep", "Sleep", "Sleep",
]

# Family passenger: includes Kids_Club activity blocks
PASSENGER_FAMILY_SCHEDULE = [
    "Sleep", "Sleep", "Sleep", "Sleep", "Sleep", "Sleep",
    "Sleep", "Sleep", "Sleep",
    MEAL_BREAKFAST, MEAL_BREAKFAST,
    "Free",
    MEAL_LUNCH, MEAL_LUNCH,
    "Free", "Free", "Free", "Free",
    MEAL_DINNER, MEAL_DINNER,
    "Free", "Free", "Free", "Sleep",
]

# Lookup table: class_id → default schedule
CLASS_SCHEDULES: dict[str, list[str]] = {
    "passenger_general": PASSENGER_SCHEDULE,
    "passenger_family": PASSENGER_FAMILY_SCHEDULE,
    "passenger_elderly": PASSENGER_ELDERLY_SCHEDULE,
    "crew_general": CREW_SCHEDULE,
    "crew_medical": MEDICAL_CREW_SCHEDULE,
    "crew_engineering": ENGINEERING_CREW_SCHEDULE,
    "crew_galley": GALLEY_CREW_SCHEDULE,
}

# Default gender distribution
DEFAULT_GENDER_DISTRIBUTION: dict[str, float] = {
    "male": 0.50,
    "female": 0.50,
}


# ── Dose-response functions (from Person.java) ──────────────────────────

def infection_probability(dose: float) -> float:
    """P(inf) = 1 - (1 + dose/β)^{-α}.  (Person.java line 166)"""
    if dose <= 0:
        return 0.0
    return 1.0 - math.pow(1.0 + dose / BETA, -ALPHA)


def illness_probability(
    dose: float,
    eta: float = ETA,
    gamma: float = GAMMA,
) -> float:
    """P(ill) = 1 - (1 + η·dose)^{-γ}.  (Person.java line 193)"""
    if dose <= 0:
        return 0.0
    return 1.0 - math.pow(1.0 + eta * dose, -gamma)


def shedding_value(day_post_infection: int, is_symptomatic: bool) -> float:
    """Compute shedding as 10^(log10_rate - doseAdjustment).

    Clamps to day index 14 if past the shedding curve length.
    (Person.java lines 321-332)
    """
    curve = SYMPTOMATIC_SHEDDING if is_symptomatic else ASYMPTOMATIC_SHEDDING
    idx = min(day_post_infection, len(curve) - 1)
    return max(1.0, math.pow(10, curve[idx] - DOSE_ADJUSTMENT))


def draw_shedding_multiplier(
    rng: np.random.Generator,
    profile: dict[str, Any],
) -> float:
    """Draw a persistent per-agent shedding multiplier from a log-normal.

    ``shedding_variance_log10`` is the σ of the normal in log10 space; median
    multiplier is 1.0.  σ=0 (or absent) yields exactly 1.0.
    """
    variance = float(profile.get("shedding_variance_log10", 0.0))
    if variance <= 0:
        return 1.0
    return 10.0 ** float(rng.normal(0.0, variance))


# ── Agent class ──────────────────────────────────────────────────────────

class KorkinAgent:
    """Single agent in the Korkin Lab infection-dynamics model.

    Attributes mirror the Java ``Person`` + ``Agent`` classes:
    - infection_status, illness_status, immune
    - shedding, acquired_particles, time_infected (epoch)
    - role (passenger/crew), home_zone, schedule
    - current_location (zone name)

    Multi-pathogen extensions:
    - infections: dict keyed by pathogen_id tracking per-pathogen state
    - susceptibility_multiplier: dict keyed by pathogen_id → scalar
    - microflora_disruption_status: scalar [0.0..1.0] indicating
      compromised native microbiome
    """

    __slots__ = (
        "agent_id", "role", "agent_class", "gender", "immune",
        "infection_status", "illness_status",
        "time_infected", "acquired_particles",
        "home_zone", "dining_zone", "work_zone", "free_zone",
        "current_location", "schedule",
        # Multi-pathogen extensions
        "infections", "susceptibility_multiplier",
        "microflora_disruption_status",
        # Chronic disease extensions
        "chronic_disease_ids", "chronic_pathogen_mods",
        "chronic_wearable_response_scale",
        "shedding_multiplier", "cabin_mate_ids",
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
        agent_class: str = "",
        gender: str = "unknown",
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.agent_class = agent_class or role
        self.gender = gender
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

        # Multi-pathogen co-infection tracking:
        # {pathogen_id: {"status": InfectionStatus, "illness": IllnessStatus,
        #   "time_infected": int|None, "acquired_particles": float}}
        self.infections: dict[str, dict[str, Any]] = {}

        # Per-pathogen susceptibility scaling (higher = more vulnerable)
        self.susceptibility_multiplier: dict[str, float] = {}

        # Microflora disruption scalar [0.0 = healthy, 1.0 = fully disrupted]
        self.microflora_disruption_status: float = 0.0

        # Chronic disease state (static, assigned at initialization)
        self.chronic_disease_ids: list[str] = []
        # Resolved per-pathogen modifiers from chronic diseases:
        # {pathogen_id: {"susceptibility_multiplier", "severity_multiplier",
        #   "recovery_day_extension", "illness_probability_boost"}}
        self.chronic_pathogen_mods: dict[str, dict[str, float]] = {}
        # Aggregate wearable infection response scale from chronic diseases
        self.chronic_wearable_response_scale: float = 1.0

        # Legacy single-pathogen shedding host factor (also mirrored on first infection)
        self.shedding_multiplier: float = 1.0
        # Cabin-mate agent IDs sharing the same stateroom (mega_cruise_5000)
        self.cabin_mate_ids: frozenset[int] = frozenset()

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
        return shedding_value(dpi, self.is_symptomatic) * self.shedding_multiplier

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

    def init_pathogen_susceptibility(
        self, pathogen_id: str, base_susceptibility: float = 1.0,
    ) -> None:
        """Set default susceptibility for a pathogen if not already set."""
        if pathogen_id not in self.susceptibility_multiplier:
            self.susceptibility_multiplier[pathogen_id] = base_susceptibility

    def infect_with_pathogen(
        self,
        pathogen_id: str,
        dose: float,
        epoch: int,
        *,
        time_infected: int = 0,
        rng: np.random.Generator | None = None,
        profile: dict[str, Any] | None = None,
    ) -> None:
        """Record co-infection for a specific pathogen.

        ``time_infected`` is days post-infection at assignment (index into
        shedding curves). Seeded introductions read ``initial_time_infected``
        from the pathogen profile; transmission events use the default 0.

        When ``rng`` and ``profile`` are supplied, draws a persistent
        ``shedding_multiplier`` from ``profile['shedding_variance_log10']``.
        """
        if time_infected < 0:
            raise ValueError(f"time_infected must be non-negative, got {time_infected}")
        shedding_mult = (
            draw_shedding_multiplier(rng, profile or {})
            if rng is not None
            else 1.0
        )
        self.infections[pathogen_id] = {
            "status": InfectionStatus.INFECTED,
            "illness": IllnessStatus.NOT_ILL,
            "time_infected": time_infected,
            "acquired_particles": dose,
            "infection_epoch": epoch,
            "shedding_multiplier": shedding_mult,
        }
        # Set legacy fields to infected if this is the first infection
        if self.infection_status == InfectionStatus.SUSCEPTIBLE:
            self.infection_status = InfectionStatus.INFECTED
            self.illness_status = IllnessStatus.NOT_ILL
            self.time_infected = time_infected
            self.acquired_particles = dose
            self.shedding_multiplier = shedding_mult

    def is_infected_with(self, pathogen_id: str) -> bool:
        """Check if agent is infected with a specific pathogen."""
        inf = self.infections.get(pathogen_id)
        if inf is None:
            return False
        return inf["status"] == InfectionStatus.INFECTED

    def get_pathogen_shedding(self, pathogen_id: str, profile: dict) -> float:
        """Shedding value for a specific pathogen based on its profile."""
        inf = self.infections.get(pathogen_id)
        if inf is None or inf["status"] != InfectionStatus.INFECTED:
            return 0.0
        dpi = inf["time_infected"]
        if dpi is None or dpi < 0:
            return 0.0
        is_symp = inf["illness"] == IllnessStatus.SYMPTOMATIC
        curve = profile.get(
            "shedding_curve_log10",
            SYMPTOMATIC_SHEDDING if is_symp else ASYMPTOMATIC_SHEDDING,
        )
        if not is_symp:
            curve = profile.get("asymptomatic_shedding_log10", curve)
        adj = profile.get("dose_adjustment", DOSE_ADJUSTMENT)
        idx = min(dpi, len(curve) - 1)
        base = math.pow(10, curve[idx] - adj)
        return base * inf.get("shedding_multiplier", 1.0)

    def update_microflora_disruption(self, pathogen_profiles: dict) -> None:
        """Recompute microflora_disruption_status from all active infections."""
        max_disruption = 0.0
        for pid, inf in self.infections.items():
            if inf["status"] != InfectionStatus.INFECTED:
                continue
            profile = pathogen_profiles.get(pid, {})
            mf = profile.get("microflora_disruption", {})
            if mf.get("causes_disruption", False):
                mag = mf.get("disruption_magnitude", 0.5)
                max_disruption = max(max_disruption, mag)
        self.microflora_disruption_status = max_disruption

    @property
    def active_pathogen_ids(self) -> list[str]:
        """List of pathogen IDs this agent is actively infected with."""
        return [
            pid for pid, inf in self.infections.items()
            if inf["status"] == InfectionStatus.INFECTED
        ]

    def apply_chronic_disease(
        self,
        disease_id: str,
        pathogen_modifiers: dict[str, dict[str, float]],
        wearable_response_scale: float = 1.0,
    ) -> None:
        """Register a chronic disease and merge its per-pathogen modifiers."""
        if disease_id in self.chronic_disease_ids:
            return
        self.chronic_disease_ids.append(disease_id)
        for pid, mods in pathogen_modifiers.items():
            if pid not in self.chronic_pathogen_mods:
                self.chronic_pathogen_mods[pid] = dict(mods)
            else:
                existing = self.chronic_pathogen_mods[pid]
                existing["susceptibility_multiplier"] = (
                    existing.get("susceptibility_multiplier", 1.0)
                    * mods.get("susceptibility_multiplier", 1.0)
                )
                existing["severity_multiplier"] = max(
                    existing.get("severity_multiplier", 1.0),
                    mods.get("severity_multiplier", 1.0),
                )
                existing["recovery_day_extension"] = (
                    existing.get("recovery_day_extension", 0)
                    + mods.get("recovery_day_extension", 0)
                )
                existing["illness_probability_boost"] = min(
                    0.5,
                    existing.get("illness_probability_boost", 0.0)
                    + mods.get("illness_probability_boost", 0.0),
                )
        self.chronic_wearable_response_scale = max(
            self.chronic_wearable_response_scale, wearable_response_scale,
        )

    def get_chronic_recovery_day(
        self, pathogen_id: str, base_recovery_day: int,
    ) -> int:
        """Return recovery day adjusted for chronic disease extensions."""
        mods = self.chronic_pathogen_mods.get(
            pathogen_id, self.chronic_pathogen_mods.get("default", {}),
        )
        return base_recovery_day + int(mods.get("recovery_day_extension", 0))

    def get_chronic_illness_boost(self, pathogen_id: str) -> float:
        """Return additive illness probability boost from chronic diseases."""
        mods = self.chronic_pathogen_mods.get(
            pathogen_id, self.chronic_pathogen_mods.get("default", {}),
        )
        return float(mods.get("illness_probability_boost", 0.0))

    def get_chronic_severity_multiplier(self, pathogen_id: str) -> float:
        """Return severity multiplier from chronic diseases."""
        mods = self.chronic_pathogen_mods.get(
            pathogen_id, self.chronic_pathogen_mods.get("default", {}),
        )
        return float(mods.get("severity_multiplier", 1.0))

    @property
    def has_chronic_disease(self) -> bool:
        return len(self.chronic_disease_ids) > 0

    def to_schema_dict(self) -> dict[str, Any]:
        """Export agent state in telemetry_buffer.schema format."""
        from telemetry_buffer.agent_axes import (
            COMPLIANCE_COMPLIANT,
            INFECTION_IMMUNE,
            INFECTION_INFECTED,
            INFECTION_RECOVERED,
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
            PRESENTATION_SYMPTOMATIC,
        )

        if self.infection_status == InfectionStatus.INFECTED:
            infection_state = INFECTION_INFECTED
            symptom_presentation = (
                PRESENTATION_SYMPTOMATIC
                if self.is_symptomatic
                else PRESENTATION_ASYMPTOMATIC
            )
        elif self.is_recovered:
            infection_state = INFECTION_RECOVERED
            symptom_presentation = PRESENTATION_ASYMPTOMATIC
        elif self.immune:
            infection_state = INFECTION_IMMUNE
            symptom_presentation = PRESENTATION_ASYMPTOMATIC
        else:
            infection_state = INFECTION_SUSCEPTIBLE
            symptom_presentation = PRESENTATION_ASYMPTOMATIC

        # Multi-pathogen infection summary
        pathogen_states = {}
        for pid, inf in self.infections.items():
            pathogen_states[pid] = {
                "status": inf["status"].name,
                "illness": inf["illness"].name,
                "days_post_infection": inf["time_infected"],
            }

        result = {
            "agent_id": self.agent_id,
            "infection_state": infection_state,
            "symptom_presentation": symptom_presentation,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "shedding_rate": round(self.current_shedding, 2),
            "location": self.current_location,
            "role": self.role,
            "agent_class": self.agent_class,
            "gender": self.gender,
            "days_post_infection": self.days_post_infection if self.is_infected else None,
            "pathogen_infections": pathogen_states,
            "susceptibility_multiplier": dict(self.susceptibility_multiplier),
            "microflora_disruption": round(self.microflora_disruption_status, 4),
        }
        if self.chronic_disease_ids:
            result["chronic_disease_ids"] = list(self.chronic_disease_ids)
        if self.cabin_mate_ids:
            result["cabin_mate_ids"] = sorted(self.cabin_mate_ids)
        return result


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
        agent_classes: list[dict[str, Any]] | None = None,
        gender_distribution: dict[str, float] | None = None,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.zones = zones or DEFAULT_ZONES
        self.num_passengers = num_passengers
        self.num_crew = num_crew
        self.initial_infected = initial_infected
        self.immune_ratio = immune_ratio
        self.vsp_isolation = vsp_isolation
        self._agent_classes = agent_classes
        self._gender_distribution = gender_distribution or DEFAULT_GENDER_DISTRIBUTION
        self.vsp_threshold_fraction: float = VSP_THRESHOLD_FRACTION

        self._dining_zones = [z["name"] for z in self.zones if z["type"] == "Dining"]
        self._free_zones = [z["name"] for z in self.zones if z["type"] == "Free"]
        self._room_zones = [
            z["name"] for z in self.zones
            if z["type"] in ("Room", "Cabin_Corridor")
        ]
        self._all_zone_names = [z["name"] for z in self.zones]

        self.agents: list[KorkinAgent] = []
        self.epoch: int = 0
        self.vsp_triggered: bool = False
        self.isolated_ids: set[int] = set()
        self.quarantined_ids: set[int] = set()

        self._zone_pathogen_mass: dict[str, float] = {z["name"]: 0.0 for z in self.zones}
        # Multi-pathogen mass pools: {pathogen_id: {zone_name: float}}
        self._multi_pathogen_mass: dict[str, dict[str, float]] = {}
        self._external_transport: bool = False
        self._external_transmission: bool = False

        self._initialize_agents()

    def _assign_gender(self) -> str:
        """Sample a gender string from the configured distribution."""
        labels = list(self._gender_distribution.keys())
        weights = [self._gender_distribution[g] for g in labels]
        total = sum(weights)
        if total <= 0:
            return "unknown"
        probs = [w / total for w in weights]
        return str(self.rng.choice(labels, p=probs))

    def _resolve_zone(self, preference: str, fallback_zones: list[str]) -> str:
        """Pick a zone matching *preference* substring, or fall back."""
        matches = [z for z in fallback_zones if preference.lower() in z.lower()]
        if matches:
            return str(self.rng.choice(matches))
        if fallback_zones:
            return str(self.rng.choice(fallback_zones))
        return "unknown"

    def _initialize_agents(self) -> None:
        """Create the full agent population.

        When ``agent_classes`` are provided (from config), agents are
        distributed across the defined classes.  Otherwise falls back to
        the legacy two-class (passenger / crew) split.
        """
        total = self.num_passengers + self.num_crew
        immune_remaining = int(total * self.immune_ratio)
        infected_remaining = self.initial_infected
        agent_id = 0

        if self._agent_classes:
            agent_id = self._initialize_agents_from_classes(
                agent_id, immune_remaining, infected_remaining,
            )
        else:
            agent_id = self._initialize_agents_legacy(
                agent_id, immune_remaining, infected_remaining,
            )

    def _initialize_agents_from_classes(
        self,
        start_id: int,
        immune_remaining: int,
        infected_remaining: int,
    ) -> int:
        """Create agents distributed across configured agent classes."""
        total = self.num_passengers + self.num_crew
        agent_id = start_id

        # Build ordered list of (class_cfg, count) pairs
        class_counts: list[tuple[dict[str, Any], int]] = []
        allocated = 0
        for cls_cfg in self._agent_classes:
            fraction = cls_cfg.get("fraction", 0.0)
            count = int(total * fraction)
            class_counts.append((cls_cfg, count))
            allocated += count
        # Assign remainder to the first class
        if allocated < total and class_counts:
            first_cls, first_count = class_counts[0]
            class_counts[0] = (first_cls, first_count + (total - allocated))

        agents_left = sum(c for _, c in class_counts)

        for cls_cfg, count in class_counts:
            agent_id, immune_remaining, infected_remaining, agents_left = (
                self._spawn_class_agents(
                    cls_cfg, count, agent_id,
                    immune_remaining, infected_remaining, agents_left,
                )
            )

        return agent_id

    def _spawn_class_agents(
        self,
        cls_cfg: dict[str, Any],
        count: int,
        agent_id: int,
        immune_remaining: int,
        infected_remaining: int,
        agents_left: int,
    ) -> tuple[int, int, int, int]:
        class_id = cls_cfg.get("class_id", "crew_general")
        role_group = cls_cfg.get("role_group", "crew")
        schedule_template = CLASS_SCHEDULES.get(
            class_id, CREW_SCHEDULE if role_group == "crew" else PASSENGER_SCHEDULE,
        )
        home_pref = cls_cfg.get("home_zone_preference", "Berthing")
        duty_zone = cls_cfg.get("duty_zone", "")
        free_pref = cls_cfg.get("free_zone_preference", "")

        for _ in range(count):
            immune = False
            if immune_remaining > 0 and agents_left > 0:
                if self.rng.random() < immune_remaining / agents_left:
                    immune = True
                    immune_remaining -= 1
            agents_left -= 1

            home = self._resolve_zone(home_pref, self._room_zones)
            dining = str(self.rng.choice(self._dining_zones))
            if duty_zone:
                work = self._resolve_zone(duty_zone, self._free_zones + self._dining_zones)
            elif role_group == "crew":
                work = str(self.rng.choice(self._free_zones + self._dining_zones))
            else:
                work = str(self.rng.choice(self._free_zones))
            free = (
                self._resolve_zone(free_pref, self._free_zones)
                if free_pref else str(self.rng.choice(self._free_zones))
            )

            agent = KorkinAgent(
                agent_id=agent_id, role=role_group, immune=immune,
                home_zone=home, dining_zone=dining,
                work_zone=work, free_zone=free,
                schedule=list(schedule_template),
                agent_class=class_id, gender=self._assign_gender(),
            )

            if not immune and infected_remaining > 0:
                self._seed_initial_infection(agent, self.rng)
                infected_remaining -= 1

            self.agents.append(agent)
            agent_id += 1

        return agent_id, immune_remaining, infected_remaining, agents_left

    @staticmethod
    def _seed_initial_infection(agent: KorkinAgent, rng: np.random.Generator) -> None:
        agent.infection_status = InfectionStatus.INFECTED
        agent.time_infected = 1
        agent.acquired_particles = math.pow(
            10, SYMPTOMATIC_SHEDDING[1] - DOSE_ADJUSTMENT,
        )
        ill_prob = illness_probability(agent.acquired_particles)
        if rng.random() < ill_prob:
            agent.illness_status = IllnessStatus.SYMPTOMATIC

    def _initialize_agents_legacy(
        self,
        start_id: int,
        immune_remaining: int,
        infected_remaining: int,
    ) -> int:
        """Legacy two-class (passenger/crew) initialization."""
        agent_id = start_id

        agents_left = self.num_passengers + self.num_crew

        # Passengers
        for _ in range(self.num_passengers):
            immune = False
            if immune_remaining > 0 and agents_left > 0:
                if self.rng.random() < immune_remaining / agents_left:
                    immune = True
                    immune_remaining -= 1
            agents_left -= 1

            home = self.rng.choice(
                [z for z in self._room_zones if "Pax_" in z or "Passenger" in z or "Berthing" in z]
                if any("Pax_" in z or "Passenger" in z for z in self._room_zones)
                else self._room_zones
            )
            dining = self.rng.choice(self._dining_zones)
            free = self.rng.choice(self._free_zones)
            work = self.rng.choice(self._free_zones)
            gender = self._assign_gender()
            schedule = list(PASSENGER_SCHEDULE)

            agent = KorkinAgent(
                agent_id=agent_id, role="passenger", immune=immune,
                home_zone=home, dining_zone=dining,
                work_zone=work, free_zone=free, schedule=schedule,
                agent_class="passenger_general", gender=gender,
            )

            if not immune and infected_remaining > 0:
                agent.infection_status = InfectionStatus.INFECTED
                agent.time_infected = 1
                agent.acquired_particles = math.pow(10, SYMPTOMATIC_SHEDDING[1] - DOSE_ADJUSTMENT)
                ill_prob = illness_probability(agent.acquired_particles)
                if self.rng.random() < ill_prob:
                    agent.illness_status = IllnessStatus.SYMPTOMATIC
                infected_remaining -= 1

            self.agents.append(agent)
            agent_id += 1

        # Crew
        for _ in range(self.num_crew):
            immune = False
            if immune_remaining > 0 and agents_left > 0:
                if self.rng.random() < immune_remaining / agents_left:
                    immune = True
                    immune_remaining -= 1
            agents_left -= 1

            home = self.rng.choice(
                [z for z in self._room_zones if "Crew_Corridor" in z or "Crew" in z or "Berthing" in z]
                if any("Crew_Corridor" in z or "Crew" in z for z in self._room_zones)
                else self._room_zones
            )
            dining = self.rng.choice(self._dining_zones)
            free = self.rng.choice(self._free_zones)
            work = self.rng.choice(self._free_zones + self._dining_zones)
            gender = self._assign_gender()
            schedule = list(CREW_SCHEDULE)

            agent = KorkinAgent(
                agent_id=agent_id, role="crew", immune=immune,
                home_zone=home, dining_zone=dining,
                work_zone=work, free_zone=free, schedule=schedule,
                agent_class="crew_general", gender=gender,
            )

            if not immune and infected_remaining > 0:
                agent.infection_status = InfectionStatus.INFECTED
                agent.time_infected = 1
                agent.acquired_particles = math.pow(10, SYMPTOMATIC_SHEDDING[1] - DOSE_ADJUSTMENT)
                ill_prob = illness_probability(agent.acquired_particles)
                if self.rng.random() < ill_prob:
                    agent.illness_status = IllnessStatus.SYMPTOMATIC
                infected_remaining -= 1

            self.agents.append(agent)
            agent_id += 1

        return agent_id

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
            if agent.agent_id in self.quarantined_ids:
                agent.current_location = agent.home_zone
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
                if self.rng.random() < ill_prob:
                    agent.illness_status = IllnessStatus.SYMPTOMATIC

        # 4. Recovery (Person.java: dpi >= 3)
        for agent in self.agents:
            if agent.is_infected and agent.days_post_infection >= RECOVERY_DAY:
                agent.infection_status = InfectionStatus.RECOVERED
                agent.illness_status = IllnessStatus.RECOVERED

        # 5. VSP quarantine check (Agent.java: 3% threshold)
        # VSP confinement sends symptomatic agents to quarters (quarantine),
        # not to isolation units.  Quarantined agents remain HVAC-connected.
        total_pop = len(self.agents)
        total_ill = sum(1 for a in self.agents if a.is_symptomatic)
        vsp_threshold = int(self.vsp_threshold_fraction * total_pop)
        if self.vsp_isolation and total_ill >= vsp_threshold and not self.vsp_triggered:
            self.vsp_triggered = True

        if self.vsp_triggered:
            confined = self.isolated_ids | self.quarantined_ids
            for agent in self.agents:
                if agent.is_symptomatic and agent.agent_id not in confined:
                    self.quarantined_ids.add(agent.agent_id)

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
            per_pathogen = {}
            for pid, masses in self._multi_pathogen_mass.items():
                per_pathogen[pid] = round(masses.get(zname, 0.0), 3)
            spaces_out[zname] = {
                "pathogen_mass": round(self._zone_pathogen_mass.get(zname, 0.0), 3),
                "pathogen_mass_by_id": per_pathogen,
                "microbiome_id": f"profile_{zname.lower()}",
            }
        return {
            "epoch": self.epoch,
            "agents": agents_out,
            "spaces": spaces_out,
        }

    @property
    def zone_pathogen_mass(self) -> dict[str, float]:
        """Read/write access to per-zone pathogen mass for CONTAM transport.

        Returns the aggregate (summed) mass across all pathogens.
        """
        return self._zone_pathogen_mass

    @zone_pathogen_mass.setter
    def zone_pathogen_mass(self, value: dict[str, float]) -> None:
        self._zone_pathogen_mass = value

    @property
    def multi_pathogen_mass(self) -> dict[str, dict[str, float]]:
        """Per-pathogen mass pools: {pathogen_id: {zone: mass}}."""
        return self._multi_pathogen_mass

    @multi_pathogen_mass.setter
    def multi_pathogen_mass(self, value: dict[str, dict[str, float]]) -> None:
        self._multi_pathogen_mass = value

    def initialize_pathogen(self, pathogen_id: str) -> None:
        """Set up zero-mass pools for a new pathogen across all zones."""
        self._multi_pathogen_mass[pathogen_id] = {
            z["name"]: 0.0 for z in self.zones
        }

    def get_pathogen_zone_mass(self, pathogen_id: str) -> dict[str, float]:
        """Get per-zone mass for a specific pathogen."""
        return self._multi_pathogen_mass.get(pathogen_id, {})

    def set_pathogen_zone_mass(
        self, pathogen_id: str, masses: dict[str, float],
    ) -> None:
        """Update per-zone mass for a specific pathogen."""
        self._multi_pathogen_mass[pathogen_id] = masses
        # Recompute aggregate
        self._recompute_aggregate_mass()

    def _recompute_aggregate_mass(self) -> None:
        """Recompute the aggregate zone_pathogen_mass from all pathogens."""
        agg: dict[str, float] = {z["name"]: 0.0 for z in self.zones}
        for pid, masses in self._multi_pathogen_mass.items():
            for zname, mass in masses.items():
                agg[zname] = agg.get(zname, 0.0) + mass
        self._zone_pathogen_mass = agg

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
        quarantined = len(self.quarantined_ids)

        # Agent class breakdown
        class_counts: dict[str, int] = {}
        for a in self.agents:
            class_counts[a.agent_class] = class_counts.get(a.agent_class, 0) + 1

        # Gender breakdown
        gender_counts: dict[str, int] = {}
        for a in self.agents:
            gender_counts[a.gender] = gender_counts.get(a.gender, 0) + 1

        return {
            "epoch": self.epoch,
            "total": total,
            "susceptible": susceptible,
            "infected": infected,
            "symptomatic": symptomatic,
            "recovered": recovered,
            "immune": immune,
            "isolated": isolated,
            "quarantined": quarantined,
            "vsp_triggered": self.vsp_triggered,
            "agent_classes": class_counts,
            "gender_distribution": gender_counts,
        }
