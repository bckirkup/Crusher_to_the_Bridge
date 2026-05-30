"""
Apply strategic decision actions to ship simulation state.

Maps decision_engine ActionEnvelope entries to existing orchestrator hooks.
"""

from __future__ import annotations

from typing import Any

from decision_engine.actions import ActionEnvelope
from orchestrator_types import SimulationState


def apply_action_envelope(
    envelope: ActionEnvelope | None,
    state: SimulationState,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Merge envelope into epoch-local overrides. Returns applied-action log."""
    if envelope is None or not envelope.actions:
        return {}

    applied: dict[str, Any] = {"by_actor": {}}
    overrides = cfg.setdefault("_picard_epoch_overrides", {})

    for actor_id, actions in envelope.actions.items():
        actor_log: list[str] = []
        for action in actions:
            kind = action.get("kind", "")
            if kind == "set_surveillance_cadence":
                pcr = action.get("pcr_cadence")
                seq = action.get("sequencing_cadence")
                if pcr is not None:
                    overrides["pcr_cadence"] = int(pcr)
                if seq is not None:
                    overrides["sequencing_cadence"] = int(seq)
                actor_log.append(kind)
            elif kind == "noop":
                actor_log.append("noop")
        if actor_log:
            applied["by_actor"][str(actor_id)] = actor_log

    return applied
