"""Filter protocol activation by command authorization (Law 1 safe)."""

from __future__ import annotations

from typing import Any


def eligible_protocol_ids(standing_protocols: list[Any], stoplights: dict) -> list[str]:
    return [
        p.protocol_id
        for p in standing_protocols
        if p.is_triggered(stoplights)
    ]


def filter_active_modifiers(
    active_mods: list[dict[str, Any]],
    authorized_sop_ids: list[str] | None,
) -> list[dict[str, Any]]:
    if authorized_sop_ids is None:
        return active_mods
    allowed = set(authorized_sop_ids)
    return [m for m in active_mods if m.get("protocol_id") in allowed]
