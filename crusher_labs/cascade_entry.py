"""
Cascade entry tiers and wearable sensor fusion for the diagnostic cascade.

Sick-call self-reports enter at Tier 1 (rapid testing). Wearable alerts enter
at Tier 0 (clinical triage). Wearable device aggregation and alert gating are
configurable at runtime via ``diagnostic_cascade.entry`` in config.yaml or the
cascade JSON file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DEFAULT_WEARABLE_ALERT_RULES: list[dict[str, Any]] = [
    {"signal": "fever", "equals": True},
    {"signal": "anomaly_count", "operator": ">=", "value": 2},
]


@dataclass(frozen=True)
class WearableDeviceFusionConfig:
    """How to fuse readings across multiple wearable devices on one agent."""

    fever: str = "any"
    anomaly_channels: str = "union"

    @classmethod
    def from_config(cls, raw: dict[str, Any] | None) -> WearableDeviceFusionConfig:
        block = raw or {}
        fever = str(block.get("fever", "any"))
        channels = str(block.get("anomaly_channels", "union"))
        if fever not in {"any", "all", "majority"}:
            raise ValueError(
                f"wearable device fusion fever mode must be any|all|majority, got {fever!r}",
            )
        if channels not in {"union", "intersection"}:
            raise ValueError(
                "wearable device fusion anomaly_channels must be union|intersection, "
                f"got {channels!r}",
            )
        return cls(fever=fever, anomaly_channels=channels)


@dataclass(frozen=True)
class WearableAlertFusionConfig:
    """Rules that map fused wearable signals to a cascade Tier-0 entry."""

    operator: str = "or"
    rules: tuple[dict[str, Any], ...] = field(
        default_factory=lambda: tuple(DEFAULT_WEARABLE_ALERT_RULES),
    )

    @classmethod
    def from_config(cls, raw: dict[str, Any] | None) -> WearableAlertFusionConfig:
        block = raw or {}
        operator = str(block.get("operator", "or")).lower()
        if operator not in {"or", "and"}:
            raise ValueError(f"wearable alert fusion operator must be or|and, got {operator!r}")
        rules_raw = block.get("rules", DEFAULT_WEARABLE_ALERT_RULES)
        if not isinstance(rules_raw, list) or not rules_raw:
            raise ValueError("wearable alert fusion rules must be a non-empty list")
        return cls(operator=operator, rules=tuple(rules_raw))


@dataclass(frozen=True)
class CascadeEntryConfig:
    """Runtime cascade entry routing for sick-call vs wearable sources."""

    sick_call_tier: int = 1
    wearable_alert_tier: int = 0
    wearable_device_fusion: WearableDeviceFusionConfig = field(
        default_factory=WearableDeviceFusionConfig,
    )
    wearable_alert_fusion: WearableAlertFusionConfig = field(
        default_factory=WearableAlertFusionConfig,
    )

    @classmethod
    def from_config(
        cls,
        cascade_json: dict[str, Any] | None = None,
        runtime_cfg: dict[str, Any] | None = None,
    ) -> CascadeEntryConfig:
        """Merge cascade JSON ``cascade_entry`` with config.yaml overrides."""
        merged: dict[str, Any] = {}
        if cascade_json:
            merged.update(cascade_json.get("cascade_entry", {}))
        if runtime_cfg:
            merged = _deep_merge_dict(merged, runtime_cfg.get("entry", {}))

        sick_call_tier = int(merged.get("sick_call_tier", 1))
        wearable_alert_tier = int(merged.get("wearable_alert_tier", 0))
        if sick_call_tier < 0 or wearable_alert_tier < 0:
            raise ValueError("cascade entry tiers must be non-negative integers")

        return cls(
            sick_call_tier=sick_call_tier,
            wearable_alert_tier=wearable_alert_tier,
            wearable_device_fusion=WearableDeviceFusionConfig.from_config(
                merged.get("wearable_device_fusion"),
            ),
            wearable_alert_fusion=WearableAlertFusionConfig.from_config(
                merged.get("wearable_alert_fusion"),
            ),
        )


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _eval_fusion_rule(agent_data: dict[str, Any], rule: dict[str, Any]) -> bool:
    signal = str(rule.get("signal", ""))
    if not signal:
        raise ValueError("wearable fusion rule missing signal")

    if signal == "fever":
        actual = bool(agent_data.get("fever", False))
        if "equals" in rule:
            return actual == bool(rule["equals"])
        return actual

    if signal == "anomaly_count":
        actual = int(agent_data.get("anomaly_count", 0))
        op = str(rule.get("operator", ">="))
        expected = rule.get("value", 0)
        if not isinstance(expected, (int, float)):
            raise ValueError("anomaly_count rule value must be numeric")
        threshold = int(expected)
        if op == ">=":
            return actual >= threshold
        if op == ">":
            return actual > threshold
        if op == "==":
            return actual == threshold
        if op == "<=":
            return actual <= threshold
        if op == "<":
            return actual < threshold
        raise ValueError(f"unsupported anomaly_count operator: {op}")

    if signal == "anomaly_channels":
        channels = agent_data.get("anomaly_channels", [])
        count = len(channels) if isinstance(channels, list) else 0
        op = str(rule.get("operator", ">="))
        expected = int(rule.get("value", 1))
        if op == ">=":
            return count >= expected
        if op == "==":
            return count == expected
        raise ValueError(f"unsupported anomaly_channels operator: {op}")

    raise ValueError(f"unsupported wearable fusion signal: {signal}")


def evaluate_wearable_alert(
    agent_data: dict[str, Any],
    fusion: WearableAlertFusionConfig,
) -> bool:
    """Return True when fused wearable data should enter cascade Tier 0."""
    if not fusion.rules:
        return False
    outcomes = [_eval_fusion_rule(agent_data, rule) for rule in fusion.rules]
    if fusion.operator == "and":
        return all(outcomes)
    return any(outcomes)


def fuse_device_results(
    device_results: list[dict[str, Any]],
    fusion: WearableDeviceFusionConfig,
) -> dict[str, Any]:
    """Fuse per-device wearable epoch payloads into one agent-level report."""
    if not device_results:
        return {
            "devices": [],
            "device_id": "none",
            "fever": False,
            "anomaly_channels": [],
            "anomaly_count": 0,
            "visibility": [],
            "summary": {},
            "hourly": {},
        }

    fever_flags = [bool(dr.get("fever", False)) for dr in device_results]
    if fusion.fever == "all":
        agg_fever = bool(fever_flags) and all(fever_flags)
    elif fusion.fever == "majority":
        agg_fever = sum(fever_flags) > len(fever_flags) / 2
    else:
        agg_fever = any(fever_flags)

    channel_sets = [
        set(dr.get("anomaly_channels", []))
        for dr in device_results
        if isinstance(dr.get("anomaly_channels"), list)
    ]
    if fusion.anomaly_channels == "intersection" and channel_sets:
        agg_channels = sorted(set.intersection(*channel_sets)) if channel_sets else []
    else:
        agg_channels: list[str] = []
        for ch_set in channel_sets:
            for ch in ch_set:
                if ch not in agg_channels:
                    agg_channels.append(ch)

    merged_summary: dict[str, dict[str, Any]] = {}
    for dr in device_results:
        for ch, ch_data in dr.get("summary", {}).items():
            if ch not in merged_summary:
                merged_summary[ch] = dict(ch_data)
            else:
                existing_z = merged_summary[ch].get("z_score", 0.0) or 0.0
                new_z = ch_data.get("z_score", 0.0) or 0.0
                existing_anomaly = merged_summary[ch].get("anomaly", False)
                new_anomaly = ch_data.get("anomaly", False)
                if (new_anomaly and not existing_anomaly) or (
                    new_anomaly == existing_anomaly and new_z > existing_z
                ):
                    merged_summary[ch] = dict(ch_data)

    visibility_list = []
    for dr in device_results:
        vis = dr.get("visibility")
        if isinstance(vis, list):
            visibility_list.extend(vis)
        elif vis is not None:
            visibility_list.append(vis)

    return {
        "devices": device_results,
        "device_id": device_results[0].get("device_id", "none"),
        "fever": agg_fever,
        "anomaly_channels": agg_channels,
        "anomaly_count": len(agg_channels),
        "visibility": visibility_list,
        "summary": merged_summary,
        "hourly": device_results[0].get("hourly", {}) if device_results else {},
    }
