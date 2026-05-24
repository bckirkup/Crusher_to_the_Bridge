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
from engines.py_contam_bridge import build_transport_engine, ContamTransportEngine
from engines.transmission_core import (
    TransmissionCore,
    build_hvac_downstream_map,
)
from engines.py_contam_bridge import load_air_flow_paths
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


# ── Initialization ───────────────────────────────────────────────────────

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


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
    seeds = seq_modality.seed_zones(zones)
    return seeds


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


# ── Korkin Lab engine helpers ────────────────────────────────────────────

def _build_engine(
    cfg: dict[str, Any],
    seed: int = 42,
) -> KorkinShipEngine:
    """Initialise the real infection-dynamics engine from config.

    Uses the ship_graph zones from config.yaml, mapping them to the
    Korkin Lab zone types (Room, Dining, Free).
    """
    graph_cfg = cfg.get("ship_graph", {})
    zones = graph_cfg.get("zones", [])
    num_agents = graph_cfg.get("num_agents", 20)
    roles_cfg = graph_cfg.get("agent_roles", {})
    passenger_frac = roles_cfg.get("passenger_fraction", 0.70)
    num_passengers = int(num_agents * passenger_frac)
    num_crew = num_agents - num_passengers

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

        # Attach multi-pathogen metadata
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


# ── Main loop ────────────────────────────────────────────────────────────

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

            # Propagate to graywater downstream zones (reduced magnitude)
            for gz in graywater_zones:
                gzs = zone_shifts.setdefault(gz, {})
                gzs[d_type] = gzs.get(d_type, 0.0) + mag * 0.3

    return zone_shifts


