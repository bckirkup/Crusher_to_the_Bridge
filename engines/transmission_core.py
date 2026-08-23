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

import fnmatch
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import (
    ALPHA,
    BETA,
    SURFACE_DEPOSITION_FRACTION,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import SimClock
from engines.strain_dose_ledger import (
    UNRESOLVED_STRAIN,
    Contributor,
    DoseAttribution,
    EmissionContribution,
    EmissionMix,
    ReservoirComposition,
    StrainDoseLedger,
    attribution,
    build_emission_mix,
    draw_contributor,
)
from engines.strain_mutation import MutationOperator
from engines.strain_state import (
    IMMUNITY_AT_EMBARKATION,
    IMMUNITY_FROM_INFECTION,
    ImmuneRecord,
    Phenotype,
    StrainEvolutionConfig,
    StrainRegistry,
    StrainState,
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

# R0-calibrated contact pool (from Person.java avgR array) — legacy contact_mode
AVG_R_POOL = [1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2]

# Defaults for density_dependent contact_mode (partial overrides merge onto these)
DEFAULT_DENSITY_CFG: dict[str, float] = {
    "reference_occupancy": 50.0,
    "base_contacts": 1.33,
    "max_contacts": 20.0,
    "exponent": 0.5,
    "crew_contact_multiplier": 2.0,
}
DEFAULT_CONTACT_MODE = "density_dependent"

# Per-pathogen route weights (identity default → no change when absent)
DEFAULT_ROUTE_WEIGHTS: dict[str, float] = {
    "direct_contact": 1.0,
    "droplet": 1.0,
    "hvac_airborne": 1.0,
    "fomite": 1.0,
    "food_contamination": 1.0,
    "environmental_source": 1.0,
}
# Internal pathway dose keys → transmission_route_weights keys
PATHWAY_WEIGHT_KEYS: dict[str, str] = {
    "direct_contact": "direct_contact",
    "droplet": "droplet",
    "hvac_airborne": "hvac_airborne",
    "fomite": "fomite",
    "food": "food_contamination",
    "environmental": "environmental_source",
}

# Log-sigma defaults for heterogeneous_zone_dose (mean-1 lognormal).
# Low in cabins (near-uniform stateroom mixing); high in dining/service;
# medium-high in free/common areas. Not the default contact_mode.
DEFAULT_HETEROGENEOUS_SIGMA_BY_ZONE_TYPE: dict[str, float] = {
    "Cabin_Corridor": 0.25,  # low
    "Dining": 1.0,           # high
    "Free": 0.75,            # medium-high
    "Room": 0.5,
    "Medical": 0.5,
    "Engineering": 0.5,
}
DEFAULT_HETEROGENEOUS_SIGMA_SERVICE = 1.0  # Galley / service (high)
DEFAULT_HETEROGENEOUS_SIGMA_DEFAULT = 0.75
CONTACT_MODES = frozenset({
    "legacy",
    "density_dependent",
    "heterogeneous_zone_dose",
})


# ── Data structures ─────────────────────────────────────────────────────

@dataclass
class TransmissionEvent:
    """A single transmission event across any pathway.

    ``source_agent_id`` and ``source_strain_id`` are populated only when strain
    attribution is active and the winning contribution came from a pathway that
    knows its shedder; reservoir pathways name a strain but no source agent.
    """
    epoch: int
    pathway: str  # "direct_contact" | "droplet" | "hvac_airborne" | "fomite"
    source_agent_id: int | None
    target_agent_id: int
    zone: str
    dose: float
    source_strain_id: str | None = None


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

# Fraction of a shedding host's emission entering a zone-scoped environmental
# reservoir (spore shedding into a spa or ward). Applied only under variant
# surveillance, since it adds a host input the scalar reservoir never had.
ENV_HOST_DEPOSITION_FRACTION = 1e-4

# Reservoir kinds tracked by the strain composition shadow of the pools
SURFACE_RESERVOIR = "surface"
FOOD_RESERVOIR = "food"
AIRBORNE_RESERVOIR = "air"
ENV_RESERVOIR = "env"

# Zone stand-in for the ship-wide (HVAC-systemic) environmental reservoir
SHIP_WIDE_ZONE = "_ship"

# Per-epoch survival of a zone's aerosol composition. Mirrors the bridge's flat
# airborne decay (ENV_DECAY_RATE); only shares are read, so any uniform
# rescaling the transport engine applies on top leaves attribution unchanged.
AIRBORNE_COMPOSITION_RETENTION = 0.5

# Pool mass at or under which a contributor counts as gone from a reservoir
POOL_EXTINCTION_MASS = 1e-12


def _best_protection(
    config: StrainEvolutionConfig,
    priors: Mapping[str, float | None],
    challenge: StrainState,
) -> float:
    """Protection the best-matched prior exposure gives against a challenge.

    The maximum over the host's immune history rather than a sum: repeated
    exposure to related genotypes does not stack past what the closest match
    already gives, and a host that has met the challenge genotype itself is
    protected as if its heterologous exposures had not happened.

    Each prior carries its own age in days of natural history (``None`` for a
    lineage still resident), so a fresh exposure and a year-old one to the same
    genotype are not the same immunity.
    """
    return max(
        config.waned_protection(prior, challenge, age)
        for prior, age in priors.items()
    )


def _nonspecific_protection(
    config: StrainEvolutionConfig,
    priors: Mapping[str, float | None],
) -> float:
    """Protection a host has against a challenge it cannot even name.

    Only the refractory window counts: it is a genotype-blind post-resolution
    refractoriness, so it applies to unlabeled dose exactly as it applies to a
    named lineage, while the matched ``cross_immunity`` value cannot — there is
    no genotype to match. Passing a matched value of zero makes the waning
    kernel return the window inside it and decay to zero after it, so unlabeled
    dose outside the window stays unprotected as it was.

    A prior with no resolution age (a resident lineage, or an embarkation prior
    of unknown date) has no window and contributes nothing here.
    """
    return max(
        (
            config.immune_waning.protection_at(0.0, age, 0.0)
            for age in priors.values() if age is not None
        ),
        default=0.0,
    )


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
        cfg: dict[str, Any] | None = None,
        food_zone_multipliers: dict[str, float] | None = None,
        strain_registry: StrainRegistry | None = None,
        clock: SimClock | None = None,
    ) -> None:
        self.rng = rng
        # The run's one clock, so an immunity parameter written in days of
        # natural history is aged on the same grid the biology advances on.
        self.clock = clock if clock is not None else SimClock.from_config(cfg)
        self.zone_volumes = zone_volumes or {}
        self.pathogen_profiles = pathogen_profiles or {}
        self.zone_types = zone_types or {}
        self.zone_ventilation = zone_ventilation or {}
        self.confinement_isolation_factor = confinement_isolation_factor
        self.corridor_direct_contact_factor = corridor_direct_contact_factor
        self.food_zone_multipliers = food_zone_multipliers or {}
        self._quarantined_ids: set[int] = set()
        # Voyage layer contact scale (1.0 when effects disabled)
        self.voyage_contact_multiplier: float = 1.0

        tx = (cfg or {}).get("transmission", {}) or {}
        mode = str(tx.get("contact_mode", DEFAULT_CONTACT_MODE))
        if mode not in CONTACT_MODES:
            mode = DEFAULT_CONTACT_MODE
        self.contact_mode = mode
        provided = tx.get("density_dependent") or {}
        if not isinstance(provided, dict):
            provided = {}
        self.density_cfg: dict[str, float] = {
            **DEFAULT_DENSITY_CFG,
            **{k: float(v) for k, v in provided.items() if k in DEFAULT_DENSITY_CFG},
        }
        # Dining-type zones or Galley IDs: crew contact multiplier applies here
        self._service_zones: set[str] = {
            z
            for z, t in self.zone_types.items()
            if t == "Dining" or "Galley" in z
        }
        het_raw = tx.get("heterogeneous_zone_dose") or {}
        if not isinstance(het_raw, dict):
            het_raw = {}
        sigma_map = dict(DEFAULT_HETEROGENEOUS_SIGMA_BY_ZONE_TYPE)
        provided_sigma = het_raw.get("sigma_by_zone_type") or {}
        if isinstance(provided_sigma, dict):
            for k, v in provided_sigma.items():
                sigma_map[str(k)] = float(v)
        self.heterogeneous_sigma_by_zone_type = sigma_map
        self.heterogeneous_sigma_service = float(
            het_raw.get(
                "sigma_service",
                DEFAULT_HETEROGENEOUS_SIGMA_SERVICE,
            ),
        )
        self.heterogeneous_sigma_default = float(
            het_raw.get(
                "default_sigma",
                DEFAULT_HETEROGENEOUS_SIGMA_DEFAULT,
            ),
        )

        # Persistent state: surface fomite pools per zone per pathogen
        # {pathogen_id: {zone: mass}}
        self.surface_pools: dict[str, float] = {}  # aggregate (legacy)
        self.surface_pools_by_pathogen: dict[str, dict[str, float]] = {}
        self._surface_last_deposition_epoch: dict[str, int] = {}

        # Persistent state: airborne aerosol pools per zone per pathogen
        self.aerosol_pools: dict[str, float] = {}  # aggregate (legacy)
        self.aerosol_pools_by_pathogen: dict[str, dict[str, float]] = {}

        # Pathway 5: food contamination pools per Dining zone per pathogen
        self.food_pools: dict[str, dict[str, float]] = {}

        # Pathway 6: environmental contamination load per pathogen
        self.environmental_load: dict[str, float] = {}
        # Zone-scoped environmental reservoirs {pid: {zone: mass}}
        self.env_contamination: dict[str, dict[str, float]] = {}

        # Previous epoch's zone occupancy (for fomite trailing detection)
        self._prev_zone_occupants: dict[str, set[int]] = {}

        # Previous epoch's zone shedders per pathogen
        self._prev_zone_shedders: dict[str, list[int]] = {}
        self._prev_zone_shedders_by_pathogen: dict[str, dict[str, list[int]]] = {}

        self._init_strain_tracking(cfg, strain_registry)

        # Protocol-driven pathway scalars (1.0 = no modification)
        self.direct_contact_scalar: float = 1.0
        self.droplet_scalar: float = 1.0
        self.hvac_airborne_scalar: float = 1.0

    # ── Strain attribution (variant surveillance) ────────────────────

    def _init_strain_tracking(
        self,
        cfg: dict[str, Any] | None,
        strain_registry: StrainRegistry | None,
    ) -> None:
        """Set up the strain-resolved dose ledger when the flag is on.

        With ``variant_surveillance.enabled`` false there is no registry, every
        attribution hook short-circuits, and no RNG draw is added — so a run is
        bit-identical to the pre-strain engine.
        """
        vs = (cfg or {}).get("variant_surveillance", {}) or {}
        enabled = bool(vs.get("enabled", False))
        self.strain_registry: StrainRegistry | None = strain_registry or (
            StrainRegistry() if enabled else None
        )
        self.strain_configs: dict[str, StrainEvolutionConfig] = {}
        if self.strain_registry is not None:
            for pid, profile in self.pathogen_profiles.items():
                config = StrainEvolutionConfig.from_profile(
                    {**profile, "pathogen_id": pid},
                )
                if config is not None:
                    self.strain_configs[pid] = config
        self.mutation_operator: MutationOperator | None = (
            MutationOperator(self.strain_registry, self.strain_configs)
            if self.strain_registry is not None
            else None
        )
        # Strain composition of the lagged pools (air, surfaces, food, environment)
        self._reservoir = ReservoirComposition()
        # Founder strain of each pathogen's environmental reservoir
        self._env_strain_ids: dict[str, str] = {}
        # Per-epoch strain-resolved dose: {agent: {pathogen: {contributor: dose}}}
        self._strain_doses: dict[int, dict[str, dict[Contributor, float]]] = {}
        self._last_pathogen_doses: dict[int, dict[str, float]] = {}

    @property
    def strain_tracking(self) -> bool:
        """True when doses are attributed to strains."""
        return self.strain_registry is not None

    def _transmissibility(self, strain_id: str) -> float:
        if self.strain_registry is None or strain_id == UNRESOLVED_STRAIN:
            return 1.0
        return self.strain_registry.get(strain_id).transmissibility_multiplier

    def _phenotype(self, strain_id: str | None) -> Phenotype | None:
        """Heritable effects of a strain, cached onto the infection record.

        The shedding and incubation axes are read outside transmission (by the
        shedding curve and the epoch's illness draw), so they travel with the
        infection rather than requiring those call sites to hold a registry.
        """
        if self.strain_registry is None or not strain_id:
            return None
        return Phenotype.of(self.strain_registry.get(strain_id))

    def _founder_genotype(self, pathogen_id: str) -> str:
        """Draw a founder genotype from the pathogen's prior distribution."""
        config = self.strain_configs.get(pathogen_id)
        if config is None or not config.prior_genotype_distribution:
            return ""
        genotypes = tuple(config.prior_genotype_distribution)
        probs = [config.prior_genotype_distribution[g] for g in genotypes]
        return str(self.rng.choice(genotypes, p=probs))

    def _resident_strain_id(self, agent: KorkinAgent, pathogen_id: str) -> str | None:
        """Strain an agent is shedding, minting a founder for seeded infections.

        Seeded and pre-existing infections predate any strain, so the first time
        one is used as a source it is assigned a founder lineage — which is also
        how the introduced-diversity regime gets its diversity.
        """
        if self.strain_registry is None or pathogen_id == "_default":
            return None
        strain_id = agent.strain_id_for(pathogen_id)
        if strain_id is not None:
            return strain_id
        founder = self.strain_registry.mint(
            pathogen_id,
            genotype=self._founder_genotype(pathogen_id),
            origin="founder",
        )
        agent.assign_strain(
            pathogen_id, founder.strain_id, Phenotype.of(founder),
        )
        return founder.strain_id

    def _environmental_strain_id(self, pathogen_id: str) -> str | None:
        """Founder strain of a pathogen's environmental reservoir."""
        if self.strain_registry is None or pathogen_id == "_default":
            return None
        strain_id = self._env_strain_ids.get(pathogen_id)
        if strain_id is None:
            founder = self.strain_registry.mint(
                pathogen_id,
                genotype=self._founder_genotype(pathogen_id),
                origin="founder",
            )
            strain_id = founder.strain_id
            self._env_strain_ids[pathogen_id] = strain_id
        return strain_id

    def _shed_masses(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        emitted: float,
    ) -> list[tuple[str, float]]:
        """One host's emitted mass, split among the lineages it carries.

        A co-infected host emits a mixture, so its onward transmissions are
        attributable to either lineage in proportion to what it is shedding.
        """
        shares = agent.strain_shedding_shares(
            pathogen_id, self.pathogen_profiles.get(pathogen_id, {}),
        )
        if not shares:
            strain_id = self._resident_strain_id(agent, pathogen_id)
            return [] if strain_id is None else [(strain_id, emitted)]
        return [(sid, emitted * share) for sid, share in shares.items()]

    def _emissions(
        self,
        weighted_shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
    ) -> list[EmissionContribution]:
        contributions: list[EmissionContribution] = []
        for agent, emitted in weighted_shedders:
            for strain_id, mass in self._shed_masses(agent, pathogen_id, emitted):
                contributions.append(EmissionContribution(
                    strain_id=strain_id,
                    source_agent_id=agent.agent_id,
                    emitted=mass,
                    transmissibility=self._transmissibility(strain_id),
                ))
        return contributions

    def _shedder_mix(
        self,
        shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
    ) -> EmissionMix | None:
        """Emission mix of the strains shed into one zone."""
        if self.strain_registry is None:
            return None
        return build_emission_mix(self._emissions(shedders, pathogen_id))

    def _direct_contact_mix(
        self,
        target: KorkinAgent,
        shedders: list[tuple[KorkinAgent, float]],
        pathogen_id: str,
        zone_mix: EmissionMix | None,
    ) -> EmissionMix | None:
        """Direct-contact mix for one target.

        ``zone_mix`` serves every target in a well-mixed zone; under cabin
        confinement each pair has its own contact factor, so the shares are
        rebuilt per target.
        """
        if zone_mix is not None or self.strain_registry is None:
            return zone_mix
        return self._shedder_mix(
            [
                (shedder, emitted * self._cabin_pair_contact_factor(shedder, target))
                for shedder, emitted in shedders
            ],
            pathogen_id,
        )

    def _min_strain_fraction(self, pathogen_id: str) -> float:
        """Frequency floor below which a pool's lineages are lumped."""
        config = self.strain_configs.get(pathogen_id)
        return 0.0 if config is None else config.min_strain_fraction

    def _reservoir_mix(
        self, kind: str, pathogen_id: str, zone_name: str,
    ) -> EmissionMix | None:
        """Emission mix of a pool's current strain composition."""
        if self.strain_registry is None:
            return None
        key = ReservoirComposition.key(kind, pathogen_id, zone_name)
        multipliers = {
            strain_id: self._transmissibility(strain_id)
            for strain_id, _ in self._reservoir.contributors(key)
        }
        return self._reservoir.mix(key, multipliers)

    def _deposit_reservoir_strains(
        self,
        kind: str,
        pathogen_id: str,
        zone_name: str,
        deposits: list[tuple[KorkinAgent, float]],
    ) -> None:
        """Record who deposited what into a lagged pool."""
        if self.strain_registry is None:
            return
        key = ReservoirComposition.key(kind, pathogen_id, zone_name)
        for agent, mass in deposits:
            for strain_id, strain_mass in self._shed_masses(agent, pathogen_id, mass):
                self._reservoir.deposit(
                    key, (strain_id, agent.agent_id), strain_mass,
                )
        self._reservoir.lump(self._min_strain_fraction(pathogen_id), key)

    def surface_lineage_masses(
        self,
        pathogen_id: str,
        zone_name: str,
    ) -> dict[str, float]:
        """Return current surface mass grouped by reportable genotype."""
        if self.strain_registry is None:
            return {}
        key = ReservoirComposition.key(SURFACE_RESERVOIR, pathogen_id, zone_name)
        grouped: dict[str, float] = {}
        for (strain_id, _source_agent_id), mass in self._reservoir.contributors(key).items():
            if strain_id == UNRESOLVED_STRAIN:
                genotype = UNRESOLVED_STRAIN
            else:
                genotype = self.strain_registry.get(strain_id).genotype or UNRESOLVED_STRAIN
            grouped[genotype] = grouped.get(genotype, 0.0) + float(mass)
        return grouped

    def surface_epochs_since_deposition(
        self,
        pathogen_id: str,
        zone_name: str,
        current_epoch: int,
    ) -> int | None:
        """Return elapsed epochs since the last positive surface deposit."""
        if self.strain_registry is None:
            return None
        key = ReservoirComposition.key(SURFACE_RESERVOIR, pathogen_id, zone_name)
        deposited = self._surface_last_deposition_epoch.get(key)
        if deposited is None:
            return None
        return max(int(current_epoch) - deposited, 0)

    def _seed_environmental_composition(
        self,
        pathogen_id: str,
        zone_name: str,
        level: float,
    ) -> None:
        """Give a reservoir its founder lineage the first time it is read.

        A reservoir that predates the run (spa biofilm, spore load) has a
        lineage no host deposited, so it is minted once at the pool's own mass
        and then competes with host deposits like any other contributor. An
        empty reservoir is not seeded: its composition is whatever hosts put in
        it.
        """
        key = ReservoirComposition.key(ENV_RESERVOIR, pathogen_id, zone_name)
        if level <= 0.0 or self._reservoir.contributors(key):
            return
        strain_id = self._environmental_strain_id(pathogen_id)
        if strain_id is None:
            return
        self._reservoir.deposit(key, (strain_id, None), level)

    def _environmental_attribution(
        self,
        ledger: StrainDoseLedger | None,
        pathogen_id: str,
        zone_name: str = SHIP_WIDE_ZONE,
        level: float = 0.0,
    ) -> DoseAttribution | None:
        """Attribution for reservoir-only exposure (no shedder to name)."""
        if self.strain_registry is None or pathogen_id == "_default":
            return None
        self._seed_environmental_composition(pathogen_id, zone_name, level)
        mix = self._reservoir_mix(ENV_RESERVOIR, pathogen_id, zone_name)
        if mix is None:
            return None
        return attribution(ledger, mix)

    def _update_env_reservoir_strains(
        self,
        pathogen_id: str,
        zone_name: str,
        level: float,
        factor: float,
        occupants: list[KorkinAgent],
        profile: dict[str, Any],
    ) -> float:
        """Age a zone reservoir's composition and add host shedding to it.

        Returns the mass deposited, which is added to the scalar reservoir too so
        the pool and its composition describe the same thing.
        """
        if self.strain_registry is None or pathogen_id == "_default":
            return 0.0
        key = ReservoirComposition.key(ENV_RESERVOIR, pathogen_id, zone_name)
        self._seed_environmental_composition(pathogen_id, zone_name, level)
        self._reservoir.decay(factor, key)
        deposits = [
            (agent, sv * ENV_HOST_DEPOSITION_FRACTION)
            for agent, sv in self._get_shedders(occupants, pathogen_id, profile)
        ]
        self._deposit_reservoir_strains(
            ENV_RESERVOIR, pathogen_id, zone_name, deposits,
        )
        return sum(mass for _, mass in deposits)

    def _airborne_composition(
        self,
        pathogen_id: str,
        zone_shedders: dict[str, list[tuple[KorkinAgent, float]]],
    ) -> None:
        """Age each zone's aerosol composition, then add this epoch's shedding.

        Read before the deposit, so a downstream pickup is attributed to the air
        that is already in the zone rather than to whoever is shedding upstream
        right now — the composition is the lag the scalar pool does not carry.
        """
        if self.strain_registry is None:
            return
        self._reservoir.decay_kind(
            AIRBORNE_COMPOSITION_RETENTION,
            f"{AIRBORNE_RESERVOIR}|{pathogen_id}",
        )
        for zone_name, shedders in zone_shedders.items():
            self._deposit_reservoir_strains(
                AIRBORNE_RESERVOIR, pathogen_id, zone_name, list(shedders),
            )

    def _decay_surface_composition(self) -> None:
        """Age surface strain composition with the surface pools it shadows."""
        if self.strain_registry is None:
            return
        self._reservoir.decay_kind(1.0 - SURFACE_DECAY_RATE, SURFACE_RESERVOIR)

    def collect_extinct_strains(self, agents: list[KorkinAgent]) -> tuple[str, ...]:
        """Drop registry entries no host and no pool still references.

        Live means carried by an infection (any resident lineage of a
        co-infection, not just the record's primary) or standing in a pool above
        :data:`POOL_EXTINCTION_MASS`; the registry additionally keeps the
        ancestry of what is live, so a lineage's parents stay callable after the
        lineage itself dies out. The environmental founders are held too — one
        per pathogen, reused whenever a reservoir is re-seeded.
        """
        if self.strain_registry is None:
            return ()
        self._reservoir.drop_empty(POOL_EXTINCTION_MASS)
        live: set[str] = set(self._env_strain_ids.values())
        live |= self._reservoir.strain_ids()
        for agent in agents:
            for infection in agent.infections.values():
                strain_id = infection.get("strain_id")
                if strain_id is not None:
                    live.add(str(strain_id))
                residents = infection.get("strains")
                if isinstance(residents, dict):
                    live |= {str(sid) for sid in residents}
        return self.strain_registry.collect(live)

    def _accumulate(
        self,
        target_id: int,
        pathway: str,
        dose: float,
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        attribution_: DoseAttribution | None = None,
    ) -> float:
        """Add one exposure's dose, scaled by emission-side transmissibility.

        Returns the dose actually credited, which is what the tracing record
        should report.
        """
        if attribution_ is not None:
            dose *= attribution_.emission_factor
        agent_doses[target_id] = agent_doses.get(target_id, 0.0) + dose
        if agent_pathway_doses is not None:
            pw = agent_pathway_doses.setdefault(target_id, {})
            pw[pathway] = pw.get(pathway, 0.0) + dose
        if attribution_ is not None:
            attribution_.record(target_id, pathway, dose)
        return dose

    def _fold_strain_doses(
        self,
        pathogen_id: str,
        ledger: StrainDoseLedger | None,
        weights: dict[str, float],
        susceptibility: dict[int, float],
    ) -> None:
        """Merge one pathogen pass's ledger into the epoch's strain doses."""
        if ledger is None:
            return
        pathway_weights = {
            pathway: float(weights.get(PATHWAY_WEIGHT_KEYS.get(pathway, pathway), 1.0))
            for pathway in PATHWAY_WEIGHT_KEYS
        }
        for agent_id in ledger.agent_ids():
            mult = susceptibility.get(agent_id, 1.0)
            by_pathogen = self._strain_doses.setdefault(agent_id, {})
            bucket = by_pathogen.setdefault(pathogen_id, {})
            for contributor, dose in ledger.strain_doses(
                agent_id, pathway_weights,
            ).items():
                bucket[contributor] = bucket.get(contributor, 0.0) + dose * mult

    def _draw_source(self, agent_id: int, pathogen_id: str) -> Contributor:
        """Draw the parent strain (and its shedder) from the dose shares.

        A draw that lands on the unresolved bin of a pool returns no parent: the
        acquiring host carries a lineage the pool could not resolve, and is
        minted its own founder if it ever sheds.
        """
        shares = self._strain_doses.get(agent_id, {}).get(pathogen_id, {})
        if not shares:
            return ("", None)
        contributor = draw_contributor(shares, self.rng)
        if contributor is None or contributor[0] == UNRESOLVED_STRAIN:
            return ("", None)
        return contributor

    def _embarkation_genotype(
        self, agent: KorkinAgent, pathogen_id: str,
    ) -> str | None:
        """Genotype an agent immune at embarkation is immune *against*.

        Drawn once from ``prior_genotype_distribution`` and cached, because
        pre-existing immunity has to be against something before a challenge
        genotype can escape it. Also written to the immune history, so standing
        immunity and immunity earned aboard read the same way downstream.
        """
        if not agent.immune:
            return None
        cached = agent.prior_genotypes.get(pathogen_id)
        if cached is None:
            cached = self._founder_genotype(pathogen_id)
            agent.prior_genotypes[pathogen_id] = cached
            if cached:
                agent.record_immunity(ImmuneRecord(
                    pathogen_id=pathogen_id,
                    genotype=cached,
                    origin=IMMUNITY_AT_EMBARKATION,
                ))
        return cached or None

    def _resolved_exposure_ages(
        self, agent: KorkinAgent, pathogen_id: str, epoch: int,
    ) -> dict[str, float]:
        """Days of natural history since each genotype's exposure resolved.

        The most recent record wins for a genotype met more than once, and the
        conversion from epochs runs through the run's clock, so a refractory
        window written in days means the same thing on any epoch grid.

        Only exposures resolved aboard have a resolution time. An embarkation
        prior was raised at an unknown point before the voyage, so it is left
        ageless rather than dated to epoch 0, which would hand a host whose
        infection was years ago a fresh refractory window.
        """
        ages: dict[str, float] = {}
        for record in agent.immune_history:
            if record.pathogen_id != pathogen_id or not record.genotype:
                continue
            if record.origin != IMMUNITY_FROM_INFECTION:
                continue
            days = self.clock.days_elapsed(max(0, epoch - record.epoch))
            prior = ages.get(record.genotype)
            if prior is None or days < prior:
                ages[record.genotype] = days
        return ages

    def _prior_exposures(
        self, agent: KorkinAgent, pathogen_id: str, epoch: int,
    ) -> dict[str, float | None]:
        """Prior genotypes mapped to the age of the exposure that raised them.

        ``None`` marks an exposure with no resolution time on this voyage: a
        lineage still resident (interference from an ongoing infection, which is
        not memory) or an embarkation prior. Both keep the declared
        ``cross_immunity`` value, neither gains a refractory window. A genotype
        the host has both resolved and re-acquired keeps its resolved age, since
        the memory is the thing a challenge of that genotype meets first.
        """
        ages = self._resolved_exposure_ages(agent, pathogen_id, epoch)
        exposures: dict[str, float | None] = {
            genotype: ages.get(genotype)
            for genotype in self._prior_genotypes(agent, pathogen_id)
        }
        return exposures

    def _prior_genotypes(
        self, agent: KorkinAgent, pathogen_id: str,
    ) -> tuple[str, ...]:
        """Every genotype this agent's standing immunity was raised against.

        Three sources: exposures resolved aboard (the immune history, which is a
        snapshot and so survives the lineage being collected), lineages still
        resident — an ongoing infection interferes with a challenge of its own
        genotype before it has cleared — and, for an agent immune at
        embarkation, the drawn prior. A host that has resolved two genotypes is
        protected by both, so the challenge is scored against the best match
        rather than the most recent exposure.
        """
        if self.strain_registry is None:
            return ()
        priors: dict[str, None] = dict.fromkeys(
            agent.immune_genotypes(pathogen_id),
        )
        for strain_id in agent.resident_strains(pathogen_id):
            if strain_id in self.strain_registry:
                genotype = self.strain_registry.get(strain_id).genotype
                if genotype:
                    priors.setdefault(genotype, None)
        embarked = self._embarkation_genotype(agent, pathogen_id)
        if embarked:
            priors.setdefault(embarked, None)
        return tuple(priors)

    def _challenge_protection(
        self, agent: KorkinAgent, pathogen_id: str, epoch: int = 0,
    ) -> float:
        """Protection against this epoch's challenge, in [0, 1].

        Absolute (1.0) for an agent immune at embarkation, which reproduces the
        legacy behaviour exactly whenever variant surveillance is off or the
        pathogen declares no ``cross_immunity``. With genotype-aware immunity
        configured, protection instead becomes specific and breachable: the
        dose-share-weighted mean of ``effective_protection`` over the strains
        challenging this agent, so a heterologous or escape mutant gets through
        an immunity that a homologous strain would not.
        """
        config = self.strain_configs.get(pathogen_id)
        legacy = 1.0 if agent.immune else 0.0
        if self.strain_registry is None or config is None or not config.cross_immunity:
            return legacy
        priors = self._prior_exposures(agent, pathogen_id, epoch)
        if not priors:
            return 0.0
        shares = self._strain_doses.get(agent.agent_id, {}).get(pathogen_id, {})
        total = sum(shares.values())
        if total <= 0.0:
            return legacy
        # Unattributed dose — no strain, or a pool's sub-floor tail — carries no
        # genotype to be recognised, so it earns only the *non*-specific part of
        # the host's immunity: the refractory window, which is genotype-blind by
        # construction, and nothing from the matched cross-immunity matrix. It
        # stays in the denominator either way, so after the window it is
        # unprotected dose as before.
        unnamed = _nonspecific_protection(config, priors)
        weighted = sum(
            dose * (
                _best_protection(config, priors, self.strain_registry.get(sid))
                if sid and sid != UNRESOLVED_STRAIN else unnamed
            )
            for (sid, _source), dose in shares.items()
        )
        return max(0.0, min(1.0, weighted / total))

    def _dose_response(self, pathogen_id: str, dose: float) -> float:
        """Probability one epoch's dose of a pathogen establishes an infection."""
        dr = self.pathogen_profiles.get(pathogen_id, {}).get("dose_response", {})
        if dr.get("model", "beta_poisson") == "exponential":
            return 1.0 - math.exp(-dr.get("k", 0.01) * dose)
        return 1.0 - math.pow(
            1.0 + dose / dr.get("beta", BETA), -dr.get("alpha", ALPHA),
        )

    def _superinfection_susceptibility(self, pathogen_id: str) -> float:
        """How much of a naive host's susceptibility an infected host retains.

        Homotypic interference: an established infection occupies the niche, so
        a second lineage of the same pathogen faces a discounted challenge. This
        is the *non*-genotype-specific part — genotype-specific interference
        already arrives through ``cross_immunity``, which sees the resident
        strain as the host's prior exposure.
        """
        config = self.strain_configs.get(pathogen_id)
        if config is None:
            return 0.0
        return max(0.0, min(1.0, config.superinfection_susceptibility))

    def _superinfection_open(self, pathogen_id: str) -> bool:
        """True when a second lineage of this pathogen can establish at all.

        False without strain tracking, which is what keeps an already-infected
        agent skipped exactly as before.
        """
        if self.strain_registry is None:
            return False
        return self._superinfection_susceptibility(pathogen_id) > 0.0

    def _establish(
        self,
        agent: KorkinAgent,
        pathogen_id: str,
        acquired_strain_id: str,
        dose: float,
        epoch: int,
        *,
        resident: bool,
    ) -> bool:
        """Install an acquired strain, as a new infection or a co-resident.

        False when nothing new established — re-exposure of a host that already
        carries this very lineage, whose inoculum is absorbed rather than
        counted as a transmission event.
        """
        if agent.immune and not resident:
            # Breakthrough: genotype-specific immunity was breached, so the host
            # leaves the immune compartment and takes the ordinary legacy path.
            agent.immune = False
            agent.infection_status = InfectionStatus.SUSCEPTIBLE
        if resident:
            strain_id = acquired_strain_id or self._unresolved_founder(pathogen_id)
            return agent.superinfect_with_strain(
                pathogen_id,
                strain_id,
                dose,
                epoch,
                phenotype=self._phenotype(strain_id),
            )
        agent.infect_with_pathogen(
            pathogen_id,
            dose,
            epoch,
            rng=self.rng,
            profile=self.pathogen_profiles.get(pathogen_id, {}),
            strain_id=acquired_strain_id or None,
            strain_phenotype=self._phenotype(acquired_strain_id),
        )
        return True

    def _unresolved_founder(self, pathogen_id: str) -> str:
        """Founder for a superinfection whose parent the pool could not resolve.

        A co-resident lineage has to be nameable: the census counts it and every
        assay reads it back, so an acquisition drawn from a sub-floor pool bin
        founds its own lineage here — the same contract
        :meth:`_resident_strain_id` applies when such a host first sheds. Before
        this, an unresolved superinfection installed a resident keyed on the
        empty string, which the lineage census then failed to look up.
        """
        if self.strain_registry is None:
            return ""
        founder = self.strain_registry.mint(
            pathogen_id,
            genotype=self._founder_genotype(pathogen_id),
            origin="founder",
        )
        return founder.strain_id

    def _inherit_strain(self, parent_strain_id: str) -> str:
        """Strain a new infection acquires: the parent's, or a mutant of it.

        Mutation is drawn once per infection event, so a lineage label means one
        genome rather than one infection.
        """
        if self.mutation_operator is None or not parent_strain_id:
            return parent_strain_id
        return self.mutation_operator.on_transmission(parent_strain_id, self.rng)

    def apply_within_host_mutations(self, agents: list[KorkinAgent]) -> None:
        """Draw one within-host mutation chance per resident lineage-epoch.

        Off unless a pathogen sets ``within_host_mutation_rate`` > 0, which is
        the only mutational supply available to the de novo regime when a voyage
        is too short for transmission chains to supply it (plan §0 decision 2).
        Untracked infections are left alone rather than minted a founder here:
        founders appear when an agent first sheds, so enabling the within-host
        source cannot change who is a founder. In a co-infected host each
        lineage mutates on its own, replacing itself rather than the mixture, so
        a mutation in one strain never erases its co-resident.
        """
        if self.mutation_operator is None:
            return
        rates = {
            pid: cfg.within_host_mutation_rate
            for pid, cfg in self.strain_configs.items()
            if cfg.within_host_mutation_rate > 0.0
        }
        if not rates:
            return
        for agent in agents:
            for pathogen_id in rates:
                for strain_id in tuple(agent.resident_strains(pathogen_id)):
                    mutated = self.mutation_operator.within_host(strain_id, self.rng)
                    if mutated != strain_id:
                        agent.replace_strain(
                            pathogen_id, strain_id, mutated,
                            self._phenotype(mutated),
                        )

    def apply_recombination(self, agents: list[KorkinAgent]) -> None:
        """Draw one recombination chance per co-infected agent-epoch.

        Recombination is the only evolutionary source that needs two parents in
        one place, which is why it could not exist before co-infection did. It
        runs after within-host mutation so a lineage that mutated this epoch is
        already the thing that recombines, and it is off unless a pathogen sets
        ``recombination_rate`` > 0.

        The recombinant *replaces the lineage it arose in* and the donor stays
        resident, so one event leaves a host's resident count unchanged:
        reassortment happens in place, and only superinfection widens a mixture.
        Over a voyage the population still diversifies, since a recombinant is a
        new lineage that can superinfect a host already carrying both parents.
        """
        if self.mutation_operator is None:
            return
        pathogens = tuple(
            pid for pid, cfg in self.strain_configs.items()
            if cfg.recombination_rate > 0.0
        )
        if not pathogens:
            return
        for agent in agents:
            for pathogen_id in pathogens:
                self._recombine_in_host(agent, pathogen_id)

    def _recombine_in_host(self, agent: KorkinAgent, pathogen_id: str) -> None:
        """One recombination draw for one host's residents of one pathogen."""
        if self.mutation_operator is None:
            return
        residents = tuple(agent.resident_strains(pathogen_id))
        if len(residents) < 2:
            return
        outcome = self.mutation_operator.recombine(residents, self.rng)
        if outcome is None:
            return
        replaced, recombinant = outcome
        agent.replace_strain(
            pathogen_id, replaced, recombinant, self._phenotype(recombinant),
        )

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
                baseline = float(ec.get("baseline_environmental_load", 0.0))
                self.environmental_load[pid] = baseline
                source_zones = ec.get("source_zones")
                if source_zones:
                    self.env_contamination.setdefault(pid, {})
                    for z in zone_names:
                        if self._zone_matches(z, source_zones):
                            self.env_contamination[pid].setdefault(z, baseline)

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
        self.apply_within_host_mutations(agents)
        self.apply_recombination(agents)

        # Build zone occupancy maps
        zone_occupants: dict[str, list[KorkinAgent]] = {}
        for agent in agents:
            loc = agent.current_location
            if loc in ("Isolated_In_Quarters", "Ashore"):
                continue
            if getattr(agent, "ashore", False):
                continue
            zone_occupants.setdefault(loc, []).append(agent)

        # Per-agent accumulated dose across all pathways (aggregate)
        agent_doses: dict[int, float] = {}
        # Track per-agent per-pathway dose breakdown for attribution
        agent_pathway_doses: dict[int, dict[str, float]] = {}
        # Per-agent per-pathogen dose accumulator
        agent_pathogen_doses: dict[int, dict[str, float]] = {}
        # Strain-resolved shadow of the same doses (empty when flag is off);
        # the pooled doses are kept so the shadow can be checked against the
        # dose that actually drove the draw
        self._strain_doses = {}
        self._last_pathogen_doses = agent_pathogen_doses

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
                resident = agent.is_infected_with(pathogen_id)
                if resident and not self._superinfection_open(pathogen_id):
                    continue
                p_dose = agent_pathogen_doses.get(agent.agent_id, {}).get(pathogen_id, 0.0)
                if p_dose <= 0:
                    continue
                protection = self._challenge_protection(agent, pathogen_id, epoch)
                if protection >= 1.0:
                    continue

                inf_prob = self._dose_response(pathogen_id, p_dose)
                inf_prob *= 1.0 - protection
                if resident:
                    inf_prob *= self._superinfection_susceptibility(pathogen_id)

                if self.rng.random() < inf_prob:
                    parent_strain_id, source_agent_id = self._draw_source(
                        agent.agent_id, pathogen_id,
                    )
                    acquired_strain_id = self._inherit_strain(parent_strain_id)
                    if not self._establish(
                        agent, pathogen_id, acquired_strain_id, p_dose, epoch,
                        resident=resident,
                    ):
                        continue

                    pw_doses = agent_pathway_doses.get(agent.agent_id, {})
                    dominant = max(pw_doses, key=pw_doses.get) if pw_doses else "unknown"
                    event = TransmissionEvent(
                        epoch=epoch,
                        pathway=dominant,
                        source_agent_id=source_agent_id,
                        target_agent_id=agent.agent_id,
                        zone=agent.current_location,
                        dose=p_dose,
                        source_strain_id=parent_strain_id or None,
                    )
                    events.append(event)
                    matrix.transmission_events.append({
                        "target_id": agent.agent_id,
                        "zone": agent.current_location,
                        "pathogen_id": pathogen_id,
                        "dominant_pathway": dominant,
                        "total_dose": round(p_dose, 4),
                        "superinfection": resident,
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
        self.collect_extinct_strains(agents)

        return matrix, events

    def _merge_pathogen_doses(
        self,
        agents: list[KorkinAgent],
        pathogen_id: str,
        p_agent_doses: dict[int, float],
        agent_doses: dict[int, float],
        agent_pathogen_doses: dict[int, dict[str, float]],
    ) -> dict[int, float]:
        """Scale one pathogen's doses by susceptibility and merge them in.

        Returns the per-agent susceptibility multipliers, so the strain-resolved
        shadow can be scaled by exactly the same factors.
        """
        susceptibility: dict[int, float] = {}
        for aid, dose in p_agent_doses.items():
            agent_obj = next((a for a in agents if a.agent_id == aid), None)
            mult = (
                agent_obj.susceptibility_multiplier.get(pathogen_id, 1.0)
                if agent_obj is not None else 1.0
            )
            susceptibility[aid] = mult
            scaled_dose = dose * mult
            agent_doses[aid] = agent_doses.get(aid, 0.0) + scaled_dose
            apd = agent_pathogen_doses.setdefault(aid, {})
            apd[pathogen_id] = apd.get(pathogen_id, 0.0) + scaled_dose
        return susceptibility

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
        ledger = StrainDoseLedger() if self.strain_tracking else None
        ec = profile.get("environmental_contamination", {})
        person_to_person = ec.get("person_to_person", True)

        if person_to_person:
            self._pathway_direct_contact(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )
            self._pathway_droplet(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        self._pathway_hvac_airborne(
            epoch, zone_occupants, p_mass,
            hvac_downstream_zones or {},
            p_agent_doses, matrix, events,
            p_agent_pw, pathogen_id=pathogen_id, ledger=ledger,
        )

        if person_to_person:
            self._pathway_fomite(
                epoch, zone_occupants, p_agent_doses, matrix, events,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        fc = profile.get("food_contamination", {})
        if fc.get("enabled", False):
            self._pathway_food_contamination(
                epoch, zone_occupants, p_agent_doses, matrix,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        if ec.get("enabled", False):
            self._pathway_environmental(
                zone_occupants, p_agent_doses, matrix,
                p_agent_pw, pathogen_id=pathogen_id, profile=profile,
                ledger=ledger,
            )

        self._apply_route_weights(profile, p_agent_doses, p_agent_pw)

        susceptibility = self._merge_pathogen_doses(
            agents, pathogen_id, p_agent_doses,
            agent_doses, agent_pathogen_doses,
        )

        self._fold_strain_doses(
            pathogen_id, ledger, self._route_weights(profile), susceptibility,
        )

        for aid, pw in p_agent_pw.items():
            merged = agent_pathway_doses.setdefault(aid, {})
            for pw_name, pw_dose in pw.items():
                key = f"{pw_name}:{pathogen_id}" if pathogen_id != "_default" else pw_name
                merged[key] = merged.get(key, 0.0) + pw_dose

    def _route_weights(self, profile: dict[str, Any] | None) -> dict[str, float]:
        """Resolve transmission_route_weights (identity default)."""
        raw = (profile or {}).get("transmission_route_weights")
        if not isinstance(raw, dict) or not raw:
            return dict(DEFAULT_ROUTE_WEIGHTS)
        weights = dict(DEFAULT_ROUTE_WEIGHTS)
        for key in DEFAULT_ROUTE_WEIGHTS:
            if key in raw:
                weights[key] = float(raw[key])
        return weights

    def _apply_route_weights(
        self,
        profile: dict[str, Any] | None,
        agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]],
    ) -> None:
        """Scale each pathway's dose contribution by pathogen route weights."""
        weights = self._route_weights(profile)
        if all(abs(weights[k] - 1.0) < 1e-15 for k in DEFAULT_ROUTE_WEIGHTS):
            return
        for aid, pw in agent_pathway_doses.items():
            total = 0.0
            for pw_name, pw_dose in pw.items():
                wkey = PATHWAY_WEIGHT_KEYS.get(pw_name, pw_name)
                w = float(weights.get(wkey, 1.0))
                scaled = pw_dose * w
                pw[pw_name] = scaled
                total += scaled
            agent_doses[aid] = total

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

    def _effective_contacts(self, n_occupants: int, agent: KorkinAgent) -> int:
        """Occupancy-scaled contact draw for density_dependent contact_mode.

        contacts ≈ base * (n / ref)^α, optionally multiplied for crew in
        Dining/Galley service zones, capped, then Poisson-sampled.
        """
        cfg = self.density_cfg
        ref = max(float(cfg["reference_occupancy"]), 1e-9)
        base = float(cfg["base_contacts"])
        alpha = float(cfg["exponent"])
        max_c = float(cfg["max_contacts"])

        raw = base * (max(n_occupants, 0) / ref) ** alpha
        loc = getattr(agent, "current_location", None) or ""
        if getattr(agent, "role", "") == "crew" and loc in self._service_zones:
            raw *= float(cfg.get("crew_contact_multiplier", 1.0))
        raw *= float(self.voyage_contact_multiplier)

        mean_contacts = min(raw, max_c)
        if mean_contacts <= 0.0:
            return 0
        # Cap again after the Poisson draw so max_contacts is a hard limit.
        return min(int(max_c), max(0, int(self.rng.poisson(mean_contacts))))

    def _draw_contact_multiplier(
        self,
        n_occupants: int,
        target: KorkinAgent,
    ) -> int:
        """Return r0_draw for direct contact under the active contact_mode."""
        if self.contact_mode in ("density_dependent", "heterogeneous_zone_dose"):
            return self._effective_contacts(n_occupants, target)
        base = int(self.rng.choice(AVG_R_POOL))
        # Legacy mode: still scale by voyage contact multiplier when active
        scaled = int(round(base * float(self.voyage_contact_multiplier)))
        return max(0, scaled)

    def _zone_exposure_sigma(self, zone_name: str) -> float:
        """Log-sigma for within-zone exposure heterogeneity."""
        # Galley / service names: high heterogeneity (plume / sequential contact).
        if "Galley" in zone_name:
            return max(0.0, self.heterogeneous_sigma_service)
        ztype = self.zone_types.get(zone_name, "")
        return max(
            0.0,
            float(
                self.heterogeneous_sigma_by_zone_type.get(
                    ztype,
                    self.heterogeneous_sigma_default,
                ),
            ),
        )

    def _zone_exposure_factor(self, zone_name: str) -> float:
        """Mean-1 lognormal within-zone exposure multiplier.

        Draws ``exp(N(-σ²/2, σ))`` so ``E[factor] = 1`` and the density-
        dependent mean dose is preserved in expectation.
        """
        sigma = self._zone_exposure_sigma(zone_name)
        if sigma <= 0.0:
            return 1.0
        mu = -0.5 * sigma * sigma
        return float(math.exp(self.rng.normal(mu, sigma)))

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
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Person-to-person transmission via close contact in shared rooms."""
        use_het = self.contact_mode == "heterogeneous_zone_dose"
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
            zone_mix = (
                None if cabin_confinement
                else self._shedder_mix(shedders, pathogen_id)
            )

            for target in susceptible:
                r0_draw = self._draw_contact_multiplier(n_occupants, target)
                dose = self._direct_contact_dose(
                    target, shedders, total_shedding, n_occupants, r0_draw,
                    cabin_confinement,
                )
                dose *= self.direct_contact_scalar
                dose *= zone_dc_factor
                exposure_factor = 1.0
                if use_het:
                    exposure_factor = self._zone_exposure_factor(zone_name)
                    dose *= exposure_factor
                mix = self._direct_contact_mix(
                    target, shedders, pathogen_id, zone_mix,
                )
                dose = self._accumulate(
                    target.agent_id, "direct_contact", dose,
                    agent_doses, agent_pathway_doses,
                    attribution(ledger, mix),
                )

                rec: dict[str, Any] = {
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "source_ids": shedder_ids,
                    "pathogen_id": pathogen_id,
                    "dose": round(dose, 4),
                    "occupant_count": len(occupants),
                    "r0_draw": r0_draw,
                }
                if use_het:
                    rec["zone_exposure_factor"] = round(exposure_factor, 6)
                matrix.shared_room_exposures.append(rec)

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
        ledger: StrainDoseLedger | None = None,
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
            mix = self._shedder_mix(shedders, pathogen_id)

            for target in susceptible:
                dose = concentration * volume * AEROSOL_INHALATION_FRACTION
                dose *= self.droplet_scalar
                dose *= vent_factor
                dose *= self._confinement_factor(target)
                dose = self._accumulate(
                    target.agent_id, "droplet", dose,
                    agent_doses, agent_pathway_doses,
                    attribution(ledger, mix),
                )

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
        source_attribution: DoseAttribution | None = None,
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
            dose = self._accumulate(
                target.agent_id, "hvac_airborne", dose,
                agent_doses, agent_pathway_doses, source_attribution,
            )

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
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Exposure from airborne pathogen drifted via HVAC from upstream zones.

        The dose is taken from the mass standing in the *target* zone, which is
        older than this epoch's shedding, so it is attributed to that zone's
        aerosol composition; the upstream shedders are the fallback for air whose
        history the composition does not yet cover.
        """
        zone_shedders: dict[str, list[tuple[KorkinAgent, float]]] = {}
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, None)
            if shedders:
                zone_shedders[zone_name] = shedders

        # For each downstream zone receiving HVAC air from a shedding zone
        for source_zone, shedders in zone_shedders.items():
            downstream = hvac_downstream_zones.get(source_zone, [])
            for target_zone in downstream:
                if target_zone == source_zone:
                    continue

                mass_in_target = zone_pathogen_mass.get(target_zone, 0.0)
                if mass_in_target <= 0:
                    continue

                mix = self._reservoir_mix(
                    AIRBORNE_RESERVOIR, pathogen_id, target_zone,
                ) or self._shedder_mix(shedders, pathogen_id)
                self._apply_hvac_downstream_doses(
                    target_zone, source_zone, [s.agent_id for s, _ in shedders],
                    mass_in_target,
                    zone_occupants, agent_doses, matrix,
                    agent_pathway_doses, pathogen_id,
                    attribution(ledger, mix),
                )

        self._airborne_composition(pathogen_id, zone_shedders)

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
        surface_attribution: DoseAttribution | None = None,
    ) -> None:
        if self._cabin_confinement_active(target):
            return
        if self.rng.random() > FOMITE_PICKUP_PROBABILITY:
            return

        dose = self._accumulate(
            target.agent_id, "fomite", surface_mass * FOMITE_TRANSFER_FRACTION,
            agent_doses, agent_pathway_doses, surface_attribution,
        )

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
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Surface contamination from shedders; stochastic pickup by later visitors."""
        dep_frac = SURFACE_DEPOSITION_FRACTION
        if profile:
            dep_frac = profile.get("surface_deposition_fraction", dep_frac)

        # a) Deposit new fomite mass from current shedders (not confined to cabin)
        for zone_name, occupants in zone_occupants.items():
            shedders = self._get_shedders(occupants, pathogen_id, profile)
            deposits: list[tuple[KorkinAgent, float]] = []
            for agent, sv in shedders:
                if self._cabin_confinement_active(agent):
                    continue
                deposit = sv * dep_frac
                deposits.append((agent, deposit))
                self.surface_pools[zone_name] = (
                    self.surface_pools.get(zone_name, 0.0) + deposit
                )
            self._deposit_reservoir_strains(
                SURFACE_RESERVOIR, pathogen_id, zone_name, deposits,
            )
            if self.strain_registry is not None:
                deposited_mass = sum(mass for _, mass in deposits)
                if deposited_mass > 0.0:
                    key = ReservoirComposition.key(
                        SURFACE_RESERVOIR, pathogen_id, zone_name,
                    )
                    self._surface_last_deposition_epoch[key] = int(epoch)

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
            surface_attribution = attribution(
                ledger,
                self._reservoir_mix(SURFACE_RESERVOIR, pathogen_id, zone_name),
            )

            for target in susceptible:
                self._apply_fomite_pickup(
                    target, zone_name, surface_mass,
                    prev_occupant_ids, prev_shedders,
                    agent_doses, matrix, agent_pathway_doses, pathogen_id,
                    surface_attribution,
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
        ledger: StrainDoseLedger | None = None,
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
            self._deposit_reservoir_strains(
                FOOD_RESERVOIR, pathogen_id, zone_name,
                [(a, sv * FOOD_DEPOSITION_FRACTION) for a, sv in shedders],
            )
            for _, sv in shedders:
                food_zones[zone_name] += sv * FOOD_DEPOSITION_FRACTION

            # Net growth (reproduction minus decay), applied to the pool and to
            # its composition together so the two stay proportional
            pool = food_zones[zone_name]
            if pool > 0:
                pool *= (1.0 + growth - decay)
                food_zones[zone_name] = max(pool, 0.0)
                self._reservoir.decay(
                    1.0 + growth - decay,
                    ReservoirComposition.key(
                        FOOD_RESERVOIR, pathogen_id, zone_name,
                    ),
                )

            if food_zones[zone_name] <= 0:
                continue

            # Dose to susceptible agents eating here
            susceptible = self._get_susceptible(occupants, pathogen_id)
            zone_mult = self._food_zone_multiplier(zone_name)
            food_attribution = attribution(
                ledger,
                self._reservoir_mix(FOOD_RESERVOIR, pathogen_id, zone_name),
            )
            for target in susceptible:
                dose = food_zones[zone_name] * FOOD_INGESTION_FRACTION * zone_mult
                dose = self._accumulate(
                    target.agent_id, "food", dose,
                    agent_doses, agent_pathway_doses, food_attribution,
                )

                matrix.food_contamination_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "food_pool_mass": round(food_zones[zone_name], 4),
                    "food_zone_multiplier": zone_mult,
                    "dose": round(dose, 4),
                })

    # ── Pathway 6: Environmental Source ─────────────────────────────

    def _zone_matches(self, zone_name: str, patterns: list[str]) -> bool:
        """True if zone_name matches any exact or fnmatch-style pattern."""
        for pat in patterns:
            if zone_name == pat or fnmatch.fnmatch(zone_name, pat):
                return True
        return False

    def _food_zone_multiplier(self, zone_name: str) -> float:
        """Food contamination dose multiplier for a Dining zone."""
        if zone_name in self.food_zone_multipliers:
            return float(self.food_zone_multipliers[zone_name])
        # Infer from dining_service_type if catalogued via zone name heuristics
        return 1.0

    def _pathway_environmental(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None = None,
        pathogen_id: str = "_default",
        profile: dict | None = None,
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Environmental source pathway (HVAC-systemic or zone-scoped).

        Legacy mode (no ``source_zones``): ship-wide HVAC biofilm load
        delivers to every zone. Zone-scoped mode: per-zone reservoirs in
        matching source zones with probabilistic exposure.
        """
        ec = (profile or {}).get("environmental_contamination", {})
        if not ec.get("enabled", False):
            return

        source_zones = ec.get("source_zones")
        if source_zones:
            self._pathway_environmental_zone_scoped(
                zone_occupants, agent_doses, matrix, agent_pathway_doses,
                pathogen_id=pathogen_id, profile=profile or {}, ledger=ledger,
            )
            return

        load = self.environmental_load.get(pathogen_id, 0.0)
        col_rate = ec.get("colonization_rate_per_epoch", 0.0)

        # Grow the HVAC biofilm load
        load *= (1.0 + col_rate)
        self.environmental_load[pathogen_id] = load

        if load <= 0:
            return

        env_attribution = self._environmental_attribution(
            ledger, pathogen_id, SHIP_WIDE_ZONE, load,
        )

        # Deliver to all zones (environmental pathogen is HVAC-systemic)
        for zone_name, occupants in zone_occupants.items():
            volume = self.zone_volumes.get(zone_name, 100.0)
            delivered = load * ENV_DELIVERY_FRACTION
            concentration = delivered / max(volume, 1.0)

            susceptible = self._get_susceptible(occupants, pathogen_id)
            for target in susceptible:
                dose = concentration * AEROSOL_INHALATION_FRACTION * volume
                dose *= self.hvac_airborne_scalar
                dose = self._accumulate(
                    target.agent_id, "environmental", dose,
                    agent_doses, agent_pathway_doses, env_attribution,
                )

                matrix.environmental_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "environmental_load": round(load, 4),
                    "delivered_mass": round(delivered, 4),
                    "dose": round(dose, 4),
                })

    def _pathway_environmental_zone_scoped(
        self,
        zone_occupants: dict[str, list[KorkinAgent]],
        agent_doses: dict[int, float],
        matrix: ContactTracingMatrix,
        agent_pathway_doses: dict[int, dict[str, float]] | None,
        *,
        pathogen_id: str,
        profile: dict[str, Any],
        ledger: StrainDoseLedger | None = None,
    ) -> None:
        """Per-zone environmental reservoirs (Legionella spa / C.diff spores)."""
        ec = profile.get("environmental_contamination", {})
        source_zones = list(ec.get("source_zones") or [])
        emission = float(ec.get("base_emission_rate", 0.001))
        p_expose = float(ec.get("exposure_probability_per_epoch", 0.1))
        spore_decay = float(ec.get("spore_decay_rate_per_epoch", 0.0))
        col_rate = float(ec.get("colonization_rate_per_epoch", 0.0))
        reservoirs = self.env_contamination.setdefault(pathogen_id, {})

        # Grow / decay matching zones; ensure keys exist for occupied matches
        for zone_name in zone_occupants:
            if not self._zone_matches(zone_name, source_zones):
                continue
            level = float(reservoirs.get(zone_name, 0.0))
            if level <= 0.0 and zone_name not in reservoirs:
                level = float(ec.get("baseline_environmental_load", 0.0))
            factor = (1.0 + col_rate) * max(0.0, 1.0 - spore_decay)
            deposited = self._update_env_reservoir_strains(
                pathogen_id, zone_name, level, factor,
                zone_occupants[zone_name], profile,
            )
            reservoirs[zone_name] = max(level * factor + deposited, 0.0)

        for zone_name, occupants in zone_occupants.items():
            if not self._zone_matches(zone_name, source_zones):
                continue
            contamination = float(reservoirs.get(zone_name, 0.0))
            if contamination <= 0.0:
                continue
            susceptible = self._get_susceptible(occupants, pathogen_id)
            env_attribution = self._environmental_attribution(
                ledger, pathogen_id, zone_name, contamination,
            )
            for target in susceptible:
                if self.rng.random() >= p_expose:
                    continue
                dose = self._accumulate(
                    target.agent_id, "environmental", contamination * emission,
                    agent_doses, agent_pathway_doses, env_attribution,
                )
                matrix.environmental_exposures.append({
                    "target_id": target.agent_id,
                    "zone": zone_name,
                    "pathogen_id": pathogen_id,
                    "environmental_load": round(contamination, 4),
                    "dose": round(dose, 4),
                    "zone_scoped": True,
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
        """Return agents this pathogen can still challenge.

        Naive agents always. Additionally, once variant surveillance is on: an
        already-infected agent when a second lineage can establish, and an
        immune agent when the pathogen has a ``cross_immunity`` matrix — an
        escape mutant that never reaches an immune host can never be seen to
        escape anything.
        """
        result = []
        challengeable = pathogen_id != "_default" and self.strain_registry is not None
        for a in occupants:
            if a.immune and not (
                challengeable and self._genotype_aware(pathogen_id)
            ):
                continue
            if pathogen_id == "_default":
                if a.infection_status == InfectionStatus.SUSCEPTIBLE:
                    result.append(a)
            elif not a.is_infected_with(pathogen_id) or (
                challengeable and self._superinfection_open(pathogen_id)
            ):
                result.append(a)
        return result

    def _genotype_aware(self, pathogen_id: str) -> bool:
        """True when this pathogen's immunity is genotype-specific."""
        config = self.strain_configs.get(pathogen_id)
        return config is not None and bool(config.cross_immunity)

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
        self._decay_surface_composition()

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
