#!/usr/bin/env python3
"""
orchestrator.py – The Master Intercom Loop  (Phase 4+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-pathogen concurrent simulation with microflora disruption:

1. **Real ABM Core (Korkin Lab infection-dynamics):**
   Agent graph with multi-pathogen co-infection tracking.

2. **Structural Environment (GRUMB):**
   Ship graph zones seeded with multi-kingdom log-ratio abundance arrays.
   Microflora disruption shifts detected via CLR-space anomaly scoring.

3. **Human Behavior (FRED reference):**
   Categorized background sick-call noise + quarantine compliance.

4. **Clinical Progression (EMOD reference):**
   Shedding-phase-gated RDT sensitivity with early/peak/late caps.

5. **Multi-Pathogen Engine:**
   Concurrent pathogen instances with separate mass pools per room.
   Dual-signal shedding: pathogen + altered microflora.

Usage::

    python orchestrator.py              # uses num_epochs from config.yaml (default 24)
    python orchestrator.py --epochs 250 # override to 250 epochs
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from telemetry_buffer.schema import (
    make_agent,
    make_ground_truth,
    make_space,
    read_ground_truth,
    write_ground_truth,
)
from crusher_labs import build_modalities, load_config
from crusher_labs.observation_core import (
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
    ClinicalRapidDiagnostic,
    ClinicalQPCR,
    ClinicalMicrobiology,
)
from crusher_labs.lab_notebook import (
    ArtificialLabNotebook,
    build_notebook_from_config,
    load_logging_profile,
)
from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    InfectionStatus,
    IllnessStatus,
    illness_probability,
)
from engines.py_contam_bridge import (
    build_transport_engine,
    ContamTransportEngine,
    load_air_flow_paths,
)
from engines.transmission_core import (
    TransmissionCore,
    build_hvac_downstream_map,
)
from crusher_labs.protocol_engine import (
    ProtocolEngine,
    compute_stoplights,
    load_protocols,
    apply_hvac_modifiers,
    apply_transmission_modifiers,
    reset_modifiers,
)
from crusher_labs.cost_ledger import (
    CostLedger,
    build_ledger_from_config,
    load_resource_costs,
)

# ── Trigger status constants ─────────────────────────────────────────────
STATUS_BASELINE = "BASELINE"
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"

# ── Defaults for configurable fractions (Law 1: no hardcoded ops) ────────
DEFAULT_AIRBORNE_FRACTION = 0.6
DEFAULT_SURFACE_FRACTION = 0.4
DEFAULT_GREYWATER_FRACTION = 0.1
DEFAULT_GRAYWATER_PROPAGATION_FACTOR = 0.3

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


# ── Simulation state container ───────────────────────────────────────────

@dataclass
class SimulationState:
    """Mutable state carried across epochs."""

    trigger_status: str = STATUS_BASELINE
    isolated_ids: set[int] = field(default_factory=set)
    quarantine_refusers: set[int] = field(default_factory=set)
    quarantine_order_epoch: dict[int, int] = field(default_factory=dict)
    escalation_log: list[dict[str, Any]] = field(default_factory=list)
    compliance_log: list[dict[str, Any]] = field(default_factory=list)
    simulation_history: list[dict[str, Any]] = field(default_factory=list)


# ── Spatial layout & ship graph ──────────────────────────────────────────

def _load_spatial_layout(cfg: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Load zones from the spatial layout JSON if configured."""
    graph_cfg = cfg.get("ship_graph", {})
    layout_path = graph_cfg.get("spatial_layout")
    if not layout_path:
        return None
    full_path = os.path.join(_REPO_ROOT, layout_path)
    if not os.path.isfile(full_path):
        return None
    with open(full_path, "r", encoding="utf-8") as fh:
        layout = json.load(fh)
    return [
        {
            "name": z["id"],
            "type": z["type"],
            "traffic": z.get("traffic", "medium"),
            "volume_m3": z.get("volume_m3", 100),
            "display": z.get("display", {}),
            "deck": z.get("deck", "main"),
        }
        for z in layout.get("zones", [])
    ]


