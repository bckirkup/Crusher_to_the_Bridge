"""
telemetry_buffer.fields
~~~~~~~~~~~~~~~~~~~~~~~

Typed contract for the per-epoch telemetry payload.

``schemas/simulation_history.schema.json`` is the source of truth for the
field names of an epoch record; this module exposes those names as
constants and ``TypedDict`` shapes so consumers do not couple to raw
string literals.  ``tests/test_telemetry_fields.py`` checks the
constants against the schema, so a producer-side rename fails there
instead of silently degrading every ``.get()`` default downstream.

Field-name constants are grouped by the record they index:

* ``RECORD_*`` – top-level ``EpochRecord`` keys
* ``AGENT_*`` – per-agent ``AgentState`` keys
* ``ZONE_*`` – per-zone ``ZoneState`` keys
* ``SUMMARY_*`` / ``COST_*`` / ``CASCADE_*`` / ``WEARABLE_*`` /
  ``VOYAGE_*`` / ``TRACING_*`` – nested block keys
"""

from __future__ import annotations

from typing import Any, Final, Mapping, TypedDict

# ── EpochRecord ──────────────────────────────────────────────────────────

RECORD_EPOCH: Final = "epoch"
RECORD_TRIGGER_STATUS: Final = "trigger_status"
RECORD_SUMMARY: Final = "summary"
RECORD_SPACES: Final = "spaces"
RECORD_AGENTS: Final = "agents"
RECORD_CONTACT_TRACING: Final = "contact_tracing"
RECORD_MULTI_PATHOGEN: Final = "multi_pathogen"
RECORD_STRAIN_CENSUS: Final = "strain_census"
RECORD_REACTIVE_PROTOCOLS: Final = "reactive_protocols"
RECORD_COST_ACCOUNTING: Final = "cost_accounting"
RECORD_OBSERVATION_ENGINE: Final = "observation_engine"
RECORD_MICROFLORA_SHIFTS: Final = "microflora_shifts"
RECORD_MICROFLORA_SEQUENCING: Final = "microflora_sequencing"
RECORD_WEARABLE_MONITORING: Final = "wearable_monitoring"
RECORD_DIAGNOSTIC_CASCADE: Final = "diagnostic_cascade"
RECORD_HVAC: Final = "hvac"
RECORD_CRUSHER_OPS: Final = "crusher_ops"
# Emitted by orchestrator_record but not yet declared in the schema.
RECORD_INFECTION_COUNTERS: Final = "infection_counters"
RECORD_VOYAGE_EPOCH: Final = "voyage_epoch"

RECORD_REQUIRED: Final = (
    RECORD_EPOCH,
    RECORD_SUMMARY,
    RECORD_SPACES,
    RECORD_AGENTS,
    RECORD_TRIGGER_STATUS,
)

# ── AgentState ───────────────────────────────────────────────────────────

AGENT_ID: Final = "agent_id"
AGENT_INFECTION_STATE: Final = "infection_state"
AGENT_SYMPTOM_PRESENTATION: Final = "symptom_presentation"
AGENT_COMPLIANCE_STATUS: Final = "compliance_status"
AGENT_LEGACY_SYMPTOM_STATUS: Final = "symptom_status"
AGENT_LOCATION: Final = "location"
AGENT_SHEDDING_RATE: Final = "shedding_rate"
AGENT_DAY_OF_INFECTION: Final = "day_of_infection"
AGENT_INFECTION_PATHWAY: Final = "infection_pathway"
AGENT_CLASS: Final = "agent_class"
AGENT_GENDER: Final = "gender"
AGENT_SUSCEPTIBILITY_MULTIPLIER: Final = "susceptibility_multiplier"
AGENT_MICROFLORA_DISRUPTION: Final = "microflora_disruption"
AGENT_ACTIVE_PATHOGEN_IDS: Final = "active_pathogen_ids"
# Full-retention extras emitted by orchestrator_record / the engine.
AGENT_ROLE: Final = "role"
AGENT_CABIN_MATE_IDS: Final = "cabin_mate_ids"
AGENT_PATHOGEN_INFECTIONS: Final = "pathogen_infections"

# ── ZoneState ────────────────────────────────────────────────────────────

