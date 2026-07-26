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

The combined dose from all pathways feeds the dose-response function:
- **Beta-Poisson**: ``P(inf) = 1 - (1 + dose/β)^{-α}``
- **Exponential**: ``P(inf) = 1 - exp(-k * dose)``
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
    # Pathway 5: Food contamination — ingestion dose from contaminated
    # food in Dining-type zones
    food_contamination_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Pathway 6: Environmental source — dose from HVAC-colonized pathogen
    # (e.g. Legionella biofilm) independent of infected agents
    environmental_exposures: list[dict[str, Any]] = field(default_factory=list)
    # Actual infection events across all pathways
    transmission_events: list[dict[str, Any]] = field(default_factory=list)
    # Epoch x zone occupancy / contact summary (surfaces zone_occupants map)
    zone_contact_summary: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "shared_room_exposures": self.shared_room_exposures,
            "droplet_exposures": self.droplet_exposures,
            "hvac_downstream_exposures": self.hvac_downstream_exposures,
            "fomite_trailing_exposures": self.fomite_trailing_exposures,
            "food_contamination_exposures": self.food_contamination_exposures,
            "environmental_exposures": self.environmental_exposures,
            "transmission_events": self.transmission_events,
            "zone_contact_summary": self.zone_contact_summary,
        }


# ── Four-pathway transmission engine ────────────────────────────────────

# Balcony cabins: outdoor air dilution reduces aerosol exposure (PLATFORM_CABIN_REVISION)
BALCONY_AEROSOL_REDUCTION = 0.5

# Default confinement isolation for quarantined agents in cabin corridors
DEFAULT_CONFINEMENT_ISOLATION_FACTOR = 0.05

# Direct contact between confined agent and non-cabin-mate (closed door)
NON_MATE_CONFINEMENT_CONTACT_FACTOR = 0.01

# Hallway encounter rate vs well-mixed ward (Cabin_Corridor zones)
DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR = 0.15

# Fraction of shedding deposited into food pools in Dining-type zones
FOOD_DEPOSITION_FRACTION = 1e-4

# Fraction of food-pool pathogen ingested per agent per epoch
FOOD_INGESTION_FRACTION = 0.05

# Fraction of environmental load delivered per zone per epoch
ENV_DELIVERY_FRACTION = 0.01


