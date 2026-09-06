"""Host natural history: one owner for the course of an infection.

This module owns the per-pathogen infection record's *timeline* — the
incubation period a host drew, whether and when it presents, how severely,
when the illness ends, and when shedding ends — and the transitions that move
a record along it. The record itself still lives on the agent
(``KorkinAgent.infections`` in ``engines.infection_dynamics_bridge``), which is
where a consumer reads it; what lives here is every write that advances it and
every derived day-valued threshold read off it.

The reason for the seam is documented in
``docs/proposals/defect_resolution_plan.md`` (Track A, item A1): the reads and
the writes used to sit in four modules — the record on ``KorkinAgent``, the
transitions in ``orchestrator_epoch``, the consequences in
``engines.transmission_core``, and a boarding writer in ``engines.initiation``
— with nothing owning *which curve this host is on*. The clock and the curve
came to disagree because the transition that cleared illness and the read that
selected the curve had no common owner.

Nothing here is epidemiological: every constant is read from the pathogen
profile, and the two defaults present (``ONSET_DAY`` and the fallback recovery
day) are the legacy Person.java values that were already in force at the call
sites this module was extracted from.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from engines.incubation import (
    IncubationHost,
    IncubationModel,
    host_incubation_state,
)
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    ever_presented,
)
from engines.pharmaceutical_interventions import (
    apply_treatment_at_onset,
    illness_multiplier,
)
from engines.sim_clock import crossed_day_boundary
from engines.strain_state import ImmuneRecord, StrainRegistry
from engines.transmission_core import draw_emesis_schedule, draw_symptom_axes

# Earliest day post-infection symptoms can appear (Person.java: dpi >= 1),
# before any strain-specific incubation modifier. Used only by pathogens
# without an ``incubation`` distribution block.
ONSET_DAY = 1.0

# Illness duration for a profile that declares none, from the same source.
DEFAULT_RECOVERY_DAY = 3

__all__ = [
    "DEFAULT_RECOVERY_DAY",
    "ONSET_DAY",
    "advance_infections",
    "clearance_days",
    "draw_symptom_onset",
    "draw_symptom_severity",
    "ever_presented",
    "host_age_band",
    "incubation_days",
    "onset_day",
    "presentation_probability",
    "project_legacy_illness",
    "record_cleared_immunity",
    "severity_on_day",
    "severity_probabilities",
]


def record_cleared_immunity(
    agent: Any,
    pathogen_id: str,
    cleared: list[str],
    strain_registry: StrainRegistry | None,
    epoch: int,
) -> None:
    """Write an immune record for each lineage that just cleared.

    One record per lineage, not one per infection: a co-infected host resolves
    two exposures and comes out of it with memory of both genotypes, which is
    the whole point of sequencing a mixed infection.
    """
    if strain_registry is None:
        return
    for strain_id in cleared:
        if strain_id not in strain_registry:
            continue
        strain = strain_registry.get(strain_id)
        agent.record_immunity(ImmuneRecord(
            pathogen_id=pathogen_id,
            genotype=strain.genotype,
            strain_id=strain_id,
            epoch=epoch,
            immune_escape=strain.immune_escape,
        ))


def incubation_days(
    agent: IncubationHost,
    pathogen_id: str,
    inf: dict[str, Any],
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> float:
    """This infection's incubation period, drawn once and then remembered.

    Drawn at the first progression step rather than at infection so every entry
    point — seeding, transmission, environmental acquisition — gets a draw, and
    conditioned on the inoculum actually acquired. A pathogen with no
    ``incubation`` block keeps its fixed onset day.
    """
    stored = inf.get("incubation_days")
    if stored is not None:
        return float(stored)
    model = IncubationModel.from_mapping(profile.get("incubation"))
    if model is None:
        drawn = float(profile.get("symptom_onset_day", ONSET_DAY))
    else:
        drawn = model.sample_days(
            dose=float(inf["acquired_particles"]),
            host=host_incubation_state(agent, pathogen_id),
            rng=rng,
        )
    inf["incubation_days"] = drawn
    return drawn


def onset_day(
    agent: IncubationHost,
    pathogen_id: str,
    inf: dict[str, Any],
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> float:
    """Day post-infection this host's symptoms can first appear.

    A strain's incubation modifier shifts the host's own drawn period (negative
    = faster onset), so both halves of the phenotype axis are live for any
    pathogen whose incubation distribution has room below its median.
    """
    drawn = incubation_days(agent, pathogen_id, inf, profile, rng)
    return max(0.0, drawn + float(inf.get("strain_incubation_modifier", 0.0)))


def presentation_probability(inf: dict[str, Any], prof: dict[str, Any]) -> float:
    """Probability of presenting given infection, before the chronic boost.

    A profile carrying ``symptomatic_fraction`` presents at that measured
    proportion irrespective of acquisition dose; profiles carrying
    ``illness_probability`` keep the dose-conditional Hill form.
    """
    fixed = prof.get("symptomatic_fraction")
    if fixed is not None:
        return float(fixed)
    ill_params = prof.get("illness_probability", {})
    eta_p = ill_params.get("eta", 0.508)
    gamma_p = ill_params.get("gamma", 0.095)
    return 1.0 - math.pow(1.0 + eta_p * inf["acquired_particles"], -gamma_p)


def draw_symptom_onset(
    agent: Any,
    pid: str,
    inf: dict[str, Any],
    prof: dict[str, Any],
    rng: np.random.Generator,
    _epoch: int = 0,
) -> None:
    """One presentation draw for a host past its incubation period.

    The draw is dose-conditional for a Hill-form profile and dose-independent
    for a profile declaring ``symptomatic_fraction``.
    An imported host carries no acquisition dose, so its record states
    ``will_present`` and that boolean replaces the dose draw: without the seam
    a dose of zero would make every imported host asymptomatic and the
    boarding state axis silently void.

    Vaccination and prophylaxis scale this draw rather than the acquisition
    that preceded it, because that is where their measured effect sits: both
    reduce symptomatic influenza while leaving infection itself largely
    untouched.
    """
    forced = inf.get("will_present")
    if forced is None:
        ill_prob = presentation_probability(inf, prof)
        ill_prob = min(1.0, ill_prob + agent.get_chronic_illness_boost(pid))
        ill_prob *= illness_multiplier(agent, pid)
        presents = rng.random() < ill_prob
    else:
        presents = bool(forced)
    if presents:
        inf["illness"] = IllnessStatus.SYMPTOMATIC
        inf["onset_time_infected"] = inf.get("time_infected", 0)
        inf["presented"] = True
        draw_symptom_axes(inf, prof, rng)
        draw_emesis_schedule(agent, pid, prof, rng)
        apply_treatment_at_onset(agent, pid, inf, prof)
        if inf.get("symptom_severity") in (None, "", "asymptomatic"):
            inf["symptom_severity"] = draw_symptom_severity(
                prof, rng, host_age_band(agent),
            )
        inf["symptom_severity_peak"] = inf["symptom_severity"]
        inf["symptom_severity"] = severity_on_day(
            prof, inf["symptom_severity_peak"], 0,
        )
        if agent.illness_status == IllnessStatus.NOT_ILL:
            agent.illness_status = IllnessStatus.SYMPTOMATIC
    else:
        inf["symptom_severity"] = "asymptomatic"


def host_age_band(agent: Any) -> str:
    """The age band label one host carries, or the empty string.

    Every agent the run builds carries ``age_band``; the fallback exists for
    the minimal hosts that exercise the presentation draw alone, and it reads
    the profile's declared reference vector rather than inventing a band.
    """
    try:
        band = agent.age_band
    except AttributeError:
        return ""
    return str(band or "")


def severity_probabilities(
    severity: dict[str, Any],
    age_band: str = "",
) -> list[float]:
    """The five-state distribution one host's age band reads.

    ``base_probabilities_by_age_band`` is an exact-label lookup, as the
    incubation host factors are, and ``base_probabilities`` is the declared
    reference vector a band the profile does not name reads: severity that
    spans orders of magnitude across age cannot be interpolated between two
    labels whose numeric spans the population configs never state.
    """
    by_band = severity.get("base_probabilities_by_age_band") or {}
    vector = by_band.get(age_band) if age_band else None
    if vector is None:
        vector = severity.get("base_probabilities") or []
    return [float(value) for value in vector]


def draw_symptom_severity(
    profile: dict[str, Any],
    rng: np.random.Generator,
    age_band: str = "",
) -> str:
    """Draw one symptomatic state from the renormalised five-state prior.

    The state drawn is the **peak** of the course. Where the profile declares a
    trajectory, ``severity_on_day`` reads the day the host is on and returns
    what an observer sees on it, which is at or below this state.

    Where the profile declares ``base_probabilities_by_age_band`` the draw is
    conditioned on the host's band; the renormalisation over the four
    symptomatic states is unchanged, so what the band moves is the case mix
    within presentation and not the probability of presenting.
    """
    severity = profile.get("severity_model", {})
    states = severity.get("states", [])
    probabilities = severity_probabilities(severity, age_band)
    if len(states) != 5 or len(probabilities) != 5:
        return ""
    symptomatic_states = [str(state) for state in states[1:]]
    symptomatic_probabilities = np.asarray(probabilities[1:], dtype=float)
    symptomatic_probabilities /= symptomatic_probabilities.sum()
    return str(rng.choice(symptomatic_states, p=symptomatic_probabilities))


def severity_on_day(
    prof: dict[str, Any],
    peak_severity: str,
    day_index: int,
) -> str:
    """The severity an observer sees on one day of a course peaking at ``peak``.

    ``severity_model.trajectory_ladder_offsets_by_day`` is authored on the
    onset axis, one entry per day, like the shedding curve, and its last entry
    is held for a longer illness. Each entry is a count of rungs below the
    peak, so an absent trajectory holds the peak for the whole illness — the
    single-state behaviour this replaces, and what every shipped profile still
    gets.

    The floor is the mildest symptomatic rung. A host carrying ``SYMPTOMATIC``
    illness is never moved onto the asymptomatic rung: that rung means the host
    never presented, which is what the presentation draw decides and not
    something a day of the course can undo.
    """
    severity = prof.get("severity_model") or {}
    offsets = severity.get("trajectory_ladder_offsets_by_day") or []
    states = [str(state) for state in severity.get("states") or []]
    if not offsets or peak_severity not in states:
        return peak_severity
    peak_index = states.index(peak_severity)
    if peak_index <= 1:
        return peak_severity
    offset = int(offsets[min(max(day_index, 0), len(offsets) - 1)])
    return states[min(peak_index, max(1, peak_index + offset))]


def _advance_severity(
    clock: Any,
    inf: dict[str, Any],
    prof: dict[str, Any],
    epochs_infected: int,
) -> None:
    """Move this epoch's visible severity along the host's own course.

    Read from the peak and the day rather than accumulated from the last
    epoch, so the path does not depend on how finely time is cut and a record
    written before this seam existed still resolves.
    """
    peak = inf.get("symptom_severity_peak")
    onset_time = inf.get("onset_time_infected")
    if not peak or onset_time is None:
        return
    day_index = clock.day_index(max(0, epochs_infected - int(onset_time)))
    inf["symptom_severity"] = severity_on_day(prof, peak, day_index)


def clearance_days(
    agent: Any,
    pid: str,
    inf: dict[str, Any],
    prof: dict[str, Any],
    onset: float,
) -> tuple[float, float]:
    """Illness and shedding clearance days for one infection, both from onset.

    ``recovery_day`` is the illness duration; ``shedding_duration_days`` is the
    infectious period, and a profile that omits it says the two coincide. The
    shedding threshold is never earlier than the illness one, so a host whose
    illness is extended keeps shedding to the end of that illness.

    The infection record is read before the profile, because a chronic shedder
    carries a host-specific infectious period stamped onto the record at
    infection.
    """
    recovery_day = agent.get_chronic_recovery_day(
        pid, inf.get("recovery_day", prof.get("recovery_day", DEFAULT_RECOVERY_DAY)),
    )
    shedding_duration = float(
        inf.get(
            "shedding_duration_days",
            prof.get("shedding_duration_days", recovery_day),
        ),
    )
    return (
        onset + recovery_day,
        onset + max(shedding_duration, float(recovery_day)),
    )


def _clear_emesis_records(agent: Any, pid: str) -> None:
    """Drop the emesis records an ended illness leaves behind."""
    agent.emesis_episode_schedule_by_pathogen.pop(pid, None)
    agent.emesis_episode_load_by_pathogen.pop(pid, None)
    agent.emesis_deposition_records_by_pathogen.pop(pid, None)


def advance_infections(
    agent: Any,
    pathogen_profiles: dict[str, dict[str, Any]],
    rng: np.random.Generator,
    strain_registry: StrainRegistry | None = None,
    epoch: int = 0,
) -> None:
    """Advance every open infection on one host by a single epoch."""
    clock = agent.clock
    for pid, inf in tuple(agent.infections.items()):
        if inf["status"] != InfectionStatus.INFECTED:
            continue
        prof = pathogen_profiles.get(pid, {})

        if inf["time_infected"] is not None:
            inf["time_infected"] += 1

        # The counter is in epochs; every threshold below is in days.
        epochs_infected = inf["time_infected"] or 0
        days_infected = clock.days_elapsed(epochs_infected)
        onset = onset_day(agent, pid, inf, prof, rng)
        if (
            inf["illness"] == IllnessStatus.NOT_ILL
            and crossed_day_boundary(clock, epochs_infected, onset)
        ):
            # Once per day of natural history, not once per epoch, so the chance
            # of presenting does not depend on how finely time is cut — and the
            # first chance is the epoch that crosses this host's own drawn
            # incubation period, so onset is not rounded up to a whole day.
            draw_symptom_onset(agent, pid, inf, prof, rng, epoch)
        elif inf["illness"] == IllnessStatus.SYMPTOMATIC:
            _advance_severity(clock, inf, prof, epochs_infected)

        illness_clearance_day, shedding_clearance_day = clearance_days(
            agent, pid, inf, prof, onset,
        )
        if (
            days_infected >= illness_clearance_day
            and inf["illness"] == IllnessStatus.SYMPTOMATIC
        ):
            # Illness ends on its own clock, and the emesis records are part of
            # the illness: convalescent shedding is faecal, not emetic.
            inf["illness"] = IllnessStatus.RECOVERED
            _clear_emesis_records(agent, pid)
        cleared: list[str] = []
        # Co-resident lineages clear on their own clocks, so the pathogen-level
        # infection stays open until the last one goes: a strain acquired on
        # day four is still being shed when the primary infection would have
        # ended. A lineage is carried for as long as it is shed, not only for
        # as long as the host is ill.
        residents_left = agent.advance_resident_strains(
            pid, shedding_clearance_day, cleared,
        )
        record_cleared_immunity(agent, pid, cleared, strain_registry, epoch)
        if days_infected >= shedding_clearance_day and residents_left == 0:
            # The hand load has to survive convalescent shedding, so it is
            # dropped with the infection rather than with the illness.
            inf["status"] = InfectionStatus.RECOVERED
            inf["illness"] = IllnessStatus.RECOVERED
            agent.cumulative_exposure.pop(pid, None)
            agent.cumulative_exposure_by_route.pop(pid, None)
            agent.hand_load_by_pathogen.pop(pid, None)
            _clear_emesis_records(agent, pid)


def project_legacy_illness(agent: Any) -> None:
    """Rewrite the agent-level illness fields from the per-pathogen records.

    The agent-level fields are a summary channel, not a second state machine:
    every summary, VSP threshold and legacy prevalence series reads them, and
    they used to be updated only on the transitions the fallback happened to
    see. A host re-infected before its last lineage cleared therefore never
    reached agent-level recovery and latched SYMPTOMATIC for the rest of the
    voyage, while the records it shadows kept moving.

    A host with no records keeps whatever the fallback path gave it.
    """
    if not agent.infections:
        return
    active = [
        inf for inf in agent.infections.values()
        if inf["status"] == InfectionStatus.INFECTED
    ]
    if not active:
        if agent.infection_status == InfectionStatus.INFECTED:
            agent.infection_status = InfectionStatus.RECOVERED
            agent.illness_status = IllnessStatus.RECOVERED
        return
    agent.infection_status = InfectionStatus.INFECTED
    agent.time_infected = max(inf["time_infected"] or 0 for inf in active)
    symptomatic = any(
        inf["illness"] == IllnessStatus.SYMPTOMATIC for inf in active
    )
    agent.illness_status = (
        IllnessStatus.SYMPTOMATIC if symptomatic else IllnessStatus.NOT_ILL
    )
