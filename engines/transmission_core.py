"""
engines.transmission_core
~~~~~~~~~~~~~~~~~~~~~~~~~

Four-pathway transmission model for the Crusher-to-the-Bridge digital twin.

Pathogens navigate the shipboard environment through four distinct,
independent transport pathways, each with its own dose contribution
and contact-tracing signature:

1. **Direct Contact** — stochastic person-to-person transmission when
   an infectious and susceptible agent share the same room node,
   scaled by the room's vicinity density (avgR).

2. **Short-Range Droplet** — immediate aerosolization within the shared
   room.  Large droplets settle quickly; fine aerosols remain suspended
   in the room's airborne mass pool.

3. **Long-Range Airborne (HVAC Drift)** — the py-contam bridge reads
   the suspended aerosol pools and drifts a fraction through ductwork
   to downstream room nodes via ``air_flow_paths.json``.

4. **Fomite Deposition & Surface Touch** — pathogen mass from air and
   direct shedding deposits onto fixed surface pools.  Agents entering
   later have a stochastic probability of picking up surface mass,
   carrying it on their FRED schedule.

Each pathway produces:
- A **dose contribution** to susceptible agents
- A **contact-tracing record** for the surveillance inference hook

The combined dose from all pathways feeds the dose-response function:
- **Beta-Poisson**: ``P(inf) = 1 - (1 + dose/β)^{-α}``
- **Exponential**: ``P(inf) = 1 - exp(-k * dose)``
"""

from __future__ import annotations

