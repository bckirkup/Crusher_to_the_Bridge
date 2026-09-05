"""Static agent profiles for decision-layer hooks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

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


def age_band_probabilities(
    template: dict[str, Any],
) -> tuple[list[str], np.ndarray | None]:
    """The template's age bands and the probability each is drawn with.

    ``age_bands`` alone draws uniformly (``None`` probabilities, so the draw
    consumes the stream exactly as every bundle before weights existed did).
    ``age_band_weights`` declares a composition — one non-negative weight per
    band, normalised here — so a scenario can carry a measured age table
    instead of a uniform one. A malformed declaration is a load error rather
    than a silently uniform population.
    """
    bands = [str(band) for band in template.get("age_bands", ["adult"])]
    if not bands:
        raise ValueError("age_bands must name at least one band")
    weights = template.get("age_band_weights")
    if weights is None:
        return bands, None
    values = np.asarray([float(w) for w in weights], dtype=float)
    if values.shape != (len(bands),):
        raise ValueError(
            f"age_band_weights has {values.size} entries for {len(bands)} age_bands",
        )
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("age_band_weights must be finite and non-negative")
    total = float(values.sum())
    if total <= 0.0:
        raise ValueError("age_band_weights must have a positive sum")
    return bands, values / total


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
    age_bands, band_p = age_band_probabilities(tmpl)
    age_band = str(rng.choice(age_bands, p=band_p))
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
        profile = _profile_for_agent(
            agent, templates, default_template, device_map, rng,
            immunocompromised_fraction,
        )
        profiles[agent.agent_id] = profile
        _publish_host_biology(agent, profile)
    return profiles


@runtime_checkable
class HostBiologyAgent(Protocol):
    """An agent that can carry the host biology an infection model reads."""

    age_band: str
    immunocompromised: bool


def _publish_host_biology(agent: object, profile: AgentProfile) -> None:
    """Copy the host attributes the infection model conditions on onto the agent.

    Age band lives only in this layer, and the incubation distribution needs it
    where the infection is. Agent types without these fields are left alone, so
    a population that cannot carry host biology keeps the neutral default rather
    than a guessed one.
    """
    if not isinstance(agent, HostBiologyAgent):
        return
    agent.age_band = profile.age_band
    if profile.immunocompromised:
        agent.immunocompromised = True


def default_bundle_path(repo_root: str) -> str:
    return os.path.join(
        repo_root,
        "picard_framework",
        "data",
        "agent_profiles",
        "default_ship_population.json",
    )
