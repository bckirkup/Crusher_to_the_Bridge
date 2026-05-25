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
    },
    "respiratory_viral": {
        "heart_rate": {"early": 2.0, "peak": 12.0, "late": 6.0, "recovery": 1.5},
        "body_temp": {"early": 0.4, "peak": 1.8, "late": 1.0, "recovery": 0.2},
        "spo2": {"early": -0.5, "peak": -3.0, "late": -1.5, "recovery": -0.3},
        "respiratory_rate": {"early": 1.0, "peak": 5.0, "late": 2.5, "recovery": 0.5},
        "hrv": {"early": -4.0, "peak": -18.0, "late": -10.0, "recovery": -3.0},
        "sleep_score": {"early": -5.0, "peak": -30.0, "late": -18.0, "recovery": -5.0},
        "activity_score": {"early": -5.0, "peak": -25.0, "late": -12.0, "recovery": -3.0},
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
    ) -> None:
        self.device_id = device_id
        self.channels = list(channels)
        self.noise = noise or {}
        self.infection_responses = infection_responses or DEFAULT_INFECTION_RESPONSES
        self.phase_boundaries = phase_boundaries or DEFAULT_PHASE_BOUNDARIES
        self.channel_baselines = channel_baselines or {}

    def get_channel_noise(self, channel: str) -> dict[str, float]:
        if channel in self.noise:
            return self.noise[channel]
        return DEFAULT_NOISE.get(channel, {"sigma": 1.0, "drift_rate": 0.0, "dropout_prob": 0.0})

    def get_channel_baseline(self, channel: str) -> dict[str, float]:
        if channel in self.channel_baselines:
            return self.channel_baselines[channel]
        return DEFAULT_CHANNEL_BASELINES.get(channel, {"mean": 0.0, "std": 1.0})

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "channels": self.channels,
        }


# ── AgentWearableState ───────────────────────────────────────────────────

class AgentWearableState:
    """Per-agent wearable state including personalised baselines and drift."""

    def __init__(
        self,
        agent_id: int,
        device: WearableDevice,
        baselines: dict[str, float],
    ) -> None:
        self.agent_id = agent_id
        self.device = device
        self.baselines = dict(baselines)
        self.drift: dict[str, float] = {ch: 0.0 for ch in device.channels}

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "device_id": self.device.device_id,
            "baselines": dict(self.baselines),
        }


# ── WearableMonitor (fleet manager) ─────────────────────────────────────

