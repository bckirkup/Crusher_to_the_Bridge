"""
Apply strategic decision actions to ship simulation state.

Maps decision_engine ActionEnvelope entries to existing orchestrator hooks.
"""

from __future__ import annotations

from typing import Any, Callable

from decision_engine.actions import ActionEnvelope
from decision_engine.context import EpochDecisionContext
from orchestrator_types import SimulationState

_ActionHandler = Callable[..., str]


def _protocol_id_from_action(action: dict[str, Any]) -> str:
    return str(action.get("protocol_id") or action.get("sop_id") or "")


def _apply_surveillance_cadence(action: dict[str, Any], overrides: dict[str, Any]) -> None:
    pcr = action.get("pcr_cadence")
    seq = action.get("sequencing_cadence")
    if pcr is not None:
        overrides["pcr_cadence"] = int(pcr)
    if seq is not None:
        overrides["sequencing_cadence"] = int(seq)


def _apply_surveillance_budget_emphasis(action: dict[str, Any], overrides: dict[str, Any]) -> None:
    emphasis = action.get("emphasis", "")
    if emphasis == "pcr":
        overrides["pcr_cadence"] = 1
    elif emphasis == "sequencing":
        overrides["sequencing_cadence"] = 1


def _apply_behavioral_override(
    action: dict[str, Any],
    state: SimulationState,
) -> None:
    aid = action.get("agent_id")
    if aid is not None:
        state.agent_behavioral_overrides[int(aid)] = action.get("kind", "")


def _handle_cadence(action: dict[str, Any], *, overrides: dict[str, Any], **_: Any) -> str:
    _apply_surveillance_cadence(action, overrides)
    return "set_surveillance_cadence"


def _handle_budget(action: dict[str, Any], *, overrides: dict[str, Any], **_: Any) -> str:
    _apply_surveillance_budget_emphasis(action, overrides)
    return "set_surveillance_budget_emphasis"


def _handle_isolation(action: dict[str, Any], *, overrides: dict[str, Any], **_: Any) -> str:
    overrides["isolation_threshold_scale"] = float(action.get("threshold_scale", 1.0))
    return "set_isolation_posture"


def _handle_noop(_action: dict[str, Any], **_: Any) -> str:
    return "noop"


def _handle_authorize(action: dict[str, Any], *, ctx: EpochDecisionContext, **_: Any) -> str:
    ids = action.get("protocol_ids")
    if isinstance(ids, list):
        ctx.authorized_sop_ids = [str(x) for x in ids]
    return "authorize_sop_subset"


def _handle_directive(action: dict[str, Any], *, ctx: EpochDecisionContext, **_: Any) -> str:
    ctx.command_directives.append(action.get("directive", action))
    return "directive_to_medical"


def _handle_stance(action: dict[str, Any], *, ctx: EpochDecisionContext, **_: Any) -> str:
    ctx.corporate_communication_stance = float(action.get("stance", 0.0))
    return "corporate_communication_stance"


def _handle_instruction(action: dict[str, Any], *, ctx: EpochDecisionContext, **_: Any) -> str:
    msg = action.get("message", "")
    if msg:
        ctx.sop_announcements.append(msg)
    return "issue_crew_instruction"


def _handle_activate(action: dict[str, Any], *, state: SimulationState, **_: Any) -> str:
    pid = _protocol_id_from_action(action)
    if pid:
        state.forced_protocol_ids.add(pid)
    return f"activate:{pid}"


def _handle_deactivate(action: dict[str, Any], *, state: SimulationState, **_: Any) -> str:
    pid = _protocol_id_from_action(action)
    if pid:
        state.forced_protocol_ids.discard(pid)
    return f"deactivate:{pid}"


def _handle_verify(
    action: dict[str, Any],
    *,
    state: SimulationState,
    zones_ok: set[str],
    envelope: ActionEnvelope,
    **_: Any,
) -> str:
    zone = str(action.get("zone", ""))
    if zone and (not zones_ok or zone in zones_ok):
        state.verification_test_queue.append({"epoch": envelope.epoch, "zone": zone})
    return f"verify:{zone}"


def _handle_recommend(action: dict[str, Any], *, ctx: EpochDecisionContext, **_: Any) -> str:
    pid = _protocol_id_from_action(action)
    if pid:
        ctx.sop_recommendations.append(pid)
    return f"recommend:{pid}"


def _handle_behavior(action: dict[str, Any], *, state: SimulationState, **_: Any) -> str:
    _apply_behavioral_override(action, state)
    return f"{action.get('kind')}:{action.get('agent_id')}"


_NEEDS_CTX = frozenset(
    {
        "authorize_sop_subset",
        "directive_to_medical",
        "corporate_communication_stance",
        "issue_crew_instruction",
        "recommend_sop",
    },
)

_ACTION_HANDLERS: dict[str, _ActionHandler] = {
    "set_surveillance_cadence": _handle_cadence,
    "set_surveillance_budget_emphasis": _handle_budget,
    "set_isolation_posture": _handle_isolation,
    "noop": _handle_noop,
    "authorize_sop_subset": _handle_authorize,
    "directive_to_medical": _handle_directive,
    "corporate_communication_stance": _handle_stance,
    "issue_crew_instruction": _handle_instruction,
    "activate_sop": _handle_activate,
    "request_sop_activation": _handle_activate,
    "deactivate_sop": _handle_deactivate,
    "order_verification_test": _handle_verify,
    "recommend_sop": _handle_recommend,
    "hide_symptoms": _handle_behavior,
    "report_sick_call": _handle_behavior,
    "refuse_quarantine": _handle_behavior,
}


def _dispatch_action(
    action: dict[str, Any],
    *,
    state: SimulationState,
    overrides: dict[str, Any],
    ctx: EpochDecisionContext | None,
    zones_ok: set[str],
    envelope: ActionEnvelope,
) -> str | None:
    kind = str(action.get("kind") or "")
    handler = _ACTION_HANDLERS.get(kind)
    if handler is None:
        return None
    if kind in _NEEDS_CTX and ctx is None:
        return None
    return handler(
        action,
        state=state,
        overrides=overrides,
        ctx=ctx,
        zones_ok=zones_ok,
        envelope=envelope,
    )


def apply_action_envelope(
    envelope: ActionEnvelope | None,
    state: SimulationState,
    cfg: dict[str, Any],
    decision_ctx: EpochDecisionContext | None = None,
    valid_zones: set[str] | None = None,
) -> dict[str, Any]:
    """Merge envelope into simulation state and epoch-local overrides."""
    if envelope is None or not envelope.actions:
        return {}

    applied: dict[str, Any] = {"by_actor": {}}
    overrides = cfg.setdefault("_picard_epoch_overrides", {})
    zones_ok = valid_zones or set()

    for actor_id, actions in envelope.actions.items():
        actor_log: list[str] = []
        for action in actions:
            label = _dispatch_action(
                action,
                state=state,
                overrides=overrides,
                ctx=decision_ctx,
                zones_ok=zones_ok,
                envelope=envelope,
            )
            if label:
                actor_log.append(label)
        if actor_log:
            applied["by_actor"][str(actor_id)] = actor_log

    return applied