def run() -> None:
    sep = "═" * 80
    thin = "─" * 80

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

    # Initialise the real Korkin Lab infection-dynamics engine
    engine = _build_engine(cfg, seed=seed)

    thin_line = "─" * 80
    print(thin_line)
    print("  KORKIN LAB ENGINE  ·  infection-dynamics ABM initialized")
    print(thin_line)
    engine_summary = engine.get_summary()
    print(f"\n  Population: {engine_summary['total']} agents "
          f"({engine.num_passengers} passengers, {engine.num_crew} crew)")
    print(f"  Immune (negative secretors): {engine_summary['immune']}")
    print(f"  Initial infected: {engine_summary['infected']}")
    print(f"  Zones: {', '.join(z['name'] for z in engine.zones)}")
    print(f"  VSP isolation: {'enabled' if engine.vsp_isolation else 'disabled'}")
    print(f"  Model: Norwalk virus dose-response (α={0.111}, β={32.81})")
    print(f"  Shedding: symptomatic log10 curve [7.75..8.0] over 15 days")
    print()

    # Initialise the CONTAM transport engine for aerosol mass transport
    contam_engine = build_transport_engine(_REPO_ROOT, cfg)
    if contam_engine is not None:
        engine.enable_external_transport()
        hvac_cfg = cfg.get("hvac", {})
        filter_type = hvac_cfg.get("filter_type", "MERV-13")
        print(thin_line)
        print("  CONTAM TRANSPORT ENGINE  ·  py-contam multi-zone airflow initialized")
        print(thin_line)
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

    # ── Load multi-pathogen profiles ───────────────────────────────
    pathogen_profiles = _load_pathogen_profiles(cfg)
    mp_cfg = cfg.get("multi_pathogen", {})
    mf_cfg = cfg.get("microflora", {})
    enable_dual_signal = mf_cfg.get("enable_dual_signal", True)

    if pathogen_profiles:
        print(thin_line)
        print("  MULTI-PATHOGEN ENGINE  ·  active profiles loaded")
        print(thin_line)
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

        # Initialize per-pathogen mass pools in the engine
        for pid in pathogen_profiles:
            engine.initialize_pathogen(pid)

        # Initialize agent susceptibility multipliers
        imm_frac = mp_cfg.get("immunocompromised_fraction", 0.05)
        imm_mult = mp_cfg.get("immunocompromised_multiplier", 2.0)
        n_immunocompromised = int(len(engine.agents) * imm_frac)
        immunocompromised_ids: set[int] = set()

        for agent in engine.agents:
            for pid, prof in pathogen_profiles.items():
                base_susc = prof.get("base_susceptibility", 1.0)
                agent.init_pathogen_susceptibility(pid, base_susc)

        # Assign elevated susceptibility to a fraction of agents
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

        print(f"  Immunocompromised agents: {len(immunocompromised_ids)}/{len(engine.agents)} "
              f"(mult={imm_mult}x)")
        print(f"  Dual-signal shedding: {'enabled' if enable_dual_signal else 'disabled'}")
        print()

        # Seed initial infections per pathogen profile
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
    else:
        immunocompromised_ids = set()

    # Initialise the four-pathway TransmissionCore
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

    print(thin_line)
    print("  TRANSMISSION CORE  ·  four-pathway model initialized")
    print(thin_line)
    print("    1. Direct Contact      (zone-colocation, avgR scaling)")
    print("    2. Short-Range Droplet (immediate room aerosol)")
    print("    3. Long-Range Airborne (HVAC drift via py-contam)")
    print("    4. Fomite Deposition   (surface pools + stochastic pickup)")
    print(f"   HVAC downstream links: {sum(len(v) for v in hvac_downstream.values())}")
    if pathogen_profiles:
        print(f"   Active pathogens: {', '.join(pathogen_profiles.keys())}")
    print()

    # ── Initialize Observation Engine instruments ─────────────────
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

    # Individual patient clinical diagnostics (Sick Call)
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

    print(thin_line)
    print("  OBSERVATION ENGINE  ·  instrument-level diagnostics initialized")
    print(thin_line)
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

    # ── Initialize Reactive Protocol Engine & Cost Ledger ────────────
    protocols_cfg_path = os.path.join(_REPO_ROOT, "data", "config", "protocols.json")
    resource_cfg_path = os.path.join(_REPO_ROOT, "data", "config", "resource_costs.json")

    cost_ledger = build_ledger_from_config(resource_cfg_path)
    resource_costs_cfg = load_resource_costs(resource_cfg_path)
    standing_protocols = load_protocols(protocols_cfg_path)
    protocol_engine = ProtocolEngine(standing_protocols, cost_ledger)

    original_filter_eff = (
        contam_engine.filter_efficiency if contam_engine is not None else 0.50
    )

    print(thin_line)
    print("  REACTIVE PROTOCOL ENGINE  ·  standing protocols loaded")
    print(thin_line)
    for sp in standing_protocols:
        trigger = sp.trigger
        print(f"    {sp.protocol_id}  {sp.name}")
        print(f"      Trigger: {trigger['instrument_class']} ≥ {trigger['stoplight_level']}")
    print(f"   Protocols loaded: {len(standing_protocols)}")
    print(f"   Starting budget: ${cost_ledger.financial_balance:,.2f}")
    print(f"   Starting labor:  {cost_ledger.labor_remaining:.1f} person-hours")
    print(f"   Material items:  {len(cost_ledger.inventory)}")
    print()

    grumb_seeds = _initialize_grumb_seeding(seq, ship["zones"])
    _print_initialization(ship, grumb_seeds, cfg)

    trigger_status = STATUS_BASELINE
    isolated_ids: set[int] = set()
    quarantine_refusers: set[int] = set()
    quarantine_order_epoch: dict[int, int] = {}
    escalation_log: list[dict[str, Any]] = []
    compliance_log: list[dict[str, Any]] = []
    simulation_history: list[dict[str, Any]] = []

    for epoch in range(num_epochs):
        # ── 1. FRED compliance check for pending quarantine orders ────
        newly_complied: set[int] = set()
        for aid in list(quarantine_refusers):
            epochs_since = epoch - quarantine_order_epoch.get(aid, epoch)
            if syndromic.check_quarantine_compliance(aid, epochs_since):
                newly_complied.add(aid)
                quarantine_refusers.discard(aid)
                isolated_ids.add(aid)
                compliance_log.append({
                    "epoch": epoch, "agent_id": aid,
                    "action": "delayed_compliance",
                    "delay": epochs_since,
                })

        # ── 1b. Mid-cruise pathogen introductions ──────────────────────
        if pathogen_profiles:
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

        # ── 2. Real engine step ───────────────────────────────────────
        engine.isolated_ids = set(isolated_ids)
        engine_payload = engine.step()

        # ── 2a. Multi-pathogen infection progression ─────────────────
        if pathogen_profiles:
            for agent in engine.agents:
                for pid, inf in list(agent.infections.items()):
                    if inf["status"] != InfectionStatus.INFECTED:
                        continue
                    prof = pathogen_profiles.get(pid, {})

                    # Advance time post infection
                    if inf["time_infected"] is not None:
                        inf["time_infected"] += 1

                    # Illness progression
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

                    # Recovery
                    recovery_day = prof.get("recovery_day", 3)
                    if dpi >= recovery_day:
                        inf["status"] = InfectionStatus.RECOVERED
                        inf["illness"] = IllnessStatus.RECOVERED

                # Update legacy status if all infections resolved
                any_active = any(
                    inf["status"] == InfectionStatus.INFECTED
                    for inf in agent.infections.values()
                )
                if agent.infections and not any_active:
                    if agent.infection_status == InfectionStatus.INFECTED:
                        agent.infection_status = InfectionStatus.RECOVERED
                        agent.illness_status = IllnessStatus.RECOVERED

                # Update microflora disruption status
                agent.update_microflora_disruption(pathogen_profiles)

            # ── 2a-ii. Per-pathogen mass accumulation ────────────────
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

        # ── 2b. Four-pathway transmission ────────────────────────────
        tracing_matrix, tx_events = tx_core.execute_transmission(
            epoch=epoch,
            agents=engine.agents,
            zone_pathogen_mass=engine.zone_pathogen_mass,
            hvac_downstream_zones=hvac_downstream,
            multi_pathogen_mass=(
                engine.multi_pathogen_mass if pathogen_profiles else None
            ),
        )

        # ── 2c. CONTAM aerosol mass transport ─────────────────────────
        if contam_engine is not None:
            updated_masses = contam_engine.transport_step(
                engine.zone_pathogen_mass,
            )
            engine.zone_pathogen_mass = updated_masses

        # ── 2d. Dual-signal shedding: compute microflora shifts ──────
        zone_microflora_shifts: dict[str, dict[str, float]] = {}
        if pathogen_profiles and enable_dual_signal:
            zone_microflora_shifts = _compute_zone_microflora_shifts(
                engine.agents, pathogen_profiles, cfg,
            )

        # Re-export payload with updated zone masses and agent states
        engine_payload = engine._export_payload()

        # Convert engine output → telemetry schema, applying FRED overrides
        agents, spaces = _engine_payload_to_schema(
            engine_payload, isolated_ids, quarantine_refusers,
        )
        active_symptomatic = sum(
            1 for a in agents
            if a["symptom_status"] in ("symptomatic", "non_compliant",
                                       "asymptomatic_shedding")
        )

        payload = make_ground_truth(epoch=epoch, agents=agents, spaces=spaces)
        write_ground_truth(payload)

        # ── 3. Read back from neutral buffer (decoupled IO) ─────────
        truth = read_ground_truth()
        assert truth is not payload, "Shared-memory leak!"

        # ── 4. Syndromic surveillance (every epoch) ─────────────────
        syn_result = syndromic.query_ground_truth(truth)
        sick_call_ids = syn_result["sick_call_agents"]

        # ── 5. Clinical RDT on sick-call agents (EMOD phase-gated) ──
        rdt_result = rdt.query_ground_truth(truth, sick_call_ids=sick_call_ids)

        # ── 6. Targeted PCR ─────────────────────────────────────────
        pcr_result = None
        if trigger_status == STATUS_SUSPECTED:
            pcr_result = pcr.query_ground_truth(
                truth, surface_wipe_zones=high_traffic,
            )
        elif trigger_status == STATUS_CONFIRMED:
            pcr_result = pcr.query_ground_truth(
                truth, surface_wipe_zones=zone_names,
            )
        else:
            pcr_cadence = cfg.get("targeted_pcr", {}).get("cadence", 4)
            if epoch % pcr_cadence == 0:
                pcr_result = pcr.query_ground_truth(truth)

        # ── 7. Metagenomic sequencing (with microflora shift detection) ─
        seq_result = None
        seq_cadence = cfg.get("sequencing", {}).get("cadence", 8)
        if epoch % seq_cadence == 0:
            seq_result = seq.query_ground_truth(
                truth,
                zone_microflora_shifts=zone_microflora_shifts,
            )

        # ── 7b. Observation Engine instruments ────────────────────────
        zone_airborne: dict[str, float] = {}
        zone_surface: dict[str, float] = {}
        for zname, zdata in spaces.items():
            total_mass = zdata.get("pathogen_mass", 0.0)
            zone_airborne[zname] = total_mass * 0.6  # 60% airborne fraction
            zone_surface[zname] = total_mass * 0.4   # 40% surface fraction

        air_results = air_sniffer.sample_all_zones(zone_airborne, zone_volumes)

        fred_compliance = cfg.get("fred_behavior", {}).get(
            "quarantine_compliance", 0.85,
        )
        swab_targets = None
        if trigger_status in (STATUS_SUSPECTED, STATUS_CONFIRMED):
            swab_targets = high_traffic if trigger_status == STATUS_SUSPECTED else zone_names
        swab_results = surface_swab.swab_zones(
            zone_surface, fred_compliance, target_zones=swab_targets,
        )

        # Wastewater: combine pathogen mass + microflora shifts
        ww_pathogen_mass: dict[str, float] = {}
        for zname in zone_names:
            ww_pathogen_mass[zname] = zone_surface.get(zname, 0.0) * 0.1  # greywater fraction
        ww_microflora: dict[str, dict[str, float]] = {}
        for zname, mf_data in zone_microflora_shifts.items():
            ww_microflora[zname] = mf_data
        ww_per_pathogen = (
            {pid: engine.get_pathogen_zone_mass(pid) for pid in pathogen_profiles}
            if pathogen_profiles else None
        )
        graywater_zones = cfg.get("microflora", {}).get("graywater_zones", [])
        ww_target_zones = graywater_zones if graywater_zones else zone_names
        ww_results = wastewater_seq.sample_all_zones(
            ww_pathogen_mass, ww_microflora,
            pathogen_mass_by_id=ww_per_pathogen,
            wastewater_zones=ww_target_zones,
        )

        # ── 7c. Individual Patient Clinical Diagnostics (Sick Call) ───
        sick_call_agents = [
            a for a in agents
            if a["agent_id"] in syn_result.get("sick_call_agents", [])
        ]
        clin_rdt_results: dict[int, dict[str, Any]] = {}
        clin_qpcr_results: dict[int, dict[str, Any]] = {}
        clin_microbio_results: dict[int, dict[str, Any]] = {}

        if sick_call_agents:
            clin_rdt_results = clin_rdt.test_sick_call_agents(sick_call_agents)
            clin_qpcr_results = clin_qpcr.test_sick_call_agents(sick_call_agents)
            clin_microbio_results = clin_microbio.test_sick_call_agents(sick_call_agents)

        # Log instrument results to lab notebook
        notebook.log_air_sniffer(epoch, air_results)
        notebook.log_surface_swab(epoch, swab_results)
        notebook.log_wastewater_seq(epoch, ww_results)
        notebook.log_clinical_rdt(epoch, clin_rdt_results)
        notebook.log_clinical_qpcr(epoch, clin_qpcr_results)
        notebook.log_clinical_microbiology(epoch, clin_microbio_results)
        notebook.log_agent_summary(epoch, agents)

        # ── 8. Escalation check ─────────────────────────────────────
        prev_status = trigger_status
        trigger_status = _check_escalation(
            trigger_status, syn_result, pcr_result, cfg,
        )

        if trigger_status != prev_status:
            escalation_log.append({
                "epoch": epoch,
                "from": prev_status,
                "to": trigger_status,
            })
            notebook.log_trigger_transition(epoch, prev_status, trigger_status)

        # ── 8b. Reactive Protocol Engine evaluation ────────────────
        stoplights = compute_stoplights(
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )

        # Reset modifiers to baseline before re-evaluating
        reset_modifiers(contam_engine, tx_core, original_filter_eff)

        active_mods = protocol_engine.evaluate_epoch(epoch, stoplights)
        merged_mods = protocol_engine.get_merged_modifiers(active_mods)

        # Apply physics/behavior modifiers from active protocols
        if merged_mods:
            apply_hvac_modifiers(contam_engine, merged_mods)
            apply_transmission_modifiers(tx_core, merged_mods)

        # ── 8c. Cost accounting — baseline surveillance + per-test ───
        baseline_costs = resource_costs_cfg.get("baseline_surveillance_costs_per_epoch", {})
        cost_ledger.debit_baseline_surveillance(epoch, baseline_costs)

        per_test = resource_costs_cfg.get("per_test_costs", {})
        # Environmental instruments
        cost_ledger.debit_per_test(epoch, "air_sniffer_sample", len(air_results), per_test)
        cost_ledger.debit_per_test(epoch, "surface_swab", len(swab_results), per_test)
        cost_ledger.debit_per_test(epoch, "wastewater_sequencing", len(ww_results), per_test)
        # Clinical instruments (per sick-call patient)
        n_sick = len(clin_rdt_results)
        cost_ledger.debit_per_test(epoch, "clinical_rdt", n_sick, per_test)
        cost_ledger.debit_per_test(epoch, "clinical_qpcr", n_sick, per_test)
        cost_ledger.debit_per_test(epoch, "clinical_microbiology", n_sick, per_test)

        # ── 9. CONFIRMED → quarantine with FRED compliance ──────────
        if trigger_status == STATUS_CONFIRMED:
            for agent in agents:
                aid = agent["agent_id"]
                if aid in isolated_ids or aid in quarantine_refusers:
                    continue
                if (
                    agent["symptom_status"] in ("symptomatic", "non_compliant")
                    or agent.get("shedding_rate", 0.0) > 0.0
                ):
                    if syndromic.check_quarantine_compliance(aid, 0):
                        isolated_ids.add(aid)
                        compliance_log.append({
                            "epoch": epoch, "agent_id": aid,
                            "action": "immediate_compliance",
                        })
                    else:
                        quarantine_refusers.add(aid)
                        quarantine_order_epoch[aid] = epoch
                        compliance_log.append({
                            "epoch": epoch, "agent_id": aid,
                            "action": "refused_quarantine",
                        })

        # ── 10. Record simulation history ───────────────────────────
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

        # Disrupted agent count
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
                "isolated": len(isolated_ids),
                "quarantine_refusers": len(quarantine_refusers),
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

        epoch_record["crusher_ops"]["isolated_agents"] = sorted(isolated_ids)

        # Observation Engine instrument records
        epoch_record["observation_engine"] = {
            "air_sniffer": air_results,
            "surface_swab": swab_results,
            "wastewater_sequencing": ww_results,
            "clinical_rdt": clin_rdt_results,
            "clinical_qpcr": clin_qpcr_results,
            "clinical_microbiology": clin_microbio_results,
            "logging_fidelity": fidelity_name,
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
        epoch_cost = cost_ledger.get_epoch_summary(epoch)
        epoch_record["cost_accounting"] = epoch_cost

        simulation_history.append(epoch_record)

        # ── 11. Live progress bar ───────────────────────────────────
        n_active_sops = len(active_mods)
        running_balance = cost_ledger.financial_balance
        _print_progress(
            epoch, num_epochs, trigger_status,
            n_active_sops, running_balance, prev_status,
        )

    # ── Save simulation history ──────────────────────────────────────
    history_path = os.path.join(
        _REPO_ROOT, "telemetry_buffer", "simulation_history.json",
    )
    with open(history_path, "w", encoding="utf-8") as fh:
        json.dump(simulation_history, fh, indent=2)
    print(f"\n  Simulation history saved to: {history_path}")

    # ── Serialize the Artificial Lab Notebook ───────────────────────
    if lab_notebook_enabled:
        notebook.set_run_metadata(
            num_agents=num_agents,
            num_epochs=num_epochs,
            pathogens=list(pathogen_profiles.keys()) if pathogen_profiles else [],
            zones=zone_names,
            trigger_timeline=escalation_log,
        )
        nb_output = logging_config.get("lab_notebook", {}).get(
            "output_path", "telemetry_buffer/artificial_lab_notebook.json",
        )
        nb_path = os.path.join(_REPO_ROOT, nb_output)
        financial_audit = cost_ledger.generate_financial_audit()
        protocol_summary = protocol_engine.generate_protocol_summary()
        notebook.serialize(
            nb_path,
            financial_audit=financial_audit,
            protocol_summary=protocol_summary,
        )
        print(f"  Lab notebook saved to: {nb_path} ({len(notebook.records)} records)")

    # ── Executive Summary ──────────────────────────────────────────────
    final_summary = engine.get_summary()
    audit = cost_ledger.generate_financial_audit()
    proto_summary = protocol_engine.generate_protocol_summary()

    _print_executive_summary(
        num_agents=num_agents,
        num_epochs=num_epochs,
        engine_summary=final_summary,
        audit=audit,
        proto_summary=proto_summary,
        escalation_log=escalation_log,
        compliance_log=compliance_log,
        trigger_status=trigger_status,
        isolated_count=len(isolated_ids),
        refuser_count=len(quarantine_refusers),
        contam_engine=contam_engine,
        zone_pathogen_mass=engine.zone_pathogen_mass,
        hvac_cfg=cfg.get("hvac", {}),
        pathogen_profiles=pathogen_profiles,
    )


def _print_progress(
    epoch: int,
    num_epochs: int,
    trigger_status: str,
    n_active_sops: int,
    running_balance: float,
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
        f"Budget:${running_balance:>10,.0f}"
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

    # ── Section 1: Epidemiological Metrics ────────────────────────
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

    # Co-infection
    if pathogen_profiles and len(pathogen_profiles) > 1:
        lines.append(row(f"Pathogen count:      {len(pathogen_profiles)}"))
        for pid in pathogen_profiles:
            lines.append(row(f"  - {pid}"))

    # Escalation timeline
    if escalation_log:
        lines.append(row())
        lines.append(row("Escalation timeline:"))
        for entry in escalation_log:
            lines.append(row(f"  Epoch {entry['epoch']:02d}:  {entry['from']}  ->  {entry['to']}"))

    # FRED compliance
    if compliance_log:
        refused = sum(1 for c in compliance_log if c["action"] == "refused_quarantine")
        immediate = sum(1 for c in compliance_log if c["action"] == "immediate_compliance")
        lines.append(row(f"Compliance:          {immediate} immediate, {refused} refused"))

    # Labor
    summary = audit["summary"]
    lines.append(row(f"Person-hours remaining: {summary['remaining_labor_hours']:.1f} / {summary['starting_labor_capacity_hours']:.0f}"))

    lines.append(divider)

    # ── Section 2: Financial & Resource Audit ─────────────────────
    lines.append(row("FINANCIAL & RESOURCE AUDIT"))
    lines.append(thin_div)
    lines.append(row(f"Starting budget:     ${summary['starting_financial_budget_usd']:>10,.2f}"))
    lines.append(row(f"Total spent:         ${summary['total_expenditure_usd']:>10,.2f}"))
    lines.append(row(f"  Surveillance:      ${summary['surveillance_cost_usd']:>10,.2f}"))
    lines.append(row(f"  Intervention:      ${summary['intervention_cost_usd']:>10,.2f}"))
    lines.append(row(f"Remaining balance:   ${summary['remaining_balance_usd']:>10,.2f}"))
    lines.append(row())
    lines.append(row(f"Labor consumed:      {summary['total_labor_consumed_hours']:>8.1f} person-hours"))
    lines.append(row(f"  Surveillance:      {summary['surveillance_labor_hours']:>8.1f} person-hours"))
    lines.append(row(f"  Intervention:      {summary['intervention_labor_hours']:>8.1f} person-hours"))

    # Depleted materials warning
    depleted = [
        item for item, data in audit["material_inventory"].items()
        if data["remaining"] == 0 and data["consumed"] > 0
    ]
    if depleted:
        lines.append(row())
        lines.append(row("!! WARNING — DEPLETED SUPPLIES !!"))
        for item in depleted:
            data = audit["material_inventory"][item]
            lines.append(row(f"  {item}: {data['starting']} -> 0  (${data['total_cost_usd']:.2f})"))

    lines.append(divider)

    # ── Section 3: SOP History ────────────────────────────────────
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

    # ── Footer ────────────────────────────────────────────────────
    lines.append(row(f"{num_epochs} epochs completed.  Data bridged cleanly."))
    lines.append(row(f"Isolated: {isolated_count}/{num_agents}   Non-compliant: {refuser_count}"))
    lines.append(bottom)

    print()
    print("\n".join(lines))


if __name__ == "__main__":
    run()
    sys.exit(0)
