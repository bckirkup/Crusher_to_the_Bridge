"""
Apply strategic decision actions to ship simulation state.

Maps decision_engine ActionEnvelope entries to existing orchestrator hooks.
"""

from __future__ import annotations

from typing import Any

from decision_engine.actions import ActionEnvelope
from decision_engine.context import EpochDecisionContext
from orchestrator_types import SimulationState


def apply_action_envelope(
    envelope: ActionEnvelope | None,
    state: SimulationState,
    cfg: dict[str, Any],
    decision_ctx: EpochDecisionContext | None = None,
) -> dict[str, Any]:
    """Merge envelope into epoch-local overrides. Returns applied-action log."""
    if envelope is None or not envelope.actions:
        return {}

    applied: dict[str, Any] = {"by_actor": {}}
    overrides = cfg.setdefault("_picard_epoch_overrides", {})
    ctx = decision_ctx

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
            elif kind == "set_isolation_posture":
                factor = action.get("threshold_scale", 1.0)
                overrides["isolation_threshold_scale"] = float(factor)
                actor_log.append(kind)
            elif kind == "noop":
                actor_log.append("noop")
            elif kind == "authorize_sop_subset" and ctx is not None:
                ids = action.get("protocol_ids")
                if isinstance(ids, list):
                    ctx.authorized_sop_ids = [str(x) for x in ids]
                actor_log.append(kind)
            elif kind == "directive_to_medical" and ctx is not None:
                ctx.command_directives.append(action.get("directive", action))
                actor_log.append(kind)
            elif kind == "corporate_communication_stance" and ctx is not None:
                ctx.corporate_communication_stance = float(action.get("stance", 0.0))
                actor_log.append(kind)
            elif kind == "issue_crew_instruction" and ctx is not None:
                msg = action.get("message", "")
                if msg:
                    ctx.sop_announcements.append(msg)
                actor_log.append(kind)
            elif kind == "recommend_sop":
                actor_log.append(f"recommend:{action.get('protocol_id', '')}")
            elif kind == "request_sop_activation":
                actor_log.append(f"request:{action.get('protocol_id', '')}")
        if actor_log:
            applied["by_actor"][str(actor_id)] = actor_log

    return applied