ZONE_PATHOGEN_MASS: Final = "pathogen_mass"
ZONE_PATHOGEN_MASS_BY_ID: Final = "pathogen_mass_by_id"
ZONE_CONCENTRATION_PER_M3: Final = "concentration_per_m3"
ZONE_VOLUME_M3: Final = "volume_m3"
ZONE_MICROBIOME_ID: Final = "microbiome_id"

# ── summary block ────────────────────────────────────────────────────────

SUMMARY_SUSCEPTIBLE: Final = "susceptible"
SUMMARY_INFECTED: Final = "infected"
SUMMARY_ISOLATED: Final = "isolated"
SUMMARY_RECOVERED: Final = "recovered"
SUMMARY_IMMUNE: Final = "immune"
SUMMARY_SYMPTOMATIC: Final = "symptomatic"
SUMMARY_SICK_CALL_COUNT: Final = "sick_call_count"
SUMMARY_DISRUPTED_MICROFLORA_COUNT: Final = "disrupted_microflora_count"
SUMMARY_QUARANTINE_REFUSERS: Final = "quarantine_refusers"
# Emitted by orchestrator_record but not yet declared in the schema.
SUMMARY_QUARANTINED: Final = "quarantined"
SUMMARY_CUMULATIVE_REPORTED_CASES: Final = "cumulative_reported_cases"
SUMMARY_CUMULATIVE_REPORTED_CASES_PASSENGER: Final = "cumulative_reported_cases_passenger"
SUMMARY_CUMULATIVE_REPORTED_CASES_CREW: Final = "cumulative_reported_cases_crew"
SUMMARY_CUMULATIVE_REPORTED_NOISE_CASES: Final = "cumulative_reported_noise_cases"
SUMMARY_CUMULATIVE_EVER_ILL: Final = "cumulative_ever_ill"
SUMMARY_CUMULATIVE_EVER_ILL_PASSENGER: Final = "cumulative_ever_ill_passenger"
SUMMARY_CUMULATIVE_EVER_ILL_CREW: Final = "cumulative_ever_ill_crew"
SUMMARY_CUMULATIVE_EVER_INFECTED: Final = "cumulative_ever_infected"
SUMMARY_CUMULATIVE_EVER_INFECTED_PASSENGER: Final = "cumulative_ever_infected_passenger"
SUMMARY_CUMULATIVE_EVER_INFECTED_CREW: Final = "cumulative_ever_infected_crew"
SUMMARY_PASSENGER_COMPLEMENT: Final = "passenger_complement"
SUMMARY_CREW_COMPLEMENT: Final = "crew_complement"
SUMMARY_INFECTION_ATTACK_RATE_PASSENGER: Final = "infection_attack_rate_passenger"
SUMMARY_INFECTION_ATTACK_RATE_CREW: Final = "infection_attack_rate_crew"
SUMMARY_REPORTED_CASE_RATE_PASSENGER: Final = "reported_case_rate_passenger"
SUMMARY_REPORTED_CASE_RATE_CREW: Final = "reported_case_rate_crew"
SUMMARY_EVER_ILL_RATE_PASSENGER: Final = "ever_ill_rate_passenger"
SUMMARY_EVER_ILL_RATE_CREW: Final = "ever_ill_rate_crew"
SUMMARY_SANITARY_ACTIVITY: Final = "sanitary_activity"

# ── reactive_protocols block ─────────────────────────────────────────────

PROTOCOLS_ACTIVE: Final = "active_protocols"
PROTOCOLS_MERGED_MODIFIERS: Final = "merged_modifiers"
PROTOCOLS_STOPLIGHTS: Final = "stoplights"
PROTOCOLS_TRIGGER_STATUS: Final = "trigger_status"

# ── cost_accounting block ────────────────────────────────────────────────

COST_EPOCH: Final = "epoch"
COST_TOTAL_FINANCIAL_USD: Final = "total_financial_usd"
COST_TOTAL_LABOR_HOURS: Final = "total_labor_hours"
COST_FINANCIAL_BALANCE_REMAINING: Final = "financial_balance_remaining"
COST_LABOR_HOURS_REMAINING: Final = "labor_hours_remaining"
COST_ENTRIES_COUNT: Final = "entries_count"
COST_OPERATIONAL_IMPACT_EPOCH: Final = "operational_impact_epoch"
COST_OPERATIONAL_IMPACT_CUMULATIVE: Final = "operational_impact_cumulative"
COST_OPERATIONAL_IMPACT_BREAKDOWN: Final = "operational_impact_breakdown"

