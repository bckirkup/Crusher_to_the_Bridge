"""
engines.transmission_core
~~~~~~~~~~~~~~~~~~~~~~~~~

Four-pathway transmission model for the Crusher-to-the-Bridge digital twin.

Pathogens navigate the shipboard environment through four distinct,
independent transport pathways, each with its own dose contribution
and contact-tracing signature:

1. **Direct Contact** — stochastic person-to-person transmission when
   an infectious and susceptible agent share the same room node,
   scaled by the room's vicinity density (avgR).

2. **Short-Range Droplet** — immediate aerosolization within the shared
   room.  Large droplets settle quickly; fine aerosols remain suspended
   in the room's airborne mass pool.

3. **Long-Range Airborne (HVAC Drift)** — the py-contam bridge reads
   the suspended aerosol pools and drifts a fraction through ductwork
   to downstream room nodes via ``air_flow_paths.json``.

4. **Fomite Deposition & Surface Touch** — pathogen mass from air and
   direct shedding deposits onto fixed surface pools.  Agents entering
   later have a stochastic probability of picking up surface mass,
   carrying it on their FRED schedule.

Each pathway produces:
- A **dose contribution** to susceptible agents
- A **contact-tracing record** for the surveillance inference hook

The combined dose from all pathways feeds the Korkin Lab dose-response
function: ``P(inf) = 1 - (1 + dose/β)^{-α}``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import (
    ALPHA,
    BETA,
    SURFACE_DEPOSITION_FRACTION,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    infection_probability,
)


# ── Pathway-specific parameters ──────────────────────────────────────────

# Fraction of total shedding that becomes immediate room-level aerosol
DROPLET_AEROSOL_FRACTION = 0.05

# Fraction of room aerosol pool inhaled by an occupant per epoch
AEROSOL_INHALATION_FRACTION = 0.02

# Fraction of surface fomite mass picked up by a touching agent per visit
FOMITE_PICKUP_PROBABILITY = 0.10
FOMITE_TRANSFER_FRACTION = 0.01

# Surface decay rate per epoch (distinct from airborne CONTAM decay)
SURFACE_DECAY_RATE = 0.05

# R0-calibrated contact pool (from Person.java avgR array)
AVG_R_POOL = [1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2]


# ── Data structures ─────────────────────────────────────────────────────

@dataclass
class TransmissionEvent:
    """A single transmission event across any pathway."""
    epoch: int
    pathway: str  # "direct_contact" | "droplet" | "hvac_airborne" | "fomite"
    source_agent_id: int | None
    target_agent_id: int
    zone: str
    dose: float


@dataclass
class ExposureRecord:
    """Per-agent exposure record for the contact-tracing matrix."""
    agent_id: int
    zone: str
    pathway: str
    dose: float
    source_agents: list[int] = field(default_factory=list)
    source_zone: str | None = None


@dataclass
class ContactTracingMatrix:
    """Per-epoch contact-tracing matrix for surveillance inference."""
    epoch: int
    # Pathway 1: Who shared a room with whom
    shared_room_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 2: Short-range droplet exposures within rooms
    droplet_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 3: HVAC downstream — who entered a room receiving air from
    # a room that had a shedding agent
    hvac_downstream_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 4: Fomite trailing — who entered a room after an infectious
    # agent left, contacting contaminated surfaces
    fomite_trailing_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Actual infection events across all pathways
    transmission_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "shared_room_exposures": self.shared_room_exposures,
            "droplet_exposures": self.droplet_exposures,
            "hvac_downstream_exposures": self.hvac_downstream_exposures,
            "fomite_trailing_exposures": self.fomite_trailing_exposures,
            "transmission_events": self.transmission_events,
        }


# ── Four-pathway transmission engine ────────────────────────────────────

class TransmissionCore:
    """Executes all four transmission pathways per epoch.

    Replaces the monolithic zone-colocation model in
    ``infection_dynamics_bridge.py`` with explicit, independently-tracked
    pathways. Each pathway contributes a dose that is summed before
    applying the Korkin Lab dose-response function.

    Supports multi-pathogen concurrent simulation: each pathogen runs
    through all four pathways independently with separate mass pools
    and per-agent susceptibility multipliers.

    Parameters
    ----------
    rng : np.random.Generator
        Shared RNG for reproducibility.
    zone_volumes : dict
        Zone name → volume in m³ (from spatial_layout.json).
    pathogen_profiles : dict, optional
        Pathogen ID → profile dict (from active_profiles.json).
    """

    def __init__(
        self,
        rng: np.random.Generator,
        zone_volumes: dict[str, float] | None = None,
        pathogen_profiles: dict[str, dict] | None = None,
    ) -> None:
        self.rng = rng
        self.zone_volumes = zone_volumes or {}
        self.pathogen_profiles = pathogen_profiles or {}

        # Persistent state: surface fomite pools per zone per pathogen
        # {pathogen_id: {zone: mass}}
        self.surface_pools: dict[str, float] = {}  # aggregate (legacy)
        self.surface_pools_by_pathogen: dict[str, dict[str, float]] = {}

        # Persistent state: airborne aerosol pools per zone per pathogen
        self.aerosol_pools: dict[str, float] = {}  # aggregate (legacy)
        self.aerosol_pools_by_pathogen: dict[str, dict[str, float]] = {}

        # Previous epoch's zone occupancy (for fomite trailing detection)
        self._prev_zone_occupants: dict[str, set[int]] = {}

        # Previous epoch's zone shedders per pathogen
        self._prev_zone_shedders: dict[str, list[int]] = {}
        self._prev_zone_shedders_by_pathogen: dict[str, dict[str, list[int]]] = {}

    def initialize_zones(self, zone_names: list[str]) -> None:
        """Set up pools for all zones."""
        for z in zone_names:
            self.surface_pools.setdefault(z, 0.0)
            self.aerosol_pools.setdefault(z, 0.0)
            self._prev_zone_occupants.setdefault(z, set())
            self._prev_zone_shedders.setdefault(z, [])
        # Initialize per-pathogen pools
        for pid in self.pathogen_profiles:
            self.surface_pools_by_pathogen.setdefault(pid, {})
            self.aerosol_pools_by_pathogen.setdefault(pid, {})
            self._prev_zone_shedders_by_pathogen.setdefault(pid, {})
            for z in zone_names:
                self.surface_pools_by_pathogen[pid].setdefault(z, 0.0)
                self.aerosol_pools_by_pathogen[pid].setdefault(z, 0.0)
                self._prev_zone_shedders_by_pathogen[pid].setdefault(z, [])

    def execute_transmission(
        self,
        epoch: int,
        agents: list[KorkinAgent],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]] | None = None,
        multi_pathogen_mass: dict[str, dict[str, float]] | None = None,
    ) -> tuple[ContactTracingMatrix, list[TransmissionEvent]]:
        """Run all four transmission pathways for one epoch.

        Parameters
        ----------
        epoch : int
            Current epoch number.
        agents : list[KorkinAgent]
            All agents (locations already updated for this epoch).
        zone_pathogen_mass : dict
            Current aggregate airborne pathogen mass per zone.
        hvac_downstream_zones : dict, optional
            Map of zone → list of downstream zones receiving its air.
        multi_pathogen_mass : dict, optional
            Per-pathogen mass pools: {pathogen_id: {zone: mass}}.

        Returns
        -------
        (ContactTracingMatrix, list[TransmissionEvent])
            The tracing matrix and list of actual infections.
        """
        matrix = ContactTracingMatrix(epoch=epoch)
        events: list[TransmissionEvent] = []

        # Build zone occupancy maps
        zone_occupants: dict[str, list[KorkinAgent]] = {}
        for agent in agents:
            loc = agent.current_location
            if loc == "Isolated_In_Quarters":
                continue
            zone_occupants.setdefault(loc, []).append(agent)

        # Per-agent accumulated dose across all pathways (aggregate)
        agent_doses: dict[int, float] = {}
        # Track per-agent per-pathway dose breakdown for attribution
        agent_pathway_doses: dict[int, dict[str, float]] = {}
        # Per-agent per-pathogen dose accumulator
        agent_pathogen_doses: dict[int, dict[str, float]] = {}

        # Determine which pathogens are active this epoch
        active_pathogens = list(self.pathogen_profiles.keys()) if self.pathogen_profiles else ["_default"]

        for pathogen_id in active_pathogens:
            profile = self.pathogen_profiles.get(pathogen_id, {})
            p_mass = (multi_pathogen_mass or {}).get(pathogen_id, zone_pathogen_mass)

            # Per-pathogen per-agent dose this pathogen
            p_agent_doses: dict[int, float] = {}
            p_agent_pw: dict[int, dict[str, float]] = {}

            # ── Pathway 1: Direct Contact ────────────────────────
            self._pathway_direct_contact(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

            # ── Pathway 2: Short-Range Droplet ───────────────────
            self._pathway_droplet(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

            # ── Pathway 3: Long-Range Airborne (HVAC Drift) ──────
            self._pathway_hvac_airborne(
                epoch, zone_occupants, p_mass,
                hvac_downstream_zones or {},
                p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id,
            )

            # ── Pathway 4: Fomite Deposition & Surface Touch ─────
            self._pathway_fomite(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

            # Apply susceptibility multiplier per agent per pathogen
            for aid, dose in p_agent_doses.items():
                agent_obj = next((a for a in agents if a.agent_id == aid), None)
                if agent_obj is not None:
                    mult = agent_obj.susceptibility_multiplier.get(pathogen_id, 1.0)
                    scaled_dose = dose * mult
                else:
                    scaled_dose = dose
                agent_doses[aid] = agent_doses.get(aid, 0.0) + scaled_dose
                apd = agent_pathogen_doses.setdefault(aid, {})
                apd[pathogen_id] = apd.get(pathogen_id, 0.0) + scaled_dose

            # Merge pathway breakdowns
            for aid, pw in p_agent_pw.items():
                merged = agent_pathway_doses.setdefault(aid, {})
                for pw_name, pw_dose in pw.items():
                    key = f"{pw_name}:{pathogen_id}" if pathogen_id != "_default" else pw_name
                    merged[key] = merged.get(key, 0.0) + pw_dose

        # ── Apply combined dose-response per pathogen ───────────────
        for agent in agents:
            for pathogen_id in active_pathogens:
                if agent.is_infected_with(pathogen_id):
                    continue
                if agent.immune:
                    continue
                p_dose = agent_pathogen_doses.get(agent.agent_id, {}).get(pathogen_id, 0.0)
                if p_dose <= 0:
                    continue

                profile = self.pathogen_profiles.get(pathogen_id, {})
                dr = profile.get("dose_response", {})
                p_alpha = dr.get("alpha", ALPHA)
                p_beta = dr.get("beta", BETA)
                inf_prob = 1.0 - math.pow(1.0 + p_dose / p_beta, -p_alpha)

                if self.rng.random() < inf_prob:
                    agent.infect_with_pathogen(pathogen_id, p_dose, epoch)

                    pw_doses = agent_pathway_doses.get(agent.agent_id, {})
                    dominant = max(pw_doses, key=pw_doses.get) if pw_doses else "unknown"
                    event = TransmissionEvent(
                        epoch=epoch,
                        pathway=dominant,
                        source_agent_id=None,
                        target_agent_id=agent.agent_id,
                        zone=agent.current_location,
                        dose=p_dose,
                    )
                    events.append(event)
                    matrix.transmission_events.append({
                        "target_id": agent.agent_id,
                        "zone": agent.current_location,
                        "pathogen_id": pathogen_id,
                        "dominant_pathway": dominant,
                        "total_dose": round(p_dose, 4),
                        "pathway_breakdown": {
                            k: round(v, 4)
                            for k, v in pw_doses.items()
                            if pathogen_id in k or pathogen_id == "_default"
                        },
                    })

        # ── Update persistent state for next epoch ───────────────────
        self._update_surface_pools(zone_occupants)
        self._update_prev_occupancy(zone_occupants)

        return matrix, events

    # ── Pathway 1: Direct Contact ────────────────────────────────────

    def _pathway_direct_contact(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
    ) -> None:
        """Person-to-person transmission via close contact in shared rooms."""
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not shedders or not susceptible:
                continue

            total_shedding = sum(sv for _, sv in shedders)
            shedder_ids = [s.agent_id for s, _ in shedders]
            n_occupants = max(len(occupants), 1)

            for target in susceptible:
                r0_draw = int(self.rng.choice(AVG_R_POOL))
                dose = total_shedding / n_occupants * r0_draw
                agent_doses[target.agent_id] = (
                    agent_doses.get(target.agent_id, 0.0) + dose
                )
                if agent_pathway_doses is not None:
                    pw = agent_pathway_doses.setdefault(target.agent_id, {})
                    pw["direct_contact"] = pw.get("direct_contact", 0.0) + dose

                matrix.shared_room_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "source_ids": shedder_ids,
                    "pathogen_id": pathogen_id,
                    "dose": round(dose, 4),
                    "occupant_count": len(occupants),
                    "r0_draw": r0_draw,
                })

    # ── Pathway 2: Short-Range Droplet ───────────────────────────────

    def _pathway_droplet(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
    ) -> None:
        """Immediate aerosol exposure from shedders in the same room."""
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not shedders or not susceptible:
                continue

            total_aerosol = sum(
                sv * DROPLET_AEROSOL_FRACTION for _, sv in shedders
            )

            self.aerosol_pools[zone_name] = (
                self.aerosol_pools.get(zone_name, 0.0) + total_aerosol
            )

            volume = self.zone_volumes.get(zone_name, 100.0)
            concentration = total_aerosol / max(volume, 1.0)
            shedder_ids = [s.agent_id for s, _ in shedders]

            for target in susceptible:
                dose = concentration * volume * AEROSOL_INHALATION_FRACTION
                agent_doses[target.agent_id] = (
                    agent_doses.get(target.agent_id, 0.0) + dose
                )
                if agent_pathway_doses is not None:
                    pw = agent_pathway_doses.setdefault(target.agent_id, {})
                    pw["droplet"] = pw.get("droplet", 0.0) + dose

                matrix.droplet_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "source_ids": shedder_ids,
                    "pathogen_id": pathogen_id,
                    "dose": round(dose, 4),
                    "aerosol_mass": round(total_aerosol, 4),
                    "concentration_per_m3": round(concentration, 6),
                })

    # ── Pathway 3: Long-Range Airborne (HVAC Drift) ──────────────────

    def _pathway_hvac_airborne(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
    ) -> None:
        """Exposure from airborne pathogen drifted via HVAC from upstream zones."""
        shedding_zones: dict[str, list[int]] = {}
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, None)
            if shedders:
                shedding_zones[zone_name] = [s.agent_id for s, _ in shedders]

        # For each downstream zone receiving HVAC air from a shedding zone
        for source_zone, shedder_ids in shedding_zones.items():
            downstream = hvac_downstream_zones.get(source_zone, [])
            for target_zone in downstream:
                if target_zone == source_zone:
                    continue

                # Pathogen mass in the target zone from CONTAM transport
                mass_in_target = zone_pathogen_mass.get(target_zone, 0.0)
                if mass_in_target <= 0:
                    continue

                volume = self.zone_volumes.get(target_zone, 100.0)
                concentration = mass_in_target / max(volume, 1.0)

                # Susceptible agents in the downstream zone get exposed
                target_occupants = zone_occupants.get(target_zone, [])
                susceptible = self._get_susceptible(target_occupants, pathogen_id)
                if not susceptible:
                    continue

                for target in susceptible:
                    dose = concentration * AEROSOL_INHALATION_FRACTION * volume
                    agent_doses[target.agent_id] = (
                        agent_doses.get(target.agent_id, 0.0) + dose
                    )
                    if agent_pathway_doses is not None:
                        pw = agent_pathway_doses.setdefault(target.agent_id, {})
                        pw["hvac_airborne"] = pw.get("hvac_airborne", 0.0) + dose

                    matrix.hvac_downstream_exposures.append({
                        "target_id": target.agent_id,
                        "target_zone": target_zone,
                        "source_zone": source_zone,
                        "source_agent_ids": shedder_ids,
                        "pathogen_id": pathogen_id,
                        "dose": round(dose, 4),
                        "airborne_mass": round(mass_in_target, 4),
                        "concentration_per_m3": round(concentration, 6),
                    })

    # ── Pathway 4: Fomite Deposition & Surface Touch ─────────────────

    def _pathway_fomite(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
    ) -> None:
        """Surface contamination from shedders; stochastic pickup by later visitors."""
        dep_frac = SURFACE_DEPOSITION_FRACTION
        if profile:
            dep_frac = profile.get("surface_deposition_fraction", dep_frac)

        # a) Deposit new fomite mass from current shedders
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            for agent, sv in shedders:
                deposit = sv * dep_frac
                self.surface_pools[zone_name] = (
                    self.surface_pools.get(zone_name, 0.0) + deposit
                )

        # b) Fomite trailing detection + pickup
        for zone_name, occupants in zone_occupants.items():
            surface_mass = self.surface_pools.get(zone_name, 0.0)
            if surface_mass <= 0:
                continue

            susceptible = self._get_susceptible(occupants, pathogen_id)
            if not susceptible:
                continue

            # Identify trailing: agent was NOT in this zone last epoch
            # but a shedder WAS here last epoch
            prev_shedders = self._prev_zone_shedders.get(zone_name, [])
            prev_occupant_ids = self._prev_zone_occupants.get(zone_name, set())

            for target in susceptible:
                # Stochastic surface touch
                if self.rng.random() > FOMITE_PICKUP_PROBABILITY:
                    continue

                dose = surface_mass * FOMITE_TRANSFER_FRACTION
                agent_doses[target.agent_id] = (
                    agent_doses.get(target.agent_id, 0.0) + dose
                )
                if agent_pathway_doses is not None:
                    pw = agent_pathway_doses.setdefault(target.agent_id, {})
                    pw["fomite"] = pw.get("fomite", 0.0) + dose

                is_trailing = (
                    target.agent_id not in prev_occupant_ids
                    and len(prev_shedders) > 0
                )

                matrix.fomite_trailing_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "surface_mass": round(surface_mass, 4),
                    "dose": round(dose, 4),
                    "is_trailing": is_trailing,
                    "prev_shedder_ids": prev_shedders if is_trailing else [],
                })

    # ── Multi-pathogen shedder/susceptible helpers ─────────────────────

    def _get_shedders(
        self,
        occupants: list[KorkinAgent],
        pathogen_id: str,
        profile: dict | None,
    ) -> list[tuple[KorkinAgent, float]]:
        """Return (agent, shedding_value) for agents shedding this pathogen."""
        result = []
        for a in occupants:
            if pathogen_id == "_default":
                if a.is_infected and a.current_shedding > 0:
                    result.append((a, a.current_shedding))
            else:
                sv = a.get_pathogen_shedding(pathogen_id, profile or {})
                if sv > 0:
                    result.append((a, sv))
        return result

    def _get_susceptible(
        self,
        occupants: list[KorkinAgent],
        pathogen_id: str,
    ) -> list[KorkinAgent]:
        """Return agents susceptible to this specific pathogen."""
        result = []
        for a in occupants:
            if a.immune:
                continue
            if pathogen_id == "_default":
                if a.infection_status == InfectionStatus.SUSCEPTIBLE:
                    result.append(a)
            else:
                if not a.is_infected_with(pathogen_id):
                    result.append(a)
        return result

    # ── State management ─────────────────────────────────────────────

    def _update_surface_pools(
        self, zone_occupants: dict[str, list[KorkinAgent]],
    ) -> None:
        """Apply surface decay after fomite interactions."""
        for zone_name in list(self.surface_pools):
            self.surface_pools[zone_name] *= (1.0 - SURFACE_DECAY_RATE)

    def _update_prev_occupancy(
        self, zone_occupants: dict[str, list[KorkinAgent]],
    ) -> None:
        """Snapshot current occupancy for next epoch's fomite trailing."""
        self._prev_zone_occupants = {}
        self._prev_zone_shedders = {}
        for zone_name, occupants in zone_occupants.items():
            self._prev_zone_occupants[zone_name] = {
                a.agent_id for a in occupants
            }
            self._prev_zone_shedders[zone_name] = [
                a.agent_id for a in occupants
                if a.is_infected and a.current_shedding > 0
            ]


