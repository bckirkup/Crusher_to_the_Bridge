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
from engines.crew_duty_exclusion import is_food_employee
from engines.infection_dynamics_bridge import (
    ALPHA,
    BETA,
    DEFAULT_AIRBORNE_HALF_LIFE_HOURS,
    HAND_CARRIAGE_PROPENSITY_BETA,
    SURFACE_DEPOSITION_FRACTION,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS_PER_DAY, LEGACY_EPOCH_DAY, SimClock
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
# Donor hand -> recipient hand transfer efficiency: the fraction of a
# contaminated hand's load moved to a clean hand in one interpersonal hand
# contact. Wa human rotavirus suspended in 10% faeces on volunteers'
# fingerpads, donor held against recipient for 10 s at ~1 kg/cm2: 6.6% of the
# input infectious virus transferred 20 min after inoculation and 2.8% at
# 60 min. Ansari et al. 1988, J Clin Microbiol 26:1513-1518, read from the
# Abstract -- the 1988 issue is a scanned PDF with no machine-readable full
# text and no OCR available, so the Results dispersion was not retrievable.
# Grade B: measured hand-to-hand, right direction, right matrix (faeces),
# wrong virus. The same experiment's hand -> steel (16.1%) and steel -> hand
# (16.8%) arms bracket this engine's fomite transfer distributions, which is
# the cross-check that it is the same measurement family. The two time points
# are the frozen interval; neither is a stated central value, so a contact
# draws uniformly across them. Origin: Ab.
HAND_TO_HAND_TRANSFER_RANGE = (0.028, 0.066)
HAND_INACTIVATION_RATE_PER_HOUR_RANGE = (0.61, 1.7)
# Defecation events per day: the frequency at which a faecally shedding host
# recontaminates its own hands, and so the only quantity through which symptom
# status reaches the faecal-hand-fomite-food chain. Two arms, because that is
# what the symptom axis changes; the per-event hand load is the same measured
# Liu ceiling in both. Applies only to a profile that declares
# ``stool_events_per_day``; a profile without it keeps the continuous
# relaxation this pair replaces.
#
# Non-diarrhoeal arm: US adults reporting normal bowel habits, 95.9% between 3
# and 21 bowel movements per week = 0.43-3.0/day, with once daily the single
# most common habit and only 40% of men / 33% of women on a regular 24 h cycle.
# Interval: 0.43-3.0/day; Shape: U. Mitsuhashi et al. 2017, Am J Gastroenterol
# (NHANES 2009-2010, N=4,775), and Heaton et al. 1992, Gut (N=1,897 prospective
# diaries). Grade B: general adult population standing in for a passenger
# complement. Origin: Ab.
BASELINE_STOOL_EVENTS_PER_DAY = 1.0
# Diarrhoeal arm: adults presenting with acute gastroenteritis, mean stool
# frequency 5.63 +/- 1.43/day at presentation falling to 1.65 +/- 0.65/day by
# day 7. Interval: 3.0-8.5/day, floored at the >=3 unformed stools/24 h that
# *defines* acute diarrhoea (the case definition Kirby et al. 2016 scored
# norovirus challenge subjects against) and ceilinged at mean + 2 SD; Shape: U.
# Patel et al. 2025, BMC Nutrition (MAESTRO, 683 AGE patients, 239 sites,
# India). Grade C: mixed-aetiology care-seeking AGE under probiotic treatment,
# not norovirus-confirmed and not a community cohort, so the arm is swept
# rather than asserted. Origin: Ab. No norovirus-specific stools-per-day
# distribution was retrieved; the challenge literature reports the case
# definition and total stool weight, not an event rate (Atmar 2008, Kirby
# 2016), and a case-definition threshold is not a mean.
DIARRHOEAL_STOOL_EVENTS_PER_DAY = 5.63
# Feature names any enteric profile may use for the diarrhoeal phase feature.
DIARRHOEAL_PHASE_FEATURES = frozenset({
    "watery_diarrhea", "diarrhea", "bloody_diarrhea",
})
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
# more than diners do. Touch rate is a property of the activity, not the room,
# so it is the shift that carries this rate: a food employee working its
# service zone, not any crew member present in one (a crew member eating in
# the crew mess is a diner, and takes the diner rate).
CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR = 545.4
# Denominator of the fomite pickup model: the pool's mass enters a pickup only
# as the areal density mass/area, so these are what converts a zone's pool into
# a surface concentration. Total high-touch surface area per room in m2 has
# never been measured by anybody (register null class ∅lit), so every entry is
# a declared assumption and the class is a permanent Grade C liability.
# No source: declared assumption. Grade C. Origin: n/a.
# The density is uniform over the zone: a pool gain deposited by one event is
# available at the same concentration to every touch anywhere in the zone.
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


VOMITING_AXIS = "vomiting"
DIARRHOEA_AXIS = "diarrhoea"


def has_symptom_axis(inf: dict[str, Any], axis: str) -> bool:
    """Whether one infection record carries a symptom axis.

    A record with no drawn axes carries every feature its phase declares, so a
    profile that declares no axis probabilities behaves as it did before the
    axes existed.
    """
    axes = inf.get("symptom_axes")
    if not isinstance(axes, dict):
        return True
    return bool(axes.get(axis, True))


def draw_symptom_axes(
    inf: dict[str, Any],
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> None:
    """Draw which symptom classes one symptomatic host expresses.

    Vomiting and diarrhoea are independent observables in the challenge
    literature, not two labels for one severity: 72% of symptomatic GII.2
    subjects vomited (70% GI.1), and of those who vomited 50% also met the
    diarrhoea case definition (57% GI.1). Kirby et al. 2016, PLoS ONE
    (DOI 10.1371/journal.pone.0143759), Tables 1-2; human challenge subjects,
    Grade B for an adult passenger complement, origin Tn. A symptomatic host
    that does not vomit met the illness definition through diarrhoea, so the
    diarrhoea share of non-vomiters defaults to 1: that is the case definition
    closing the classes, not a measurement, and a profile may declare it.

    A profile declaring no ``symptom_axis_probabilities`` draws nothing and
    consumes no RNG.
    """
    shares = profile.get("clinical_presentation", {}).get(
        "symptom_axis_probabilities",
    )
    if not isinstance(shares, dict):
        return
    vomits = bool(rng.random() < float(shares.get("vomiting", 1.0)))
    key = (
        "diarrhoea_given_vomiting" if vomits
        else "diarrhoea_given_no_vomiting"
    )
    diarrhoea = bool(rng.random() < float(shares.get(key, 1.0)))
    inf["symptom_axes"] = {
        VOMITING_AXIS: vomits,
        DIARRHOEA_AXIS: diarrhoea,
    }


def draw_emesis_schedule(
    agent: Any,
    pathogen_id: str,
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> None:
    """Draw onset-relative emesis times and the illness total, once.

    The per-subject cumulative shed is the identified quantity, so it is drawn
    once here and partitioned equally over the episodes drawn with it; nothing
    is drawn per episode at emission time. A host whose drawn symptom axes
    exclude vomiting draws no schedule at all.
    """
    if not hasattr(agent, "emesis_episode_schedule_by_pathogen"):
        return
    if not has_symptom_axis(
        agent.infections.get(pathogen_id) or {}, VOMITING_AXIS,
    ):
        agent.emesis_episode_schedule_by_pathogen[pathogen_id] = []
        agent.emesis_episode_load_by_pathogen[pathogen_id] = 0.0
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
# PLoS Med; 7,290 diaries, 97,904 contacts; a contact is skin-to-skin or a
# two-way conversation of >= 3 words; distinct persons per day). Supersedes
# the avgR pool inherited from Korkin's Person.java. Grade C for this
# setting: a general European population, not a confined ship, and role- and
# activity-blind by construction. Kept as the whole-day reference and as the
# uniform control arm; CONTACT-ARCH-01 (``activity_contacts`` below) derives
# the draw from the schedule and the architecture instead when a run declares
# it. docs/literature/consensus_tranche_37_contact_architecture.md.
POLYMOD_CONTACTS_PER_DAY = 13.4

# CONTACT-ARCH-01: the contact draw as a property of the activity the schedule
# and the ship's architecture put a host in, not of the day. Each activity's
# rate is distinct partners per hour, declared by the run; there is no engine
# default for any of them because none is measured on a cruise ship under
# ordinary operations (Pung et al. 2022, Nat Commun 13:1956, is the only
# cruise sensor record and a COVID-era floor: passengers median 20 close
# contacts/day, crew 10; ~3 per >=1 h F&B visit). A run that enables the block
# must declare all eight. Absent, the uniform POLYMOD draw above runs on its
# old RNG path. docs/contact_architecture_spec.md.
CONTACT_ACTIVITIES: tuple[str, ...] = (
    "cabin",
    "corridor",
    "work_service",
    "work_other",
    "dining_table",
    "dining_venue",
    "leisure",
    "other",
)
# Refusal band on a declared per-hour rate, not an interval: the largest
# individual daily count in the institutional sensor record is 47.3 (Duval et
# al. 2018), so 30/h admits any measured rate and refuses a units error.
CONTACT_RATE_PER_HOUR_BOUNDS = (0.0, 30.0)
CONTACT_RATE_ROLES: tuple[str, ...] = ("passenger", "crew")

# CONTACT-ARCH-02: a visit's contacts saturate with dwell time. The per-hour
# rates above are measured over short dwells (Pung Fig. 2a: an F&B visit's
# close contacts plateau after >= 1 h), so a run may declare, per activity, a
# saturation time-scale tau in hours: the expected new contacts over a dwell
# of t hours is rate * tau * (1 - exp(-t / tau)), whose initial slope is the
# declared rate and whose plateau is rate * tau. An activity with no tau
# declared accrues at the constant rate, which is the tau -> infinity limit
# and the CONTACT-ARCH-01 path bit for bit. No tau is measured for any
# setting; each is a declared swept axis. Refusal band, not an interval: a
# visit cannot outlast a day of schedule.
CONTACT_SATURATION_HOURS_BOUNDS = (0.0, HOURS_PER_DAY)

# Defaults for density_dependent contact_mode (partial overrides merge onto these)
DEFAULT_DENSITY_CFG: dict[str, float] = {
    "reference_occupancy": 50.0,
    "base_contacts_per_day": POLYMOD_CONTACTS_PER_DAY,
    "max_contacts_per_day": 40.0,
    "exponent": 0.5,
    "crew_contact_multiplier": 2.0,
}
DEFAULT_CONTACT_MODE = "per_partner_contact"

# CONTACT-SCALE-01: how a person's contacts divide between the classes present.
# Shirreff et al. 2024 (Epidemics 47:100807; 2,114 wearers, 15 hospital wards,
# 33,946 proximity-sensor contacts) fit contact rate against the number of
# persons actually present as c = a(phi) * N^phi, with a(phi) renormalised so
# total contact time is conserved: phi = 0 is frequency-dependent, phi = 1
# linear density-dependent. Two findings, Grade B (analogous confined
# institution), origin R + Fig 1/3: a person's contacts with *everyone* present
# are frequency-dependent (credibility intervals include zero ward by ward, and
# the aggregate favours phi = 0) -- which is the POLYMOD draw above and is left
# alone -- while contacts *directed at a subpopulation* scale with that
# subpopulation's density, superlinearly (phi > 1) in several wards for
# patient-to-patient and nurse-to-patient contact, and negatively in a few.
# So the exponent here divides a draw whose total it never changes. No value is
# adopted: nothing measures phi for a dining room or a cruise ship, so it is a
# declared swept axis and the default reproduces the shipped model exactly.
DEFAULT_CONTACT_CLASS_EXPONENT = 0.0
# Refusal band on the declaration, not an interval and not a prior: wide enough
# to contain the reported ward posteriors (below zero through above one) and
# narrow enough that a typo cannot enter as a contact kernel.
CONTACT_CLASS_EXPONENT_BOUNDS = (-2.0, 3.0)

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

# Hallway encounter rate vs well-mixed ward (Cabin_Corridor zones). Applies
# to the corridor residual only: a cabin is its own compartment and its
# occupants meet at full strength (see ``_cabin_compartments``).
DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR = 0.15

# Key separator for the cabin compartments a Cabin_Corridor is split into.
# A compartment is one stateroom: the agent and its ``cabin_mate_ids``,
# labelled by the lowest agent id in the cabin.
CABIN_COMPARTMENT_SEPARATOR = "::cabin"

# Share of a seated diner's direct contacts that fall within its own table
# party rather than elsewhere in the venue (other tables, staff). Video
# observation of a full lunch service in a table-service restaurant (Zhang et
# al. 2021, J Infect 83:207, doi:10.1016/j.jinf.2021.05.030; ~13,000
# close-contact episodes, >40,000 touches): no close contact between diners at
# different tables, and 0 % of a diner's touches on another table's diners or
# objects (Results, Table 3: self 97.9 %, same table 2.1 %, other table 0 %,
# staff 0 %). Corroborated on a second service (Zhang et al. 2022, J Infect,
# doi:10.1016/j.jinf.2022.08.029: 3,108 close contacts, none between the
# source diners and the diners at two of the other tables). Grade B (analogous setting:
# a land restaurant, not a ship's dining room), origin R + T3. The residual
# staff–diner close contacts those studies do record are small and not
# tabulated as a share, so they are absorbed at 1.0 and stand as the open
# term; the share is a sweep axis on [0, 1] where 0 is the venue-wide draw
# the model made before parties existed (bit-identical), not a fitted value.
DEFAULT_DINING_PARTY_CONTACT_SHARE = 1.0

# AERO-NEAR-01: the near-field air compartment over the co-located unit (the
# cabin in a Cabin_Corridor, the table party in a seated Dining venue). The
# short-range inhalation route is a two-compartment form (Nicas & Jones 2009):
# the far field is the zone's well-mixed pool exactly as before, and a share
# ``retained_fraction`` (kappa) of each unit-affiliated shedder's aerosol is
# breathed at the unit's own volume before it reaches the room. kappa = 0 is
# the pre-change route, same code path, bit-identical. The near-field volume
# and exchange rate are measured nowhere for a table or a bedroom (literature
# tranche 36, docs/literature/consensus_tranche_36_near_field_air.md, all four
# questions), so kappa ships as a declared swept axis on [0, 1] with no
# default level, and the unit volume is declared geometry: a per-berth and a
# per-seat volume the run must state when it turns the near field on.
# ``neighbour_table_ratio`` (rho) is the second ring of the dining record:
# the exposure at a neighbouring table relative to the index table, which is
# the quantity Li et al. 2021 Table 3 tabulates (CFD exposure 0.76-1.04 in the
# same air stream, 0.40-0.47 downstream, 0.04-0.23 remote; Grade B, analogous
# setting, an ordering envelope and not a dose). rho on [0, 1] keeps the
# ordering same table >= neighbour table >= far table for every admissible
# value. Nothing here may be chosen against A5, A9 or a posting rate.
DEFAULT_NEAR_FIELD_RETAINED_FRACTION = 0.0
DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO = 0.0

# Hand → food transfer efficiency per bare-hand contact with communal or
# served food. Span of the measured means across food matrices and studies:
# finger → tomato 0.3 ± 0.5 % and → cucumber 7 ± 8 % (Tuladhar 2013, MNV-1),
# glove → cucumber 1.5 ± 1.9 % (Rönnqvist 2014, human norovirus), finger pad →
# lettuce 18 ± 5.7 % and → ham 46 ± 20.3 % (Bidawid 2004, FCV infectivity),
# hand → lettuce 25 % (Grove 2015). Direct measurement of this quantity on
# this material, but in the laboratory and mostly on surrogates, so B is the
# ceiling exactly as it is for the non-porous fomite legs in tranche 12.
# The span is read as a per-contact draw; a uniform draw across it is a
# convention, not a measured distribution. Grade B (interval), shape Grade X.
HAND_TO_FOOD_TRANSFER_FRACTION_RANGE = (0.003, 0.46)

# Bare-hand contacts with communal or served food, per shedder per day of
# presence in a food zone. ∅ null in the literature (tranche 29 §4): nothing
# measures how often a person touches communal food, and the nearest
# retrievals are bacterial loads on self-service touchscreens and touch
# frequencies from indoor-chemical exposure work. It is therefore declared,
# and it is the axis this route must be swept on rather than valued at.
# The shipped number is not a measurement and is not a new assumption: it is
# the retired ``FOOD_DEPOSITION_FRACTION_OF_EMISSION`` = 1e-4 re-expressed in
# the composed units, so that decomposing the route does not silently move its
# magnitude. At the shipped hand load (10^3.86 referenced to a curve peak of
# 10^11.0) and release adjustment (10^4.0/day), 1e-4 of the emission is 1e3
# copies/day, and 1e3 / (E[transfer] × 10^3.86) = 0.6 contacts/day. Two things
# follow and are recorded rather than repaired: a physically plausible rate is
# a few contacts per meal, i.e. 5–17× higher, so the sourced corridor's own
# interior deposits more than the retired constant did; and unlike that
# constant this deposit no longer scales with the swept release adjustment,
# because hand load is measured directly against the curve peak.
# Tranche 30 found the nearest measured analogues, and both sit an order of
# magnitude above this rate without measuring it: hand-to-*mouth* contacts
# during eating run at a median 7/h, adults 6/h and an adult 75th percentile
# of 11/h (Wilson 2020, J Expo Sci Environ Epidemiol, 263 people observed
# 30 min each; Grade B, origin R), and hand-hygiene-requiring occasions in a
# sandwich factory at ~3.1 per handler-hour (Mohamed 2024, J Food Prot, 588
# occasions, 12 handlers, 16 h of CCTV). Neither is a hand-to-*food* contact,
# so neither replaces this value; together they make it plausibly low by an
# order of magnitude, which is a reason to sweep it and not to reset it.
# No source: declared assumption, swept. Grade C. Origin: n/a.
FOOD_HAND_CONTACTS_PER_DAY = 0.6

# Multiplier on the food-contact rate for crew working a service zone, i.e.
# the food-handler channel. NEARS attributes ~40 % of retail outbreaks with
# identified contributing factors to food contamination by an ill or
# infectious food worker (Moritz 2023), so the channel is real; its *rate* is
# not measured, and the only measured staff-vs-diner contact ratio in a
# restaurant is 12.7× on shared surfaces (Jin 2022, the same study behind
# ``CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR``). Carried across from surface
# contacts to food contacts, which is an inference, not a measurement.
# Note what this multiplier is *not*: it scales a service-zone crew agent's
# contact rate, and carries no probability that the handler is shedding while
# working. That quantity is bounded in the general food-service literature but
# on the wrong denominator — 11.9 % of 491 US food workers worked two or more
# shifts while vomiting or with diarrhoea in the previous year (Sumner 2011),
# ~20 % at least one shift (Carpenter 2013), and one third of restaurants have
# no policy stating when an ill worker is excluded (Norton 2015) — all
# 12-month worker-level recall, where a per-shift probability is what would be
# needed, and there is no food-handler shift in the model to attach one to
# (tranche 30 §2). Recorded as bounded and not adoptable — and those figures
# are land-based, where VSP's crew arm is the opposite regime: a crew member
# meeting the AGE case definition is *required* to be isolated, a food employee
# until 48 h symptom-free with documented medical clearance before returning to
# work (VSP 2018 Operations Manual §4.4.1.1.1), where the same manual only
# *advises* it of passengers. No standing exclusion of that kind exists here;
# the model's only symptom-triggered removal is SOP-008, gated at escalation
# status ALERT (tranche 33). The multiplier is not a stand-in for it and does
# not move to compensate.
# Grade C inferred. Origin: Jin 2022 ratio, transferred across contact type.
FOOD_HANDLER_CONTACT_MULTIPLIER = 12.7

# Fraction of a food pool's standing pathogen mass ingested per agent per day.
# A fractional removal from a stock, so it compounds within a day and is read
# to the epoch through ``SimClock.decay_per_epoch``. The unit is declared here,
# not the shape: a constant fraction is continuous grazing, not sized meals at
# set hours, and the value is not a measurement of either.
# Not a biological quantity, and no literature search can raise its grade
# (tranche 29 §3): with the shipped decay of 0.1/day it leaves 85.5 % of the
# pool standing each day, which is a statement about food-service turnover —
# how long served food remains available before it is eaten or discarded — not
# about virus. Virus persistence on food is the conservative half of that
# product and is supported (HuNoV < 1 log in 1–2 weeks on produce, Cook 2016;
# MNV infectivity 1 log in 4 days on lettuce ≈ 0.44/day, Fallahi 2011, i.e. 4×
# faster than the shipped decay). The carry-over, not the deposition share, is
# what makes this route dominate delivered dose, which is why the profile may
# override it (``food_contamination.ingestion_fraction_per_day``) and sweep it.
# No source: declared assumption, swept. Grade C. Origin: n/a.
FOOD_INGESTION_FRACTION_PER_DAY = 0.05

# Fraction of the standing environmental load delivered to a zone per day.
# Delivery does not deplete the load, so a day's flux divides linearly across
# the day's epochs: read through ``SimClock.amount_per_epoch``.
# Searched and null (tranche 29 §8): nothing measures occupant intake as a
# fraction of a standing zone load. The only values published in this shape are
# environmental transmission rates of fitted compartmental models (e.g. Gogovi
# 2025), rejected as model outputs under the register's standing rule, and the
# nearest empirical analogue is chemical hand-to-mouth exposure, not virus.
# No source: declared assumption. Grade C. Origin: n/a.
ENV_DELIVERY_FRACTION_PER_DAY = 0.01

# Share of a shedding host's emission entering a zone-scoped environmental
# reservoir (spore shedding into a spa or ward). Applied only under variant
# surveillance, since it adds a host input the scalar reservoir never had.
# A share of an already per-epoch emission, like the food deposition share,
# so it is dimensionless and takes no clock conversion.
# Searched and null (tranche 29 §8), and unlike the food share it cannot even
# be composed: the reservoir it feeds is not a defined material, so no transfer
# assay is commensurable with it.
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


def _parse_dining_party_share(tx: dict[str, Any]) -> float:
    raw = tx.get("dining_party_contact_share", DEFAULT_DINING_PARTY_CONTACT_SHARE)
    share = float(raw)
    if not math.isfinite(share) or not 0.0 <= share <= 1.0:
        raise ValueError(
            "transmission.dining_party_contact_share must be in [0, 1], "
            f"got {raw!r}",
        )
    return share


@dataclass(frozen=True)
class NearFieldAir:
    """Declared near-field air compartment (AERO-NEAR-01); off at kappa 0."""

    retained_fraction: float = DEFAULT_NEAR_FIELD_RETAINED_FRACTION
    neighbour_table_ratio: float = DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO
    cabin_berth_volume_m3: float | None = None
    table_seat_volume_m3: float | None = None

    @property
    def active(self) -> bool:
        return self.retained_fraction > 0.0


def _near_field_unit_fraction(block: dict[str, Any], key: str, default: float) -> float:
    raw = block.get(key, default)
    value = float(raw)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(
            f"transmission.near_field_air.{key} must be finite in [0, 1], got {raw!r}",
        )
    return value


def _near_field_volume(block: dict[str, Any], key: str, required: bool) -> float | None:
    raw = block.get(key)
    if raw is None:
        if required:
            raise ValueError(
                f"transmission.near_field_air.{key} must be declared when "
                "retained_fraction is above 0: the near-field volume is "
                "declared geometry, not a default",
            )
        return None
    value = float(raw)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(
            f"transmission.near_field_air.{key} must be finite and positive, got {raw!r}",
        )
    return value


def _parse_near_field_air(tx: dict[str, Any]) -> NearFieldAir:
    """Read the near-field air declaration (AERO-NEAR-01).

    Absent, or ``retained_fraction`` 0, is the pre-change well-mixed route and
    takes the same code path. A run that turns the near field on must declare
    both unit volumes; there is no measured default to fall back on.
    """
    block = tx.get("near_field_air") or {}
    if not isinstance(block, dict):
        raise ValueError("transmission.near_field_air must be a mapping")
    kappa = _near_field_unit_fraction(
        block, "retained_fraction", DEFAULT_NEAR_FIELD_RETAINED_FRACTION,
    )
    rho = _near_field_unit_fraction(
        block, "neighbour_table_ratio", DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO,
    )
    required = kappa > 0.0
    return NearFieldAir(
        retained_fraction=kappa,
        neighbour_table_ratio=rho,
        cabin_berth_volume_m3=_near_field_volume(block, "cabin_berth_volume_m3", required),
        table_seat_volume_m3=_near_field_volume(block, "table_seat_volume_m3", required),
    )


def _parse_contact_class_exponent(tx: dict[str, Any]) -> float:
    """Read the class-directed contact exponent phi (CONTACT-SCALE-01).

    phi = 0 (the default) leaves a target's contacts distributed over the other
    occupants exactly as before, and takes the same code path, so a run is
    bit-identical to the pre-change tree. Non-zero phi reweights *which* class
    the same number of contacts land on; it never changes how many.
    """
    raw = tx.get("contact_class_exponent", DEFAULT_CONTACT_CLASS_EXPONENT)
    phi = float(raw)
    low, high = CONTACT_CLASS_EXPONENT_BOUNDS
    if not math.isfinite(phi) or not low <= phi <= high:
        raise ValueError(
            "transmission.contact_class_exponent must be finite in "
            f"[{low}, {high}], got {raw!r}",
        )
    return phi


def _parse_contact_rate(activity: str, raw: Any) -> dict[str, float]:
    """One activity's declared rate as a per-role mapping (CONTACT-ARCH-01).

    A bare number applies to every role; a mapping must name every role in
    ``CONTACT_RATE_ROLES``. Either way each value is finite and inside
    ``CONTACT_RATE_PER_HOUR_BOUNDS``.
    """
    key = f"transmission.activity_contacts.rates_per_hour.{activity}"
    if isinstance(raw, Mapping):
        missing = [r for r in CONTACT_RATE_ROLES if r not in raw]
        unknown = [r for r in raw if r not in CONTACT_RATE_ROLES]
        if missing or unknown:
            raise ValueError(
                f"{key} must map exactly the roles {list(CONTACT_RATE_ROLES)}; "
                f"missing {missing}, unknown {unknown}",
            )
        items = {str(r): raw[r] for r in CONTACT_RATE_ROLES}
    else:
        items = {r: raw for r in CONTACT_RATE_ROLES}
    low, high = CONTACT_RATE_PER_HOUR_BOUNDS
    out: dict[str, float] = {}
    for role, value in items.items():
        try:
            rate = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key}[{role}] must be a number, got {value!r}") from exc
        if not math.isfinite(rate) or not low <= rate <= high:
            raise ValueError(
                f"{key}[{role}] must be finite in [{low}, {high}] per hour, "
                f"got {value!r}",
            )
        out[role] = rate
    return out


def _parse_activity_saturation(block: Mapping[str, Any]) -> dict[str, float]:
    """Read ``activity_contacts.saturation_hours`` (CONTACT-ARCH-02).

    Optional and partial: only the activities named saturate; each value is
    a finite time-scale in hours inside ``CONTACT_SATURATION_HOURS_BOUNDS``,
    exclusive at zero. Absent, no activity saturates.
    """
    raw = block.get("saturation_hours")
    if raw is None:
        return {}
    key = "transmission.activity_contacts.saturation_hours"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be a mapping over activities")
    unknown = [a for a in raw if a not in CONTACT_ACTIVITIES]
    if unknown:
        raise ValueError(f"{key} names unknown activities {unknown}")
    low, high = CONTACT_SATURATION_HOURS_BOUNDS
    out: dict[str, float] = {}
    for activity, value in raw.items():
        try:
            tau = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{key}.{activity} must be a number of hours, got {value!r}",
            ) from exc
        if not math.isfinite(tau) or not low < tau <= high:
            raise ValueError(
                f"{key}.{activity} must be finite in ({low}, {high}] hours, "
                f"got {value!r}",
            )
        out[str(activity)] = tau
    return out


def _parse_activity_contacts(tx: dict[str, Any]) -> dict[str, dict[str, float]] | None:
    """Read ``transmission.activity_contacts`` (CONTACT-ARCH-01), or None.

    None -- the block absent or ``enabled: false`` -- keeps the uniform
    POLYMOD draw on its old code path and RNG. Enabled, every activity in
    ``CONTACT_ACTIVITIES`` must be declared: there is no default rate for any
    of them, and the block is only read under ``per_partner_contact``.
    """
    block = tx.get("activity_contacts")
    if not block:
        return None
    if not isinstance(block, Mapping):
        raise ValueError("transmission.activity_contacts must be a mapping")
    if not bool(block.get("enabled", False)):
        return None
    if _parse_contact_mode(tx) != "per_partner_contact":
        raise ValueError(
            "transmission.activity_contacts requires contact_mode "
            "per_partner_contact",
        )
    rates = block.get("rates_per_hour")
    if not isinstance(rates, Mapping):
        raise ValueError(
            "transmission.activity_contacts.rates_per_hour must be a mapping "
            f"over {list(CONTACT_ACTIVITIES)}",
        )
    missing = [a for a in CONTACT_ACTIVITIES if a not in rates]
    unknown = [a for a in rates if a not in CONTACT_ACTIVITIES]
    if missing or unknown:
        raise ValueError(
            "transmission.activity_contacts.rates_per_hour must declare every "
            f"activity in {list(CONTACT_ACTIVITIES)}; missing {missing}, "
            f"unknown {unknown}",
        )
    return {a: _parse_contact_rate(a, rates[a]) for a in CONTACT_ACTIVITIES}


def _parse_service_surface_knockout(cfg: dict[str, Any]) -> bool:
    """Whether this run knocks out the service-surface rate (SURF-KO-01).

    A diagnostic arm, off unless a run declares ``service_surface_knockout:
    {enabled: true}``. On, a food employee on shift in its service zone touches
    shared surfaces at the diner rate rather than the staff rate, which
    measures how much of the crew arm that one rate carries. It is not a
    production setting and the staff rate itself is unchanged.
    """
    block = cfg.get("service_surface_knockout")
    if block is None:
        return False
    if not isinstance(block, dict):
        raise ValueError(
            "service_surface_knockout must be a mapping with an 'enabled' key",
        )
    enabled = block.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError(
            f"service_surface_knockout.enabled must be a bool, got {enabled!r}",
        )
    return enabled


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
        self.dining_party_contact_share = _parse_dining_party_share(
            (cfg or {}).get("transmission", {}) or {},
        )
        self.service_surface_knockout = _parse_service_surface_knockout(
            cfg or {},
        )
        self.contact_class_exponent = _parse_contact_class_exponent(
            (cfg or {}).get("transmission", {}) or {},
        )
        # phi is only ever exactly 0.0 by default or declaration; any other
        # value, however small, is a declared class-directed kernel.
        self._class_directed_contacts = abs(self.contact_class_exponent) > 0.0
        self.activity_contacts = _parse_activity_contacts(
            (cfg or {}).get("transmission", {}) or {},
        )
        self.activity_saturation_hours: dict[str, float] = (
            _parse_activity_saturation(
                ((cfg or {}).get("transmission", {}) or {}).get(
                    "activity_contacts", {},
                ) or {},
            )
            if self.activity_contacts is not None else {}
        )
        if self.activity_saturation_hours and self.clock.mode == LEGACY_EPOCH_DAY:
            raise ValueError(
                "transmission.activity_contacts.saturation_hours needs an "
                "hourly clock: a visit cannot be timed on a day-long epoch",
            )
        self.near_field_air = _parse_near_field_air(
            (cfg or {}).get("transmission", {}) or {},
        )
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
    def service_zones(self) -> frozenset[str]:
        """Zones where a crew member is doing food service.

        The same set the crew contact multiplier, the service-surface contact
        rate and the food-handler multiplier key off, exposed read-only so a
        consumer cannot silently disagree with the transmission model about
        who is a food employee.
        """
        return frozenset(self._service_zones)

    def _scheduled_activity(self, agent: KorkinAgent, epoch: int) -> str:
        """The schedule token governing *agent* where it currently stands.

        The engine records the token it placed the agent by, and that record
        is the activity: it and ``current_location`` were resolved for the
        same hour, whereas the core's *epoch* counter need not agree with the
        engine's. Re-deriving the hour from *epoch* is the fallback for an
        agent nothing has placed yet.
        """
        recorded = getattr(agent, "current_activity", "")
        if recorded:
            return str(recorded)
        schedule = getattr(agent, "schedule", None)
        if not schedule:
            return ""
        hour = self.clock.hour_of_day(epoch)
        return str(schedule[hour % len(schedule)])

    def _on_service_duty(
        self,
        agent: KorkinAgent,
        zone_name: str,
        epoch: int,
    ) -> bool:
        """True when *agent* is a food employee on shift in *zone_name*.

        Presence in a service zone is not the food-handler channel. Every crew
        member eats three times a day, ``CrewMess`` is a Dining zone on every
        hull, and dining zones are drawn across the whole Dining set, so a
        role-and-location test makes an engineer at lunch a galley worker. The
        channel is a duty state: the zone is this agent's own work zone, and
        the schedule has it working rather than eating or off watch.
        """
        return (
            zone_name in self._service_zones
            and is_food_employee(agent, self._service_zones)
            and getattr(agent, "work_zone", "") == zone_name
            and self._scheduled_activity(agent, epoch) == "Work"
        )

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
        if self._is_cabin_compartment(zone_name):
            return 1.0
        if self.zone_types.get(zone_name) == "Cabin_Corridor":
            return self.corridor_direct_contact_factor
        return 1.0

    @staticmethod
    def _is_cabin_compartment(zone_name: str) -> bool:
        return CABIN_COMPARTMENT_SEPARATOR in zone_name

    @staticmethod
    def compartment_parent(zone_name: str) -> str:
        """The ship zone a compartment key belongs to (identity for zones)."""
        return zone_name.split(CABIN_COMPARTMENT_SEPARATOR, 1)[0]

    def _cabin_compartment_key(self, zone_name: str, agent: KorkinAgent) -> str:
        label = min(set(agent.cabin_mate_ids) | {agent.agent_id})
        key = f"{zone_name}{CABIN_COMPARTMENT_SEPARATOR}{label}"
        self.zone_types.setdefault(key, "Cabin_Corridor")
        return key

    def _cabin_compartments(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
    ) -> dict[str, list[KorkinAgent]]:
        """Split each Cabin_Corridor's occupants into staterooms.

        Other zones pass through unchanged. An agent with no cabin mates is a
        single cabin. The corridor itself is not returned: hallway encounters
        are the direct-contact residual, handled by ``_direct_contact_units``.
        """
        out: dict[str, list[KorkinAgent]] = {}
        for zone_name, occupants in zone_occupants.items():
            if (
                self.zone_types.get(zone_name) != "Cabin_Corridor"
                or self._is_cabin_compartment(zone_name)
            ):
                out[zone_name] = occupants
                continue
            for agent in occupants:
                key = self._cabin_compartment_key(zone_name, agent)
                out.setdefault(key, []).append(agent)
        return out

    def zone_surface_keys(self, zone_name: str) -> list[str]:
        """A zone's own surface key plus every cabin compartment within it."""
        prefix = zone_name + CABIN_COMPARTMENT_SEPARATOR
        keys = {zone_name}
        keys.update(k for k in self.surface_pools if k.startswith(prefix))
        for pools in self.surface_pools_by_pathogen.values():
            keys.update(k for k in pools if k.startswith(prefix))
        return sorted(keys)

    def zone_surface_mass(self, zone_name: str, pathogen_id: str | None = None) -> float:
        """Surface mass on a zone plus every cabin compartment within it."""
        pools = (
            self.surface_pools if pathogen_id is None
            else self.surface_pools_by_pathogen.get(pathogen_id, {})
        )
        return sum(pools.get(key, 0.0) for key in self.zone_surface_keys(zone_name))

    def zone_surface_lineage_masses(
        self,
        pathogen_id: str,
        zone_name: str,
    ) -> dict[str, float]:
        """Genotype composition pooled over a zone and its cabin compartments."""
        grouped: dict[str, float] = {}
        for key in self.zone_surface_keys(zone_name):
            for genotype, mass in self.surface_lineage_masses(pathogen_id, key).items():
                grouped[genotype] = grouped.get(genotype, 0.0) + mass
        return grouped

    def zone_surface_epochs_since_deposition(
        self,
        pathogen_id: str,
        zone_name: str,
        current_epoch: int,
    ) -> int | None:
        """Epochs since the freshest deposit on a zone or any cabin within it."""
        ages = [
            age for age in (
                self.surface_epochs_since_deposition(pathogen_id, key, current_epoch)
                for key in self.zone_surface_keys(zone_name)
            )
            if age is not None
        ]
        return min(ages) if ages else None

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

    def _near_field_unit(
        self,
        zone_name: str,
        target: KorkinAgent,
        shedder: KorkinAgent,
    ) -> tuple[float, float] | None:
        """Weight and effective volume of the near field target shares with shedder.

        Three units, in the order the record resolves them: the stateroom a pair
        of cabin mates share at night, the table a seated party shares at a meal,
        and the neighbouring table as the second ring, weighted by the declared
        ``neighbour_table_ratio``. Anyone else in the room is far field only.
        """
        near = self.near_field_air
        if shedder.agent_id == target.agent_id:
            return None
        if shedder.agent_id in target.cabin_mate_ids:
            if self.zone_types.get(zone_name) != "Cabin_Corridor":
                return None
            berth = near.cabin_berth_volume_m3
            if berth is None:
                return None
            return 1.0, berth * (len(target.cabin_mate_ids) + 1)
        if zone_name != target.dining_zone or not target.dining_party_ids:
            return None
        seat = near.table_seat_volume_m3
        if seat is None:
            return None
        table_volume = seat * (len(target.dining_party_ids) + 1)
        if shedder.agent_id in target.dining_party_ids:
            return 1.0, table_volume
        if self._adjacent_table(target, shedder):
            return near.neighbour_table_ratio, table_volume
        return None

    def _adjacent_table(self, target: KorkinAgent, shedder: KorkinAgent) -> bool:
        """Whether the two are seated at neighbouring tables in one sitting.

        Declared topology, not a distance kernel: tables are dealt in
        consecutive slices of a sitting, so consecutive indices are the pair the
        dining record calls adjacent, and no third ring exists.
        """
        index = target.dining_table_index
        other = shedder.dining_table_index
        return (
            index >= 0
            and other >= 0
            and abs(index - other) == 1
            and shedder.dining_zone == target.dining_zone
            and shedder.meal_seating == target.meal_seating
        )

    def _near_field_admits(self, profile: dict | None) -> bool:
        """Whether this pathogen's continuous emission may take a near field.

        The near field concentrates *continuous respiratory* emission, and an
        ``emesis_conditioned`` arm has none: the record supports norovirus in
        air only from a vomiting episode (tranche 36 §5), so enhancing that
        arm's continuous droplet term would amplify a route the literature does
        not license at any magnitude. Such an arm keeps the far field it has
        today; its emesis-aerosol near field is a separate item.
        """
        if not self.near_field_air.active:
            return False
        return (profile or {}).get(
            "airborne_emission_mode",
        ) != "emesis_conditioned"

    def _near_field_droplet_dose(
        self,
        zone_name: str,
        target: KorkinAgent,
        emitted_shedders: list[tuple[KorkinAgent, float]],
        volume: float,
        vent_factor: float,
        target_factor: float,
    ) -> float:
        """AERO-NEAR-01: the short-range term of the two-compartment air route.

        No emission is created. A share ``retained_fraction`` of the aerosol a
        near-field partner already emitted into this zone's pool is breathed at
        the unit's own volume instead of the room's, so the term is the
        difference of the two concentrations and vanishes when the unit is no
        smaller than the room. The far-field term above is untouched, and the
        zone pool the drift route reads keeps the whole emitted mass.
        """
        near = self.near_field_air
        if not near.active:
            return 0.0
        room_concentration_per_unit_mass = 1.0 / max(volume, 1.0)
        dose = 0.0
        for shedder, emitted in emitted_shedders:
            unit = self._near_field_unit(zone_name, target, shedder)
            if unit is None:
                continue
            weight, unit_volume = unit
            gain = 1.0 / unit_volume - room_concentration_per_unit_mass
            if weight <= 0.0 or gain <= 0.0:
                continue
            dose += (
                near.retained_fraction
                * weight
                * emitted * DROPLET_AEROSOL_FRACTION
                * gain
                * self.inhaled_air_volume_m3_per_epoch
                * self.droplet_scalar
                * vent_factor
                * target_factor
            )
        return dose

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
        pathogen_id: str,
        epoch: int,
    ) -> float:
        if self.contact_mode == "per_partner_contact":
            sampled, _ = self._sample_contact_partners(
                shedders, n_occupants, r0_draw,
            )
            dose, _moved = self._per_partner_contact_dose(
                target, sampled, cabin_confinement, pathogen_id, epoch,
            )
            return dose
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
        class_counts: dict[str, int] | None = None,
    ) -> tuple[list[tuple[KorkinAgent, float]], int]:
        """Sample distinct shedding partners for one target.

        With ``contact_class_exponent`` at its default 0 the draw is uniform
        over the other occupants, which is the shipped model; *class_counts* is
        then ignored and this method is entered and left on the same path as
        before. Non-zero phi routes through ``_sample_partners_by_class``,
        which divides the *same* draw between the classes present.
        """
        if class_counts and self._class_directed_contacts:
            return self._sample_partners_by_class(
                shedders, class_counts, r0_draw,
            )
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

    def _class_draw_weights(self, class_counts: dict[str, int]) -> list[float]:
        """Share of a contact draw each class receives, in key order.

        Contacts directed at a class scale as ``N_class ** phi`` (Shirreff
        2024), and the draw is renormalised over the classes present so its
        total is unchanged — the aggregate stays frequency-dependent, which is
        what that study measures. The per-class share is therefore
        ``N_c ** (1 + phi)`` normalised, since a class of ``N_c`` eligible
        partners already receives ``N_c`` of the uniform draw's weight.
        """
        power = 1.0 + self.contact_class_exponent
        raw = [float(max(n, 0)) ** power for n in class_counts.values()]
        total = sum(raw)
        if total <= 0.0:
            return [0.0 for _ in raw]
        return [w / total for w in raw]

    def _sample_partners_by_class(
        self,
        shedders: list[tuple[KorkinAgent, float]],
        class_counts: dict[str, int],
        r0_draw: int,
    ) -> tuple[list[tuple[KorkinAgent, float]], int]:
        """Split one contact draw between classes, then sample within each.

        The number of contacts is not touched: ``r0_draw`` is allocated over
        the classes present by ``_class_draw_weights`` and each class's share
        is sampled from that class's own pool by the unchanged hypergeometric
        draw. A class's allocation is capped by its eligible pool exactly as a
        whole-room draw is capped by the room.
        """
        k = max(int(r0_draw), 0)
        weights = self._class_draw_weights(class_counts)
        if k <= 0 or sum(weights) <= 0.0:
            return [], 0
        allocation = self.rng.multinomial(k, weights)
        sampled: list[tuple[KorkinAgent, float]] = []
        drawn = 0
        for (role, n_class), k_class in zip(
            class_counts.items(), allocation, strict=True,
        ):
            class_shedders = [
                (s, sv) for s, sv in shedders if s.role == role
            ]
            partners, n_drawn = self._sample_contact_partners(
                class_shedders, int(n_class) + 1, int(k_class),
            )
            sampled.extend(partners)
            drawn += n_drawn
        return sampled, drawn

    def _pool_class_counts(
        self,
        occupants: Iterable[KorkinAgent],
        target: KorkinAgent,
    ) -> dict[str, int] | None:
        """Eligible partners in a pool by role, or None when there is nothing to divide.

        None keeps the caller on the uniform draw without iterating the pool,
        so the default run does no extra work and consumes no extra RNG.
        """
        if not self._class_directed_contacts:
            return None
        counts: dict[str, int] = {}
        for agent in occupants:
            counts[agent.role] = counts.get(agent.role, 0) + 1
        counts[target.role] = counts.get(target.role, 1) - 1
        present = {role: n for role, n in counts.items() if n > 0}
        # One class present is one class to allocate to: the exponent has
        # nothing to divide, so the pool keeps the uniform draw and its RNG.
        return present if len(present) > 1 else None

    def _seated_partner_sample(
        self,
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
        occupants: list[KorkinAgent],
        present_ids: frozenset[int],
        r0_draw: int,
        zone_name: str,
    ) -> tuple[list[tuple[KorkinAgent, float]], int] | None:
        """Partners for a diner seated with its table party, or None.

        A diner at its own venue's table splits its contact draw between the
        party present at the table and the rest of the room by
        ``dining_party_contact_share``; the draw itself is unchanged, only who
        it lands on. Anyone without a party in this venue (staff on shift,
        buffet diners) keeps the venue-wide draw, as does every diner when the
        share is 0. Each of the two pools then divides its own share between
        the classes sitting in it, under ``contact_class_exponent``.
        """
        party = target.dining_party_ids
        share = self.dining_party_contact_share
        if not party or share <= 0.0 or zone_name != target.dining_zone:
            return None
        n_occupants = max(len(occupants), 1)
        n_party = 1 + len(party & present_ids)
        k = max(int(r0_draw), 0)
        if share >= 1.0 or k == 0:
            k_party = k
        else:
            k_party = int(self.rng.binomial(k, share))
        party_shedders = [(s, sv) for s, sv in shedders if s.agent_id in party]
        floor_shedders = [(s, sv) for s, sv in shedders if s.agent_id not in party]
        at_table, n_table = self._sample_contact_partners(
            party_shedders, n_party, k_party,
            self._pool_class_counts(
                (a for a in occupants if a.agent_id in party), target,
            ),
        )
        on_floor, n_floor = self._sample_contact_partners(
            floor_shedders, n_occupants - n_party + 1, k - k_party,
            self._pool_class_counts(
                (a for a in occupants if a.agent_id not in party), target,
            ),
        )
        return at_table + on_floor, n_table + n_floor

    def _hand_contact_transfers(
        self,
        target: KorkinAgent,
        sampled_shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
        cabin_confinement: bool,
    ) -> list[tuple[KorkinAgent, float]]:
        """Debit each donor's hand and return what each moved to the recipient.

        The donor's reservoir is finite and shared: N partners in one epoch draw
        down the same pair of hands, so the route cannot deliver more than the
        donor is carrying however many contacts it makes.
        """
        moved: list[tuple[KorkinAgent, float]] = []
        for shedder, _shedding in sampled_shedders:
            donor = shedder.hand_load_by_pathogen.get(pathogen_id, 0.0)
            if donor <= 0.0:
                continue
            fraction = self.rng.uniform(*HAND_TO_HAND_TRANSFER_RANGE)
            if cabin_confinement:
                fraction *= self._cabin_pair_contact_factor(shedder, target)
            amount = min(donor, donor * fraction)
            if amount <= 0.0:
                continue
            shedder.hand_load_by_pathogen[pathogen_id] = donor - amount
            moved.append((shedder, amount))
        return moved

    def _per_partner_contact_dose(
        self,
        target: KorkinAgent,
        sampled_shedders: list[tuple[KorkinAgent, float]],
        cabin_confinement: bool,
        pathogen_id: str,
        epoch: int,
    ) -> tuple[float, list[tuple[KorkinAgent, float]]]:
        """Compose interpersonal contact through the donor's hand reservoir.

        Hand-mediated close contact -- a handshake is the iconic instance, not the
        only one -- moves a measured fraction of the donor's *hand* load onto the
        recipient's hand, which then reaches the mouth through the same
        hand-to-mouth process the fomite chain uses. Droplet, emesis aerosol,
        fomite and food keep their own pathways and are not folded in here.
        """
        moved = self._hand_contact_transfers(
            target, sampled_shedders, pathogen_id, cabin_confinement,
        )
        acquired = sum(amount for _, amount in moved)
        if acquired <= 0.0:
            return 0.0, moved
        hand = target.hand_load_by_pathogen.get(pathogen_id, 0.0)
        target.hand_load_by_pathogen[pathogen_id] = hand + acquired
        dose = self._hand_to_mouth_dose(target, epoch, hand + acquired)
        target.hand_load_by_pathogen[pathogen_id] = hand + acquired - dose
        return dose * self._confinement_factor(target), moved

    def _effective_contacts(
        self,
        n_occupants: int,
        agent: KorkinAgent,
        epoch: int,
    ) -> int:
        """Occupancy-scaled contact draw for density_dependent contact_mode.

        contacts ≈ base * (n / ref)^α, optionally multiplied for a food
        employee working its service zone, capped, then Poisson-sampled.
        """
        cfg = self.density_cfg
        ref = max(float(cfg["reference_occupancy"]), 1e-9)
        base = self.clock.amount_per_epoch(float(cfg["base_contacts_per_day"]))
        alpha = float(cfg["exponent"])
        max_c = self.clock.amount_per_epoch(float(cfg["max_contacts_per_day"]))

        raw = base * (max(n_occupants, 0) / ref) ** alpha
        loc = getattr(agent, "current_location", None) or ""
        if self._on_service_duty(agent, loc, epoch):
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

    def _contact_activity(
        self,
        target: KorkinAgent,
        unit_name: str,
        zone_name: str,
        hallway: bool,
        epoch: int,
    ) -> str:
        """The contact activity a target is in, for one mixing unit (CONTACT-ARCH-01).

        Resolved from state the engine already holds -- the unit the
        architecture placed the target in, the zone's type, the schedule token
        and the duty state -- so role enters through the schedule and the
        duty assignment, not through the role label.
        """
        if hallway:
            return "corridor"
        if unit_name != zone_name:
            return "cabin"
        token = self._scheduled_activity(target, epoch).split(":", 1)[0]
        if token == "Sleep":
            return "cabin"
        if token == "Work":
            # Working is what the schedule says a host is doing, whatever the
            # room is for: a crew member in a Dining zone who is not a food
            # employee on shift there is at work, not at a meal.
            return (
                "work_service"
                if self._on_service_duty(target, zone_name, epoch)
                else "work_other"
            )
        # A meal is a meal wherever it is taken, and a Dining zone is a meal
        # for whoever is in it off `Work` and off `Sleep`.
        if token == "Meal" or self.zone_types.get(zone_name) == "Dining":
            if target.dining_party_ids and zone_name == target.dining_zone:
                return "dining_table"
            return "dining_venue"
        if token == "Free":
            return "leisure"
        return "other"

    def _activity_contact_draw(
        self,
        target: KorkinAgent,
        unit_name: str,
        zone_name: str,
        hallway: bool,
        epoch: int,
    ) -> int:
        """Contact draw from the declared per-activity rate (CONTACT-ARCH-01)."""
        rates = self.activity_contacts or {}
        activity = self._contact_activity(
            target, unit_name, zone_name, hallway, epoch,
        )
        by_role = rates[activity]
        if target.role not in by_role:
            raise ValueError(
                f"activity_contacts has no rate for role {target.role!r} in "
                f"activity {activity!r}",
            )
        per_hour = by_role[target.role]
        tau = self.activity_saturation_hours.get(activity)
        if tau is None:
            mean = self.clock.amount_per_epoch(per_hour * HOURS_PER_DAY)
        else:
            mean = self._saturated_visit_contacts(target, per_hour, tau)
        mean *= float(self.voyage_contact_multiplier)
        if mean <= 0.0:
            return 0
        return max(0, int(self.rng.poisson(mean)))

    def _saturated_visit_contacts(
        self,
        target: KorkinAgent,
        per_hour: float,
        tau: float,
    ) -> float:
        """Expected new contacts this epoch, *tau* hours into saturation.

        Cumulative contacts over a visit of ``t`` hours are
        ``per_hour * tau * (1 - exp(-t / tau))``; this epoch's share is that
        curve's increment over the hours the epoch spans, from the dwell the
        engine has recorded for the target (CONTACT-ARCH-02).
        """
        dwelt = self.clock.hours_elapsed(target.dwell_epochs)
        span = self.clock.hours_per_epoch
        return per_hour * tau * (
            math.exp(-dwelt / tau) - math.exp(-(dwelt + span) / tau)
        )

    def _draw_contact_multiplier(
        self,
        n_occupants: int,
        target: KorkinAgent,
        epoch: int,
    ) -> int:
        """Return r0_draw for direct contact under the active contact_mode."""
        if self.contact_mode in ("density_dependent", "heterogeneous_zone_dose"):
            return self._effective_contacts(n_occupants, target, epoch)
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
        """Person-to-person transmission via close contact in shared rooms.

        A ``Cabin_Corridor`` is not one room. Its occupants meet their own
        cabin at full strength (one compartment per stateroom) and the rest of
        the corridor only as the hallway residual, scaled by
        ``corridor_direct_contact_factor`` and excluding cabin mates already
        met inside.

        A table-service dining room is one room, but a seated diner's contact
        draw lands on its own table party by ``dining_party_contact_share``
        (``_seated_partner_sample``, ``per_partner_contact`` mode only).

        Within whichever pool a target draws from, ``contact_class_exponent``
        sets how the same draw divides between the classes in it: 0, the
        default, is the uniform draw this model has always made.
        """
        for unit_name, occupants, hallway in self._direct_contact_units(
            zone_occupants,
        ):
            self._direct_contact_unit(
                epoch, unit_name, occupants, hallway, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, profile, ledger,
            )

    def _direct_contact_units(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
    ) -> list[tuple[str, list[KorkinAgent], bool]]:
        """Mixing units for direct contact: (name, occupants, is_hallway)."""
        units: list[tuple[str, list[KorkinAgent], bool]] = []
        for zone_name, occupants in zone_occupants.items():
            if self.zone_types.get(zone_name) != "Cabin_Corridor":
                units.append((zone_name, occupants, False))
                continue
            cabins = self._cabin_compartments({zone_name: occupants})
            units.extend(
                (key, members, False)
                for key, members in cabins.items()
                if len(members) > 1
            )
            units.append((zone_name, occupants, True))
        return units

    @staticmethod
    def _hallway_shedders(
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
    ) -> list[tuple[KorkinAgent, float]]:
        """Shedders a target can meet in the corridor: everyone but cabin mates."""
        return [
            (s, sv) for s, sv in shedders
            if s.agent_id not in target.cabin_mate_ids
        ]

    def _direct_contact_unit(
        self,
        epoch: int,
        unit_name: str,
        occupants: list[KorkinAgent],
        hallway: bool,
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
        profile: dict | None,
        ledger: StrainDoseLedger | None,
    ) -> None:
        """Direct-contact doses for every susceptible in one mixing unit."""
        use_het = self.contact_mode == "heterogeneous_zone_dose"
        use_partner = self.contact_mode == "per_partner_contact"
        shedders = self._get_shedders(occupants, pathogen_id, profile)
        susceptible = self._get_susceptible(occupants, pathogen_id)
        if not shedders or not susceptible:
            return

        zone_name = self.compartment_parent(unit_name)
        total_shedding = sum(sv for _, sv in shedders)
        shedder_ids = [s.agent_id for s, _ in shedders]
        n_occupants = max(len(occupants), 1)
        zone_dc_factor = self._direct_contact_zone_factor(unit_name)
        cabin_confinement = self._zone_has_cabin_confinement(
            zone_name, shedders, susceptible,
        )
        zone_mix = (
            None if cabin_confinement
            else self._shedder_mix(shedders, pathogen_id)
        )
        present_ids = frozenset(a.agent_id for a in occupants)

        by_activity = use_partner and self.activity_contacts is not None
        for target in susceptible:
            if by_activity:
                r0_draw = self._activity_contact_draw(
                    target, unit_name, zone_name, hallway, epoch,
                )
            else:
                r0_draw = self._draw_contact_multiplier(
                    n_occupants, target, epoch,
                )
            sampled_shedders = shedders
            moved: list[tuple[KorkinAgent, float]] = []
            n_contacts = r0_draw
            if use_partner:
                seated = self._seated_partner_sample(
                    target, shedders, occupants, present_ids, r0_draw,
                    zone_name,
                )
                sampled_shedders, n_contacts = (
                    seated if seated is not None
                    else self._sample_contact_partners(
                        shedders, n_occupants, r0_draw,
                        self._pool_class_counts(occupants, target),
                    )
                )
                if hallway:
                    sampled_shedders = self._hallway_shedders(
                        target, sampled_shedders,
                    )
                dose, moved = self._per_partner_contact_dose(
                    target, sampled_shedders, cabin_confinement,
                    pathogen_id, epoch,
                )
            else:
                unit_shedders = shedders
                unit_shedding = total_shedding
                if hallway:
                    unit_shedders = self._hallway_shedders(target, shedders)
                    unit_shedding = sum(sv for _, sv in unit_shedders)
                dose = self._direct_contact_dose(
                    target, unit_shedders, unit_shedding, n_occupants, r0_draw,
                    cabin_confinement, pathogen_id, epoch,
                )
            dose *= self.direct_contact_scalar
            dose *= zone_dc_factor
            exposure_factor = 1.0
            if use_het:
                exposure_factor = self._zone_exposure_factor(zone_name)
                dose *= exposure_factor
            # Under composition a donor's contribution is what came off its
            # hands, not what it emitted, so the shares are transfer-weighted.
            mix = (
                self._shedder_mix(moved, pathogen_id) if use_partner
                else self._direct_contact_mix(
                    target, sampled_shedders, pathogen_id, zone_mix,
                )
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
            if unit_name != zone_name:
                rec["compartment"] = unit_name
            if use_partner:
                rec["source_ids"] = [
                    shedder.agent_id for shedder, _ in moved
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
        near_field_on = self._near_field_admits(profile)
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
                near_dose = 0.0
                if near_field_on:
                    near_dose = self._near_field_droplet_dose(
                        zone_name, target, emitted_shedders, volume,
                        vent_factor, target_factor,
                    )
                dose += near_dose
                dose = self._accumulate(
                    target.agent_id, "droplet", dose,
                    agent_doses, agent_pathway_doses,
                    attribution(ledger, mix),
                )

                exposure: dict[str, Any] = {
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "source_ids": shedder_ids,
                    "pathogen_id": pathogen_id,
                    "dose": round(dose, 4),
                    "aerosol_mass": round(total_aerosol, 4),
                    "concentration_per_m3": round(concentration, 6),
                }
                if near_dose > 0.0:
                    # Written only when the near field is on, so the payload of
                    # a run without it is the pre-change payload.
                    exposure["near_field_dose"] = round(near_dose, 4)
                matrix.droplet_exposures.append(exposure)

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
        agent: KorkinAgent | None,
        epoch: int,
    ) -> float:
        if agent is not None and self._on_service_duty(agent, zone_name, epoch):
            # SURF-KO-01 knocks the shift out, not the zone: an on-duty food
            # employee takes the diner rate Jin measured in the same
            # restaurant in the same hour, rather than falling back on its
            # zone's class -- a service zone classes as ``galley``, which is
            # the staff rate again and would knock nothing out.
            hourly = (
                SURFACE_CONTACTS_PER_HOUR["dining"]
                if self.service_surface_knockout
                else CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR
            )
        else:
            hourly = SURFACE_CONTACTS_PER_HOUR[self._fomite_zone_class(zone_name)]
        return hourly * self.clock.hours_per_epoch

    def _fomite_is_eating(self, target: KorkinAgent, epoch: int) -> bool:
        return self._scheduled_activity(target, epoch).startswith("Meal")

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
        epoch: int,
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
            self._fomite_surface_contacts(zone_name, target, epoch)
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

    def _hand_carriage_propensity(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
    ) -> float:
        """This host's probability that a defecation contaminates its hand.

        A per-host-per-infection beta-binomial draw (Liu 2013 Table 3): some
        infected hosts never carry at all, which a per-event common rate
        cannot express.
        """
        existing = agent.hand_carriage_propensity_by_pathogen.get(pathogen_id)
        if existing is not None:
            return existing
        propensity = float(self.rng.beta(*HAND_CARRIAGE_PROPENSITY_BETA))
        agent.hand_carriage_propensity_by_pathogen[pathogen_id] = propensity
        return propensity

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
        """Relax one host's hand load over one epoch.

        A profile declaring ``stool_events_per_day`` recontaminates the hand at
        a defecation *event*: between events the load only decays, and an event
        returns it to the measured Liu ceiling. A profile without that
        declaration keeps the continuous relaxation toward the ceiling, which
        holds every shedding host's hand near its maximum at all times.
        """
        target = agent.get_pathogen_hand_target(pathogen_id, profile or {})
        current = agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        if target <= 0.0 and current <= 0.0:
            return
        rate = self._hand_inactivation_rate(agent, pathogen_id, profile)
        survival = math.exp(-rate * self.clock.hours_per_epoch)
        events_per_day = self._stool_event_rate_per_day(
            agent, pathogen_id, profile,
        )
        if events_per_day is None:
            agent.hand_load_by_pathogen[pathogen_id] = (
                target + (current - target) * survival
            )
            return
        # Thin the defecation rate by this host's carriage propensity here and
        # not in _stool_event_rate_per_day: the accessor reports a physical
        # quantity the profile declares (defecation frequency), while carriage
        # is a separate mechanism conditioned on defecation. Bernoulli
        # thinning of a Poisson rate is distributionally identical to gating
        # each event, and doing it before both uses keeps the stationary-load
        # initialisation consistent with the event stream.
        events_per_day *= self._hand_carriage_propensity(agent, pathogen_id)
        if pathogen_id not in agent.hand_load_by_pathogen:
            current = self._stationary_hand_load(
                target, rate, events_per_day,
            )
        decayed = current * survival
        if self._stool_event_occurs(events_per_day):
            decayed = max(decayed, target)
        agent.hand_load_by_pathogen[pathogen_id] = decayed

    def _stationary_hand_load(
        self,
        target: float,
        inactivation_rate_per_hour: float,
        events_per_day: float,
    ) -> float:
        """Hand load for a host first seen mid-illness.

        A host that has been shedding since before this epoch has already
        defecated; starting its hand at zero would make every host's first
        exposure depend on when the first event happens to fall. The backward
        recurrence time of a Poisson process is exponential with the same
        rate, so the load is the ceiling decayed over that draw.
        """
        rate = max(events_per_day, 1e-9)
        since_days = float(self.rng.exponential(1.0 / rate))
        return target * math.exp(
            -inactivation_rate_per_hour * since_days * HOURS_PER_DAY,
        )

    def _stool_event_occurs(self, events_per_day: float) -> bool:
        """Whether at least one defecation event falls in this epoch."""
        expected = max(0.0, events_per_day) * self.clock.day_fraction_per_epoch
        probability = 1.0 - math.exp(-expected)
        return bool(self.rng.random() < probability)

    def _stool_event_rate_per_day(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict | None,
    ) -> float | None:
        """Defecation events per day for one host, or ``None``.

        ``None`` means the profile declares no stool-event arms, so this host's
        hand is maintained by the continuous path instead.
        """
        arms = (profile or {}).get("stool_events_per_day")
        if not isinstance(arms, dict):
            return None
        baseline = float(arms.get(
            "baseline", BASELINE_STOOL_EVENTS_PER_DAY,
        ))
        if not self._diarrhoea_active(agent, pathogen_id, profile or {}):
            return baseline
        return float(arms.get(
            "diarrhoeal", DIARRHOEAL_STOOL_EVENTS_PER_DAY,
        ))

    def _diarrhoea_active(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict,
    ) -> bool:
        """Whether this host is passing diarrhoeal stool in this epoch.

        Three conditions, all independent of the RNA it emits: the host is
        currently symptomatic, its drawn symptom axes include diarrhoea, and
        the phase its infection age falls in declares the diarrhoeal feature.
        A never-symptomatic, incubating or convalescent host therefore sheds
        RNA on its own curve while defecating at the non-diarrhoeal rate.
        """
        eligible = self._symptomatic_phase(agent, pathogen_id, profile)
        if eligible is None:
            return False
        phase, _ = eligible
        if not has_symptom_axis(
            agent.infections.get(pathogen_id) or {}, DIARRHOEA_AXIS,
        ):
            return False
        features = set(phase.get("features", []))
        return bool(features & DIARRHOEAL_PHASE_FEATURES)

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

    @staticmethod
    def _symptomatic_phase(
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict,
    ) -> tuple[dict, float] | None:
        """The clinical phase one currently symptomatic host sits in."""
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
        if phase is None:
            return None
        return phase, age

    def _emesis_phase(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        profile: dict,
    ) -> tuple[dict, float] | None:
        eligible = self._symptomatic_phase(agent, pathogen_id, profile)
        if eligible is None:
            return None
        phase, age = eligible
        if "vomiting" not in phase.get("features", []):
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
            "zone": self.compartment_parent(zone_name),
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
        """Surface contamination from shedders; stochastic pickup by later visitors.

        In a ``Cabin_Corridor`` a shedder's hands touch the stateroom's own
        surfaces (its toilet and fittings), so each cabin compartment carries
        its own pool. Occupants pick up from their cabin's pool and from any
        mass already on the corridor itself (emesis, an environmental source),
        so a contaminated hallway still reaches the cabins along it.
        """
        if pathogen_id == "_default" and not self.pathogen_profiles:
            # Deprecated compatibility path for unprofiled legacy harnesses;
            # delete once those harnesses migrate to pathogen profiles.
            self._pathway_fomite_legacy_default(
                epoch, zone_occupants, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, ledger,
            )
            return
        pickup_units = dict(zone_occupants)
        zone_occupants = self._cabin_compartments(zone_occupants)
        pickup_units.update(zone_occupants)
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
                    self._fomite_surface_contacts(zone_name, agent, epoch)
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
        for zone_name, occupants in pickup_units.items():
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
                        target, zone_name, surface_mass, epoch,
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

        Contamination enters through hands, one contact at a time: a shedder
        present in a food zone touches communal food, transfers a measured
        fraction of what is on the hand, and loses it off the hand. Susceptible
        agents eating in the zone receive an ingestion dose from the standing
        pool, which grows and decays between epochs.
        """
        fc = (profile or {}).get("food_contamination", {})
        if not fc.get("enabled", False):
            return

        food_zones = self.food_pools.get(pathogen_id, {})
        if not food_zones:
            return

        growth_factor, decay_factor = self._food_rate_factors(fc)
        # The fomite pathway owns hand relaxation and hygiene for every
        # occupant of every zone, and runs before this one, so this route
        # deposits from post-hygiene hands. It runs under the same
        # ``person_to_person`` switch; when that is off, this route still needs
        # a hand to deposit from, so it maintains the hands it uses itself.
        owns_hands = not (profile or {}).get(
            "environmental_contamination", {},
        ).get("person_to_person", True)

        for zone_name in food_zones:
            occupants = zone_occupants.get(zone_name, [])
            if owns_hands:
                for agent in occupants:
                    self._replenish_hand(agent, pathogen_id, profile)

            deposits = self._food_deposits(
                zone_name, occupants, pathogen_id, profile, fc, epoch,
            )
            self._deposit_reservoir_strains(
                FOOD_RESERVOIR, pathogen_id, zone_name, deposits,
            )
            for _agent, deposit in deposits:
                food_zones[zone_name] += deposit

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

            if not occupants:
                continue

            self._food_ingestion(
                zone_name, occupants, food_zones, fc, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, ledger,
            )

        if owns_hands:
            for zone_name in food_zones:
                for agent in zone_occupants.get(zone_name, []):
                    self._apply_hand_hygiene(agent, pathogen_id, profile)

    def _food_ingestion(
        self,
        zone_name: str,
        occupants: list[KorkinAgent],
        food_zones: dict[str, float],
        fc: dict[str, Any],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
        ledger: StrainDoseLedger | None,
    ) -> None:
        """Eat one zone's standing food pool down, and dose whoever it can.

        Every diner present takes an equal share of the pool off it, because a
        share eaten by an immune or already-infected diner is eaten, not left
        on the buffet for the next epoch; only a susceptible diner's share
        becomes a dose. Removing only the susceptible shares made a zone's
        pool -- and so every remaining susceptible's dose -- rise with the
        immune fraction, on top of the rise deposition already gives it.
        """
        susceptible = self._get_susceptible(occupants, pathogen_id)
        zone_mult = self._food_zone_multiplier(zone_name)
        food_attribution = attribution(
            ledger,
            self._reservoir_mix(FOOD_RESERVOIR, pathogen_id, zone_name),
        )
        n_occupants = len(occupants)
        pool_before = food_zones[zone_name]
        per_head = (
            pool_before
            / n_occupants
            * self._food_ingestion_per_epoch(fc)
            * zone_mult
        )
        eaten_each = per_head * self._delivery_scale(
            per_head * n_occupants, pool_before,
        )
        for target in susceptible:
            dose = self._accumulate(
                target.agent_id, "food", eaten_each,
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
        remaining = max(0.0, pool_before - eaten_each * n_occupants)
        food_zones[zone_name] = remaining
        if pool_before > 0.0 and remaining < pool_before:
            self._reservoir.decay(
                remaining / pool_before,
                ReservoirComposition.key(
                    FOOD_RESERVOIR, pathogen_id, zone_name,
                ),
            )

    def _food_deposits(
        self,
        zone_name: str,
        occupants: list[KorkinAgent],
        pathogen_id: str,
        profile: dict | None,
        food_cfg: dict[str, Any],
        epoch: int,
    ) -> list[tuple[KorkinAgent, float]]:
        """Hand-borne deposits into one zone's food pool, depleting the hands.

        Composed the way the fomite deposit is — contacts x per-contact
        transfer x what is on the hand — rather than as a share of the
        depositor's whole emission, which no assay measures and which let a
        hygiene lever pass straight through this route (FOOD-ARCH-01).
        """
        deposits: list[tuple[KorkinAgent, float]] = []
        for agent, _sv in self._get_shedders(occupants, pathogen_id, profile):
            if self._cabin_confinement_active(agent):
                continue
            hand = agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
            if hand <= 0.0:
                continue
            transfer = self.rng.uniform(*HAND_TO_FOOD_TRANSFER_FRACTION_RANGE)
            requested = (
                self._food_hand_contacts(zone_name, agent, food_cfg, epoch)
                * transfer
                * hand
            )
            deposit = min(hand, max(0.0, requested))
            if deposit <= 0.0:
                continue
            agent.hand_load_by_pathogen[pathogen_id] = hand - deposit
            deposits.append((agent, deposit))
        return deposits

    def _food_hand_contacts(
        self,
        zone_name: str,
        agent: KorkinAgent,
        food_cfg: dict[str, Any],
        epoch: int,
    ) -> float:
        """Bare-hand food contacts this agent makes in this zone this epoch.

        A count per day of presence, so it divides across the day's epochs. A
        food employee on shift in its own service zone is the food-handler
        channel and takes the handler multiplier; a crew member eating in a
        dining zone is a diner and does not.
        """
        per_day = float(food_cfg.get(
            "hand_food_contacts_per_day", FOOD_HAND_CONTACTS_PER_DAY,
        ))
        if self._on_service_duty(agent, zone_name, epoch):
            per_day *= float(food_cfg.get(
                "food_handler_contact_multiplier",
                FOOD_HANDLER_CONTACT_MULTIPLIER,
            ))
        return self.clock.amount_per_epoch(max(per_day, 0.0))

    def _food_ingestion_per_epoch(self, food_cfg: dict[str, Any]) -> float:
        """Share of the standing pool eaten per agent per epoch.

        A removal from a stock, so it compounds within the day. Overridable
        per profile because it is food-service turnover rather than virology
        and has to be swept (tranche 29 §3).
        """
        configured = food_cfg.get("ingestion_fraction_per_day")
        if configured is None:
            return self.food_ingestion_fraction_per_epoch
        return self.clock.decay_per_epoch(max(float(configured), 0.0))

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
        snapshot = dict(zone_occupants)
        snapshot.update(self._cabin_compartments(zone_occupants))
        for zone_name, occupants in snapshot.items():
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
