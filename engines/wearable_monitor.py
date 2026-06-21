"""
engines.wearable_monitor
~~~~~~~~~~~~~~~~~~~~~~~~

Extensible wearable physiological monitoring for shipboard agents.

Each agent may be assigned one or more **device** instances drawn from
a config-driven registry.  A device definition specifies:

- Which sensor **channels** it carries (heart_rate, body_temp, spo2, …)
- Per-channel **baseline** ranges (optionally varying by agent class / gender)
- Per-channel **noise** parameters (Gaussian σ, drift, dropout probability)
- Per-channel **infection_response** profiles keyed by pathogen category,
  tied to EMOD shedding phases (early / peak / late / recovery)
- A **detection_profile** with sensitivity/specificity/latency
- **Confounders** with channel-specific bias and noise multipliers

The ``WearableMonitor`` class manages the full fleet of per-agent
devices and produces fine-grained (24 hourly readings) plus daily
summary data each epoch.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import (
    KorkinAgent,
    InfectionStatus,
    IllnessStatus,
)


# ── Channel baseline defaults ────────────────────────────────────────────

DEFAULT_CHANNEL_BASELINES: dict[str, dict[str, float]] = {
    "heart_rate": {"mean": 68.0, "std": 4.0, "unit_label": "bpm"},
    "respiratory_rate": {"mean": 15.0, "std": 1.5, "unit_label": "breaths/min"},
    "body_temp": {"mean": 36.6, "std": 0.15, "unit_label": "°C"},
    "spo2": {"mean": 97.5, "std": 0.5, "unit_label": "%"},
    "hrv": {"mean": 45.0, "std": 8.0, "unit_label": "ms"},
    "sleep_score": {"mean": 80.0, "std": 5.0, "unit_label": "score"},
    "activity_score": {"mean": 50.0, "std": 10.0, "unit_label": "score"},
    "glucose": {"mean": 95.0, "std": 12.0, "unit_label": "mg/dL"},
}

# Class-specific baseline adjustments (additive offsets from default)
CLASS_BASELINE_OFFSETS: dict[str, dict[str, float]] = {
    "passenger_elderly": {
        "heart_rate": 4.0,
        "spo2": -1.5,
        "hrv": -10.0,
        "activity_score": -15.0,
        "sleep_score": -5.0,
    },
    "crew_engineering": {
        "activity_score": 10.0,
        "heart_rate": -2.0,
    },
    "crew_galley": {
        "activity_score": 8.0,
    },
    "crew_medical": {
        "activity_score": 5.0,
    },
}

# Gender-specific baseline adjustments
GENDER_BASELINE_OFFSETS: dict[str, dict[str, float]] = {
    "female": {
        "heart_rate": 2.0,
        "body_temp": 0.1,
    },
    "male": {
        "heart_rate": -1.0,
    },
}

# Schedule-activity mapping: how each schedule block modulates activity
ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "Sleep": 0.05,
    "Meal:Breakfast": 0.3,
    "Meal:Lunch": 0.3,
    "Meal:Dinner": 0.3,
    "Free": 0.6,
    "Work": 0.9,
}


# ── Infection response defaults (per EMOD shedding phase) ────────────────

DEFAULT_INFECTION_RESPONSES: dict[str, dict[str, dict[str, float]]] = {
    "enteric_viral": {
        "heart_rate": {"early": 3.0, "peak": 10.0, "late": 5.0, "recovery": 1.0},
        "body_temp": {"early": 0.3, "peak": 1.5, "late": 0.8, "recovery": 0.1},
        "spo2": {"early": 0.0, "peak": -0.5, "late": -0.3, "recovery": 0.0},
        "respiratory_rate": {"early": 0.5, "peak": 2.0, "late": 1.0, "recovery": 0.2},
        "hrv": {"early": -3.0, "peak": -15.0, "late": -8.0, "recovery": -2.0},
        "sleep_score": {"early": -5.0, "peak": -25.0, "late": -15.0, "recovery": -3.0},
        "activity_score": {"early": -5.0, "peak": -20.0, "late": -10.0, "recovery": -2.0},
        "glucose": {"early": 5.0, "peak": 15.0, "late": 8.0, "recovery": 2.0},
    },
    "respiratory_viral": {
        "heart_rate": {"early": 2.0, "peak": 12.0, "late": 6.0, "recovery": 1.5},
        "body_temp": {"early": 0.4, "peak": 1.8, "late": 1.0, "recovery": 0.2},
        "spo2": {"early": -0.5, "peak": -3.0, "late": -1.5, "recovery": -0.3},
        "respiratory_rate": {"early": 1.0, "peak": 5.0, "late": 2.5, "recovery": 0.5},
        "hrv": {"early": -4.0, "peak": -18.0, "late": -10.0, "recovery": -3.0},
        "sleep_score": {"early": -5.0, "peak": -30.0, "late": -18.0, "recovery": -5.0},
        "activity_score": {"early": -5.0, "peak": -25.0, "late": -12.0, "recovery": -3.0},
        "glucose": {"early": 8.0, "peak": 20.0, "late": 10.0, "recovery": 3.0},
    },
}

# Phase boundaries (days post infection → phase name)
# Aligned with EMOD shedding_phases config: early=[0,3), peak=[3,8), late=[8,12)
DEFAULT_PHASE_BOUNDARIES: list[tuple[int, str]] = [
    (0, "early"),
    (3, "peak"),
    (8, "late"),
    (12, "recovery"),
]


# ── Noise defaults ───────────────────────────────────────────────────────

DEFAULT_NOISE: dict[str, dict[str, float]] = {
    "heart_rate": {"sigma": 2.0, "drift_rate": 0.1, "dropout_prob": 0.005},
    "respiratory_rate": {"sigma": 0.8, "drift_rate": 0.05, "dropout_prob": 0.005},
    "body_temp": {"sigma": 0.08, "drift_rate": 0.01, "dropout_prob": 0.002},
    "spo2": {"sigma": 0.3, "drift_rate": 0.02, "dropout_prob": 0.003},
    "hrv": {"sigma": 5.0, "drift_rate": 0.5, "dropout_prob": 0.01},
    "sleep_score": {"sigma": 3.0, "drift_rate": 0.0, "dropout_prob": 0.0},
    "activity_score": {"sigma": 5.0, "drift_rate": 0.0, "dropout_prob": 0.0},
    "glucose": {"sigma": 8.0, "drift_rate": 0.5, "dropout_prob": 0.01},
}


def _get_infection_phase(days_post_infection: int, boundaries: list[tuple[int, str]]) -> str:
    """Map days-post-infection to a named shedding phase."""
    phase = "recovery"
    for threshold, name in boundaries:
        if days_post_infection >= threshold:
            phase = name
    return phase


def _compute_infection_delta(
    channel: str,
    agent: KorkinAgent,
    pathogen_profiles: dict[str, dict[str, Any]],
    infection_responses: dict[str, dict[str, dict[str, float]]],
    phase_boundaries: list[tuple[int, str]],
) -> float:
    """Compute the aggregate infection-driven perturbation for one channel."""
    total_delta = 0.0
    for pid, inf in agent.infections.items():
        if inf["status"] != InfectionStatus.INFECTED:
            continue
        dpi = inf.get("time_infected", 0) or 0
        phase = _get_infection_phase(dpi, phase_boundaries)

        profile = pathogen_profiles.get(pid, {})
        category = profile.get("category", "enteric_viral")

        response_map = infection_responses.get(category, {})
        channel_response = response_map.get(channel, {})
        delta = channel_response.get(phase, 0.0)
        total_delta += delta
    return total_delta


# ── WearableDevice ───────────────────────────────────────────────────────

class WearableDevice:
    """A single wearable device type with its sensor channel configuration.

    Instances are shared across agents of the same class — the per-agent
    variation comes from baseline offsets and stochastic noise.
    """

    def __init__(
        self,
        device_id: str,
        channels: list[str],
        noise: dict[str, dict[str, float]] | None = None,
        infection_responses: dict[str, dict[str, dict[str, float]]] | None = None,
        phase_boundaries: list[tuple[int, str]] | None = None,
        channel_baselines: dict[str, dict[str, float]] | None = None,
        detection_profile: dict[str, float] | None = None,
        confounders: list[dict[str, Any]] | None = None,
    ) -> None:
        self.device_id = device_id
        self.channels = list(channels)
        self.noise = noise or {}
        self.infection_responses = infection_responses or DEFAULT_INFECTION_RESPONSES
        self.phase_boundaries = phase_boundaries or DEFAULT_PHASE_BOUNDARIES
        self.channel_baselines = channel_baselines or {}
        self.detection_profile = detection_profile
        self.confounders = confounders or []

    def get_channel_noise(self, channel: str) -> dict[str, float]:
        if channel in self.noise:
            return self.noise[channel]
        return DEFAULT_NOISE.get(channel, {"sigma": 1.0, "drift_rate": 0.0, "dropout_prob": 0.0})

    def get_channel_baseline(self, channel: str) -> dict[str, float]:
        if channel in self.channel_baselines:
            return self.channel_baselines[channel]
        return DEFAULT_CHANNEL_BASELINES.get(channel, {"mean": 0.0, "std": 1.0})

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "device_id": self.device_id,
            "channels": self.channels,
        }
        if self.detection_profile:
            result["detection_profile"] = dict(self.detection_profile)
        if self.confounders:
            result["confounders"] = [c.get("confounder_id", "") for c in self.confounders]
        return result


# ── AgentWearableState ───────────────────────────────────────────────────

class AgentWearableState:
    """Per-agent per-device wearable state including personalised baselines and drift."""

    def __init__(
        self,
        agent_id: int,
        device: WearableDevice,
        baselines: dict[str, float],
        visibility: str = "medical_staff",
    ) -> None:
        self.agent_id = agent_id
        self.device = device
        self.baselines = dict(baselines)
        self.drift: dict[str, float] = {ch: 0.0 for ch in device.channels}
        self.visibility = visibility

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "device_id": self.device.device_id,
            "baselines": dict(self.baselines),
            "visibility": self.visibility,
        }


# ── DeviceAssignment ─────────────────────────────────────────────────────

class DeviceAssignment:
    """A single device assignment entry: device_id + coverage + visibility."""

    def __init__(
        self,
        device_id: str,
        coverage: float = 1.0,
        visibility: str = "medical_staff",
    ) -> None:
        self.device_id = device_id
        self.coverage = coverage
        self.visibility = visibility


# ── WearableMonitor (fleet manager) ─────────────────────────────────────

class WearableMonitor:
    """Manages the full fleet of wearable devices across all agents.

    Constructed from config during initialization.  Each epoch, call
    ``generate_epoch_data`` to produce fine-grained (24 hourly readings)
    and daily summaries for every monitored agent.

    Supports multiple devices per agent — each agent may have zero or
    more ``AgentWearableState`` entries.
    """

    def __init__(
        self,
        devices: dict[str, WearableDevice],
        class_device_assignments: dict[str, list[DeviceAssignment]],
        chronic_disease_device_map: list[dict[str, Any]] | None = None,
        rng: np.random.Generator | None = None,
        anomaly_z_threshold: float = 2.0,
    ) -> None:
        self.devices = devices
        self.class_device_assignments = class_device_assignments
        self.chronic_disease_device_map = chronic_disease_device_map or []
        self.rng = rng if rng is not None else np.random.default_rng()
        self.anomaly_z_threshold = anomaly_z_threshold
        self._agent_states: dict[int, list[AgentWearableState]] = {}

    @property
    def agent_states(self) -> dict[int, list[AgentWearableState]]:
        return self._agent_states

    def _compute_baselines(
        self,
        agent: KorkinAgent,
        device: WearableDevice,
        class_offsets: dict[str, dict[str, float]] | None = None,
        gender_offsets: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, float]:
        """Compute personalised baselines for one device on one agent."""
        class_offsets = class_offsets or CLASS_BASELINE_OFFSETS
        gender_offsets = gender_offsets or GENDER_BASELINE_OFFSETS
        baselines: dict[str, float] = {}
        for ch in device.channels:
            ch_base = device.get_channel_baseline(ch)
            mean = ch_base.get("mean", 0.0)
            std = ch_base.get("std", 1.0)
            personal = float(self.rng.normal(mean, std * 0.3))
            cls_off = class_offsets.get(agent.agent_class, {}).get(ch, 0.0)
            personal += cls_off
            gen_off = gender_offsets.get(agent.gender, {}).get(ch, 0.0)
            personal += gen_off
            baselines[ch] = round(personal, 2)
        return baselines

    def initialize_agent(
        self,
        agent: KorkinAgent,
        class_offsets: dict[str, dict[str, float]] | None = None,
        gender_offsets: dict[str, dict[str, float]] | None = None,
        chronic_disease_ids: list[str] | None = None,
    ) -> list[AgentWearableState]:
        """Assign wearable devices and compute personalised baselines.

        Returns the list of AgentWearableState objects created (may be
        empty if no devices were assigned due to coverage rolls).
        """
        assignments = self.class_device_assignments.get(agent.agent_class)
        if assignments is None:
            assignments = self.class_device_assignments.get("default", [])

        states: list[AgentWearableState] = []
        assigned_device_ids: set[str] = set()

        for assignment in assignments:
            if assignment.device_id not in self.devices:
                continue
            if self.rng.random() > assignment.coverage:
                continue
            device = self.devices[assignment.device_id]
            baselines = self._compute_baselines(agent, device, class_offsets, gender_offsets)
            state = AgentWearableState(
                agent.agent_id, device, baselines, visibility=assignment.visibility,
            )
            states.append(state)
            assigned_device_ids.add(assignment.device_id)

        # Chronic disease device assignments (additive)
        for cd_entry in self.chronic_disease_device_map:
            disease_id = cd_entry.get("disease_id", "")
            if not chronic_disease_ids or disease_id not in chronic_disease_ids:
                continue
            did = cd_entry.get("device_id", "")
            if did not in self.devices or did in assigned_device_ids:
                continue
            cd_coverage = float(cd_entry.get("coverage", 1.0))
            if self.rng.random() > cd_coverage:
                continue
            device = self.devices[did]
            cd_visibility = cd_entry.get("visibility", "medical_staff")
            baselines = self._compute_baselines(agent, device, class_offsets, gender_offsets)
            state = AgentWearableState(
                agent.agent_id, device, baselines, visibility=cd_visibility,
            )
            states.append(state)
            assigned_device_ids.add(did)

        if states:
            self._agent_states[agent.agent_id] = states
        return states

    def generate_epoch_data(
        self,
        agents: list[KorkinAgent],
        pathogen_profiles: dict[str, dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Generate wearable data for all monitored agents for one epoch.

        Returns ``{agent_id: {"devices": [...], "fever": bool, ...}}``.
        Each agent's result aggregates across all their devices.
        """
        results: dict[int, dict[str, Any]] = {}
        for agent in agents:
            agent_states = self._agent_states.get(agent.agent_id)
            if not agent_states:
                continue
            results[agent.agent_id] = self._generate_agent_epoch_multi(
                agent, agent_states, pathogen_profiles,
            )
        return results

    def _sample_confounders(
        self,
        agent: KorkinAgent,
        device: WearableDevice,
    ) -> dict[str, dict[str, Any]]:
        """Sample which confounders are active for this agent/device this epoch.

        Returns ``{confounder_id: {channel: {bias, noise_mult}, ...}}``.
        """
        active: dict[str, dict[str, Any]] = {}
        for conf in device.confounders:
            cid = conf.get("confounder_id", "")
            prevalence = float(conf.get("prevalence", 0.0))
            susceptible_classes = conf.get("susceptible_classes", [])
            susceptible_role = conf.get("susceptible_role_group", "")

            is_susceptible = (
                not susceptible_classes
                or agent.agent_class in susceptible_classes
            )
            if not is_susceptible and susceptible_role:
                is_susceptible = agent.agent_class.startswith(susceptible_role)

            if not is_susceptible:
                continue
            if self.rng.random() >= prevalence:
                continue
            active[cid] = conf.get("affected_channels", {})
        return active

    def _generate_agent_epoch_multi(
        self,
        agent: KorkinAgent,
        states: list[AgentWearableState],
        pathogen_profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate epoch data across all devices for one agent, then aggregate."""
        device_results: list[dict[str, Any]] = []
        agg_fever = False
        agg_anomaly_channels: list[str] = []
        visibility_list: list[str] = []

        for state in states:
            confounder_effects = self._sample_confounders(agent, state.device)
            result = self._generate_single_device_epoch(
                agent, state, pathogen_profiles, confounder_effects,
            )
            result = self._apply_detection_profile(
                agent, state.device, result,
            )
            result["visibility"] = state.visibility
            device_results.append(result)

            if result.get("fever", False):
                agg_fever = True
            for ch in result.get("anomaly_channels", []):
                if ch not in agg_anomaly_channels:
                    agg_anomaly_channels.append(ch)
            visibility_list.append(state.visibility)

        return {
            "devices": device_results,
            "device_id": device_results[0]["device_id"] if device_results else "none",
            "fever": agg_fever,
            "anomaly_channels": agg_anomaly_channels,
            "anomaly_count": len(agg_anomaly_channels),
            "visibility": visibility_list,
            "summary": self._merge_summaries(device_results),
            "hourly": device_results[0].get("hourly", {}) if device_results else {},
        }

    def _merge_summaries(self, device_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Merge summary dicts across multiple device results.

        For channels present on multiple devices, pick the one with
        the highest z_score (most informative reading).
        """
        merged: dict[str, dict[str, Any]] = {}
        for dr in device_results:
            for ch, ch_data in dr.get("summary", {}).items():
                if ch not in merged:
                    merged[ch] = dict(ch_data)
                else:
                    existing_z = merged[ch].get("z_score", 0.0) or 0.0
                    new_z = ch_data.get("z_score", 0.0) or 0.0
                    if new_z > existing_z:
                        merged[ch] = dict(ch_data)
        return merged

    def _generate_single_device_epoch(
        self,
        agent: KorkinAgent,
        state: AgentWearableState,
        pathogen_profiles: dict[str, dict[str, Any]],
        confounder_effects: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate one epoch of wearable data for a single device."""
        device = state.device
        hourly: dict[str, list[float | None]] = {ch: [] for ch in device.channels}
        summary: dict[str, dict[str, Any]] = {}

        for ch in device.channels:
            noise_cfg = device.get_channel_noise(ch)
            sigma = noise_cfg.get("sigma", 1.0)
            drift_rate = noise_cfg.get("drift_rate", 0.0)
            dropout_prob = noise_cfg.get("dropout_prob", 0.0)

            baseline = state.baselines.get(ch, 0.0)

            # Confounder effects: bias + noise multiplier
            confounder_bias = 0.0
            confounder_noise_mult = 1.0
            for _cid, ch_effects in confounder_effects.items():
                if ch in ch_effects:
                    eff = ch_effects[ch]
                    confounder_bias += float(eff.get("bias", 0.0))
                    confounder_noise_mult *= float(eff.get("noise_mult", 1.0))

            effective_sigma = sigma * confounder_noise_mult

            # Infection perturbation (scaled by chronic disease response factor)
            inf_delta = _compute_infection_delta(
                ch, agent, pathogen_profiles,
                device.infection_responses, device.phase_boundaries,
            )
            if hasattr(agent, "chronic_wearable_response_scale"):
                inf_delta *= agent.chronic_wearable_response_scale

            readings: list[float | None] = []
            for hour in range(24):
                # Sensor dropout
                if self.rng.random() < dropout_prob:
                    readings.append(None)
                    continue

                # Activity modulation for relevant channels
                activity_mult = 1.0
                if ch in ("heart_rate", "activity_score"):
                    activity_block = agent.schedule[hour] if hour < len(agent.schedule) else "Sleep"
                    activity_mult = ACTIVITY_MULTIPLIERS.get(
                        activity_block.split(":")[0] if ":" in activity_block else activity_block,
                        0.5,
                    )

                # Circadian modulation for temp and heart rate
                circadian = 0.0
                if ch == "body_temp":
                    circadian = 0.3 * math.sin(2 * math.pi * (hour - 4) / 24.0)
                elif ch == "heart_rate":
                    circadian = 3.0 * math.sin(2 * math.pi * (hour - 4) / 24.0)

                # Sleep modulation
                is_sleep_hour = (
                    hour < len(agent.schedule) and agent.schedule[hour] == "Sleep"
                )
                sleep_mod = 0.0
                if ch == "sleep_score" and is_sleep_hour:
                    sleep_mod = 3.0
                elif ch == "sleep_score" and not is_sleep_hour:
                    sleep_mod = -2.0

                # Drift accumulation
                state.drift[ch] += float(self.rng.normal(0, drift_rate))
                state.drift[ch] *= 0.95  # mean-revert

                # Compose reading (include confounder bias)
                value = baseline + confounder_bias + inf_delta + circadian + sleep_mod + state.drift[ch]

                if ch in ("heart_rate", "activity_score"):
                    value = (
                        baseline + confounder_bias
                        + (circadian + sleep_mod + state.drift[ch]) * activity_mult
                        + inf_delta
                    )

                # Add measurement noise (with confounder-scaled sigma)
                value += float(self.rng.normal(0, effective_sigma))

                # Clamp to physiological bounds
                value = _clamp_channel(ch, value)
                readings.append(round(value, 2))

            hourly[ch] = readings

            # Compute summary statistics
            valid = [r for r in readings if r is not None]
            if valid:
                ch_summary: dict[str, Any] = {
                    "mean": round(sum(valid) / len(valid), 2),
                    "min": round(min(valid), 2),
                    "max": round(max(valid), 2),
                    "readings_count": len(valid),
                    "dropout_count": readings.count(None),
                }
                # Anomaly flag: deviation from baseline
                mean_val = ch_summary["mean"]
                baseline_val = state.baselines.get(ch, mean_val)
                ch_base_cfg = device.get_channel_baseline(ch)
                baseline_std = ch_base_cfg.get("std", 1.0)
                if baseline_std > 0:
                    z_score = abs(mean_val - baseline_val) / baseline_std
                    ch_summary["z_score"] = round(z_score, 2)
                    ch_summary["anomaly"] = z_score > self.anomaly_z_threshold
                else:
                    ch_summary["z_score"] = 0.0
                    ch_summary["anomaly"] = False
            else:
                ch_summary = {
                    "mean": None, "min": None, "max": None,
                    "readings_count": 0, "dropout_count": 24,
                    "z_score": 0.0, "anomaly": False,
                }
            summary[ch] = ch_summary

        # Fever flag (convenience)
        fever = False
        temp_summary = summary.get("body_temp")
        if temp_summary and temp_summary.get("max") is not None:
            fever = temp_summary["max"] >= 37.8

        # Aggregate anomaly count
        anomaly_channels = [
            ch for ch, s in summary.items() if s.get("anomaly", False)
        ]

        return {
            "device_id": device.device_id,
            "hourly": hourly,
            "summary": summary,
            "fever": fever,
            "anomaly_channels": anomaly_channels,
            "anomaly_count": len(anomaly_channels),
        }

    def _apply_detection_profile(
        self,
        agent: KorkinAgent,
        device: WearableDevice,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply sensitivity/specificity gating to anomaly and fever flags."""
        profile = device.detection_profile
        if profile is None:
            return result

        is_truly_infected = any(
            inf["status"] == InfectionStatus.INFECTED
            for inf in agent.infections.values()
        )

        # Latency: suppress alerts if infection is too recent
        latency_hours = int(profile.get("alert_latency_hours", 0))
        if latency_hours > 0 and is_truly_infected:
            min_dpi = min(
                (inf.get("time_infected", 0) or 0)
                for inf in agent.infections.values()
                if inf["status"] == InfectionStatus.INFECTED
            )
            if min_dpi * 24 < latency_hours:
                is_truly_infected = False

        # Anomaly sensitivity/specificity
        sensitivity = float(profile.get("sensitivity", 1.0))
        specificity = float(profile.get("specificity", 1.0))

        has_anomaly = result.get("anomaly_count", 0) > 0
        if has_anomaly and is_truly_infected:
            if self.rng.random() > sensitivity:
                result["anomaly_channels"] = []
                result["anomaly_count"] = 0
                for ch_data in result.get("summary", {}).values():
                    ch_data["anomaly"] = False
        elif has_anomaly and not is_truly_infected:
            pass  # already a false positive from the raw data
        elif not has_anomaly and not is_truly_infected:
            if self.rng.random() > specificity:
                fp_ch = self.rng.choice(device.channels) if device.channels else "heart_rate"
                result["anomaly_channels"] = [fp_ch]
                result["anomaly_count"] = 1
                if fp_ch in result.get("summary", {}):
                    result["summary"][fp_ch]["anomaly"] = True

        # Fever sensitivity/specificity
        fever_sens = float(profile.get("fever_sensitivity", 1.0))
        fever_spec = float(profile.get("fever_specificity", 1.0))
        raw_fever = result.get("fever", False)

        if raw_fever and is_truly_infected:
            if self.rng.random() > fever_sens:
                result["fever"] = False
        elif not raw_fever and not is_truly_infected:
            if self.rng.random() > fever_spec:
                result["fever"] = True

        return result

    def get_fleet_summary(self) -> dict[str, Any]:
        """Summary of the wearable fleet configuration."""
        device_counts: dict[str, int] = {}
        visibility_counts: dict[str, int] = {"medical_staff": 0, "wearer_only": 0, "both": 0}
        total_agents = len(self._agent_states)
        total_devices = 0
        for states in self._agent_states.values():
            for state in states:
                did = state.device.device_id
                device_counts[did] = device_counts.get(did, 0) + 1
                total_devices += 1
                vis = state.visibility
                if vis in visibility_counts:
                    visibility_counts[vis] += 1

        return {
            "total_monitored": total_agents,
            "total_device_instances": total_devices,
            "devices": {
                did: device.to_dict() for did, device in self.devices.items()
            },
            "device_deployment_counts": device_counts,
            "visibility_breakdown": visibility_counts,
        }


def _clamp_channel(channel: str, value: float) -> float:
    """Clamp a reading to physiologically plausible bounds."""
    bounds: dict[str, tuple[float, float]] = {
        "heart_rate": (30.0, 200.0),
        "respiratory_rate": (4.0, 40.0),
        "body_temp": (34.0, 42.0),
        "spo2": (70.0, 100.0),
        "hrv": (5.0, 150.0),
        "sleep_score": (0.0, 100.0),
        "activity_score": (0.0, 100.0),
        "glucose": (40.0, 400.0),
    }
    lo, hi = bounds.get(channel, (-1e6, 1e6))
    return max(lo, min(hi, value))


# ── Config-driven construction ───────────────────────────────────────────

def build_wearable_device_from_config(
    device_cfg: dict[str, Any],
) -> WearableDevice:
    """Build a WearableDevice from a YAML config block."""
    device_id = device_cfg["device_id"]
    channels = device_cfg.get("channels", list(DEFAULT_CHANNEL_BASELINES.keys()))

    noise: dict[str, dict[str, float]] = {}
    for ch_noise in device_cfg.get("noise", []):
        ch_name = ch_noise.get("channel", "")
        if ch_name:
            noise[ch_name] = {
                k: v for k, v in ch_noise.items() if k != "channel"
            }

    infection_responses: dict[str, dict[str, dict[str, float]]] = {}
    for ir_cfg in device_cfg.get("infection_responses", []):
        category = ir_cfg.get("pathogen_category", "")
        if not category:
            continue
        channel_map: dict[str, dict[str, float]] = {}
        for ch_resp in ir_cfg.get("channel_responses", []):
            ch_name = ch_resp.get("channel", "")
            if ch_name:
                channel_map[ch_name] = {
                    k: v for k, v in ch_resp.items() if k != "channel"
                }
        infection_responses[category] = channel_map

    if not infection_responses:
        infection_responses = dict(DEFAULT_INFECTION_RESPONSES)

    phase_boundaries: list[tuple[int, str]] = []
    for pb in device_cfg.get("phase_boundaries", []):
        phase_boundaries.append((pb["day"], pb["phase"]))
    if not phase_boundaries:
        phase_boundaries = list(DEFAULT_PHASE_BOUNDARIES)

    channel_baselines: dict[str, dict[str, float]] = {}
    for cb in device_cfg.get("channel_baselines", []):
        ch_name = cb.get("channel", "")
        if ch_name:
            channel_baselines[ch_name] = {
                k: v for k, v in cb.items() if k != "channel"
            }

    detection_profile: dict[str, float] | None = None
    dp_cfg = device_cfg.get("detection_profile")
    if dp_cfg and isinstance(dp_cfg, dict):
        detection_profile = {k: float(v) for k, v in dp_cfg.items()}

    confounders: list[dict[str, Any]] = device_cfg.get("confounders", [])

    return WearableDevice(
        device_id=device_id,
        channels=channels,
        noise=noise,
        infection_responses=infection_responses,
        phase_boundaries=phase_boundaries,
        channel_baselines=channel_baselines,
        detection_profile=detection_profile,
        confounders=confounders,
    )


def build_wearable_monitor_from_config(
    cfg: dict[str, Any],
    rng: np.random.Generator | None = None,
) -> WearableMonitor | None:
    """Build the full WearableMonitor fleet from config.

    Returns None if wearable_monitoring is absent or disabled.

    Supports both the old single-device class_device_map format::

        class_device_map:
          - {agent_class: "default", device_id: "oura_ring"}

    and the new multi-device format::

        class_device_map:
          - agent_class: "default"
            devices:
              - {device_id: "oura_ring", coverage: 1.0, visibility: "medical_staff"}
    """
    wm_cfg = cfg.get("wearable_monitoring")
    if wm_cfg is None:
        return None
    if not wm_cfg.get("enabled", True):
        return None

    devices: dict[str, WearableDevice] = {}
    for dev_cfg in wm_cfg.get("devices", []):
        device = build_wearable_device_from_config(dev_cfg)
        devices[device.device_id] = device

    class_device_assignments: dict[str, list[DeviceAssignment]] = {}
    for mapping in wm_cfg.get("class_device_map", []):
        agent_class = mapping.get("agent_class", "")
        if not agent_class:
            continue

        # New multi-device format
        if "devices" in mapping:
            assignments: list[DeviceAssignment] = []
            for dev_entry in mapping["devices"]:
                did = dev_entry.get("device_id", "")
                if did:
                    assignments.append(DeviceAssignment(
                        device_id=did,
                        coverage=float(dev_entry.get("coverage", 1.0)),
                        visibility=dev_entry.get("visibility", "medical_staff"),
                    ))
            class_device_assignments[agent_class] = assignments
        else:
            # Old single-device format (backward compatible)
            device_id = mapping.get("device_id", "")
            if device_id:
                class_device_assignments[agent_class] = [
                    DeviceAssignment(
                        device_id=device_id,
                        coverage=float(mapping.get("coverage", 1.0)),
                        visibility=mapping.get("visibility", "medical_staff"),
                    ),
                ]

    if not devices:
        return None

    chronic_disease_device_map = wm_cfg.get("chronic_disease_device_map", [])

    anomaly_z_threshold = wm_cfg.get("anomaly_z_threshold", 2.0)

    return WearableMonitor(
        devices=devices,
        class_device_assignments=class_device_assignments,
        chronic_disease_device_map=chronic_disease_device_map,
        rng=rng,
        anomaly_z_threshold=anomaly_z_threshold,
    )
