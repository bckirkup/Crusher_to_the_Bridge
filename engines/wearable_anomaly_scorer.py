"""
engines.wearable_anomaly_scorer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confounder-aware infection scoring for wearable physiological alerts.

Replaces naive multi-channel anomaly counting with weighted residual scoring
that subtracts confounder template matches and downweights fleet-wide events.
"""

from __future__ import annotations

import math
from typing import Any


from simulation_utils.numeric import is_nonzero, is_zero


DEFAULT_CHANNEL_INFECTION_WEIGHTS: dict[str, float] = {
    "heart_rate": 0.3,
    "hrv": 0.3,
    "body_temp": 1.0,
    "spo2": 0.8,
    "sleep_score": 0.2,
    "activity_score": 0.4,
    "respiratory_rate": 0.6,
    "glucose": 1.0,
}

DEFAULT_CONFOUNDER_TEMPLATES: dict[str, dict[str, float]] = {
    "seasickness": {
        "heart_rate": 2.0,
        "hrv": -2.5,
        "body_temp": 0.0,
        "spo2": 0.0,
        "activity_score": 0.5,
        "glucose": 0.0,
    },
    "alcohol": {
        "heart_rate": 1.5,
        "hrv": -2.0,
        "body_temp": 0.0,
        "sleep_score": -2.0,
        "activity_score": 0.0,
        "glucose": 1.5,
    },
    "exercise": {
        "heart_rate": 4.0,
        "hrv": -1.0,
        "activity_score": 3.0,
        "body_temp": 0.3,
        "spo2": 0.0,
        "glucose": -0.5,
    },
    "meal_glucose_spike": {
        "glucose": 2.5,
        "heart_rate": 0.0,
    },
    "wrist_motion": {
        "heart_rate": 1.0,
        "spo2": 0.5,
    },
}


def _cosine_similarity(
    vec_a: dict[str, float],
    vec_b: dict[str, float],
) -> float:
    """Cosine similarity over the union of channel keys."""
    keys = set(vec_a) | set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in keys)
    norm_a = math.sqrt(sum(vec_a.get(k, 0.0) ** 2 for k in keys))
    norm_b = math.sqrt(sum(vec_b.get(k, 0.0) ** 2 for k in keys))
    if is_zero(norm_a) or is_zero(norm_b):
        return 0.0
    return dot / (norm_a * norm_b)


def _signed_z_scores(
    summary: dict[str, dict[str, Any]],
    anomaly_z_threshold: float,
) -> dict[str, float]:
    """Extract signed z-scores for anomalous channels from a summary dict."""
    z_scores: dict[str, float] = {}
    for ch, ch_data in summary.items():
        if not ch_data.get("anomaly", False):
            continue
        if "signed_z_score" in ch_data:
            z_scores[ch] = float(ch_data["signed_z_score"])
        else:
            z = float(ch_data.get("z_score", 0.0) or 0.0)
            if z > anomaly_z_threshold:
                z_scores[ch] = z
    return z_scores


