"""
orchestrator_init.py – Initialization helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Spatial layout loading, ship graph setup, Korkin Lab engine
construction, pathogen profile loading, multi-pathogen
initialization, observation engine, and protocol engine setup.
"""

from __future__ import annotations

import json
import os
import warnings
from collections import defaultdict
from typing import Any

import numpy as np

from crusher_labs.cost_ledger import (
    build_ledger_from_config,
    load_resource_costs,
)
from crusher_labs.lab_notebook import (
    build_notebook_from_config,
    load_logging_profile,
)
from crusher_labs.modalities.wearable import WearableDataStream
from crusher_labs.observation_core import (
    ClinicalMicrobiology,
    ClinicalQPCR,
    ClinicalRapidDiagnostic,
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
)
from crusher_labs.protocol_engine import (
    ProtocolEngine,
    load_protocols,
)
from engines.infection_dynamics_bridge import (
    VSP_RULE_INSTANT_PREVALENCE,
    VSP_RULE_REPORTED_PASSENGER_CASES,
    InfectionStatus,
    KorkinShipEngine,
)
from engines.py_contam_bridge import ContamTransportEngine
from engines.sim_clock import SimClock, config_epochs_for_hours
from engines.wearable_monitor import (
    WearableMonitor,
    build_wearable_monitor_from_config,
)
from orchestrator_display import (
    print_observation_engine,
    print_protocol_engine,
)
from orchestrator_types import (
    COMPLIANCE_COMPLIANT,
    COMPLIANCE_ISOLATED,
    COMPLIANCE_NON_COMPLIANT,
    COMPLIANCE_QUARANTINED,
    LOCATION_ISOLATED,
    REPO_ROOT,
    ObservationEngine,
    ProtocolContext,
)
from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.agent_axes import (
    INFECTION_INFECTED,
    INFECTION_RECOVERED,
    agent_has_symptomatic_presentation,
    resolve_agent_axes,
)
from telemetry_buffer.schema import make_agent, make_space

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
            "max_occupancy": z.get("max_occupancy"),
            "dining_service_type": z.get("dining_service_type", ""),
            "food_contamination_multiplier": z.get("food_contamination_multiplier"),
        }
        for z in layout.get("zones", [])
    ]


def default_cabin_size(zone_name: str, zone_type: str, cabin_size: int | None) -> int | None:
    """Resolve cabin occupancy for cabin-mate pairing."""
    if cabin_size is not None:
        return int(cabin_size)
    if zone_type != "Cabin_Corridor":
        return None
    # Contam-safe IDs: CC_* / OC_* crew-officer; FC_* family; EC_* enlisted; PC_* pax.
    if zone_name.startswith(("Crew_", "CC_", "OC_")):
        return 3 if zone_name.startswith(("Crew_", "CC_")) else 1
    if zone_name.startswith("FC_"):
        return 4
    return 2