# ── diagnostic_cascade block ─────────────────────────────────────────────

CASCADE_NEW_TIER0_AGENTS: Final = "new_tier0_agents"
CASCADE_NEW_TIER1_AGENTS: Final = "new_tier1_agents"
CASCADE_TIER_ADVANCEMENTS: Final = "tier_advancements"
CASCADE_TESTS_ORDERED: Final = "tests_ordered"
CASCADE_CONFINEMENTS_ORDERED: Final = "confinements_ordered"
CASCADE_WEARABLE_OFFERS: Final = "wearable_offers"
CASCADE_FLEET_SOPS_UNLOCKED: Final = "fleet_sops_unlocked"

# ── wearable_monitoring block ────────────────────────────────────────────

WEARABLE_TOTAL_MONITORED: Final = "total_monitored"
WEARABLE_TOTAL_STAFF_VISIBLE: Final = "total_staff_visible"
WEARABLE_FEVER_COUNT: Final = "fever_count"
WEARABLE_FEVER_RATE: Final = "fever_rate"
WEARABLE_ANOMALY_COUNT: Final = "anomaly_count"
WEARABLE_ANOMALY_RATE: Final = "anomaly_rate"
WEARABLE_CHANNEL_ANOMALY_COUNTS: Final = "channel_anomaly_counts"
WEARABLE_STAFF_VISIBLE_AGENTS: Final = "staff_visible_agents"
WEARABLE_WEARER_ONLY_AGENTS: Final = "wearer_only_agents"
WEARABLE_VISIBILITY_BREAKDOWN: Final = "visibility_breakdown"
WEARABLE_DEVICE_DEPLOYMENT_COUNTS: Final = "device_deployment_counts"

# ── contact_tracing block ────────────────────────────────────────────────

TRACING_TRANSMISSION_EVENTS: Final = "transmission_events"

# ── voyage_epoch block (itinerary; not in the schema) ────────────────────

VOYAGE_DAY: Final = "voyage_day"
VOYAGE_PORT: Final = "port"

# ── infection_counters block (not in the schema) ─────────────────────────

COUNTER_PASSENGER_REPORTED_CASE_RATE: Final = "passenger_reported_case_rate"
COUNTER_VALUE: Final = "value"
COUNTER_NEWLY_CONFINED: Final = "newly_confined"
COUNTER_EXCEEDED: Final = "exceeded"

# ── observation_engine block ─────────────────────────────────────────────

OBSERVATION_SURFACE_SWAB: Final = "surface_swab"
OBSERVATION_SURFACE_MASS: Final = "surface_mass"


# ── Typed shapes ─────────────────────────────────────────────────────────


class AgentState(TypedDict, total=False):
    agent_id: int
    infection_state: str
    symptom_presentation: str
    compliance_status: str
    symptom_status: str
    location: str
    shedding_rate: float
    day_of_infection: int
    infection_pathway: str
    agent_class: str
    gender: str
    susceptibility_multiplier: dict[str, float]
    microflora_disruption: float
    active_pathogen_ids: list[str]
    role: str
    cabin_mate_ids: list[int]
    pathogen_infections: dict[str, Any]


class ZoneState(TypedDict, total=False):
    pathogen_mass: float
    pathogen_mass_by_id: dict[str, float]
    concentration_per_m3: float
    volume_m3: float
    microbiome_id: str


class EpochRecord(TypedDict, total=False):
    epoch: int
    trigger_status: str
    summary: dict[str, Any]
    spaces: dict[str, ZoneState]
    agents: list[AgentState]
    contact_tracing: dict[str, Any]
    multi_pathogen: dict[str, Any]
    strain_census: list[dict[str, Any]]
    reactive_protocols: dict[str, Any]
    cost_accounting: dict[str, Any]
    observation_engine: dict[str, Any]
    microflora_shifts: dict[str, Any]
    microflora_sequencing: dict[str, Any]
    wearable_monitoring: dict[str, Any]
    diagnostic_cascade: dict[str, Any]
    hvac: dict[str, Any]
    crusher_ops: dict[str, Any]
    infection_counters: dict[str, Any]
    voyage_epoch: dict[str, Any]


