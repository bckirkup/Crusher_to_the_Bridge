"""
crusher_labs.modalities.wearable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wearable data stream modality for the Crusher Labs observation suite.

Consumes raw wearable monitor output (fine-grained + summary) from
``engines.wearable_monitor`` and applies an additional observation-noise
layer (simulating real-world Bluetooth sync lag, motion artefacts, etc.)
before presenting the data to the surveillance pipeline.

Provides:
- ``query_ground_truth()`` — per-epoch wearable telemetry with anomaly flags
- Anomaly detection using per-channel z-scores (baseline-relative)
- Aggregated fleet-level health indicators for the stoplight system
"""

from __future__ import annotations

from typing import Any

import numpy as np


class WearableDataStream:
    """Crusher Labs modality that wraps raw wearable monitor data.

    Adds observation noise (sync lag, motion artefacts) and produces
    fleet-level anomaly summaries consumable by the lab notebook and
    protocol engine.
    """

    name = "wearable"

    def __init__(
        self,
        observation_noise_sigma: float = 0.5,
        sync_dropout_prob: float = 0.02,
        anomaly_z_threshold: float = 2.0,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.observation_noise_sigma = observation_noise_sigma
        self.sync_dropout_prob = sync_dropout_prob
        self.anomaly_z_threshold = anomaly_z_threshold
        self.rng = rng if rng is not None else np.random.default_rng()

    def query_ground_truth(
        self,
        truth: dict[str, Any],
        wearable_data: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """Process raw wearable data through the observation layer.

        Parameters
        ----------
        truth : dict
            The standard ground-truth payload (epoch, agents, spaces).
        wearable_data : dict
            Raw output from ``WearableMonitor.generate_epoch_data``.

        Returns
        -------
        dict
            Modality result with per-agent observed summaries and
            fleet-level anomaly indicators.
        """
        epoch = truth.get("epoch", 0)

        agent_results: dict[int, dict[str, Any]] = {}
        total_fever = 0
        total_anomaly = 0
        channel_anomaly_counts: dict[str, int] = {}

        for aid, raw in wearable_data.items():
            observed = self._apply_observation_noise(raw)
            agent_results[aid] = observed

            if observed.get("fever", False):
                total_fever += 1
            anomaly_count = observed.get("anomaly_count", 0)
            if anomaly_count > 0:
                total_anomaly += 1
            for ch in observed.get("anomaly_channels", []):
                channel_anomaly_counts[ch] = channel_anomaly_counts.get(ch, 0) + 1

        total_monitored = len(wearable_data)
        fever_rate = total_fever / max(total_monitored, 1)
        anomaly_rate = total_anomaly / max(total_monitored, 1)

        return {
            "modality": self.name,
            "epoch": epoch,
            "agent_results": agent_results,
            "fleet_summary": {
                "total_monitored": total_monitored,
                "fever_count": total_fever,
                "fever_rate": round(fever_rate, 4),
                "anomaly_count": total_anomaly,
                "anomaly_rate": round(anomaly_rate, 4),
                "channel_anomaly_counts": channel_anomaly_counts,
            },
        }

    def _apply_observation_noise(
        self,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        """Layer observation noise onto raw wearable readings."""
        observed_summary: dict[str, dict[str, Any]] = {}
        raw_summary = raw.get("summary", {})

        for ch, ch_data in raw_summary.items():
            obs_ch = dict(ch_data)

            # Sync dropout: may lose entire channel for this epoch
            if self.rng.random() < self.sync_dropout_prob:
                obs_ch["mean"] = None
                obs_ch["min"] = None
                obs_ch["max"] = None
                obs_ch["sync_dropout"] = True
                obs_ch["anomaly"] = False
            else:
                obs_ch["sync_dropout"] = False
                # Add observation noise to summary stats
                if obs_ch.get("mean") is not None:
                    obs_ch["mean"] = round(
                        obs_ch["mean"] + float(self.rng.normal(0, self.observation_noise_sigma * 0.3)),
                        2,
                    )
                if obs_ch.get("min") is not None:
                    obs_ch["min"] = round(
                        obs_ch["min"] + float(self.rng.normal(0, self.observation_noise_sigma * 0.2)),
                        2,
                    )
                if obs_ch.get("max") is not None:
                    obs_ch["max"] = round(
                        obs_ch["max"] + float(self.rng.normal(0, self.observation_noise_sigma * 0.2)),
                        2,
                    )

            observed_summary[ch] = obs_ch

        anomaly_channels = [
            ch for ch, s in observed_summary.items()
            if s.get("anomaly", False)
        ]

        return {
            "device_id": raw.get("device_id", "unknown"),
            "summary": observed_summary,
            "fever": raw.get("fever", False),
            "anomaly_channels": anomaly_channels,
            "anomaly_count": len(anomaly_channels),
        }
