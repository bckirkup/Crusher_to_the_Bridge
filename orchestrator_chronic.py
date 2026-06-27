"""
orchestrator_chronic.py – Chronic disease initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Loads chronic disease profiles from JSON config, assigns diseases
to agents based on per-class prevalence, and applies pathogen
susceptibility / severity modifiers.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import KorkinShipEngine
from simulation_utils.paths import resolve_repo_path


from simulation_utils.numeric import float_ne


def load_chronic_disease_config(
    cfg: dict[str, Any],
    repo_root: str = "",
) -> dict[str, dict[str, Any]]:
    """Load chronic disease profiles from JSON config.

    Returns ``{disease_id: disease_profile}`` or empty dict when disabled.
    """
    cd_cfg = cfg.get("chronic_disease", {})
    if not cd_cfg.get("enabled", False):
        return {}
    config_path = cd_cfg.get("config_path", "data/config/chronic_diseases.json")
    full_path = resolve_repo_path(repo_root, config_path) if repo_root else config_path
    if not os.path.isfile(full_path):
        return {}
    with open(full_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    diseases: dict[str, dict[str, Any]] = {}
    for d in data.get("diseases", []):
        did = d.get("disease_id", "")
        if did:
            diseases[did] = d
    return diseases


def assign_chronic_diseases(
    engine: KorkinShipEngine,
    chronic_config: dict[str, dict[str, Any]],
    pathogen_profiles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
    rng: np.random.Generator,
) -> dict[int, list[str]]:
    """Assign chronic diseases to agents based on class prevalence.

    For each agent and each disease, roll independently using the
    disease's ``prevalence_by_class`` for the agent's class (falling
    back to ``default``).  Respects ``max_comorbid`` cap.

    Applies pathogen susceptibility modifiers to the agent's existing
    ``susceptibility_multiplier`` dict (multiplicative composition with
    any pre-existing immunocompromised multiplier).

    Returns ``{agent_id: [disease_ids]}`` mapping.
    """
    if not chronic_config:
        return {}

    cd_cfg = cfg.get("chronic_disease", {})
    allow_comorbid = cd_cfg.get("allow_comorbid", True)
    max_comorbid = cd_cfg.get("max_comorbid", 2)

    assignments: dict[int, list[str]] = {}

    disease_list = list(chronic_config.items())

    for agent in engine.agents:
        if agent.immune:
            continue

        assigned: list[str] = []

        for disease_id, disease_profile in disease_list:
            if not allow_comorbid and assigned:
                break
            if len(assigned) >= max_comorbid:
                break

            prevalence_map = disease_profile.get("prevalence_by_class", {})
            prevalence = prevalence_map.get(
                agent.agent_class,
                prevalence_map.get("default", 0.0),
            )

            if prevalence <= 0.0:
                continue
            if rng.random() >= prevalence:
                continue

            pathogen_mods = disease_profile.get("pathogen_modifiers", {})
            wearable_scale = disease_profile.get(
                "wearable_infection_response_scale", 1.0,
            )

            agent.apply_chronic_disease(disease_id, pathogen_mods, wearable_scale)

            # Apply susceptibility multipliers to existing per-pathogen
            # susceptibility (multiplicative composition).
            for pid in pathogen_profiles:
                pmods = pathogen_mods.get(pid, pathogen_mods.get("default", {}))
                susc_mult = pmods.get("susceptibility_multiplier", 1.0)
                if float_ne(susc_mult, 1.0):
                    current = agent.susceptibility_multiplier.get(pid, 1.0)
                    agent.susceptibility_multiplier[pid] = current * susc_mult

            assigned.append(disease_id)

        if assigned:
            assignments[agent.agent_id] = assigned

    return assignments


def get_chronic_wearable_offsets(
    chronic_config: dict[str, dict[str, Any]],
    assignments: dict[int, list[str]],
) -> dict[int, dict[str, float]]:
    """Compute per-agent wearable baseline offsets from chronic diseases.

    Returns ``{agent_id: {channel: offset}}`` with additive offsets.
    """
    offsets: dict[int, dict[str, float]] = {}
    for agent_id, disease_ids in assignments.items():
        agent_offsets: dict[str, float] = {}
        for did in disease_ids:
            disease = chronic_config.get(did, {})
            wb_offsets = disease.get("wearable_baseline_offsets", {})
            for ch, val in wb_offsets.items():
                agent_offsets[ch] = agent_offsets.get(ch, 0.0) + float(val)
        if agent_offsets:
            offsets[agent_id] = agent_offsets
    return offsets


def get_chronic_medications(
    chronic_config: dict[str, dict[str, Any]],
    assignments: dict[int, list[str]],
) -> dict[int, list[str]]:
    """Collect chronic medications for each agent.

    Returns ``{agent_id: [medication_names]}``.
    """
    meds: dict[int, list[str]] = {}
    for agent_id, disease_ids in assignments.items():
        agent_meds: list[str] = []
        for did in disease_ids:
            disease = chronic_config.get(did, {})
            agent_meds.extend(disease.get("chronic_medications", []))
        if agent_meds:
            meds[agent_id] = agent_meds
    return meds


def get_chronic_behavioral_modifiers(
    chronic_config: dict[str, dict[str, Any]],
    assignments: dict[int, list[str]],
) -> dict[int, dict[str, float]]:
    """Compute per-agent behavioral modifiers from chronic diseases.

    Returns ``{agent_id: {"sick_call_probability_boost": float,
    "quarantine_compliance_boost": float}}``.
    """
    result: dict[int, dict[str, float]] = {}
    for agent_id, disease_ids in assignments.items():
        agent_mods: dict[str, float] = {}
        for did in disease_ids:
            disease = chronic_config.get(did, {})
            beh = disease.get("behavioral_modifiers", {})
            for key, val in beh.items():
                agent_mods[key] = agent_mods.get(key, 0.0) + float(val)
        # Cap boosts
        if "sick_call_probability_boost" in agent_mods:
            agent_mods["sick_call_probability_boost"] = min(
                0.30, agent_mods["sick_call_probability_boost"],
            )
        if "quarantine_compliance_boost" in agent_mods:
            agent_mods["quarantine_compliance_boost"] = min(
                0.15, agent_mods["quarantine_compliance_boost"],
            )
        if agent_mods:
            result[agent_id] = agent_mods
    return result


def print_chronic_disease_summary(
    chronic_config: dict[str, dict[str, Any]],
    assignments: dict[int, list[str]],
    total_agents: int,
) -> None:
    """Print chronic disease assignment summary to console."""
    if not assignments:
        print("  Chronic disease: disabled or no assignments")
        return

    print(f"  Chronic disease agents: {len(assignments)}/{total_agents}")
    disease_counts: dict[str, int] = {}
    for disease_ids in assignments.values():
        for did in disease_ids:
            disease_counts[did] = disease_counts.get(did, 0) + 1
    for did, count in sorted(disease_counts.items()):
        name = chronic_config.get(did, {}).get("name", did)
        print(f"    {name}: {count} agents")
    comorbid = sum(1 for dids in assignments.values() if len(dids) > 1)
    if comorbid > 0:
        print(f"    Comorbid (2+ diseases): {comorbid} agents")
    print()