def assign_cabin_mates(
    agents: list[Any],
    zones: list[dict[str, Any]],
) -> None:
    """Pair agents into cabins within each ``Cabin_Corridor`` zone.

    Applies to cabin-corridor platforms (mega_cruise_5000, expedition_cruise_450,
    and other recipe-generated cruise classes). Sets ``cabin_mate_ids`` on each
    agent to the other occupants of the same stateroom. Non-cabin zones are skipped.
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


def load_vsp_trigger_rule(cfg: dict[str, Any]) -> str:
    """Read and validate the selectable VSP trigger rule."""
    rule = cfg.get("escalation", {}).get(
        "vsp_trigger_rule", VSP_RULE_REPORTED_PASSENGER_CASES,
    )
    valid = {VSP_RULE_REPORTED_PASSENGER_CASES, VSP_RULE_INSTANT_PREVALENCE}
    if rule not in valid:
        raise ValueError(f"Unknown VSP trigger rule: {rule!r}")
    return str(rule)


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

def resolve_platform_id_from_cfg(cfg: dict[str, Any]) -> str:
    """Best-effort platform_id from ship_graph.spatial_layout path."""
    layout = (cfg.get("ship_graph") or {}).get("spatial_layout", "")
    if not layout:
        return ""
    norm = os.path.normpath(layout)
    parts = norm.replace("\\", "/").split("/")
    if "platforms" in parts:
        idx = parts.index("platforms")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def load_and_merge_voyage_config(
    cfg: dict[str, Any],
    *,
    repo_root: str = REPO_ROOT,
    platform_id: str | None = None,
) -> dict[str, Any]:
    """Load platform voyage_config.json and deep-merge config_overrides.voyage."""
    from engines.voyage_itinerary import (
        load_voyage_config,
        merge_voyage_overrides,
        voyage_config_path_for_platform,
    )

    pid = platform_id or resolve_platform_id_from_cfg(cfg)
    path = voyage_config_path_for_platform(repo_root, pid) if pid else None
    base = load_voyage_config(path)
    overrides = cfg.get("voyage")
    if isinstance(overrides, dict):
        return merge_voyage_overrides(base, overrides)
    return base


def apply_voyage_dining_meal_weights(
    cfg: dict[str, Any],
    voyage_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Apply platform dining_meal_weights into agent_behavior.

    Platform class tables replace the stock ``DEFAULT_AGENT_BEHAVIOR`` /
    ``config.yaml`` meal weights (so expedition keeps buffet=0). Explicit
    non-default ``agent_behavior.dining_meal_weights`` (Picard overrides)
    still overlay the platform table per meal.
    """
    from engines.infection_dynamics_bridge import DEFAULT_AGENT_BEHAVIOR
    from engines.voyage_itinerary import dining_meal_weights_from_config

    platform_weights = dining_meal_weights_from_config(voyage_cfg)
    if not platform_weights:
        return cfg
    behavior = dict(cfg.get("agent_behavior") or {})
    cfg_meals = dict(behavior.get("dining_meal_weights") or {})
    default_meals = DEFAULT_AGENT_BEHAVIOR.get("dining_meal_weights") or {}
    using_stock_defaults = (not cfg_meals) or cfg_meals == default_meals
    if using_stock_defaults:
        behavior["dining_meal_weights"] = {
            meal: dict(weights)
            for meal, weights in platform_weights.items()
        }
    else:
        merged_meals: dict[str, Any] = {}
        for meal in ("breakfast", "lunch", "dinner"):
            base = dict(platform_weights.get(meal) or {})
            overlay = dict(cfg_meals.get(meal) or {})
            merged_meals[meal] = {**base, **overlay} if (base or overlay) else {}
        for meal, weights in cfg_meals.items():
            if meal not in merged_meals:
                merged_meals[meal] = weights
        behavior["dining_meal_weights"] = merged_meals
    cfg = dict(cfg)
    cfg["agent_behavior"] = behavior
    return cfg


# Stock modality / FRED defaults (config.yaml). Voyage medical_response seeds
# only when the target key is still at these values so campaign overrides win.
_STOCK_SICK_CALL_PROBABILITY = 0.70
_STOCK_QUARANTINE_COMPLIANCE = 0.85
_STOCK_DETECTION_DELAY_EPOCHS = 0
_STOCK_CREW_SCREENING_INTERVAL: int | None = None


def _is_stock_probability(value: Any, stock: float) -> bool:
    if value is None:
        return True
    try:
        return abs(float(value) - float(stock)) < 1e-12
    except (TypeError, ValueError):
        return False


def _is_stock_int(value: Any, stock: int) -> bool:
    if value is None:
        return True
    try:
        return int(value) == int(stock)
    except (TypeError, ValueError):
        return False


def _seed_float_if_stock(
    dest: dict[str, Any],
    dest_key: str,
    med: dict[str, Any],
    med_key: str,
    stock: float,
) -> bool:
    """Copy med[med_key] → dest[dest_key] when dest is still at stock. Returns True if seeded."""
    if med_key not in med:
        return False
    current = dest.get(dest_key, stock)
    if not _is_stock_probability(current, stock):
        return False
    dest[dest_key] = float(med[med_key])
    return True


def _seed_detection_delay_if_stock(
    syndromic: dict[str, Any],
    med: dict[str, Any],
) -> bool:
    key = (
        "detection_delay_hours"
        if "detection_delay_hours" in med
        else "detection_delay_epochs"
    )
    if key not in med:
        return False
    if key == "detection_delay_epochs":
        warnings.warn(
            "detection_delay_epochs is deprecated; use detection_delay_hours",
            DeprecationWarning,
            stacklevel=3,
        )
    current = syndromic.get(
        "detection_delay_hours",
        syndromic.get("detection_delay_epochs", _STOCK_DETECTION_DELAY_EPOCHS),
    )
    if not _is_stock_int(current, _STOCK_DETECTION_DELAY_EPOCHS):
        return False
    syndromic["detection_delay_hours"] = float(med[key])
    return True


def _seed_crew_screening_if_stock(
    syndromic: dict[str, Any],
    med: dict[str, Any],
) -> bool:
    key = (
        "crew_screening_interval_hours"
        if "crew_screening_interval_hours" in med
        else "crew_screening_interval_epochs"
    )
    if key not in med:
        return False
    if key == "crew_screening_interval_epochs":
        warnings.warn(
            "crew_screening_interval_epochs is deprecated; "
            "use crew_screening_interval_hours",
            DeprecationWarning,
            stacklevel=3,
        )
    current = syndromic.get(
        "crew_screening_interval_hours",
        syndromic.get(
            "crew_screening_interval_epochs", _STOCK_CREW_SCREENING_INTERVAL,
        ),
    )
    if current is not None and current != _STOCK_CREW_SCREENING_INTERVAL:
        return False
    raw = med[key]
    syndromic["crew_screening_interval_hours"] = (
        None if raw is None else float(raw)
    )
    return True