class TransmissionCore:
    """Executes six transmission pathways per epoch.

    Pathways 1–4 are the original four-pathway model.  Pathway 5 (food
    contamination) and pathway 6 (environmental source) extend coverage
    to enteric foodborne and environmentally-colonised pathogens.

    Parameters
    ----------
    rng : np.random.Generator
        Shared RNG for reproducibility.
    zone_volumes : dict
        Zone name → volume in m³ (from spatial_layout.json).
    pathogen_profiles : dict, optional
        Pathogen ID → profile dict (from active_profiles.json).
    zone_types : dict, optional
        Zone name → type string (from spatial_layout.json).
    """

    def __init__(
        self,
        rng: np.random.Generator,
        zone_volumes: dict[str, float] | None = None,
        pathogen_profiles: dict[str, dict] | None = None,
        zone_types: dict[str, str] | None = None,
        zone_ventilation: dict[str, str] | None = None,
        confinement_isolation_factor: float = DEFAULT_CONFINEMENT_ISOLATION_FACTOR,
        corridor_direct_contact_factor: float = DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR,
    ) -> None:
        self.rng = rng
        self.zone_volumes = zone_volumes or {}
        self.pathogen_profiles = pathogen_profiles or {}
        self.zone_types = zone_types or {}
        self.zone_ventilation = zone_ventilation or {}
        self.confinement_isolation_factor = confinement_isolation_factor
        self.corridor_direct_contact_factor = corridor_direct_contact_factor
        self._quarantined_ids: set[int] = set()

        # Persistent state: surface fomite pools per zone per pathogen
        # {pathogen_id: {zone: mass}}
        self.surface_pools: dict[str, float] = {}  # aggregate (legacy)
        self.surface_pools_by_pathogen: dict[str, dict[str, float]] = {}

        # Persistent state: airborne aerosol pools per zone per pathogen
        self.aerosol_pools: dict[str, float] = {}  # aggregate (legacy)
        self.aerosol_pools_by_pathogen: dict[str, dict[str, float]] = {}

        # Pathway 5: food contamination pools per Dining zone per pathogen
        self.food_pools: dict[str, dict[str, float]] = {}

        # Pathway 6: environmental contamination load per pathogen
        self.environmental_load: dict[str, float] = {}

        # Previous epoch's zone occupancy (for fomite trailing detection)
        self._prev_zone_occupants: dict[str, set[int]] = {}

        # Previous epoch's zone shedders per pathogen
        self._prev_zone_shedders: dict[str, list[int]] = {}
        self._prev_zone_shedders_by_pathogen: dict[str, dict[str, list[int]]] = {}

        # Protocol-driven pathway scalars (1.0 = no modification)
        self.direct_contact_scalar: float = 1.0
        self.droplet_scalar: float = 1.0
        self.hvac_airborne_scalar: float = 1.0

    def _aerosol_ventilation_factor(self, zone_name: str) -> float:
        """Outdoor-air dilution for balcony cabin corridors."""
        vent = self.zone_ventilation.get(zone_name, "")
        if vent == "balcony_partial":
            return BALCONY_AEROSOL_REDUCTION
        return 1.0

    def _direct_contact_zone_factor(self, zone_name: str) -> float:
        if self.zone_types.get(zone_name) == "Cabin_Corridor":
            return self.corridor_direct_contact_factor
        return 1.0

    def _is_quarantined(self, agent: KorkinAgent) -> bool:
        return agent.agent_id in self._quarantined_ids

    def _cabin_confinement_active(self, agent: KorkinAgent) -> bool:
        """Cabin-corridor confinement rules apply only in Cabin_Corridor zones."""
        if agent.agent_id not in self._quarantined_ids:
            return False
        return self.zone_types.get(agent.current_location) == "Cabin_Corridor"

    def _confinement_factor(self, agent: KorkinAgent) -> float:
        if self._cabin_confinement_active(agent):
            return self.confinement_isolation_factor
        return 1.0

    def _cabin_pair_contact_factor(
        self, shedder: KorkinAgent, target: KorkinAgent,
    ) -> float:
        """Scale direct-contact dose for cabin-corridor confinement pairs."""
        if self.zone_types.get(target.current_location) != "Cabin_Corridor":
            return 1.0
        confined_target = self._cabin_confinement_active(target)
        confined_shedder = self._cabin_confinement_active(shedder)
        if not confined_target and not confined_shedder:
            return 1.0
        if shedder.agent_id in target.cabin_mate_ids:
            return 1.0
        return NON_MATE_CONFINEMENT_CONTACT_FACTOR

    def initialize_zones(self, zone_names: list[str]) -> None:
        """Set up pools for all zones."""
        for z in zone_names:
            self.surface_pools.setdefault(z, 0.0)
            self.aerosol_pools.setdefault(z, 0.0)
            self._prev_zone_occupants.setdefault(z, set())
            self._prev_zone_shedders.setdefault(z, [])
        # Identify Dining-type zones for food contamination
        dining_zones = [
            z for z in zone_names
            if self.zone_types.get(z, "") == "Dining"
        ]
        # Initialize per-pathogen pools
        for pid, profile in self.pathogen_profiles.items():
            self.surface_pools_by_pathogen.setdefault(pid, {})
            self.aerosol_pools_by_pathogen.setdefault(pid, {})
            self._prev_zone_shedders_by_pathogen.setdefault(pid, {})
            for z in zone_names:
                self.surface_pools_by_pathogen[pid].setdefault(z, 0.0)
                self.aerosol_pools_by_pathogen[pid].setdefault(z, 0.0)
                self._prev_zone_shedders_by_pathogen[pid].setdefault(z, [])
            # Initialize food contamination pools for Dining zones
            fc = profile.get("food_contamination", {})
            if fc.get("enabled", False):
                food_zones = fc.get("food_zones", dining_zones)
                self.food_pools.setdefault(pid, {})
                for fz in food_zones:
                    self.food_pools[pid].setdefault(fz, 0.0)
            # Initialize environmental contamination load
            ec = profile.get("environmental_contamination", {})
            if ec.get("enabled", False):
                self.environmental_load[pid] = ec.get(
                    "baseline_environmental_load", 0.0
                )

    def execute_transmission(
        self,
        epoch: int,
        agents: list[KorkinAgent],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]] | None = None,
        multi_pathogen_mass: dict[str, dict[str, float]] | None = None,
        quarantined_ids: set[int] | None = None,
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
        quarantined_ids : set[int], optional
            Agents confined to quarters; receive reduced direct contact / droplet
            and no fomite pickup in cabin-corridor platforms.

        Returns
        -------
        (ContactTracingMatrix, list[TransmissionEvent])
            The tracing matrix and list of actual infections.
        """
        matrix = ContactTracingMatrix(epoch=epoch)
        events: list[TransmissionEvent] = []
        self._quarantined_ids = set(quarantined_ids or ())

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
            self._execute_pathogen_pathways(
                epoch, agents, zone_occupants, zone_pathogen_mass,
                hvac_downstream_zones, multi_pathogen_mass,
                pathogen_id, agent_doses, agent_pathway_doses, agent_pathogen_doses,
                matrix, events,
            )

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
                model_type = dr.get("model", "beta_poisson")
                if model_type == "exponential":
                    k = dr.get("k", 0.01)
                    inf_prob = 1.0 - math.exp(-k * p_dose)
                else:
                    p_alpha = dr.get("alpha", ALPHA)
                    p_beta = dr.get("beta", BETA)
                    inf_prob = 1.0 - math.pow(1.0 + p_dose / p_beta, -p_alpha)

                if self.rng.random() < inf_prob:
                    profile = self.pathogen_profiles.get(pathogen_id, {})
                    agent.infect_with_pathogen(
                        pathogen_id,
                        p_dose,
                        epoch,
                        rng=self.rng,
                        profile=profile,
                    )

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

        # ── Per-zone contact summary (occupancy map used for doses) ──
        matrix.zone_contact_summary = self._build_zone_contact_summary(
            zone_occupants, matrix, active_pathogens,
        )

        # ── Update persistent state for next epoch ───────────────────
        self._update_surface_pools(zone_occupants)
        self._update_prev_occupancy(zone_occupants)

        return matrix, events

    def _execute_pathogen_pathways(
        self,
        epoch: int,
        agents: list[KorkinAgent],
        zone_occupants: dict[str, list[KorkinAgent]],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]] | None,
        multi_pathogen_mass: dict[str, dict[str, float]] | None,
        pathogen_id: str,
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]],
        agent_pathogen_doses: dict[int, dict[str, float]],
        matrix: ContactTracingMatrix,
        events: list[TransmissionEvent],
    ) -> None:
        profile = self.pathogen_profiles.get(pathogen_id, {})
        p_mass = (multi_pathogen_mass or {}).get(pathogen_id, zone_pathogen_mass)
        p_agent_doses: dict[int, float] = {}
        p_agent_pw: dict[int, dict[str, float]] = {}
        ec = profile.get("environmental_contamination", {})
        person_to_person = ec.get("person_to_person", True)

        if person_to_person:
            self._pathway_direct_contact(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )
            self._pathway_droplet(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

        self._pathway_hvac_airborne(
            epoch, zone_occupants, p_mass,
            hvac_downstream_zones or {},
            p_agent_doses, matrix, events,
            p_agent_pw, pathogen_id=pathogen_id,
        )

        if person_to_person:
            self._pathway_fomite(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

        fc = profile.get("food_contamination", {})
        if fc.get("enabled", False):
            self._pathway_food_contamination(
                epoch, zone_occupants, p_agent_doses, matrix,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

        if ec.get("enabled", False):
            self._pathway_environmental(
                epoch, zone_occupants, p_agent_doses, matrix,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
            )

        for aid, dose in p_agent_doses.items():
            agent_obj = next((a for a in agents if a.agent_id == aid), None)
            mult = (
                agent_obj.susceptibility_multiplier.get(pathogen_id, 1.0)
                if agent_obj is not None else 1.0
            )
            scaled_dose = dose * mult
            agent_doses[aid] = agent_doses.get(aid, 0.0) + scaled_dose
            apd = agent_pathogen_doses.setdefault(aid, {})
            apd[pathogen_id] = apd.get(pathogen_id, 0.0) + scaled_dose

        for aid, pw in p_agent_pw.items():
            merged = agent_pathway_doses.setdefault(aid, {})
            for pw_name, pw_dose in pw.items():
                key = f"{pw_name}:{pathogen_id}" if pathogen_id != "_default" else pw_name
                merged[key] = merged.get(key, 0.0) + pw_dose

    # ── Pathway 1: Direct Contact ────────────────────────────────────

    def _zone_has_cabin_confinement(
        self,
        zone_name: str,
        shedders: list[tuple[KorkinAgent, float]],
        susceptible: list[KorkinAgent],
    ) -> bool:
        if self.zone_types.get(zone_name) != "Cabin_Corridor":
            return False
        if any(self._cabin_confinement_active(s) for s, _ in shedders):
            return True
        return any(self._cabin_confinement_active(t) for t in susceptible)

    def _direct_contact_dose(
        self,
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
        total_shedding: float,
        n_occupants: int,
        r0_draw: int,
        cabin_confinement: bool,
    ) -> float:
        if cabin_confinement:
            dose = 0.0
            for shedder, sv in shedders:
                pair_factor = self._cabin_pair_contact_factor(shedder, target)
                dose += sv * pair_factor / n_occupants * r0_draw
            return dose
        dose = total_shedding / n_occupants * r0_draw
        return dose * self._confinement_factor(target)

    def _pathway_direct_contact(
        self,
        _epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
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
            zone_dc_factor = self._direct_contact_zone_factor(zone_name)
            cabin_confinement = self._zone_has_cabin_confinement(
                zone_name, shedders, susceptible,
            )

            for target in susceptible:
                r0_draw = int(self.rng.choice(AVG_R_POOL))
                dose = self._direct_contact_dose(
                    target, shedders, total_shedding, n_occupants, r0_draw,
                    cabin_confinement,
                )
                dose *= self.direct_contact_scalar
                dose *= zone_dc_factor
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
        _epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
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
            vent_factor = self._aerosol_ventilation_factor(zone_name)

            for target in susceptible:
                dose = concentration * volume * AEROSOL_INHALATION_FRACTION
                dose *= self.droplet_scalar
                dose *= vent_factor
                dose *= self._confinement_factor(target)
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

    def _apply_hvac_downstream_doses(
        self,
        target_zone: str,
        source_zone: str,
        shedder_ids: list[int],
        mass_in_target: float,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
    ) -> None:
        volume = self.zone_volumes.get(target_zone, 100.0)
        concentration = mass_in_target / max(volume, 1.0)
        target_occupants = zone_occupants.get(target_zone, [])
        susceptible = self._get_susceptible(target_occupants, pathogen_id)
        if not susceptible:
            return

        for target in susceptible:
            dose = concentration * AEROSOL_INHALATION_FRACTION * volume
            dose *= self.hvac_airborne_scalar
            dose *= self._aerosol_ventilation_factor(target_zone)
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

    def _pathway_hvac_airborne(
        self,
        _epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        zone_pathogen_mass: dict[str, float],
        hvac_downstream_zones: dict[str, list[str]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
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

                mass_in_target = zone_pathogen_mass.get(target_zone, 0.0)
                if mass_in_target <= 0:
                    continue

                self._apply_hvac_downstream_doses(
                    target_zone, source_zone, shedder_ids, mass_in_target,
                    zone_occupants, agent_doses, matrix,
                    agent_pathway_doses, pathogen_id,
                )

    # ── Pathway 4: Fomite Deposition & Surface Touch ─────────────────

    def _apply_fomite_pickup(
        self,
        target: KorkinAgent,
        zone_name: str,
        surface_mass: float,
        prev_occupant_ids: set[int],
        prev_shedders: list[int],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        pathogen_id: str,
    ) -> None:
        if self._cabin_confinement_active(target):
            return
        if self.rng.random() > FOMITE_PICKUP_PROBABILITY:
            return

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

    def _pathway_fomite(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        _events: list[TransmissionEvent],
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
    ) -> None:
        """Surface contamination from shedders; stochastic pickup by later visitors."""
        dep_frac = SURFACE_DEPOSITION_FRACTION
        if profile:
            dep_frac = profile.get("surface_deposition_fraction", dep_frac)

        # a) Deposit new fomite mass from current shedders (not confined to cabin)
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            for agent, sv in shedders:
                if self._cabin_confinement_active(agent):
                    continue
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
                self._apply_fomite_pickup(
                    target, zone_name, surface_mass,
                    prev_occupant_ids, prev_shedders,
                    agent_doses, matrix, agent_pathway_doses, pathogen_id,
                )

    # ── Pathway 5: Food Contamination ────────────────────────────────

    def _pathway_food_contamination(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
    ) -> None:
        """Food contamination in Dining-type zones.

        Infected agents shedding in a food zone deposit pathogen into a
        persistent food pool.  The pool grows each epoch (bacterial
        reproduction) and decays slowly.  Susceptible agents eating in the
        zone receive an ingestion dose from the pool.
        """
        fc = (profile or {}).get("food_contamination", {})
        if not fc.get("enabled", False):
            return

        food_zones = self.food_pools.get(pathogen_id, {})
        if not food_zones:
            return

        growth = fc.get("growth_rate_per_epoch", 0.0)
        decay = fc.get("decay_rate_per_epoch", 0.1)

        for zone_name in food_zones:
            occupants = zone_occupants.get(zone_name, [])

            # Deposit from shedders present in this food zone
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            for _, sv in shedders:
                food_zones[zone_name] += sv * FOOD_DEPOSITION_FRACTION

            # Net growth (reproduction minus decay)
            pool = food_zones[zone_name]
            if pool > 0:
                pool *= (1.0 + growth - decay)
                food_zones[zone_name] = max(pool, 0.0)

            if food_zones[zone_name] <= 0:
                continue

            # Dose to susceptible agents eating here
            susceptible = self._get_susceptible(occupants, pathogen_id)
            for target in susceptible:
                dose = food_zones[zone_name] * FOOD_INGESTION_FRACTION
                agent_doses[target.agent_id] = (
                    agent_doses.get(target.agent_id, 0.0) + dose
                )
                if agent_pathway_doses is not None:
                    pw = agent_pathway_doses.setdefault(target.agent_id, {})
                    pw["food"] = pw.get("food", 0.0) + dose

                matrix.food_contamination_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "food_pool_mass": round(food_zones[zone_name], 4),
                    "dose": round(dose, 4),
                })

    # ── Pathway 6: Environmental Source ─────────────────────────────

    def _pathway_environmental(
        self,
        epoch: int,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
    ) -> None:
        """Environmental source pathway for HVAC-colonised pathogens.

        The HVAC system itself harbours the pathogen (e.g. Legionella
        biofilm).  Each epoch the environmental load grows at the
        colonisation rate and delivers a fraction of its mass to every
        HVAC-connected zone.  Agents inhale the delivered dose.
        """
        ec = (profile or {}).get("environmental_contamination", {})
        if not ec.get("enabled", False):
            return

        load = self.environmental_load.get(pathogen_id, 0.0)
        col_rate = ec.get("colonization_rate_per_epoch", 0.0)

        # Grow the HVAC biofilm load
        load *= (1.0 + col_rate)
        self.environmental_load[pathogen_id] = load

        if load <= 0:
            return

        # Deliver to all zones (environmental pathogen is HVAC-systemic)
        for zone_name, occupants in zone_occupants.items():
            volume = self.zone_volumes.get(zone_name, 100.0)
            delivered = load * ENV_DELIVERY_FRACTION
            concentration = delivered / max(volume, 1.0)

            susceptible = self._get_susceptible(occupants, pathogen_id)
            for target in susceptible:
                dose = concentration * AEROSOL_INHALATION_FRACTION * volume
                dose *= self.hvac_airborne_scalar
                agent_doses[target.agent_id] = (
                    agent_doses.get(target.agent_id, 0.0) + dose
                )
                if agent_pathway_doses is not None:
                    pw = agent_pathway_doses.setdefault(target.agent_id, {})
                    pw["environmental"] = pw.get("environmental", 0.0) + dose

                matrix.environmental_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "environmental_load": round(load, 4),
                    "delivered_mass": round(delivered, 4),
                    "dose": round(dose, 4),
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

    # ── Per-zone contact summary ─────────────────────────────────────

    def _build_zone_contact_summary(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
        matrix: ContactTracingMatrix,
        active_pathogens: list[str],
    ) -> list[dict[str, Any]]:
        """Summarize epoch occupancy and contact intensity per zone.

        Surfaces the same ``zone_occupants`` map used for transmission so
        analysis can verify mixing (e.g. Medical zones are not a sick-call
        gathering point — sick-call is roster-only).
        """
        shared_by_zone: dict[str, int] = {}
        for row in matrix.shared_room_exposures:
            z = row.get("zone", "")
            shared_by_zone[z] = shared_by_zone.get(z, 0) + 1

        droplet_by_zone: dict[str, int] = {}
        for row in matrix.droplet_exposures:
            z = row.get("zone", "")
            droplet_by_zone[z] = droplet_by_zone.get(z, 0) + 1

        infection_by_zone: dict[str, int] = {}
        for row in matrix.transmission_events:
            z = row.get("zone", "")
            infection_by_zone[z] = infection_by_zone.get(z, 0) + 1

        summary: list[dict[str, Any]] = []
        for zone_name in sorted(zone_occupants.keys()):
            occupants = zone_occupants[zone_name]
            if not occupants:
                continue
            occupant_ids = sorted(a.agent_id for a in occupants)
            shedder_ids: set[int] = set()
            for pathogen_id in active_pathogens:
                profile = self.pathogen_profiles.get(pathogen_id, {})
                for agent, _sv in self._get_shedders(
                    occupants, pathogen_id, profile or None,
                ):
                    shedder_ids.add(agent.agent_id)
            sorted_shedders = sorted(shedder_ids)
            summary.append({
                "zone": zone_name,
                "occupant_count": len(occupant_ids),
                "occupant_ids": occupant_ids,
                "shedder_count": len(sorted_shedders),
                "shedder_ids": sorted_shedders,
                "shared_room_exposure_count": shared_by_zone.get(zone_name, 0),
                "droplet_exposure_count": droplet_by_zone.get(zone_name, 0),
                "infection_count": infection_by_zone.get(zone_name, 0),
            })
        return summary

    # ── State management ─────────────────────────────────────────────

    def _update_surface_pools(
        self, _zone_occupants: dict[str, list[KorkinAgent]],
    ) -> None:
        """Apply surface decay after fomite interactions."""
        for zone_name in self.surface_pools:
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
