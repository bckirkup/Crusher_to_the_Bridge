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
from collections import defaultdict
from typing import Any

import numpy as np

from telemetry_buffer.agent_axes import resolve_agent_axes
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
    COMPLIANCE_ISOLATED,
    COMPLIANCE_QUARANTINED,
    COMPLIANCE_NON_COMPLIANT,
    COMPLIANCE_COMPLIANT,
    LOCATION_ISOLATED,
    ObservationEngine,
    ProtocolContext,
)
from simulation_utils.paths import resolve_repo_path, validated_open
from orchestrator_display import (
    print_observation_engine,
    print_protocol_engine,
)


# ── Spatial layout & ship graph ──────────────────────────────────────────

def load_spatial_layout(cfg: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Load zones from the spatial layout JSON if configured."""
    layout = load_platform_layout_doc(cfg)
    if layout is None:
        return None
    return [
        {
            "name": z["id"],
            "type": z["type"],
            "traffic": z.get("traffic", "medium"),
            "volume_m3": z.get("volume_m3", 100),
            "display": z.get("display", {}),
            "deck": z.get("deck", "main"),
            "cabin_ventilation_type": z.get("cabin_ventilation_type", ""),
            "cabin_size": z.get("cabin_size"),
        }
        for z in layout.get("zones", [])
    ]


def default_cabin_size(zone_name: str, zone_type: str, cabin_size: int | None) -> int | None:
    """Resolve cabin occupancy for cabin-mate pairing."""
    if cabin_size is not None:
        return int(cabin_size)
    if zone_type != "Cabin_Corridor":
        return None
    if zone_name.startswith("Crew_"):
        return 3
    return 2


def assign_cabin_mates(
    agents: list[Any],
    zones: list[dict[str, Any]],
) -> None:
    """Pair agents into cabins within each corridor zone (mega_cruise_5000).

    Sets ``cabin_mate_ids`` on each agent to the other occupants of the
    same stateroom.  Non-cabin zones are skipped.
    """
    zone_meta = {z["name"]: z for z in zones}
    agents_by_zone: dict[str, list[Any]] = defaultdict(list)
    for agent in agents:
        agents_by_zone[agent.home_zone].append(agent)

    for zone_name, zone_agents in agents_by_zone.items():
        meta = zone_meta.get(zone_name, {})
        cabin_size = default_cabin_size(
            zone_name,
            meta.get("type", ""),
            meta.get("cabin_size"),
        )
        if cabin_size is None or cabin_size < 1:
            continue
        for i in range(0, len(zone_agents), cabin_size):
            cabin_group = zone_agents[i : i + cabin_size]
            cabin_ids = {a.agent_id for a in cabin_group}
            for agent in cabin_group:
                agent.cabin_mate_ids = frozenset(cabin_ids - {agent.agent_id})


def load_platform_layout_doc(cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Load the raw platform spatial_layout.json document."""
    graph_cfg = cfg.get("ship_graph", {})
    layout_path = graph_cfg.get("spatial_layout")
    if not layout_path:
        return None
    full_path = resolve_repo_path(REPO_ROOT, layout_path)
    if not os.path.isfile(full_path):
        return None
    with validated_open(full_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def resolve_graywater_zones(
    cfg: dict[str, Any],
    zone_names: list[str] | None = None,
) -> list[str]:
    """Resolve wastewater collection zones for ship-wide greywater sampling.

    Priority:
    1. ``microflora.graywater_zones`` in config (explicit override)
    2. ``graywater_zones`` on the active platform ``spatial_layout.json``
    3. All simulation zones (per-zone sampling fallback)
    """
    mf_cfg = cfg.get("microflora", {})
    explicit = mf_cfg.get("graywater_zones")
    if explicit:
        return list(explicit)

    layout = load_platform_layout_doc(cfg)
    if layout:
        platform_zones = layout.get("graywater_zones")
        if platform_zones:
            return list(platform_zones)

    return list(zone_names) if zone_names else []


def load_isolation_unit_capacity(cfg: dict[str, Any], default: int = 0) -> int:
    """Read isolation_unit_capacity from the platform spatial layout."""
    layout = load_platform_layout_doc(cfg)
    if layout is None:
        return default
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

    # VSP threshold confinement is now handled by configurable infection
    # counters in the orchestrator, not by the engine's internal check.
    return KorkinShipEngine(
        num_passengers=num_passengers,
        num_crew=num_crew,
        initial_infected=cfg.get("initial_infected", 1),
        zones=engine_zones,
        seed=seed,
        vsp_isolation=False,
        agent_classes=agent_classes,
        gender_distribution=gender_distribution,
    )


def _agent_compliance_state(
    aid: int,
    a: dict[str, Any],
    isolated_ids: set[int],
    quarantined_ids: set[int],
    quarantine_refusers: set[int],
) -> tuple[str, float, str | None]:
    if aid in isolated_ids:
        return COMPLIANCE_ISOLATED, 0.0, LOCATION_ISOLATED
    if aid in quarantined_ids:
        return (
            COMPLIANCE_QUARANTINED,
            float(a.get("shedding_rate", 0.0)),
            a.get("location", "unknown"),
        )
    if aid in quarantine_refusers:
        return (
            COMPLIANCE_NON_COMPLIANT,
            float(a.get("shedding_rate", 0.0)),
            a.get("location", "unknown"),
        )
    return (
        COMPLIANCE_COMPLIANT,
        float(a.get("shedding_rate", 0.0)),
        a.get("location"),
    )


def _copy_optional_agent_fields(
    agent_dict: dict[str, Any],
    a: dict[str, Any],
) -> None:
    for key in (
        "pathogen_infections",
        "susceptibility_multiplier",
        "microflora_disruption",
        "chronic_disease_ids",
    ):
        if key in a:
            agent_dict[key] = a[key]


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
        infection_state, symptom_presentation, compliance_status = resolve_agent_axes(a)
        compliance_status, shedding, location = _agent_compliance_state(
            aid, a, isolated_ids, quarantined_ids, quarantine_refusers,
        )

        agent_dict = make_agent(
            agent_id=aid,
            infection_state=infection_state,
            symptom_presentation=symptom_presentation,
            compliance_status=compliance_status,
            shedding_rate=shedding,
            location=location,
            agent_class=a_class,
            gender=a_gender,
        )

        _copy_optional_agent_fields(agent_dict, a)

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
    """Load multi-pathogen profiles from config.

    Prefers ``multi_pathogen.resolved_profiles`` injected by PicardRunSpec
    (after pathogen_overrides). Falls back to ``profiles_path`` on disk.
    """
    mp_cfg = cfg.get("multi_pathogen", {})
    resolved = mp_cfg.get("resolved_profiles")
    if isinstance(resolved, dict) and resolved:
        return {str(pid): dict(prof) for pid, prof in resolved.items()}

    profiles_path = mp_cfg.get("profiles_path", "data/pathogens/active_profiles.json")
    full_path = resolve_repo_path(REPO_ROOT, profiles_path)
    if not os.path.isfile(full_path):
        return {}
    with validated_open(full_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
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
                dpi = int(prof.get("initial_time_infected", 0))
                for agent in chosen:
                    agent.infect_with_pathogen(
                        pid, 1e4, 0, time_infected=dpi, rng=rng, profile=prof,
                    )
                    print(f"  Seeded {pid} → agent {agent.agent_id}")
    print()

    return immunocompromised_ids


# ── Observation engine initialization ────────────────────────────────────

def init_observation_engine(
    cfg: dict[str, Any],
    seed: int,
) -> ObservationEngine:
    """Initialise all six diagnostic instruments and the lab notebook."""
    obs_cfg_path = resolve_repo_path(REPO_ROOT, "data/config/logging_profile.json")
    fidelity_name, _fidelity, logging_config = load_logging_profile(obs_cfg_path)
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
    from crusher_labs import wastewater_sequencing_params

    ww_params = wastewater_sequencing_params(cfg)
    wastewater_seq = WastewaterSequencingGrid(
        read_depth=ww_params["read_depth"],
        dirichlet_concentration=ww_params["dirichlet_concentration"],
        pseudocount=ww_params["pseudocount"],
        aitchison_anomaly_threshold=ww_params["aitchison_anomaly_threshold"],
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
    from crusher_labs.clinical_correlation import ClinicalTestCorrelation

    clinical_correlation = ClinicalTestCorrelation.from_config(cfg, seed=seed)

    notebook = build_notebook_from_config(obs_cfg_path)

    from crusher_labs.instrument_turnaround import (
        InstrumentTurnaroundQueue,
        InstrumentTurnaroundRegistry,
    )
    from crusher_labs.long_read_escalation import is_long_read_enabled, long_read_config
    from crusher_labs.modalities.long_read_sequencing import LongReadNanoporeSequencing
    from crusher_labs.observation_core import LongReadVerificationSequencing

    tat_cfg = cfg.get("instrument_turnaround", {})
    tat_path = tat_cfg.get("config_path", "data/config/instrument_turnaround.json")
    lr_profile_turnaround: dict[str, Any] | None = None
    long_read_inst: LongReadVerificationSequencing | None = None
    if is_long_read_enabled(cfg):
        lr_cfg = long_read_config(cfg)
        params_path = lr_cfg.get(
            "params_path", "data/config/long_read_sequencing_params.json",
        )
        profile = lr_cfg.get("default_profile", "flongle_rapid")
        modality = LongReadNanoporeSequencing.from_params_path(
            params_path,
            profile,
            enabled=True,
            rng=np.random.default_rng(seed + 7),
            repo_root=REPO_ROOT,
        )
        lr_profile_turnaround = modality.turnaround
        long_read_inst = LongReadVerificationSequencing(
            modality=modality,
            cross_contamination_rate=xcontam_rate,
            control_intensity=ctrl_intensity,
            rng=np.random.default_rng(seed + 8),
        )

    tat_registry = InstrumentTurnaroundRegistry.load(
        tat_path,
        repo_root=REPO_ROOT,
        long_read_profile_turnaround=lr_profile_turnaround,
    )
    turnaround = InstrumentTurnaroundQueue(tat_registry)

    print_observation_engine(fidelity_name, xcontam_rate, ctrl_intensity, lab_notebook_enabled)

    return ObservationEngine(
        air_sniffer=air_sniffer,
        surface_swab=surface_swab,
        wastewater_seq=wastewater_seq,
        clin_rdt=clin_rdt,
        clin_qpcr=clin_qpcr,
        clin_microbio=clin_microbio,
        clinical_correlation=clinical_correlation,
        notebook=notebook,
        fidelity_name=fidelity_name,
        lab_notebook_enabled=lab_notebook_enabled,
        turnaround=turnaround,
        long_read=long_read_inst,
    )


# ── Protocol engine initialization ───────────────────────────────────────

def init_protocol_engine(
    _cfg: dict[str, Any],
    contam_engine: ContamTransportEngine | None,
    *,
    protocols_path: str | None = None,
    resource_costs_path: str | None = None,
    logging_profile_path: str | None = None,
) -> ProtocolContext:
    """Initialise the reactive protocol engine and cost ledger."""
    protocols_cfg_path = resolve_repo_path(
        REPO_ROOT,
        protocols_path or "data/config/protocols.json",
    )
    resource_cfg_path = resolve_repo_path(
        REPO_ROOT,
        resource_costs_path or "data/config/resource_costs.json",
    )
    _ = logging_profile_path  # reserved for future logging-profile overrides

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
    chronic_wearable_offsets: dict[int, dict[str, float]] | None = None,
    chronic_assignments: dict[int, list[str]] | None = None,
    repo_root: str | None = None,
) -> tuple[WearableMonitor | None, WearableDataStream | None]:
    """Initialise wearable physiological monitors and the Crusher Labs modality.

    When *chronic_wearable_offsets* is provided, chronic disease baseline
    offsets are applied after class/gender offsets during initialization.

    When *chronic_assignments* is provided, agents may receive additional
    devices from the ``chronic_disease_device_map`` configuration.

    Returns ``(None, None)`` when wearable monitoring is disabled or absent.
    """
    rng = np.random.default_rng(seed)
    root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=root)
    if monitor is None:
        return None, None

    chronic_assignments = chronic_assignments or {}
    for agent in engine.agents:
        disease_ids = chronic_assignments.get(agent.agent_id)
        monitor.initialize_agent(agent, chronic_disease_ids=disease_ids)

    # Apply chronic disease wearable baseline offsets
    if chronic_wearable_offsets:
        for agent_id, offsets in chronic_wearable_offsets.items():
            states = monitor.agent_states.get(agent_id)
            if not states:
                continue
            for state in states:
                for ch, offset in offsets.items():
                    if ch in state.baselines:
                        state.baselines[ch] = round(state.baselines[ch] + offset, 2)

    wm_cfg = cfg.get("wearable_monitoring", {})
    modality = WearableDataStream(
        observation_noise_sigma=wm_cfg.get("observation_noise_sigma", 0.5),
        sync_dropout_prob=wm_cfg.get("sync_dropout_prob", 0.02),
        anomaly_z_threshold=wm_cfg.get("anomaly_z_threshold", 2.0),
        rng=np.random.default_rng(seed),
    )

    return monitor, modality