def apply_voyage_medical_response(
    cfg: dict[str, Any],
    voyage_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Apply platform medical_response into syndromic / fred_behavior.

    Seeds only when the destination key is still at stock defaults so explicit
    Picard/campaign ``config_overrides`` (e.g. none_true sick_call=0) win.
    ``isolation_compliance`` seeds ``fred_behavior.quarantine_compliance``.
    """
    from engines.voyage_itinerary import medical_response_from_config

    med = medical_response_from_config(voyage_cfg)
    if not med:
        return cfg

    syndromic = dict(cfg.get("syndromic") or {})
    fred = dict(cfg.get("fred_behavior") or {})
    changed = False
    changed |= _seed_float_if_stock(
        syndromic, "sick_call_probability", med, "sick_call_probability",
        _STOCK_SICK_CALL_PROBABILITY,
    )
    changed |= _seed_float_if_stock(
        fred, "quarantine_compliance", med, "isolation_compliance",
        _STOCK_QUARANTINE_COMPLIANCE,
    )
    changed |= _seed_detection_delay_if_stock(syndromic, med)
    changed |= _seed_crew_screening_if_stock(syndromic, med)
    if not changed:
        return cfg
    cfg = dict(cfg)
    cfg["syndromic"] = syndromic
    cfg["fred_behavior"] = fred
    return cfg


def build_engine(
    cfg: dict[str, Any],
    seed: int = 42,
    *,
    clock: SimClock | None = None,
) -> KorkinShipEngine:
    """Initialise the real infection-dynamics engine from config.

    Uses the ship_graph zones from spatial_layout.json (or inline
    fallback), mapping them to the Korkin Lab zone types.

    ``clock`` is the run's single natural-history clock; callers that have
    resolved the itinerary pass it so the engine and the itinerary cannot
    disagree about how long an epoch is.
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
        {
            "name": z["name"],
            "type": z["type"],
            "capacity": z.get("traffic", "medium"),
            "max_occupancy": z.get("max_occupancy"),
            "dining_service_type": z.get("dining_service_type", ""),
            "food_contamination_multiplier": z.get("food_contamination_multiplier"),
        }
        for z in zones
    ]

    agent_classes = graph_cfg.get("agent_classes")
    gender_distribution = graph_cfg.get("gender_distribution")

    # An explicit ship_graph.immune_fraction sweeps pre-existing immunity;
    # when unset the engine keeps its default immune_ratio.
    engine_kwargs: dict[str, Any] = {}
    if "immune_fraction" in graph_cfg:
        engine_kwargs["immune_ratio"] = float(graph_cfg["immune_fraction"])

    # VSP threshold confinement is handled by configurable infection counters
    # in the orchestrator, not by the engine's internal check.  The
    # ``vsp_trigger_rule`` governs that engine path when a caller enables it.
    return KorkinShipEngine(
        num_passengers=num_passengers,
        num_crew=num_crew,
        initial_infected=cfg.get("initial_infected", 1),
        zones=engine_zones,
        seed=seed,
        vsp_isolation=False,
        vsp_trigger_rule=load_vsp_trigger_rule(cfg),
        agent_classes=agent_classes,
        gender_distribution=gender_distribution,
        agent_behavior=cfg.get("agent_behavior"),
        clock=clock or SimClock.from_config(cfg),
        **engine_kwargs,
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
        "observed_syndromes",
        "clinical_features",
        "days_since_symptom_onset",
        "cabin_mate_ids",
        "role",
    ):
        if key in a:
            agent_dict[key] = a[key]


