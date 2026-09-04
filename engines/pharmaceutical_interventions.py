"""Vaccination and antiviral policy as declared scenario axes.

Both interventions here are split along the same two axes, because the
evidence splits that way and a single "protection" scalar would hide it:

- **Acquisition**: does the host become infected at all?
- **Illness given infection**: does an infected host become a case?

Influenza vaccination and oseltamivir post-exposure prophylaxis both act
almost entirely on the second axis. Presa 2025 titles the finding
"morbidity benefits amid low infection prevention", and Zhao 2024's WHO
network meta-analysis finds neuraminidase-inhibitor prophylaxis
"probably ha[s] little or no effect on prevention of asymptomatic
influenza virus infection" while cutting *symptomatic* influenza to
RR 0.40. So the acquisition axis defaults to zero effect for both and is
exposed as a sweep, rather than being folded into a profile's
``base_susceptibility`` where it would silently absorb transmission
error.

Nothing here is fitted. Every default is either a pooled measurement with
its source recorded on the field, or an explicit zero where the evidence
does not support an effect.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

# Pooled vaccine efficacy against laboratory-confirmed (symptomatic)
# influenza, Ge 2025 (Clin Microbiol Infect, 26 RCTs, 104,931 participants,
# DOI 10.1016/j.cmi.2025.09.005): 48.48% (95% CI 41.9-54.29). With the
# acquisition axis at zero this is exactly the illness-given-infection term.
DEFAULT_VACCINE_EFFICACY_AGAINST_ILLNESS = 0.4848

# Oseltamivir post-exposure prophylaxis against symptomatic influenza in
# hosts at high risk of severe disease, Zhao 2024 (Lancet 404:1841, WHO
# guideline NMA, DOI 10.1016/S0140-6736(24)01357-6): RR 0.40 (0.26-0.62),
# moderate certainty. The same review finds little or no effect on
# asymptomatic infection, which is why the acquisition term is zero.
DEFAULT_PROPHYLAXIS_EFFICACY_AGAINST_ILLNESS = 0.60

# Oseltamivir treatment started early shortens illness by about a day:
# Fry 2014 (Lancet Infect Dis 14:109, RCT, n=1190) median symptom duration
# 3 vs 4 days, and shortens shedding (virus isolation cut 15.2% / 30.2% /
# 47.5% at days 2 / 4 / 7).
DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS = 1.0

# Whether treating an index case reduces onward transmission is NOT
# established: Ng 2010 found household secondary infection odds 0.54
# (0.11-2.57) with treatment within 24 h, an interval spanning no effect.
# The default is therefore no effect, and the field exists so the question
# can be swept rather than assumed.
DEFAULT_TREATMENT_TRANSMISSION_MULTIPLIER = 1.0

# Beyond this the antiviral benefit is not claimed. Fry 2014 still measured
# a shedding effect past 48 h, so this is a declared operational cutoff.
DEFAULT_TREATMENT_WINDOW_HOURS = 48.0


def _bounded(value: Any, name: str, default: float = 0.0) -> float:
    """Read one probability-valued knob, rejecting anything outside [0, 1]."""
    if value is None:
        return float(default)
    number = float(value)
    if not np.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must lie in [0, 1], got {value!r}")
    return number


def _non_negative(value: Any, name: str, default: float = 0.0) -> float:
    """Read one duration- or multiplier-valued knob that cannot go negative."""
    if value is None:
        return float(default)
    number = float(value)
    if not np.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be non-negative, got {value!r}")
    return number


def _coverage_by_role(raw: Any, name: str) -> dict[str, float]:
    """Read a role-keyed coverage map, e.g. ``{"crew": 0.955}``.

    Roles are the manifest's own ("passenger", "crew"); a role absent from
    the map is uncovered, which keeps a partially-specified manifest from
    quietly covering everybody.
    """
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{name} must be a mapping of role to coverage")
    return {
        str(role): _bounded(value, f"{name}.{role}")
        for role, value in raw.items()
    }


@dataclass(frozen=True)
class VaccinationPolicy:
    """Manifest vaccination coverage and its two efficacy axes."""

    coverage_by_role: Mapping[str, float] = field(default_factory=dict)
    efficacy_against_acquisition: float = 0.0
    efficacy_against_illness: float = DEFAULT_VACCINE_EFFICACY_AGAINST_ILLNESS

    @classmethod
    def from_config(cls, raw: Mapping[str, Any]) -> VaccinationPolicy:
        return cls(
            coverage_by_role=_coverage_by_role(
                raw.get("coverage_by_role"), "vaccination.coverage_by_role",
            ),
            efficacy_against_acquisition=_bounded(
                raw.get("efficacy_against_acquisition"),
                "vaccination.efficacy_against_acquisition",
            ),
            efficacy_against_illness=_bounded(
                raw.get("efficacy_against_illness"),
                "vaccination.efficacy_against_illness",
                DEFAULT_VACCINE_EFFICACY_AGAINST_ILLNESS,
            ),
        )


@dataclass(frozen=True)
class AntiviralPolicy:
    """Oseltamivir treatment and post-exposure prophylaxis, kept separate.

    Treatment reaches hosts who become cases; prophylaxis reaches hosts who
    have not. They carry their own coverage, their own timing and their own
    effects, so a scenario can run either alone.
    """

    treatment_coverage_by_role: Mapping[str, float] = field(default_factory=dict)
    treatment_start_hours_after_onset: float = 0.0
    treatment_window_hours: float = DEFAULT_TREATMENT_WINDOW_HOURS
    treatment_illness_reduction_days: float = (
        DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS
    )
    treatment_shedding_reduction_days: float = (
        DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS
    )
    treatment_transmission_multiplier: float = (
        DEFAULT_TREATMENT_TRANSMISSION_MULTIPLIER
    )
    prophylaxis_coverage_by_role: Mapping[str, float] = field(
        default_factory=dict,
    )
    prophylaxis_efficacy_against_acquisition: float = 0.0
    prophylaxis_efficacy_against_illness: float = (
        DEFAULT_PROPHYLAXIS_EFFICACY_AGAINST_ILLNESS
    )

    @classmethod
    def from_config(cls, raw: Mapping[str, Any]) -> AntiviralPolicy:
        treatment = raw.get("treatment") or {}
        prophylaxis = raw.get("prophylaxis") or {}
        return cls(
            treatment_coverage_by_role=_coverage_by_role(
                treatment.get("coverage_by_role"),
                "antiviral.treatment.coverage_by_role",
            ),
            treatment_start_hours_after_onset=_non_negative(
                treatment.get("start_hours_after_onset"),
                "antiviral.treatment.start_hours_after_onset",
            ),
            treatment_window_hours=_non_negative(
                treatment.get("window_hours"),
                "antiviral.treatment.window_hours",
                DEFAULT_TREATMENT_WINDOW_HOURS,
            ),
            treatment_illness_reduction_days=_non_negative(
                treatment.get("illness_reduction_days"),
                "antiviral.treatment.illness_reduction_days",
                DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS,
            ),
            treatment_shedding_reduction_days=_non_negative(
                treatment.get("shedding_reduction_days"),
                "antiviral.treatment.shedding_reduction_days",
                DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS,
            ),
            treatment_transmission_multiplier=_non_negative(
                treatment.get("transmission_multiplier"),
                "antiviral.treatment.transmission_multiplier",
                DEFAULT_TREATMENT_TRANSMISSION_MULTIPLIER,
            ),
            prophylaxis_coverage_by_role=_coverage_by_role(
                prophylaxis.get("coverage_by_role"),
                "antiviral.prophylaxis.coverage_by_role",
            ),
            prophylaxis_efficacy_against_acquisition=_bounded(
                prophylaxis.get("efficacy_against_acquisition"),
                "antiviral.prophylaxis.efficacy_against_acquisition",
            ),
            prophylaxis_efficacy_against_illness=_bounded(
                prophylaxis.get("efficacy_against_illness"),
                "antiviral.prophylaxis.efficacy_against_illness",
                DEFAULT_PROPHYLAXIS_EFFICACY_AGAINST_ILLNESS,
            ),
        )


@dataclass(frozen=True)
class PathogenPharmacology:
    """The vaccination and antiviral policies in force for one pathogen."""

    vaccination: VaccinationPolicy | None = None
    antiviral: AntiviralPolicy | None = None


def resolve_pharmacology(
    cfg: Mapping[str, Any] | None,
) -> dict[str, PathogenPharmacology]:
    """Read ``cfg['pharmaceutical_interventions']`` into per-pathogen policies.

    A run that declares nothing gets an empty mapping and behaves exactly as
    it did before this module existed.
    """
    raw = (cfg or {}).get("pharmaceutical_interventions")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("pharmaceutical_interventions must be a mapping")
    resolved: dict[str, PathogenPharmacology] = {}
    for pathogen_id, block in raw.items():
        if not isinstance(block, Mapping):
            raise ValueError(
                f"pharmaceutical_interventions.{pathogen_id} must be a mapping",
            )
        vaccination = block.get("vaccination")
        antiviral = block.get("antiviral")
        resolved[str(pathogen_id)] = PathogenPharmacology(
            vaccination=(
                VaccinationPolicy.from_config(vaccination)
                if isinstance(vaccination, Mapping)
                else None
            ),
            antiviral=(
                AntiviralPolicy.from_config(antiviral)
                if isinstance(antiviral, Mapping)
                else None
            ),
        )
    return resolved


def _covered(
    coverage_by_role: Mapping[str, float],
    role: str,
    rng: np.random.Generator,
) -> bool:
    """One coverage draw for this host's role."""
    probability = float(coverage_by_role.get(role, 0.0))
    return probability > 0.0 and rng.random() < probability