class WearableAnomalyScorer:
    """Score agent wearable data for infection signal after confounder removal."""

    def __init__(
        self,
        channel_weights: dict[str, float],
        infection_score_threshold: float = 1.5,
        anomaly_z_threshold: float = 2.0,
        fleet_anomaly_floor: float = 0.15,
        fleet_anomaly_downweight: float = 0.1,
        confounder_match_threshold: float = 0.7,
        confounder_templates: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self.channel_weights = dict(channel_weights)
        self.infection_score_threshold = infection_score_threshold
        self.anomaly_z_threshold = anomaly_z_threshold
        self.fleet_anomaly_floor = fleet_anomaly_floor
        self.fleet_anomaly_downweight = fleet_anomaly_downweight
        self.confounder_match_threshold = confounder_match_threshold
        self.confounder_templates = confounder_templates or {}

    def _match_confounders(
        self,
        z_scores: dict[str, float],
    ) -> tuple[set[str], list[str]]:
        explained_channels: set[str] = set()
        matched_confounders: list[str] = []
        for cid, template in self.confounder_templates.items():
            similarity = _cosine_similarity(z_scores, template)
            if similarity >= self.confounder_match_threshold:
                matched_confounders.append(cid)
                for ch, tz in template.items():
                    if is_nonzero(tz) and ch in z_scores:
                        explained_channels.add(ch)
        return explained_channels, matched_confounders

    def _residual_infection_score(
        self,
        z_scores: dict[str, float],
        explained_channels: set[str],
        fleet_anomaly_rates: dict[str, float],
    ) -> float:
        infection_score = 0.0
        for ch, z in z_scores.items():
            if ch in explained_channels:
                continue
            weight = self.channel_weights.get(ch, 0.3)
            fleet_rate = fleet_anomaly_rates.get(ch, 0.0)
            if fleet_rate > self.fleet_anomaly_floor:
                weight *= self.fleet_anomaly_downweight
            infection_score += abs(z) * weight
        return infection_score

    def score_agent(
        self,
        summary: dict[str, dict[str, Any]],
        fleet_anomaly_rates: dict[str, float],
    ) -> tuple[float, list[str]]:
        """Return (infection_score, matched_confounder_ids) for one agent."""
        z_scores = _signed_z_scores(summary, self.anomaly_z_threshold)
        if not z_scores:
            return 0.0, []

        explained_channels, matched_confounders = self._match_confounders(z_scores)
        infection_score = self._residual_infection_score(
            z_scores, explained_channels, fleet_anomaly_rates,
        )

        return round(infection_score, 3), matched_confounders

    def compute_fleet_anomaly_rates(
        self,
        agent_summaries: list[dict[str, dict[str, Any]]],
    ) -> dict[str, float]:
        """Compute per-channel fleet anomaly rate across monitored agents."""
        if not agent_summaries:
            return {}
        channel_counts: dict[str, int] = {}
        n_agents = len(agent_summaries)
        for summary in agent_summaries:
            for ch, ch_data in summary.items():
                if ch_data.get("anomaly", False):
                    channel_counts[ch] = channel_counts.get(ch, 0) + 1
        return {
            ch: count / n_agents
            for ch, count in channel_counts.items()
        }


def _load_confounder_templates(
    block: dict[str, Any],
    devices: dict[str, Any] | None,
) -> dict[str, dict[str, float]]:
    templates: dict[str, dict[str, float]] = dict(DEFAULT_CONFOUNDER_TEMPLATES)

    global_templates = block.get("confounder_templates", {})
    if isinstance(global_templates, dict):
        for cid, tvec in global_templates.items():
            if isinstance(tvec, dict):
                templates[cid] = {k: float(v) for k, v in tvec.items()}

    if devices:
        for device in devices.values():
            for conf in getattr(device, "confounders", []) or []:
                cid = conf.get("confounder_id", "")
                tvec = conf.get("template_z_vector")
                if cid and isinstance(tvec, dict):
                    templates[cid] = {k: float(v) for k, v in tvec.items()}

    return templates


def build_wearable_anomaly_scorer_from_config(
    wm_cfg: dict[str, Any],
    devices: dict[str, Any] | None = None,
) -> WearableAnomalyScorer | None:
    """Build scorer from wearable_monitoring config; None if disabled."""
    ad_cfg = wm_cfg.get("anomaly_detection")
    if ad_cfg is not None and not ad_cfg.get("enabled", True):
        return None

    block = ad_cfg or wm_cfg
    channel_weights = dict(
        block.get("channel_infection_weights", DEFAULT_CHANNEL_INFECTION_WEIGHTS),
    )
    templates = _load_confounder_templates(block, devices)

    return WearableAnomalyScorer(
        channel_weights=channel_weights,
        infection_score_threshold=float(
            block.get("infection_score_threshold", 1.5),
        ),
        anomaly_z_threshold=float(block.get("anomaly_z_threshold", 2.0)),
        fleet_anomaly_floor=float(block.get("fleet_anomaly_floor", 0.15)),
        fleet_anomaly_downweight=float(
            block.get("fleet_anomaly_downweight", 0.1),
        ),
        confounder_match_threshold=float(
            block.get("confounder_match_threshold", 0.7),
        ),
        confounder_templates=templates,
    )
