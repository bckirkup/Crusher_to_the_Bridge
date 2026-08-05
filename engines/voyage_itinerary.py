"""
voyage_itinerary.py — Cruise voyage day-type / port-visit layer.

Config lives in ``data/platforms/<id>/voyage_config.json``. Engine effects
(ashore marking, contact/dining multipliers, embarkation surge) apply only
when ``voyage.effects_enabled`` is true. Shore infection probability is
parsed for forward compatibility but never introduces pathogens (v1 stub).
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any

DAY_TYPES = frozenset({"sea_day", "port_day", "embarkation", "disembarkation"})

IDENTITY_DINING: dict[str, float] = {
    "breakfast": 1.0,
    "lunch": 1.0,
    "dinner": 1.0,
}

DEFAULT_DAY_DEFAULTS: dict[str, dict[str, Any]] = {
    "sea_day": {
        "onboard_passenger_fraction": 1.0,
        "contact_rate_multiplier": 1.0,
        "dining_demand_multiplier": 1.0,
    },
    "port_day": {
        "onboard_passenger_fraction": 0.30,
        "contact_rate_multiplier": 0.40,
        "dining_demand_multiplier": {
            "breakfast": 0.80,
            "lunch": 0.30,
            "dinner": 0.90,
        },
    },
    "embarkation": {
        "onboard_passenger_fraction": 1.0,
        "contact_rate_multiplier": 1.2,
        "dining_demand_multiplier": 1.0,
        "embarkation_buffet_surge": True,
    },
    "disembarkation": {
        "onboard_passenger_fraction": 0.0,
        "contact_rate_multiplier": 0.2,
        "dining_demand_multiplier": {
            "breakfast": 0.5,
            "lunch": 0.1,
            "dinner": 0.1,
        },
    },
}

EMPTY_VOYAGE_CONFIG: dict[str, Any] = {
    "voyage": {
        "effects_enabled": False,
        "total_epochs": 24,
        "epoch_duration_hours": 1,
        "itinerary": [],
        "defaults": copy.deepcopy(DEFAULT_DAY_DEFAULTS),
    },
}


@dataclass
class EpochState:
    """Per-epoch voyage / port-visit state resolved from itinerary config."""

    day_type: str = "sea_day"
    voyage_day: int = 1
    epoch_of_day: int = 0
    onboard_fraction: float = 1.0
    contact_multiplier: float = 1.0
    dining_multiplier: dict[str, float] = field(
        default_factory=lambda: dict(IDENTITY_DINING),
    )
    port: str = ""
    effects_active: bool = False
    in_embarkation_window: bool = False
    in_disembark_window: bool = False
    in_reembark_window: bool = False
    between_ashore_windows: bool = False
    buffet_surge_fraction: float = 0.0
    disembark_fraction: float = 0.0
    shore_infection_probability: float = 0.0
    notes: str = ""

    def to_telemetry(self) -> dict[str, Any]:
        """Compact history blob."""
        return {
            "day_type": self.day_type,
            "voyage_day": self.voyage_day,
            "epoch_of_day": self.epoch_of_day,
            "onboard_fraction": self.onboard_fraction,
            "contact_multiplier": self.contact_multiplier,
            "dining_multiplier": dict(self.dining_multiplier),
            "port": self.port,
            "effects_active": self.effects_active,
            "in_embarkation_window": self.in_embarkation_window,
            "in_disembark_window": self.in_disembark_window,
            "in_reembark_window": self.in_reembark_window,
            "between_ashore_windows": self.between_ashore_windows,
            "buffet_surge_fraction": self.buffet_surge_fraction,
            "disembark_fraction": self.disembark_fraction,
            "shore_infection_probability": self.shore_infection_probability,
        }


def identity_epoch_state(*, voyage_day: int = 1, epoch_of_day: int = 0) -> EpochState:
    """All-sea-day no-op state (effects off or empty itinerary)."""
    return EpochState(
        day_type="sea_day",
        voyage_day=voyage_day,
        epoch_of_day=epoch_of_day,
        onboard_fraction=1.0,
        contact_multiplier=1.0,
        dining_multiplier=dict(IDENTITY_DINING),
        effects_active=False,
    )


def deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overlay onto a deep copy of base."""
    out = copy.deepcopy(base)
    for key, value in overlay.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = deep_merge_dict(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_voyage_config(path: str | None) -> dict[str, Any]:
    """Load voyage config JSON, or return empty identity config if missing."""
    if not path or not os.path.isfile(path):
        return copy.deepcopy(EMPTY_VOYAGE_CONFIG)
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"voyage_config must be an object: {path}")
    return normalize_voyage_config(raw)


