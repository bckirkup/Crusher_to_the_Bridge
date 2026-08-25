"""
Resolve time-dependent clinical syndromes and features from pathogen profiles.

Observed syndromes drive cascade assay routing. Severity
(``symptom_presentation``) remains a separate orthogonal axis.
"""

from __future__ import annotations

from typing import Any

SYNDROME_TOKENS = frozenset({
    "gastrointestinal",
    "respiratory",
    "systemic_febrile",
    "rash",
    "wound_soft_tissue",
    "neurologic",
})


def _infection_is_active(info: Any) -> bool:
    if not isinstance(info, dict):
        return False
    status = str(info.get("status", "")).upper()
    return status == "INFECTED"


def _infection_is_symptomatic(info: Any) -> bool:
    if not isinstance(info, dict):
        return False
    illness = str(info.get("illness", "")).upper()
    return illness == "SYMPTOMATIC"


def resolve_phase(
    presentation: dict[str, Any],
    dpi: int,
) -> dict[str, Any] | None:
    """Return the presentation phase matching *dpi*, if any."""
    phases = presentation.get("phases") or []
    if not phases:
        return None
    matched: dict[str, Any] | None = None
    for phase in phases:
        dpi_min = int(phase.get("dpi_min", 0))
        dpi_max = phase.get("dpi_max", None)
        if dpi < dpi_min:
            continue
        if dpi_max is not None and dpi > int(dpi_max):
            continue
        matched = phase
    if matched is not None:
        return matched
    # Past last bounded phase → use last phase with dpi_max null or highest dpi_min
    open_ended = [p for p in phases if p.get("dpi_max") is None]
    if open_ended:
        return max(open_ended, key=lambda p: int(p.get("dpi_min", 0)))
    return max(phases, key=lambda p: int(p.get("dpi_min", 0)))


def presentation_for_pathogen(
    pathogen_id: str,
    pathogen_profiles: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if not pathogen_profiles:
        return {}
    profile = pathogen_profiles.get(pathogen_id) or {}
    block = profile.get("clinical_presentation")
    return block if isinstance(block, dict) else {}


def _noise_reason_to_syndrome(
    noise_categories: list[dict[str, Any]] | None,
) -> dict[str, str]:
    reason_to_syndrome: dict[str, str] = {}
    for cat in noise_categories or []:
        reason = str(cat.get("reason", ""))
        syn = cat.get("syndrome")
        if reason and syn:
            reason_to_syndrome[reason] = str(syn)
    # Defaults if config omitted syndrome
    reason_to_syndrome.setdefault("seasickness", "gastrointestinal")
    reason_to_syndrome.setdefault("fatigue", "systemic_febrile")
    reason_to_syndrome.setdefault("minor_injury", "wound_soft_tissue")
    return reason_to_syndrome


def _stamp_noise_syndrome_on_agent(
    agent: dict[str, Any],
    reason: str,
    reason_to_syndrome: dict[str, str],
) -> None:
    if agent.get("observed_syndromes"):
        return
    syn = reason_to_syndrome.get(reason)
    if not syn:
        return
    agent["observed_syndromes"] = [syn]
    agent["days_since_symptom_onset"] = max(
        1, int(agent.get("days_since_symptom_onset") or 1),
    )


def apply_noise_syndromes_to_agents(
    agents: list[dict[str, Any]],
    syn_result: dict[str, Any],
    noise_categories: list[dict[str, Any]] | None = None,
) -> None:
    """Stamp observed_syndromes on noise sick-call agents from category config."""
    reason_to_syndrome = _noise_reason_to_syndrome(noise_categories)
    by_id = {int(a["agent_id"]): a for a in agents}
    for entry in syn_result.get("noise_reasons") or []:
        if not isinstance(entry, dict):
            continue
        aid = int(entry.get("agent_id", -1))
        reason = str(entry.get("reason", ""))
        agent = by_id.get(aid)
        if agent is None:
            continue
        _stamp_noise_syndrome_on_agent(agent, reason, reason_to_syndrome)


def _collect_phase_features(
    phase: dict[str, Any] | None,
    seen_feat: set[str],
    features: list[str],
) -> list[Any] | None:
    if phase is None:
        return None
    for feat in phase.get("features") or []:
        key = str(feat)
        if key not in seen_feat:
            seen_feat.add(key)
            features.append(key)
    return phase.get("syndromes")


def _append_unique_syndromes(
    base_syndromes: list[Any],
    seen_syn: set[str],
    syndromes: list[str],
) -> None:
    for syn in base_syndromes:
        key = str(syn)
        if key in SYNDROME_TOKENS and key not in seen_syn:
            seen_syn.add(key)
            syndromes.append(key)


def annotate_agent_clinical_presentation(
    agent: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    """Mutate *agent* with observed_syndromes, clinical_features, days_since_symptom_onset.

    Only *symptomatic* active infections contribute syndromes/features.
    """
    infections = agent.get("pathogen_infections") or {}
    syndromes: list[str] = []
    features: list[str] = []
    max_symptom_days = 0
    seen_syn: set[str] = set()
    seen_feat: set[str] = set()

    for pid, info in infections.items():
        if not _infection_is_active(info) or not _infection_is_symptomatic(info):
            continue
        dpi = int(info.get("days_post_infection") or 0)
        recorded_symptom_days = info.get("days_since_symptom_onset")
        if recorded_symptom_days is None:
            # Fallback for legacy payloads and hosts whose onset was not saved.
            symptom_days = max(1, dpi)
            phase_day = dpi
        else:
            symptom_days = max(1, int(recorded_symptom_days))
            phase_day = symptom_days
        max_symptom_days = max(max_symptom_days, symptom_days)
        presentation = presentation_for_pathogen(str(pid), pathogen_profiles)
        phase = resolve_phase(presentation, phase_day)
        phase_syndromes = _collect_phase_features(phase, seen_feat, features)
        base_syndromes = phase_syndromes or presentation.get("syndromes") or []
        _append_unique_syndromes(base_syndromes, seen_syn, syndromes)

    agent["observed_syndromes"] = syndromes
    agent["clinical_features"] = features
    agent["days_since_symptom_onset"] = max_symptom_days if syndromes else 0
    return agent


def annotate_agents_clinical_presentation(
    agents: list[dict[str, Any]],
    pathogen_profiles: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    for agent in agents:
        annotate_agent_clinical_presentation(agent, pathogen_profiles)
    return agents
