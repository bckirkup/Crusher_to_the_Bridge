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
    {"signal": "infection_score", "operator": ">", "value": 1.5},
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


def _compare_numeric(
    actual: float,
    op: str,
    threshold: float,
    *,
    signal: str,
) -> bool:
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
    raise ValueError(f"unsupported {signal} operator: {op}")


def _eval_numeric_fusion_rule(
    agent_data: dict[str, Any],
    rule: dict[str, Any],
    *,
    signal: str,
    field: str,
    default: int | float,
    cast: type,
) -> bool:
    actual = cast(agent_data.get(field, default))
    op = str(rule.get("operator", ">=" if signal == "anomaly_count" else ">"))
    expected = rule.get("value", default)
    if not isinstance(expected, (int, float)):
        raise ValueError(f"{signal} rule value must be numeric")
    return _compare_numeric(actual, op, cast(expected), signal=signal)


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
        return _eval_numeric_fusion_rule(
            agent_data, rule, signal="anomaly_count",
            field="anomaly_count", default=0, cast=int,
        )

    if signal == "infection_score":
        return _eval_numeric_fusion_rule(
            agent_data, rule, signal="infection_score",
            field="infection_score", default=0.0, cast=float,
        )

    if signal == "anomaly_channels":
        channels = agent_data.get("anomaly_channels", [])
        count = len(channels) if isinstance(channels, list) else 0
        op = str(rule.get("operator", ">="))
        expected = int(rule.get("value", 1))
        return _compare_numeric(count, op, expected, signal="anomaly_channels")

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


def _empty_fused_device_report() -> dict[str, Any]:
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


def _aggregate_fever(
    fever_flags: list[bool],
    fusion: WearableDeviceFusionConfig,
) -> bool:
    if fusion.fever == "all":
        return bool(fever_flags) and all(fever_flags)
    if fusion.fever == "majority":
        return sum(fever_flags) > len(fever_flags) / 2
    return any(fever_flags)


def _aggregate_anomaly_channels(
    device_results: list[dict[str, Any]],
    fusion: WearableDeviceFusionConfig,
) -> list[str]:
    channel_sets = [
        set(dr.get("anomaly_channels", []))
        for dr in device_results
        if isinstance(dr.get("anomaly_channels"), list)
    ]
    if fusion.anomaly_channels == "intersection" and channel_sets:
        return sorted(set.intersection(*channel_sets)) if channel_sets else []
    agg_channels: list[str] = []
    for ch_set in channel_sets:
        for ch in ch_set:
            if ch not in agg_channels:
                agg_channels.append(ch)
    return agg_channels


def _merge_device_summaries(
    device_results: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged_summary: dict[str, dict[str, Any]] = {}
    for dr in device_results:
        for ch, ch_data in dr.get("summary", {}).items():
            if ch not in merged_summary:
                merged_summary[ch] = dict(ch_data)
                continue
            existing_z = merged_summary[ch].get("z_score", 0.0) or 0.0
            new_z = ch_data.get("z_score", 0.0) or 0.0
            existing_anomaly = merged_summary[ch].get("anomaly", False)
            new_anomaly = ch_data.get("anomaly", False)
            if (new_anomaly and not existing_anomaly) or (
                new_anomaly == existing_anomaly and new_z > existing_z
            ):
                merged_summary[ch] = dict(ch_data)
    return merged_summary


def _collect_device_visibility(
    device_results: list[dict[str, Any]],
) -> list[Any]:
    visibility_list: list[Any] = []
    for dr in device_results:
        vis = dr.get("visibility")
        if isinstance(vis, list):
            visibility_list.extend(vis)
        elif vis is not None:
            visibility_list.append(vis)
    return visibility_list


def fuse_device_results(
    device_results: list[dict[str, Any]],
    fusion: WearableDeviceFusionConfig,
) -> dict[str, Any]:
    """Fuse per-device wearable epoch payloads into one agent-level report."""
    if not device_results:
        return _empty_fused_device_report()

    fever_flags = [bool(dr.get("fever", False)) for dr in device_results]
    agg_channels = _aggregate_anomaly_channels(device_results, fusion)

    return {
        "devices": device_results,
        "device_id": device_results[0].get("device_id", "none"),
        "fever": _aggregate_fever(fever_flags, fusion),
        "anomaly_channels": agg_channels,
        "anomaly_count": len(agg_channels),
        "visibility": _collect_device_visibility(device_results),
        "summary": _merge_device_summaries(device_results),
        "hourly": device_results[0].get("hourly", {}) if device_results else {},
    }
