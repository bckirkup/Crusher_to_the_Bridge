"""INFO-SUPPRESS-V1: suppression keyed on the outbreak becoming KNOWN.

A response channel parallel to the scheduled-SOP machinery: the info
state latches when the escalation trigger status reaches the declared
level (plus an optional declared response delay) and stays latched for
the rest of the voyage. Model-default OFF -- a run opts in by declaring
``info_suppression`` in its config overrides.

Three declared sub-channels:

- ``self_isolation``: scope agents are offered voluntary confinement
  each epoch while latched, governed by the shipped FRED sticky
  compliance classes. A declined offer leaves no refuser mark --
  declining voluntary isolation is not refusing a confinement order,
  so the symptomatic path keeps working on non-participants.
- ``closed_zones``: venue cancellation, one-shot at latch -- the
  venue leaves the engine's dining/leisure catalogs and every
  assigned agent's fixed ``dining_zone``/``free_zone`` re-points home.
  Not the per-epoch relocation sweep SOP-009 uses; cancelled venues
  do not reopen.
- ``route_scalars``: transmission channel scalars multiplied while
  latched (the crew-service-change lever), composed multiplicatively
  with whatever the epoch's protocol modifiers already applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from orchestrator_types import STATUS_RANK

_CHANNEL_SCALARS: frozenset[str] = frozenset({
    "direct_contact_scalar",
    "droplet_scalar",
    "hvac_airborne_scalar",
    "fomite_scalar",
})

_SCOPE_ROLES: dict[str, str] = {
    "passengers": "passenger",
    "crew": "crew",
    "all": "all",
}


@dataclass(frozen=True)
class InfoSuppressionSpec:
    """Resolved ``info_suppression`` config block."""

    enabled: bool = False
    trigger_status: str = "suspected"
    self_isolation_scope: str | None = None
    closed_zones: tuple[str, ...] = ()
    route_scalars: dict[str, float] = field(default_factory=dict)
    response_delay_epochs: int = 0

    @property
    def trigger_rank(self) -> int:
        return STATUS_RANK[self.trigger_status.upper()]

    @property
    def scope_role(self) -> str | None:
        """The ``role`` value the self-isolation scope admits, or None."""
        if self.self_isolation_scope is None:
            return None
        return _SCOPE_ROLES[self.self_isolation_scope]

    @classmethod
    def from_config(
        cls,
        raw: Mapping[str, Any] | None,
        *,
        hours_per_epoch: float = 1.0,
    ) -> "InfoSuppressionSpec":
        """Resolve the declared block; ``enabled: false``/absent is inert."""
        if not raw:
            return cls()
        if not raw.get("enabled", False):
            return cls()
        trigger = str(raw.get("trigger_status", "suspected")).lower()
        if trigger.upper() not in STATUS_RANK:
            raise ValueError(
                f"info_suppression.trigger_status {trigger!r} is not an "
                f"escalation status {sorted(STATUS_RANK)}"
            )
        scope = raw.get("self_isolation_scope")
        if scope is not None:
            scope = str(scope).lower()
            if scope not in _SCOPE_ROLES:
                raise ValueError(
                    f"info_suppression.self_isolation_scope {scope!r} not in "
                    f"{sorted(_SCOPE_ROLES)}"
                )
        scalars: dict[str, float] = {}
        for key, val in (raw.get("route_scalars") or {}).items():
            if key not in _CHANNEL_SCALARS:
                raise ValueError(
                    f"info_suppression.route_scalars key {key!r} not in "
                    f"{sorted(_CHANNEL_SCALARS)}"
                )
            scalar = float(val)
            if not 0.0 < scalar <= 1.0:
                raise ValueError(
                    f"info_suppression.route_scalars.{key}={scalar} outside (0,1]"
                )
            scalars[key] = scalar
        delay_hours = float(raw.get("response_delay_hours") or 0.0)
        if delay_hours < 0.0:
            raise ValueError(
                "info_suppression.response_delay_hours must be >= 0"
            )
        return cls(
            enabled=True,
            trigger_status=trigger,
            self_isolation_scope=scope,
            closed_zones=tuple(str(z) for z in (raw.get("closed_zones") or ())),
            route_scalars=scalars,
            response_delay_epochs=int(round(delay_hours / hours_per_epoch)),
        )
