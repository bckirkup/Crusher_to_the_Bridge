"""
engines.infection_dynamics_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python bridge to the Korkin Lab ``infection-dynamics`` ABM.

Faithfully re-implements the core mathematical structures from the Java
source (``NorwalkVirus/Source/CruiseShipModel/``) so that the orchestrator
can initialise the real agent graph at t=0 and advance it each epoch.

Key parameters extracted from the Java source
----------------------------------------------
- **Person.java**: Norwalk shedding curves (log10 copies/g stool, days 0-14),
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
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from engines.sim_clock import LEGACY_CLOCK, LEGACY_EPOCH_DAY, SimClock, crossed_day_boundary
from engines.strain_state import ImmuneRecord, Phenotype

# ── Korkin Lab parameters (from Person.java) ─────────────────────────────

# RT-PCR shedding values: log10(copies per gram of stool), indexed by day
# post-onset.
# Source: "Norwalk Virus Shedding after Experimental Human Infection" Fig 1C/E.
SYMPTOMATIC_SHEDDING = [7.75, 9.0, 11.0, 11.0, 11.0, 10.0, 10.0, 9.5, 9.0, 9.0, 8.0, 8.0, 8.0, 8.0, 8.0]
ASYMPTOMATIC_SHEDDING = [7.75, 9.5, 10.5, 10.0, 9.0, 8.0, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75]
# Preferred physical interpretation: -log10 grams of stool released to the
# environment per epoch. Keep the old name as a compatibility alias.
ENVIRONMENTAL_FAECAL_RELEASE_LOG10_G_PER_EPOCH = 4.0
DOSE_ADJUSTMENT = ENVIRONMENTAL_FAECAL_RELEASE_LOG10_G_PER_EPOCH

# Hand-route absolute load, and the faecal peak it was measured alongside.
# Hand rinses from 6 experimentally infected GI.1 (Norwalk) subjects, 18/71
# samples positive, mean 3.86 log10 genome-equivalent copies per hand.
# Liu et al. 2013, Appl Environ Microbiol 79:7875. Grade B. Origin: Ab.
HAND_LOAD_LOG10_GEC = 3.86
# The faecal-curve peak the hand load is read against, so the hand route
# tracks the curve instead of pinning one absolute load for every genogroup.
# Not a measurement of the hand route: it is the GI.1 peak of the shipped
# curve, and their difference (-7.14 log10 g of stool per hand) is a derived
# bridge no study has measured. Class X (convention). Origin: Sec.
HAND_LOAD_REFERENCE_PEAK_LOG10 = 11.0


def environmental_release_log10_per_day(
    profile: dict[str, Any] | None,
) -> float:
    """Normalizer from the shedding curve's assay unit to released material.

    Key precedence is matrix-neutral first: a respiratory profile releases
    exhaled aerosol, not grams of stool, so it declares
    ``environmental_release_log10_per_day`` and the two enteric names
    remain as aliases for the profiles that measured stool. The returned
    offset applies to a daily amount; the caller converts the resulting
    emission to the epoch through ``SimClock.amount_per_epoch``.
    """
    values = profile or {}
    for key in (
        "environmental_release_log10_per_day",
        "environmental_faecal_release_log10_g_per_epoch",
        "dose_adjustment",
    ):
        if key in values:
            return float(values[key])
    return float(ENVIRONMENTAL_FAECAL_RELEASE_LOG10_G_PER_EPOCH)


def environmental_faecal_release_log10_g_per_epoch(
    profile: dict[str, Any] | None,
) -> float:
    """Enteric-named alias retained for existing call sites."""
    return environmental_release_log10_per_day(profile)

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
VSP_RULE_REPORTED_PASSENGER_CASES = "reported_passenger_cases"
VSP_RULE_INSTANT_PREVALENCE = "instant_prevalence"

# Recovery threshold (from Person.java)
RECOVERY_DAY = 3

# Virtual symptom-onset day used by the legacy fallback path
ONSET_DAY = 1

# Environmental deposition: fraction of shedding that deposits on surfaces
# (ViralParticle.java: particles survive 86400 steps = 1 day). Unsourced
# (class I, register 3.4): no study reports a deposited share of shedding.
# Legacy paths only — a profiled arm deposits through the emesis and
# faecal-release paths instead.
SURFACE_DEPOSITION_FRACTION = 1e-4

# Airborne share of emission for a continuous arm that declares none. The same
# unsourced 1e-4, inherited by the norovirus arm before the field was
# redefined; measured fine shares are [0.76, 0.92] (tranche 27), three to four
# orders away. No active profile reads this: both continuous arms declare
# airborne_emission_fraction and the norovirus arm is emesis-conditioned.
UNSOURCED_AIRBORNE_EMISSION_FRACTION = 1e-4

# Aerosol half-life fallback for the pathogen-agnostic zone-mass path.
# van Doremalen et al., NEJM 2020;382:1564 (SARS-CoV-2 aerosol half-life).
DEFAULT_AIRBORNE_HALF_LIFE_HOURS = 1.1

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

DEFAULT_FOOD_CONTAMINATION_MULTIPLIER: dict[str, float] = {
    "buffet": 3.0,
    "mdr": 1.0,
    "specialty": 0.5,
    "crew_mess": 1.0,
    "galley": 0.5,
}

DEFAULT_AGENT_BEHAVIOR: dict[str, Any] = {
    "dining_rotation_probability": 0.0,
    "free_zone_rotation_probability": 0.0,
    "dining_meal_weights": {
        "breakfast": {"buffet": 0.6, "mdr": 0.3, "specialty": 0.1},
        "lunch": {"buffet": 0.5, "mdr": 0.3, "specialty": 0.2},
        "dinner": {"buffet": 0.2, "mdr": 0.5, "specialty": 0.3},
    },
}

# Passenger leisure access. No zone record on any platform carries an access
# field, so crew-only machinery and service spaces are identified from tokens
# their own name, deck and description already use. Interim measure; the
# durable fix is proposed in docs/proposals/zone_access_attribute_spec.md.
NON_LEISURE_ZONE_TOKENS = (
    "engine", "machinery", "waste", "laundry", "stores", "provision",
    "galley", "bridge", "navigation", "technical",
)


def is_leisure_accessible(zone: dict[str, Any]) -> bool:
    """Return whether a zone is suitable for passenger leisure access."""
    text = " ".join(
        str(zone.get(field, ""))
        for field in ("name", "deck", "description")
    ).lower()
    return not any(token in text for token in NON_LEISURE_ZONE_TOKENS)


def weighted_zone_choice(
    catalog: list[dict[str, Any]], rng: np.random.Generator,
) -> str | None:
    """Draw a zone with probability proportional to its capacity."""
    if not catalog:
        return None
    labels: list[str] = []
    weights: list[float] = []
    for entry in catalog:
        cap = entry.get("max_occupancy")
        try:
            capacity = float(cap) if cap is not None else 100.0
        except (TypeError, ValueError):
            capacity = 100.0
        labels.append(str(entry["name"]))
        weights.append(max(capacity, 1.0))
    total = sum(weights)
    probs = [weight / total for weight in weights]
    return str(rng.choice(labels, p=probs))


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


def shedding_value(day_post_onset: int, is_symptomatic: bool) -> float:
    """Compute shedding as 10^(log10_rate - doseAdjustment).

    Curves are indexed from symptom onset. Clamps to the last day if the
    requested index is past the shedding curve length.
    (Person.java lines 321-332)
    """
    curve = SYMPTOMATIC_SHEDDING if is_symptomatic else ASYMPTOMATIC_SHEDDING
    idx = min(max(day_post_onset, 0), len(curve) - 1)
    return max(1.0, math.pow(10, curve[idx] - DOSE_ADJUSTMENT))


def ever_presented(inf: dict[str, Any]) -> bool:
    """Whether this infection ever presented symptomatically.

    The curve a host emits on is fixed at presentation, not re-chosen each
    epoch: a host whose illness has ended while it is still shedding reads the
    tail of the curve it started on, instead of switching onto the
    asymptomatic curve mid-course. The onset and illness clauses keep records
    built by paths that never set the flag on their original curve.
    """
    return (
        bool(inf.get("presented"))
        or inf.get("onset_time_infected") is not None
        or inf.get("illness") == IllnessStatus.SYMPTOMATIC
    )


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


# ── Co-resident strains ──────────────────────────────────────────────────

@dataclass
class StrainInfection:
    """One lineage residing in one host's infection of one pathogen.

    Same-pathogen co-infection needs a per-lineage clock and inoculum: a strain
    acquired on day four is at the start of its own shedding curve inside a host
    whose infection is four days old, and it clears on its own schedule.
    """

    strain_id: str
    time_infected: int
    acquired_particles: float
    acquired_particles_by_route: dict[str, float] = field(default_factory=dict)
    shedding_multiplier: float = 1.0
    incubation_modifier: float = 0.0
    infection_epoch: int = 0


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
    - secretor_negative_by_pathogen: dict keyed by pathogen_id → bool
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
        "secretor_negative_by_pathogen",
        "dose_response_susceptibility", "cumulative_exposure",
        "cumulative_exposure_by_route",
        "hand_load_by_pathogen", "hand_inactivation_rate_by_pathogen",
        "emesis_episode_schedule_by_pathogen",
        "emesis_episode_load_by_pathogen",
        "emesis_deposition_records_by_pathogen",
        "microflora_disruption_status",
        # Chronic disease extensions
        "chronic_disease_ids", "chronic_pathogen_mods",
        "chronic_wearable_response_scale",
        # Chronic norovirus shedding: per-pathogen duration for hosts drawn as
        # chronic shedders at initialization
        "chronic_shedding_duration_by_pathogen",
        # What the manifest gave this host: vaccination and antiviral status
        "pharma_by_pathogen",
        "shedding_multiplier", "cabin_mate_ids", "ashore",
        # Variant surveillance: genotype standing immunity was raised against
        "prior_genotypes", "immune_history",
        # Host biology read by the incubation distribution
        "age_band", "immunocompromised",
        # Shared epoch/day conversion; every day-valued comparison goes through it
        "clock",
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
        # Host biology conditioning the incubation draw. Populated by the
        # population builders that know it; neutral (no effect) when they don't.
        self.age_band: str = ""
        self.immunocompromised: bool = False
        self.time_infected: int | None = None
        self.acquired_particles: float = 0.0
        # One shared instance per run, assigned by the engine. Legacy by default
        # so an agent built outside a simulation behaves as it always did.
        self.clock: SimClock = LEGACY_CLOCK
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
        # Whether this host drew the secretor-negative (FUT2) phenotype, per
        # pathogen. Kept explicit so host genetics stay inspectable rather than
        # being implicit in a susceptibility float.
        self.secretor_negative_by_pathogen: dict[str, bool] = {}
        # Persistent beta-Poisson host mixing variable, drawn lazily per pathogen.
        self.dose_response_susceptibility: dict[str, float] = {}
        # Effective dose accumulated during the current infection challenge.
        self.cumulative_exposure: dict[str, float] = {}
        # Effective dose accumulated by route during the current challenge.
        self.cumulative_exposure_by_route: dict[str, dict[str, float]] = {}
        # Copies carried on each hand, keyed by pathogen.
        self.hand_load_by_pathogen: dict[str, float] = {}
        # Per-host/pathogen hand inactivation draws, sampled lazily.
        self.hand_inactivation_rate_by_pathogen: dict[str, float] = {}
        # Elapsed days since onset, drawn once for each symptomatic illness.
        self.emesis_episode_schedule_by_pathogen: dict[str, list[float]] = {}
        # Per-episode share of the illness's cumulative emesis shed, drawn with
        # the schedule so nothing is drawn per episode.
        self.emesis_episode_load_by_pathogen: dict[str, float] = {}
        self.emesis_deposition_records_by_pathogen: dict[
            str, list[dict[str, Any]]
        ] = {}

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
        # Chronic shedding duration in days from onset, per pathogen, assigned
        # at initialization to immunocompromised hosts drawn as chronic
        # shedders. Empty for every other host.
        self.chronic_shedding_duration_by_pathogen: dict[str, float] = {}
        # Per-pathogen vaccination and antiviral status drawn from the
        # manifest at initialization. Kept off susceptibility_multiplier's
        # books as a record so a run can report who was covered, not only
        # what their susceptibility ended up being.
        self.pharma_by_pathogen: dict[str, dict[str, Any]] = {}

        # Legacy single-pathogen shedding host factor (also mirrored on first infection)
        self.shedding_multiplier: float = 1.0
        # Cabin-mate agent IDs sharing the same stateroom (mega_cruise_5000)
        self.cabin_mate_ids: frozenset[int] = frozenset()
        # Voyage layer: passenger ashore during port/disembark windows
        self.ashore: bool = False

        # {pathogen_id: genotype} the agent's pre-existing immunity was raised
        # against; empty unless variant surveillance is on
        self.prior_genotypes: dict[str, str] = {}

        # Every resolved exposure, appended as each lineage clears; empty unless
        # variant surveillance is on
        self.immune_history: list[ImmuneRecord] = []

    @property
    def days_post_infection(self) -> int:
        """Days since infection (0-indexed).  -1 if not infected.

        ``time_infected`` counts epochs; this is that count read in days through
        the run's clock, which is the only place the two units meet.
        """
        if self.time_infected is None:
            return -1
        return self.clock.day_index(self.time_infected)

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
        """Active legacy shedding value, with no presymptomatic window.

        The legacy property has no pathogen profile to supply a
        presymptomatic window, so its empty profile intentionally means
        shedding begins at virtual or realized onset.
        """
        if not self.is_infected:
            return 0.0
        if self.time_infected is None:
            return 0.0
        infection = next(iter(self.infections.values()), {})
        days_since_onset, curve_index = self._shedding_age(
            self.time_infected, infection, {}, self.clock,
        )
        if days_since_onset < 0.0:
            return 0.0
        return (
            self.clock.amount_per_epoch(
                shedding_value(curve_index, self.is_symptomatic),
            )
            * self.shedding_multiplier
        )

    def get_location_for_hour(
        self,
        hour: int,
        randomness: float = 0.0,
        *,
        rng: np.random.Generator | None = None,
        dining_catalog: list[dict[str, Any]] | None = None,
        free_catalog: list[dict[str, Any]] | None = None,
        agent_behavior: dict[str, Any] | None = None,
    ) -> str:
        """Determine where this agent should be at the given hour.

        Mirrors Agent.getProjectedDestination() in the Java source.
        Optional dining/free rotation uses engine RNG + zone catalog.
        """
        adjusted_hour = int((hour + randomness + 24.0) % 24.0)
        adjusted_hour %= len(self.schedule)
        activity = self.schedule[adjusted_hour]
        if activity == "Sleep":
            return self.home_zone
        if activity.startswith("Meal"):
            return self._resolve_dining_location(
                activity,
                rng=rng,
                dining_catalog=dining_catalog,
                agent_behavior=agent_behavior,
            )
        if activity == "Free":
            return self._resolve_free_location(
                rng=rng,
                free_catalog=free_catalog,
                agent_behavior=agent_behavior,
            )
        if activity == "Work":
            return self.work_zone
        return self.home_zone

    def _meal_type_for_activity(self, activity: str) -> str:
        if "Breakfast" in activity:
            return "breakfast"
        if "Lunch" in activity:
            return "lunch"
        if "Dinner" in activity:
            return "dinner"
        return "lunch"

    def _resolve_dining_location(
        self,
        activity: str,
        *,
        rng: np.random.Generator | None,
        dining_catalog: list[dict[str, Any]] | None,
        agent_behavior: dict[str, Any] | None,
    ) -> str:
        behavior = agent_behavior or {}
        p_rotate = float(behavior.get("dining_rotation_probability", 0.0) or 0.0)
        # Voyage dining-demand multiplier scales rotation propensity (port lunch drop).
        dining_demand = behavior.get("_voyage_dining_multiplier") or {}
        meal_preview = self._meal_type_for_activity(activity)
        if isinstance(dining_demand, dict) and meal_preview in dining_demand:
            p_rotate *= float(dining_demand[meal_preview])
        elif isinstance(dining_demand, (int, float)):
            p_rotate *= float(dining_demand)
        if (
            rng is None
            or not dining_catalog
            or p_rotate <= 0.0
            or rng.random() >= p_rotate
        ):
            return self.dining_zone

        meal = meal_preview
        meal_weights = (behavior.get("dining_meal_weights") or {}).get(meal) or {}
        # Crew prefer crew_mess venues when rotating.
        if self.role == "crew" and not meal_weights:
            meal_weights = {"crew_mess": 1.0}
        elif self.role == "crew":
            meal_weights = {**meal_weights, "crew_mess": max(
                float(meal_weights.get("crew_mess", 0.0)), 0.5,
            )}

        candidates: list[str] = []
        weights: list[float] = []
        for entry in dining_catalog:
            name = str(entry["name"])
            stype = str(entry.get("service_type") or "mdr")
            # Skip galleys for passenger dining rotation.
            if self.role != "crew" and stype == "galley":
                continue
            cap = entry.get("max_occupancy")
            try:
                capacity = float(cap) if cap is not None else 100.0
            except (TypeError, ValueError):
                capacity = 100.0
            type_w = float(meal_weights.get(stype, 0.0))
            if type_w <= 0.0 and stype not in meal_weights:
                # Unknown service types: small residual weight so rotation works
                type_w = 0.05
            if type_w <= 0.0:
                continue
            candidates.append(name)
            weights.append(max(capacity, 1.0) * type_w)

        if not candidates:
            return self.dining_zone
        total = sum(weights)
        probs = [w / total for w in weights]
        return str(rng.choice(candidates, p=probs))

    def _resolve_free_location(
        self,
        *,
        rng: np.random.Generator | None,
        free_catalog: list[dict[str, Any]] | None,
        agent_behavior: dict[str, Any] | None,
    ) -> str:
        behavior = agent_behavior or {}
        p_rotate = float(behavior.get("free_zone_rotation_probability", 0.0) or 0.0)
        if (
            rng is None
            or not free_catalog
            or p_rotate <= 0.0
            or rng.random() >= p_rotate
        ):
            return self.free_zone
        return weighted_zone_choice(free_catalog, rng) or self.free_zone

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
        strain_id: str | None = None,
        strain_phenotype: Phenotype | None = None,
        acquired_particles_by_route: dict[str, float] | None = None,
    ) -> None:
        """Record co-infection for a specific pathogen.

        ``time_infected`` is the infection's age in **epochs** at assignment;
        the day-valued ``initial_time_infected`` profile field is converted
        through the run's clock by the seeding caller. Transmission events use
        the default 0.

        When ``rng`` and ``profile`` are supplied, draws a persistent
        ``shedding_multiplier`` from ``profile['shedding_variance_log10']``.

        ``strain_id`` is the resident strain when variant surveillance is on,
        and ``None`` otherwise; it is the strain actually acquired, since
        mutation is drawn elsewhere. ``strain_phenotype`` caches that strain's
        heritable effects on the infection record, so the epoch loop and the
        shedding read need no registry of their own.
        """
        if time_infected < 0:
            raise ValueError(f"time_infected must be non-negative, got {time_infected}")
        self.emesis_episode_schedule_by_pathogen.pop(pathogen_id, None)
        self.emesis_episode_load_by_pathogen.pop(pathogen_id, None)
        self.emesis_deposition_records_by_pathogen.pop(pathogen_id, None)
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
            "acquired_particles_by_route": dict(acquired_particles_by_route or {}),
            "infection_epoch": epoch,
            "shedding_multiplier": shedding_mult,
        }
        # A chronic shedder carries its own infectious period, so the record
        # states the duration this host will shed for and the clearance seam
        # reads the record before the profile.
        chronic_days = self.get_chronic_shedding_duration(pathogen_id)
        if chronic_days is not None:
            self.infections[pathogen_id]["shedding_duration_days"] = chronic_days
        if strain_id is not None:
            self._write_strain(pathogen_id, strain_id, strain_phenotype)
        # The agent-level fields follow the records: any episode that starts
        # while they show no active infection reopens them, so a second episode
        # is visible in the legacy channel instead of being hidden behind the
        # first one's RECOVERED.
        if self.infection_status != InfectionStatus.INFECTED:
            self.infection_status = InfectionStatus.INFECTED
            self.illness_status = IllnessStatus.NOT_ILL
            self.time_infected = time_infected
            self.acquired_particles = dose
            self.shedding_multiplier = shedding_mult

    def superinfect_with_strain(
        self,
        pathogen_id: str,
        strain_id: str,
        dose: float,
        epoch: int,
        *,
        phenotype: Phenotype | None = None,
        acquired_particles_by_route: dict[str, float] | None = None,
    ) -> bool:
        """Add a co-resident strain to an existing infection of one pathogen.

        The host's illness clock, cumulative dose, and pathogen-level status are
        already running and are left alone: superinfection adds a lineage, it
        does not restart the infection. A strain already resident simply takes
        on the extra inoculum, which is what reinfection by the same lineage
        amounts to. Returns True when a new lineage established.
        """
        residents = self.resident_strains(pathogen_id)
        if not residents:
            return False
        resident = residents.get(strain_id)
        if resident is not None:
            resident.acquired_particles += dose
            return False
        pheno = phenotype or Phenotype()
        residents[strain_id] = StrainInfection(
            strain_id=strain_id,
            time_infected=0,
            acquired_particles=dose,
            acquired_particles_by_route=dict(acquired_particles_by_route or {}),
            shedding_multiplier=pheno.shedding_multiplier,
            incubation_modifier=pheno.incubation_modifier,
            infection_epoch=epoch,
        )
        return True

    def resident_strains(self, pathogen_id: str) -> dict[str, StrainInfection]:
        """Lineages co-residing in an active infection, keyed by strain id.

        Empty for an untracked infection, which is how a consumer tells one
        unnamed infection from one named lineage.
        """
        inf = self.infections.get(pathogen_id)
        if inf is None or inf["status"] != InfectionStatus.INFECTED:
            return {}
        residents = inf.get("strains")
        return residents if isinstance(residents, dict) else {}

    def advance_resident_strains(
        self,
        pathogen_id: str,
        shedding_clearance_day: float,
        cleared: list[str] | None = None,
    ) -> int:
        """Age each resident lineage by an epoch and clear those done shedding.

        The threshold is the host's total infectious course in days:
        incubation/onset plus the shedding duration, which outlasts the illness
        whenever the profile says it does. The lineage counter is in epochs,
        and the run's clock converts between them. Returns the number still
        resident, so the caller can hold the pathogen-level infection open
        until the last lineage clears. Ids of the lineages that cleared this
        call are appended to ``cleared`` when given, since each one is an
        exposure the host now has immune memory of.
        """
        residents = self.resident_strains(pathogen_id)
        for strain_id, resident in tuple(residents.items()):
            resident.time_infected += 1
            if (
                self.clock.days_elapsed(resident.time_infected)
                >= shedding_clearance_day
            ):
                del residents[strain_id]
                if cleared is not None:
                    cleared.append(strain_id)
        if residents:
            self._promote_primary_strain(pathogen_id, residents)
        return len(residents)

    def _promote_primary_strain(
        self,
        pathogen_id: str,
        residents: dict[str, StrainInfection],
    ) -> None:
        """Hand the pathogen-level strain fields to a surviving lineage.

        The primary lineage can clear while a later superinfecting one is still
        resident, and the pathogen-level record has to keep naming something
        that is actually there. The longest-resident survivor takes over.
        """
        inf = self.infections[pathogen_id]
        if inf.get("strain_id") in residents:
            return
        heir = min(residents.values(), key=lambda r: r.infection_epoch)
        inf["strain_id"] = heir.strain_id
        inf["strain_shedding_multiplier"] = heir.shedding_multiplier
        inf["strain_incubation_modifier"] = heir.incubation_modifier

    def is_infected_with(self, pathogen_id: str) -> bool:
        """Check if agent is infected with a specific pathogen."""
        inf = self.infections.get(pathogen_id)
        if inf is None:
            return False
        return inf["status"] == InfectionStatus.INFECTED

    def record_immunity(self, record: ImmuneRecord) -> None:
        """Remember one resolved exposure.

        A repeat of a genotype already recorded is still appended: exposure count
        and timing are what a serology or reinfection analysis reads, and
        protection is computed over the distinct genotypes anyway.
        """
        self.immune_history.append(record)

    def immune_genotypes(self, pathogen_id: str) -> tuple[str, ...]:
        """Distinct genotypes this host has immune memory of, in first-seen order."""
        seen: dict[str, None] = {}
        for record in self.immune_history:
            if record.pathogen_id == pathogen_id and record.genotype:
                seen.setdefault(record.genotype, None)
        return tuple(seen)

    def strain_id_for(self, pathogen_id: str) -> str | None:
        """Primary strain of an infection, or ``None`` if untracked.

        The primary lineage is the one that started (or now carries) this
        infection; ``resident_strains`` is the co-infection-aware view.
        """
        inf = self.infections.get(pathogen_id)
        if inf is None:
            return None
        strain_id = inf.get("strain_id")
        return None if strain_id is None else str(strain_id)

    def assign_strain(
        self,
        pathogen_id: str,
        strain_id: str,
        phenotype: Phenotype | None = None,
    ) -> None:
        """Attach a strain, and its heritable effects, to an infection record.

        Used for seeded infections, which are created before any strain exists,
        and after a within-host mutation replaces the resident strain.
        """
        if pathogen_id not in self.infections:
            raise KeyError(f"agent {self.agent_id} has no {pathogen_id} infection")
        self._write_strain(pathogen_id, strain_id, phenotype)

    def replace_strain(
        self,
        pathogen_id: str,
        old_strain_id: str,
        new_strain_id: str,
        phenotype: Phenotype | None = None,
    ) -> None:
        """Substitute one resident lineage for its descendant, clock intact.

        A within-host mutation happens inside an infection already under way, so
        the resident's day post-infection and inoculum carry over to the child
        instead of resetting.
        """
        residents = self.resident_strains(pathogen_id)
        resident = residents.pop(old_strain_id, None)
        if resident is None:
            return
        pheno = phenotype or Phenotype()
        residents[new_strain_id] = StrainInfection(
            strain_id=new_strain_id,
            time_infected=resident.time_infected,
            acquired_particles=resident.acquired_particles,
            acquired_particles_by_route=dict(resident.acquired_particles_by_route),
            shedding_multiplier=pheno.shedding_multiplier,
            incubation_modifier=pheno.incubation_modifier,
            infection_epoch=resident.infection_epoch,
        )
        inf = self.infections[pathogen_id]
        if inf.get("strain_id") == old_strain_id:
            inf["strain_id"] = new_strain_id
            inf["strain_shedding_multiplier"] = pheno.shedding_multiplier
            inf["strain_incubation_modifier"] = pheno.incubation_modifier

    def _write_strain(
        self,
        pathogen_id: str,
        strain_id: str,
        phenotype: Phenotype | None,
    ) -> None:
        """Record a strain plus the phenotype axes read outside transmission.

        The pathogen-level fields describe the *primary* lineage — the one whose
        arrival started this infection — since illness onset belongs to the
        infection rather than to whatever superinfects it on day four.
        """
        pheno = phenotype or Phenotype()
        inf = self.infections[pathogen_id]
        inf["strain_id"] = strain_id
        inf["strain_shedding_multiplier"] = pheno.shedding_multiplier
        inf["strain_incubation_modifier"] = pheno.incubation_modifier
        inf["strains"] = {strain_id: StrainInfection(
            strain_id=strain_id,
            time_infected=int(inf["time_infected"] or 0),
            acquired_particles=float(inf["acquired_particles"]),
            acquired_particles_by_route=dict(
                inf.get("acquired_particles_by_route", {}),
            ),
            shedding_multiplier=pheno.shedding_multiplier,
            incubation_modifier=pheno.incubation_modifier,
            infection_epoch=int(inf["infection_epoch"]),
        )}

    def get_pathogen_shedding(self, pathogen_id: str, profile: dict) -> float:
        """Shedding value for a specific pathogen based on its profile."""
        inf = self.infections.get(pathogen_id)
        if inf is None or inf["status"] != InfectionStatus.INFECTED:
            return 0.0
        epochs_infected = inf["time_infected"]
        if epochs_infected is None or epochs_infected < 0:
            return 0.0
        is_symp = ever_presented(inf)
        curve = profile.get(
            "shedding_curve_log10",
            SYMPTOMATIC_SHEDDING if is_symp else ASYMPTOMATIC_SHEDDING,
        )
        if not is_symp:
            curve = profile.get("asymptomatic_shedding_log10", curve)
        adj = environmental_release_log10_per_day(profile)
        host_mult = inf.get("shedding_multiplier", 1.0)
        residents = self.resident_strains(pathogen_id)
        if residents:
            # Each lineage starts its own onset-anchored curve at acquisition;
            # the host-level illness clock remains on the primary infection.
            return host_mult * sum(
                self._resident_emissions(
                    residents, curve, adj, self.clock, profile,
                ).values(),
            )
        # Host factor (per-agent log-normal draw) and strain factor (heritable)
        # compose multiplicatively and are kept apart so a high shedder stays
        # attributable to the host or to the lineage, not to both at once.
        days_since_onset, curve_index = self._shedding_age(
            epochs_infected, inf, profile, self.clock,
        )
        if days_since_onset < -float(profile.get("presymptomatic_shedding_days", 0.0)):
            return 0.0
        idx = min(max(curve_index, 0), len(curve) - 1)
        return self.clock.amount_per_epoch(
            math.pow(10, curve[idx] - adj)
            * host_mult
            * inf.get("strain_shedding_multiplier", 1.0),
        )

    def get_pathogen_hand_target(
        self,
        pathogen_id: str,
        profile: dict[str, Any],
    ) -> float:
        """Return the measured stool-linked target load for one hand."""
        inf = self.infections.get(pathogen_id)
        if inf is None or inf["status"] != InfectionStatus.INFECTED:
            return 0.0
        epochs_infected = inf.get("time_infected")
        if epochs_infected is None or epochs_infected < 0:
            return 0.0
        symptomatic = ever_presented(inf)
        curve = profile.get(
            "shedding_curve_log10",
            SYMPTOMATIC_SHEDDING if symptomatic else ASYMPTOMATIC_SHEDDING,
        )
        if not symptomatic:
            curve = profile.get("asymptomatic_shedding_log10", curve)
        days_since_onset, curve_index = self._shedding_age(
            epochs_infected, inf, profile, self.clock,
        )
        if days_since_onset < -float(
            profile.get("presymptomatic_shedding_days", 0.0),
        ):
            return 0.0
        idx = min(max(curve_index, 0), len(curve) - 1)
        return (
            math.pow(10.0, HAND_LOAD_LOG10_GEC)
            * math.pow(10.0, curve[idx] - HAND_LOAD_REFERENCE_PEAK_LOG10)
            * float(inf.get("shedding_multiplier", 1.0))
        )

    def strain_shedding_shares(
        self, pathogen_id: str, profile: dict,
    ) -> dict[str, float]:
        """Fraction of this host's emission owed to each resident lineage.

        Empty when nothing is co-resident, so callers can keep their
        single-strain path. Shares are what attributes an onward transmission to
        one of the lineages a co-infected host is carrying.
        """
        residents = self.resident_strains(pathogen_id)
        if len(residents) < 2:
            return {}
        inf = self.infections[pathogen_id]
        is_symp = ever_presented(inf)
        curve = profile.get(
            "shedding_curve_log10",
            SYMPTOMATIC_SHEDDING if is_symp else ASYMPTOMATIC_SHEDDING,
        )
        if not is_symp:
            curve = profile.get("asymptomatic_shedding_log10", curve)
        adj = environmental_release_log10_per_day(profile)
        emissions = self._resident_emissions(
            residents, curve, adj, self.clock, profile,
        )
        total = sum(emissions.values())
        if total <= 0.0:
            return {}
        return {sid: value / total for sid, value in emissions.items()}

    @staticmethod
    def _resident_emissions(
        residents: dict[str, StrainInfection],
        curve: list[float],
        adj: float,
        clock: SimClock,
        profile: dict,
    ) -> dict[str, float]:
        """Emission of each co-resident lineage, before the host factor.

        Lineages partition one host's shedding capacity in proportion to the
        inoculum that established them — co-infection redistributes emission
        rather than multiplying it, so two strains in one host do not out-shed
        the same host carrying one. Each is read on its own acquisition-
        anchored onset curve and scaled by its heritable factor, which is what
        lets a fitter or
        later-arriving strain take over the mix.
        """
        inocula = {
            sid: max(resident.acquired_particles, 0.0)
            for sid, resident in residents.items()
        }
        pool = sum(inocula.values())
        emissions: dict[str, float] = {}
        for sid, resident in residents.items():
            share = inocula[sid] / pool if pool > 0.0 else 1.0 / len(residents)
            days_since_onset, curve_index = KorkinAgent._shedding_age(
                resident.time_infected, {}, profile, clock,
            )
            if days_since_onset < -float(
                profile.get("presymptomatic_shedding_days", 0.0),
            ):
                continue
            idx = min(max(curve_index, 0), len(curve) - 1)
            emissions[sid] = (
                clock.amount_per_epoch(
                    share
                    * math.pow(10, curve[idx] - adj)
                    * resident.shedding_multiplier,
                )
            )
        return emissions

    @staticmethod
    def _shedding_age(
        epochs_infected: int,
        inf: dict[str, Any],
        profile: dict,
        clock: SimClock,
    ) -> tuple[float, int]:
        """Return elapsed days since onset and the day-curve index.

        Shedding curves are authored on the onset axis.  A realized onset is
        preferred; an unpresented infection uses its drawn incubation as a
        virtual onset, and legacy profiles use their configured onset day.
        """
        onset_time = inf.get("onset_time_infected")
        if onset_time is not None:
            elapsed_epochs = max(0, epochs_infected - int(onset_time))
            return (
                clock.days_elapsed(elapsed_epochs),
                clock.day_index(elapsed_epochs),
            )
        incubation_days = inf.get("incubation_days")
        if incubation_days is not None:
            days_since_onset = clock.days_elapsed(epochs_infected) - float(
                incubation_days,
            )
            return days_since_onset, math.floor(days_since_onset)
        onset_day = float(profile.get("symptom_onset_day", ONSET_DAY))
        days_since_onset = clock.days_elapsed(epochs_infected) - onset_day
        return (
            days_since_onset,
            math.floor(days_since_onset),
        )

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

    def set_chronic_shedding_duration(
        self, pathogen_id: str, days: float,
    ) -> None:
        """Record this host's chronic shedding duration in days from onset."""
        self.chronic_shedding_duration_by_pathogen[pathogen_id] = float(days)

    def get_chronic_shedding_duration(self, pathogen_id: str) -> float | None:
        """Return the host's chronic shedding duration, or None if not chronic.

        A chronic shedder's infectious period is a host property assigned at
        initialization, so it overrides the profile's population shedding
        duration for this host alone.
        """
        return self.chronic_shedding_duration_by_pathogen.get(pathogen_id)

    @property
    def has_chronic_disease(self) -> bool:
        return len(self.chronic_disease_ids) > 0

    def _symptom_days(self, inf: dict[str, Any]) -> int | None:
        """Return 1-based symptom days, or ``None`` when onset is unknown.

        This differs from the 0-based ``days_post_infection`` value, so the
        fields must not be compared as an ordering invariant.
        """
        time_infected = inf.get("time_infected")
        onset_time = inf.get("onset_time_infected")
        if time_infected is None or onset_time is None:
            return None
        elapsed = max(0, int(time_infected) - int(onset_time))
        return self.clock.day_index(elapsed) + 1

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
                "pathogen_id": pid,
                "status": inf["status"].name,
                "illness": inf["illness"].name,
                "days_post_infection": (
                    None if inf["time_infected"] is None
                    else self.clock.day_index(inf["time_infected"])
                ),
                "days_since_symptom_onset": self._symptom_days(inf),
                "symptom_severity": inf.get("symptom_severity", ""),
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

    Initialises the agent graph from the real model parameters and advances the
    simulation one epoch at a time. How much natural history an epoch buys is
    the ``clock``'s business, not this class's: see ``engines.sim_clock``.
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
        agent_behavior: dict[str, Any] | None = None,
        clock: SimClock | None = None,
        vsp_trigger_rule: str = VSP_RULE_REPORTED_PASSENGER_CASES,
    ) -> None:
        if vsp_trigger_rule not in {
            VSP_RULE_REPORTED_PASSENGER_CASES,
            VSP_RULE_INSTANT_PREVALENCE,
        }:
            raise ValueError(f"Unknown VSP trigger rule: {vsp_trigger_rule!r}")
        self.rng = np.random.default_rng(seed)
        self.clock = clock or LEGACY_CLOCK
        self.zones = zones or DEFAULT_ZONES
        self.num_passengers = num_passengers
        self.num_crew = num_crew
        self.initial_infected = initial_infected
        self.immune_ratio = immune_ratio
        self.vsp_isolation = vsp_isolation
        self.vsp_trigger_rule = vsp_trigger_rule
        self._agent_classes = agent_classes
        self._gender_distribution = gender_distribution or DEFAULT_GENDER_DISTRIBUTION
        self.vsp_threshold_fraction: float = VSP_THRESHOLD_FRACTION
        self.vsp_reported_case_fraction: float = 0.0
        behavior = dict(DEFAULT_AGENT_BEHAVIOR)
        if agent_behavior:
            behavior.update({
                k: v for k, v in agent_behavior.items()
                if k != "dining_meal_weights"
            })
            if "dining_meal_weights" in agent_behavior:
                merged_meals = dict(DEFAULT_AGENT_BEHAVIOR["dining_meal_weights"])
                for meal, weights in (agent_behavior["dining_meal_weights"] or {}).items():
                    merged_meals[meal] = {
                        **(merged_meals.get(meal) or {}),
                        **(weights or {}),
                    }
                behavior["dining_meal_weights"] = merged_meals
        self.agent_behavior = behavior
        # Per-epoch voyage EpochState (set by orchestrator when effects active)
        self.voyage_epoch_state: Any = None

        self._dining_zones = [z["name"] for z in self.zones if z["type"] == "Dining"]
        self._free_zones = [z["name"] for z in self.zones if z["type"] == "Free"]
        self._leisure_catalog: list[dict[str, Any]] = [
            {"name": z["name"], "max_occupancy": z.get("max_occupancy")}
            for z in self.zones
            if z.get("type") == "Free" and is_leisure_accessible(z)
        ]
        if not self._leisure_catalog:
            self._leisure_catalog = [
                {"name": z["name"], "max_occupancy": z.get("max_occupancy")}
                for z in self.zones
                if z.get("type") == "Free"
            ]
        self._room_zones = [
            z["name"] for z in self.zones
            if z["type"] in ("Room", "Cabin_Corridor")
        ]
        self._all_zone_names = [z["name"] for z in self.zones]
        self._dining_catalog: list[dict[str, Any]] = []
        for z in self.zones:
            if z.get("type") != "Dining":
                continue
            stype = str(z.get("dining_service_type") or "")
            if not stype:
                name = str(z["name"]).lower()
                if "galley" in name:
                    stype = "galley"
                elif "mess" in name:
                    stype = "crew_mess"
                elif any(x in name for x in ("buffet", "lido", "windjammer", "grill", "cafe")):
                    stype = "buffet"
                elif "spec" in name:
                    stype = "specialty"
                else:
                    stype = "mdr"
            self._dining_catalog.append({
                "name": z["name"],
                "service_type": stype,
                "max_occupancy": z.get("max_occupancy"),
                "food_contamination_multiplier": z.get(
                    "food_contamination_multiplier",
                ),
            })

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

        for agent in self.agents:
            agent.clock = self.clock

    @property
    def _seed_infection_epochs(self) -> int:
        """Epochs of infection age an index case is seeded with.

        Index cases start one day into the fallback onset clock, at the head
        of the shedding curve, which is one epoch only when an epoch is a day.
        """
        return max(1, int(round(self.clock.epochs_for_days(1.0))))

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
                if free_pref
                else weighted_zone_choice(self._leisure_catalog, self.rng) or "unknown"
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

    def _seed_initial_infection(
        self, agent: KorkinAgent, rng: np.random.Generator,
    ) -> None:
        agent.infection_status = InfectionStatus.INFECTED
        agent.time_infected = self._seed_infection_epochs
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
            free = weighted_zone_choice(self._leisure_catalog, self.rng) or "unknown"
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
                agent.time_infected = self._seed_infection_epochs
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
            free = weighted_zone_choice(self._leisure_catalog, self.rng) or "unknown"
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
                agent.time_infected = self._seed_infection_epochs
                agent.acquired_particles = math.pow(10, SYMPTOMATIC_SHEDDING[1] - DOSE_ADJUSTMENT)
                ill_prob = illness_probability(agent.acquired_particles)
                if self.rng.random() < ill_prob:
                    agent.illness_status = IllnessStatus.SYMPTOMATIC
                infected_remaining -= 1

            self.agents.append(agent)
            agent_id += 1

        return agent_id

    def _advance_illness_and_recovery(self) -> None:
        """Age every infection one epoch, then present and recover on days.

        ``time_infected`` is an epoch count; ``ONSET_DAY`` and ``RECOVERY_DAY``
        are days, with recovery measured from onset, so the total course is
        incubation plus ``RECOVERY_DAY``. The clock is the only thing that
        relates those units. The illness draw fires once per day of natural
        history rather than once per epoch, so a finer grid does not hand a
        host more chances to present.

        A host carrying per-pathogen records has its natural history owned by
        those records, not by this fallback: they hold the drawn incubation
        period, the profile's own dose response and recovery day, and the
        strain's modifiers. Only the epoch counter is advanced for such a host,
        since the shedding read and the payload still read it.
        """
        for agent in self.agents:
            if not agent.is_infected:
                continue
            if agent.time_infected is not None:
                agent.time_infected += 1
            if agent.infections:
                continue
            self._draw_fallback_onset(agent)

        for agent in self.agents:
            if agent.infections:
                continue
            if (
                agent.is_infected
                and agent.days_post_infection >= ONSET_DAY + RECOVERY_DAY
            ):
                agent.infection_status = InfectionStatus.RECOVERED
                agent.illness_status = IllnessStatus.RECOVERED
                agent.hand_load_by_pathogen.clear()

    def _draw_fallback_onset(self, agent: KorkinAgent) -> None:
        """Present a host that has no per-pathogen record, on the fixed day."""
        if agent.illness_status != IllnessStatus.NOT_ILL:
            return
        if not crossed_day_boundary(self.clock, agent.time_infected or 0, ONSET_DAY):
            return
        ill_prob = illness_probability(agent.acquired_particles)
        if self.rng.random() < ill_prob:
            agent.illness_status = IllnessStatus.SYMPTOMATIC

    def step(self) -> dict[str, Any]:
        """Advance the simulation by one epoch.

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

        # The legacy clock intentionally retains its historical midday lookup.
        hour = self.clock.hour_of_day(self.epoch)

        from engines.voyage_itinerary import (
            LOCATION_ASHORE,
            apply_ashore_and_embarkation,
            apply_embarkation_surge_locations,
        )

        voyage_state = self.voyage_epoch_state
        if voyage_state is not None:
            apply_ashore_and_embarkation(
                self.agents,
                voyage_state,
                rng=self.rng,
                dining_catalog=self._dining_catalog,
            )
            behavior = dict(self.agent_behavior)
            if getattr(voyage_state, "effects_active", False):
                behavior["_voyage_dining_multiplier"] = dict(
                    voyage_state.dining_multiplier or {},
                )
            else:
                behavior.pop("_voyage_dining_multiplier", None)
        else:
            behavior = self.agent_behavior

        # 1. Update agent locations
        for agent in self.agents:
            if getattr(agent, "ashore", False):
                agent.current_location = LOCATION_ASHORE
                continue
            if agent.agent_id in self.isolated_ids:
                agent.current_location = "Isolated_In_Quarters"
                continue
            if agent.agent_id in self.quarantined_ids:
                agent.current_location = agent.home_zone
                continue
            randomness = self.rng.uniform(-1.0, 1.0)
            if self.clock.mode != LEGACY_EPOCH_DAY:
                randomness = 0.0
            agent.current_location = agent.get_location_for_hour(
                hour,
                randomness,
                rng=self.rng,
                dining_catalog=self._dining_catalog,
                free_catalog=self._leisure_catalog,
                agent_behavior=behavior,
            )

        if voyage_state is not None:
            apply_embarkation_surge_locations(
                self.agents,
                voyage_state,
                rng=self.rng,
                dining_catalog=self._dining_catalog,
            )

        # 2. Infection transmission
        # When TransmissionCore is active (_external_transmission=True),
        # this step is skipped — the orchestrator calls TransmissionCore
        # which handles all four pathways (direct, droplet, HVAC, fomite).
        if not self._external_transmission:
            zone_occupants: dict[str, list[KorkinAgent]] = {z: [] for z in self._all_zone_names}
            zone_occupants["Isolated_In_Quarters"] = []
            zone_occupants[LOCATION_ASHORE] = []
            for agent in self.agents:
                loc = agent.current_location
                if loc in zone_occupants:
                    zone_occupants[loc].append(agent)

            for zone_name, occupants in zone_occupants.items():
                if zone_name in ("Isolated_In_Quarters", LOCATION_ASHORE):
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

        # 3-4. Illness progression and recovery, both on the day scale
        self._advance_illness_and_recovery()

        # 5. VSP quarantine check
        self._check_vsp_trigger()

        # 6. Zone pathogen mass: new deposits from shedders
        # NOTE: Decay is now handled externally by the CONTAM transport
        # engine (py_contam_bridge) when available.  If no transport engine
        # is configured, the orchestrator falls back to the legacy flat
        # fallback airborne survival when external transport is disabled.
        if not self._external_transport:
            for zname in self._all_zone_names:
                self._zone_pathogen_mass[zname] *= (
                    self.clock.survival_from_half_life(
                        DEFAULT_AIRBORNE_HALF_LIFE_HOURS,
                    )
                )

        for agent in self.agents:
            if agent.is_infected and agent.current_shedding > 0:
                loc = agent.current_location
                if loc in self._zone_pathogen_mass:
                    deposited = agent.current_shedding * SURFACE_DEPOSITION_FRACTION
                    self._zone_pathogen_mass[loc] += deposited

        # 7. Export payload
        return self._export_payload()

    def _check_vsp_trigger(self) -> None:
        """Apply the VSP trigger and quarantine symptomatic agents.

        The reported-case fraction is cumulative reported passenger cases
        divided by the passenger complement, as specified by equation
        ``vsp-trigger`` in ``docs/reports/05_vsp.tex``.  It is one epoch stale
        by construction because sick calls for epoch *t* are generated in the
        surveillance phase after biology; that reporting lag is realistic.
        The default is reported passenger cases because the instantaneous
        prevalence form is unreachable at hourly resolution.
        """
        if self.vsp_trigger_rule == VSP_RULE_REPORTED_PASSENGER_CASES:
            threshold_reached = (
                self.vsp_reported_case_fraction >= self.vsp_threshold_fraction
            )
        else:
            total_pop = len(self.agents)
            total_ill = sum(1 for a in self.agents if a.is_symptomatic)
            vsp_threshold = int(self.vsp_threshold_fraction * total_pop)
            threshold_reached = total_ill >= vsp_threshold
        if self.vsp_isolation and threshold_reached and not self.vsp_triggered:
            self.vsp_triggered = True

        if self.vsp_triggered:
            confined = self.isolated_ids | self.quarantined_ids
            for agent in self.agents:
                if agent.is_symptomatic and agent.agent_id not in confined:
                    self.quarantined_ids.add(agent.agent_id)

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
            "vsp_triggered": self.vsp_triggered,
            "vsp_reported_case_fraction": self.vsp_reported_case_fraction,
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
            "vsp_reported_case_fraction": self.vsp_reported_case_fraction,
            "agent_classes": class_counts,
            "gender_distribution": gender_counts,
        }
