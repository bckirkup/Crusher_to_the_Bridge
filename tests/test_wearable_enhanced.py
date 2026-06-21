"""
test_wearable_enhanced.py – Tests for enhanced wearable model (Issue #111)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers: multi-device, coverage fraction, visibility tiers,
chronic disease device map, confounders, detection profiles,
glucose channel, and backward-compatible config parsing.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.wearable_monitor import (
    AgentWearableState,
    DeviceAssignment,
    WearableDevice,
    WearableMonitor,
    build_wearable_device_from_config,
    build_wearable_monitor_from_config,
    DEFAULT_CHANNEL_BASELINES,
)
from engines.infection_dynamics_bridge import (
    KorkinAgent,
    InfectionStatus,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


def _make_agent(
    agent_id: int = 0,
    agent_class: str = "passenger_general",
    gender: str = "male",
    zone: str = "zone_A",
    infections: dict[str, dict[str, Any]] | None = None,
) -> KorkinAgent:
    """Build a minimal KorkinAgent for testing."""
    role = "passenger" if agent_class.startswith("passenger") else "crew"
    schedule = ["Sleep"] * 8 + ["Duty:Morning"] * 4 + ["Free:Dining"] * 2 + \
               ["Duty:Afternoon"] * 4 + ["Free:Recreation"] * 4 + ["Sleep"] * 2
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=zone,
        dining_zone="mess_hall",
        work_zone="bridge",
        free_zone="lounge",
        schedule=schedule,
        agent_class=agent_class,
        gender=gender,
    )
    if infections:
        agent.infections = infections
    return agent


def _make_oura_device() -> WearableDevice:
    return WearableDevice(
        device_id="oura_ring",
        channels=["heart_rate", "hrv", "body_temp"],
    )


def _make_garmin_device() -> WearableDevice:
    return WearableDevice(
        device_id="garmin_watch",
        channels=["heart_rate", "hrv", "body_temp", "activity_score"],
    )


def _make_cgm_device() -> WearableDevice:
    return WearableDevice(
        device_id="cgm_patch",
        channels=["body_temp", "glucose"],
        channel_baselines={"glucose": {"mean": 95.0, "std": 12.0}},
    )


# ── Multi-device per agent ───────────────────────────────────────────────


class TestMultiDevice:
    """Agents can be assigned multiple devices simultaneously."""

    def test_multi_device_assignment(self) -> None:
        oura = _make_oura_device()
        garmin = _make_garmin_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "garmin_watch": garmin},
            class_device_assignments={
                "default": [
                    DeviceAssignment("oura_ring"),
                    DeviceAssignment("garmin_watch"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(agent)
        assert len(states) == 2
        device_ids = {s.device.device_id for s in states}
        assert device_ids == {"oura_ring", "garmin_watch"}

    def test_agent_states_is_list(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={"default": [DeviceAssignment("oura_ring")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=5)
        monitor.initialize_agent(agent)
        states = monitor.agent_states.get(5)
        assert isinstance(states, list)
        assert len(states) == 1

    def test_epoch_data_aggregates_across_devices(self) -> None:
        oura = _make_oura_device()
        garmin = _make_garmin_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "garmin_watch": garmin},
            class_device_assignments={
                "default": [
                    DeviceAssignment("oura_ring"),
                    DeviceAssignment("garmin_watch"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        monitor.initialize_agent(agent)
        data = monitor.generate_epoch_data([agent], {})
        assert 1 in data
        epoch = data[1]
        assert "devices" in epoch
        assert len(epoch["devices"]) == 2
        assert isinstance(epoch["fever"], bool)
        assert isinstance(epoch["anomaly_count"], int)
        assert isinstance(epoch["visibility"], list)


# ── Coverage fraction ────────────────────────────────────────────────────


class TestCoverageFraction:
    """Coverage < 1.0 means some agents don't get the device."""

    def test_zero_coverage_no_assignment(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring", coverage=0.0)],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(agent)
        assert len(states) == 0
        assert 1 not in monitor.agent_states

    def test_full_coverage_always_assigned(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring", coverage=1.0)],
            },
            rng=np.random.default_rng(42),
        )
        for i in range(20):
            agent = _make_agent(agent_id=i)
            states = monitor.initialize_agent(agent)
            assert len(states) == 1

    def test_partial_coverage_probabilistic(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring", coverage=0.5)],
            },
            rng=np.random.default_rng(42),
        )
        assigned = 0
        for i in range(100):
            agent = _make_agent(agent_id=i)
            states = monitor.initialize_agent(agent)
            if len(states) > 0:
                assigned += 1
        # With 50% coverage and 100 agents, expect roughly 50 (20-80 range)
        assert 20 <= assigned <= 80