def assign_host_pharmacology(
    agents: list[Any],
    pharmacology: Mapping[str, PathogenPharmacology],
    rng: np.random.Generator,
) -> None:
    """Draw vaccination and prophylaxis status, and apply acquisition effects.

    Acquisition protection multiplies ``susceptibility_multiplier``, which
    keeps it visibly separate from the profile's ``base_susceptibility``:
    that field is pathogen biology, this one is what the manifest did to the
    host. Illness protection is stored rather than applied, because it is
    conditional on an infection that has not happened yet.
    """
    for pathogen_id, policies in pharmacology.items():
        for agent in agents:
            state = _draw_host_state(agent, policies, rng)
            agent.pharma_by_pathogen[pathogen_id] = state
            if pathogen_id in agent.susceptibility_multiplier:
                agent.susceptibility_multiplier[pathogen_id] *= float(
                    state["acquisition_multiplier"],
                )


def _draw_host_state(
    agent: Any,
    policies: PathogenPharmacology,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Everything one host's manifest status implies, drawn once."""
    role = str(getattr(agent, "role", ""))
    vaccination = policies.vaccination
    antiviral = policies.antiviral
    vaccinated = bool(
        vaccination and _covered(vaccination.coverage_by_role, role, rng),
    )
    prophylaxed = bool(
        antiviral
        and _covered(antiviral.prophylaxis_coverage_by_role, role, rng),
    )
    treatment_covered = bool(
        antiviral
        and _covered(antiviral.treatment_coverage_by_role, role, rng),
    )
    acquisition = 1.0
    illness = 1.0
    if vaccinated and vaccination is not None:
        acquisition *= 1.0 - vaccination.efficacy_against_acquisition
        illness *= 1.0 - vaccination.efficacy_against_illness
    if prophylaxed and antiviral is not None:
        acquisition *= 1.0 - antiviral.prophylaxis_efficacy_against_acquisition
        illness *= 1.0 - antiviral.prophylaxis_efficacy_against_illness
    state: dict[str, Any] = {
        "vaccinated": vaccinated,
        "prophylaxis": prophylaxed,
        "treatment_covered": treatment_covered,
        "acquisition_multiplier": acquisition,
        "illness_multiplier": illness,
        "treated": False,
    }
    state.update(_treatment_terms(treatment_covered, antiviral))
    return state


def _treatment_terms(
    covered: bool,
    policy: AntiviralPolicy | None,
) -> dict[str, Any]:
    """Resolve this host's treatment effects once, at assignment.

    The effects are static per role and pathogen, so they are resolved here
    and carried on the host. The epoch loop then doses a host from its own
    record, and no policy object has to be threaded through it.
    """
    if policy is None or not covered:
        return {"treatment_reaches_host": False}
    return {
        # A dose arriving after the benefit window is no dose at all.
        "treatment_reaches_host": (
            policy.treatment_start_hours_after_onset
            <= policy.treatment_window_hours
        ),
        "treatment_illness_reduction_days": (
            policy.treatment_illness_reduction_days
        ),
        "treatment_shedding_reduction_days": (
            policy.treatment_shedding_reduction_days
        ),
        "treatment_transmission_multiplier": (
            policy.treatment_transmission_multiplier
        ),
    }


def illness_multiplier(agent: Any, pathogen_id: str) -> float:
    """Factor on this host's probability of becoming a case, given infection."""
    state = getattr(agent, "pharma_by_pathogen", {}).get(pathogen_id)
    if not state:
        return 1.0
    return float(state["illness_multiplier"])


def apply_treatment_at_onset(
    agent: Any,
    pathogen_id: str,
    infection: dict[str, Any],
    profile: Mapping[str, Any],
) -> bool:
    """Dose a host that has just become a case, and stamp the effects.

    Treatment shortens this host's illness and infectious period and scales
    its onward shedding. The values are written onto the infection record
    because that is where the epoch loop already looks first, ahead of the
    profile, for a host-specific natural history.
    """
    state = getattr(agent, "pharma_by_pathogen", {}).get(pathogen_id)
    if not state or not state.get("treatment_reaches_host"):
        return False
    recovery_day = float(
        infection.get("recovery_day", profile.get("recovery_day", 3)),
    )
    shedding_days = float(
        infection.get(
            "shedding_duration_days",
            profile.get("shedding_duration_days", recovery_day),
        ),
    )
    infection["recovery_day"] = max(
        0.0,
        recovery_day - float(state["treatment_illness_reduction_days"]),
    )
    infection["shedding_duration_days"] = max(
        0.0,
        shedding_days - float(state["treatment_shedding_reduction_days"]),
    )
    infection["shedding_multiplier"] = (
        float(infection.get("shedding_multiplier", 1.0))
        * float(state["treatment_transmission_multiplier"])
    )
    state["treated"] = True
    return True