class PublicSnapshot(TypedDict, total=False):
    """Host-provided public snapshot consumed by ``DecisionRound.solve``."""

    epoch: int
    agents: list[AgentState]
    summary: dict[str, Any]
    stoplights: dict[str, Any]
    trigger_status: str | None
    cost_accounting: dict[str, Any]
    observation_engine: dict[str, Any]


PUBLIC_EPOCH: Final = "epoch"
PUBLIC_AGENTS: Final = RECORD_AGENTS
PUBLIC_SUMMARY: Final = RECORD_SUMMARY
PUBLIC_STOPLIGHTS: Final = PROTOCOLS_STOPLIGHTS
PUBLIC_TRIGGER_STATUS: Final = RECORD_TRIGGER_STATUS
PUBLIC_COST_ACCOUNTING: Final = RECORD_COST_ACCOUNTING
PUBLIC_OBSERVATION_ENGINE: Final = RECORD_OBSERVATION_ENGINE


# ── Accessors ────────────────────────────────────────────────────────────


def record_agents(record: Mapping[str, Any]) -> list[AgentState]:
    agents = record.get(RECORD_AGENTS) or []
    return agents if isinstance(agents, list) else []


def record_spaces(record: Mapping[str, Any]) -> dict[str, ZoneState]:
    spaces = record.get(RECORD_SPACES) or {}
    return spaces if isinstance(spaces, dict) else {}


def record_block(record: Mapping[str, Any], key: str) -> dict[str, Any]:
    """Return a nested object block (``summary``, ``cost_accounting``, ...)."""
    block = record.get(key) or {}
    return block if isinstance(block, dict) else {}


def record_epoch(record: Mapping[str, Any], default: int = 0) -> int:
    return int(record.get(RECORD_EPOCH, default))


def record_trigger_status(record: Mapping[str, Any], default: Any = None) -> Any:
    """Trigger status, falling back to the ``reactive_protocols`` copy."""
    if RECORD_TRIGGER_STATUS in record:
        return record[RECORD_TRIGGER_STATUS]
    return record_block(record, RECORD_REACTIVE_PROTOCOLS).get(
        PROTOCOLS_TRIGGER_STATUS, default,
    )


def record_stoplights(record: Mapping[str, Any]) -> dict[str, Any]:
    return record_block(
        record_block(record, RECORD_REACTIVE_PROTOCOLS), PROTOCOLS_STOPLIGHTS,
    )


def agent_id(agent: Mapping[str, Any]) -> int:
    return int(agent[AGENT_ID])


def agent_location(agent: Mapping[str, Any], default: str = "") -> str:
    return str(agent.get(AGENT_LOCATION) or default)


def zone_pathogen_mass(zone: Mapping[str, Any]) -> float:
    """Total pathogen mass; per-pathogen dicts are summed."""
    mass = zone.get(ZONE_PATHOGEN_MASS, 0.0)
    if isinstance(mass, dict):
        return float(sum(mass.values()))
    return float(mass or 0.0)


def public_view(last: Mapping[str, Any], epoch: int | None = None) -> PublicSnapshot:
    """Build the decision-engine public snapshot from the latest epoch record.

    This is the single place that maps Bridge/Picard simulation-history
    fields onto the snapshot shape ``ObservationModel.build`` reads.
    ``epoch`` overrides the record's own epoch (the runner passes the epoch
    about to be decided, which is one ahead of ``last``).
    """
    return {
        PUBLIC_EPOCH: record_epoch(last) if epoch is None else epoch,
        PUBLIC_AGENTS: record_agents(last),
        PUBLIC_SUMMARY: record_block(last, RECORD_SUMMARY),
        PUBLIC_STOPLIGHTS: record_stoplights(last),
        PUBLIC_TRIGGER_STATUS: record_trigger_status(last),
        PUBLIC_COST_ACCOUNTING: record_block(last, RECORD_COST_ACCOUNTING),
        PUBLIC_OBSERVATION_ENGINE: record_block(last, RECORD_OBSERVATION_ENGINE),
    }