def normalize_voyage_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Fill defaults; validate day types lightly."""
    cfg = deep_merge_dict(EMPTY_VOYAGE_CONFIG, raw)
    voyage = cfg.setdefault("voyage", {})
    voyage.setdefault("effects_enabled", False)
    voyage.setdefault("epoch_duration_hours", 1)
    voyage.setdefault("itinerary", [])
    defaults = voyage.setdefault("defaults", {})
    for day_type, day_def in DEFAULT_DAY_DEFAULTS.items():
        defaults[day_type] = deep_merge_dict(day_def, defaults.get(day_type) or {})
    for day in voyage.get("itinerary") or []:
        dtype = str(day.get("type", ""))
        if dtype not in DAY_TYPES:
            raise ValueError(f"Unknown itinerary day type: {dtype!r}")
    return cfg


def voyage_config_path_for_platform(repo_root: str, platform_id: str) -> str:
    """Canonical path for a platform voyage_config.json."""
    return os.path.join(
        repo_root, "data", "platforms", platform_id, "voyage_config.json",
    )


def merge_voyage_overrides(
    platform_cfg: dict[str, Any],
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Deep-merge Picard ``config_overrides.voyage`` (or full voyage doc)."""
    if not overrides:
        return platform_cfg
    # Allow either {effects_enabled, itinerary, ...} or full {voyage: {...}, dining...}
    if (
        "voyage" in overrides
        or "dining_meal_weights" in overrides
        or "medical_response" in overrides
    ):
        return deep_merge_dict(platform_cfg, overrides)
    return deep_merge_dict(platform_cfg, {"voyage": overrides})


def _normalize_dining_multiplier(raw: Any) -> dict[str, float]:
    if isinstance(raw, dict):
        out = dict(IDENTITY_DINING)
        for meal, val in raw.items():
            out[str(meal)] = float(val)
        return out
    if raw is None:
        return dict(IDENTITY_DINING)
    scalar = float(raw)
    return {k: scalar for k in IDENTITY_DINING}


def _in_window(epoch_of_day: int, window: list[int] | tuple[int, ...] | None) -> bool:
    if not window or len(window) < 2:
        return False
    start, end = int(window[0]), int(window[1])
    lo, hi = (start, end) if start <= end else (end, start)
    return lo <= epoch_of_day <= hi


def _day_entry_for(
    itinerary: list[dict[str, Any]],
    voyage_day: int,
) -> dict[str, Any] | None:
    for day in itinerary:
        if int(day.get("day", -1)) == voyage_day:
            return day
    return None


def resolve_epoch_state(
    config: dict[str, Any] | None,
    epoch: int,
    *,
    epoch_duration_hours: float | None = None,
) -> EpochState:
    """Map a 1-indexed simulation epoch to voyage ``EpochState``.

    When ``effects_enabled`` is false or the itinerary is empty, returns an
    identity sea-day state (``effects_active=False``).
    """
    cfg = normalize_voyage_config(config or {})
    voyage = cfg.get("voyage") or {}
    hours = float(
        epoch_duration_hours
        if epoch_duration_hours is not None
        else voyage.get("epoch_duration_hours", 1) or 1,
    )
    if hours <= 0:
        hours = 1.0
    epochs_per_day = max(1, int(round(24.0 / hours)))
    ep = max(1, int(epoch))
    voyage_day = (ep - 1) // epochs_per_day + 1
    epoch_of_day = (ep - 1) % epochs_per_day

    effects_enabled = bool(voyage.get("effects_enabled", False))
    itinerary = list(voyage.get("itinerary") or [])
    if not effects_enabled or not itinerary:
        return identity_epoch_state(
            voyage_day=voyage_day,
            epoch_of_day=epoch_of_day,
        )

    day_entry = _day_entry_for(itinerary, voyage_day)
    if day_entry is None:
        # Past / before configured days → treat as sea day with effects on
        day_type = "sea_day"
        day_entry = {"day": voyage_day, "type": "sea_day"}
    else:
        day_type = str(day_entry.get("type", "sea_day"))

    defaults = (voyage.get("defaults") or {}).get(day_type) or DEFAULT_DAY_DEFAULTS.get(
        day_type, DEFAULT_DAY_DEFAULTS["sea_day"],
    )
    dining = _normalize_dining_multiplier(defaults.get("dining_demand_multiplier", 1.0))
    contact = float(defaults.get("contact_rate_multiplier", 1.0))
    onboard = float(defaults.get("onboard_passenger_fraction", 1.0))

    in_embark = _in_window(epoch_of_day, day_entry.get("embarkation_window_epochs"))
    in_disembark = _in_window(epoch_of_day, day_entry.get("disembark_window_epochs"))
    in_reembark = _in_window(epoch_of_day, day_entry.get("reembark_window_epochs"))

    between_ashore = False
    if day_type == "port_day":
        d_win = day_entry.get("disembark_window_epochs") or []
        r_win = day_entry.get("reembark_window_epochs") or []
        if len(d_win) >= 2 and len(r_win) >= 2:
            d_end = max(int(d_win[0]), int(d_win[1]))
            r_start = min(int(r_win[0]), int(r_win[1]))
            between_ashore = d_end < epoch_of_day < r_start

    buffet_surge = 0.0
    if day_type == "embarkation" and in_embark:
        buffet_surge = float(day_entry.get("buffet_surge_fraction", 0.80))
        if defaults.get("embarkation_buffet_surge", True):
            contact = max(contact, float(defaults.get("contact_rate_multiplier", 1.2)))

    disembark_fraction = float(day_entry.get("disembark_fraction", 0.0) or 0.0)
    if day_type == "port_day" and (in_disembark or between_ashore):
        onboard = max(0.0, 1.0 - disembark_fraction)
    elif day_type == "port_day" and in_reembark:
        onboard = 1.0
    elif day_type == "disembarkation" and in_disembark:
        onboard = float(defaults.get("onboard_passenger_fraction", 0.0))

    return EpochState(
        day_type=day_type,
        voyage_day=voyage_day,
        epoch_of_day=epoch_of_day,
        onboard_fraction=onboard,
        contact_multiplier=contact,
        dining_multiplier=dining,
        port=str(day_entry.get("port") or ""),
        effects_active=True,
        in_embarkation_window=in_embark,
        in_disembark_window=in_disembark,
        in_reembark_window=in_reembark,
        between_ashore_windows=between_ashore,
        buffet_surge_fraction=buffet_surge,
        disembark_fraction=disembark_fraction,
        shore_infection_probability=float(
            day_entry.get("shore_infection_probability", 0.0) or 0.0,
        ),
        notes=str(day_entry.get("notes") or ""),
    )


