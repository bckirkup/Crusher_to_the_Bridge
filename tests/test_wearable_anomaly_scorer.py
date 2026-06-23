"""Tests for confounder-aware wearable infection scoring."""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.wearable_anomaly_scorer import (
    WearableAnomalyScorer,
    build_wearable_anomaly_scorer_from_config,
)
from engines.wearable_monitor import (
    DeviceAssignment,
    WearableDevice,
    WearableMonitor,
    build_wearable_monitor_from_config,
)
from engines.infection_dynamics_bridge import KorkinAgent, InfectionStatus
from crusher_labs.cascade_entry import (
    WearableAlertFusionConfig,
    evaluate_wearable_alert,
)


def _make_agent(agent_id: int = 0) -> KorkinAgent:
    schedule = ["Sleep"] * 24
    return KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone="zone_A",
        dining_zone="mess_hall",
        work_zone="bridge",
        free_zone="lounge",
        schedule=schedule,
        agent_class="passenger_general",
        gender="male",
    )


def _summary_with_anomalies(
    channels: dict[str, float],
    *,
    signed: bool = True,
) -> dict[str, dict]:
    """Build a summary dict with anomalous z-scores on named channels."""
    summary: dict[str, dict] = {}
    for ch, z in channels.items():
        entry: dict = {"z_score": abs(z), "anomaly": True, "mean": 0.0}
        if signed:
            entry["signed_z_score"] = z
        summary[ch] = entry
    return summary


class TestWearableAnomalyScorer:
    def test_seasickness_pattern_low_infection_score(self) -> None:
        scorer = WearableAnomalyScorer(
            channel_weights={"heart_rate": 0.3, "hrv": 0.3, "body_temp": 1.0},
            confounder_templates={
                "seasickness": {
                    "heart_rate": 2.0,
                    "hrv": -2.5,
                    "body_temp": 0.0,
                },
            },
            confounder_match_threshold=0.7,
        )
        summary = _summary_with_anomalies({
            "heart_rate": 2.5,
            "hrv": -3.0,
        })
        score, matched = scorer.score_agent(summary, {})
        assert "seasickness" in matched
        assert score < 1.5

    def test_infection_pattern_high_score(self) -> None:
        scorer = WearableAnomalyScorer(
            channel_weights={"body_temp": 1.0, "glucose": 1.0},
            confounder_templates={
                "seasickness": {"heart_rate": 2.0, "hrv": -2.5},
            },
        )
        summary = _summary_with_anomalies({
            "body_temp": 3.0,
            "glucose": 2.5,
        })
        score, matched = scorer.score_agent(summary, {})
        assert matched == []
        assert score > 1.5

    def test_fleet_wide_downweight(self) -> None:
        scorer = WearableAnomalyScorer(
            channel_weights={"heart_rate": 0.3},
            fleet_anomaly_floor=0.15,
            fleet_anomaly_downweight=0.1,
            confounder_templates={},
        )
        summary = _summary_with_anomalies({"heart_rate": 3.0})
        score_high_fleet, _ = scorer.score_agent(
            summary, {"heart_rate": 0.5},
        )
        score_low_fleet, _ = scorer.score_agent(
            summary, {"heart_rate": 0.05},
        )
        assert score_high_fleet < score_low_fleet

    def test_fever_still_triggers_cascade(self) -> None:
        fusion = WearableAlertFusionConfig()
        assert evaluate_wearable_alert(
            {"fever": True, "infection_score": 0.0}, fusion,
        )
        assert not evaluate_wearable_alert(
            {"fever": False, "infection_score": 0.5}, fusion,
        )
        assert evaluate_wearable_alert(
            {"fever": False, "infection_score": 2.0}, fusion,
        )

    def test_compute_fleet_anomaly_rates(self) -> None:
        scorer = WearableAnomalyScorer(channel_weights={})
        summaries = [
            _summary_with_anomalies({"heart_rate": 2.5}),
            _summary_with_anomalies({"heart_rate": 3.0, "hrv": 2.5}),
            {},
        ]
        rates = scorer.compute_fleet_anomaly_rates(summaries)
        assert rates["heart_rate"] == pytest.approx(2 / 3)
        assert rates["hrv"] == pytest.approx(1 / 3)


class TestScorerIntegration:
    def test_generate_epoch_data_includes_infection_score(self) -> None:
        device = WearableDevice(
            device_id="oura_ring",
            channels=["heart_rate", "hrv", "body_temp"],
            confounders=[
                {
                    "confounder_id": "seasickness",
                    "prevalence": 0.0,
                    "affected_channels": {
                        "heart_rate": {"bias": 8.0, "noise_mult": 1.5},
                        "hrv": {"bias": -12.0, "noise_mult": 1.8},
                    },
                },
            ],
        )
        scorer = WearableAnomalyScorer(
            channel_weights={"heart_rate": 0.3, "hrv": 0.3, "body_temp": 1.0},
        )
        monitor = WearableMonitor(
            devices={"oura_ring": device},
            class_device_assignments={
                "default": [DeviceAssignment("oura_ring")],
            },
            rng=np.random.default_rng(42),
            anomaly_scorer=scorer,
        )
        agents = [_make_agent(i) for i in range(10)]
        for a in agents:
            monitor.initialize_agent(a)
        data = monitor.generate_epoch_data(agents, {})
        for aid, epoch in data.items():
            assert "infection_score" in epoch
            assert "matched_confounders" in epoch
            assert isinstance(epoch["infection_score"], float)

    def test_build_from_config(self) -> None:
        wm_cfg = {
            "anomaly_detection": {
                "enabled": True,
                "infection_score_threshold": 1.5,
                "channel_infection_weights": {"body_temp": 1.0},
            },
        }
        scorer = build_wearable_anomaly_scorer_from_config(wm_cfg)
        assert scorer is not None
        assert scorer.infection_score_threshold == 1.5

    def test_build_monitor_from_config_has_scorer(self) -> None:
        import yaml
        cfg_path = os.path.join(REPO_ROOT, "crusher_labs", "config.yaml")
        with open(cfg_path, encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        monitor = build_wearable_monitor_from_config(
            cfg, rng=np.random.default_rng(0), repo_root=REPO_ROOT,
        )
        assert monitor is not None
        assert monitor.anomaly_scorer is not None