def build_hvac_downstream_map(
    airflow_paths: dict[str, Any],
) -> dict[str, list[str]]:
    """Build a map of zone → downstream zones from air_flow_paths.json.

    A zone B is downstream of zone A if there is any airflow path
    (HVAC recirculation, cross-zone link, or adjacency) from A → B.
    """
    downstream: dict[str, list[str]] = {}

    # From HVAC zones: rooms within the same HVAC zone are all mutually downstream
    for hvac_zone in airflow_paths.get("hvac_zones", []):
        rooms = hvac_zone.get("rooms", [])
        for room in rooms:
            others = [r for r in rooms if r != room]
            downstream.setdefault(room, []).extend(others)

    # From cross-zone links: map HVAC zone → rooms, then add downstream
    zone_rooms: dict[str, list[str]] = {}
    for hvac_zone in airflow_paths.get("hvac_zones", []):
        zone_rooms[hvac_zone["id"]] = hvac_zone.get("rooms", [])

    for link in airflow_paths.get("cross_zone_links", []):
        from_rooms = zone_rooms.get(link["from"], [])
        to_rooms = zone_rooms.get(link["to"], [])
        for fr in from_rooms:
            for tr in to_rooms:
                downstream.setdefault(fr, []).append(tr)

    # From adjacency: direct room-to-room connections
    for adj in airflow_paths.get("adjacency", []):
        downstream.setdefault(adj["from"], []).append(adj["to"])
        downstream.setdefault(adj["to"], []).append(adj["from"])

    # Deduplicate
    for zone in downstream:
        downstream[zone] = list(set(downstream[zone]))

    return downstream
