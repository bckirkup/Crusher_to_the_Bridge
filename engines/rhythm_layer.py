"""SHIP-RHYTHM-02 — schedule-conditioned co-presence layer.

Implements ``docs/rhythm/rhythm_spec.md`` over the transcribed day programs in
``data/rhythm/event_catalogs.json``. At the first epoch of each ship day every
agent is dealt an itinerary: for each catalog event the agent is eligible for,
a Bernoulli draw on ``participation_fraction`` commits it, and committed
events own their occupants for their occupancy window. ``synchronized_end``
events egress their occupants into transit corridors on the epoch containing
the window end — the pour-out front.

``rhythm.enabled: false`` is the labelled baseline: no ``RhythmLayer`` is ever
constructed, no engine branch runs, and the independent per-epoch location
draws stay byte-identical to the pre-layer code. When no flag is configured
the layer is ON for platforms carrying a catalog (the six classes in
``data/rhythm/event_catalogs.json``) and inert everywhere else — naval
platforms and legacy hulls have no catalog and change nothing.

Epoch resolution: the engine epoch is one hour. Sub-epoch event fields
(``egress_front_minutes`` 5–20 min, watch turnovers of 15 min) are resolved
at the epoch containing them — the epoch covering a front is the front epoch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from engines.sim_clock import HOURS as _CLOCK_HOURS
from engines.voyage_itinerary import (
    _match_ashore_target,
    crew_shore_leave_group,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EVENT_CATALOG_PATH = _REPO_ROOT / "data" / "rhythm" / "event_catalogs.json"

MINUTES_PER_DAY = 1440

# Occupancy conflict order (spec §4.1): an agent committed to two overlapping
# events occupies the higher-priority one. port_call ranks above meals because
# being ashore is a full-day state that outranks any onboard claim.
_EVENT_PRIORITY = {
    "port_call": 0,
    "meal_seating": 1,
    "watch_turnover": 2,
    "duty": 2,
    "show_performance": 3,
    "scheduled_activity": 4,
    "queue_event": 5,
    "embarkation_flow": 6,
    "disembarkation_flow": 6,
    "open_venue": 7,
    "cleaning_rotation": 7,
}
_DEFAULT_PRIORITY = 9

# Venue roles that name transit space; the pour-out front and port-call
# depart/return transits occupy these. Declared role spellings across the six
# catalogs plus the cabin-corridor fallback every platform carries as
# ``Cabin_Corridor``-typed zones.
_CORRIDOR_ROLES = (
    "gangway_corridor",
    "piazza_promenade",
    "promenade",
    "reception",
    "corridors",
)
_CORRIDOR_ZONE_TYPE = "Cabin_Corridor"

# Share of a Sleep-token hour the agent spends in its cabin, by clock hour.
# Anchored on the ATUS share-asleep-by-clock-hour profile (Basner et al. 2007,
# Sleep; Davis et al. 2023; Sturm 2019 PCD): near-unity plateau ~01:00–05:00,
# shoulders through ~07:00–09:00, a low nap floor across the day.
# Interval: night plateau [0.85, 1.0]; shoulders declared. Shape: empirical.
# Grade B (time-use survey, analogous setting). Origin: R/Ab.
ASLEEP_IN_CABIN_SHARE = (
    0.78, 0.90, 0.94, 0.96, 0.96, 0.93, 0.78, 0.55,
    0.32, 0.16, 0.09, 0.06, 0.06, 0.05, 0.05, 0.05,
    0.05, 0.05, 0.05, 0.06, 0.08, 0.16, 0.34, 0.58,
)

# Post-prandial emesis coupling (spec §4.5). The multiplier is a per-epoch
# hazard ratio between post-meal and other epochs, applied as a deferral gate
# on pending episodes (inside the window an episode fires; outside it defers
# with probability 1/multiplier). Declared wide — no norovirus-specific
# meal-timing study; gastric-emptying anchors only (Vijayvargiya 2018 OR≈2.0,
# Carbone 2021 ~90 min). Interval [1.0, 3.0], midpoint shipped. Grade ∅lit —
# declared, E-tier candidate.
DEFAULT_POST_PRANDIAL_EMESIS_MULTIPLIER = 2.0
# Interval [30, 120] min declared; ~90 min post-meal nausea elevation
# (Carbone 2021) is the physiological anchor. Grade C.
DEFAULT_POST_PRANDIAL_WINDOW_MINUTES = 90.0
# Share of ashore passengers whose return falls in the last tender /
# all-aboard hour. Interval [0.3, 0.7] declared, midpoint shipped. Grade C.
DEFAULT_PORT_RETURN_FRONT_CONCENTRATION = 0.5

# Crew-served conversion of a cancelled self-service buffet halves throughput:
# declared interpretation of the catalog's ``cancelled_or_crew_served`` effect.
_CREW_SERVED_CAPACITY = 0.5
# ``essential_only`` cleaning under confinement keeps half the passes.
_ESSENTIAL_ONLY_SHARE = 0.5


def _parse_minutes(hhmm: str) -> int:
    """'HH:MM' → minutes into the ship day."""
    hh, mm = str(hhmm).split(":")
    return int(hh) * 60 + int(mm)


@dataclass(frozen=True)
class _Commitment:
    """One agent's commitment to one catalog event occurrence."""

    priority: int
    start_min: int
    end_min: int
    zone: str
    # Catalog identity — which event/occurrence claimed this commitment.
    event_id: str
    event_class: str
    # Minute the occupancy ends for a synchronized egress, else None.
    egress_min: int | None
    corridor_zone: str | None
    is_meal: bool
    # (depart_min, return_min) ashore interval for port_call, else None.
    port_span: tuple[int, int] | None

    def covers(self, hour: int) -> bool:
        lo, hi = hour * 60, hour * 60 + 60
        return self.start_min < hi and self.end_min > lo

    def egress_epoch(self, hour: int) -> bool:
        """This epoch carries the shared-clock egress front."""
        if self.egress_min is None:
            return False
        return hour * 60 < self.egress_min <= hour * 60 + 60


