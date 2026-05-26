"""
orchestrator_init.py – Initialization helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Spatial layout loading, ship graph setup, Korkin Lab engine
construction, pathogen profile loading, multi-pathogen
initialization, observation engine, and protocol engine setup.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any

import numpy as np

from telemetry_buffer.schema import make_agent, make_space
from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    InfectionStatus,
    IllnessStatus,
)
from engines.wearable_monitor import (
    WearableMonitor,
    build_wearable_monitor_from_config,
)
from crusher_labs.modalities.wearable import WearableDataStream
from engines.py_contam_bridge import ContamTransportEngine
from crusher_labs.observation_core import (
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
    ClinicalRapidDiagnostic,
    ClinicalQPCR,
    ClinicalMicrobiology,
)
from crusher_labs.lab_notebook import (
    build_notebook_from_config,
    load_logging_profile,
)
from crusher_labs.protocol_engine import (
    ProtocolEngine,
    load_protocols,
)
from crusher_labs.cost_ledger import (
    build_ledger_from_config,
    load_resource_costs,
)
from orchestrator_types import (
    REPO_ROOT,
    SYMPTOM_ISOLATED,
    SYMPTOM_QUARANTINED,
    SYMPTOM_NON_COMPLIANT,
    LOCATION_ISOLATED,
    ObservationEngine,
    ProtocolContext,
)
from orchestrator_display import (
    print_observation_engine,
    print_protocol_engine,
)


# ── Spatial layout & ship graph ──────────────────────────────────────────

def load_spatial_layout(cfg: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Load zones from the spatial layout JSON if configured."""
    graph_cfg = cfg.get("ship_graph", {})
    layout_path = graph_cfg.get("spatial_layout")
    if not layout_path:
        return None
    full_path = os.path.join(REPO_ROOT, layout_path)
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


def load_isolation_unit_capacity(cfg: dict[str, Any], default: int = 0) -> int:
    """Read isolation_unit_capacity from the platform spatial layout."""
    graph_cfg = cfg.get("ship_graph", {})
    layout_path = graph_cfg.get("spatial_layout")
    if not layout_path:
        return default
    full_path = os.path.join(REPO_ROOT, layout_path)
    if not os.path.isfile(full_path):
        return default
    with open(full_path, "r", encoding="utf-8") as fh:
        layout = json.load(fh)
    return int(layout.get("isolation_unit_capacity", default))