import fnmatch
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from crusher_labs.clinical_presentation import resolve_phase
from engines.infection_dynamics_bridge import (
    ALPHA,
    BETA,
    DEFAULT_AIRBORNE_HALF_LIFE_HOURS,
    SURFACE_DEPOSITION_FRACTION,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import LEGACY_EPOCH_DAY, SimClock
from engines.strain_dose_ledger import (
    UNRESOLVED_STRAIN,
    Contributor,
    DoseAttribution,
    EmissionContribution,
    EmissionMix,
    ReservoirComposition,
    StrainDoseLedger,
    attribution,
    build_emission_mix,
    draw_contributor,
)
from engines.strain_mutation import MutationOperator
from engines.strain_state import (
    IMMUNITY_AT_EMBARKATION,
    IMMUNITY_FROM_INFECTION,
    ImmuneRecord,
    Phenotype,
    StrainEvolutionConfig,
    StrainRegistry,
    StrainState,
)

# ── Pathway-specific parameters ──────────────────────────────────────────

# Fraction of total shedding that becomes immediate room-level aerosol
DROPLET_AEROSOL_FRACTION = 0.05

# ICRP-style adult daily inhaled air volume, converted through SimClock.
BREATHING_RATE_M3_PER_DAY = 14.4

# Hand-transfer distributions and contact frequencies from the authored
# fomite rederivation specification.
HAND_AREA_CM2_RANGE = (445.0, 535.0)
SURFACE_CONTACT_FRACTION_RANGE = (0.008, 0.25)
MOUTH_CONTACT_FRACTION_RANGE = (0.008, 0.012)
# Surface -> hand transfer efficiency (pickup direction). Drying is a weak
# lever here: 2-11% off a dried donor surface (Sharps 2012, via fomite), and
# 2.0 +/- 2.0% from stainless steel (Tuladhar 2013).
SURFACE_TO_HAND_LOGNORMAL = (-2.1, 1.4)
# Hand -> surface transfer efficiency (deposit direction). Identical numbers to
# the pickup distribution, split out because they are two different measured
# quantities and the drying lever differs sharply between them: hand -> surface
# falls from 13% to 0.1% after 10 minutes of drying (Tuladhar 2013) and from
# 59% to below 1% (Sharps 2012), a ~100x lever that has no counterpart on the
# pickup side. The shipped distribution is a *wet-contact* parameterisation,
# defensible against Tuladhar's immediate 13% and Bidawid's 13%; reusing it for
# a dried donor hand would be about 100x too high.
HAND_TO_SURFACE_LOGNORMAL = (-2.1, 1.4)
# Drying-state multiplier on the deposit direction only. Neutral by default, so
# it reproduces the shipped arithmetic exactly and consumes no RNG; the sourced
# axis it opens is screened, not asserted (see bounded_screen.py).
HAND_TO_SURFACE_DRYING_MULTIPLIER = 1.0
HAND_TO_MOUTH_NORMAL = (0.339, 0.132)
HAND_INACTIVATION_RATE_PER_HOUR_RANGE = (0.61, 1.7)
HAND_HYGIENE_EFFICACY_LOG10 = (1.06, 0.54, 0.0, 1.89)
HAND_HYGIENE_RATE_PER_HOUR_DEFAULT = 0.0
NON_EATING_MOUTH_CONTACTS_PER_HOUR = (2.9, 2.5)
EATING_MOUTH_CONTACTS_PER_HOUR = (7.7, 4.1)
# Measured shared-surface touch rates, contacts per hour. These are
# public/shared-surface rates, not all-surface rates: the studies separate
# touches of one's own belongings from touches of shared fomites, and only the
# latter drive fomite transmission.
SURFACE_CONTACTS_PER_HOUR = {
    # University dormitory primary shared surfaces, 10.4-25.4/h; midpoint.
    # Yuan et al. 2024, Building and Environment. Grade B.
    "cabin": 17.9,
    # Hotel lobby, 627 touches by 324 people over 30 h.
    # Ackerley et al. 2023/2025. Grade B, and the only hospitality field study.
    "public": 21.0,
    # Restaurant diners, public-surface contacts. Jin et al. 2022, IJID
    # (a norovirus surface-transmission study). Grade B.
    "dining": 42.8,
    # Restaurant staff, public-surface contacts. Jin et al. 2022. Grade B.
    "galley": 545.4,
    # Crew eating; diner rate applies to the eater, not the server.
    "crew_mess": 42.8,
}
# Same restaurant, same study, same hour: staff touch shared surfaces 12.7x
# more than diners do. Touch rate is a property of the activity, not only of
# the room, so crew working a service zone take the staff rate.
CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR = 545.4
HIGH_TOUCH_AREA_M2 = {
    "cabin": 1.5,
    "dining": 8.0,
    "public": 6.0,
    "galley": 10.0,
    "crew_mess": 4.0,
}

# Fraction of high-touch objects actually cleaned in a daily housekeeping
# pass. Covert fluorescent-marker audit of 8,344 objects in 273 public
# restrooms on 56 cruise ships: 37% cleaned daily (range 4-100%, 95% CI
# 29.2-45.4%). Carling et al. 2009, Clin Infect Dis 49:1312. Direct
# measurement of this quantity in this setting. Grade A.
ROUTINE_CLEANING_COVERAGE = 0.37

# Log10 reduction of norovirus on a hard surface per cleaning event, over the
# objects actually cleaned. Midpoint of the two definition-matched
# measurements: 1.0 for a single liquid-soap or 250-ppm-chlorine wipe of
# hNoV on stainless steel (Tuladhar et al. 2012, lab carrier test) and 1.57
# for targeted hygiene wipes and sprays measured with a viral tracer in a
# hotel lobby (Spitzer et al. 2025, Int J Hyg Environ Health 267:114586 —
# field, hospitality). Midpoint of the two, stated as such. Grade B.
ROUTINE_CLEANING_LOG10_REDUCTION = 1.29

# Housekeeping passes per day. One pass is the denominator of Carling's
# "cleaned on a daily basis". Grade B.
ROUTINE_CLEANING_EVENTS_PER_DAY = 1.0

# Log10 reduction of the hypochlorite step of outbreak-response disinfection.
# 5,000 ppm sodium hypochlorite on a fecally soiled stainless steel surface
# reduces norovirus surrogates by 3 log10 at >=3 min contact (Park et al.
# 2011, Foodborne Pathog Dis 8:1005); 1,000-5,000 ppm for 60 s gives 2.5-3.1
# log10 GEC on soiled steel (Escudero-Abarca et al. 2022, J Appl Microbiol).
# Grade B.
OUTBREAK_DISINFECTION_STEP_LOG10_REDUCTION = 3.0

# Outbreak response is a two-step procedure: detergent preclean, then
# hypochlorite (Dancer 2014; Park et al. 2011 both recommend precleaning to
# drop the organic load first). The field reports two-step efficacy additively
# in log10, and that additivity is an assumption, not a measurement. Grade C.
OUTBREAK_DISINFECTION_LOG10_REDUCTION = (
    ROUTINE_CLEANING_LOG10_REDUCTION + OUTBREAK_DISINFECTION_STEP_LOG10_REDUCTION
)

# Fraction of high-touch objects reached by an outbreak-response pass. Not
# measured on ships. The only measured effect of supervision and feedback on
# cleaning thoroughness is 34% -> 53% in two hospitals (Murphy et al. 2011,
# Healthcare Infection, fluorescent marker), a relative factor of 1.56, which
# applied to Carling's 37% baseline gives 0.58. Inferred across settings, and
# it must be swept rather than asserted. Grade C.
OUTBREAK_CLEANING_COVERAGE = 0.58
# Per-subject cumulative emesis shed, drawn log-uniform once per symptomatic
# illness. Kirby et al. 2016, PLoS ONE, Table 3, per-subject cumulative shed in
# vomitus: GII.2 Snow Mountain mean 1.8e7 GEC (SEM 1.8e7), GI.1 2.3e8, with the
# per-subject values spanning roughly 1e5-1e8. Grade B: surrogate genotype, as
# no GII.4 emesis measurement exists (docs/literature/consensus_tranche_4.md
# section 3).
#
# This is the quantity the paper identifies, and it replaces the former
# volume x titre product. Titre and volume are not independent of the total:
# the measured GII.2 sample-mean titre (1.6e5 GEC/mL) times the measured mean
# total volume (845 mL) is 1.35e8, 7.5x the same paper's measured per-subject
# cumulative 1.8e7, because the titre mean is taken over positive samples on a
# heavy right tail. Adopting titre and volume as independent inputs therefore
# overstates emission by an order of magnitude while looking like provenance.
#
# The endpoints are set by this arithmetic check, not by tuning: the arithmetic
# mean of a log-uniform on [1e5, 1e8] is (1e8 - 1e5) / ln(1e3) = 1.45e7, within
# 1.25x of Kirby's measured GII.2 per-subject mean of 1.8e7. The interval
# reproduces the measured mean rather than being fitted to any anchor.
EMESIS_TOTAL_SHED_GEC_RANGE = (1e5, 1e8)
# Emesis titre is deliberately absent: no profile key resolves to one, and the
# emesis record carries titre as a derived diagnostic, episode_load /
# volume_ml. The withdrawn figure is recorded in
# docs/norovirus/norovirus_open_ledger.md.
# Vomitus volume from Tung-Thompson et al. 2015 and Booth & Frost 2019;
# measured range, evidence grade B. Still drawn per episode, but it no longer
# multiplies a titre to make the emitted load: with the per-subject total
# identified, volume is only the physical volume of the deposit, carried on the
# record for the deposition geometry and for any concentration-based check.
EMESIS_VOLUME_ML_RANGE = (50.0, 800.0)
# Emesis events per subject, 1-7 with mode 1 (Kirby et al. 2016, Tables 2-3);
# measured count, evidence grade B. With the per-illness total identified, the
# episode count only partitions and times that same total -- it no longer
# scales emission -- which is why correcting the former (1, 3) is safe.
EMESIS_EPISODES_RANGE = (1, 7)
# Aerosol fraction from Tung-Thompson et al. 2015 surrogate measurements;
# evidence grade B.
EMESIS_AEROSOL_FRACTION_RANGE = (7.2e-7, 2.67e-4)
# Forward/lateral deposition footprint from Booth 2014 and Booth & Frost 2019;
# measured geometry, evidence grade B.
EMESIS_DEPOSITION_AREA_M2 = 7.8


def draw_emesis_schedule(
    agent: Any,
    pathogen_id: str,
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> None:
    """Draw onset-relative emesis times and the illness total, once.

    The per-subject cumulative shed is the identified quantity, so it is drawn
    once here and partitioned equally over the episodes drawn with it; nothing
    is drawn per episode at emission time.
    """
    if not hasattr(agent, "emesis_episode_schedule_by_pathogen"):
        return
    phases = profile.get("clinical_presentation", {}).get("phases", [])
    emetic_phases = [
        phase for phase in phases if "vomiting" in phase.get("features", [])
    ]
    if not emetic_phases:
        agent.emesis_episode_schedule_by_pathogen[pathogen_id] = []
        agent.emesis_episode_load_by_pathogen[pathogen_id] = 0.0
        return
    bounds = [
        (
            float(phase.get("dpi_min", 0)),
            float(phase["dpi_max"]) + 1.0
            if phase.get("dpi_max") is not None
            else float(profile.get("recovery_day", 3)),
        )
        for phase in emetic_phases
    ]
    window_start = min(start for start, _ in bounds)
    window_end = max(end for _, end in bounds)
    low, high = profile.get("emesis_episodes_range", EMESIS_EPISODES_RANGE)
    count = int(rng.integers(int(low), int(high) + 1))
    schedule = rng.uniform(window_start, window_end, count)
    agent.emesis_episode_schedule_by_pathogen[pathogen_id] = sorted(
        float(age) for age in schedule
    )
    total_low, total_high = profile.get(
        "emesis_total_shed_gec_range", EMESIS_TOTAL_SHED_GEC_RANGE,
    )
    total_shed = math.exp(rng.uniform(
        math.log(float(total_low)), math.log(float(total_high)),
    ))
    agent.emesis_episode_load_by_pathogen[pathogen_id] = (
        total_shed / max(1, count)
    )


# Deprecated names retained for import compatibility. The measured hand
# transfer chain above no longer uses these lumped factors.
FOMITE_PICKUP_PROBABILITY = 0.10
FOMITE_TRANSFER_FRACTION = 0.01
DECK_HEIGHT_M = 2.5
FOMITE_CONTACT_AREA_M2 = 2e-4

# Default surface decay rate, in the log10-per-day unit every source measures.
DEFAULT_SURFACE_DECAY_LOG10_PER_DAY = 0.301030


def surface_fraction_per_day(log10_per_day: float) -> float:
    """Convert a measured log10 reduction per day to the fractional daily loss the clock consumes."""
    return 1.0 - math.pow(10.0, -float(log10_per_day))

# R0-calibrated contact pool (from Person.java avgR array) — legacy contact_mode
AVG_R_POOL = [1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2]
# Mean daily contacts, POLYMOD 8-country diary study (Mossong et al. 2008,
# PLoS Med). Supersedes the avgR pool inherited from Korkin's Person.java.
POLYMOD_CONTACTS_PER_DAY = 13.4

# Defaults for density_dependent contact_mode (partial overrides merge onto these)
DEFAULT_DENSITY_CFG: dict[str, float] = {
    "reference_occupancy": 50.0,
    "base_contacts_per_day": POLYMOD_CONTACTS_PER_DAY,
    "max_contacts_per_day": 40.0,
    "exponent": 0.5,
    "crew_contact_multiplier": 2.0,
}
DEFAULT_CONTACT_MODE = "per_partner_contact"

# Per-route dose efficiency multipliers (identity default → no change when
# absent). These are independent per-route multipliers, not normalised shares:
# the one pathogen with a measured per-portal ratio (influenza, intranasal vs
# aerosol ID50) differs by orders of magnitude between routes, so a set of
# shares cannot represent route efficiency. They neither do nor need to sum
# to 1.
DEFAULT_ROUTE_EFFICIENCY: dict[str, float] = {
    "direct_contact": 1.0,
    "droplet": 1.0,
    "hvac_airborne": 1.0,
    "fomite": 1.0,
    "food_contamination": 1.0,
    "environmental_source": 1.0,
}
# Deprecated alias, kept for external readers.
DEFAULT_ROUTE_WEIGHTS = DEFAULT_ROUTE_EFFICIENCY

# Internal pathway dose keys → route_efficiency_multipliers keys
PATHWAY_EFFICIENCY_KEYS: dict[str, str] = {
    "direct_contact": "direct_contact",
    "droplet": "droplet",
    "hvac_airborne": "hvac_airborne",
    "fomite": "fomite",
    "food": "food_contamination",
    "environmental": "environmental_source",
}
# Deprecated alias, kept for external readers.
PATHWAY_WEIGHT_KEYS = PATHWAY_EFFICIENCY_KEYS


def route_efficiency_from_clearance_rates(
    rates_per_hour: dict[str, float],
    reference_route: str,
) -> dict[str, float]:
    """Route efficiency multipliers implied by per-route clearance rates.

    Inoculum retained at portal *j* and cleared at ``lambda_j`` accrues total
    hazard proportional to ``D_j / lambda_j``, so per-virion efficiency goes as
    the mean residence time ``1 / lambda_j``. A dose-response is fitted to
    inoculum administered at one portal, and every loss upstream of that portal
    is already inside its constants, so that portal is the reference:
    ``lambda_reference / lambda_j``, identically 1.0 on the reference route. Any
    other reference multiplies every route by one constant, which the dose scale
    absorbs.

    This is the only route by which a clearance rate enters the model. Route
    efficiency has one owning field, ``route_efficiency_multipliers``; a
    clearance layer standing beside it would parameterise the same quantity
    twice and neither would be identifiable, so profiles declaring one are
    refused at load. Which portal an exposure route terminates at is a claim
    about the pathogen and not a default: ``reference_route`` is required, and
    only the routes supplied are returned.
    """
    if reference_route not in DEFAULT_ROUTE_EFFICIENCY:
        raise ValueError(
            f"reference_route {reference_route!r} is not a transmission route; "
            f"expected one of {sorted(DEFAULT_ROUTE_EFFICIENCY)}",
        )
    rates: dict[str, float] = {}
    for route, rate in rates_per_hour.items():
        if route not in DEFAULT_ROUTE_EFFICIENCY:
            raise ValueError(
                f"clearance rate given for unknown route {route!r}; "
                f"expected one of {sorted(DEFAULT_ROUTE_EFFICIENCY)}",
            )
        value = float(rate)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(
                f"clearance rate for {route!r} must be finite and positive, "
                f"got {rate!r}: a zero rate is an infinite residence time",
            )
        rates[route] = value
    reference = rates.get(reference_route)
    if reference is None:
        raise ValueError(
            f"no clearance rate given for the reference route "
            f"{reference_route!r}; without it the multipliers have no scale",
        )
    return {route: reference / rate for route, rate in rates.items()}


# Log-sigma defaults for heterogeneous_zone_dose (mean-1 lognormal).
# Low in cabins (near-uniform stateroom mixing); high in dining/service;
# medium-high in free/common areas. Not the default contact_mode.
DEFAULT_HETEROGENEOUS_SIGMA_BY_ZONE_TYPE: dict[str, float] = {
    "Cabin_Corridor": 0.25,  # low
    "Dining": 1.0,           # high
    "Free": 0.75,            # medium-high
    "Room": 0.5,
    "Medical": 0.5,
    "Engineering": 0.5,
}
DEFAULT_HETEROGENEOUS_SIGMA_SERVICE = 1.0  # Galley / service (high)
DEFAULT_HETEROGENEOUS_SIGMA_DEFAULT = 0.75
CONTACT_MODES = frozenset({
    "legacy",
    "density_dependent",
    "heterogeneous_zone_dose",
    "per_partner_contact",
})


# ── Data structures ─────────────────────────────────────────────────────

@dataclass
class TransmissionEvent:
    """A single transmission event across any pathway.

    ``source_agent_id`` and ``source_strain_id`` are populated only when strain
    attribution is active and the winning contribution came from a pathway that
    knows its shedder; reservoir pathways name a strain but no source agent.
    """
    epoch: int
    pathway: str  # "direct_contact" | "droplet" | "hvac_airborne" | "fomite"
    source_agent_id: int | None
    target_agent_id: int
    zone: str
    dose: float
    source_strain_id: str | None = None
    acquired_particles_by_route: dict[str, float] = field(default_factory=dict)


@dataclass
class ExposureRecord:
    """Per-agent exposure record for the contact-tracing matrix."""
    agent_id: int
    zone: str
    pathway: str
    dose: float
    source_agents: list[int] = field(default_factory=list)
    source_zone: str | None = None


@dataclass
class ContactTracingMatrix:
    """Per-epoch contact-tracing matrix for surveillance inference."""
    epoch: int
    # Pathway 1: Who shared a room with whom
    shared_room_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 2: Short-range droplet exposures within rooms
    droplet_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 3: HVAC downstream — who entered a room receiving air from
    # a room that had a shedding agent
    hvac_downstream_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 4: Fomite trailing — who entered a room after an infectious
    # agent left, contacting contaminated surfaces
    fomite_trailing_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 5: Food contamination — ingestion dose from contaminated
    # food in Dining-type zones
    food_contamination_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 6: Environmental source — dose from HVAC-colonized pathogen
    # (e.g. Legionella biofilm) independent of infected agents
    environmental_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Actual infection events across all pathways
    transmission_events: list[dict[str, Any]] = field(default_factory=list)
    # Epoch x zone occupancy / contact summary (surfaces zone_occupants map)
    zone_contact_summary: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "shared_room_exposures": self.shared_room_exposures,
            "droplet_exposures": self.droplet_exposures,
            "hvac_downstream_exposures": self.hvac_downstream_exposures,
            "fomite_trailing_exposures": self.fomite_trailing_exposures,
            "food_contamination_exposures": self.food_contamination_exposures,
            "environmental_exposures": self.environmental_exposures,
            "transmission_events": self.transmission_events,
            "zone_contact_summary": self.zone_contact_summary,
        }


# ── Four-pathway transmission engine ────────────────────────────────────

# Balcony cabins: outdoor air dilution reduces aerosol exposure (PLATFORM_CABIN_REVISION)
BALCONY_AEROSOL_REDUCTION = 0.5

# Default confinement isolation for quarantined agents in cabin corridors
DEFAULT_CONFINEMENT_ISOLATION_FACTOR = 0.05

# Direct contact between confined agent and non-cabin-mate (closed door)
NON_MATE_CONFINEMENT_CONTACT_FACTOR = 0.01

# Hallway encounter rate vs well-mixed ward (Cabin_Corridor zones)
DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR = 0.15

# Share of a shedding host's emission deposited into food pools in Dining-type
# zones. A share of an emission, not a rate: the emission it multiplies is
# already the epoch's amount (``get_pathogen_shedding`` returns
# ``amount_per_epoch``), so this fraction is dimensionless and the deposit is
# grid-invariant without conversion. Converting it a second time through a
# clock helper would divide the deposit by the epochs in a day.
# Open on provenance: the emission it takes a share of is total faecal
# shedding, with no distinction between formed stool and diarrhoeal liquid
# during the symptomatic window, and no gut-transit lag between ingestion and
# shedding; a sourced value would have to say which of those it measured.
# No source: declared assumption. Grade C. Origin: n/a.
FOOD_DEPOSITION_FRACTION_OF_EMISSION = 1e-4

# Fraction of a food pool's standing pathogen mass ingested per agent per day.
# A fractional removal from a stock, so it compounds within a day and is read
# to the epoch through ``SimClock.decay_per_epoch``. The unit is declared here,
# not the shape: a constant fraction is continuous grazing, not sized meals at
# set hours, and the value is not a measurement of either.
# No source: declared assumption. Grade C. Origin: n/a.
FOOD_INGESTION_FRACTION_PER_DAY = 0.05

# Fraction of the standing environmental load delivered to a zone per day.
# Delivery does not deplete the load, so a day's flux divides linearly across
# the day's epochs: read through ``SimClock.amount_per_epoch``.
# No source: declared assumption. Grade C. Origin: n/a.
ENV_DELIVERY_FRACTION_PER_DAY = 0.01

# Share of a shedding host's emission entering a zone-scoped environmental
# reservoir (spore shedding into a spa or ward). Applied only under variant
# surveillance, since it adds a host input the scalar reservoir never had.
# A share of an already per-epoch emission, like the food deposition share,
# so it is dimensionless and takes no clock conversion.
# No source: declared assumption. Grade C. Origin: n/a.
ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION = 1e-4

# Reservoir kinds tracked by the strain composition shadow of the pools
SURFACE_RESERVOIR = "surface"
FOOD_RESERVOIR = "food"
AIRBORNE_RESERVOIR = "air"
ENV_RESERVOIR = "env"

# Zone stand-in for the ship-wide (HVAC-systemic) environmental reservoir
SHIP_WIDE_ZONE = "_ship"

# Pool mass at or under which a contributor counts as gone from a reservoir
POOL_EXTINCTION_MASS = 1e-12


def _best_protection(
    config: StrainEvolutionConfig,
    priors: Mapping[str, float | None],
    challenge: StrainState,
) -> float:
    """Protection the best-matched prior exposure gives against a challenge.

    The maximum over the host's immune history rather than a sum: repeated
    exposure to related genotypes does not stack past what the closest match
    already gives, and a host that has met the challenge genotype itself is
    protected as if its heterologous exposures had not happened.

    Each prior carries its own age in days of natural history (``None`` for a
    lineage still resident), so a fresh exposure and a year-old one to the same
    genotype are not the same immunity.
    """
    return max(
        config.waned_protection(prior, challenge, age)
        for prior, age in priors.items()
    )


def _nonspecific_protection(
    config: StrainEvolutionConfig,
    priors: Mapping[str, float | None],
) -> float:
    """Protection a host has against a challenge it cannot even name.

    Only the refractory window counts: it is a genotype-blind post-resolution
    refractoriness, so it applies to unlabeled dose exactly as it applies to a
    named lineage, while the matched ``cross_immunity`` value cannot — there is
    no genotype to match. Passing a matched value of zero makes the waning
    kernel return the window inside it and decay to zero after it, so unlabeled
    dose outside the window stays unprotected as it was.

    A prior with no resolution age (a resident lineage, or an embarkation prior
    of unknown date) has no window and contributes nothing here.
    """
    return max(
        (
            config.immune_waning.protection_at(0.0, age, 0.0)
            for age in priors.values() if age is not None
        ),
        default=0.0,
    )


def _parse_contact_mode(tx: dict[str, Any]) -> str:
    mode = str(tx.get("contact_mode", DEFAULT_CONTACT_MODE))
    if mode not in CONTACT_MODES:
        return DEFAULT_CONTACT_MODE
    return mode


def _parse_density_cfg(tx: dict[str, Any]) -> dict[str, float]:
    provided = tx.get("density_dependent") or {}
    if not isinstance(provided, dict):
        provided = {}
    aliases = {
        "base_contacts": "base_contacts_per_day",
        "max_contacts": "max_contacts_per_day",
    }
    normalized = {aliases.get(k, k): v for k, v in provided.items()}
    return {
        **DEFAULT_DENSITY_CFG,
        **{
            k: float(v)
            for k, v in normalized.items()
            if k in DEFAULT_DENSITY_CFG
        },
    }


def _parse_heterogeneous_sigma(
    tx: dict[str, Any],
) -> tuple[dict[str, float], float, float]:
    het_raw = tx.get("heterogeneous_zone_dose") or {}
    if not isinstance(het_raw, dict):
        het_raw = {}
    sigma_map = dict(DEFAULT_HETEROGENEOUS_SIGMA_BY_ZONE_TYPE)
    provided_sigma = het_raw.get("sigma_by_zone_type") or {}
    if isinstance(provided_sigma, dict):
        for k, v in provided_sigma.items():
            sigma_map[str(k)] = float(v)
    sigma_service = float(
        het_raw.get("sigma_service", DEFAULT_HETEROGENEOUS_SIGMA_SERVICE),
    )
    sigma_default = float(
        het_raw.get("default_sigma", DEFAULT_HETEROGENEOUS_SIGMA_DEFAULT),
    )
    return sigma_map, sigma_service, sigma_default


def _parse_surface_cleaning_cfg(
    tx: dict[str, Any],
) -> dict[str, Any]:
    """Resolve surface-cleaning settings, retaining module defaults."""
    cleaning = tx.get("surface_cleaning", {})
    if cleaning is None:
        cleaning = {}
    if not isinstance(cleaning, Mapping):
        raise ValueError("transmission.surface_cleaning must be a mapping")
    routine = cleaning.get("routine", {})
    if routine is None:
        routine = {}
    outbreak = cleaning.get("outbreak_response", {})
    if outbreak is None:
        outbreak = {}
    if not isinstance(routine, Mapping):
        raise ValueError("surface_cleaning.routine must be a mapping")
    if not isinstance(outbreak, Mapping):
        raise ValueError("surface_cleaning.outbreak_response must be a mapping")
    routine_coverage, routine_events, routine_log10_reduction = (
        _parse_routine_cleaning_scalars(routine)
    )
    return {
        "enabled": bool(cleaning.get("enabled", True)),
        "routine_coverage": routine_coverage,
        "routine_log10_reduction": routine_log10_reduction,
        "routine_events_per_day": routine_events,
        "routine_by_zone_class": _parse_routine_by_zone_class(
            routine.get("by_zone_class", {}),
            routine_coverage,
            routine_events,
        ),
        "outbreak_coverage": float(
            outbreak.get("coverage", OUTBREAK_CLEANING_COVERAGE),
        ),
        "outbreak_log10_reduction": float(
            outbreak.get(
                "log10_reduction", OUTBREAK_DISINFECTION_LOG10_REDUCTION,
            ),
        ),
    }


def _parse_routine_cleaning_scalars(
    routine: Mapping[str, Any],
) -> tuple[float, float, float]:
    """Parse and validate global routine-cleaning values."""
    routine_coverage = float(
        routine.get("coverage", ROUTINE_CLEANING_COVERAGE),
    )
    routine_events = float(
        routine.get("events_per_day", ROUTINE_CLEANING_EVENTS_PER_DAY),
    )
    if not 0.0 <= routine_coverage <= 1.0:
        raise ValueError("surface_cleaning.routine.coverage must be in [0,1]")
    if routine_events < 0.0:
        raise ValueError("surface_cleaning.routine.events_per_day must be >= 0")
    routine_log10_reduction = float(
        routine.get(
            "log10_reduction", ROUTINE_CLEANING_LOG10_REDUCTION,
        ),
    )
    if routine_log10_reduction < 0.0:
        raise ValueError(
            "surface_cleaning.routine.log10_reduction must be >= 0",
        )
    return routine_coverage, routine_events, routine_log10_reduction


def _parse_routine_by_zone_class(
    raw: Any,
    routine_coverage: float,
    routine_events: float,
) -> dict[str, dict[str, float]]:
    """Parse optional per-zone routine-cleaning overrides."""
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ValueError("surface_cleaning.routine.by_zone_class must be a mapping")
    by_zone_class: dict[str, dict[str, float]] = {}
    for zone_class, values in raw.items():
        if zone_class not in HIGH_TOUCH_AREA_M2:
            raise ValueError(
                f"unknown surface-cleaning zone class: {zone_class}",
            )
        if not isinstance(values, Mapping):
            raise ValueError(
                f"surface_cleaning.routine.by_zone_class.{zone_class} "
                "must be a mapping",
            )
        unknown_fields = set(values) - {"coverage", "events_per_day"}
        if unknown_fields:
            raise ValueError(
                f"unknown fields in surface-cleaning zone class "
                f"{zone_class}: {sorted(unknown_fields)}",
            )
        coverage = float(values.get("coverage", routine_coverage))
        events = float(values.get("events_per_day", routine_events))
        if not 0.0 <= coverage <= 1.0:
            raise ValueError(
                f"surface_cleaning.routine.by_zone_class.{zone_class}."
                "coverage must be in [0,1]",
            )
        if events < 0.0:
            raise ValueError(
                f"surface_cleaning.routine.by_zone_class.{zone_class}."
                "events_per_day must be >= 0",
            )
        by_zone_class[zone_class] = {
            "coverage": coverage,
            "events_per_day": events,
        }
    return by_zone_class


class TransmissionCore:
    """Executes six transmission pathways per epoch.

    Pathways 1–4 are the original four-pathway model.  Pathway 5 (food
    contamination) and pathway 6 (environmental source) extend coverage
    to enteric foodborne and environmentally-colonised pathogens.

    Parameters
    ----------
    rng : np.random.Generator
        Shared RNG for reproducibility.
    zone_volumes : dict
        Zone name → volume in m³ (from spatial_layout.json).
    pathogen_profiles : dict, optional
        Pathogen ID → profile dict (from active_profiles.json).
    zone_types : dict, optional
        Zone name → type string (from spatial_layout.json).
    """

    def __init__(
        self,
        rng: np.random.Generator,
        zone_volumes: dict[str, float] | None = None,
        pathogen_profiles: dict[str, dict] | None = None,
        zone_types: dict[str, str] | None = None,
        zone_ventilation: dict[str, str] | None = None,
        confinement_isolation_factor: float = DEFAULT_CONFINEMENT_ISOLATION_FACTOR,
        corridor_direct_contact_factor: float = DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR,
        cfg: dict[str, Any] | None = None,
        food_zone_multipliers: dict[str, float] | None = None,
        strain_registry: StrainRegistry | None = None,
        clock: SimClock | None = None,
    ) -> None:
        self.rng = rng
        # The run's one clock, so an immunity parameter written in days of
        # natural history is aged on the same grid the biology advances on.
        self.clock = clock if clock is not None else SimClock.from_config(cfg)
        self.inhaled_air_volume_m3_per_epoch = self.clock.amount_per_epoch(
            BREATHING_RATE_M3_PER_DAY,
        )
        # Two pool fractions read off a standing mass rather than off an
        # emission, so each needs the conversion its own kinetics implies:
        # ingestion removes a share of the pool and compounds, while delivery
        # is a flux out of an undepleted load and divides.
        self.food_ingestion_fraction_per_epoch = self.clock.decay_per_epoch(
            FOOD_INGESTION_FRACTION_PER_DAY,
        )
        self.env_delivery_fraction_per_epoch = self.clock.amount_per_epoch(
            ENV_DELIVERY_FRACTION_PER_DAY,
        )
        self.zone_volumes = zone_volumes or {}
        self.pathogen_profiles = pathogen_profiles or {}
        self.zone_types = zone_types or {}
        self.zone_ventilation = zone_ventilation or {}
        self.confinement_isolation_factor = confinement_isolation_factor
        self.corridor_direct_contact_factor = corridor_direct_contact_factor
        self.food_zone_multipliers = food_zone_multipliers or {}
        self._quarantined_ids: set[int] = set()
        # Voyage layer contact scale (1.0 when effects disabled)
        self.voyage_contact_multiplier: float = 1.0

        tx = (cfg or {}).get("transmission", {}) or {}
        self.contact_mode = _parse_contact_mode(tx)
        self.density_cfg: dict[str, float] = _parse_density_cfg(tx)
        cleaning_cfg = _parse_surface_cleaning_cfg(tx)
        self.surface_cleaning_enabled = bool(cleaning_cfg["enabled"])
        self.routine_cleaning_coverage = float(cleaning_cfg["routine_coverage"])
        self.routine_cleaning_log10_reduction = float(
            cleaning_cfg["routine_log10_reduction"],
        )
        self.routine_cleaning_events_per_day = float(
            cleaning_cfg["routine_events_per_day"],
        )
        self.routine_cleaning_by_zone_class: dict[str, dict[str, float]] = (
            cleaning_cfg["routine_by_zone_class"]
        )
        self.outbreak_cleaning_coverage = float(
            cleaning_cfg["outbreak_coverage"],
        )
        self.outbreak_cleaning_log10_reduction = float(
            cleaning_cfg["outbreak_log10_reduction"],
        )
        # Dining-type zones or Galley IDs: crew contact multiplier applies here
        self._service_zones: set[str] = {
            z
            for z, t in self.zone_types.items()
            if t == "Dining" or "Galley" in z
        }
        (
            self.heterogeneous_sigma_by_zone_type,
            self.heterogeneous_sigma_service,
            self.heterogeneous_sigma_default,
        ) = _parse_heterogeneous_sigma(tx)

        # Persistent state: surface fomite pools per zone per pathogen
        # {pathogen_id: {zone: mass}}
        self.surface_pools: dict[str, float] = {}  # aggregate (legacy)
        self.surface_pools_by_pathogen: dict[str, dict[str, float]] = {}
        self.surface_pools_cleanable_by_pathogen: dict[str, dict[str, float]] = {}
        self._routine_cleaning_accumulators: dict[str, float] = {}
        self._routine_cleaning_event_counts: dict[str, int] = {}
        self._surface_last_deposition_epoch: dict[str, int] = {}

        # Persistent state: airborne aerosol pools per zone per pathogen
        self.aerosol_pools: dict[str, float] = {}  # aggregate (legacy)
        self.aerosol_pools_by_pathogen: dict[str, dict[str, float]] = {}
        self.emesis_aerosol_pending_by_pathogen: dict[str, dict[str, float]] = {}

        # Pathway 5: food contamination pools per Dining zone per pathogen
        self.food_pools: dict[str, dict[str, float]] = {}

        # Pathway 6: environmental contamination load per pathogen
        self.environmental_load: dict[str, float] = {}
        # Zone-scoped environmental reservoirs {pid: {zone: mass}}
        self.env_contamination: dict[str, dict[str, float]] = {}

        # Previous epoch's zone occupancy (for fomite trailing detection)
        self._prev_zone_occupants: dict[str, set[int]] = {}

        # Previous epoch's zone shedders per pathogen
        self._prev_zone_shedders: dict[str, list[int]] = {}
        self._prev_zone_shedders_by_pathogen: dict[str, dict[str, list[int]]] = {}
        # Per-epoch route cache, initialized before any direct helper call.
        self._last_pathogen_route_doses: dict[str, dict[int, dict[str, float]]] = {}

        self._init_strain_tracking(cfg, strain_registry)

        # Protocol-driven pathway scalars (1.0 = no modification)
        self.direct_contact_scalar: float = 1.0
        self.droplet_scalar: float = 1.0
        self.hvac_airborne_scalar: float = 1.0

    # ── Strain attribution (variant surveillance) ────────────────────

    def _init_strain_tracking(
        self,
        cfg: dict[str, Any] | None,
        strain_registry: StrainRegistry | None,
    ) -> None:
        """Set up the strain-resolved dose ledger when the flag is on.

        With ``variant_surveillance.enabled`` false there is no registry, every
        attribution hook short-circuits, and no RNG draw is added — so a run is
        bit-identical to the pre-strain engine.
        """
        vs = (cfg or {}).get("variant_surveillance", {}) or {}
        enabled = bool(vs.get("enabled", False))
        self.strain_registry: StrainRegistry | None = strain_registry or (
            StrainRegistry() if enabled else None
        )
        self.strain_configs: dict[str, StrainEvolutionConfig] = {}
        if self.strain_registry is not None:
            for pid, profile in self.pathogen_profiles.items():
                config = self._strain_config_for_profile(pid, profile)
                if config is not None:
                    self.strain_configs[pid] = config
        self.mutation_operator: MutationOperator | None = (
            MutationOperator(self.strain_registry, self.strain_configs)
            if self.strain_registry is not None
            else None
        )
        # Strain composition of the lagged pools (air, surfaces, food, environment)
        self._reservoir = ReservoirComposition()
        # Founder strain of each pathogen's environmental reservoir
        self._env_strain_ids: dict[str, str] = {}
        # Per-epoch strain-resolved dose: {agent: {pathogen: {contributor: dose}}}
        self._strain_doses: dict[int, dict[str, dict[Contributor, float]]] = {}
        self._last_pathogen_doses: dict[int, dict[str, float]] = {}
        self._last_pathogen_route_doses: dict[
            str, dict[int, dict[str, float]]
        ] = {}

    def _strain_config_for_profile(
        self,
        pathogen_id: str,
        profile: dict[str, Any],
    ) -> StrainEvolutionConfig | None:
        config = StrainEvolutionConfig.from_profile(
            {**profile, "pathogen_id": pathogen_id},
        )
        if config is None:
            return None
        raw = profile.get("strain_evolution", {})
        if (
            "within_host_mutation_rate_per_day" in raw
            or "within_host_mutation_rate" in raw
        ):
            config = replace(
                config,
                within_host_mutation_rate=self.clock.probability_per_epoch(
                    config.within_host_mutation_rate,
                ),
            )
        if "recombination_rate_per_day" in raw or "recombination_rate" in raw:
            config = replace(
                config,
                recombination_rate=self.clock.probability_per_epoch(
                    config.recombination_rate,
                ),
            )
        return config

    @property
    def strain_tracking(self) -> bool:
        """True when doses are attributed to strains."""
        return self.strain_registry is not None

    def _transmissibility(self, strain_id: str) -> float:
        if self.strain_registry is None or strain_id == UNRESOLVED_STRAIN:
            return 1.0
        return self.strain_registry.get(strain_id).transmissibility_multiplier

    def _phenotype(self, strain_id: str | None) -> Phenotype | None:
        """Heritable effects of a strain, cached onto the infection record.

        The shedding and incubation axes are read outside transmission (by the
        shedding curve and the epoch's illness draw), so they travel with the
        infection rather than requiring those call sites to hold a registry.
        """
        if self.strain_registry is None or not strain_id:
            return None
        return Phenotype.of(self.strain_registry.get(strain_id))

    def _founder_genotype(self, pathogen_id: str) -> str:
        """Draw a founder genotype from the pathogen's prior distribution."""
        config = self.strain_configs.get(pathogen_id)
        if config is None or not config.prior_genotype_distribution:
            return ""
        genotypes = tuple(config.prior_genotype_distribution)
        probs = [config.prior_genotype_distribution[g] for g in genotypes]
        return str(self.rng.choice(genotypes, p=probs))

    def _resident_strain_id(self, agent: KorkinAgent, pathogen_id: str) -> str | None:
        """Strain an agent is shedding, minting a founder for seeded infections.

        Seeded and pre-existing infections predate any strain, so the first time
        one is used as a source it is assigned a founder lineage — which is also
        how the introduced-diversity regime gets its diversity.
        """
        if self.strain_registry is None or pathogen_id == "_default":
            return None
        strain_id = agent.strain_id_for(pathogen_id)
        if strain_id is not None:
            return strain_id
        founder = self.strain_registry.mint(
            pathogen_id,
            genotype=self._founder_genotype(pathogen_id),
            origin="founder",
        )
        agent.assign_strain(
            pathogen_id, founder.strain_id, Phenotype.of(founder),
        )
        return founder.strain_id

    def register_seeded_founders(self, agents: Iterable[KorkinAgent]) -> None:
        """Assign founder strains to infections present before transmission.

        Seeded infections have a genome before they become shedders.  Register
        those founders eagerly so short runs still expose their lineage census.
        """
        if self.strain_registry is None:
            return
        for agent in agents:
            for pathogen_id, infection in agent.infections.items():
                if infection.get("status") != InfectionStatus.INFECTED:
                    continue
                self._resident_strain_id(agent, pathogen_id)

    def _environmental_strain_id(self, pathogen_id: str) -> str | None:
        """Founder strain of a pathogen's environmental reservoir."""
        if self.strain_registry is None or pathogen_id == "_default":
            return None
        strain_id = self._env_strain_ids.get(pathogen_id)
        if strain_id is None:
            founder = self.strain_registry.mint(
                pathogen_id,
                genotype=self._founder_genotype(pathogen_id),
                origin="founder",
            )
            strain_id = founder.strain_id
            self._env_strain_ids[pathogen_id] = strain_id
        return strain_id

    def _shed_masses(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        emitted: float,
    ) -> list[tuple[str, float]]:
        """One host's emitted mass, split among the lineages it carries.

        A co-infected host emits a mixture, so its onward transmissions are
        attributable to either lineage in proportion to what it is shedding.
        """
        shares = agent.strain_shedding_shares(
            pathogen_id, self.pathogen_profiles.get(pathogen_id, {}),
        )
        if not shares:
            strain_id = self._resident_strain_id(agent, pathogen_id)
            return [] if strain_id is None else [(strain_id, emitted)]
        return [(sid, emitted * share) for sid, share in shares.items()]

    def _emissions(
        self,
        weighted_shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
    ) -> list[EmissionContribution]:
        contributions: list[EmissionContribution] = []
        for agent, emitted in weighted_shedders:
            for strain_id, mass in self._shed_masses(agent, pathogen_id, emitted):
                contributions.append(EmissionContribution(
                    strain_id=strain_id,
                    source_agent_id=agent.agent_id,
                    emitted=mass,
                    transmissibility=self._transmissibility(strain_id),
                ))
        return contributions

    def _shedder_mix(
        self,
        shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
    ) -> EmissionMix | None:
        """Emission mix of the strains shed into one zone."""
        if self.strain_registry is None:
            return None
        return build_emission_mix(self._emissions(shedders, pathogen_id))

    def _direct_contact_mix(
        self,
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
        zone_mix: EmissionMix | None,
    ) -> EmissionMix | None:
        """Direct-contact mix for one target.

        ``zone_mix`` serves every target in a well-mixed zone; under cabin
        confinement each pair has its own contact factor, so the shares are
        rebuilt per target.
        """
        if zone_mix is not None or self.strain_registry is None:
            return zone_mix
        return self._shedder_mix(
            [
                (shedder, emitted * self._cabin_pair_contact_factor(shedder, target))
                for shedder, emitted in shedders
            ],
            pathogen_id,
        )

    def _min_strain_fraction(self, pathogen_id: str) -> float:
        """Frequency floor below which a pool's lineages are lumped."""
        config = self.strain_configs.get(pathogen_id)
        return 0.0 if config is None else config.min_strain_fraction

    def _reservoir_mix(
        self, kind: str, pathogen_id: str, zone_name: str,
    ) -> EmissionMix | None:
        """Emission mix of a pool's current strain composition."""
        if self.strain_registry is None:
            return None
        key = ReservoirComposition.key(kind, pathogen_id, zone_name)
        multipliers = {
            strain_id: self._transmissibility(strain_id)
            for strain_id, _ in self._reservoir.contributors(key)
        }
        return self._reservoir.mix(key, multipliers)

    def _deposit_reservoir_strains(
        self,
        kind: str,
        pathogen_id: str,
        zone_name: str,
        deposits: list[tuple[KorkinAgent, float]],
    ) -> None:
        """Record who deposited what into a lagged pool."""
        if self.strain_registry is None:
            return
        key = ReservoirComposition.key(kind, pathogen_id, zone_name)
        for agent, mass in deposits:
            for strain_id, strain_mass in self._shed_masses(agent, pathogen_id, mass):
                self._reservoir.deposit(
                    key, (strain_id, agent.agent_id), strain_mass,
                )
        self._reservoir.lump(self._min_strain_fraction(pathogen_id), key)

    def surface_lineage_masses(
        self,
        pathogen_id: str,
        zone_name: str,
    ) -> dict[str, float]:
        """Return current surface mass grouped by reportable genotype."""
        if self.strain_registry is None:
            return {}
        key = ReservoirComposition.key(SURFACE_RESERVOIR, pathogen_id, zone_name)
        grouped: dict[str, float] = {}
        for (strain_id, _source_agent_id), mass in self._reservoir.contributors(key).items():
            if strain_id == UNRESOLVED_STRAIN:
                genotype = UNRESOLVED_STRAIN
            else:
                genotype = self.strain_registry.get(strain_id).genotype or UNRESOLVED_STRAIN
            grouped[genotype] = grouped.get(genotype, 0.0) + float(mass)
        return grouped

    def surface_epochs_since_deposition(
        self,
        pathogen_id: str,
        zone_name: str,
        current_epoch: int,
    ) -> int | None:
        """Return elapsed epochs since the last positive surface deposit."""
        if self.strain_registry is None:
            return None
        key = ReservoirComposition.key(SURFACE_RESERVOIR, pathogen_id, zone_name)
        deposited = self._surface_last_deposition_epoch.get(key)
        if deposited is None:
            return None
        return max(int(current_epoch) - deposited, 0)

    def _seed_environmental_composition(
        self,
        pathogen_id: str,
        zone_name: str,
        level: float,
    ) -> None:
        """Give a reservoir its founder lineage the first time it is read.

        A reservoir that predates the run (spa biofilm, spore load) has a
        lineage no host deposited, so it is minted once at the pool's own mass
        and then competes with host deposits like any other contributor. An
        empty reservoir is not seeded: its composition is whatever hosts put in
        it.
        """
        key = ReservoirComposition.key(ENV_RESERVOIR, pathogen_id, zone_name)
        if level <= 0.0 or self._reservoir.contributors(key):
            return
        strain_id = self._environmental_strain_id(pathogen_id)
        if strain_id is None:
            return
        self._reservoir.deposit(key, (strain_id, None), level)

    def _environmental_attribution(
        self,
        ledger: StrainDoseLedger | None,
        pathogen_id: str,
        zone_name: str = SHIP_WIDE_ZONE,
        level: float = 0.0,
    ) -> DoseAttribution | None:
        """Attribution for reservoir-only exposure (no shedder to name)."""
        if self.strain_registry is None or pathogen_id == "_default":
            return None
        self._seed_environmental_composition(pathogen_id, zone_name, level)
        mix = self._reservoir_mix(ENV_RESERVOIR, pathogen_id, zone_name)
        if mix is None:
            return None
        return attribution(ledger, mix)

    def _update_env_reservoir_strains(
        self,
        pathogen_id: str,
        zone_name: str,
        level: float,
        factor: float,
        occupants: list[KorkinAgent],
        profile: dict[str, Any],
    ) -> float:
        """Age a zone reservoir's composition and add host shedding to it.

        Returns the mass deposited, which is added to the scalar reservoir too so
        the pool and its composition describe the same thing.
        """
        if self.strain_registry is None or pathogen_id == "_default":
            return 0.0
        key = ReservoirComposition.key(ENV_RESERVOIR, pathogen_id, zone_name)
        self._seed_environmental_composition(pathogen_id, zone_name, level)
        self._reservoir.decay(factor, key)
        deposits = [
            (agent, sv * ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION)
            for agent, sv in self._get_shedders(occupants, pathogen_id, profile)
        ]
        self._deposit_reservoir_strains(
            ENV_RESERVOIR, pathogen_id, zone_name, deposits,
        )
        return sum(mass for _, mass in deposits)

    def _airborne_composition(
        self,
        pathogen_id: str,
        zone_shedders: dict[str, list[tuple[KorkinAgent, float]]],
    ) -> None:
        """Age each zone's aerosol composition, then add this epoch's shedding.

        Read before the deposit, so a downstream pickup is attributed to the air
        that is already in the zone rather than to whoever is shedding upstream
        right now — the composition is the lag the scalar pool does not carry.
        """
        if self.strain_registry is None:
            return
        self._reservoir.decay_kind(
            self._airborne_survival(pathogen_id),
            f"{AIRBORNE_RESERVOIR}|{pathogen_id}",
        )
        for zone_name, shedders in zone_shedders.items():
            self._deposit_reservoir_strains(
                AIRBORNE_RESERVOIR, pathogen_id, zone_name, list(shedders),
            )

    def _decay_surface_composition(self) -> None:
        """Age surface strain composition with the surface pools it shadows."""
        if self.strain_registry is None:
            return
        for pathogen_id, profile in self.pathogen_profiles.items():
            self._reservoir.decay_kind(
                self._surface_survival(profile),
                f"{SURFACE_RESERVOIR}|{pathogen_id}",
            )

    def _age_aerosol_pools(self) -> None:
        """Age telemetry aerosol pools once before this epoch's deposits.

        The aggregate pool is rebuilt from the per-pathogen sums wherever a
        zone is tracked per pathogen, so the two views cannot drift when
        pathogens carry different airborne half-lives. A zone written only
        into the aggregate ages at the default half-life.
        """
        for pathogen_id, pools in self.aerosol_pools_by_pathogen.items():
            survival = self._airborne_survival(pathogen_id)
            for zone_name in pools:
                pools[zone_name] = max(0.0, pools[zone_name] * survival)
        default_survival = self.clock.survival_from_half_life(
            DEFAULT_AIRBORNE_HALF_LIFE_HOURS,
        )
        for zone_name in self.aerosol_pools:
            tracked = [
                pools[zone_name]
                for pools in self.aerosol_pools_by_pathogen.values()
                if zone_name in pools
            ]
            self.aerosol_pools[zone_name] = max(
                0.0,
                sum(tracked) if tracked
                else self.aerosol_pools[zone_name] * default_survival,
            )

    @staticmethod
    def _bounded_fraction(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _deposit_surface_mass(
        self,
        pathogen_id: str,
        zone_name: str,
        mass: float,
    ) -> None:
        """Add surface mass to the aggregate and cleanable compartments."""
        mass = float(mass)
        if not math.isfinite(mass) or mass <= 0.0:
            return
        coverage, _ = self._routine_cleaning_schedule(zone_name)
        self.surface_pools[zone_name] = (
            self.surface_pools.get(zone_name, 0.0) + mass
        )
        pools = self.surface_pools_by_pathogen.setdefault(pathogen_id, {})
        pools[zone_name] = pools.get(zone_name, 0.0) + mass
        cleanable = self.surface_pools_cleanable_by_pathogen.setdefault(
            pathogen_id, {},
        )
        cleanable[zone_name] = cleanable.get(zone_name, 0.0) + mass * coverage
        self._routine_cleaning_accumulators.setdefault(zone_name, 0.0)

    def _scale_surface_mass(
        self,
        pathogen_id: str,
        zone_name: str,
        factor: float,
    ) -> None:
        """Scale one pathogen's total and cleanable surface mass together."""
        factor = self._bounded_fraction(factor)
        pools = self.surface_pools_by_pathogen.get(pathogen_id)
        if pools is None or zone_name not in pools:
            if pathogen_id == "_default" and zone_name in self.surface_pools:
                self.surface_pools[zone_name] = max(
                    0.0, self.surface_pools[zone_name] * factor,
                )
            return
        previous = max(0.0, float(pools[zone_name]))
        remaining = previous * factor
        pools[zone_name] = remaining
        aggregate = max(0.0, float(self.surface_pools.get(zone_name, 0.0)))
        self.surface_pools[zone_name] = max(
            0.0, aggregate - previous + remaining,
        )
        cleanable = self.surface_pools_cleanable_by_pathogen.setdefault(
            pathogen_id, {},
        )
        cleanable[zone_name] = min(
            remaining,
            max(0.0, float(cleanable.get(zone_name, 0.0))) * factor,
        )

    def _routine_cleaning_event(self, zone_name: str) -> None:
        """Apply one routine pass to the cleanable compartment in a zone."""
        multiplier = 10.0 ** -max(
            0.0, float(self.routine_cleaning_log10_reduction),
        )
        for pathogen_id, pools in self.surface_pools_by_pathogen.items():
            total = max(0.0, float(pools.get(zone_name, 0.0)))
            if total <= 0.0:
                continue
            cleanable = self.surface_pools_cleanable_by_pathogen.setdefault(
                pathogen_id, {},
            )
            old_cleanable = min(
                total, max(0.0, float(cleanable.get(zone_name, 0.0))),
            )
            retention = 1.0 - (old_cleanable / total) * (1.0 - multiplier)
            self._scale_surface_mass(pathogen_id, zone_name, retention)
            cleanable[zone_name] = old_cleanable * multiplier
            if self.strain_registry is not None:
                self._reservoir.decay(
                    retention,
                    ReservoirComposition.key(
                        SURFACE_RESERVOIR, pathogen_id, zone_name,
                    ),
                )

    def _step_routine_surface_cleaning(self) -> None:
        """Advance daily housekeeping accumulators and fire discrete passes."""
        if not self.surface_cleaning_enabled:
            return
        zones = set(self._routine_cleaning_accumulators)
        zones.update(self.surface_pools)
        for pools in self.surface_pools_by_pathogen.values():
            zones.update(pools)
        for zone_name in zones:
            events_per_day = self._routine_cleaning_schedule(zone_name)[1]
            increment = (
                max(0.0, events_per_day)
                * self.clock.day_fraction_per_epoch
            )
            if increment <= 0.0:
                continue
            self._routine_cleaning_accumulators.setdefault(zone_name, 0.0)
            accumulator = self._routine_cleaning_accumulators[zone_name] + increment
            while accumulator + 1e-12 >= 1.0:
                self._routine_cleaning_event(zone_name)
                self._routine_cleaning_event_counts[zone_name] = (
                    self._routine_cleaning_event_counts.get(zone_name, 0) + 1
                )
                accumulator -= 1.0
            accumulator = max(0.0, accumulator)
            self._routine_cleaning_accumulators[zone_name] = accumulator

    def disinfect_surfaces(self, log10_reduction: float, coverage: float) -> None:
        """Apply nested outbreak-response disinfection to surface compartments."""
        reduction = max(0.0, float(log10_reduction))
        coverage = self._bounded_fraction(coverage)
        kill_multiplier = 10.0 ** -reduction
        zone_names = {
            zone_name
            for pools in self.surface_pools_by_pathogen.values()
            for zone_name in pools
        }
        disinfection_factors = {
            zone_name: self._nested_disinfection_factors(
                self._routine_cleaning_schedule(zone_name)[0],
                coverage,
                kill_multiplier,
            )
            for zone_name in zone_names
        }
        for pathogen_id, pools in self.surface_pools_by_pathogen.items():
            for zone_name, value in pools.items():
                total = max(0.0, float(value))
                if total <= 0.0:
                    continue
                cleanable = self.surface_pools_cleanable_by_pathogen.setdefault(
                    pathogen_id, {},
                )
                old_cleanable = min(
                    total, max(0.0, float(cleanable.get(zone_name, 0.0))),
                )
                old_missed = total - old_cleanable
                cleanable_factor, missed_factor = disinfection_factors[zone_name]
                retention = (
                    old_cleanable * cleanable_factor
                    + old_missed * missed_factor
                ) / total
                self._scale_surface_mass(pathogen_id, zone_name, retention)
                cleanable[zone_name] = old_cleanable * cleanable_factor
                if self.strain_registry is not None:
                    self._reservoir.decay(
                        retention,
                        ReservoirComposition.key(
                            SURFACE_RESERVOIR, pathogen_id, zone_name,
                        ),
                    )

    @classmethod
    def _nested_disinfection_factors(
        cls,
        routine_coverage: float,
        coverage: float,
        kill_multiplier: float,
    ) -> tuple[float, float]:
        routine_coverage = cls._bounded_fraction(routine_coverage)
        if coverage > routine_coverage and routine_coverage < 1.0:
            # Grade C assumption: outbreak coverage nests routine coverage.
            nested_fraction = (coverage - routine_coverage) / (
                1.0 - routine_coverage
            )
            cleanable_factor = kill_multiplier
            missed_factor = 1.0 - nested_fraction * (1.0 - kill_multiplier)
        elif routine_coverage > 0.0:
            cleanable_factor = 1.0 - (
                coverage / routine_coverage
            ) * (1.0 - kill_multiplier)
            missed_factor = 1.0
        else:
            cleanable_factor = 1.0
            missed_factor = 1.0
        return (
            cls._bounded_fraction(cleanable_factor),
            cls._bounded_fraction(missed_factor),
        )

    def _surface_survival(self, profile: dict[str, Any] | None = None) -> float:
        """Return one-epoch surface survival for a pathogen profile.

        Every source measures surface inactivation as a log10 reduction per day,
        so ``surface_decay_log10_per_day`` is the only key; a profile without it
        falls back to ``DEFAULT_SURFACE_DECAY_LOG10_PER_DAY``, not to another
        spelling. The conversion to the fractional daily loss the clock consumes
        is ``surface_fraction_per_day``, the single place it is expressed.
        """
        prof = profile or {}
        log10_per_day = float(prof.get(
            "surface_decay_log10_per_day",
            DEFAULT_SURFACE_DECAY_LOG10_PER_DAY,
        ))
        per_day = surface_fraction_per_day(log10_per_day)
        return 1.0 - self.clock.decay_per_epoch(per_day)

    def _airborne_survival(self, pathogen_id: str) -> float:
        """Return one-epoch aerosol survival from the pathogen half-life."""
        profile = self.pathogen_profiles.get(pathogen_id, {})
        half_life = float(profile.get("airborne_half_life_hours", 1.1))
        return self.clock.survival_from_half_life(half_life)

    def collect_extinct_strains(self, agents: list[KorkinAgent]) -> tuple[str, ...]:
        """Drop registry entries no host and no pool still references.

        Live means carried by an infection (any resident lineage of a
        co-infection, not just the record's primary) or standing in a pool above
        :data:`POOL_EXTINCTION_MASS`; the registry additionally keeps the
        ancestry of what is live, so a lineage's parents stay callable after the
        lineage itself dies out. The environmental founders are held too — one
        per pathogen, reused whenever a reservoir is re-seeded.
        """
        if self.strain_registry is None:
            return ()
        self._reservoir.drop_empty(POOL_EXTINCTION_MASS)
        live: set[str] = set(self._env_strain_ids.values())
        live |= self._reservoir.strain_ids()
        for agent in agents:
            for infection in agent.infections.values():
                strain_id = infection.get("strain_id")
                if strain_id is not None:
                    live.add(str(strain_id))
                residents = infection.get("strains")
                if isinstance(residents, dict):
                    live |= {str(sid) for sid in residents}
        return self.strain_registry.collect(live)

    def _accumulate(
        self,
        target_id: int,
        pathway: str,
        dose: float,
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        attribution_: DoseAttribution | None = None,
    ) -> float:
        """Add one exposure's dose, scaled by emission-side transmissibility.

        Returns the dose actually credited, which is what the tracing record
        should report.
        """
        if attribution_ is not None:
            dose *= attribution_.emission_factor
        agent_doses[target_id] = agent_doses.get(target_id, 0.0) + dose
        if agent_pathway_doses is not None:
            pw = agent_pathway_doses.setdefault(target_id, {})
            pw[pathway] = pw.get(pathway, 0.0) + dose
        if attribution_ is not None:
            attribution_.record(target_id, pathway, dose)
        return dose

    def _fold_strain_doses(
        self,
        pathogen_id: str,
        ledger: StrainDoseLedger | None,
        weights: dict[str, float],
        susceptibility: dict[int, float],
        npi: dict[int, dict[str, float]] | None = None,
    ) -> None:
        """Merge one pathogen pass's ledger into the epoch's strain doses.

        The strain shadow is scaled by the same per-route factors the doses
        were, so a host's NPIs shift attribution exactly as they shift the
        dose rather than leaving the shadow at the unreduced shares.
        """
        if ledger is None:
            return
        pathway_weights = {
            pathway: float(
                weights.get(PATHWAY_EFFICIENCY_KEYS.get(pathway, pathway), 1.0),
            )
            for pathway in PATHWAY_EFFICIENCY_KEYS
        }
        for agent_id in ledger.agent_ids():
            mult = susceptibility.get(agent_id, 1.0)
            by_pathogen = self._strain_doses.setdefault(agent_id, {})
            bucket = by_pathogen.setdefault(pathogen_id, {})
            for contributor, dose in ledger.strain_doses(
                agent_id,
                self._host_pathway_weights(
                    pathway_weights, (npi or {}).get(agent_id),
                ),
            ).items():
                bucket[contributor] = bucket.get(contributor, 0.0) + dose * mult

    @staticmethod
    def _host_pathway_weights(
        pathway_weights: dict[str, float],
        reductions: dict[str, float] | None,
    ) -> dict[str, float]:
        """Fold one host's NPI multipliers into the pathway weights."""
        if not reductions:
            return pathway_weights
        return {
            pathway: weight * float(
                reductions.get(
                    PATHWAY_EFFICIENCY_KEYS.get(pathway, pathway), 1.0,
                ),
            )
            for pathway, weight in pathway_weights.items()
        }

    def _draw_source(self, agent_id: int, pathogen_id: str) -> Contributor:
        """Draw the parent strain (and its shedder) from the dose shares.

        A draw that lands on the unresolved bin of a pool returns no parent: the
        acquiring host carries a lineage the pool could not resolve, and is
        minted its own founder if it ever sheds.
        """
        shares = self._strain_doses.get(agent_id, {}).get(pathogen_id, {})
        if not shares:
            return ("", None)
        contributor = draw_contributor(shares, self.rng)
        if contributor is None or contributor[0] == UNRESOLVED_STRAIN:
            return ("", None)
        return contributor

    def _embarkation_genotype(
        self, agent: KorkinAgent, pathogen_id: str,
    ) -> str | None:
        """Genotype an agent immune at embarkation is immune *against*.

        Drawn once from ``prior_genotype_distribution`` and cached, because
        pre-existing immunity has to be against something before a challenge
        genotype can escape it. Also written to the immune history, so standing
        immunity and immunity earned aboard read the same way downstream.
        """
        if not agent.immune:
            return None
        cached = agent.prior_genotypes.get(pathogen_id)
        if cached is None:
            cached = self._founder_genotype(pathogen_id)
            agent.prior_genotypes[pathogen_id] = cached
            if cached:
                agent.record_immunity(ImmuneRecord(
                    pathogen_id=pathogen_id,
                    genotype=cached,
                    origin=IMMUNITY_AT_EMBARKATION,
                ))
        return cached or None

    def _resolved_exposure_ages(
        self, agent: KorkinAgent, pathogen_id: str, epoch: int,
    ) -> dict[str, float]:
        """Days of natural history since each genotype's exposure resolved.

        The most recent record wins for a genotype met more than once, and the
        conversion from epochs runs through the run's clock, so a refractory
        window written in days means the same thing on any epoch grid.

        Only exposures resolved aboard have a resolution time. An embarkation
        prior was raised at an unknown point before the voyage, so it is left
        ageless rather than dated to epoch 0, which would hand a host whose
        infection was years ago a fresh refractory window.
        """
        ages: dict[str, float] = {}
        for record in agent.immune_history:
            if record.pathogen_id != pathogen_id or not record.genotype:
                continue
            if record.origin != IMMUNITY_FROM_INFECTION:
                continue
            days = self.clock.days_elapsed(max(0, epoch - record.epoch))
            prior = ages.get(record.genotype)
            if prior is None or days < prior:
                ages[record.genotype] = days
        return ages

    def _prior_exposures(
        self, agent: KorkinAgent, pathogen_id: str, epoch: int,
    ) -> dict[str, float | None]:
        """Prior genotypes mapped to the age of the exposure that raised them.

        ``None`` marks an exposure with no resolution time on this voyage: a
        lineage still resident (interference from an ongoing infection, which is
        not memory) or an embarkation prior. Both keep the declared
        ``cross_immunity`` value, neither gains a refractory window. A genotype
        the host has both resolved and re-acquired keeps its resolved age, since
        the memory is the thing a challenge of that genotype meets first.
        """
        ages = self._resolved_exposure_ages(agent, pathogen_id, epoch)
        exposures: dict[str, float | None] = {
            genotype: ages.get(genotype)
            for genotype in self._prior_genotypes(agent, pathogen_id)
        }
        return exposures

    def _prior_genotypes(
        self, agent: KorkinAgent, pathogen_id: str,
    ) -> tuple[str, ...]:
        """Every genotype this agent's standing immunity was raised against.

        Three sources: exposures resolved aboard (the immune history, which is a
        snapshot and so survives the lineage being collected), lineages still
        resident — an ongoing infection interferes with a challenge of its own
        genotype before it has cleared — and, for an agent immune at
        embarkation, the drawn prior. A host that has resolved two genotypes is
        protected by both, so the challenge is scored against the best match
        rather than the most recent exposure.
        """
        if self.strain_registry is None:
            return ()
        priors: dict[str, None] = dict.fromkeys(
            agent.immune_genotypes(pathogen_id),
        )
        for strain_id in agent.resident_strains(pathogen_id):
            if strain_id in self.strain_registry:
                genotype = self.strain_registry.get(strain_id).genotype
                if genotype:
                    priors.setdefault(genotype, None)
        embarked = self._embarkation_genotype(agent, pathogen_id)
        if embarked:
            priors.setdefault(embarked, None)
        return tuple(priors)

    def _challenge_protection(
        self, agent: KorkinAgent, pathogen_id: str, epoch: int = 0,
    ) -> float:
        """Protection against this epoch's challenge, in [0, 1].

        Absolute (1.0) for an agent immune at embarkation, which reproduces the
        legacy behaviour exactly whenever variant surveillance is off or the
        pathogen declares no ``cross_immunity``. With genotype-aware immunity
        configured, protection instead becomes specific and breachable: the
        dose-share-weighted mean of ``effective_protection`` over the strains
        challenging this agent, so a heterologous or escape mutant gets through
        an immunity that a homologous strain would not.
        """
        config = self.strain_configs.get(pathogen_id)
        legacy = 1.0 if agent.immune else 0.0
        if self.strain_registry is None or config is None or not config.cross_immunity:
            return legacy
        priors = self._prior_exposures(agent, pathogen_id, epoch)
        if not priors:
            return 0.0
        shares = self._strain_doses.get(agent.agent_id, {}).get(pathogen_id, {})
        total = sum(shares.values())
        if total <= 0.0:
            return legacy
        # Unattributed dose — no strain, or a pool's sub-floor tail — carries no
        # genotype to be recognised, so it earns only the *non*-specific part of
        # the host's immunity: the refractory window, which is genotype-blind by
        # construction, and nothing from the matched cross-immunity matrix. It
        # stays in the denominator either way, so after the window it is
        # unprotected dose as before.
        unnamed = _nonspecific_protection(config, priors)
        weighted = sum(
            dose * (
                _best_protection(config, priors, self.strain_registry.get(sid))
                if sid and sid != UNRESOLVED_STRAIN else unnamed
            )
            for (sid, _source), dose in shares.items()
        )
        return max(0.0, min(1.0, weighted / total))

    def _dose_response(self, pathogen_id: str, dose: float) -> float:
        """Probability one epoch's dose of a pathogen establishes an infection."""
        dr = self.pathogen_profiles.get(pathogen_id, {}).get("dose_response", {})
        if dr.get("model", "beta_poisson") == "exponential":
            return 1.0 - math.exp(-dr.get("k", 0.01) * dose)
        return 1.0 - math.pow(
            1.0 + dose / dr.get("beta", BETA), -dr.get("alpha", ALPHA),
        )

    def _dose_response_susceptibility(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
    ) -> float:
        """Return the host's persistent dose-response susceptibility."""
        existing = agent.dose_response_susceptibility.get(pathogen_id)
        if existing is not None:
            return existing
        dr = self.pathogen_profiles.get(pathogen_id, {}).get("dose_response", {})
        if dr.get("model", "beta_poisson") == "exponential":
            susceptibility = float(dr.get("k", 0.01))
        else:
            susceptibility = float(
                self.rng.beta(dr.get("alpha", ALPHA), dr.get("beta", BETA)),
            )
        agent.dose_response_susceptibility[pathogen_id] = susceptibility
        return susceptibility

    def _dose_response_hazard(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        effective_dose: float,
    ) -> float:
        """Compute one epoch's hazard from persistent host susceptibility."""
        susceptibility = self._dose_response_susceptibility(agent, pathogen_id)
        return -math.expm1(-susceptibility * effective_dose)

    def _superinfection_susceptibility(self, pathogen_id: str) -> float:
        """How much of a naive host's susceptibility an infected host retains.

        Homotypic interference: an established infection occupies the niche, so
        a second lineage of the same pathogen faces a discounted challenge. This
        is the *non*-genotype-specific part — genotype-specific interference
        already arrives through ``cross_immunity``, which sees the resident
        strain as the host's prior exposure.
        """
        config = self.strain_configs.get(pathogen_id)
        if config is None:
            return 0.0
        return max(0.0, min(1.0, config.superinfection_susceptibility))

    def _superinfection_open(self, pathogen_id: str) -> bool:
        """True when a second lineage of this pathogen can establish at all.

        False without strain tracking, which is what keeps an already-infected
        agent skipped exactly as before.
        """
        if self.strain_registry is None:
            return False
        return self._superinfection_susceptibility(pathogen_id) > 0.0

    def _establish(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        acquired_strain_id: str,
        dose: float,
        epoch: int,
        *,
        resident: bool,
        acquired_particles_by_route: dict[str, float] | None = None,
    ) -> bool:
        """Install an acquired strain, as a new infection or a co-resident.

        False when nothing new established — re-exposure of a host that already
        carries this very lineage, whose inoculum is absorbed rather than
        counted as a transmission event.
        """
        if agent.immune and not resident:
            # Breakthrough: genotype-specific immunity was breached, so the host
            # leaves the immune compartment and takes the ordinary legacy path.
            agent.immune = False
            agent.infection_status = InfectionStatus.SUSCEPTIBLE
        if resident:
            strain_id = acquired_strain_id or self._unresolved_founder(pathogen_id)
            established = agent.superinfect_with_strain(
                pathogen_id,
                strain_id,
                dose,
                epoch,
                phenotype=self._phenotype(strain_id),
                acquired_particles_by_route=acquired_particles_by_route,
            )
            return established
        agent.infect_with_pathogen(
            pathogen_id,
            dose,
            epoch,
            rng=self.rng,
            profile=self.pathogen_profiles.get(pathogen_id, {}),
            strain_id=acquired_strain_id or None,
            strain_phenotype=self._phenotype(acquired_strain_id),
            acquired_particles_by_route=acquired_particles_by_route,
        )
        return True

    def _unresolved_founder(self, pathogen_id: str) -> str:
        """Founder for a superinfection whose parent the pool could not resolve.

        A co-resident lineage has to be nameable: the census counts it and every
        assay reads it back, so an acquisition drawn from a sub-floor pool bin
        founds its own lineage here — the same contract
        :meth:`_resident_strain_id` applies when such a host first sheds. Before
        this, an unresolved superinfection installed a resident keyed on the
        empty string, which the lineage census then failed to look up.
        """
        if self.strain_registry is None:
            return ""
        founder = self.strain_registry.mint(
            pathogen_id,
            genotype=self._founder_genotype(pathogen_id),
            origin="founder",
        )
        return founder.strain_id

    def _inherit_strain(self, parent_strain_id: str) -> str:
        """Strain a new infection acquires: the parent's, or a mutant of it.

        Mutation is drawn once per infection event, so a lineage label means one
        genome rather than one infection.
        """
        if self.mutation_operator is None or not parent_strain_id:
            return parent_strain_id
        return self.mutation_operator.on_transmission(parent_strain_id, self.rng)

    def apply_within_host_mutations(self, agents: list[KorkinAgent]) -> None:
        """Draw one within-host mutation chance per resident lineage-epoch.

        Off unless a pathogen sets ``within_host_mutation_rate`` > 0, which is
        the only mutational supply available to the de novo regime when a voyage
        is too short for transmission chains to supply it (plan §0 decision 2).
        Untracked infections are left alone rather than minted a founder here:
        founders appear when an agent first sheds, so enabling the within-host
        source cannot change who is a founder. In a co-infected host each
        lineage mutates on its own, replacing itself rather than the mixture, so
        a mutation in one strain never erases its co-resident.
        """
        if self.mutation_operator is None:
            return
        rates = {
            pid: cfg.within_host_mutation_rate
            for pid, cfg in self.strain_configs.items()
            if cfg.within_host_mutation_rate > 0.0
        }
        if not rates:
            return
        for agent in agents:
            for pathogen_id in rates:
                for strain_id in tuple(agent.resident_strains(pathogen_id)):
                    mutated = self.mutation_operator.within_host(strain_id, self.rng)
                    if mutated != strain_id:
                        agent.replace_strain(
                            pathogen_id, strain_id, mutated,
                            self._phenotype(mutated),
                        )

    def apply_recombination(self, agents: list[KorkinAgent]) -> None:
        """Draw one recombination chance per co-infected agent-epoch.

        Recombination is the only evolutionary source that needs two parents in
        one place, which is why it could not exist before co-infection did. It
        runs after within-host mutation so a lineage that mutated this epoch is
        already the thing that recombines, and it is off unless a pathogen sets
        ``recombination_rate`` > 0.

        The recombinant *replaces the lineage it arose in* and the donor stays
        resident, so one event leaves a host's resident count unchanged:
        reassortment happens in place, and only superinfection widens a mixture.
        Over a voyage the population still diversifies, since a recombinant is a
        new lineage that can superinfect a host already carrying both parents.
        """
        if self.mutation_operator is None:
            return
        pathogens = tuple(
            pid for pid, cfg in self.strain_configs.items()
            if cfg.recombination_rate > 0.0
        )
        if not pathogens:
            return
        for agent in agents:
            for pathogen_id in pathogens:
                self._recombine_in_host(agent, pathogen_id)

    def _recombine_in_host(self, agent: KorkinAgent, pathogen_id: str) -> None:
        """One recombination draw for one host's residents of one pathogen."""
        if self.mutation_operator is None:
            return
        residents = tuple(agent.resident_strains(pathogen_id))
        if len(residents) < 2:
            return
        outcome = self.mutation_operator.recombine(residents, self.rng)
        if outcome is None:
            return
        replaced, recombinant = outcome
        agent.replace_strain(
            pathogen_id, replaced, recombinant, self._phenotype(recombinant),
        )

    def _aerosol_ventilation_factor(self, zone_name: str) -> float:
        """Outdoor-air dilution for balcony cabin corridors."""
        vent = self.zone_ventilation.get(zone_name, "")
        if vent == "balcony_partial":
            return BALCONY_AEROSOL_REDUCTION
        return 1.0

    def _direct_contact_zone_factor(self, zone_name: str) -> float:
        if self.zone_types.get(zone_name) == "Cabin_Corridor":
            return self.corridor_direct_contact_factor
        return 1.0

    def _is_quarantined(self, agent: KorkinAgent) -> bool:
        return agent.agent_id in self._quarantined_ids

    def _cabin_confinement_active(self, agent: KorkinAgent) -> bool:
        """Cabin-corridor confinement rules apply only in Cabin_Corridor zones."""
        if agent.agent_id not in self._quarantined_ids:
            return False
        return self.zone_types.get(agent.current_location) == "Cabin_Corridor"

    def _confinement_factor(self, agent: KorkinAgent) -> float:
        if self._cabin_confinement_active(agent):
            return self.confinement_isolation_factor
        return 1.0

    def confinement_emission_factor(self, agent: KorkinAgent) -> float:
        """Scale emission into shared pools for cabin-confined agents."""
        if self._cabin_confinement_active(agent):
            return self.confinement_isolation_factor
        return 1.0

    def _cabin_mate_droplet_addback(
        self,
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
        volume: float,
        vent_factor: float,
        target_factor: float,
    ) -> float:
        """Restore withheld emission for cabin mates sharing the cabin."""
        addback = 0.0
        for shedder, shedding in shedders:
            if shedder.agent_id not in target.cabin_mate_ids:
                continue
            unattenuated = (
                shedding * DROPLET_AEROSOL_FRACTION
                / max(volume, 1.0)
                * self.inhaled_air_volume_m3_per_epoch
                * self.droplet_scalar
                * vent_factor
            )
            addback += unattenuated * (
                1.0
                - self.confinement_emission_factor(shedder)
                * target_factor
            )
        return addback

    def _cabin_pair_contact_factor(
        self, shedder: KorkinAgent, target: KorkinAgent,
    ) -> float:
        """Scale direct-contact dose for cabin-corridor confinement pairs."""
        if self.zone_types.get(target.current_location) != "Cabin_Corridor":
            return 1.0
        confined_target = self._cabin_confinement_active(target)
        confined_shedder = self._cabin_confinement_active(shedder)
        if not confined_target and not confined_shedder:
            return 1.0
        if shedder.agent_id in target.cabin_mate_ids:
            return 1.0
        return NON_MATE_CONFINEMENT_CONTACT_FACTOR

    def initialize_zones(self, zone_names: list[str]) -> None:
        """Set up pools for all zones."""
        for z in zone_names:
            self.surface_pools.setdefault(z, 0.0)
            self.aerosol_pools.setdefault(z, 0.0)
            self._prev_zone_occupants.setdefault(z, set())
            self._prev_zone_shedders.setdefault(z, [])
            self._routine_cleaning_accumulators.setdefault(z, 0.0)
            self._routine_cleaning_event_counts.setdefault(z, 0)
        # Identify Dining-type zones for food contamination
        dining_zones = [
            z for z in zone_names
            if self.zone_types.get(z, "") == "Dining"
        ]
        # Initialize per-pathogen pools
        for pid, profile in self.pathogen_profiles.items():
            self.surface_pools_by_pathogen.setdefault(pid, {})
            self.surface_pools_cleanable_by_pathogen.setdefault(pid, {})
            self.aerosol_pools_by_pathogen.setdefault(pid, {})
            self._prev_zone_shedders_by_pathogen.setdefault(pid, {})
            for z in zone_names:
                self.surface_pools_by_pathogen[pid].setdefault(z, 0.0)
                self.surface_pools_cleanable_by_pathogen[pid].setdefault(z, 0.0)
                self.aerosol_pools_by_pathogen[pid].setdefault(z, 0.0)
                self._prev_zone_shedders_by_pathogen[pid].setdefault(z, [])
            # Initialize food contamination pools for Dining zones
            fc = profile.get("food_contamination", {})
            if fc.get("enabled", False):
                food_zones = fc.get("food_zones", dining_zones)
                self.food_pools.setdefault(pid, {})
                for fz in food_zones:
                    self.food_pools[pid].setdefault(fz, 0.0)
            # Initialize environmental contamination load
            ec = profile.get("environmental_contamination", {})
            if ec.get("enabled", False):
                baseline = float(ec.get("baseline_environmental_load", 0.0))
                self.environmental_load[pid] = baseline
                source_zones = ec.get("source_zones")
                if source_zones:
                    self.env_contamination.setdefault(pid, {})
                    for z in zone_names:
                        if self._zone_matches(z, source_zones):
                            self.env_contamination[pid].setdefault(z, baseline)

    def execute_transmission(
        self,
        epoch: int,
        agents: list[KorkinAgent],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]] | None = None,
        multi_pathogen_mass: dict[str, dict[str, float]] | None = None,
        quarantined_ids: set[int] | None = None,
    ) -> tuple[ContactTracingMatrix, list[TransmissionEvent]]:
        """Run all four transmission pathways for one epoch.

        Parameters
        ----------
        epoch : int
            Current epoch number.
        agents : list[KorkinAgent]
            All agents (locations already updated for this epoch).
        zone_pathogen_mass : dict
            Current aggregate airborne pathogen mass per zone.
        hvac_downstream_zones : dict, optional
            Map of zone → list of downstream zones receiving its air.
        multi_pathogen_mass : dict, optional
            Per-pathogen mass pools: {pathogen_id: {zone: mass}}.
        quarantined_ids : set[int], optional
            Agents confined to quarters; receive reduced direct contact / droplet
            and no fomite pickup in cabin-corridor platforms.

        Returns
        -------
        (ContactTracingMatrix, list[TransmissionEvent])
            The tracing matrix and list of actual infections.
        """
        matrix = ContactTracingMatrix(epoch=epoch)
        events: list[TransmissionEvent] = []
        self._quarantined_ids = set(quarantined_ids or ())
        self.apply_within_host_mutations(agents)
        self.apply_recombination(agents)
        self._age_aerosol_pools()

        # Build zone occupancy maps
        zone_occupants: dict[str, list[KorkinAgent]] = {}
        for agent in agents:
            loc = agent.current_location
            if loc in ("Isolated_In_Quarters", "Ashore"):
                continue
            if getattr(agent, "ashore", False):
                continue
            zone_occupants.setdefault(loc, []).append(agent)

        # Per-agent accumulated dose across all pathways (aggregate)
        agent_doses: dict[int, float] = {}
        # Track per-agent per-pathway dose breakdown for attribution
        agent_pathway_doses: dict[int, dict[str, float]] = {}
        # Per-agent per-pathogen dose accumulator
        agent_pathogen_doses: dict[int, dict[str, float]] = {}
        # Strain-resolved shadow of the same doses (empty when flag is off);
        # the pooled doses are kept so the shadow can be checked against the
        # dose that actually drove the draw
        self._strain_doses = {}
        self._last_pathogen_doses = agent_pathogen_doses
        self._last_pathogen_route_doses = {}

        # Determine which pathogens are active this epoch
        active_pathogens = list(self.pathogen_profiles.keys()) if self.pathogen_profiles else ["_default"]

        for pathogen_id in active_pathogens:
            self._execute_pathogen_pathways(
                epoch, agents, zone_occupants, zone_pathogen_mass,
                hvac_downstream_zones, multi_pathogen_mass,
                pathogen_id, agent_doses, agent_pathway_doses, agent_pathogen_doses,
                matrix, events,
            )

        # ── Apply combined dose-response per pathogen ───────────────
        for agent in agents:
            for pathogen_id in active_pathogens:
                resident = agent.is_infected_with(pathogen_id)
                if resident and not self._superinfection_open(pathogen_id):
                    continue
                p_dose = agent_pathogen_doses.get(agent.agent_id, {}).get(pathogen_id, 0.0)
                if p_dose <= 0:
                    continue
                protection = self._challenge_protection(agent, pathogen_id, epoch)
                if protection >= 1.0:
                    continue

                effective_dose = p_dose * (1.0 - protection)
                if resident:
                    effective_dose *= self._superinfection_susceptibility(pathogen_id)
                if effective_dose <= 0.0:
                    continue

                cumulative_dose = (
                    agent.cumulative_exposure.get(pathogen_id, 0.0)
                    + effective_dose
                )
                route_doses = self._effective_route_doses(
                    agent.agent_id,
                    pathogen_id,
                    effective_dose,
                )
                agent.cumulative_exposure[pathogen_id] = cumulative_dose
                route_ledger = agent.cumulative_exposure_by_route.setdefault(
                    pathogen_id, {},
                )
                for route, route_dose in route_doses.items():
                    route_ledger[route] = route_ledger.get(route, 0.0) + route_dose
                inf_prob = self._dose_response_hazard(
                    agent, pathogen_id, effective_dose,
                )

                if self.rng.random() < inf_prob:
                    parent_strain_id, source_agent_id = self._draw_source(
                        agent.agent_id, pathogen_id,
                    )
                    acquired_strain_id = self._inherit_strain(parent_strain_id)
                    if not self._establish(
                        agent, pathogen_id, acquired_strain_id, cumulative_dose, epoch,
                        resident=resident,
                        acquired_particles_by_route=dict(route_ledger),
                    ):
                        continue
                    agent.cumulative_exposure[pathogen_id] = 0.0
                    agent.cumulative_exposure_by_route.pop(pathogen_id, None)

                    pw_doses = agent_pathway_doses.get(agent.agent_id, {})
                    dominant = max(pw_doses, key=pw_doses.get) if pw_doses else "unknown"
                    route_ledger = dict(route_ledger)
                    event = TransmissionEvent(
                        epoch=epoch,
                        pathway=dominant,
                        source_agent_id=source_agent_id,
                        target_agent_id=agent.agent_id,
                        zone=agent.current_location,
                        dose=p_dose,
                        source_strain_id=parent_strain_id or None,
                        acquired_particles_by_route=route_ledger,
                    )
                    events.append(event)
                    matrix.transmission_events.append({
                        "target_id": agent.agent_id,
                        "zone": agent.current_location,
                        "pathogen_id": pathogen_id,
                        "dominant_pathway": dominant,
                        "total_dose": round(p_dose, 4),
                        "superinfection": resident,
                        "pathway_breakdown": {
                            k: round(v, 4)
                            for k, v in pw_doses.items()
                            if pathogen_id in k or pathogen_id == "_default"
                        },
                    })

        # ── Per-zone contact summary (occupancy map used for doses) ──
        matrix.zone_contact_summary = self._build_zone_contact_summary(
            zone_occupants, matrix, active_pathogens,
        )

        # ── Update persistent state for next epoch ───────────────────
        self._update_surface_pools(zone_occupants)
        self._update_prev_occupancy(zone_occupants)
        self.collect_extinct_strains(agents)

        return matrix, events

    def _merge_pathogen_doses(
        self,
        agents: list[KorkinAgent],
        pathogen_id: str,
        p_agent_doses: dict[int, float],
        agent_doses: dict[int, float],
        agent_pathogen_doses: dict[int, dict[str, float]],
    ) -> dict[int, float]:
        """Scale one pathogen's doses by susceptibility and merge them in.

        Returns the per-agent susceptibility multipliers, so the strain-resolved
        shadow can be scaled by exactly the same factors.
        """
        susceptibility: dict[int, float] = {}
        for aid, dose in p_agent_doses.items():
            agent_obj = next((a for a in agents if a.agent_id == aid), None)
            mult = (
                agent_obj.susceptibility_multiplier.get(pathogen_id, 1.0)
                if agent_obj is not None else 1.0
            )
            susceptibility[aid] = mult
            scaled_dose = dose * mult
            agent_doses[aid] = agent_doses.get(aid, 0.0) + scaled_dose
            apd = agent_pathogen_doses.setdefault(aid, {})
            apd[pathogen_id] = apd.get(pathogen_id, 0.0) + scaled_dose
        return susceptibility

    def _effective_route_doses(
        self,
        agent_id: int,
        pathogen_id: str,
        effective_dose: float,
    ) -> dict[str, float]:
        """Return this epoch's effective dose split by transmission route."""
        raw = self._last_pathogen_route_doses.get(pathogen_id, {}).get(
            agent_id, {},
        )
        raw_total = sum(raw.values())
        if raw_total <= 0.0:
            return {}
        route_doses = {
            route: dose * effective_dose / raw_total
            for route, dose in raw.items()
        }
        dominant = max(route_doses, key=route_doses.get)
        route_doses[dominant] += effective_dose - sum(route_doses.values())
        return route_doses

    def _execute_pathogen_pathways(
        self,
        epoch: int,
        agents: list[KorkinAgent],
        zone_occupants: dict[str, list[KorkinAgent]],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]] | None,
        multi_pathogen_mass: dict[str, dict[str, float]] | None,
        pathogen_id: str,
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]],
        agent_pathogen_doses: dict[int, dict[str, float]],
        matrix: ContactTracingMatrix,
        events: list[TransmissionEvent],
    ) -> None:
        profile = self.pathogen_profiles.get(pathogen_id, {})
        p_mass = (multi_pathogen_mass or {}).get(pathogen_id, zone_pathogen_mass)
        p_agent_doses: dict[int, float] = {}
        p_agent_pw: dict[int, dict[str, float]] = {}
        ledger = StrainDoseLedger() if self.strain_tracking else None
        ec = profile.get("environmental_contamination", {})
        person_to_person = ec.get("person_to_person", True)

        if person_to_person:
            self._pathway_direct_contact(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )
            self._pathway_droplet(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        self._pathway_hvac_airborne(
            epoch, zone_occupants, p_mass,
            hvac_downstream_zones or {},
            p_agent_doses, matrix, events,
            p_agent_pw, pathogen_id=pathogen_id, ledger=ledger,
        )

        if person_to_person:
            self._pathway_fomite(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        fc = profile.get("food_contamination", {})
        if fc.get("enabled", False):
            self._pathway_food_contamination(
                epoch, zone_occupants, p_agent_doses, matrix,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        if ec.get("enabled", False):
            self._pathway_environmental(
                zone_occupants, p_agent_doses, matrix,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        self._apply_route_efficiencies(profile, p_agent_doses, p_agent_pw)
        npi = self._npi_route_multipliers(agents)
        self._apply_npi_dose_reduction(npi, p_agent_doses, p_agent_pw)

        susceptibility = self._merge_pathogen_doses(
            agents, pathogen_id, p_agent_doses,
            agent_doses, agent_pathogen_doses,
        )

        self._fold_strain_doses(
            pathogen_id, ledger, self._route_efficiencies(profile), susceptibility,
            npi,
        )
        self._last_pathogen_route_doses[pathogen_id] = {
            aid: dict(pw) for aid, pw in p_agent_pw.items()
        }

        for aid, pw in p_agent_pw.items():
            merged = agent_pathway_doses.setdefault(aid, {})
            for pw_name, pw_dose in pw.items():
                key = f"{pw_name}:{pathogen_id}" if pathogen_id != "_default" else pw_name
                merged[key] = merged.get(key, 0.0) + pw_dose

    def _route_efficiencies(
        self, profile: dict[str, Any] | None,
    ) -> dict[str, float]:
        """Resolve route_efficiency_multipliers (identity default).

        ``transmission_route_weights`` is the deprecated alias for the same
        numbers. Nothing here normalises them: they are independent per-route
        dose multipliers.

        This is the sole owner of per-route efficiency (#25). A second
        multiplier standing on one route occupies the same position in the
        product and only the product is identifiable, which is why the retired
        ``contact_transfer_fraction`` is refused at load rather than defaulted
        (#22).
        """
        raw = (profile or {}).get("route_efficiency_multipliers")
        if not isinstance(raw, dict) or not raw:
            raw = (profile or {}).get("transmission_route_weights")
        if not isinstance(raw, dict) or not raw:
            return dict(DEFAULT_ROUTE_EFFICIENCY)
        weights = dict(DEFAULT_ROUTE_EFFICIENCY)
        for key in DEFAULT_ROUTE_EFFICIENCY:
            if key in raw:
                weights[key] = float(raw[key])
        return weights

    def _apply_route_efficiencies(
        self,
        profile: dict[str, Any] | None,
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]],
    ) -> None:
        """Scale each pathway's dose by the pathogen's route efficiency."""
        weights = self._route_efficiencies(profile)
        if all(abs(weights[k] - 1.0) < 1e-15 for k in DEFAULT_ROUTE_EFFICIENCY):
            return
        for aid, pw in agent_pathway_doses.items():
            total = 0.0
            for pw_name, pw_dose in pw.items():
                wkey = PATHWAY_EFFICIENCY_KEYS.get(pw_name, pw_name)
                w = float(weights.get(wkey, 1.0))
                scaled = pw_dose * w
                pw[pw_name] = scaled
                total += scaled
            agent_doses[aid] = total

    @staticmethod
    def _npi_route_multipliers(
        agents: list[KorkinAgent],
    ) -> dict[int, dict[str, float]]:
        """Collect the hosts whose declared NPIs reduce an incoming dose.

        Empty when no measure was declared, which is what keeps a run
        without an ``non_pharmaceutical_interventions`` block identical.
        """
        return {
            agent.agent_id: agent.dose_reduction_multipliers
            for agent in agents
            if agent.dose_reduction_multipliers
        }

    @staticmethod
    def _apply_npi_dose_reduction(
        npi: dict[int, dict[str, float]],
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]],
    ) -> None:
        """Scale each host's pathway doses by its own NPI multipliers.

        Applied after route efficiency and before susceptibility, gastric
        survival and cumulative exposure, per formal_spec_v2 §3.7: route
        efficiency is how well the route delivers to a portal, and an NPI
        is what the operator put between the two.
        """
        for aid, pw in agent_pathway_doses.items():
            reductions = npi.get(aid)
            if not reductions:
                continue
            total = 0.0
            for pw_name, pw_dose in pw.items():
                wkey = PATHWAY_EFFICIENCY_KEYS.get(pw_name, pw_name)
                scaled = pw_dose * float(reductions.get(wkey, 1.0))
                pw[pw_name] = scaled
                total += scaled
            agent_doses[aid] = total

    # Deprecated method aliases: external probes and tests still call these.
    _route_weights = _route_efficiencies
    _apply_route_weights = _apply_route_efficiencies

    # ── Pathway 1: Direct Contact ────────────────────────────────────

    def _zone_has_cabin_confinement(
        self,
        zone_name: str,
        shedders: list[tuple[KorkinAgent, float]],
        susceptible: list[KorkinAgent],
    ) -> bool:
        if self.zone_types.get(zone_name) != "Cabin_Corridor":
            return False
        if any(self._cabin_confinement_active(s) for s, _ in shedders):
            return True
        return any(self._cabin_confinement_active(t) for t in susceptible)

    def _direct_contact_dose(
        self,
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
        total_shedding: float,
        n_occupants: int,
        r0_draw: int,
        cabin_confinement: bool,
    ) -> float:
        if self.contact_mode == "per_partner_contact":
            sampled, _ = self._sample_contact_partners(
                shedders, n_occupants, r0_draw,
            )
            return self._per_partner_contact_dose(
                target, sampled, cabin_confinement,
            )
        if cabin_confinement:
            dose = 0.0
            for shedder, sv in shedders:
                pair_factor = self._cabin_pair_contact_factor(shedder, target)
                dose += sv * pair_factor / n_occupants * r0_draw
            return dose
        dose = total_shedding / n_occupants * r0_draw
        return dose * self._confinement_factor(target)

    def _sample_contact_partners(
        self,
        shedders: list[tuple[KorkinAgent, float]],
        n_occupants: int,
        r0_draw: int,
    ) -> tuple[list[tuple[KorkinAgent, float]], int]:
        """Sample distinct shedding partners for one target."""
        eligible = max(n_occupants - 1, 0)
        k = min(max(int(r0_draw), 0), eligible)
        if eligible <= 0 or k <= 0 or not shedders:
            return [], k
        n_shedders = min(len(shedders), eligible)
        n_non_shedders = eligible - n_shedders
        sampled_shedders = int(
            self.rng.hypergeometric(n_shedders, n_non_shedders, k),
        )
        if sampled_shedders <= 0:
            return [], k
        indices = self.rng.choice(
            len(shedders), size=sampled_shedders, replace=False,
        )
        return [shedders[int(index)] for index in np.atleast_1d(indices)], k

    def _per_partner_contact_dose(
        self,
        target: KorkinAgent,
        sampled_shedders: list[tuple[KorkinAgent, float]],
        cabin_confinement: bool,
    ) -> float:
        """Sum sampled partner shedding without zone-average dilution."""
        dose = 0.0
        for shedder, shedding in sampled_shedders:
            if cabin_confinement:
                shedding *= self._cabin_pair_contact_factor(shedder, target)
            dose += shedding
        return dose * self._confinement_factor(target)

    def _effective_contacts(self, n_occupants: int, agent: KorkinAgent) -> int:
        """Occupancy-scaled contact draw for density_dependent contact_mode.

        contacts ≈ base * (n / ref)^α, optionally multiplied for crew in
        Dining/Galley service zones, capped, then Poisson-sampled.
        """
        cfg = self.density_cfg
        ref = max(float(cfg["reference_occupancy"]), 1e-9)
        base = self.clock.amount_per_epoch(float(cfg["base_contacts_per_day"]))
        alpha = float(cfg["exponent"])
        max_c = self.clock.amount_per_epoch(float(cfg["max_contacts_per_day"]))

        raw = base * (max(n_occupants, 0) / ref) ** alpha
        loc = getattr(agent, "current_location", None) or ""
        if getattr(agent, "role", "") == "crew" and loc in self._service_zones:
            raw *= float(cfg.get("crew_contact_multiplier", 1.0))
        raw *= float(self.voyage_contact_multiplier)

        mean_contacts = min(raw, max_c)
        if mean_contacts <= 0.0:
            return 0
        draw = max(0, int(self.rng.poisson(mean_contacts)))
        # In sub-day runs max_contacts caps the mean, not each draw. A
        # per-epoch integer cap would make a daily cap bind 24 times.
        if self.clock.mode == LEGACY_EPOCH_DAY:
            return min(math.ceil(max_c), draw)
        return draw

    def _draw_contact_multiplier(
        self,
        n_occupants: int,
        target: KorkinAgent,
    ) -> int:
        """Return r0_draw for direct contact under the active contact_mode."""
        if self.contact_mode in ("density_dependent", "heterogeneous_zone_dose"):
            return self._effective_contacts(n_occupants, target)
        if self.contact_mode == "legacy":
            base = int(self.rng.choice(AVG_R_POOL))
            # Legacy mode: still scale by voyage contact multiplier when active
            scaled = (
                base
                * self.clock.day_fraction_per_epoch
                * float(self.voyage_contact_multiplier)
            )
            if self.clock.mode == LEGACY_EPOCH_DAY:
                return max(0, int(round(scaled)))
            whole = math.floor(scaled)
            return max(0, whole + int(self.rng.random() < scaled - whole))
        mean = self.clock.amount_per_epoch(POLYMOD_CONTACTS_PER_DAY)
        mean *= float(self.voyage_contact_multiplier)
        return max(0, int(self.rng.poisson(mean)))

    def _zone_exposure_sigma(self, zone_name: str) -> float:
        """Log-sigma for within-zone exposure heterogeneity."""
        # Galley / service names: high heterogeneity (plume / sequential contact).
        if "Galley" in zone_name:
            return max(0.0, self.heterogeneous_sigma_service)
        ztype = self.zone_types.get(zone_name, "")
        return max(
            0.0,
            float(
                self.heterogeneous_sigma_by_zone_type.get(
                    ztype,
                    self.heterogeneous_sigma_default,
                ),
            ),
        )

    def _zone_exposure_factor(self, zone_name: str) -> float:
        """Mean-1 lognormal within-zone exposure multiplier.

        Draws ``exp(N(-σ²/2, σ))`` so ``E[factor] = 1`` and the density-
        dependent mean dose is preserved in expectation.
        """
        sigma = self._zone_exposure_sigma(zone_name)
        if sigma <= 0.0:
            return 1.0
        mu = -0.5 * sigma * sigma
        return float(math.exp(self.rng.normal(mu, sigma)))

    def _pathway_direct_contact(
        self,
        _epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Person-to-person transmission via close contact in shared rooms."""
        use_het = self.contact_mode == "heterogeneous_zone_dose"
        use_partner = self.contact_mode == "per_partner_contact"
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not shedders or not susceptible:
                continue

            total_shedding = sum(sv for _, sv in shedders)
            shedder_ids = [s.agent_id for s, _ in shedders]
            n_occupants = max(len(occupants), 1)
            zone_dc_factor = self._direct_contact_zone_factor(zone_name)
            cabin_confinement = self._zone_has_cabin_confinement(
                zone_name, shedders, susceptible,
            )
            zone_mix = (
                None if cabin_confinement
                else self._shedder_mix(shedders, pathogen_id)
            )

            for target in susceptible:
                r0_draw = self._draw_contact_multiplier(n_occupants, target)
                sampled_shedders = shedders
                n_contacts = r0_draw
                if use_partner:
                    sampled_shedders, n_contacts = self._sample_contact_partners(
                        shedders, n_occupants, r0_draw,
                    )
                    dose = self._per_partner_contact_dose(
                        target, sampled_shedders, cabin_confinement,
                    )
                else:
                    dose = self._direct_contact_dose(
                        target, shedders, total_shedding, n_occupants, r0_draw,
                        cabin_confinement,
                    )
                dose *= self.direct_contact_scalar
                dose *= zone_dc_factor
                exposure_factor = 1.0
                if use_het:
                    exposure_factor = self._zone_exposure_factor(zone_name)
                    dose *= exposure_factor
                mix = self._direct_contact_mix(
                    target,
                    sampled_shedders,
                    pathogen_id,
                    None if use_partner else zone_mix,
                )
                dose = self._accumulate(
                    target.agent_id, "direct_contact", dose,
                    agent_doses, agent_pathway_doses,
                    attribution(ledger, mix),
                )

                rec: dict[str, Any] = {
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "source_ids": shedder_ids,
                    "pathogen_id": pathogen_id,
                    "dose": round(dose, 4),
                    "occupant_count": len(occupants),
                    "r0_draw": r0_draw,
                }
                if use_partner:
                    rec["source_ids"] = [
                        shedder.agent_id for shedder, _ in sampled_shedders
                    ]
                    rec["n_contacts"] = n_contacts
                if use_het:
                    rec["zone_exposure_factor"] = round(exposure_factor, 6)
                matrix.shared_room_exposures.append(rec)

    # ── Pathway 2: Short-Range Droplet ───────────────────────────────

    def _pathway_droplet(
        self,
        _epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Immediate aerosol exposure from shedders in the same room."""
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not shedders or not susceptible:
                continue

            emitted_shedders = [
                (shedder, sv * self.confinement_emission_factor(shedder))
                for shedder, sv in shedders
            ]
            total_aerosol = sum(
                emitted * DROPLET_AEROSOL_FRACTION
                for _, emitted in emitted_shedders
            )

            self.aerosol_pools[zone_name] = (
                self.aerosol_pools.get(zone_name, 0.0) + total_aerosol
            )
            self.aerosol_pools_by_pathogen.setdefault(
                pathogen_id, {},
            )[zone_name] = (
                self.aerosol_pools_by_pathogen.get(pathogen_id, {}).get(
                    zone_name, 0.0,
                )
                + total_aerosol
            )

            volume = self.zone_volumes.get(zone_name, 100.0)
            concentration = total_aerosol / max(volume, 1.0)
            shedder_ids = [s.agent_id for s, _ in shedders]
            vent_factor = self._aerosol_ventilation_factor(zone_name)
            mix = self._shedder_mix(emitted_shedders, pathogen_id)

            for target in susceptible:
                dose = concentration * self.inhaled_air_volume_m3_per_epoch
                dose *= self.droplet_scalar
                dose *= vent_factor
                target_factor = self._confinement_factor(target)
                dose *= target_factor
                dose += self._cabin_mate_droplet_addback(
                    target, shedders, volume, vent_factor, target_factor,
                )
                dose = self._accumulate(
                    target.agent_id, "droplet", dose,
                    agent_doses, agent_pathway_doses,
                    attribution(ledger, mix),
                )

                matrix.droplet_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "source_ids": shedder_ids,
                    "pathogen_id": pathogen_id,
                    "dose": round(dose, 4),
                    "aerosol_mass": round(total_aerosol, 4),
                    "concentration_per_m3": round(concentration, 6),
                })

    # ── Pathway 3: Long-Range Airborne (HVAC Drift) ──────────────────

    def _apply_hvac_downstream_doses(
        self,
        target_zone: str,
        source_zone: str,
        shedder_ids: list[int],
        mass_in_target: float,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
        source_attribution: DoseAttribution | None = None,
    ) -> None:
        volume = self.zone_volumes.get(target_zone, 100.0)
        concentration = mass_in_target / max(volume, 1.0)
        target_occupants = zone_occupants.get(target_zone, [])
        susceptible = self._get_susceptible(target_occupants, pathogen_id)
        if not susceptible:
            return

        for target in susceptible:
            dose = concentration * self.inhaled_air_volume_m3_per_epoch
            dose *= self.hvac_airborne_scalar
            dose *= self._aerosol_ventilation_factor(target_zone)
            dose = self._accumulate(
                target.agent_id, "hvac_airborne", dose,
                agent_doses, agent_pathway_doses, source_attribution,
            )

            matrix.hvac_downstream_exposures.append({
                "target_id": target.agent_id,
                "target_zone": target_zone,
                "source_zone": source_zone,
                "source_agent_ids": shedder_ids,
                "pathogen_id": pathogen_id,
                "dose": round(dose, 4),
                "airborne_mass": round(mass_in_target, 4),
                "concentration_per_m3": round(concentration, 6),
            })

    def _pathway_hvac_airborne(
        self,
        _epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Exposure from airborne pathogen drifted via HVAC from upstream zones.

        The dose is taken from the mass standing in the *target* zone, which is
        older than this epoch's shedding, so it is attributed to that zone's
        aerosol composition; the upstream shedders are the fallback for air whose
        history the composition does not yet cover.
        """
        zone_shedders: dict[str, list[tuple[KorkinAgent, float]]] = {}
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, None)
            if shedders:
                zone_shedders[zone_name] = shedders

        # For each downstream zone receiving HVAC air from a shedding zone
        for source_zone, shedders in zone_shedders.items():
            downstream = hvac_downstream_zones.get(source_zone, [])
            for target_zone in downstream:
                if target_zone == source_zone:
                    continue

                mass_in_target = zone_pathogen_mass.get(target_zone, 0.0)
                if mass_in_target <= 0:
                    continue

                mix = self._reservoir_mix(
                    AIRBORNE_RESERVOIR, pathogen_id, target_zone,
                ) or self._shedder_mix(shedders, pathogen_id)
                self._apply_hvac_downstream_doses(
                    target_zone, source_zone, [s.agent_id for s, _ in shedders],
                    mass_in_target,
                    zone_occupants, agent_doses, matrix,
                    agent_pathway_doses, pathogen_id,
                    attribution(ledger, mix),
                )

        self._airborne_composition(pathogen_id, zone_shedders)

    # ── Pathway 4: Fomite Deposition & Surface Touch ─────────────────

    def _fomite_zone_class(self, zone_name: str) -> str:
        """Map an existing ship zone classification to the fomite table."""
        zone_type = self.zone_types.get(zone_name, "")
        lowered = zone_name.lower()
        if "galley" in lowered or "service" in lowered:
            return "galley"
        if "crew" in lowered and ("mess" in lowered or "berth" in lowered):
            return "crew_mess"
        if zone_type == "Cabin_Corridor" or zone_type == "Room":
            return "cabin"
        if zone_type == "Dining":
            return "dining"
        return "public"

    def _routine_cleaning_schedule(self, zone_name: str) -> tuple[float, float]:
        """Return routine coverage and frequency for a zone."""
        zone_class = self._fomite_zone_class(zone_name)
        schedule = self.routine_cleaning_by_zone_class.get(zone_class)
        if schedule is None:
            return (
                self._bounded_fraction(self.routine_cleaning_coverage),
                self.routine_cleaning_events_per_day,
            )
        return (
            self._bounded_fraction(schedule["coverage"]),
            schedule["events_per_day"],
        )

    def _fomite_surface_area(self, zone_name: str) -> float:
        return HIGH_TOUCH_AREA_M2[self._fomite_zone_class(zone_name)]

    def _fomite_surface_contacts(
        self,
        zone_name: str,
        agent: KorkinAgent | None = None,
    ) -> float:
        zone_class = self._fomite_zone_class(zone_name)
        if (
            agent is not None
            and getattr(agent, "role", "") == "crew"
            and zone_name in self._service_zones
        ):
            hourly = CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR
        else:
            hourly = SURFACE_CONTACTS_PER_HOUR[zone_class]
        return hourly * self.clock.hours_per_epoch

    def _fomite_is_eating(self, target: KorkinAgent, epoch: int) -> bool:
        if not target.schedule:
            return False
        hour = self.clock.hour_of_day(epoch)
        activity = target.schedule[hour % len(target.schedule)]
        return str(activity).startswith("Meal")

    def _fomite_mouth_contacts(
        self,
        target: KorkinAgent,
        epoch: int,
    ) -> float:
        mean, sd = (
            EATING_MOUTH_CONTACTS_PER_HOUR
            if self._fomite_is_eating(target, epoch)
            else NON_EATING_MOUTH_CONTACTS_PER_HOUR
        )
        return max(
            0.0,
            float(self.rng.normal(mean, sd))
            * self.clock.hours_per_epoch,
        )

    def _fomite_pickup_request(
        self,
        target: KorkinAgent,
        zone_name: str,
        surface_mass: float,
    ) -> float:
        """Mass one target transfers from surface to hands."""
        if self._cabin_confinement_active(target):
            return 0.0
        hand_area = self.rng.uniform(*HAND_AREA_CM2_RANGE) / 1.0e4
        used_fraction = self.rng.uniform(*SURFACE_CONTACT_FRACTION_RANGE)
        transfer_efficiency = min(
            1.0,
            max(0.0, float(self.rng.lognormal(*SURFACE_TO_HAND_LOGNORMAL))),
        )
        area = self._fomite_surface_area(zone_name)
        request = (
            self._fomite_surface_contacts(zone_name, target)
            * (used_fraction * hand_area / area)
            * transfer_efficiency
            * surface_mass
        )
        return min(surface_mass, max(0.0, request))

    @staticmethod
    def _hand_to_surface_drying(profile: dict | None) -> float:
        """Drying-state multiplier on hand -> surface transfer efficiency.

        Neutral (1.0) unless a profile opts in, and it draws nothing: which
        drying state applies to a continuously recontaminated hand is not
        measured, so the axis is swept rather than valued.
        """
        value = (profile or {}).get(
            "hand_to_surface_drying_multiplier",
            HAND_TO_SURFACE_DRYING_MULTIPLIER,
        )
        return min(1.0, max(0.0, float(value)))

    def _hand_inactivation_rate(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict | None,
    ) -> float:
        existing = agent.hand_inactivation_rate_by_pathogen.get(pathogen_id)
        if existing is not None:
            return existing
        configured = (profile or {}).get("hand_inactivation_rate_per_hour")
        if isinstance(configured, (list, tuple)) and len(configured) >= 2:
            rate = float(self.rng.uniform(float(configured[0]), float(configured[1])))
        elif configured is None:
            rate = float(self.rng.uniform(*HAND_INACTIVATION_RATE_PER_HOUR_RANGE))
        else:
            rate = float(configured)
        agent.hand_inactivation_rate_by_pathogen[pathogen_id] = max(rate, 0.0)
        return agent.hand_inactivation_rate_by_pathogen[pathogen_id]

    def _hand_hygiene_efficacy(self, profile: dict | None) -> float:
        configured = (profile or {}).get(
            "hand_hygiene_efficacy_log10_reduction",
        )
        if isinstance(configured, (list, tuple)) and len(configured) >= 4:
            mean, sd, low, high = map(float, configured[:4])
        elif isinstance(configured, (list, tuple)) and len(configured) >= 2:
            mean, sd = map(float, configured[:2])
            low, high = 0.0, 1.89
        else:
            mean, sd, low, high = HAND_HYGIENE_EFFICACY_LOG10
        return float(np.clip(self.rng.normal(mean, sd), low, high))

    def _replenish_hand(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict | None,
    ) -> None:
        target = agent.get_pathogen_hand_target(pathogen_id, profile or {})
        current = agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        if target <= 0.0 and current <= 0.0:
            return
        rate = self._hand_inactivation_rate(agent, pathogen_id, profile)
        survival = math.exp(-rate * self.clock.hours_per_epoch)
        agent.hand_load_by_pathogen[pathogen_id] = (
            target + (current - target) * survival
        )

    def _apply_hand_hygiene(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict | None,
    ) -> None:
        """Apply the configured hygiene event after hand relaxation."""
        hand = agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        if hand <= 0.0:
            return
        hygiene_rate = float((profile or {}).get(
            "hand_hygiene_rate_per_hour",
            HAND_HYGIENE_RATE_PER_HOUR_DEFAULT,
        ))
        event_probability = 1.0 - math.exp(
            -max(hygiene_rate, 0.0) * self.clock.hours_per_epoch,
        )
        if event_probability > 0.0 and self.rng.random() < event_probability:
            hand *= math.pow(10.0, -self._hand_hygiene_efficacy(profile))
        agent.hand_load_by_pathogen[pathogen_id] = max(hand, 0.0)

    @staticmethod
    def _emesis_range(
        profile: dict | None,
        key: str,
        default: tuple[float, float],
    ) -> tuple[float, float]:
        value = (profile or {}).get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            low, high = float(value[0]), float(value[1])
            if low > 0.0 and high >= low:
                return low, high
        return default

    @staticmethod
    def _log_uniform_mean(low: float, high: float) -> float:
        """Arithmetic mean of a log-uniform variate on [low, high]."""
        return (high - low) / math.log(high / low)

    def _emesis_episode_load(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict,
        scheduled_episodes: int,
    ) -> float:
        """Copies expelled in one episode of this illness.

        The identified quantity is the per-subject cumulative shed, drawn once
        per illness in :func:`draw_emesis_schedule` and partitioned equally over
        the episodes drawn with it. A harness that writes a schedule directly
        never made that draw, so it falls back to the interval's arithmetic mean
        split over the scheduled episodes; the fallback consumes no RNG.
        """
        stored = getattr(
            agent, "emesis_episode_load_by_pathogen", {},
        ).get(pathogen_id)
        if stored is not None:
            return float(stored)
        low, high = self._emesis_range(
            profile, "emesis_total_shed_gec_range", EMESIS_TOTAL_SHED_GEC_RANGE,
        )
        return self._log_uniform_mean(low, high) / max(1, scheduled_episodes)

    def _emesis_phase(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict,
    ) -> tuple[dict, float] | None:
        inf = agent.infections.get(pathogen_id)
        if (
            inf is None
            or inf.get("status") != InfectionStatus.INFECTED
            or inf.get("illness") != IllnessStatus.SYMPTOMATIC
        ):
            return None
        age, _ = KorkinAgent._shedding_age(
            int(inf.get("time_infected") or 0), inf, profile, agent.clock,
        )
        if age < 0.0:
            return None
        phase = resolve_phase(
            profile.get("clinical_presentation", {}),
            math.floor(age),
        )
        if phase is None or "vomiting" not in phase.get("features", []):
            return None
        return phase, age

    def _emit_emesis(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict,
        zone_name: str,
        epoch: int,
    ) -> float:
        eligible = self._emesis_phase(agent, pathogen_id, profile)
        if eligible is None:
            return 0.0
        _, age = eligible
        schedule = agent.emesis_episode_schedule_by_pathogen.get(
            pathogen_id, [],
        )
        due = [event_age for event_age in schedule if event_age <= age]
        if not due:
            return 0.0
        agent.emesis_episode_schedule_by_pathogen[pathogen_id] = [
            event_age for event_age in schedule if event_age > age
        ]
        volume_low, volume_high = self._emesis_range(
            profile, "emesis_volume_ml_range", EMESIS_VOLUME_ML_RANGE,
        )
        aerosol_low, aerosol_high = self._emesis_range(
            profile,
            "emesis_aerosol_fraction_range",
            EMESIS_AEROSOL_FRACTION_RANGE,
        )
        episode_load = self._emesis_episode_load(
            agent, pathogen_id, profile, len(schedule),
        )
        area = float(profile.get(
            "emesis_deposition_area_m2", EMESIS_DEPOSITION_AREA_M2,
        ))
        touchable_fraction = min(
            1.0, self._fomite_surface_area(zone_name) / area,
        )
        records = agent.emesis_deposition_records_by_pathogen.setdefault(
            pathogen_id, [],
        )
        pool_gain_total = 0.0
        for _ in due:
            volume = math.exp(self.rng.uniform(
                math.log(volume_low), math.log(volume_high),
            ))
            aerosol_fraction = math.exp(self.rng.uniform(
                math.log(aerosol_low), math.log(aerosol_high),
            ))
            surface_load = episode_load * (1.0 - aerosol_fraction)
            aerosol_load = episode_load * aerosol_fraction
            pending = self.emesis_aerosol_pending_by_pathogen.setdefault(
                pathogen_id, {},
            )
            pending[zone_name] = pending.get(zone_name, 0.0) + aerosol_load
            pool_gain = surface_load * touchable_fraction
            records.append({
                "epoch": int(epoch),
                "zone": zone_name,
                "volume_ml": volume,
                # Derived diagnostic, never an input.
                "titre_gec_per_ml": episode_load / volume,
                "episode_load": episode_load,
                "surface_load": surface_load,
                "aerosol_load": aerosol_load,
                "pool_gain": pool_gain,
                "non_touchable": surface_load - pool_gain,
                "touchable_fraction": touchable_fraction,
            })
            pool_gain_total += pool_gain
        return pool_gain_total

    def drain_emesis_aerosol(self, pathogen_id: str) -> dict[str, float]:
        """Per-zone airborne mass from this epoch's emesis events, once.

        The emesis path emits to air per event, at a fraction of the expelled
        bolus, so the quantity cannot be carried as a fraction of continuous
        shedding. It is drained rather than read: the caller adds it to the
        zone reservoir exactly once per epoch.
        """
        return self.emesis_aerosol_pending_by_pathogen.pop(pathogen_id, {})

    def _deposit_emesis(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        zone_name: str,
        epoch: int,
        profile: dict,
    ) -> float:
        pool_gain = self._emit_emesis(
            agent, pathogen_id, profile, zone_name, epoch,
        )
        if pool_gain <= 0.0:
            return 0.0
        self._deposit_surface_mass(pathogen_id, zone_name, pool_gain)
        self._deposit_reservoir_strains(
            SURFACE_RESERVOIR, pathogen_id, zone_name, [(agent, pool_gain)],
        )
        if self.strain_registry is not None:
            key = ReservoirComposition.key(
                SURFACE_RESERVOIR, pathogen_id, zone_name,
            )
            self._surface_last_deposition_epoch[key] = int(epoch)
        return pool_gain

    def _hand_to_mouth_dose(
        self,
        target: KorkinAgent,
        epoch: int,
        hand_load: float,
    ) -> float:
        if hand_load <= 0.0:
            return 0.0
        used_fraction = self.rng.uniform(*MOUTH_CONTACT_FRACTION_RANGE)
        transfer_efficiency = float(np.clip(
            self.rng.normal(*HAND_TO_MOUTH_NORMAL), 0.0, 1.0,
        ))
        dose = (
            self._fomite_mouth_contacts(target, epoch)
            * used_fraction
            * transfer_efficiency
            * hand_load
        )
        return min(hand_load, max(0.0, dose))

    @staticmethod
    def _delivery_scale(requested_total: float, pool_mass: float) -> float:
        """Scale simultaneous deliveries so their sum cannot exceed the pool.

        Everyone in the zone is exposed to the same pool at the same time, so
        each dose is computed from the start-of-epoch mass and the whole set is
        scaled down together when demand exceeds supply. Doing it per target in
        list order would privilege whoever the occupant list happens to name
        first.
        """
        if requested_total <= 0.0 or requested_total <= pool_mass:
            return 1.0
        return pool_mass / requested_total

    def _record_fomite_pickup(
        self,
        target: KorkinAgent,
        zone_name: str,
        surface_mass: float,
        _delivered: float,
        dose: float,
        prev_occupant_ids: set[int],
        prev_shedders: list[int],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
        surface_attribution: DoseAttribution | None = None,
    ) -> None:
        credited_dose = self._accumulate(
            target.agent_id, "fomite", dose,
            agent_doses, agent_pathway_doses, surface_attribution,
        )

        is_trailing = (
            target.agent_id not in prev_occupant_ids
            and len(prev_shedders) > 0
        )

        matrix.fomite_trailing_exposures.append({
            "target_id": target.agent_id,
            "zone": zone_name,
            "pathogen_id": pathogen_id,
            "surface_mass": round(surface_mass, 4),
            "dose": round(credited_dose, 4),
            "is_trailing": is_trailing,
            "prev_shedder_ids": prev_shedders if is_trailing else [],
        })

    def _consume_surface_mass(
        self,
        pathogen_id: str,
        zone_name: str,
        delivered: float,
        previous_mass: float,
    ) -> None:
        """Remove delivered fomite mass and scale its strain composition."""
        if delivered <= 0.0 or previous_mass <= 0.0:
            return
        remaining = max(0.0, previous_mass - delivered)
        self._scale_surface_mass(
            pathogen_id, zone_name, remaining / previous_mass,
        )
        self._reservoir.decay(
            remaining / previous_mass,
            ReservoirComposition.key(SURFACE_RESERVOIR, pathogen_id, zone_name),
        )

    def _pathway_fomite_legacy_default(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
        ledger: StrainDoseLedger | None,
    ) -> None:
        """Preserve the unprofiled legacy harness fomite semantics."""
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, None)
            deposits: list[tuple[KorkinAgent, float]] = []
            for agent, shedding in shedders:
                if self._cabin_confinement_active(agent):
                    continue
                deposit = shedding * SURFACE_DEPOSITION_FRACTION
                deposits.append((agent, deposit))
                self._deposit_surface_mass(pathogen_id, zone_name, deposit)
            self._deposit_reservoir_strains(
                SURFACE_RESERVOIR, pathogen_id, zone_name, deposits,
            )
            if self.strain_registry is not None and deposits:
                key = ReservoirComposition.key(
                    SURFACE_RESERVOIR, pathogen_id, zone_name,
                )
                self._surface_last_deposition_epoch[key] = int(epoch)

        for zone_name, occupants in zone_occupants.items():
            surface_mass = self.surface_pools_by_pathogen.get(
                pathogen_id, {},
            ).get(zone_name, self.surface_pools.get(zone_name, 0.0))
            if surface_mass <= 0.0:
                continue
            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not susceptible:
                continue
            prev_shedders = self._prev_zone_shedders.get(zone_name, [])
            prev_occupants = self._prev_zone_occupants.get(zone_name, set())
            surface_attribution = attribution(
                ledger,
                self._reservoir_mix(SURFACE_RESERVOIR, pathogen_id, zone_name),
            )
            requests = [
                (
                    target,
                    self._legacy_fomite_pickup_request(
                        target, zone_name, surface_mass,
                    ),
                )
                for target in susceptible
            ]
            scale = self._delivery_scale(
                sum(mass for _, mass in requests), surface_mass,
            )
            delivered_total = 0.0
            for target, requested in requests:
                delivered = requested * scale
                if delivered <= 0.0:
                    continue
                self._record_fomite_pickup(
                    target, zone_name, surface_mass, delivered, delivered,
                    prev_occupants, prev_shedders, agent_doses, matrix,
                    agent_pathway_doses, pathogen_id, surface_attribution,
                )
                delivered_total += delivered
            self._consume_surface_mass(
                pathogen_id, zone_name, delivered_total, surface_mass,
            )

    def _legacy_fomite_pickup_request(
        self,
        target: KorkinAgent,
        zone_name: str,
        surface_mass: float,
    ) -> float:
        if self._cabin_confinement_active(target):
            return 0.0
        if self.rng.random() > FOMITE_PICKUP_PROBABILITY:
            return 0.0
        area = max(self.zone_volumes.get(zone_name, 100.0), 0.0)
        area /= DECK_HEIGHT_M
        if area <= 0.0:
            return 0.0
        return min(
            surface_mass,
            surface_mass / area * FOMITE_CONTACT_AREA_M2
            * FOMITE_TRANSFER_FRACTION,
        )

    def _pathway_fomite(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Surface contamination from shedders; stochastic pickup by later visitors."""
        if pathogen_id == "_default" and not self.pathogen_profiles:
            # Deprecated compatibility path for unprofiled legacy harnesses;
            # delete once those harnesses migrate to pathogen profiles.
            self._pathway_fomite_legacy_default(
                epoch, zone_occupants, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, ledger,
            )
            return
        # a) Deposit new fomite mass from current shedders (not confined to cabin)
        for zone_name, occupants in zone_occupants.items():
            for agent in occupants:
                self._replenish_hand(agent, pathogen_id, profile)
                self._deposit_emesis(
                    agent, pathogen_id, zone_name, epoch, profile or {},
                )
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            deposits: list[tuple[KorkinAgent, float]] = []
            for agent, _sv in shedders:
                if self._cabin_confinement_active(agent):
                    continue
                hand = agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
                used_fraction = self.rng.uniform(*SURFACE_CONTACT_FRACTION_RANGE)
                transfer_efficiency = min(
                    1.0,
                    max(0.0, float(self.rng.lognormal(*HAND_TO_SURFACE_LOGNORMAL))),
                ) * self._hand_to_surface_drying(profile)
                requested = (
                    self._fomite_surface_contacts(zone_name, agent)
                    * used_fraction
                    * transfer_efficiency
                    * hand
                )
                deposit = min(hand, max(0.0, requested))
                agent.hand_load_by_pathogen[pathogen_id] = hand - deposit
                deposits.append((agent, deposit))
                self._deposit_surface_mass(pathogen_id, zone_name, deposit)
            self._deposit_reservoir_strains(
                SURFACE_RESERVOIR, pathogen_id, zone_name, deposits,
            )
            if self.strain_registry is not None:
                deposited_mass = sum(mass for _, mass in deposits)
                if deposited_mass > 0.0:
                    key = ReservoirComposition.key(
                        SURFACE_RESERVOIR, pathogen_id, zone_name,
                    )
                    self._surface_last_deposition_epoch[key] = int(epoch)

        # b) Fomite trailing detection + pickup
        for zone_name, occupants in zone_occupants.items():
            path_pools = self.surface_pools_by_pathogen.get(pathogen_id)
            if path_pools is None:
                surface_mass = self.surface_pools.get(zone_name, 0.0)
            else:
                surface_mass = path_pools.get(zone_name, 0.0)
            if surface_mass <= 0:
                continue

            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not susceptible:
                continue

            # Identify trailing: agent was NOT in this zone last epoch
            # but a shedder WAS here last epoch
            prev_shedders = self._prev_zone_shedders.get(zone_name, [])
            prev_occupant_ids = self._prev_zone_occupants.get(zone_name, set())
            surface_attribution = attribution(
                ledger,
                self._reservoir_mix(SURFACE_RESERVOIR, pathogen_id, zone_name),
            )

            requests = [
                (
                    target,
                    self._fomite_pickup_request(
                        target, zone_name, surface_mass,
                    ),
                )
                for target in susceptible
            ]
            scale = self._delivery_scale(
                sum(mass for _, mass in requests), surface_mass,
            )
            delivered_total = 0.0
            for target, requested in requests:
                delivered = requested * scale
                if delivered <= 0.0:
                    continue
                hand = target.hand_load_by_pathogen.get(pathogen_id, 0.0)
                target.hand_load_by_pathogen[pathogen_id] = hand + delivered
                dose = self._hand_to_mouth_dose(target, epoch, hand + delivered)
                target.hand_load_by_pathogen[pathogen_id] = (
                    hand + delivered - dose
                )
                self._record_fomite_pickup(
                    target, zone_name, surface_mass, delivered, dose,
                    prev_occupant_ids, prev_shedders,
                    agent_doses, matrix, agent_pathway_doses, pathogen_id,
                    surface_attribution,
                )
                delivered_total += delivered
            self._consume_surface_mass(
                pathogen_id, zone_name, delivered_total, surface_mass,
            )

        for occupants in zone_occupants.values():
            for agent in occupants:
                self._apply_hand_hygiene(agent, pathogen_id, profile)

    # ── Pathway 5: Food Contamination ────────────────────────────────

    def _pathway_food_contamination(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Food contamination in Dining-type zones.

        Infected agents shedding in a food zone deposit pathogen into a
        persistent food pool.  The pool grows each epoch (bacterial
        reproduction) and decays slowly.  Susceptible agents eating in the
        zone receive an ingestion dose from the pool.
        """
        fc = (profile or {}).get("food_contamination", {})
        if not fc.get("enabled", False):
            return

        food_zones = self.food_pools.get(pathogen_id, {})
        if not food_zones:
            return

        growth_factor, decay_factor = self._food_rate_factors(fc)

        for zone_name in food_zones:
            occupants = zone_occupants.get(zone_name, [])

            # Deposit from shedders present in this food zone
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            self._deposit_reservoir_strains(
                FOOD_RESERVOIR, pathogen_id, zone_name,
                [
                    (
                        a,
                        sv
                        * self.confinement_emission_factor(a)
                        * FOOD_DEPOSITION_FRACTION_OF_EMISSION,
                    )
                    for a, sv in shedders
                ],
            )
            for agent, sv in shedders:
                food_zones[zone_name] += (
                    sv
                    * self.confinement_emission_factor(agent)
                    * FOOD_DEPOSITION_FRACTION_OF_EMISSION
                )

            # Net growth (reproduction minus decay), applied to the pool and to
            # its composition together so the two stay proportional
            pool = food_zones[zone_name]
            if pool > 0:
                pool *= growth_factor * decay_factor
                food_zones[zone_name] = max(pool, 0.0)
                self._reservoir.decay(
                    growth_factor * decay_factor,
                    ReservoirComposition.key(
                        FOOD_RESERVOIR, pathogen_id, zone_name,
                    ),
                )

            if food_zones[zone_name] <= 0:
                continue

            # Dose to susceptible agents eating here
            susceptible = self._get_susceptible(occupants, pathogen_id)
            zone_mult = self._food_zone_multiplier(zone_name)
            food_attribution = attribution(
                ledger,
                self._reservoir_mix(FOOD_RESERVOIR, pathogen_id, zone_name),
            )
            n_occupants = max(len(occupants), 1)
            pool_before = food_zones[zone_name]
            per_head = (
                pool_before
                / n_occupants
                * self.food_ingestion_fraction_per_epoch
                * zone_mult
            )
            delivered_each = per_head * self._delivery_scale(
                per_head * len(susceptible), pool_before,
            )
            for target in susceptible:
                dose = self._accumulate(
                    target.agent_id, "food", delivered_each,
                    agent_doses, agent_pathway_doses, food_attribution,
                )

                matrix.food_contamination_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "food_pool_mass": round(pool_before, 4),
                    "food_zone_multiplier": zone_mult,
                    "dose": round(dose, 4),
                })
            remaining = max(
                0.0, pool_before - delivered_each * len(susceptible),
            )
            food_zones[zone_name] = remaining
            if pool_before > 0.0 and remaining < pool_before:
                self._reservoir.decay(
                    remaining / pool_before,
                    ReservoirComposition.key(
                        FOOD_RESERVOIR, pathogen_id, zone_name,
                    ),
                )

    def _food_rate_factors(self, food_cfg: dict[str, Any]) -> tuple[float, float]:
        growth = food_cfg.get(
            "growth_rate_per_day",
            food_cfg.get("growth_rate_per_epoch", 0.0),
        )
        decay = food_cfg.get(
            "decay_rate_per_day",
            food_cfg.get("decay_rate_per_epoch", 0.1),
        )
        growth_factor = self.clock.growth_factor_per_epoch(1.0 + float(growth))
        decay_factor = 1.0 - self.clock.decay_per_epoch(float(decay))
        return growth_factor, decay_factor

    # ── Pathway 6: Environmental Source ─────────────────────────────

    def _zone_matches(self, zone_name: str, patterns: list[str]) -> bool:
        """True if zone_name matches any exact or fnmatch-style pattern."""
        for pat in patterns:
            if zone_name == pat or fnmatch.fnmatch(zone_name, pat):
                return True
        return False

    def _food_zone_multiplier(self, zone_name: str) -> float:
        """Food contamination dose multiplier for a Dining zone."""
        if zone_name in self.food_zone_multipliers:
            return float(self.food_zone_multipliers[zone_name])
        # Infer from dining_service_type if catalogued via zone name heuristics
        return 1.0

    def _pathway_environmental(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Environmental source pathway (HVAC-systemic or zone-scoped).

        Legacy mode (no ``source_zones``): ship-wide HVAC biofilm load
        delivers to every zone. Zone-scoped mode: per-zone reservoirs in
        matching source zones with probabilistic exposure.
        """
        ec = (profile or {}).get("environmental_contamination", {})
        if not ec.get("enabled", False):
            return

        source_zones = ec.get("source_zones")
        if source_zones:
            self._pathway_environmental_zone_scoped(
                zone_occupants, agent_doses, matrix, agent_pathway_doses,
                pathogen_id=pathogen_id, profile=profile or {}, ledger=ledger,
            )
            return

        load = self.environmental_load.get(pathogen_id, 0.0)
        if "colonization_rate_per_day" in ec:
            col_factor = self.clock.growth_factor_per_epoch(
                1.0 + float(ec["colonization_rate_per_day"]),
            )
        else:
            col_factor = self.clock.growth_factor_per_epoch(
                1.0 + float(ec.get("colonization_rate_per_epoch", 0.0)),
            )

        # Grow the HVAC biofilm load
        load *= col_factor
        self.environmental_load[pathogen_id] = load

        if load <= 0:
            return

        env_attribution = self._environmental_attribution(
            ledger, pathogen_id, SHIP_WIDE_ZONE, load,
        )

        # Deliver to all zones (environmental pathogen is HVAC-systemic)
        for zone_name, occupants in zone_occupants.items():
            volume = self.zone_volumes.get(zone_name, 100.0)
            delivered = load * self.env_delivery_fraction_per_epoch
            concentration = delivered / max(volume, 1.0)

            susceptible = self._get_susceptible(occupants, pathogen_id)
            for target in susceptible:
                dose = concentration * self.inhaled_air_volume_m3_per_epoch
                dose *= self.hvac_airborne_scalar
                dose = self._accumulate(
                    target.agent_id, "environmental", dose,
                    agent_doses, agent_pathway_doses, env_attribution,
                )

                matrix.environmental_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "environmental_load": round(load, 4),
                    "delivered_mass": round(delivered, 4),
                    "dose": round(dose, 4),
                })

    def _pathway_environmental_zone_scoped(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        *,
        pathogen_id: str,
        profile: dict[str, Any],
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Per-zone environmental reservoirs (Legionella spa / C.diff spores)."""
        ec = profile.get("environmental_contamination", {})
        source_zones = list(ec.get("source_zones") or [])
        emission = self.clock.amount_per_epoch(
            float(
                ec.get(
                    "base_emission_rate_per_day",
                    ec.get("base_emission_rate", 0.001),
                ),
            ),
        )
        p_expose = (
            self.clock.probability_per_epoch(float(ec["exposure_probability_per_day"]))
            if "exposure_probability_per_day" in ec
            else self.clock.probability_per_epoch(
                float(ec.get("exposure_probability_per_epoch", 0.1)),
            )
        )
        spore_decay = (
            self.clock.decay_per_epoch(float(ec["spore_decay_rate_per_day"]))
            if "spore_decay_rate_per_day" in ec
            else self.clock.decay_per_epoch(
                float(ec.get("spore_decay_rate_per_epoch", 0.0)),
            )
        )
        col_factor = (
            self.clock.growth_factor_per_epoch(
                1.0 + float(ec["colonization_rate_per_day"]),
            )
            if "colonization_rate_per_day" in ec
            else self.clock.growth_factor_per_epoch(
                1.0 + float(ec.get("colonization_rate_per_epoch", 0.0)),
            )
        )
        reservoirs = self.env_contamination.setdefault(pathogen_id, {})

        # Grow / decay matching zones; ensure keys exist for occupied matches
        for zone_name in zone_occupants:
            if not self._zone_matches(zone_name, source_zones):
                continue
            level = float(reservoirs.get(zone_name, 0.0))
            if level <= 0.0 and zone_name not in reservoirs:
                level = float(ec.get("baseline_environmental_load", 0.0))
            factor = col_factor * max(0.0, 1.0 - spore_decay)
            deposited = self._update_env_reservoir_strains(
                pathogen_id, zone_name, level, factor,
                zone_occupants[zone_name], profile,
            )
            reservoirs[zone_name] = max(level * factor + deposited, 0.0)

        for zone_name, occupants in zone_occupants.items():
            if not self._zone_matches(zone_name, source_zones):
                continue
            contamination = float(reservoirs.get(zone_name, 0.0))
            if contamination <= 0.0:
                continue
            susceptible = self._get_susceptible(occupants, pathogen_id)
            env_attribution = self._environmental_attribution(
                ledger, pathogen_id, zone_name, contamination,
            )
            for target in susceptible:
                if self.rng.random() >= p_expose:
                    continue
                dose = self._accumulate(
                    target.agent_id, "environmental", contamination * emission,
                    agent_doses, agent_pathway_doses, env_attribution,
                )
                matrix.environmental_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "environmental_load": round(contamination, 4),
                    "dose": round(dose, 4),
                    "zone_scoped": True,
                })

    # ── Multi-pathogen shedder/susceptible helpers ─────────────────────

    def _get_shedders(
        self,
        occupants: list[KorkinAgent],
        pathogen_id: str,
        profile: dict | None,
    ) -> list[tuple[KorkinAgent, float]]:
        """Return (agent, shedding_value) for agents shedding this pathogen."""
        result = []
        for a in occupants:
            if pathogen_id == "_default":
                if a.is_infected and a.current_shedding > 0:
                    result.append((a, a.current_shedding))
            else:
                sv = a.get_pathogen_shedding(pathogen_id, profile or {})
                if sv > 0:
                    result.append((a, sv))
        return result

    def _get_susceptible(
        self,
        occupants: list[KorkinAgent],
        pathogen_id: str,
    ) -> list[KorkinAgent]:
        """Return agents this pathogen can still challenge.

        Naive agents always. Additionally, once variant surveillance is on: an
        already-infected agent when a second lineage can establish, and an
        immune agent when the pathogen has a ``cross_immunity`` matrix — an
        escape mutant that never reaches an immune host can never be seen to
        escape anything.
        """
        result = []
        challengeable = pathogen_id != "_default" and self.strain_registry is not None
        for a in occupants:
            if a.immune and not (
                challengeable and self._genotype_aware(pathogen_id)
            ):
                continue
            if pathogen_id == "_default":
                if a.infection_status == InfectionStatus.SUSCEPTIBLE:
                    result.append(a)
            elif not a.is_infected_with(pathogen_id) or (
                challengeable and self._superinfection_open(pathogen_id)
            ):
                result.append(a)
        return result

    def _genotype_aware(self, pathogen_id: str) -> bool:
        """True when this pathogen's immunity is genotype-specific."""
        config = self.strain_configs.get(pathogen_id)
        return config is not None and bool(config.cross_immunity)

    # ── Per-zone contact summary ─────────────────────────────────────

    def _build_zone_contact_summary(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
        matrix: ContactTracingMatrix,
        active_pathogens: list[str],
    ) -> list[dict[str, Any]]:
        """Summarize epoch occupancy and contact intensity per zone.

        Surfaces the same ``zone_occupants`` map used for transmission so
        analysis can verify mixing (e.g. Medical zones are not a sick-call
        gathering point — sick-call is roster-only).
        """
        shared_by_zone: dict[str, int] = {}
        for row in matrix.shared_room_exposures:
            z = row.get("zone", "")
            shared_by_zone[z] = shared_by_zone.get(z, 0) + 1

        droplet_by_zone: dict[str, int] = {}
        for row in matrix.droplet_exposures:
            z = row.get("zone", "")
            droplet_by_zone[z] = droplet_by_zone.get(z, 0) + 1

        infection_by_zone: dict[str, int] = {}
        for row in matrix.transmission_events:
            z = row.get("zone", "")
            infection_by_zone[z] = infection_by_zone.get(z, 0) + 1

        summary: list[dict[str, Any]] = []
        for zone_name in sorted(zone_occupants.keys()):
            occupants = zone_occupants[zone_name]
            if not occupants:
                continue
            occupant_ids = sorted(a.agent_id for a in occupants)
            shedder_ids: set[int] = set()
            for pathogen_id in active_pathogens:
                profile = self.pathogen_profiles.get(pathogen_id, {})
                for agent, _sv in self._get_shedders(
                    occupants, pathogen_id, profile or None,
                ):
                    shedder_ids.add(agent.agent_id)
            sorted_shedders = sorted(shedder_ids)
            summary.append({
                "zone": zone_name,
                "occupant_count": len(occupant_ids),
                "occupant_ids": occupant_ids,
                "shedder_count": len(sorted_shedders),
                "shedder_ids": sorted_shedders,
                "shared_room_exposure_count": shared_by_zone.get(zone_name, 0),
                "droplet_exposure_count": droplet_by_zone.get(zone_name, 0),
                "infection_count": infection_by_zone.get(zone_name, 0),
            })
        return summary

    # ── State management ─────────────────────────────────────────────

    def _update_surface_pools(
        self, _zone_occupants: dict[str, list[KorkinAgent]],
    ) -> None:
        """Apply surface decay after fomite interactions."""
        for pathogen_id, pools in self.surface_pools_by_pathogen.items():
            survival = self._surface_survival(
                self.pathogen_profiles.get(pathogen_id),
            )
            for zone_name in pools:
                self._scale_surface_mass(pathogen_id, zone_name, survival)
        tracked_zones = {
            zone_name
            for pools in self.surface_pools_by_pathogen.values()
            for zone_name in pools
        }
        default_survival = self._surface_survival()
        for zone_name in self.surface_pools:
            if zone_name not in tracked_zones:
                self._scale_surface_mass(
                    "_default", zone_name, default_survival,
                )
        self._decay_surface_composition()
        self._step_routine_surface_cleaning()

    def _update_prev_occupancy(
        self, zone_occupants: dict[str, list[KorkinAgent]],
    ) -> None:
        """Snapshot current occupancy for next epoch's fomite trailing."""
        self._prev_zone_occupants = {}
        self._prev_zone_shedders = {}
        for zone_name, occupants in zone_occupants.items():
            self._prev_zone_occupants[zone_name] = {
                a.agent_id for a in occupants
            }
            self._prev_zone_shedders[zone_name] = [
                a.agent_id for a in occupants
                if a.is_infected and a.current_shedding > 0
            ]


def build_hvac_downstream_map(
    airflow_paths: dict[str, Any],
) -> dict[str, list[str]]:
    """Build a map of zone → downstream zones from air_flow_paths.json.

    A zone B is downstream of zone A if there is any airflow path
    (HVAC recirculation, cross-zone link, or adjacency) from A → B.
    """
    downstream: dict[str, list[str]] = {}

    # From HVAC zones: rooms within the same HVAC zone are all mutually downstream
    for hvac_zone in airflow_paths.get("hvac_zones", []):
        rooms = hvac_zone.get("rooms", [])
        for room in rooms:
            others = [r for r in rooms if r != room]
            downstream.setdefault(room, []).extend(others)

    # From cross-zone links: map HVAC zone → rooms, then add downstream
    zone_rooms: dict[str, list[str]] = {}
    for hvac_zone in airflow_paths.get("hvac_zones", []):
        zone_rooms[hvac_zone["id"]] = hvac_zone.get("rooms", [])

    for link in airflow_paths.get("cross_zone_links", []):
        from_rooms = zone_rooms.get(link["from"], [])
        to_rooms = zone_rooms.get(link["to"], [])
        for fr in from_rooms:
            for tr in to_rooms:
                downstream.setdefault(fr, []).append(tr)

    # From adjacency: direct room-to-room connections
    for adj in airflow_paths.get("adjacency", []):
        downstream.setdefault(adj["from"], []).append(adj["to"])
        downstream.setdefault(adj["to"], []).append(adj["from"])

    # Deduplicate
    for zone in downstream:
        downstream[zone] = list(set(downstream[zone]))

    return downstream
