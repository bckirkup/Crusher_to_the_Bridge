"""Commanding officer partial observation view."""

from __future__ import annotations

from typing import Any

from decision_engine.information.reputation import ReputationTracker


def build_command_observation(
    epoch: int,
    epoch_snapshot: dict[str, Any],
    reputation: ReputationTracker,
    all_protocol_ids: list[str],
    stoplight_eligible_sop_ids: list[str],
    economics_weights: dict[str, Any],
) -> dict[str, Any]:
    rp = epoch_snapshot.get("reactive_protocols", {})
    cost = epoch_snapshot.get("cost_accounting", {})
    return {
        "role": "commanding_officer",
        "epoch": epoch,
        "trigger_status": epoch_snapshot.get("trigger_status"),
        "summary": epoch_snapshot.get("summary", {}),
        "multi_pathogen": epoch_snapshot.get("multi_pathogen", {}),
        "infection_counters": epoch_snapshot.get("infection_counters", {}),
        "cost_accounting": cost,
        "economics_weights": economics_weights,
        "reputation": reputation.to_dict(),
        "stoplights": rp.get("stoplights", {}),
        "all_protocol_ids": all_protocol_ids,
        "stoplight_eligible_sop_ids": stoplight_eligible_sop_ids,
    }