def engine_payload_to_schema(
    engine_payload: dict[str, Any],
    isolated_ids: set[int],
    quarantined_ids: set[int],
    quarantine_refusers: set[int],
    pathogen_profiles: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Convert Korkin engine output to telemetry_buffer schema format.

    Applies FRED compliance overrides for isolated, quarantined, and
    non-compliant agents.  Isolated agents (in isolation units) have
    zero shedding; quarantined agents (confined to quarters) retain
    their actual shedding rate and home-zone location.
    """
    from crusher_labs.clinical_presentation import annotate_agent_clinical_presentation

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
        annotate_agent_clinical_presentation(agent_dict, pathogen_profiles)

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

def pathogen_profiles_are_respiratory(
    pathogen_profiles: dict[str, dict[str, Any]] | None,
) -> bool:
    """True when any active pathogen lists a respiratory clinical syndrome."""
    if not pathogen_profiles:
        return False
    for prof in pathogen_profiles.values():
        syndromes = (
            (prof.get("clinical_presentation") or {}).get("syndromes") or []
        )
        for syn in syndromes:
            if "respirat" in str(syn).lower():
                return True
    return False


def role_group_for_agent(agent: dict[str, Any]) -> str:
    role = str(agent.get("role") or "").lower()
    if role in ("crew", "passenger"):
        return role
    a_class = str(agent.get("agent_class") or "").lower()
    if a_class.startswith("crew"):
        return "crew"
    return "passenger"


_role_group_for_agent = role_group_for_agent


def update_ever_ill_ids(
    agents: list[dict[str, Any]],
    ever_ill_ids: set[int],
) -> None:
    """Accumulate agents who have shown symptomatic presentation."""
    from telemetry_buffer.agent_axes import agent_has_symptomatic_presentation

    for agent in agents:
        if agent_has_symptomatic_presentation(agent):
            ever_ill_ids.add(int(agent["agent_id"]))


def update_ever_infected_ids(
    agents: list[dict[str, Any]],
    ever_infected_ids: set[int],
) -> None:
    """Accumulate agents who are currently or were previously infected."""
    for agent in agents:
        infection_state, _, _ = resolve_agent_axes(agent)
        if infection_state in (INFECTION_INFECTED, INFECTION_RECOVERED):
            ever_infected_ids.add(int(agent["agent_id"]))


def update_ever_reported_ids(
    agents: list[dict[str, Any]],
    syn_result: dict[str, Any],
    ever_reported_ids: set[int],
    ever_reported_noise_ids: set[int],
) -> None:
    """Accumulate symptomatic reports and separate background-noise IDs.

    ``syndromic.query_ground_truth`` currently mislabels non-compliant,
    asymptomatic agents in ``true_positive_ids``; intersecting with the
    current symptomatic roster prevents those IDs from becoming reported
    cases while preserving the modality's existing sick-call behavior.
    """
    symptomatic_ids = {
        int(agent["agent_id"])
        for agent in agents
        if agent_has_symptomatic_presentation(agent)
    }
    ever_reported_ids.update(
        symptomatic_ids.intersection(
            int(aid) for aid in syn_result.get("true_positive_ids", [])
        ),
    )
    ever_reported_noise_ids.update(int(aid) for aid in syn_result.get("noise_ids", []))


def _compute_group_rates(
    agents: list[dict[str, Any]],
    id_set: set[int],
) -> dict[str, float]:
    if not agents:
        return {"overall": 0.0, "passenger": 0.0, "crew": 0.0, "max_group": 0.0}

    groups: dict[str, list[int]] = {"passenger": [], "crew": []}
    for agent in agents:
        groups[_role_group_for_agent(agent)].append(int(agent["agent_id"]))

    def _rate(ids: list[int]) -> float:
        return sum(aid in id_set for aid in ids) / len(ids) if ids else 0.0

    passenger = _rate(groups["passenger"])
    crew = _rate(groups["crew"])
    return {
        "overall": len(id_set) / len(agents),
        "passenger": passenger,
        "crew": crew,
        "max_group": max(passenger, crew),
    }


def compute_group_attack_rates(
    agents: list[dict[str, Any]],
    ever_ill_ids: set[int],
) -> dict[str, float]:
    """Cumulative attack rates (ever-ill / population) overall and by role group."""
    return _compute_group_rates(agents, ever_ill_ids)


def compute_group_rates_for_ids(
    agents: list[dict[str, Any]],
    ids: set[int],
) -> dict[str, float]:
    """Return overall and role-group rates for an arbitrary agent ID set."""
    return _compute_group_rates(agents, ids)


def update_cumulative_confirmed_cases(
    clin_qpcr_results: dict[Any, dict[str, Any]] | None,
    clin_rdt_results: dict[Any, dict[str, Any]] | None,
    cumulative_confirmed_case_ids: set[int],
) -> int:
    """Add clinically confirmed agents (qPCR detect or RDT positive)."""
    for aid, data in (clin_qpcr_results or {}).items():
        if data.get("detected") or (
            data.get("ct_value") is not None and float(data["ct_value"]) <= 35.0
        ):
            cumulative_confirmed_case_ids.add(int(aid))
    for aid, data in (clin_rdt_results or {}).items():
        if data.get("positive"):
            cumulative_confirmed_case_ids.add(int(aid))
    return len(cumulative_confirmed_case_ids)


def _escalation_delay_epochs(
    esc_cfg: dict[str, Any],
    target_status: str,
    clock: SimClock | None = None,
) -> int:
    from orchestrator_types import (
        STATUS_ALERT,
        STATUS_CONFIRMED,
        STATUS_LOCKDOWN,
        STATUS_SUSPECTED,
    )

    latency = esc_cfg.get("decision_latency") or {}
    key_by_status = {
        STATUS_ALERT: ("alert_delay_hours", "alert_delay_epochs"),
        STATUS_SUSPECTED: ("suspected_delay_hours", "suspected_delay_epochs"),
        STATUS_CONFIRMED: ("confirmed_delay_hours", "confirmed_delay_epochs"),
        STATUS_LOCKDOWN: ("lockdown_delay_hours", "lockdown_delay_epochs"),
    }
    keys = key_by_status.get(target_status)
    if keys is None:
        return 0
    return config_epochs_for_hours(
        latency, keys[0], keys[1], clock or SimClock.from_config({}),
    ) or 0


def _lockdown_threshold(esc_cfg: dict[str, Any]) -> float | None:
    """Return lockdown attack-rate threshold, or None if lockdown disabled."""
    raw = esc_cfg.get("lockdown_attack_rate", 0.05)
    if raw is None or raw == "never":
        return None
    return float(raw)


def _escalation_ar_thresholds(
    esc_cfg: dict[str, Any],
    *,
    respiratory_mode: bool,
) -> tuple[float, float, int | None]:
    resp = esc_cfg.get("respiratory_overrides") or {}
    if respiratory_mode:
        suspect_ar = float(resp.get(
            "suspect_attack_rate",
            esc_cfg.get("suspect_attack_rate", 0.01),
        ))
        confirm_ar = float(esc_cfg.get("confirm_attack_rate", 0.03))
        alert_confirmed: int | None = int(resp.get("alert_confirmed_cases", 1))
    else:
        suspect_ar = float(esc_cfg.get("suspect_attack_rate", 0.02))
        confirm_ar = float(esc_cfg.get("confirm_attack_rate", 0.03))
        alert_confirmed = None
    return suspect_ar, confirm_ar, alert_confirmed


def _propose_alert_level(
    trigger_status: str,
    *,
    sick_calls: int,
    alert_threshold: int,
    respiratory_mode: bool,
    alert_confirmed: int | None,
    cumulative_confirmed_cases: int,
) -> str:
    from orchestrator_types import STATUS_ALERT

    if sick_calls >= alert_threshold:
        return STATUS_ALERT
    if (
        respiratory_mode
        and alert_confirmed is not None
        and cumulative_confirmed_cases >= alert_confirmed
    ):
        return STATUS_ALERT
    return trigger_status


def propose_escalation_level(
    trigger_status: str,
    syndromic_result: dict[str, Any],
    cfg: dict[str, Any],
    *,
    attack_rate: float = 0.0,
    cumulative_confirmed_cases: int = 0,
    respiratory_mode: bool = False,
) -> str:
    """Propose the highest escalation level justified by current signals.

    Does not apply decision latency — callers queue the transition separately.
    """
    from orchestrator_types import (
        STATUS_ALERT,
        STATUS_CONFIRMED,
        STATUS_LOCKDOWN,
        STATUS_RANK,
        STATUS_SUSPECTED,
    )

    esc_cfg = cfg.get("escalation", {})
    # Backward-compatible alias: syndromic_suspect_threshold → alert_sick_call_threshold
    alert_threshold = int(
        esc_cfg.get(
            "alert_sick_call_threshold",
            esc_cfg.get("syndromic_suspect_threshold", 3),
        ),
    )
    suspect_ar, confirm_ar, alert_confirmed = _escalation_ar_thresholds(
        esc_cfg, respiratory_mode=respiratory_mode,
    )
    lockdown_ar = _lockdown_threshold(esc_cfg)

    sick_calls = int(syndromic_result.get("sick_call_count", 0))
    current_rank = STATUS_RANK.get(trigger_status, 0)

    # Advance at most one level per evaluation (organizational stair-step).
    # Latency then applies to that single step.
    if current_rank < STATUS_RANK[STATUS_ALERT]:
        return _propose_alert_level(
            trigger_status,
            sick_calls=sick_calls,
            alert_threshold=alert_threshold,
            respiratory_mode=respiratory_mode,
            alert_confirmed=alert_confirmed,
            cumulative_confirmed_cases=cumulative_confirmed_cases,
        )

    if current_rank < STATUS_RANK[STATUS_SUSPECTED]:
        if attack_rate >= suspect_ar:
            return STATUS_SUSPECTED
        return trigger_status

    if current_rank < STATUS_RANK[STATUS_CONFIRMED]:
        if attack_rate >= confirm_ar:
            return STATUS_CONFIRMED
        return trigger_status

    if current_rank < STATUS_RANK[STATUS_LOCKDOWN]:
        if lockdown_ar is not None and attack_rate >= lockdown_ar:
            return STATUS_LOCKDOWN
        return trigger_status

    return trigger_status


def _release_pending_escalation(
    current_status: str,
    epoch: int,
    pending: dict[str, Any] | None,
    esc_cfg: dict[str, Any],
    clock: SimClock | None = None,
) -> tuple[str, dict[str, Any] | None]:
    from orchestrator_types import STATUS_RANK

    effective = current_status
    updated_pending = dict(pending) if pending else None
    if updated_pending is None:
        return effective, updated_pending
    target = str(updated_pending.get("to", current_status))
    triggered_at = int(updated_pending.get("epoch_triggered", epoch))
    delay = _escalation_delay_epochs(esc_cfg, target, clock)
    if epoch >= triggered_at + delay:
        if STATUS_RANK.get(target, 0) > STATUS_RANK.get(effective, 0):
            effective = target
        updated_pending = None
    return effective, updated_pending


def _queue_escalation_transition(
    effective: str,
    proposed_status: str,
    epoch: int,
    updated_pending: dict[str, Any] | None,
    esc_cfg: dict[str, Any],
    clock: SimClock | None = None,
) -> tuple[str, dict[str, Any] | None]:
    from orchestrator_types import STATUS_RANK

    if STATUS_RANK.get(proposed_status, 0) <= STATUS_RANK.get(effective, 0):
        return effective, updated_pending
    pending_target = (
        str(updated_pending["to"]) if updated_pending else effective
    )
    if STATUS_RANK.get(proposed_status, 0) <= STATUS_RANK.get(pending_target, 0):
        return effective, updated_pending
    delay = _escalation_delay_epochs(esc_cfg, proposed_status, clock)
    if delay <= 0:
        return proposed_status, None
    return effective, {
        "to": proposed_status,
        "epoch_triggered": epoch,
    }


def apply_escalation_latency(
    current_status: str,
    proposed_status: str,
    epoch: int,
    pending: dict[str, Any] | None,
    cfg: dict[str, Any],
    *,
    clock: SimClock | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Queue escalation transitions and release them after decision latency.

    Returns ``(effective_status, updated_pending)``.
    """
    esc_cfg = cfg.get("escalation", {})
    effective, updated_pending = _release_pending_escalation(
        current_status, epoch, pending, esc_cfg, clock,
    )
    return _queue_escalation_transition(
        effective, proposed_status, epoch, updated_pending, esc_cfg, clock,
    )


def check_escalation(
    trigger_status: str,
    syndromic_result: dict[str, Any],
    pcr_result: dict[str, Any] | None,
    cfg: dict[str, Any],
    *,
    agents: list[dict[str, Any]] | None = None,
    ever_ill_ids: set[int] | None = None,
    cumulative_confirmed_cases: int = 0,
    epoch: int = 0,
    escalation_pending: dict[str, Any] | None = None,
    respiratory_mode: bool = False,
    clock: SimClock | None = None,
) -> tuple[str, dict[str, Any] | None, dict[str, float]]:
    """Evaluate escalation thresholds with optional decision latency.

    Returns ``(effective_status, updated_pending, attack_rates)``.

    Attack-rate thresholds (CDC VSP-aligned) drive SUSPECTED / CONFIRMED /
    LOCKDOWN. BASELINE → ALERT uses sick-call count (or respiratory confirmed
    cases). Organizational decision latency is applied via *escalation_pending*.

    *pcr_result* is retained for API compatibility; surface PCR no longer
    alone promotes to CONFIRMED once attack-rate keys are in use.
    """
    del pcr_result  # API compat; AR + clinical confirms replace surface PCR gate

    ill_ids = ever_ill_ids if ever_ill_ids is not None else set()
    if agents is not None:
        update_ever_ill_ids(agents, ill_ids)
        rates = compute_group_attack_rates(agents, ill_ids)
        attack_rate = float(rates["max_group"])
    else:
        rates = {"overall": 0.0, "passenger": 0.0, "crew": 0.0, "max_group": 0.0}
        attack_rate = 0.0

    proposed = propose_escalation_level(
        trigger_status,
        syndromic_result,
        cfg,
        attack_rate=attack_rate,
        cumulative_confirmed_cases=cumulative_confirmed_cases,
        respiratory_mode=respiratory_mode,
    )
    effective, pending = apply_escalation_latency(
        trigger_status, proposed, epoch, escalation_pending, cfg, clock=clock,
    )
    return effective, pending, rates


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
        profiles = {
            str(pid): dict(prof) for pid, prof in resolved.items()
        }
        _validate_symptom_severity_profiles(profiles)
        return _normalize_profile_units(profiles)

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
    _validate_symptom_severity_profiles(profiles)
    return _normalize_profile_units(profiles)


def _validate_symptom_severity_profiles(
    profiles: dict[str, dict[str, Any]],
) -> None:
    """Validate the authored five-state severity and observation models."""
    states = [
        "asymptomatic",
        "subclinical",
        "mild",
        "moderate",
        "severe_critical",
    ]
    for pathogen_id, profile in profiles.items():
        if "symptom_severity" in profile:
            raise ValueError(
                f"{pathogen_id}.symptom_severity is retired; use severity_model",
            )
        severity = profile.get("severity_model")
        observation = profile.get("observation_model")
        if severity is None and observation is None:
            continue
        if severity is None or observation is None:
            raise ValueError(
                f"{pathogen_id}.severity_model and observation_model must be paired",
            )
        if not isinstance(severity, dict):
            raise ValueError(
                f"{pathogen_id}.severity_model must be an object",
            )
        actual_states = severity.get("states")
        if actual_states != states:
            raise ValueError(
                f"{pathogen_id}.severity_model.states must equal {states}",
            )
        probabilities = severity.get("base_probabilities")
        if not isinstance(probabilities, list) or len(probabilities) != 5:
            raise ValueError(
                f"{pathogen_id}.severity_model.base_probabilities must have length 5",
            )
        values = [float(value) for value in probabilities]
        if not all(np.isfinite(value) and 0.0 <= value <= 1.0 for value in values):
            raise ValueError(
                f"{pathogen_id}.severity_model.base_probabilities must be finite and bounded",
            )
        if not np.isclose(sum(values), 1.0):
            raise ValueError(
                f"{pathogen_id}.severity_model.base_probabilities must sum to 1.0",
            )
        if values[0] >= 1.0:
            raise ValueError(
                f"{pathogen_id}.severity_model.base_probabilities[0] must be < 1",
            )
        if not isinstance(observation, dict):
            raise ValueError(
                f"{pathogen_id}.observation_model must be an object",
            )
        arrays = (
            "syndrome_case_eligibility_by_severity",
            "reporting_probability_by_severity_pre_recognition",
            "reporting_probability_by_severity_post_recognition",
            "lab_sampling_probability_by_severity",
        )
        for key in arrays:
            array = observation.get(key)
            if not isinstance(array, list) or len(array) != 5:
                raise ValueError(
                    f"{pathogen_id}.observation_model.{key} must have length 5",
                )
            numbers = [float(value) for value in array]
            if not all(
                np.isfinite(value) and 0.0 <= value <= 1.0
                for value in numbers
            ):
                raise ValueError(
                    f"{pathogen_id}.observation_model.{key} must be finite and bounded",
                )
            if numbers[0] != 0.0:
                raise ValueError(
                    f"{pathogen_id}.observation_model.{key}[0] must equal 0.0",
                )
            if any(left > right for left, right in zip(numbers, numbers[1:])):
                raise ValueError(
                    f"{pathogen_id}.observation_model.{key} must be non-decreasing",
                )
        window = observation.get("episode_reporting_window_days")
        if window is None or not np.isfinite(float(window)) or float(window) <= 0:
            raise ValueError(
                f"{pathogen_id}.observation_model.episode_reporting_window_days "
                "must be positive",
            )
        if severity.get("fatality_probability_by_severity") is not None:
            raise NotImplementedError(
                f"{pathogen_id}: severity-conditioned fatality is not implemented",
            )
        if observation.get("assay_sensitivity_by_time_since_infection") is not None:
            raise NotImplementedError(
                f"{pathogen_id}: time-varying assay sensitivity is not implemented",
            )


def _normalize_profile_units(
    profiles: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Warn once when a profile uses a retired epoch-rate key."""
    aliases = (
        ("food_contamination", "growth_rate_per_epoch"),
        ("food_contamination", "decay_rate_per_epoch"),
        ("environmental_contamination", "colonization_rate_per_epoch"),
        ("environmental_contamination", "spore_decay_rate_per_epoch"),
        ("environmental_contamination", "exposure_probability_per_epoch"),
        ("strain_evolution", "within_host_mutation_rate"),
        ("strain_evolution", "recombination_rate"),
    )
    normalized = {}
    for pathogen_id, profile in profiles.items():
        copied = dict(profile)
        for block_name, old_key in aliases:
            block = copied.get(block_name)
            if isinstance(block, dict) and old_key in block:
                warnings.warn(
                    f"{pathogen_id}.{block_name}.{old_key} is deprecated; "
                    "use the corresponding per-day key",
                    DeprecationWarning,
                    stacklevel=2,
                )
        normalized[str(pathogen_id)] = copied
    return normalized


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
            nonsus_frac = float(prof.get("innate_nonsusceptible_fraction", 0.0) or 0.0)
            if nonsus_frac > 0.0 and rng.random() < nonsus_frac:
                agent.susceptibility_multiplier[pid] = 0.0

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
            # Also host biology, not only a susceptibility multiplier: an
            # immunosuppressed host incubates longer as well as infecting easier.
            agent.immunocompromised = True
            for pid in pathogen_profiles:
                # Preserve innate nonsusceptibility (multiplier 0).
                if agent.susceptibility_multiplier.get(pid, 1.0) > 0.0:
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
                # The profile field is days post infection; the record is epochs.
                epochs_infected = int(round(engine.clock.epochs_for_days(
                    float(prof.get("initial_time_infected", 0)),
                )))
                for agent in chosen:
                    agent.infect_with_pathogen(
                        pid, 1e4, 0,
                        time_infected=epochs_infected, rng=rng, profile=prof,
                    )
                    print(f"  Seeded {pid} -> agent {agent.agent_id}")
    print()

    return immunocompromised_ids


# ── Observation engine initialization ────────────────────────────────────

def _build_strain_typing(
    cfg: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]] | None,
    *,
    seed: int,
) -> Any | None:
    """Clinical amplicon typing engine, or ``None`` when strains are untracked.

    Gated on ``variant_surveillance.enabled``: without a strain registry there
    are no lineages to type, and the pathogen-level call is the whole result.
    """
    from crusher_labs.modalities.clinical_strain_typing import (
        ClinicalStrainTyping,
        SequencingAssay,
    )

    if not (cfg.get("variant_surveillance", {}) or {}).get("enabled", False):
        return None
    assays = SequencingAssay.load_profiles(pathogen_profiles or {})
    if not assays:
        return None
    return ClinicalStrainTyping(assays, rng=np.random.default_rng(seed))


def init_observation_engine(
    cfg: dict[str, Any],
    seed: int,
    *,
    pathogen_profiles: dict[str, dict[str, Any]] | None = None,
    clock: SimClock | None = None,
) -> ObservationEngine:
    """Initialise diagnostic instruments and the lab notebook."""
    from crusher_labs.clinical_instrument_params import (
        clinical_instruments_config_path,
        load_clinical_instrument_params,
    )
    from crusher_labs.observation_core import (
        ClinicalImpression,
        ClinicalMultiplexPanel,
    )

    obs_cfg_path = resolve_repo_path(REPO_ROOT, "data/config/logging_profile.json")
    fidelity_name, _fidelity, logging_config = load_logging_profile(obs_cfg_path)
    lab_notebook_enabled = logging_config.get("lab_notebook", {}).get("enabled", True)

    qc_cfg = logging_config.get("quality_control", {})
    xcontam_rate = qc_cfg.get("cross_contamination_rate", 0.0001)
    ctrl_intensity = qc_cfg.get("control_run_intensity", "medium")

    clin_params = load_clinical_instrument_params(
        clinical_instruments_config_path(cfg),
        repo_root=REPO_ROOT,
    )

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
        instrument_params=clin_params,
    )
    clin_multiplex = ClinicalMultiplexPanel(
        instrument_params=clin_params,
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed + 3),
    )
    clin_impression = ClinicalImpression(
        instrument_params=clin_params,
        rng=np.random.default_rng(seed + 4),
    )
    clin_qpcr = ClinicalQPCR(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
        instrument_params=clin_params,
    )
    clin_microbio = ClinicalMicrobiology(
        cross_contamination_rate=xcontam_rate,
        control_intensity=ctrl_intensity,
        rng=np.random.default_rng(seed),
        instrument_params=clin_params,
        pathogen_profiles=pathogen_profiles,
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
            strain_typing=_build_strain_typing(
                cfg, pathogen_profiles, seed=seed + 9,
            ),
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
        clock=clock or SimClock.from_config(cfg),
    )
    turnaround = InstrumentTurnaroundQueue(tat_registry)

    print_observation_engine(fidelity_name, xcontam_rate, ctrl_intensity, lab_notebook_enabled)

    return ObservationEngine(
        air_sniffer=air_sniffer,
        surface_swab=surface_swab,
        wastewater_seq=wastewater_seq,
        clin_rdt=clin_rdt,
        clin_multiplex=clin_multiplex,
        clin_impression=clin_impression,
        clin_qpcr=clin_qpcr,
        clin_microbio=clin_microbio,
        clinical_correlation=clinical_correlation,
        notebook=notebook,
        fidelity_name=fidelity_name,
        lab_notebook_enabled=lab_notebook_enabled,
        turnaround=turnaround,
        long_read=long_read_inst,
        clinical_instrument_params=clin_params,
        pathogen_profiles=pathogen_profiles,
        outbreak_aware=bool(cfg.get("clinical_instruments", {}).get("outbreak_aware", False)),
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
    run_clock = SimClock.from_config(_cfg)
    standing_protocols = load_protocols(protocols_cfg_path, clock=run_clock)
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
        clock=run_clock,
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
