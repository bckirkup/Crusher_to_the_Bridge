"""Static agent profiles for decision-layer hooks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from simulation_utils.paths import validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class AgentProfile:
    profile_id: str
    agent_id: int
    agent_class: str
    role_group: str
    gender: str
    age_band: str = "adult"
    immune: bool = False
    immunocompromised: bool = False
    comorbidities: list[str] = field(default_factory=list)
    vaccinations: list[str] = field(default_factory=list)
    chronic_meds: list[str] = field(default_factory=list)
    chronic_disease_ids: list[str] = field(default_factory=list)
    device_id: str = ""
    monitored_channels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "agent_class": self.agent_class,
            "role_group": self.role_group,
            "gender": self.gender,
            "age_band": self.age_band,
            "immune": self.immune,
            "immunocompromised": self.immunocompromised,
            "comorbidities": list(self.comorbidities),
            "vaccinations": list(self.vaccinations),
            "chronic_meds": list(self.chronic_meds),
            "chronic_disease_ids": list(self.chronic_disease_ids),
            "device_id": self.device_id,
            "monitored_channels": list(self.monitored_channels),
        }


def load_agent_profile_bundle(path: str) -> dict[str, Any]:
    with validated_open(path, allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _build_device_map(
    class_device_map: dict[str, str] | list | None,
) -> dict[str, str]:
    if isinstance(class_device_map, dict):
        return class_device_map
    device_map: dict[str, str] = {}
    if isinstance(class_device_map, list):
        for entry in class_device_map:
            if isinstance(entry, dict) and "agent_class" in entry:
                device_map[str(entry["agent_class"])] = str(entry.get("device_id", ""))
    return device_map


def _profile_for_agent(
    agent: Any,
    templates: dict[str, Any],
    default_template: dict[str, Any],
    device_map: dict[str, str],
    rng: np.random.Generator,
    immunocompromised_fraction: float,
) -> AgentProfile:
    aid = agent.agent_id
    cls = getattr(agent, "agent_class", "") or "unknown"
    role = getattr(agent, "role", "passenger")
    gender = getattr(agent, "gender", "unknown")
    tmpl = templates.get(cls, default_template)
    age_bands = tmpl.get("age_bands", ["adult"])
    age_band = str(rng.choice(age_bands))
    immune = bool(getattr(agent, "immune", False))
    immuno = False
    if not immune and immunocompromised_fraction > 0:
        immuno = rng.random() < immunocompromised_fraction
    comorbidities = list(tmpl.get("comorbidities", []))
    if immuno and "immunocompromised" not in comorbidities:
        comorbidities.append("immunocompromised")
    device_id = device_map.get(cls, tmpl.get("device_id", ""))
    channels = list(tmpl.get("monitored_channels", [
        "heart_rate", "body_temp", "spo2", "respiratory_rate",
    ]))
    return AgentProfile(
        profile_id=f"{cls}_{aid}",
        agent_id=aid,
        agent_class=cls,
        role_group=role,
        gender=gender,
        age_band=age_band,
        immune=immune,
        immunocompromised=immuno,
        comorbidities=comorbidities,
        vaccinations=list(tmpl.get("vaccinations", [])),
        chronic_meds=list(tmpl.get("chronic_meds", [])),
        device_id=device_id,
        monitored_channels=channels,
    )


def build_profiles_for_agents(
    agents: list[Any],
    bundle: dict[str, Any],
    rng: np.random.Generator,
    class_device_map: dict[str, str] | None = None,
    immunocompromised_fraction: float = 0.0,
) -> dict[int, AgentProfile]:
    """Assign profiles to runtime agents using bundle templates."""
    templates = bundle.get("class_templates", {})
    default_template = bundle.get("default_template", {})
    profiles: dict[int, AgentProfile] = {}
    device_map = _build_device_map(class_device_map)

    for agent in agents:
        profiles[agent.agent_id] = _profile_for_agent(
            agent, templates, default_template, device_map, rng,
            immunocompromised_fraction,
        )
    return profiles


def default_bundle_path(repo_root: str) -> str:
    return os.path.join(
        repo_root,
        "picard_framework",
        "data",
        "agent_profiles",
        "default_ship_population.json",
    )