# ── Visibility tiers ─────────────────────────────────────────────────────


class TestVisibilityTiers:
    """Visibility controls whether data flows to medical staff stoplights."""

    def test_default_visibility_medical_staff(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(agent)
        assert states[0].visibility == "medical_staff"

    def test_wearer_only_visibility(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [
                    DeviceAssignment("oura_ring", visibility="wearer_only"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(agent)
        assert states[0].visibility == "wearer_only"

    def test_both_visibility(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [
                    DeviceAssignment("oura_ring", visibility="both"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(agent)
        assert states[0].visibility == "both"

    def test_visibility_in_epoch_data(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [
                    DeviceAssignment("oura_ring", visibility="both"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        monitor.initialize_agent(agent)
        data = monitor.generate_epoch_data([agent], {})
        assert data[1]["visibility"] == ["both"]

    def test_fleet_summary_visibility_breakdown(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "passenger_general": [
                    DeviceAssignment("oura_ring", visibility="medical_staff"),
                ],
                "crew_medical": [
                    DeviceAssignment("oura_ring", visibility="both"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        monitor.initialize_agent(_make_agent(0, "passenger_general"))
        monitor.initialize_agent(_make_agent(1, "crew_medical"))
        summary = monitor.get_fleet_summary()
        vis = summary["visibility_breakdown"]
        assert vis["medical_staff"] == 1
        assert vis["both"] == 1


# ── Chronic disease device map ───────────────────────────────────────────


class TestChronicDiseaseDeviceMap:
    """Agents with chronic diseases get additional devices."""

    def test_additive_chronic_device(self) -> None:
        oura = _make_oura_device()
        cgm = _make_cgm_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "cgm_patch": cgm},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
            },
            chronic_disease_device_map=[
                {"disease_id": "type2_diabetes", "device_id": "cgm_patch",
                 "coverage": 1.0, "visibility": "both"},
            ],
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(
            agent, chronic_disease_ids=["type2_diabetes"],
        )
        assert len(states) == 2
        device_ids = {s.device.device_id for s in states}
        assert "cgm_patch" in device_ids

    def test_no_chronic_disease_no_extra_device(self) -> None:
        oura = _make_oura_device()
        cgm = _make_cgm_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "cgm_patch": cgm},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
            },
            chronic_disease_device_map=[
                {"disease_id": "type2_diabetes", "device_id": "cgm_patch",
                 "coverage": 1.0},
            ],
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(agent)
        assert len(states) == 1
        assert states[0].device.device_id == "oura_ring"

    def test_chronic_device_respects_coverage(self) -> None:
        oura = _make_oura_device()
        cgm = _make_cgm_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "cgm_patch": cgm},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
            },
            chronic_disease_device_map=[
                {"disease_id": "type2_diabetes", "device_id": "cgm_patch",
                 "coverage": 0.0},
            ],
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(
            agent, chronic_disease_ids=["type2_diabetes"],
        )
        assert len(states) == 1  # Only oura_ring, cgm coverage=0

    def test_duplicate_device_not_added_twice(self) -> None:
        oura = _make_oura_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
            },
            chronic_disease_device_map=[
                {"disease_id": "type2_diabetes", "device_id": "oura_ring",
                 "coverage": 1.0},
            ],
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        states = monitor.initialize_agent(
            agent, chronic_disease_ids=["type2_diabetes"],
        )
        # Should not add oura_ring twice
        assert len(states) == 1


# ── Confounders ──────────────────────────────────────────────────────────


class TestConfounders:
    """Per-epoch confounder model with bias + noise multiplier."""

    def test_sample_confounders_susceptible_class(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate", "hrv"],
            confounders=[{
                "confounder_id": "seasickness",
                "prevalence": 1.0,  # always active
                "affected_channels": {
                    "heart_rate": {"bias": 8.0, "noise_mult": 1.5},
                },
                "susceptible_classes": ["passenger_general"],
            }],
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1, agent_class="passenger_general")
        effects = monitor._sample_confounders(agent, device)
        assert "seasickness" in effects
        assert "heart_rate" in effects["seasickness"]

    def test_sample_confounders_not_susceptible(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate", "hrv"],
            confounders=[{
                "confounder_id": "seasickness",
                "prevalence": 1.0,
                "affected_channels": {
                    "heart_rate": {"bias": 8.0, "noise_mult": 1.5},
                },
                "susceptible_classes": ["passenger_general"],
            }],
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1, agent_class="crew_medical")
        effects = monitor._sample_confounders(agent, device)
        assert len(effects) == 0

    def test_sample_confounders_empty_susceptible_means_all(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate"],
            confounders=[{
                "confounder_id": "exercise",
                "prevalence": 1.0,
                "affected_channels": {
                    "heart_rate": {"bias": 15.0, "noise_mult": 1.2},
                },
                "susceptible_classes": [],  # all classes susceptible
            }],
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1, agent_class="crew_engineering")
        effects = monitor._sample_confounders(agent, device)
        assert "exercise" in effects

    def test_confounder_zero_prevalence_never_active(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate"],
            confounders=[{
                "confounder_id": "exercise",
                "prevalence": 0.0,
                "affected_channels": {
                    "heart_rate": {"bias": 15.0, "noise_mult": 1.2},
                },
                "susceptible_classes": [],
            }],
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        for i in range(20):
            agent = _make_agent(agent_id=i)
            effects = monitor._sample_confounders(agent, device)
            assert len(effects) == 0


# ── Detection profile ───────────────────────────────────────────────────


class TestDetectionProfile:
    """Sensitivity/specificity/latency gating on anomaly and fever flags."""

    def test_perfect_detection_profile_no_change(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate", "body_temp"],
            detection_profile={
                "sensitivity": 1.0,
                "specificity": 1.0,
                "alert_latency_hours": 0,
                "fever_sensitivity": 1.0,
                "fever_specificity": 1.0,
            },
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        result = {
            "fever": True,
            "anomaly_channels": ["heart_rate"],
            "anomaly_count": 1,
            "summary": {"heart_rate": {"anomaly": True}},
        }
        gated = monitor._apply_detection_profile(agent, device, result)
        assert gated["fever"] is True
        assert gated["anomaly_count"] == 1

    def test_no_detection_profile_passthrough(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate"],
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        result = {"fever": True, "anomaly_channels": ["heart_rate"],
                  "anomaly_count": 1, "summary": {"heart_rate": {"anomaly": True}}}
        gated = monitor._apply_detection_profile(agent, device, result)
        assert gated is result  # unchanged

    def test_zero_sensitivity_suppresses_true_positives(self) -> None:
        device = WearableDevice(
            device_id="test_device",
            channels=["heart_rate"],
            detection_profile={
                "sensitivity": 0.0,
                "specificity": 1.0,
                "alert_latency_hours": 0,
                "fever_sensitivity": 0.0,
                "fever_specificity": 1.0,
            },
        )
        monitor = WearableMonitor(
            devices={"test_device": device},
            class_device_assignments={"default": [DeviceAssignment("test_device")]},
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(
            agent_id=1,
            infections={"norovirus": {
                "status": InfectionStatus.INFECTED,
                "time_infected": 5,
            }},
        )
        result = {
            "fever": True,
            "anomaly_channels": ["heart_rate"],
            "anomaly_count": 1,
            "summary": {"heart_rate": {"anomaly": True}},
        }
        gated = monitor._apply_detection_profile(agent, device, result)
        assert gated["anomaly_count"] == 0
        assert gated["fever"] is False


# ── Glucose channel ──────────────────────────────────────────────────────


class TestGlucoseChannel:
    """Glucose channel with cgm_patch device."""

    def test_glucose_in_defaults(self) -> None:
        assert "glucose" in DEFAULT_CHANNEL_BASELINES
        assert DEFAULT_CHANNEL_BASELINES["glucose"]["mean"] == 95.0

    def test_glucose_channel_on_device(self) -> None:
        cgm = _make_cgm_device()
        assert "glucose" in cgm.channels
        baseline = cgm.get_channel_baseline("glucose")
        assert baseline["mean"] == 95.0
        assert baseline["std"] == 12.0

    def test_glucose_epoch_data_generated(self) -> None:
        cgm = _make_cgm_device()
        monitor = WearableMonitor(
            devices={"cgm_patch": cgm},
            class_device_assignments={
                "default": [DeviceAssignment("cgm_patch")],
            },
            rng=np.random.default_rng(42),
        )
        agent = _make_agent(agent_id=1)
        monitor.initialize_agent(agent)
        data = monitor.generate_epoch_data([agent], {})
        assert 1 in data
        # Glucose should be in the first device's data
        devices = data[1]["devices"]
        assert len(devices) == 1
        assert "glucose" in devices[0]["hourly"]
        assert len(devices[0]["hourly"]["glucose"]) == 24


# ── Config parsing ───────────────────────────────────────────────────────


class TestConfigParsing:
    """Backward-compatible config parsing for old and new formats."""

    def test_old_single_device_format(self) -> None:
        cfg = {
            "wearable_monitoring": {
                "enabled": True,
                "devices": [{
                    "device_id": "oura_ring",
                    "channels": ["heart_rate", "body_temp"],
                }],
                "class_device_map": [
                    {"agent_class": "default", "device_id": "oura_ring"},
                ],
            },
        }
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        assert "default" in monitor.class_device_assignments
        assignments = monitor.class_device_assignments["default"]
        assert len(assignments) == 1
        assert assignments[0].device_id == "oura_ring"

    def test_new_multi_device_format(self) -> None:
        cfg = {
            "wearable_monitoring": {
                "enabled": True,
                "devices": [
                    {"device_id": "oura_ring", "channels": ["heart_rate"]},
                    {"device_id": "garmin_watch", "channels": ["heart_rate", "activity_score"]},
                ],
                "class_device_map": [
                    {
                        "agent_class": "default",
                        "devices": [
                            {"device_id": "oura_ring", "coverage": 0.8, "visibility": "medical_staff"},
                            {"device_id": "garmin_watch", "coverage": 0.6, "visibility": "both"},
                        ],
                    },
                ],
            },
        }
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        assignments = monitor.class_device_assignments["default"]
        assert len(assignments) == 2
        assert assignments[0].coverage == 0.8
        assert assignments[1].visibility == "both"

    def test_disabled_config_returns_none(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": False}}
        monitor = build_wearable_monitor_from_config(cfg)
        assert monitor is None

    def test_detection_profile_parsed(self) -> None:
        cfg = {
            "wearable_monitoring": {
                "enabled": True,
                "devices": [{
                    "device_id": "oura_ring",
                    "channels": ["heart_rate"],
                    "detection_profile": {
                        "sensitivity": 0.78,
                        "specificity": 0.92,
                        "alert_latency_hours": 6,
                    },
                }],
                "class_device_map": [
                    {"agent_class": "default", "device_id": "oura_ring"},
                ],
            },
        }
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        device = monitor.devices["oura_ring"]
        assert device.detection_profile is not None
        assert device.detection_profile["sensitivity"] == 0.78

    def test_confounders_parsed(self) -> None:
        cfg = {
            "wearable_monitoring": {
                "enabled": True,
                "devices": [{
                    "device_id": "oura_ring",
                    "channels": ["heart_rate", "hrv"],
                    "confounders": [{
                        "confounder_id": "seasickness",
                        "prevalence": 0.15,
                        "affected_channels": {
                            "heart_rate": {"bias": 8.0, "noise_mult": 1.5},
                        },
                        "susceptible_classes": ["passenger_general"],
                    }],
                }],
                "class_device_map": [
                    {"agent_class": "default", "device_id": "oura_ring"},
                ],
            },
        }
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        device = monitor.devices["oura_ring"]
        assert len(device.confounders) == 1
        assert device.confounders[0]["confounder_id"] == "seasickness"

    def test_chronic_disease_device_map_parsed(self) -> None:
        cfg = {
            "wearable_monitoring": {
                "enabled": True,
                "devices": [
                    {"device_id": "oura_ring", "channels": ["heart_rate"]},
                    {"device_id": "cgm_patch", "channels": ["glucose"]},
                ],
                "class_device_map": [
                    {"agent_class": "default", "device_id": "oura_ring"},
                ],
                "chronic_disease_device_map": [
                    {"disease_id": "type2_diabetes", "device_id": "cgm_patch",
                     "coverage": 0.8, "visibility": "both"},
                ],
            },
        }
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        assert len(monitor.chronic_disease_device_map) == 1
        assert monitor.chronic_disease_device_map[0]["disease_id"] == "type2_diabetes"

    def test_build_device_with_channel_baselines(self) -> None:
        device_cfg = {
            "device_id": "cgm_patch",
            "channels": ["body_temp", "glucose"],
            "channel_baselines": [
                {"channel": "glucose", "mean": 95.0, "std": 12.0},
            ],
        }
        device = build_wearable_device_from_config(device_cfg)
        assert device.device_id == "cgm_patch"
        assert "glucose" in device.channel_baselines
        assert device.channel_baselines["glucose"]["mean"] == 95.0


# ── Fleet summary ────────────────────────────────────────────────────────


class TestFleetSummary:
    """Fleet summary reflects multi-device architecture."""

    def test_total_device_instances_exceeds_agents(self) -> None:
        oura = _make_oura_device()
        garmin = _make_garmin_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "garmin_watch": garmin},
            class_device_assignments={
                "default": [
                    DeviceAssignment("oura_ring"),
                    DeviceAssignment("garmin_watch"),
                ],
            },
            rng=np.random.default_rng(42),
        )
        for i in range(5):
            monitor.initialize_agent(_make_agent(agent_id=i))
        summary = monitor.get_fleet_summary()
        assert summary["total_monitored"] == 5
        assert summary["total_device_instances"] == 10

    def test_device_deployment_counts(self) -> None:
        oura = _make_oura_device()
        garmin = _make_garmin_device()
        monitor = WearableMonitor(
            devices={"oura_ring": oura, "garmin_watch": garmin},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
                "crew_medical": [DeviceAssignment("garmin_watch")],
            },
            rng=np.random.default_rng(42),
        )
        for i in range(3):
            monitor.initialize_agent(_make_agent(agent_id=i, agent_class="passenger_general"))
        monitor.initialize_agent(_make_agent(agent_id=10, agent_class="crew_medical"))
        counts = monitor.get_fleet_summary()["device_deployment_counts"]
        assert counts["oura_ring"] == 3
        assert counts["garmin_watch"] == 1


# ── From-config integration ──────────────────────────────────────────────


class TestFromConfigIntegration:
    """Load full config.yaml and verify enhanced features."""

    def _load_cfg(self) -> dict[str, Any]:
        import yaml
        config_path = os.path.join(REPO_ROOT, "crusher_labs", "config.yaml")
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_cgm_patch_in_devices(self) -> None:
        cfg = self._load_cfg()
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        assert "cgm_patch" in monitor.devices
        cgm = monitor.devices["cgm_patch"]
        assert "glucose" in cgm.channels
        assert "body_temp" in cgm.channels

    def test_detection_profiles_present(self) -> None:
        cfg = self._load_cfg()
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        for did in ("oura_ring", "garmin_watch", "cgm_patch"):
            device = monitor.devices[did]
            assert device.detection_profile is not None, f"{did} missing detection_profile"

    def test_confounders_on_oura(self) -> None:
        cfg = self._load_cfg()
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        oura = monitor.devices["oura_ring"]
        assert len(oura.confounders) >= 2  # seasickness + alcohol + exercise

    def test_chronic_disease_device_map_present(self) -> None:
        cfg = self._load_cfg()
        monitor = build_wearable_monitor_from_config(cfg, np.random.default_rng(42))
        assert monitor is not None
        assert len(monitor.chronic_disease_device_map) >= 1
        assert monitor.chronic_disease_device_map[0]["disease_id"] == "type2_diabetes"