def initialize_ship_graph(cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the ship graph from spatial layout JSON or inline config.

    Returns zone list, agent role assignments, traffic classifications,
    and (when configured) agent class definitions.
    """
    graph_cfg = cfg.get("ship_graph", {})
    num_agents = graph_cfg.get("num_agents", 20)
    roles_cfg = graph_cfg.get("agent_roles", {})
    passenger_frac = roles_cfg.get("passenger_fraction", 0.70)

    spatial_zones = load_spatial_layout(cfg)
    zones = spatial_zones if spatial_zones else graph_cfg.get("zones", [])

    agent_classes = graph_cfg.get("agent_classes")
    gender_distribution = graph_cfg.get("gender_distribution")

    agent_roles: dict[int, str] = {}
    for aid in range(num_agents):
        agent_roles[aid] = "passenger" if aid < int(num_agents * passenger_frac) else "crew"

    high_traffic = [z["name"] for z in zones if z.get("traffic") == "high"]
    zone_names = [z["name"] for z in zones]

    result: dict[str, Any] = {
        "zones": zones,
        "zone_names": zone_names,
        "high_traffic_zones": high_traffic,
        "num_agents": num_agents,
        "agent_roles": agent_roles,
    }
    if agent_classes:
        result["agent_classes"] = agent_classes
    if gender_distribution:
        result["gender_distribution"] = gender_distribution
    return result


def initialize_grumb_seeding(
    seq_modality: Any,
    zones: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Seed all spatial nodes with GRUMB multi-kingdom log-ratio arrays at t=0."""
    return seq_modality.seed_zones(zones)


# ── Korkin Lab engine helpers ────────────────────────────────────────────

def build_engine(
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

    spatial_zones = load_spatial_layout(cfg)
    zones = spatial_zones if spatial_zones else graph_cfg.get("zones", [])

    engine_zones = [
        {"name": z["name"], "type": z["type"], "capacity": z.get("traffic", "medium")}
        for z in zones
    ]

    agent_classes = graph_cfg.get("agent_classes")
    gender_distribution = graph_cfg.get("gender_distribution")

    return KorkinShipEngine(
        num_passengers=num_passengers,
        num_crew=num_crew,
        initial_infected=cfg.get("initial_infected", 1),
        zones=engine_zones,
        seed=seed,
        agent_classes=agent_classes,
        gender_distribution=gender_distribution,
    )


def engine_payload_to_schema(
    engine_payload: dict[str, Any],
    isolated_ids: set[int],
    quarantined_ids: set[int],
    quarantine_refusers: set[int],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Convert Korkin engine output to telemetry_buffer schema format.

    Applies FRED compliance overrides for isolated, quarantined, and
    non-compliant agents.  Isolated agents (in isolation units) have
    zero shedding; quarantined agents (confined to quarters) retain
    their actual shedding rate and home-zone location.
    """
    raw_agents = engine_payload.get("agents")
    if raw_agents is None:
        raise ValueError("engine_payload missing 'agents' key")
    raw_spaces = engine_payload.get("spaces")
    if raw_spaces is None:
        raise ValueError("engine_payload missing 'spaces' key")

    agents_out: list[dict[str, Any]] = []
    for a in raw_agents:
        aid = a["agent_id"]
        a_class = a.get("agent_class")
        a_gender = a.get("gender")
        if aid in isolated_ids:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status=SYMPTOM_ISOLATED,
                shedding_rate=0.0,
                location=LOCATION_ISOLATED,
                agent_class=a_class,
                gender=a_gender,
            )
        elif aid in quarantined_ids:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status=SYMPTOM_QUARANTINED,
                shedding_rate=float(a.get("shedding_rate", 0.0)),
                location=a.get("location", "unknown"),
                agent_class=a_class,
                gender=a_gender,
            )
        elif aid in quarantine_refusers:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status=SYMPTOM_NON_COMPLIANT,
                shedding_rate=float(a.get("shedding_rate", 0.0)),
                location=a.get("location", "unknown"),
                agent_class=a_class,
                gender=a_gender,
            )
        else:
            agent_dict = make_agent(
                agent_id=aid,
                symptom_status=a["symptom_status"],
                shedding_rate=float(a.get("shedding_rate", 0.0)),
                location=a.get("location"),
                agent_class=a_class,
                gender=a_gender,
            )

        if "pathogen_infections" in a:
            agent_dict["pathogen_infections"] = a["pathogen_infections"]
        if "susceptibility_multiplier" in a:
            agent_dict["susceptibility_multiplier"] = a["susceptibility_multiplier"]
        if "microflora_disruption" in a:
            agent_dict["microflora_disruption"] = a["microflora_disruption"]

        agents_out.append(agent_dict)

    spaces_out: dict[str, dict[str, Any]] = {}
    for zname, zdata in raw_spaces.items():
        space_dict = make_space(
            pathogen_mass=float(zdata.get("pathogen_mass", 0.0)),
            microbiome_id=zdata.get("microbiome_id", f"profile_{zname.lower()}"),
        )
        if "pathogen_mass_by_id" in zdata:
            space_dict["pathogen_mass_by_id"] = zdata["pathogen_mass_by_id"]
        spaces_out[zname] = space_dict

    return agents_out, spaces_out


# ── Escalation logic ────────────────────────────────────────────────────

def check_escalation(
    trigger_status: str,
    syndromic_result: dict[str, Any],
    pcr_result: dict[str, Any] | None,
    cfg: dict[str, Any],
) -> str:
    """Evaluate trigger thresholds and return the (possibly updated) status."""
    from orchestrator_types import STATUS_BASELINE, STATUS_SUSPECTED, STATUS_CONFIRMED

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

def load_pathogen_profiles(
    cfg: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Load multi-pathogen profiles from active_profiles.json."""
    mp_cfg = cfg.get("multi_pathogen", {})
    profiles_path = mp_cfg.get("profiles_path", "data/pathogens/active_profiles.json")
    full_path = os.path.join(REPO_ROOT, profiles_path)
    if not os.path.isfile(full_path):
        return {}
    with open(full_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    profiles: dict[str, dict[str, Any]] = {}
    for p in data.get("pathogens", []):
        pid = p.get("pathogen_id", "unknown")
        profiles[pid] = p
    return profiles


def init_multi_pathogen(
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

def init_observation_engine(
    cfg: dict[str, Any],
    seed: int,
) -> ObservationEngine:
    """Initialise all six diagnostic instruments and the lab notebook."""
    obs_cfg_path = os.path.join(REPO_ROOT, "data", "config", "logging_profile.json")
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

    print_observation_engine(fidelity_name, xcontam_rate, ctrl_intensity, lab_notebook_enabled)

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

def init_protocol_engine(
    cfg: dict[str, Any],
    contam_engine: ContamTransportEngine | None,
) -> ProtocolContext:
    """Initialise the reactive protocol engine and cost ledger."""
    protocols_cfg_path = os.path.join(REPO_ROOT, "data", "config", "protocols.json")
    resource_cfg_path = os.path.join(REPO_ROOT, "data", "config", "resource_costs.json")

    cost_ledger = build_ledger_from_config(resource_cfg_path)
    resource_costs_cfg = load_resource_costs(resource_cfg_path)
    standing_protocols = load_protocols(protocols_cfg_path)
    protocol_engine = ProtocolEngine(standing_protocols, cost_ledger)

    original_filter_eff = (
        contam_engine.filter_efficiency if contam_engine is not None else 0.50
    )

    print_protocol_engine(standing_protocols, cost_ledger)

    return ProtocolContext(
        protocol_engine=protocol_engine,
        cost_ledger=cost_ledger,
        resource_costs_cfg=resource_costs_cfg,
        standing_protocols=standing_protocols,
        original_filter_eff=original_filter_eff,
    )


# ── Wearable monitor initialization ─────────────────────────────────────

def init_wearable_monitors(
    engine: KorkinShipEngine,
    cfg: dict[str, Any],
    seed: int = 42,
) -> tuple[WearableMonitor | None, WearableDataStream | None]:
    """Initialise wearable physiological monitors and the Crusher Labs modality.

    Returns ``(None, None)`` when wearable monitoring is disabled or absent.
    """
    rng = np.random.default_rng(seed)
    monitor = build_wearable_monitor_from_config(cfg, rng)
    if monitor is None:
        return None, None

    for agent in engine.agents:
        monitor.initialize_agent(agent)

    wm_cfg = cfg.get("wearable_monitoring", {})
    modality = WearableDataStream(
        observation_noise_sigma=wm_cfg.get("observation_noise_sigma", 0.5),
        sync_dropout_prob=wm_cfg.get("sync_dropout_prob", 0.02),
        anomaly_z_threshold=wm_cfg.get("anomaly_z_threshold", 2.0),
        rng=np.random.default_rng(seed),
    )

    return monitor, modality