class WearableMonitor:
    """Manages the full fleet of wearable devices across all agents.

    Constructed from config during initialization.  Each epoch, call
    ``generate_epoch_data`` to produce fine-grained (24 hourly readings)
    and daily summaries for every monitored agent.
    """

    def __init__(
        self,
        devices: dict[str, WearableDevice],
        class_device_map: dict[str, str],
        rng: np.random.Generator | None = None,
        anomaly_z_threshold: float = 2.0,
    ) -> None:
        self.devices = devices
        self.class_device_map = class_device_map
        self.rng = rng if rng is not None else np.random.default_rng()
        self.anomaly_z_threshold = anomaly_z_threshold
        self._agent_states: dict[int, AgentWearableState] = {}

    @property
    def agent_states(self) -> dict[int, AgentWearableState]:
        return self._agent_states

    def initialize_agent(
        self,
        agent: KorkinAgent,
        class_offsets: dict[str, dict[str, float]] | None = None,
        gender_offsets: dict[str, dict[str, float]] | None = None,
    ) -> AgentWearableState | None:
        """Assign a wearable device and compute personalised baselines."""
        device_id = self.class_device_map.get(agent.agent_class)
        if device_id is None:
            device_id = self.class_device_map.get("default")
        if device_id is None or device_id not in self.devices:
            return None

        device = self.devices[device_id]
        class_offsets = class_offsets or CLASS_BASELINE_OFFSETS
        gender_offsets = gender_offsets or GENDER_BASELINE_OFFSETS

        baselines: dict[str, float] = {}
        for ch in device.channels:
            ch_base = device.get_channel_baseline(ch)
            mean = ch_base.get("mean", 0.0)
            std = ch_base.get("std", 1.0)

            # Individual variation
            personal = float(self.rng.normal(mean, std * 0.3))

            # Class offset
            cls_off = class_offsets.get(agent.agent_class, {}).get(ch, 0.0)
            personal += cls_off

            # Gender offset
            gen_off = gender_offsets.get(agent.gender, {}).get(ch, 0.0)
            personal += gen_off

            baselines[ch] = round(personal, 2)

        state = AgentWearableState(agent.agent_id, device, baselines)
        self._agent_states[agent.agent_id] = state
        return state

    def generate_epoch_data(
        self,
        agents: list[KorkinAgent],
        pathogen_profiles: dict[str, dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Generate wearable data for all monitored agents for one epoch.

        Returns ``{agent_id: {"device_id": str, "hourly": {...}, "summary": {...}}}``.
        """
        results: dict[int, dict[str, Any]] = {}
        for agent in agents:
            state = self._agent_states.get(agent.agent_id)
            if state is None:
                continue
            results[agent.agent_id] = self._generate_agent_epoch(
                agent, state, pathogen_profiles,
            )
        return results

    def _generate_agent_epoch(
        self,
        agent: KorkinAgent,
        state: AgentWearableState,
        pathogen_profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate one epoch of wearable data for a single agent."""
        device = state.device
        hourly: dict[str, list[float | None]] = {ch: [] for ch in device.channels}
        summary: dict[str, dict[str, Any]] = {}

        for ch in device.channels:
            noise_cfg = device.get_channel_noise(ch)
            sigma = noise_cfg.get("sigma", 1.0)
            drift_rate = noise_cfg.get("drift_rate", 0.0)
            dropout_prob = noise_cfg.get("dropout_prob", 0.0)

            baseline = state.baselines.get(ch, 0.0)

            # Infection perturbation
            inf_delta = _compute_infection_delta(
                ch, agent, pathogen_profiles,
                device.infection_responses, device.phase_boundaries,
            )

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

                # Compose reading
                value = baseline + inf_delta + circadian + sleep_mod + state.drift[ch]

                if ch in ("heart_rate", "activity_score"):
                    value = baseline + (circadian + sleep_mod + state.drift[ch]) * activity_mult + inf_delta

                # Add measurement noise
                value += float(self.rng.normal(0, sigma))

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

    def get_fleet_summary(self) -> dict[str, Any]:
        """Summary of the wearable fleet configuration."""
        return {
            "total_monitored": len(self._agent_states),
            "devices": {
                did: device.to_dict() for did, device in self.devices.items()
            },
            "class_device_map": dict(self.class_device_map),
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

    return WearableDevice(
        device_id=device_id,
        channels=channels,
        noise=noise,
        infection_responses=infection_responses,
        phase_boundaries=phase_boundaries,
        channel_baselines=channel_baselines,
    )


def build_wearable_monitor_from_config(
    cfg: dict[str, Any],
    rng: np.random.Generator | None = None,
) -> WearableMonitor | None:
    """Build the full WearableMonitor fleet from config.

    Returns None if wearable_monitoring is absent or disabled.
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

    class_device_map: dict[str, str] = {}
    for mapping in wm_cfg.get("class_device_map", []):
        agent_class = mapping.get("agent_class", "")
        device_id = mapping.get("device_id", "")
        if agent_class and device_id:
            class_device_map[agent_class] = device_id

    if not devices:
        return None

    anomaly_z_threshold = wm_cfg.get("anomaly_z_threshold", 2.0)

    return WearableMonitor(
        devices=devices,
        class_device_map=class_device_map,
        rng=rng,
        anomaly_z_threshold=anomaly_z_threshold,
    )