def _initialize_ship_graph(cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the ship graph from spatial layout JSON or inline config.

    Returns zone list, agent role assignments, and traffic classifications.
    """
    graph_cfg = cfg.get("ship_graph", {})
    num_agents = graph_cfg.get("num_agents", 20)
    roles_cfg = graph_cfg.get("agent_roles", {})
    passenger_frac = roles_cfg.get("passenger_fraction", 0.70)

    spatial_zones = _load_spatial_layout(cfg)
    zones = spatial_zones if spatial_zones else graph_cfg.get("zones", [])

    agent_roles: dict[int, str] = {}
    for aid in range(num_agents):
        agent_roles[aid] = "passenger" if aid < int(num_agents * passenger_frac) else "crew"

    high_traffic = [z["name"] for z in zones if z.get("traffic") == "high"]
    zone_names = [z["name"] for z in zones]

    return {
        "zones": zones,
        "zone_names": zone_names,
        "high_traffic_zones": high_traffic,
        "num_agents": num_agents,
        "agent_roles": agent_roles,
    }


def _initialize_grumb_seeding(
    seq_modality: Any,
    zones: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Seed all spatial nodes with GRUMB multi-kingdom log-ratio arrays at t=0."""
    return seq_modality.seed_zones(zones)


# ── Korkin Lab engine helpers ────────────────────────────────────────────

def _build_engine(
    cfg: dict[str, Any],
    seed: int = 42,
) -> KorkinShipEngine:
    """Initialise the real infection-dynamics engine from config.

    Uses the ship_graph zones from spatial_layout.json (or inline
    fallback), mapping them to the Korkin Lab zone types.
    """
    graph_cfg = cfg.get("ship_graph", {})
    num_agents = graph_cfg.get("num_agents", 20)
    roles_cfg = graph_cfg.get("agent_roles", {})
    passenger_frac = roles_cfg.get("passenger_fraction", 0.70)
    num_passengers = int(num_agents * passenger_frac)
    num_crew = num_agents - num_passengers

    spatial_zones = _load_spatial_layout(cfg)
    zones = spatial_zones if spatial_zones else graph_cfg.get("zones", [])

    engine_zones = [
        {"name": z["name"], "type": z["type"], "capacity": z.get("traffic", "medium")}
        for z in zones
    ]

    return KorkinShipEngine(
        num_passengers=num_passengers,
        num_crew=num_crew,
        initial_infected=cfg.get("initial_infected", 1),
        zones=engine_zones,
        seed=seed,
    )


def _engine_payload_to_schema(
    engine_payload: dict[str, Any],
    isolated_ids: set[int],
    quarantine_refusers: set[int],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Convert Korkin engine output to telemetry_buffer schema format.

    Applies FRED compliance overrides for isolated / non-compliant agents.
    """
    agents_out: list[dict[str, Any]] = []
    for a in engine_payload["agents"]:
        aid = a["agent_id"]
        if aid in isolated_ids:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status="isolated",
                shedding_rate=0.0,
                location="Isolated_In_Quarters",
            )
        elif aid in quarantine_refusers:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status="non_compliant",
                shedding_rate=a.get("shedding_rate", 0.0),
                location=a.get("location", "unknown"),
            )
        else:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status=a["symptom_status"],
                shedding_rate=a.get("shedding_rate", 0.0),
                location=a.get("location"),
            )

        if "pathogen_infections" in a:
            agent_dict["pathogen_infections"] = a["pathogen_infections"]
        if "susceptibility_multiplier" in a:
            agent_dict["susceptibility_multiplier"] = a["susceptibility_multiplier"]
        if "microflora_disruption" in a:
            agent_dict["microflora_disruption"] = a["microflora_disruption"]

        agents_out.append(agent_dict)

    spaces_out: dict[str, dict[str, Any]] = {}
    for zname, zdata in engine_payload.get("spaces", {}).items():
        space_dict = make_space(
            pathogen_mass=zdata.get("pathogen_mass", 0.0),
            microbiome_id=zdata.get("microbiome_id", f"profile_{zname.lower()}"),
        )
        if "pathogen_mass_by_id" in zdata:
            space_dict["pathogen_mass_by_id"] = zdata["pathogen_mass_by_id"]
        spaces_out[zname] = space_dict

    return agents_out, spaces_out


# ── Escalation logic ────────────────────────────────────────────────────

def _check_escalation(
    trigger_status: str,
    syndromic_result: dict[str, Any],
    pcr_result: dict[str, Any] | None,
    cfg: dict[str, Any],
) -> str:
    """Evaluate trigger thresholds and return the (possibly updated) status."""
    esc_cfg = cfg.get("escalation", {})
    suspect_threshold = esc_cfg.get("syndromic_suspect_threshold", 3)
    confirm_ct = esc_cfg.get("pcr_confirm_ct_threshold", 35.0)

    if trigger_status == STATUS_BASELINE:
        if syndromic_result["sick_call_count"] >= suspect_threshold:
            return STATUS_SUSPECTED

    if trigger_status == STATUS_SUSPECTED and pcr_result is not None:
        for zone_data in pcr_result.get("zone_results", {}).values():
            ct = zone_data.get("ct_value")
            if ct is not None and ct <= confirm_ct:
                return STATUS_CONFIRMED

    return trigger_status


# ── Pathogen loading & initialization ────────────────────────────────────

def _load_pathogen_profiles(
    cfg: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Load multi-pathogen profiles from active_profiles.json."""
    mp_cfg = cfg.get("multi_pathogen", {})
    profiles_path = mp_cfg.get("profiles_path", "data/pathogens/active_profiles.json")
    full_path = os.path.join(_REPO_ROOT, profiles_path)
    if not os.path.isfile(full_path):
        return {}
    with open(full_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    profiles: dict[str, dict[str, Any]] = {}
    for p in data.get("pathogens", []):
        pid = p.get("pathogen_id", "unknown")
        profiles[pid] = p
    return profiles


def _init_multi_pathogen(
    engine: KorkinShipEngine,
    pathogen_profiles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
    rng: np.random.Generator,
) -> set[int]:
    """Initialize per-pathogen mass pools, susceptibility, and seed infections.

    Returns the set of immunocompromised agent IDs.
    """
    if not pathogen_profiles:
        return set()

    mp_cfg = cfg.get("multi_pathogen", {})

    for pid in pathogen_profiles:
        engine.initialize_pathogen(pid)

    imm_frac = mp_cfg.get("immunocompromised_fraction", 0.05)
    imm_mult = mp_cfg.get("immunocompromised_multiplier", 2.0)
    n_immunocompromised = int(len(engine.agents) * imm_frac)
    immunocompromised_ids: set[int] = set()

    for agent in engine.agents:
        for pid, prof in pathogen_profiles.items():
            base_susc = prof.get("base_susceptibility", 1.0)
            agent.init_pathogen_susceptibility(pid, base_susc)

    candidate_ids = [
        a.agent_id for a in engine.agents
        if not a.immune and a.infection_status == InfectionStatus.SUSCEPTIBLE
    ]
    if candidate_ids and n_immunocompromised > 0:
        chosen = rng.choice(
            candidate_ids,
            size=min(n_immunocompromised, len(candidate_ids)),
            replace=False,
        )
        for aid in chosen:
            immunocompromised_ids.add(int(aid))
            agent = engine.agents[int(aid)]
            for pid in pathogen_profiles:
                agent.susceptibility_multiplier[pid] = imm_mult

    # Seed initial infections per pathogen profile (epoch-0 introductions)
    for pid, prof in pathogen_profiles.items():
        intro_epoch = prof.get("introduction_epoch", 0)
        if intro_epoch == 0:
            n_init = prof.get("initial_infected", 1)
            candidates = [
                a for a in engine.agents
                if not a.immune
                and not a.is_infected_with(pid)
                and a.infection_status != InfectionStatus.RECOVERED
            ]
            if candidates:
                chosen = rng.choice(
                    candidates,
                    size=min(n_init, len(candidates)),
                    replace=False,
                )
                for agent in chosen:
                    agent.infect_with_pathogen(pid, 1e4, 0)
                    print(f"  Seeded {pid} → agent {agent.agent_id}")
    print()

    return immunocompromised_ids


# ── Observation engine initialization ────────────────────────────────────

@dataclass
class ObservationEngine:
    """Bundle of all six diagnostic instruments."""

    air_sniffer: ContinuousAirSniffer
    surface_swab: TargetedSurfaceSwab
    wastewater_seq: WastewaterSequencingGrid
    clin_rdt: ClinicalRapidDiagnostic
    clin_qpcr: ClinicalQPCR
    clin_microbio: ClinicalMicrobiology
    notebook: ArtificialLabNotebook
    fidelity_name: str
    lab_notebook_enabled: bool


def _init_observation_engine(
    cfg: dict[str, Any],
    seed: int,
) -> ObservationEngine:
    """Initialise all six diagnostic instruments and the lab notebook."""
    obs_cfg_path = os.path.join(_REPO_ROOT, "data", "config", "logging_profile.json")
    fidelity_name, fidelity, logging_config = load_logging_profile(obs_cfg_path)
    lab_notebook_enabled = logging_config.get("lab_notebook", {}).get("enabled", True)

    qc_cfg = logging_config.get("quality_control", {})
    xcontam_rate = qc_cfg.get("cross_contamination_rate", 0.0001)
    ctrl_intensity = qc_cfg.get("control_run_intensity", "medium")

    air_sniffer = ContinuousAirSniffer(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
    )
    surface_swab = TargetedSurfaceSwab(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
    )
    wastewater_seq = WastewaterSequencingGrid(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
    )
    clin_rdt = ClinicalRapidDiagnostic(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
    )
    clin_qpcr = ClinicalQPCR(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
    )
    clin_microbio = ClinicalMicrobiology(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
    )

    notebook = build_notebook_from_config(obs_cfg_path)

    _print_observation_engine(fidelity_name, xcontam_rate, ctrl_intensity, lab_notebook_enabled)

    return ObservationEngine(
        air_sniffer=air_sniffer,
        surface_swab=surface_swab,
        wastewater_seq=wastewater_seq,
        clin_rdt=clin_rdt,
        clin_qpcr=clin_qpcr,
        clin_microbio=clin_microbio,
        notebook=notebook,
        fidelity_name=fidelity_name,
        lab_notebook_enabled=lab_notebook_enabled,
    )


# ── Protocol engine initialization ───────────────────────────────────────

@dataclass
class ProtocolContext:
    """Bundle of the reactive protocol engine and cost ledger."""

    protocol_engine: ProtocolEngine
    cost_ledger: CostLedger
    resource_costs_cfg: dict[str, Any]
    standing_protocols: list[Any]
    original_filter_eff: float


def _init_protocol_engine(
    cfg: dict[str, Any],
    contam_engine: ContamTransportEngine | None,
) -> ProtocolContext:
    """Initialise the reactive protocol engine and cost ledger."""
    protocols_cfg_path = os.path.join(_REPO_ROOT, "data", "config", "protocols.json")
    resource_cfg_path = os.path.join(_REPO_ROOT, "data", "config", "resource_costs.json")

    cost_ledger = build_ledger_from_config(resource_cfg_path)
    resource_costs_cfg = load_resource_costs(resource_cfg_path)
    standing_protocols = load_protocols(protocols_cfg_path)
    protocol_engine = ProtocolEngine(standing_protocols, cost_ledger)

    original_filter_eff = (
        contam_engine.filter_efficiency if contam_engine is not None else 0.50
    )

    _print_protocol_engine(standing_protocols, cost_ledger)

    return ProtocolContext(
        protocol_engine=protocol_engine,
        cost_ledger=cost_ledger,
        resource_costs_cfg=resource_costs_cfg,
        standing_protocols=standing_protocols,
        original_filter_eff=original_filter_eff,
    )


# ── Microflora disruption ───────────────────────────────────────────────

def _compute_zone_microflora_shifts(
    agents: list,
    pathogen_profiles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, dict[str, float]]:
    """Compute per-zone microflora disruption shift magnitudes.

    For each zone, aggregate the microflora disruption from all agents
    with active disruption status, producing a dict of
    {zone: {disruption_type: magnitude}} for feeding into the GRUMB
    sequencing modality.
    """
    mf_cfg = cfg.get("microflora", {})
    shed_mass = mf_cfg.get("disrupted_shed_mass", 50.0)
    graywater_zones = mf_cfg.get("graywater_zones", [])
    gw_factor = mf_cfg.get(
        "graywater_propagation_factor", DEFAULT_GRAYWATER_PROPAGATION_FACTOR,
    )

    zone_shifts: dict[str, dict[str, float]] = {}

    for agent in agents:
        if agent.microflora_disruption_status <= 0:
            continue
        loc = agent.current_location
        if loc == "Isolated_In_Quarters":
            continue

        for pid in agent.active_pathogen_ids:
            profile = pathogen_profiles.get(pid, {})
            mf = profile.get("microflora_disruption", {})
            if not mf.get("causes_disruption", False):
                continue
            d_type = mf.get("disruption_type", "gastrointestinal")
            mag = agent.microflora_disruption_status * shed_mass / 100.0

            zs = zone_shifts.setdefault(loc, {})
            zs[d_type] = zs.get(d_type, 0.0) + mag

            for gz in graywater_zones:
                gzs = zone_shifts.setdefault(gz, {})
                gzs[d_type] = gzs.get(d_type, 0.0) + mag * gw_factor

    return zone_shifts


# ── Per-epoch steps ──────────────────────────────────────────────────────

def _step_fred_compliance(
    epoch: int,
    state: SimulationState,
    syndromic: Any,
) -> None:
    """FRED compliance check for pending quarantine orders."""
    for aid in list(state.quarantine_refusers):
        epochs_since = epoch - state.quarantine_order_epoch.get(aid, epoch)
        if syndromic.check_quarantine_compliance(aid, epochs_since):
            state.quarantine_refusers.discard(aid)
            state.isolated_ids.add(aid)
            state.compliance_log.append({
                "epoch": epoch, "agent_id": aid,
                "action": "delayed_compliance",
                "delay": epochs_since,
            })


def _step_mid_cruise_introductions(
    epoch: int,
    engine: KorkinShipEngine,
    pathogen_profiles: dict[str, dict[str, Any]],
    rng: np.random.Generator,
) -> None:
    """Introduce new pathogens at their scheduled introduction_epoch."""
    if not pathogen_profiles:
        return
    for pid, prof in pathogen_profiles.items():
        intro_epoch = prof.get("introduction_epoch", 0)
        if intro_epoch == epoch and epoch > 0:
            n_init = prof.get("initial_infected", 1)
            candidates = [
                a for a in engine.agents
                if not a.immune
                and not a.is_infected_with(pid)
                and a.infection_status != InfectionStatus.RECOVERED
                and a.current_location != "Isolated_In_Quarters"
            ]
            if candidates:
                chosen = rng.choice(
                    candidates,
                    size=min(n_init, len(candidates)),
                    replace=False,
                )
                for agent in chosen:
                    agent.infect_with_pathogen(pid, 1e4, epoch)


def _step_infection_progression(
    engine: KorkinShipEngine,
    pathogen_profiles: dict[str, dict[str, Any]],
) -> None:
    """Advance multi-pathogen infection, illness, recovery, and mass accumulation."""
    if not pathogen_profiles:
        return

    for agent in engine.agents:
        for pid, inf in list(agent.infections.items()):
            if inf["status"] != InfectionStatus.INFECTED:
                continue
            prof = pathogen_profiles.get(pid, {})

            if inf["time_infected"] is not None:
                inf["time_infected"] += 1

            dpi = inf["time_infected"] or 0
            if dpi >= 1 and inf["illness"] == IllnessStatus.NOT_ILL:
                ill_params = prof.get("illness_probability", {})
                eta_p = ill_params.get("eta", 0.508)
                gamma_p = ill_params.get("gamma", 0.095)
                dose = inf["acquired_particles"]
                ill_prob = 1.0 - math.pow(1.0 + eta_p * dose, -gamma_p)
                if ill_prob > 0.3:
                    inf["illness"] = IllnessStatus.SYMPTOMATIC
                    if agent.illness_status == IllnessStatus.NOT_ILL:
                        agent.illness_status = IllnessStatus.SYMPTOMATIC

            recovery_day = prof.get("recovery_day", 3)
            if dpi >= recovery_day:
                inf["status"] = InfectionStatus.RECOVERED
                inf["illness"] = IllnessStatus.RECOVERED

        any_active = any(
            inf["status"] == InfectionStatus.INFECTED
            for inf in agent.infections.values()
        )
        if agent.infections and not any_active:
            if agent.infection_status == InfectionStatus.INFECTED:
                agent.infection_status = InfectionStatus.RECOVERED
                agent.illness_status = IllnessStatus.RECOVERED

        agent.update_microflora_disruption(pathogen_profiles)

    # Per-pathogen mass accumulation
    for pid, prof in pathogen_profiles.items():
        dep_frac = prof.get("surface_deposition_fraction", 1e-4)
        masses = engine.get_pathogen_zone_mass(pid)
        for agent in engine.agents:
            sv = agent.get_pathogen_shedding(pid, prof)
            if sv > 0:
                loc = agent.current_location
                if loc in masses:
                    masses[loc] += sv * dep_frac
        engine.set_pathogen_zone_mass(pid, masses)


def _run_observation_sampling(
    epoch: int,
    obs: ObservationEngine,
    agents: list[dict[str, Any]],
    spaces: dict[str, dict[str, Any]],
    zone_names: list[str],
    zone_volumes: dict[str, float],
    zone_microflora_shifts: dict[str, dict[str, float]],
    trigger_status: str,
    high_traffic: list[str],
    syn_result: dict[str, Any],
    engine: KorkinShipEngine,
    pathogen_profiles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
]:
    """Run all six observation instruments for a single epoch.

    Returns (air_results, swab_results, ww_results,
             clin_rdt_results, clin_qpcr_results, clin_microbio_results).
    """
    mf_cfg = cfg.get("microflora", {})
    airborne_frac = mf_cfg.get("airborne_fraction", DEFAULT_AIRBORNE_FRACTION)
    surface_frac = mf_cfg.get("surface_fraction", DEFAULT_SURFACE_FRACTION)
    greywater_frac = mf_cfg.get("greywater_fraction", DEFAULT_GREYWATER_FRACTION)

    zone_airborne: dict[str, float] = {}
    zone_surface: dict[str, float] = {}
    for zname, zdata in spaces.items():
        total_mass = zdata.get("pathogen_mass", 0.0)
        zone_airborne[zname] = total_mass * airborne_frac
        zone_surface[zname] = total_mass * surface_frac

    air_results = obs.air_sniffer.sample_all_zones(zone_airborne, zone_volumes)

    fred_compliance = cfg.get("fred_behavior", {}).get("quarantine_compliance", 0.85)
    swab_targets = None
    if trigger_status in (STATUS_SUSPECTED, STATUS_CONFIRMED):
        swab_targets = high_traffic if trigger_status == STATUS_SUSPECTED else zone_names
    swab_results = obs.surface_swab.swab_zones(
        zone_surface, fred_compliance, target_zones=swab_targets,
    )

    # Wastewater: combine pathogen mass + microflora shifts
    ww_pathogen_mass: dict[str, float] = {}
    for zname in zone_names:
        ww_pathogen_mass[zname] = zone_surface.get(zname, 0.0) * greywater_frac
    ww_microflora: dict[str, dict[str, float]] = {}
    for zname, mf_data in zone_microflora_shifts.items():
        ww_microflora[zname] = mf_data
    ww_per_pathogen = (
        {pid: engine.get_pathogen_zone_mass(pid) for pid in pathogen_profiles}
        if pathogen_profiles else None
    )
    graywater_zones = mf_cfg.get("graywater_zones", [])
    ww_target_zones = graywater_zones if graywater_zones else zone_names
    ww_results = obs.wastewater_seq.sample_all_zones(
        ww_pathogen_mass, ww_microflora,
        pathogen_mass_by_id=ww_per_pathogen,
        wastewater_zones=ww_target_zones,
    )

    # Individual patient clinical diagnostics (Sick Call)
    sick_call_agents = [
        a for a in agents
        if a["agent_id"] in syn_result.get("sick_call_agents", [])
    ]
    clin_rdt_results: dict[int, dict[str, Any]] = {}
    clin_qpcr_results: dict[int, dict[str, Any]] = {}
    clin_microbio_results: dict[int, dict[str, Any]] = {}

    if sick_call_agents:
        clin_rdt_results = obs.clin_rdt.test_sick_call_agents(sick_call_agents)
        clin_qpcr_results = obs.clin_qpcr.test_sick_call_agents(sick_call_agents)
        clin_microbio_results = obs.clin_microbio.test_sick_call_agents(sick_call_agents)

    # Log instrument results to lab notebook
    obs.notebook.log_air_sniffer(epoch, air_results)
    obs.notebook.log_surface_swab(epoch, swab_results)
    obs.notebook.log_wastewater_seq(epoch, ww_results)
    obs.notebook.log_clinical_rdt(epoch, clin_rdt_results)
    obs.notebook.log_clinical_qpcr(epoch, clin_qpcr_results)
    obs.notebook.log_clinical_microbiology(epoch, clin_microbio_results)
    obs.notebook.log_agent_summary(epoch, agents)

    return (
        air_results, swab_results, ww_results,
        clin_rdt_results, clin_qpcr_results, clin_microbio_results,
    )


def _step_quarantine_confinement(
    epoch: int,
    agents: list[dict[str, Any]],
    merged_mods: dict[str, Any],
    trigger_status: str,
    state: SimulationState,
    syndromic: Any,
) -> None:
    """Apply quarantine confinement from protocol modifiers or legacy CONFIRMED fallback."""
    # Protocol-driven confinement
    if merged_mods.get("confine_symptomatic_to_quarters", False):
        _confine_agents(epoch, agents, state, syndromic, include_shedding=False)
        return

    # Legacy CONFIRMED → quarantine fallback (when no protocol sets the key)
    if trigger_status == STATUS_CONFIRMED:
        _confine_agents(epoch, agents, state, syndromic, include_shedding=True)


def _confine_agents(
    epoch: int,
    agents: list[dict[str, Any]],
    state: SimulationState,
    syndromic: Any,
    include_shedding: bool,
) -> None:
    """Confine symptomatic (and optionally shedding) agents to quarters."""
    for agent in agents:
        aid = agent["agent_id"]
        if aid in state.isolated_ids or aid in state.quarantine_refusers:
            continue
        is_symptomatic = agent["symptom_status"] in ("symptomatic", "non_compliant")
        is_shedding = include_shedding and agent.get("shedding_rate", 0.0) > 0.0
        if not (is_symptomatic or is_shedding):
            continue
        if syndromic.check_quarantine_compliance(aid, 0):
            state.isolated_ids.add(aid)
            state.compliance_log.append({
                "epoch": epoch, "agent_id": aid,
                "action": "immediate_compliance",
            })
        else:
            state.quarantine_refusers.add(aid)
            state.quarantine_order_epoch[aid] = epoch
            state.compliance_log.append({
                "epoch": epoch, "agent_id": aid,
                "action": "refused_quarantine",
            })


def _step_cost_accounting(
    epoch: int,
    proto_ctx: ProtocolContext,
    air_results: dict,
    swab_results: dict,
    ww_results: dict,
    clin_rdt_results: dict,
    clin_qpcr_results: dict,
    clin_microbio_results: dict,
) -> None:
    """Debit baseline surveillance and per-test costs for one epoch."""
    ledger = proto_ctx.cost_ledger
    resource_costs_cfg = proto_ctx.resource_costs_cfg

    baseline_costs = resource_costs_cfg.get("baseline_surveillance_costs_per_epoch", {})
    ledger.debit_baseline_surveillance(epoch, baseline_costs)

    per_test = resource_costs_cfg.get("per_test_costs", {})
    ledger.debit_per_test(epoch, "air_sniffer_sample", len(air_results), per_test)
    ledger.debit_per_test(epoch, "surface_swab", len(swab_results), per_test)
    ledger.debit_per_test(epoch, "wastewater_sequencing", len(ww_results), per_test)
    n_sick = len(clin_rdt_results)
    ledger.debit_per_test(epoch, "clinical_rdt", n_sick, per_test)
    ledger.debit_per_test(epoch, "clinical_qpcr", n_sick, per_test)
    ledger.debit_per_test(epoch, "clinical_microbiology", n_sick, per_test)


# ── Epoch history recording ──────────────────────────────────────────────

def _record_epoch(
    epoch: int,
    trigger_status: str,
    agents: list[dict[str, Any]],
    spaces: dict[str, dict[str, Any]],
    engine: KorkinShipEngine,
    contam_engine: ContamTransportEngine | None,
    pathogen_profiles: dict[str, dict[str, Any]],
    zone_names: list[str],
    zone_microflora_shifts: dict[str, dict[str, float]],
    syn_result: dict[str, Any],
    rdt_result: dict[str, Any],
    pcr_result: dict[str, Any] | None,
    seq_result: dict[str, Any] | None,
    tracing_matrix: Any,
    state: SimulationState,
    obs: ObservationEngine,
    active_mods: list[dict[str, Any]],
    merged_mods: dict[str, Any],
    stoplights: dict[str, dict[str, str]],
    epoch_cost: dict[str, Any],
    cfg: dict[str, Any],
    air_results: dict[str, dict[str, Any]],
    swab_results: dict[str, dict[str, Any]],
    ww_results: dict[str, dict[str, Any]],
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
    clin_microbio_results: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Build a complete epoch record for simulation_history."""
    # Multi-pathogen summary
    multi_pathogen_summary: dict[str, dict[str, int]] = {}
    if pathogen_profiles:
        for pid in pathogen_profiles:
            mp_s = {"infected": 0, "symptomatic": 0, "recovered": 0}
            for agent in engine.agents:
                inf = agent.infections.get(pid)
                if inf is None:
                    continue
                if inf["status"] == InfectionStatus.INFECTED:
                    mp_s["infected"] += 1
                    if inf["illness"] == IllnessStatus.SYMPTOMATIC:
                        mp_s["symptomatic"] += 1
                elif inf["status"] == InfectionStatus.RECOVERED:
                    mp_s["recovered"] += 1
            multi_pathogen_summary[pid] = mp_s

    disrupted_count = sum(
        1 for a in engine.agents if a.microflora_disruption_status > 0
    )

    epoch_record: dict[str, Any] = {
        "epoch": epoch,
        "trigger_status": trigger_status,
        "agents": [],
        "spaces": {},
        "summary": {
            "susceptible": 0,
            "infected": 0,
            "symptomatic": 0,
            "recovered": 0,
            "immune": 0,
            "isolated": len(state.isolated_ids),
            "quarantine_refusers": len(state.quarantine_refusers),
            "sick_call_count": syn_result["sick_call_count"],
            "disrupted_microflora_count": disrupted_count,
        },
        "multi_pathogen": multi_pathogen_summary,
        "microflora_shifts": {},
        "hvac": {
            "filter_type": cfg.get("hvac", {}).get("filter_type", "none"),
            "filter_efficiency": (
                contam_engine.filter_efficiency if contam_engine else 0.0
            ),
            "transport_active": contam_engine is not None,
        },
        "contact_tracing": tracing_matrix.to_dict(),
        "crusher_ops": {
            "surface_wipe_zones": [],
            "pcr_results": {},
            "rdt_positive_count": sum(1 for r in rdt_result["results"] if r["positive"]),
            "rdt_tested_count": rdt_result["tested_count"],
        },
    }

    for a in agents:
        status = a["symptom_status"]
        if status == "isolated":
            pass
        elif status in ("symptomatic", "non_compliant", "asymptomatic_shedding"):
            epoch_record["summary"]["infected"] += 1
            if status == "symptomatic":
                epoch_record["summary"]["symptomatic"] += 1
        elif status == "recovered":
            epoch_record["summary"]["recovered"] += 1
        elif status == "immune":
            epoch_record["summary"]["immune"] += 1
        else:
            epoch_record["summary"]["susceptible"] += 1

        agent_record: dict[str, Any] = {
            "agent_id": a["agent_id"],
            "status": status,
            "shedding_rate": a.get("shedding_rate", 0.0),
            "location": a.get("location", "unknown"),
        }
        if pathogen_profiles:
            agent_record["pathogen_infections"] = a.get("pathogen_infections", {})
            agent_record["susceptibility_multiplier"] = a.get("susceptibility_multiplier", {})
            agent_record["microflora_disruption"] = a.get("microflora_disruption", 0.0)
        epoch_record["agents"].append(agent_record)

    for zname, zdata in spaces.items():
        zone_entry: dict[str, Any] = {
            "pathogen_mass": zdata.get("pathogen_mass", 0.0),
        }
        if pathogen_profiles:
            zone_entry["pathogen_mass_by_id"] = zdata.get("pathogen_mass_by_id", {})
        if contam_engine is not None:
            node = contam_engine.zone_nodes.get(zname)
            if node is not None:
                zone_entry["concentration_per_m3"] = round(
                    node.concentration(zdata.get("pathogen_mass", 0.0)), 3,
                )
                zone_entry["volume_m3"] = node.volume_m3
        epoch_record["spaces"][zname] = zone_entry

    # Log microflora shifts per room-epoch
    for zname in zone_names:
        mf_shift = zone_microflora_shifts.get(zname, {})
        if mf_shift:
            epoch_record["microflora_shifts"][zname] = {
                "disruption_types": list(mf_shift.keys()),
                "magnitudes": {k: round(v, 4) for k, v in mf_shift.items()},
                "total_magnitude": round(sum(mf_shift.values()), 4),
            }

    # Log sequencing microflora anomaly results
    if seq_result is not None:
        epoch_record["microflora_sequencing"] = {}
        for zname, zr in seq_result.get("zone_results", {}).items():
            mf_data = zr.get("microflora_disruption", {})
            if mf_data.get("total_disruption_magnitude", 0) > 0:
                epoch_record["microflora_sequencing"][zname] = mf_data

    if pcr_result is not None:
        epoch_record["crusher_ops"]["surface_wipe_zones"] = list(
            pcr_result.get("zone_results", {}).keys()
        )
        for zname, zdata in pcr_result.get("zone_results", {}).items():
            epoch_record["crusher_ops"]["pcr_results"][zname] = {
                "ct_value": zdata.get("ct_value"),
                "detected": zdata.get("detected", False),
            }

    epoch_record["crusher_ops"]["isolated_agents"] = sorted(state.isolated_ids)

    # Observation Engine instrument records
    epoch_record["observation_engine"] = {
        "air_sniffer": air_results,
        "surface_swab": swab_results,
        "wastewater_sequencing": ww_results,
        "clinical_rdt": clin_rdt_results,
        "clinical_qpcr": clin_qpcr_results,
        "clinical_microbiology": clin_microbio_results,
        "logging_fidelity": obs.fidelity_name,
    }

    # Protocol engine + cost accounting
    epoch_record["reactive_protocols"] = {
        "active_protocols": [
            {"protocol_id": m["protocol_id"], "name": m["name"],
             "newly_activated": m["newly_activated"]}
            for m in active_mods
        ],
        "merged_modifiers": merged_mods,
        "stoplights": stoplights,
    }
    epoch_record["cost_accounting"] = epoch_cost

    return epoch_record


# ── Finalization ─────────────────────────────────────────────────────────

def _finalize_simulation(
    state: SimulationState,
    engine: KorkinShipEngine,
    obs: ObservationEngine,
    proto_ctx: ProtocolContext,
    pathogen_profiles: dict[str, dict[str, Any]],
    zone_names: list[str],
    num_agents: int,
    num_epochs: int,
    contam_engine: ContamTransportEngine | None,
    cfg: dict[str, Any],
) -> None:
    """Save simulation history, lab notebook, and print executive summary."""
    # Save simulation history
    history_path = os.path.join(
        _REPO_ROOT, "telemetry_buffer", "simulation_history.json",
    )
    with open(history_path, "w", encoding="utf-8") as fh:
        json.dump(state.simulation_history, fh, indent=2)
    print(f"\n  Simulation history saved to: {history_path}")

    # Serialize the Artificial Lab Notebook
    logging_config_path = os.path.join(_REPO_ROOT, "data", "config", "logging_profile.json")
    _, _, logging_config = load_logging_profile(logging_config_path)

    if obs.lab_notebook_enabled:
        obs.notebook.set_run_metadata(
            num_agents=num_agents,
            num_epochs=num_epochs,
            pathogens=list(pathogen_profiles.keys()) if pathogen_profiles else [],
            zones=zone_names,
            trigger_timeline=state.escalation_log,
        )
        nb_output = logging_config.get("lab_notebook", {}).get(
            "output_path", "telemetry_buffer/artificial_lab_notebook.json",
        )
        nb_path = os.path.join(_REPO_ROOT, nb_output)
        financial_audit = proto_ctx.cost_ledger.generate_financial_audit()
        protocol_summary = proto_ctx.protocol_engine.generate_protocol_summary()
        obs.notebook.serialize(
            nb_path,
            financial_audit=financial_audit,
            protocol_summary=protocol_summary,
        )
        print(f"  Lab notebook saved to: {nb_path} ({len(obs.notebook.records)} records)")

    # Executive Summary
    final_summary = engine.get_summary()
    audit = proto_ctx.cost_ledger.generate_financial_audit()
    proto_summary = proto_ctx.protocol_engine.generate_protocol_summary()

    _print_executive_summary(
        num_agents=num_agents,
        num_epochs=num_epochs,
        engine_summary=final_summary,
        audit=audit,
        proto_summary=proto_summary,
        escalation_log=state.escalation_log,
        compliance_log=state.compliance_log,
        trigger_status=state.trigger_status,
        isolated_count=len(state.isolated_ids),
        refuser_count=len(state.quarantine_refusers),
        contam_engine=contam_engine,
        zone_pathogen_mass=engine.zone_pathogen_mass,
        hvac_cfg=cfg.get("hvac", {}),
        pathogen_profiles=pathogen_profiles,
    )


# ── Display / print helpers ──────────────────────────────────────────────

def _print_initialization(
    ship: dict[str, Any],
    seeds: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> None:
    """Print the t=0 initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  INITIALIZATION  ·  Ship Graph + GRUMB Seeding + FRED/EMOD Params")
    print(thin)

    print(f"\n  Ship graph: {ship['num_agents']} agents  "
          f"({sum(1 for r in ship['agent_roles'].values() if r == 'passenger')} passengers, "
          f"{sum(1 for r in ship['agent_roles'].values() if r == 'crew')} crew)")
    print(f"  Zones: {', '.join(ship['zone_names'])}")
    print(f"  High-traffic: {', '.join(ship['high_traffic_zones'])}")

    print(f"\n  GRUMB multi-kingdom seeding (t=0):")
    for zone_name, seed in seeds.items():
        kf = seed["kingdom_fractions"]
        kf_str = "  ".join(f"{k}={v:.3f}" for k, v in kf.items())
        print(f"    {zone_name:15s} [{seed['zone_type']:7s}]  {kf_str}")

    fred_cfg = cfg.get("fred_behavior", {})
    print(f"\n  FRED behavioral params:")
    print(f"    Quarantine compliance:   {fred_cfg.get('quarantine_compliance', 0.85):.0%}")
    print(f"    Compliance delay:        {fred_cfg.get('compliance_delay_epochs', 1)} epoch(s)")
    cats = fred_cfg.get("healthy_noise_categories", [])
    for cat in cats:
        print(f"    Noise: {cat['reason']:15s}  P={cat['probability']:.3f}")

    emod_cfg = cfg.get("emod_progression", {})
    phases = emod_cfg.get("shedding_phases", [])
    print(f"\n  EMOD clinical progression:")
    print(f"    Incubation:  {emod_cfg.get('incubation_epochs', 2)} epochs")
    for ph in phases:
        print(f"    Phase {ph['name']:6s}  max_rate={ph['max_rate']:5.1f}  "
              f"sensitivity_cap={ph['sensitivity_cap']:.2f}")

    print(thin)
    print()


def _print_korkin_engine(engine: KorkinShipEngine) -> None:
    """Print Korkin Lab engine initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  KORKIN LAB ENGINE  ·  infection-dynamics ABM initialized")
    print(thin)
    engine_summary = engine.get_summary()
    print(f"\n  Population: {engine_summary['total']} agents "
          f"({engine.num_passengers} passengers, {engine.num_crew} crew)")
    print(f"  Immune (negative secretors): {engine_summary['immune']}")
    print(f"  Initial infected: {engine_summary['infected']}")
    print(f"  Zones: {', '.join(z['name'] for z in engine.zones)}")
    print(f"  VSP isolation: {'enabled' if engine.vsp_isolation else 'disabled'}")
    print()


def _print_contam_engine(
    contam_engine: ContamTransportEngine | None,
    engine: KorkinShipEngine,
    cfg: dict[str, Any],
) -> None:
    """Print CONTAM transport engine initialization summary."""
    thin = "─" * 80
    if contam_engine is not None:
        hvac_cfg = cfg.get("hvac", {})
        filter_type = hvac_cfg.get("filter_type", "MERV-13")
        print(thin)
        print("  CONTAM TRANSPORT ENGINE  ·  py-contam multi-zone airflow initialized")
        print(thin)
        transport_summary = contam_engine.get_transport_summary(engine.zone_pathogen_mass)
        print(f"\n  Filter type:        {filter_type}")
        print(f"  Filter efficiency:  {contam_engine.filter_efficiency:.1%}")
        print(f"  Natural decay rate: {contam_engine.natural_decay_rate:.1%} per epoch")
        print(f"  HVAC-ducted paths:  {transport_summary['total_hvac_paths']}")
        print(f"  Passive paths:      {transport_summary['total_passive_paths']}")
        print(f"  Zone nodes:         {len(contam_engine.zone_nodes)}")
        print()
    else:
        print("  [WARN] CONTAM transport engine not available – using legacy flat decay")
        print()


def _print_multi_pathogen(
    pathogen_profiles: dict[str, dict[str, Any]],
    immunocompromised_ids: set[int],
    engine: KorkinShipEngine,
    imm_mult: float,
    enable_dual_signal: bool,
) -> None:
    """Print multi-pathogen engine initialization summary."""
    thin = "─" * 80
    if pathogen_profiles:
        print(thin)
        print("  MULTI-PATHOGEN ENGINE  ·  active profiles loaded")
        print(thin)
        for pid, prof in pathogen_profiles.items():
            print(f"    {pid:20s}  {prof['name']}")
            print(f"      Category: {prof.get('category', '?')}")
            print(f"      Routes:   {', '.join(prof.get('transmission_routes', []))}")
            intro = prof.get("introduction_epoch", 0)
            print(f"      Intro:    epoch {intro}")
            mf = prof.get("microflora_disruption", {})
            if mf.get("causes_disruption"):
                print(f"      Microflora disruption: {mf.get('disruption_type')} "
                      f"(mag={mf.get('disruption_magnitude', 0)})")
        print()
        print(f"  Immunocompromised agents: {len(immunocompromised_ids)}/{len(engine.agents)} "
              f"(mult={imm_mult}x)")
        print(f"  Dual-signal shedding: {'enabled' if enable_dual_signal else 'disabled'}")
        print()


def _print_transmission_core(
    hvac_downstream: dict[str, list[str]],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> None:
    """Print transmission core initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  TRANSMISSION CORE  ·  four-pathway model initialized")
    print(thin)
    print("    1. Direct Contact      (zone-colocation, avgR scaling)")
    print("    2. Short-Range Droplet (immediate room aerosol)")
    print("    3. Long-Range Airborne (HVAC drift via py-contam)")
    print("    4. Fomite Deposition   (surface pools + stochastic pickup)")
    print(f"   HVAC downstream links: {sum(len(v) for v in hvac_downstream.values())}")
    if pathogen_profiles:
        print(f"   Active pathogens: {', '.join(pathogen_profiles.keys())}")
    print()


def _print_observation_engine(
    fidelity_name: str,
    xcontam_rate: float,
    ctrl_intensity: str,
    lab_notebook_enabled: bool,
) -> None:
    """Print observation engine initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  OBSERVATION ENGINE  ·  instrument-level diagnostics initialized")
    print(thin)
    print(f"    ENV 1. Continuous Air Sniffer   (aerosol Ct)")
    print(f"    ENV 2. Targeted Surface Swab    (fomite PCR + compliance variance)")
    print(f"    ENV 3. Wastewater Seq Grid      (Dirichlet-multinomial metagenomics)")
    print(f"    CLN 4. Clinical RDT             (lateral-flow antigen, binary)")
    print(f"    CLN 5. Clinical qPCR            (patient viral load Ct)")
    print(f"    CLN 6. Clinical Microbiology    (culture/staining, flora shifts)")
    print(f"   Logging fidelity:   {fidelity_name}")
    print(f"   Cross-contamination: {xcontam_rate:.4%} carryover")
    print(f"   QC control intensity: {ctrl_intensity}")
    print(f"   Lab notebook: {'enabled' if lab_notebook_enabled else 'disabled'}")
    print()


def _print_protocol_engine(
    standing_protocols: list,
    cost_ledger: CostLedger,
) -> None:
    """Print reactive protocol engine initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  REACTIVE PROTOCOL ENGINE  ·  standing protocols loaded")
    print(thin)
    for sp in standing_protocols:
        trigger = sp.trigger
        print(f"    {sp.protocol_id}  {sp.name}")
        print(f"      Trigger: {trigger['instrument_class']} ≥ {trigger['stoplight_level']}")
    print(f"   Protocols loaded: {len(standing_protocols)}")
    print(f"   Starting allocation: ${cost_ledger.financial_balance:,.2f}")
    print(f"   Starting labor:  {cost_ledger.labor_remaining:.1f} person-hours")
    print(f"   Material items:  {len(cost_ledger.inventory)}")
    print()


def _print_progress(
    epoch: int,
    num_epochs: int,
    trigger_status: str,
    n_active_sops: int,
    total_spent: float,
    prev_status: str,
) -> None:
    """Overwrite a single terminal line with a dynamic progress bar."""
    pct = (epoch + 1) / num_epochs * 100
    bar_width = 30
    filled = int(bar_width * (epoch + 1) / num_epochs)
    bar = "█" * filled + "░" * (bar_width - filled)

    status_icon = {"BASELINE": "●", "SUSPECTED": "▲", "CONFIRMED": "■"}.get(
        trigger_status, "?"
    )

    transition = ""
    if trigger_status != prev_status:
        transition = f"  *** {prev_status} → {trigger_status} ***"

    line = (
        f"\r  {bar} {pct:5.1f}%  "
        f"Epoch {epoch + 1:02d}/{num_epochs:02d}  "
        f"{status_icon} {trigger_status:<10s}  "
        f"SOPs:{n_active_sops}  "
        f"Spent:${total_spent:>10,.0f}"
        f"{transition}"
    )

    sys.stdout.write(line)
    sys.stdout.flush()

    if epoch == num_epochs - 1:
        sys.stdout.write("\n")


def _print_executive_summary(
    *,
    num_agents: int,
    num_epochs: int,
    engine_summary: dict[str, Any],
    audit: dict[str, Any],
    proto_summary: dict[str, Any],
    escalation_log: list[dict[str, Any]],
    compliance_log: list[dict[str, Any]],
    trigger_status: str,
    isolated_count: int,
    refuser_count: int,
    contam_engine: Any | None,
    zone_pathogen_mass: dict[str, float],
    hvac_cfg: dict[str, Any],
    pathogen_profiles: dict[str, Any] | None,
) -> None:
    """Print a highly visible ASCII executive summary box."""
    W = 80
    border = "╔" + "═" * (W - 2) + "╗"
    bottom = "╚" + "═" * (W - 2) + "╝"
    divider = "╠" + "═" * (W - 2) + "╣"
    thin_div = "╟" + "─" * (W - 2) + "╢"

    def row(text: str = "") -> str:
        stripped = text.rstrip()
        pad = W - 4 - len(stripped)
        if pad < 0:
            stripped = stripped[: W - 4]
            pad = 0
        return f"║ {stripped}{' ' * pad}  ║"

    lines: list[str] = []
    lines.append(border)
    lines.append(row("CRUSHER TO THE BRIDGE  ─  EXECUTIVE SUMMARY"))
    lines.append(divider)

    # Section 1: Epidemiological Metrics
    lines.append(row("EPIDEMIOLOGICAL METRICS"))
    lines.append(thin_div)
    lines.append(row(f"Total crew:          {num_agents}"))
    lines.append(row(f"Total infected:      {engine_summary['infected'] + engine_summary['recovered'] + engine_summary['isolated']}"))
    lines.append(row(f"  Currently infected: {engine_summary['infected']}"))
    lines.append(row(f"  Recovered:          {engine_summary['recovered']}"))
    lines.append(row(f"  Isolated:           {engine_summary['isolated']}"))
    lines.append(row(f"  Immune (neg sec):   {engine_summary['immune']}"))
    lines.append(row(f"  Symptomatic:        {engine_summary['symptomatic']}"))
    lines.append(row(f"VSP triggered:       {'Yes' if engine_summary['vsp_triggered'] else 'No'}"))
    lines.append(row(f"Final status:        {trigger_status}"))

    if pathogen_profiles and len(pathogen_profiles) > 1:
        lines.append(row(f"Pathogen count:      {len(pathogen_profiles)}"))
        for pid in pathogen_profiles:
            lines.append(row(f"  - {pid}"))

    if escalation_log:
        lines.append(row())
        lines.append(row("Escalation timeline:"))
        for entry in escalation_log:
            lines.append(row(f"  Epoch {entry['epoch']:02d}:  {entry['from']}  ->  {entry['to']}"))

    if compliance_log:
        refused = sum(1 for c in compliance_log if c["action"] == "refused_quarantine")
        immediate = sum(1 for c in compliance_log if c["action"] == "immediate_compliance")
        lines.append(row(f"Compliance:          {immediate} immediate, {refused} refused"))

    summary = audit["summary"]
    lines.append(row(f"Person-hours used: {summary['total_labor_consumed_hours']:.1f} / {summary['starting_labor_capacity_hours']:.0f}"))

    lines.append(divider)

    # Section 2: Financial & Resource Audit
    lines.append(row("FINANCIAL & RESOURCE AUDIT"))
    lines.append(thin_div)
    lines.append(row(f"Starting allocation: ${summary['starting_financial_budget_usd']:>10,.2f}"))
    lines.append(row(f"Total spent:         ${summary['total_expenditure_usd']:>10,.2f}"))
    lines.append(row(f"  Surveillance:      ${summary['surveillance_cost_usd']:>10,.2f}"))
    lines.append(row(f"  Intervention:      ${summary['intervention_cost_usd']:>10,.2f}"))
    lines.append(row(f"Remaining:           ${summary['remaining_balance_usd']:>10,.2f}"))
    lines.append(row())
    lines.append(row(f"Labor consumed:      {summary['total_labor_consumed_hours']:>8.1f} person-hours"))
    lines.append(row(f"  Surveillance:      {summary['surveillance_labor_hours']:>8.1f} person-hours"))
    lines.append(row(f"  Intervention:      {summary['intervention_labor_hours']:>8.1f} person-hours"))

    depleted = [
        item for item, data in audit["material_inventory"].items()
        if data["remaining"] == 0 and data["consumed"] > 0
    ]
    if depleted:
        lines.append(row())
        lines.append(row("DEPLETED SUPPLIES (fully consumed)"))
        for item in depleted:
            data = audit["material_inventory"][item]
            lines.append(row(f"  {item}: {data['starting']} -> 0  (${data['total_cost_usd']:.2f})"))

    lines.append(divider)

    # Section 3: SOP History
    lines.append(row("SOP ACTIVATION HISTORY"))
    lines.append(thin_div)

    activations = [e for e in proto_summary["event_log"] if e["event"] == "ACTIVATED"]
    if activations:
        seen: set[str] = set()
        for ev in activations:
            pid = ev["protocol_id"]
            if pid not in seen:
                seen.add(pid)
                lines.append(row(f"  {pid}  {ev['name'][:40]:<40s}  Epoch {ev['epoch']:02d}"))
    else:
        lines.append(row("  (no protocols activated)"))

    still_active = proto_summary["protocols_still_active"]
    if still_active:
        lines.append(row())
        lines.append(row(f"Still active at end: {', '.join(still_active)}"))

    lines.append(row(f"Total activations:   {proto_summary['total_activations']}"))
    lines.append(row(f"Total deactivations: {proto_summary['total_deactivations']}"))

    lines.append(divider)

    # Footer
    lines.append(row(f"{num_epochs} epochs completed.  Data bridged cleanly."))
    lines.append(row(f"Isolated: {isolated_count}/{num_agents}   Non-compliant: {refuser_count}"))
    lines.append(bottom)

    print()
    print("\n".join(lines))


# ── Main loop ────────────────────────────────────────────────────────────

def run() -> None:
    """Execute the full simulation: init, epoch loop, finalization."""
    sep = "═" * 80
    print(sep)
    print("  CRUSHER TO THE BRIDGE  ·  Phase 4+ – Multi-Pathogen & Microflora")
    print(sep)
    print()

    parser = argparse.ArgumentParser(description="Crusher to the Bridge – simulation orchestrator")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of simulation epochs (overrides config.yaml num_epochs)")
    args = parser.parse_args()

    cfg = load_config()
    num_epochs = args.epochs if args.epochs is not None else cfg.get("num_epochs", 24)
    seed = cfg.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    modalities = build_modalities(cfg, rng, total_epochs=num_epochs)

    syndromic = modalities["syndromic"]
    rdt = modalities["clinical_rdt"]
    pcr = modalities["targeted_pcr"]
    seq = modalities["sequencing"]

    # ── 0. INITIALIZATION ────────────────────────────────────────────
    ship = _initialize_ship_graph(cfg)
    num_agents = ship["num_agents"]
    zone_names = ship["zone_names"]
    high_traffic = ship["high_traffic_zones"]

    engine = _build_engine(cfg, seed=seed)
    _print_korkin_engine(engine)

    contam_engine = build_transport_engine(_REPO_ROOT, cfg)
    if contam_engine is not None:
        engine.enable_external_transport()
    _print_contam_engine(contam_engine, engine, cfg)

    # Multi-pathogen profiles
    pathogen_profiles = _load_pathogen_profiles(cfg)
    mp_cfg = cfg.get("multi_pathogen", {})
    mf_cfg = cfg.get("microflora", {})
    enable_dual_signal = mf_cfg.get("enable_dual_signal", True)

    immunocompromised_ids = _init_multi_pathogen(engine, pathogen_profiles, cfg, rng)
    imm_mult = mp_cfg.get("immunocompromised_multiplier", 2.0)
    _print_multi_pathogen(pathogen_profiles, immunocompromised_ids, engine, imm_mult, enable_dual_signal)

    # Transmission core
    airflow_data = load_air_flow_paths(_REPO_ROOT, cfg)
    zone_volumes = {
        z["name"]: z.get("volume_m3", 100.0)
        for z in ship.get("zones", [])
    }
    hvac_downstream = build_hvac_downstream_map(airflow_data) if airflow_data else {}
    tx_core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=zone_volumes,
        pathogen_profiles=pathogen_profiles,
    )
    tx_core.initialize_zones(zone_names)
    engine.enable_external_transmission()
    _print_transmission_core(hvac_downstream, pathogen_profiles)

    # Observation engine
    obs = _init_observation_engine(cfg, seed)

    # Protocol engine & cost ledger
    proto_ctx = _init_protocol_engine(cfg, contam_engine)

    # GRUMB seeding
    grumb_seeds = _initialize_grumb_seeding(seq, ship["zones"])
    _print_initialization(ship, grumb_seeds, cfg)

    # Simulation state
    state = SimulationState()

    # ── EPOCH LOOP ───────────────────────────────────────────────────
    for epoch in range(num_epochs):
        # 1. FRED compliance
        _step_fred_compliance(epoch, state, syndromic)

        # 1b. Mid-cruise pathogen introductions
        _step_mid_cruise_introductions(epoch, engine, pathogen_profiles, rng)

        # 2. Engine step
        engine.isolated_ids = set(state.isolated_ids)
        engine_payload = engine.step()

        # 2a. Infection progression
        _step_infection_progression(engine, pathogen_profiles)

        # 2b. Four-pathway transmission
        tracing_matrix, tx_events = tx_core.execute_transmission(
            epoch=epoch,
            agents=engine.agents,
            zone_pathogen_mass=engine.zone_pathogen_mass,
            hvac_downstream_zones=hvac_downstream,
            multi_pathogen_mass=(
                engine.multi_pathogen_mass if pathogen_profiles else None
            ),
        )

        # 2c. CONTAM aerosol mass transport
        if contam_engine is not None:
            updated_masses = contam_engine.transport_step(engine.zone_pathogen_mass)
            engine.zone_pathogen_mass = updated_masses

        # 2d. Dual-signal shedding: compute microflora shifts
        zone_microflora_shifts: dict[str, dict[str, float]] = {}
        if pathogen_profiles and enable_dual_signal:
            zone_microflora_shifts = _compute_zone_microflora_shifts(
                engine.agents, pathogen_profiles, cfg,
            )

        # Re-export payload with updated zone masses and agent states
        engine_payload = engine._export_payload()

        # Convert engine output to telemetry schema
        agents, spaces = _engine_payload_to_schema(
            engine_payload, state.isolated_ids, state.quarantine_refusers,
        )

        payload = make_ground_truth(epoch=epoch, agents=agents, spaces=spaces)
        write_ground_truth(payload)

        # 3. Read back from neutral buffer (decoupled IO)
        truth = read_ground_truth()
        assert truth is not payload, "Shared-memory leak!"

        # 4. Syndromic surveillance (every epoch)
        syn_result = syndromic.query_ground_truth(truth)

        # 5. Clinical RDT on sick-call agents
        sick_call_ids = syn_result["sick_call_agents"]
        rdt_result = rdt.query_ground_truth(truth, sick_call_ids=sick_call_ids)

        # 6. Targeted PCR
        pcr_result = None
        if state.trigger_status == STATUS_SUSPECTED:
            pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=high_traffic)
        elif state.trigger_status == STATUS_CONFIRMED:
            pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=zone_names)
        else:
            pcr_cadence = cfg.get("targeted_pcr", {}).get("cadence", 4)
            if epoch % pcr_cadence == 0:
                pcr_result = pcr.query_ground_truth(truth)

        # 7. Metagenomic sequencing
        seq_result = None
        seq_cadence = cfg.get("sequencing", {}).get("cadence", 8)
        if epoch % seq_cadence == 0:
            seq_result = seq.query_ground_truth(
                truth, zone_microflora_shifts=zone_microflora_shifts,
            )

        # 7b-7c. Observation engine instruments
        (air_results, swab_results, ww_results,
         clin_rdt_results, clin_qpcr_results, clin_microbio_results) = (
            _run_observation_sampling(
                epoch, obs, agents, spaces, zone_names, zone_volumes,
                zone_microflora_shifts, state.trigger_status, high_traffic,
                syn_result, engine, pathogen_profiles, cfg,
            )
        )

        # 8. Escalation check
        prev_status = state.trigger_status
        state.trigger_status = _check_escalation(
            state.trigger_status, syn_result, pcr_result, cfg,
        )
        if state.trigger_status != prev_status:
            state.escalation_log.append({
                "epoch": epoch,
                "from": prev_status,
                "to": state.trigger_status,
            })
            obs.notebook.log_trigger_transition(epoch, prev_status, state.trigger_status)

        # 8b. Reactive Protocol Engine evaluation
        stoplights = compute_stoplights(
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )
        reset_modifiers(contam_engine, tx_core, proto_ctx.original_filter_eff)
        active_mods = proto_ctx.protocol_engine.evaluate_epoch(epoch, stoplights)
        merged_mods = proto_ctx.protocol_engine.get_merged_modifiers(active_mods)

        if merged_mods:
            apply_hvac_modifiers(contam_engine, merged_mods)
            apply_transmission_modifiers(tx_core, merged_mods)

        # 8c. Cost accounting
        _step_cost_accounting(
            epoch, proto_ctx,
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )

        # 9. Quarantine confinement
        _step_quarantine_confinement(
            epoch, agents, merged_mods, state.trigger_status, state, syndromic,
        )

        # 10. Record simulation history
        epoch_cost = proto_ctx.cost_ledger.get_epoch_summary(epoch)
        epoch_record = _record_epoch(
            epoch=epoch,
            trigger_status=state.trigger_status,
            agents=agents,
            spaces=spaces,
            engine=engine,
            contam_engine=contam_engine,
            pathogen_profiles=pathogen_profiles,
            zone_names=zone_names,
            zone_microflora_shifts=zone_microflora_shifts,
            syn_result=syn_result,
            rdt_result=rdt_result,
            pcr_result=pcr_result,
            seq_result=seq_result,
            tracing_matrix=tracing_matrix,
            state=state,
            obs=obs,
            active_mods=active_mods,
            merged_mods=merged_mods,
            stoplights=stoplights,
            epoch_cost=epoch_cost,
            cfg=cfg,
            air_results=air_results,
            swab_results=swab_results,
            ww_results=ww_results,
            clin_rdt_results=clin_rdt_results,
            clin_qpcr_results=clin_qpcr_results,
            clin_microbio_results=clin_microbio_results,
        )
        state.simulation_history.append(epoch_record)

        # 11. Live progress bar
        n_active_sops = len(active_mods)
        total_spent = proto_ctx.cost_ledger.starting_financial_usd - proto_ctx.cost_ledger.financial_balance
        _print_progress(epoch, num_epochs, state.trigger_status, n_active_sops, total_spent, prev_status)

    # ── FINALIZATION ─────────────────────────────────────────────────
    _finalize_simulation(
        state=state,
        engine=engine,
        obs=obs,
        proto_ctx=proto_ctx,
        pathogen_profiles=pathogen_profiles,
        zone_names=zone_names,
        num_agents=num_agents,
        num_epochs=num_epochs,
        contam_engine=contam_engine,
        cfg=cfg,
    )


if __name__ == "__main__":
    run()
    sys.exit(0)