class RhythmLayer:
    """The day-template dealer and per-epoch location resolver for a run.

    Owns an independent RNG stream so that enabling the layer never perturbs
    the engine's baseline draw order — and disabling it is a strict no-op.
    """

    def __init__(
        self,
        catalog: dict[str, Any],
        zones: list[dict[str, Any]],
        *,
        seed: int,
        clock: Any,
        config: dict[str, Any] | None = None,
    ) -> None:
        cfg = dict(config or {})
        self.catalog = catalog
        self.clock = clock
        self.rng = np.random.default_rng(
            np.random.SeedSequence([int(seed) & 0xFFFFFFFF, 0x524859544D])
        )
        self.pp_window_minutes = float(
            cfg.get("post_prandial_window_minutes", DEFAULT_POST_PRANDIAL_WINDOW_MINUTES)
        )
        self.pp_multiplier = float(
            cfg.get("post_prandial_emesis_multiplier", DEFAULT_POST_PRANDIAL_EMESIS_MULTIPLIER)
        )
        self.return_front_concentration = float(
            cfg.get("port_return_front_concentration", DEFAULT_PORT_RETURN_FRONT_CONCENTRATION)
        )
        share = cfg.get("asleep_in_cabin_share")
        self.sleep_share = (
            tuple(float(v) for v in share) if share else ASLEEP_IN_CABIN_SHARE
        )
        if len(self.sleep_share) != 24:
            raise ValueError("rhythm.asleep_in_cabin_share needs 24 hourly shares")
        # Midday residual aboard on port days — the existing voyage-layer
        # ``onboard_passenger_fraction`` (0.30), declared here as the rhythm
        # cap so port-call participation cannot empty the ship.
        self.port_onboard_midday_floor = float(
            cfg.get("port_day_onboard_midday_residual", 0.30)
        )

        self._zone_by_name = {str(z["name"]): z for z in zones}
        self._zone_capacity = {
            str(z["name"]): max(float(z.get("max_occupancy") or 100.0), 1.0)
            for z in zones
        }
        self._type_zones: dict[str, list[str]] = {}
        self._name_index: list[str] = list(self._zone_by_name)
        for z in zones:
            self._type_zones.setdefault(str(z.get("type") or ""), []).append(
                str(z["name"])
            )
        self._corridor_zones = self._resolve_corridor_zones(catalog)

        self.dealt_day: int = 0
        self.day_type: str = ""
        self.embarkation_covered: bool = False
        self.meals_to_cabin: bool = False
        self._commitments: dict[int, list[_Commitment]] = {}
        self._pp_hours: dict[int, set[int]] = {}
        self._sleep_mid: dict[int, int] = {}

    # ── Construction ──────────────────────────────────────────────────

    @classmethod
    def from_platform(
        cls,
        platform_id: str,
        zones: list[dict[str, Any]],
        *,
        seed: int,
        clock: Any,
        config: dict[str, Any] | None,
    ) -> "RhythmLayer | None":
        """The layer for *platform_id*, or None when the run stays baseline.

        Returns None when the flag is off, when no catalog covers the
        platform, when the catalog file is absent, or when the clock is not
        the hourly mode (legacy epoch-per-day has no sub-day windows).
        """
        cfg = dict(config or {})
        if not bool(cfg.get("enabled", True)):
            return None
        # Only the hourly clock exposes the intra-day hours the windows need;
        # a legacy day-per-epoch run stays on the labelled baseline.
        if getattr(clock, "mode", _CLOCK_HOURS) != _CLOCK_HOURS:
            return None
        catalog = cls._catalog_for(platform_id)
        if catalog is None:
            return None
        return cls(catalog, zones, seed=seed, clock=clock, config=cfg)

    @staticmethod
    def _catalog_for(platform_id: str) -> dict[str, Any] | None:
        if not platform_id or not _EVENT_CATALOG_PATH.is_file():
            return None
        doc = json.loads(_EVENT_CATALOG_PATH.read_text())
        for catalog in doc.get("ship_class_catalogs", {}).values():
            if platform_id in catalog.get("platforms", []):
                return catalog
        return None

    def _resolve_corridor_zones(
        self, catalog: dict[str, Any]
    ) -> list[str]:
        """Transit zones fronts drain into: mapped corridor roles first, then
        the Cabin_Corridor-typed zones every platform carries."""
        zones: list[str] = []
        venue_map = catalog.get("venue_map", {})
        for role in _CORRIDOR_ROLES:
            for name in venue_map.get(role, []):
                if name in self._zone_by_name and name not in zones:
                    zones.append(name)
        for name in self._type_zones.get(_CORRIDOR_ZONE_TYPE, []):
            if name not in zones:
                zones.append(name)
        return zones

    def _resolve_venue(self, roles: list[str]) -> list[str]:
        """Event venue zone names for the catalog's venue_roles."""
        names = self._mapped_venues(roles)
        if names:
            return names
        names = self._venues_by_zone_type(roles)
        if names:
            return names
        return self._venues_by_name_token(roles)

    def _mapped_venues(self, roles: list[str]) -> list[str]:
        venue_map = self.catalog.get("venue_map", {})
        names: list[str] = []
        for role in roles:
            for name in venue_map.get(role, []):
                if name in self._zone_by_name and name not in names:
                    names.append(name)
        return names

    def _venues_by_zone_type(self, roles: list[str]) -> list[str]:
        """Fallback for roles a class's venue_map does not declare (e.g.
        mega's cabin_corridor): match on the zone's declared type."""
        names: list[str] = []
        for role in roles:
            normed = role.lower()
            for ztype, zone_names in self._type_zones.items():
                if ztype.lower() == normed:
                    names.extend(n for n in zone_names if n not in names)
        return names

    def _venues_by_name_token(self, roles: list[str]) -> list[str]:
        names: list[str] = []
        for role in roles:
            token = role.lower()
            for name in self._name_index:
                if token in name.lower() and name not in names:
                    names.append(name)
        return names

    # ── Day dealing ───────────────────────────────────────────────────

    def deal_day(
        self,
        agents: list[Any],
        day_type: str,
        sop_names: set[str],
        voyage_day: int,
    ) -> None:
        """Deal every agent's itinerary for one ship day (spec §4.1)."""
        self.dealt_day = voyage_day
        self.day_type = day_type
        self._commitments = {}
        self._pp_hours = {}
        self.meals_to_cabin = False
        self.embarkation_covered = False
        template = self.catalog.get("baseline_day_templates", {}).get(day_type)
        if not template:
            return
        effects = self._active_sop_effects(sop_names)
        events = template.get("events", [])
        self.embarkation_covered = day_type == "embarkation" and any(
            e.get("event_class") == "embarkation_flow" for e in events
        )
        for event in events:
            self._deal_event(event, agents, effects)

    def _active_sop_effects(self, sop_names: set[str]) -> dict[str, str]:
        """The most severe SOP variant whose triggers are active (§4.6)."""
        variants = self.catalog.get("sop_variants", {})
        picked: dict[str, str] = {}
        for variant in variants.values():
            triggers = set(variant.get("trigger_sop_names", []))
            if triggers & sop_names:
                picked = dict(variant.get("effects", {}))
        return picked

    def _eligible(self, event: dict[str, Any], agents: list[Any]) -> list[Any]:
        elig = event.get("eligible", {}) or {}
        role_groups = set(elig.get("role_groups") or [])
        classes = set(elig.get("classes") or [])
        out = []
        for a in agents:
            if role_groups and getattr(a, "role", "") not in role_groups:
                continue
            if classes and getattr(a, "agent_class", "") not in classes:
                continue
            if not role_groups and not classes:
                continue
            out.append(a)
        return out

    def _sop_shape(
        self, event: dict[str, Any], effects: dict[str, str]
    ) -> tuple[float, float, int] | None:
        """(participation, capacity multiplier, occurrences) after the active
        SOP variant's effect on this event — None when it is cancelled or
        delivered to cabins (§4.6)."""
        role_groups = set(
            (event.get("eligible", {}) or {}).get("role_groups") or []
        )
        if "passenger" in role_groups and (
            effects.get("all_passenger_events") == "cancelled"
        ):
            return None
        p = float(event.get("participation_fraction", 0.0))
        effect = self._effect_for(effects, event) or ""
        if effect == "cancelled":
            return None
        if effect == "delivered_to_cabin":
            self.meals_to_cabin = True
            return None
        if effect.startswith("capacity_multiplier"):
            m = float(effect.split()[-1])
            return min(1.0, p * m), m, 1
        if effect.startswith("frequency_multiplier"):
            return p, 1.0, max(1, round(float(effect.split()[-1])))
        if effect in ("cancelled_or_crew_served", "crew_served"):
            return (
                min(1.0, p * _CREW_SERVED_CAPACITY),
                _CREW_SERVED_CAPACITY,
                1,
            )
        if effect == "essential_only":
            return min(1.0, p * _ESSENTIAL_ONLY_SHARE), 1.0, 1
        return p, 1.0, 1

    @staticmethod
    def _event_subtype(event: dict[str, Any]) -> str:
        roles = set(event.get("venue_roles", []))
        for sub in ("buffet", "crew_mess", "mess"):
            if sub in roles:
                return sub
        return ""

    def _effect_for(
        self, effects: dict[str, str], event: dict[str, Any]
    ) -> str | None:
        eclass = str(event.get("event_class", ""))
        subtype = self._event_subtype(event)
        for key in (f"{eclass}@{subtype}" if subtype else "", eclass):
            if key and key in effects:
                return str(effects[key])
        return None

    def _deal_event(
        self,
        event: dict[str, Any],
        agents: list[Any],
        effects: dict[str, str],
    ) -> None:
        eclass = str(event.get("event_class", ""))
        eligible = self._eligible(event, agents)
        if not eligible:
            return
        shaped = self._sop_shape(event, effects)
        if shaped is None:
            return
        p, cap_mult, occurrences = shaped

        zones = self._resolve_venue(list(event.get("venue_roles", [])))
        if not zones:
            return
        capacity = sum(self._zone_capacity[z] for z in zones) * cap_mult

        start = _parse_minutes(event.get("window", ["00:00", "00:00"])[0])
        end = _parse_minutes(event.get("window", ["00:00", "00:00"])[1])
        if end <= start:
            end += MINUTES_PER_DAY
        share = float(event.get("occupancy_share", 1.0))
        egress_mode = str(event.get("egress_mode", "rolling"))
        seatings = self._event_seatings(zones) if eclass == "meal_seating" else 1

        for occurrence in range(occurrences):
            shift = occurrence * int((end - start) / max(occurrences, 1))
            self._deal_occurrence(
                event, eligible, p, capacity, zones,
                start + shift, end + shift,
                share, egress_mode, seatings, eclass,
            )

    def _event_seatings(self, zones: list[str]) -> int:
        """The venue's declared sittings — seating stagger stays delegated to
        the existing ``meal_seatings`` geometry, not re-derived here."""
        best = 1
        for name in zones:
            try:
                best = max(best, int(self._zone_by_name[name].get("meal_seatings") or 1))
            except (TypeError, ValueError):
                continue
        return best

    def _deal_occurrence(
        self,
        event: dict[str, Any],
        eligible: list[Any],
        p: float,
        capacity: float,
        zones: list[str],
        start: int,
        end: int,
        share: float,
        egress_mode: str,
        seatings: int,
        eclass: str,
    ) -> None:
        draws = self.rng.random(len(eligible)) < p
        participants = [a for a, hit in zip(eligible, draws, strict=True) if hit]
        if len(participants) > capacity:
            idx = self.rng.choice(
                len(participants), size=int(capacity), replace=False
            )
            participants = [participants[int(i)] for i in idx]
        if eclass == "port_call":
            participants = self._thin_port_participants(participants, eligible)
        zone_weights = np.array([self._zone_capacity[z] for z in zones])
        zone_weights = zone_weights / zone_weights.sum()
        for agent in participants:
            self._commit_agent(
                agent, event, zones, zone_weights, start, end,
                share, egress_mode, seatings, eclass,
            )

    def _commit_agent(
        self,
        agent: Any,
        event: dict[str, Any],
        zones: list[str],
        zone_weights: np.ndarray,
        start: int,
        end: int,
        share: float,
        egress_mode: str,
        seatings: int,
        eclass: str,
    ) -> None:
        # Meals keep the agent's assigned dining venue when the venue is in
        # the event's set, so the seated-party deal stays coherent.
        zone = getattr(agent, "dining_zone", "") if eclass == "meal_seating" else ""
        if eclass == "watch_turnover":
            zone = getattr(agent, "work_zone", "")
        if zone not in zones:
            zone = str(self.rng.choice(zones, p=zone_weights))
        occ_start, occ_end = self._occupancy_interval(
            agent, start, end, share, egress_mode, seatings, eclass,
        )
        egress_min = occ_end if egress_mode == "synchronized_end" else None
        corridor = self._pick_corridor() if egress_min is not None else None
        port_span = None
        if eclass == "port_call":
            port_span = self._port_span(start, end)
        commitment = _Commitment(
            priority=_EVENT_PRIORITY.get(eclass, _DEFAULT_PRIORITY),
            start_min=occ_start,
            end_min=occ_end,
            zone=zone,
            event_id=str(event.get("event_id", "")),
            event_class=eclass,
            egress_min=egress_min,
            corridor_zone=corridor,
            is_meal=eclass == "meal_seating",
            port_span=port_span,
        )
        self._commitments.setdefault(agent.agent_id, []).append(commitment)
        if eclass == "meal_seating" and port_span is None:
            self._mark_post_prandial(agent.agent_id, occ_end)

    def _occupancy_interval(
        self,
        agent: Any,
        start: int,
        end: int,
        share: float,
        egress_mode: str,
        seatings: int,
        eclass: str,
    ) -> tuple[int, int]:
        length = max(end - start, 1)
        if eclass == "meal_seating" and seatings > 1 and egress_mode == "synchronized_end":
            turn = max(length // seatings, 1)
            seat = int(getattr(agent, "meal_seating", 0)) % seatings
            return start + seat * turn, start + (seat + 1) * turn
        occ_len = max(int(round(length * share)), 1)
        if egress_mode == "synchronized_end":
            return end - occ_len, end
        # rolling / windowed: a uniformly-offset sub-window of the open hours
        slack = max(length - occ_len, 0)
        offset = int(self.rng.integers(0, slack + 1)) if slack else 0
        return start + offset, start + offset + occ_len

    def _port_span(self, start: int, end: int) -> tuple[int, int]:
        """Departure and return minutes inside the port-call window (§4.4)."""
        length = max(end - start, 60)
        stay = max(int(length * self.rng.uniform(0.4, 0.9)), 60)
        depart = start + int(self.rng.integers(0, max(length - stay, 1)))
        depart = min(depart, end - 30)
        ret = depart + stay
        if self.rng.random() < self.return_front_concentration:
            ret = end - int(self.rng.integers(0, 61))  # last tender hour
        ret = min(max(ret, depart + 60), end)
        return depart, ret

    def _thin_port_participants(
        self, participants: list[Any], eligible: list[Any]
    ) -> list[Any]:
        """Hold the midday ashore count under the voyage residual (§4.4): the
        share of the eligible pool ashore at once stays under
        1 - onboard_passenger_fraction."""
        cap = int(round(len(eligible) * (1.0 - self.port_onboard_midday_floor)))
        while len(participants) > cap >= 0:
            drop = int(self.rng.integers(0, len(participants)))
            participants.pop(drop)
        return participants

    def apply_ashore(
        self,
        agents: list[Any],
        epoch_state: Any,
        hour: int,
    ) -> bool:
        """Rhythm-owned port-day ashore marking (§4.4).

        Returns True when the layer owns ashore this epoch — a port day with
        voyage effects on — so the engine skips the legacy fraction-matching
        path for passengers. Crew shore leave keeps the voyage rule either
        way: it is a separate gated stratum, not a passenger effect.
        """
        if not (
            getattr(epoch_state, "effects_active", False)
            and getattr(epoch_state, "day_type", "") == "port_day"
        ):
            return False
        for agent in agents:
            if getattr(agent, "role", "") == "passenger":
                agent.ashore = self.ashore_now(agent.agent_id, hour)
        crew = [a for a in agents if getattr(a, "role", "") == "crew"]
        leaving = crew_shore_leave_group(agents, epoch_state)
        if getattr(epoch_state, "in_disembark_window", False):
            if leaving:
                _match_ashore_target(
                    leaving, epoch_state.crew_shore_leave_fraction, self.rng,
                )
            else:
                for member in crew:
                    member.ashore = False
        elif not getattr(epoch_state, "between_ashore_windows", False):
            for member in crew:
                member.ashore = False
        return True

    def _pick_corridor(self) -> str | None:
        if not self._corridor_zones:
            return None
        weights = np.array([self._zone_capacity[z] for z in self._corridor_zones])
        weights = weights / weights.sum()
        return str(self.rng.choice(self._corridor_zones, p=weights))

    def _mark_post_prandial(self, agent_id: int, occ_end_min: int) -> None:
        """The post-meal hazard window: epochs intersecting
        [meal end, meal end + window)."""
        first = int(occ_end_min // 60)
        last = int((occ_end_min + self.pp_window_minutes - 1) // 60)
        hours = self._pp_hours.setdefault(agent_id, set())
        for h in range(first, last + 1):
            hours.add(h % 24)

    # ── Per-epoch resolution ──────────────────────────────────────────

    def is_post_prandial(self, agent_id: int, hour: int) -> bool:
        return hour in self._pp_hours.get(agent_id, ())

    def ashore_now(self, agent_id: int, hour: int) -> bool:
        """Committed port-call ashore state for this epoch (§4.4)."""
        for c in self._commitments.get(agent_id, ()):
            if c.port_span is None:
                continue
            dep_h = int(c.port_span[0] // 60)
            ret_h = int(c.port_span[1] // 60)
            if dep_h < hour < ret_h:
                return True
        return False

    def location_for(self, agent: Any, hour: int, token: str) -> str | None:
        """The agent's rhythm-owned zone this epoch, or None → token fallback.

        A committed event covering the epoch wins; a synchronized_end egress
        claims the epoch containing the occupancy end. Outside events the
        Sleep token's cabin share is the time-of-day curve, and under the
        confinement SOP variant passenger meals are delivered to cabins.
        """
        entries = self._commitments.get(agent.agent_id)
        if entries:
            covering = [c for c in entries if c.covers(hour)]
            if covering:
                best = min(covering, key=lambda c: (c.priority, c.start_min))
                if best.egress_epoch(hour) and best.corridor_zone is not None:
                    return best.corridor_zone
                return best.zone
        if token == "Sleep":
            share = self._share_for(agent, hour)
            # The baseline resolves every Sleep token to home_zone; the
            # complement of the in-cabin share is the awake minority —
            # they sit in free space, not in the berth block.
            if self.rng.random() < share:
                return agent.home_zone
            return str(getattr(agent, "free_zone", "") or agent.home_zone)
        if (
            self.meals_to_cabin
            and getattr(agent, "role", "") == "passenger"
            and token.startswith("Meal")
        ):
            return agent.home_zone
        return None

    def _share_for(self, agent: Any, hour: int) -> float:
        """In-cabin share at this hour, shifted onto the agent's own sleep
        block — the watch-shifted crew curve of §4.3."""
        mid = self._sleep_mid.get(agent.agent_id)
        if mid is None:
            mid = self._sleep_midpoint(agent)
            self._sleep_mid[agent.agent_id] = mid
        return self.sleep_share[(hour - mid + 3) % 24]

    @staticmethod
    def _sleep_midpoint(agent: Any) -> int:
        """Midpoint hour of the agent's longest contiguous Sleep run."""
        schedule = list(getattr(agent, "schedule", []) or [])
        if not schedule:
            return 3
        doubled = schedule + schedule
        best_start, best_len, cur_start, cur_len = 0, 0, None, 0
        for i, tok in enumerate(doubled):
            if tok == "Sleep" and cur_len == 0:
                cur_start = i
            cur_len = cur_len + 1 if tok == "Sleep" else 0
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start if cur_start is not None else i
        return (best_start + best_len // 2) % 24


def platform_has_rhythm_catalog(platform_id: str) -> bool:
    """Whether *platform_id* is one of the catalogued cruise classes.

    Shared platform gate: mechanisms sourced to the passenger-cruise record
    (SHIP-RHYTHM-02, EXPO-CAP-01) apply to the classes with a catalog and
    leave naval hulls and legacy platforms on the labelled baseline.
    """
    return RhythmLayer._catalog_for(platform_id) is not None
