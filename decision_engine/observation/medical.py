"""Medical officer partial observation view."""

from __future__ import annotations

from typing import Any

from decision_engine.context import EpochDecisionContext
from decision_engine.intelligence import briefing_for_epoch


def build_medical_observation(
    epoch: int,
    epoch_snapshot: dict[str, Any],
    decision_ctx: EpochDecisionContext,
    global_health_timeline: dict[str, Any],
) -> dict[str, Any]:
    rp = epoch_snapshot.get("reactive_protocols", {})
    return {
        "role": "medical_officer",
        "epoch": epoch,
        "trigger_status": epoch_snapshot.get("trigger_status"),
        "observation_engine": epoch_snapshot.get("observation_engine", {}),
        "stoplights": rp.get("stoplights", {}),
        "active_protocols": rp.get("active_protocols", []),
        "sop_events": rp.get("sop_events", []),
        "command_directives": list(decision_ctx.command_directives),
        "global_health": briefing_for_epoch(global_health_timeline, epoch),
        "summary": epoch_snapshot.get("summary", {}),
        "infection_counters": epoch_snapshot.get("infection_counters", {}),
    }