def dining_meal_weights_from_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return dining_meal_weights block if present."""
    if not config:
        return None
    weights = config.get("dining_meal_weights")
    return weights if isinstance(weights, dict) else None


def medical_response_from_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return medical_response block if present."""
    if not config:
        return None
    med = config.get("medical_response")
    return med if isinstance(med, dict) else None


def epoch_state_as_dict(state: EpochState) -> dict[str, Any]:
    """Serialize EpochState (tests / debugging)."""
    return asdict(state)


LOCATION_ASHORE = "Ashore"


def _surge_dining_zone(dining_catalog: list[dict[str, Any]]) -> str | None:
    """Prefer buffet venues; fall back to MDR/casual for expedition."""
    if not dining_catalog:
        return None
    buffet = [e for e in dining_catalog if e.get("service_type") == "buffet"]
    if buffet:
        return str(buffet[0]["name"])
    mdr = [e for e in dining_catalog if e.get("service_type") == "mdr"]
    if mdr:
        return str(mdr[0]["name"])
    return str(dining_catalog[0]["name"])


def apply_ashore_and_embarkation(
    agents: list[Any],
    epoch_state: EpochState,
    *,
    rng: Any,
    dining_catalog: list[dict[str, Any]] | None = None,
) -> None:
    """Mutate passenger ``ashore`` when effects are active.

    Crew never go ashore. ``shore_infection_probability`` is intentionally
    unused (v1 stub — no pathogen introduction).
    """
    del dining_catalog  # reserved for future shore-zone catalogs
    if not epoch_state.effects_active:
        for agent in agents:
            if getattr(agent, "ashore", False):
                agent.ashore = False
        return

    passengers = [a for a in agents if getattr(a, "role", "") == "passenger"]

    if epoch_state.day_type == "disembarkation":
        leave = epoch_state.in_disembark_window or epoch_state.onboard_fraction <= 0.0
        for a in passengers:
            a.ashore = bool(leave)
        return

    if epoch_state.day_type == "port_day":
        if epoch_state.in_reembark_window:
            for a in passengers:
                a.ashore = False
            return
        if epoch_state.in_disembark_window:
            target = int(round(len(passengers) * float(epoch_state.disembark_fraction)))
            currently = [a for a in passengers if getattr(a, "ashore", False)]
            if len(currently) < target:
                candidates = [a for a in passengers if not getattr(a, "ashore", False)]
                need = target - len(currently)
                if candidates and need > 0:
                    chosen = rng.choice(
                        len(candidates),
                        size=min(need, len(candidates)),
                        replace=False,
                    )
                    if not hasattr(chosen, "__iter__"):
                        chosen = [int(chosen)]
                    for i in chosen:
                        candidates[int(i)].ashore = True
            elif len(currently) > target:
                for a in currently[: len(currently) - target]:
                    a.ashore = False
            return
        if epoch_state.between_ashore_windows:
            # Keep sticky ashore flags set during disembark window
            return
        for a in passengers:
            a.ashore = False
        return

    for a in passengers:
        a.ashore = False


def apply_embarkation_surge_locations(
    agents: list[Any],
    epoch_state: EpochState,
    *,
    rng: Any,
    dining_catalog: list[dict[str, Any]] | None = None,
) -> None:
    """Force a fraction of onboard passengers into buffet/casual dining."""
    if not epoch_state.effects_active or not epoch_state.in_embarkation_window:
        return
    frac = float(epoch_state.buffet_surge_fraction or 0.0)
    if frac <= 0.0:
        return
    zone = _surge_dining_zone(dining_catalog or [])
    if not zone:
        return
    passengers = [
        a for a in agents
        if getattr(a, "role", "") == "passenger"
        and not getattr(a, "ashore", False)
    ]
    n = int(round(len(passengers) * frac))
    if n <= 0 or not passengers:
        return
    chosen = rng.choice(len(passengers), size=min(n, len(passengers)), replace=False)
    if not hasattr(chosen, "__iter__"):
        chosen = [int(chosen)]
    for i in chosen:
        passengers[int(i)].current_location = zone
