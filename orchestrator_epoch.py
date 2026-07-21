"""
orchestrator_epoch.py – Per-epoch simulation step functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each function handles one discrete phase of the epoch loop:
FRED compliance, mid-cruise introductions, infection progression,
observation sampling, quarantine confinement, cost accounting,
and microflora disruption computation.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    InfectionStatus,
    IllnessStatus,
)
from engines.wearable_monitor import WearableMonitor
from crusher_labs.modalities.wearable import WearableDataStream
from telemetry_buffer.agent_axes import (
    agent_requires_confinement,
    agent_is_infected,
    agent_has_symptomatic_presentation,
    INFECTION_RECOVERED,
    INFECTION_SUSCEPTIBLE,
)
from orchestrator_types import (
    STATUS_SUSPECTED,
    STATUS_CONFIRMED,
    LOCATION_ISOLATED,
    DEFAULT_AIRBORNE_FRACTION,
    DEFAULT_SURFACE_FRACTION,
    DEFAULT_GREYWATER_FRACTION,
    DEFAULT_GRAYWATER_PROPAGATION_FACTOR,
    SimulationState,
    ObservationEngine,
    ProtocolContext,
)

# All confined IDs (quarantined + isolated) helper
def _all_confined(state: SimulationState) -> set[int]:
    return state.isolated_ids | state.quarantined_ids


def build_wastewater_pathogen_mass(
    zone_names: list[str],
    zone_surface: dict[str, float],
    greywater_frac: float,
    graywater_zones: list[str],
) -> dict[str, float]:
    """Pool greywater pathogen mass from all zones into collection points."""
    per_zone = {
        zname: zone_surface.get(zname, 0.0) * greywater_frac
        for zname in zone_names
    }
    if not graywater_zones:
        return per_zone

    pooled = sum(per_zone.values())
    return dict.fromkeys(graywater_zones, pooled)


def build_wastewater_pathogen_mass_by_id(
    zone_names: list[str],
    pathogen_mass_by_id: dict[str, dict[str, float]] | None,
    greywater_frac: float,
    graywater_zones: list[str],
) -> dict[str, dict[str, float]] | None:
    """Pool per-pathogen greywater mass from all zones into collection points."""
    if not pathogen_mass_by_id:
        return None
    if not graywater_zones:
        return pathogen_mass_by_id

    pooled_by_id: dict[str, dict[str, float]] = {}
    for pid, masses in pathogen_mass_by_id.items():
        pooled = sum(masses.get(zname, 0.0) * greywater_frac for zname in zone_names)
        pooled_by_id[pid] = dict.fromkeys(graywater_zones, pooled)
    return pooled_by_id


# ── VSP state synchronization ────────────────────────────────────────────

def sync_vsp_isolation(
    epoch: int,
    engine: KorkinShipEngine,
    state: SimulationState,
) -> None:
    """Sync VSP-triggered quarantine from the engine back to SimulationState.

    The Korkin engine's ``step()`` may independently quarantine agents via the
    VSP 3% threshold.  Those IDs must be merged into SimulationState so that
    downstream functions (telemetry, confinement, recording) see a consistent
    set.  VSP confinement is quarantine (confined to quarters, still
    HVAC-connected), not true isolation.
    """
    vsp_new = engine.quarantined_ids - _all_confined(state)
    if vsp_new:
        state.quarantined_ids.update(vsp_new)
        for aid in sorted(vsp_new):
            state.compliance_log.append({
                "epoch": epoch,
                "agent_id": aid,
                "action": "vsp_quarantine",
            })


# ── FRED compliance ──────────────────────────────────────────────────────

def step_fred_compliance(
    epoch: int,
    state: SimulationState,
    syndromic: Any,
) -> None:
    """FRED compliance check for pending quarantine orders."""
    for aid in tuple(state.quarantine_refusers):
        epochs_since = epoch - state.quarantine_order_epoch.get(aid, epoch)
        chronic_boost = state.chronic_behavioral_mods.get(
            aid, {},
        ).get("quarantine_compliance_boost", 0.0)
        if syndromic.check_quarantine_compliance(
            aid, epochs_since, chronic_compliance_boost=chronic_boost,
        ):
            state.quarantine_refusers.discard(aid)
            state.quarantined_ids.add(aid)
            state.compliance_log.append({
                "epoch": epoch, "agent_id": aid,
                "action": "delayed_compliance",
                "delay": epochs_since,
            })


# ── Mid-cruise pathogen introductions ────────────────────────────────────

def step_mid_cruise_introductions(
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
                and a.current_location != LOCATION_ISOLATED
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
                        pid, 1e4, epoch, time_infected=dpi, rng=rng, profile=prof,
                    )


# ── Infection progression ────────────────────────────────────────────────

def _advance_agent_pathogen_infections(
    agent: Any,
    pathogen_profiles: dict[str, dict[str, Any]],
    rng: np.random.Generator,
) -> None:
    for pid, inf in tuple(agent.infections.items()):
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
            ill_prob = min(1.0, ill_prob + agent.get_chronic_illness_boost(pid))
            if rng.random() < ill_prob:
                inf["illness"] = IllnessStatus.SYMPTOMATIC
                if agent.illness_status == IllnessStatus.NOT_ILL:
                    agent.illness_status = IllnessStatus.SYMPTOMATIC

        recovery_day = agent.get_chronic_recovery_day(
            pid, prof.get("recovery_day", 3),
        )
        if dpi >= recovery_day:
            inf["status"] = InfectionStatus.RECOVERED
            inf["illness"] = IllnessStatus.RECOVERED


def step_infection_progression(
    engine: KorkinShipEngine,
    pathogen_profiles: dict[str, dict[str, Any]],
) -> None:
    """Advance multi-pathogen infection, illness, recovery, and mass accumulation."""
    if not pathogen_profiles:
        return

    for agent in engine.agents:
        _advance_agent_pathogen_infections(agent, pathogen_profiles, engine.rng)

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


# ── Chronic disease severity escalation ──────────────────────────────────

def apply_chronic_severity_escalation(
    agents: list[dict[str, Any]],
    engine: KorkinShipEngine,
    rng: np.random.Generator,
) -> None:
    """Escalate symptomatic chronic-disease agents to SEVERE presentation.

    For each symptomatic agent with chronic diseases, the severity
    multiplier determines the probability of escalation:
    ``P(severe) = clamp(severity_mult - 1.0, 0, 1)``.
    """
    from telemetry_buffer.agent_axes import (
        PRESENTATION_SYMPTOMATIC,
        PRESENTATION_SEVERE,
    )
    for agent_dict in agents:
        pres = agent_dict.get("symptom_presentation", "")
        if pres != PRESENTATION_SYMPTOMATIC:
            continue
        aid = agent_dict["agent_id"]
        korkin_agent = None
        if aid < len(engine.agents):
            korkin_agent = engine.agents[aid]
        if korkin_agent is None or not korkin_agent.has_chronic_disease:
            continue
        max_sev = 1.0
        for pid in korkin_agent.active_pathogen_ids:
            sev = korkin_agent.get_chronic_severity_multiplier(pid)
            max_sev = max(max_sev, sev)
        escalation_prob = min(1.0, max(0.0, max_sev - 1.0))
        if escalation_prob > 0 and rng.random() < escalation_prob:
            agent_dict["symptom_presentation"] = PRESENTATION_SEVERE


# ── Observation sampling ─────────────────────────────────────────────────

def _run_clinical_panel(
    obs: ObservationEngine,
    sick_call_agents: list[dict[str, Any]],
) -> tuple[
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
]:
    if not sick_call_agents:
        return {}, {}, {}
    from crusher_labs.clinical_correlation import run_correlated_clinical_panel

    return run_correlated_clinical_panel(
        obs, sick_call_agents, obs.clinical_correlation,
    )


def _submit_observation_queue(
    queue: Any,
    epoch: int,
    air_results: dict[str, dict[str, Any]],
    swab_results: dict[str, dict[str, Any]],
    ww_results: dict[str, dict[str, Any]],
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
    clin_microbio_results: dict[int, dict[str, Any]],
) -> None:
    from crusher_labs.instrument_turnaround import (
        INSTRUMENT_AIR,
        INSTRUMENT_MICROBIO,
        INSTRUMENT_QPCR,
        INSTRUMENT_RDT,
        INSTRUMENT_SWAB,
        INSTRUMENT_WW,
    )

    queue.submit_dict(INSTRUMENT_AIR, air_results, epoch)
    queue.submit_dict(INSTRUMENT_SWAB, swab_results, epoch)
    queue.submit_dict(INSTRUMENT_WW, ww_results, epoch)
    queue.submit_dict(INSTRUMENT_RDT, clin_rdt_results, epoch)
    queue.submit_dict(INSTRUMENT_QPCR, clin_qpcr_results, epoch)
    queue.submit_dict(INSTRUMENT_MICROBIO, clin_microbio_results, epoch)


def _run_long_read_escalation(
    obs: ObservationEngine,
    queue: Any,
    cfg: dict[str, Any],
    epoch: int,
    spaces: dict[str, dict[str, Any]],
    agents: list[dict[str, Any]],
    pathogen_profiles: dict[str, dict[str, Any]],
    ww_results: dict[str, dict[str, Any]],
    swab_results: dict[str, dict[str, Any]],
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
    clin_microbio_results: dict[int, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    from crusher_labs.instrument_turnaround import INSTRUMENT_LONG_READ
    from crusher_labs.long_read_escalation import collect_long_read_escalation_requests

    long_read_results: dict[str, dict[str, Any]] = {}
    long_read_ordered_count = 0
    if obs.long_read is None:
        return long_read_results, long_read_ordered_count

    requests = collect_long_read_escalation_requests(
        cfg,
        ww_results=ww_results,
        swab_results=swab_results,
        clin_rdt_results=clin_rdt_results,
        clin_qpcr_results=clin_qpcr_results,
        clin_microbio_results=clin_microbio_results,
    )
    if not requests:
        return long_read_results, long_read_ordered_count

    raw_lr = obs.long_read.run_requests(
        requests,
        epoch=epoch,
        spaces=spaces,
        agents=agents,
        pathogen_profiles=pathogen_profiles,
    )
    for req_id, payload in raw_lr.items():
        queue.submit(INSTRUMENT_LONG_READ, req_id, payload, epoch)
        long_read_ordered_count += 1
    released = queue.release(epoch)
    long_read_results = released.get(INSTRUMENT_LONG_READ, {})
    return long_read_results, long_read_ordered_count


def run_observation_sampling(
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
    dict[str, dict[str, Any]],
    int,
]:
    """Run all six observation instruments for a single epoch.

    Returns (air_results, swab_results, ww_results,
             clin_rdt_results, clin_qpcr_results, clin_microbio_results,
             long_read_results, long_read_ordered_count).
    Delivered results respect instrument turnaround; stoplights use delivered only.
    """
    from crusher_labs.instrument_turnaround import (
        merge_released_into_observation,
    )

    queue = obs.turnaround
    if queue is None:
        from crusher_labs.instrument_turnaround import (
            InstrumentTurnaroundQueue,
            InstrumentTurnaroundRegistry,
        )

        queue = InstrumentTurnaroundQueue(InstrumentTurnaroundRegistry({"instruments": {}}))

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

    ww_microflora: dict[str, dict[str, float]] = {}
    for zname, mf_data in zone_microflora_shifts.items():
        ww_microflora[zname] = mf_data
    ww_per_pathogen = (
        {pid: engine.get_pathogen_zone_mass(pid) for pid in pathogen_profiles}
        if pathogen_profiles else None
    )
    from orchestrator_init import resolve_graywater_zones

    ww_target_zones = resolve_graywater_zones(cfg, zone_names)
    ww_pathogen_mass = build_wastewater_pathogen_mass(
        zone_names, zone_surface, greywater_frac, ww_target_zones,
    )
    ww_per_pathogen = build_wastewater_pathogen_mass_by_id(
        zone_names, ww_per_pathogen, greywater_frac, ww_target_zones,
    )
    ww_results = obs.wastewater_seq.sample_all_zones(
        ww_pathogen_mass, ww_microflora,
        pathogen_mass_by_id=ww_per_pathogen,
        wastewater_zones=ww_target_zones,
    )

    sick_call_agents = [
        a for a in agents
        if a["agent_id"] in syn_result.get("sick_call_agents", [])
    ]
    clin_rdt_results, clin_qpcr_results, clin_microbio_results = (
        _run_clinical_panel(obs, sick_call_agents)
    )

    if queue is not None:
        _submit_observation_queue(
            queue, epoch, air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )

    released = queue.release(epoch) if queue is not None else {}
    (
        air_results,
        swab_results,
        ww_results,
        clin_rdt_results,
        clin_qpcr_results,
        clin_microbio_results,
        long_read_results,
    ) = merge_released_into_observation(released)

    long_read_ordered_count = 0
    if queue is not None:
        long_read_results, long_read_ordered_count = _run_long_read_escalation(
            obs, queue, cfg, epoch, spaces, agents, pathogen_profiles,
            ww_results, swab_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )

    if obs.lab_notebook_enabled:
        obs.notebook.log_air_sniffer(epoch, air_results)
        obs.notebook.log_surface_swab(epoch, swab_results)
        obs.notebook.log_wastewater_seq(epoch, ww_results)
        obs.notebook.log_clinical_rdt(epoch, clin_rdt_results)
        obs.notebook.log_clinical_qpcr(epoch, clin_qpcr_results)
        obs.notebook.log_clinical_microbiology(epoch, clin_microbio_results)
        obs.notebook.log_agent_summary(epoch, agents)
        if long_read_results:
            obs.notebook.log_long_read_verification(epoch, long_read_results)

    return (
        air_results, swab_results, ww_results,
        clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        long_read_results,
        long_read_ordered_count,
    )


# ── Quarantine confinement ───────────────────────────────────────────────

def step_quarantine_confinement(
    epoch: int,
    agents: list[dict[str, Any]],
    merged_mods: dict[str, Any],
    trigger_status: str,
    state: SimulationState,
    syndromic: Any,
) -> None:
    """Apply quarantine confinement from protocol modifiers or legacy CONFIRMED fallback.

    Handles three confinement modes:
    - SOP-009 ``confine_all_to_quarters``: full-ship lockdown of ALL agents
    - SOP-008/010 ``confine_symptomatic_to_quarters``: symptomatic only
    - Legacy fallback: confine symptomatic + shedding when CONFIRMED
    """
    exempt_classes: set[str] = set(merged_mods.get("exempt_classes", []))

    # SOP-009: full-ship lockdown — confine every agent
    if merged_mods.get("confine_all_to_quarters", False):
        confine_all_agents(epoch, agents, state, syndromic, exempt_classes)
        return

    # SOP-008/010: symptomatic-only confinement
    if merged_mods.get("confine_symptomatic_to_quarters", False):
        confine_agents(
            epoch, agents, state, syndromic,
            include_shedding=False, exempt_classes=exempt_classes,
        )
        return

    # Legacy fallback when CONFIRMED but no protocol modifier active
    if trigger_status == STATUS_CONFIRMED:
        confine_agents(epoch, agents, state, syndromic, include_shedding=True)


def confine_agents(
    epoch: int,
    agents: list[dict[str, Any]],
    state: SimulationState,
    syndromic: Any,
    include_shedding: bool,
    exempt_classes: set[str] | None = None,
) -> None:
    """Confine symptomatic (and optionally shedding) agents to quarters (quarantine).

    Agents whose ``agent_class`` is in *exempt_classes* are skipped.
    """
    confined = _all_confined(state)
    _exempt = exempt_classes or set()
    for agent in agents:
        aid = agent["agent_id"]
        if aid in confined or aid in state.quarantine_refusers:
            continue
        if agent.get("agent_class", "") in _exempt:
            continue
        is_symptomatic = agent_requires_confinement(agent)
        is_shedding = include_shedding and agent.get("shedding_rate", 0.0) > 0.0
        if not (is_symptomatic or is_shedding):
            continue
        override = state.agent_behavioral_overrides.get(aid)
        chronic_boost = state.chronic_behavioral_mods.get(
            aid, {},
        ).get("quarantine_compliance_boost", 0.0)
        if syndromic.check_quarantine_compliance(
            aid, 0, behavioral_override=override,
            chronic_compliance_boost=chronic_boost,
        ):
            state.quarantined_ids.add(aid)
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


def confine_all_agents(
    epoch: int,
    agents: list[dict[str, Any]],
    state: SimulationState,
    syndromic: Any,
    exempt_classes: set[str] | None = None,
) -> None:
    """SOP-009: confine ALL agents to quarters (quarantine lockdown).

    Agents whose ``agent_class`` is in *exempt_classes* are skipped.
    """
    confined = _all_confined(state)
    _exempt = exempt_classes or set()
    for agent in agents:
        aid = agent["agent_id"]
        if aid in confined or aid in state.quarantine_refusers:
            continue
        if agent.get("agent_class", "") in _exempt:
            continue
        override = state.agent_behavioral_overrides.get(aid)
        chronic_boost = state.chronic_behavioral_mods.get(
            aid, {},
        ).get("quarantine_compliance_boost", 0.0)
        if syndromic.check_quarantine_compliance(
            aid, 0, behavioral_override=override,
            chronic_compliance_boost=chronic_boost,
        ):
            state.quarantined_ids.add(aid)
            state.compliance_log.append({
                "epoch": epoch, "agent_id": aid,
                "action": "general_confinement",
            })
        else:
            state.quarantine_refusers.add(aid)
            state.quarantine_order_epoch[aid] = epoch
            state.compliance_log.append({
                "epoch": epoch, "agent_id": aid,
                "action": "refused_general_confinement",
            })


def apply_surface_decontamination(
    engine: KorkinShipEngine,
    factor: float,
) -> None:
    """SOP-010: reduce surface pathogen mass by a decontamination factor.

    ``factor`` is the *reduction* fraction (e.g. 0.60 means remove 60% of
    surface mass, retaining 40%).
    """
    retention = 1.0 - max(0.0, min(1.0, factor))
    for zname in engine.zone_pathogen_mass:
        engine.zone_pathogen_mass[zname] *= retention


def apply_zone_closures(
    engine: KorkinShipEngine,
    closed_zones: list[str],
) -> None:
    """SOP-009: relocate agents from closed zones to their home zones."""
    closed_set = set(closed_zones)
    for agent in engine.agents:
        if agent.current_location in closed_set:
            agent.current_location = agent.home_zone


# ── Cost accounting ──────────────────────────────────────────────────────

def step_cost_accounting(
    epoch: int,
    proto_ctx: ProtocolContext,
    air_results: dict,
    swab_results: dict,
    ww_results: dict,
    clin_rdt_results: dict,
    _clin_qpcr_results: dict,
    _clin_microbio_results: dict,
) -> None:
    """Debit baseline surveillance and per-test costs for one epoch."""
    ledger = proto_ctx.cost_ledger
    resource_costs_cfg = proto_ctx.resource_costs_cfg

    baseline_costs = resource_costs_cfg.get("baseline_surveillance_costs_per_epoch", {})
    ledger.debit_baseline_surveillance(epoch, baseline_costs)

    per_test = resource_costs_cfg.get("per_test_costs", {})
    ledger.debit_per_test(epoch, "air_sniffer_sample", len(air_results), per_test)
    # Observation engine surface swabs are PCR-style (Ct/LOD), not culture.
    ledger.debit_per_test(epoch, "surface_swab_pcr", len(swab_results), per_test)
    # Wastewater instrument is a sequencing grid.
    ledger.debit_per_test(epoch, "wastewater_sequencing_panel", len(ww_results), per_test)
    n_sick = len(clin_rdt_results)
    ledger.debit_per_test(epoch, "clinical_rdt", n_sick, per_test)
    ledger.debit_per_test(epoch, "clinical_qpcr", n_sick, per_test)
    ledger.debit_per_test(epoch, "clinical_microbiology", n_sick, per_test)


def step_operational_impact_accounting(
    epoch: int,
    state: SimulationState,
    agents: list[dict[str, Any]],
    merged_modifiers: dict[str, Any],
    proto_ctx: Any,
    zone_type_by_id: dict[str, str] | None = None,
) -> None:
    """Accumulate operational impact score from confinement and active modifiers."""
    from crusher_labs.cost_ledger import compute_operational_impact

    ledger = proto_ctx.cost_ledger
    active_ids = proto_ctx.protocol_engine.get_active_protocols()
    ois_delta, breakdown = compute_operational_impact(
        agents=agents,
        quarantined_ids=state.quarantined_ids,
        isolated_ids=state.isolated_ids,
        merged_modifiers=merged_modifiers,
        active_protocol_ids=active_ids,
        ois_weights=ledger.ois_weights,
        zone_type_by_id=zone_type_by_id,
    )
    if ois_delta > 0:
        ledger.accumulate_operational_impact(
            epoch,
            ois_delta,
            breakdown=breakdown,
        )


def step_long_read_cost_accounting(
    epoch: int,
    proto_ctx: ProtocolContext,
    long_read_ordered_count: int,
) -> None:
    """Debit long-read verification runs when escalation orders a run (submit epoch)."""
    if long_read_ordered_count <= 0:
        return
    per_test = proto_ctx.resource_costs_cfg.get("per_test_costs", {})
    proto_ctx.cost_ledger.debit_per_test(
        epoch, "long_read_verification", long_read_ordered_count, per_test,
    )


def step_cascade_cost_accounting(
    epoch: int,
    proto_ctx: ProtocolContext,
    cascade_result: dict[str, Any] | None,
) -> None:
    """Debit cascade-ordered diagnostic tests via per_test_costs ledger entries."""
    if not cascade_result:
        return
    per_test = proto_ctx.resource_costs_cfg.get("per_test_costs", {})
    tests_ordered = cascade_result.get("tests_ordered", {})
    if not isinstance(tests_ordered, dict):
        return
    test_counts: dict[str, int] = {}
    for test_keys in tests_ordered.values():
        if not isinstance(test_keys, list):
            continue
        for test_key in test_keys:
            test_counts[test_key] = test_counts.get(str(test_key), 0) + 1
    for test_key, count in test_counts.items():
        if count > 0 and test_key in per_test:
            proto_ctx.cost_ledger.debit_per_test(
                epoch, test_key, count, per_test,
            )


# ── Microflora disruption ───────────────────────────────────────────────

def compute_zone_microflora_shifts(
    agents: list,
    pathogen_profiles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, dict[str, float]]:
    """Compute per-zone microflora disruption shift magnitudes.

    For each zone, aggregate the microflora disruption from all agents
    with active disruption status, producing a dict of
    {zone: {disruption_type: magnitude}}.
    """
    mf_cfg = cfg.get("microflora", {})
    shed_mass = mf_cfg.get("disrupted_shed_mass", 50.0)
    from orchestrator_init import resolve_graywater_zones

    graywater_zones = resolve_graywater_zones(cfg)
    gw_factor = mf_cfg.get(
        "graywater_propagation_factor", DEFAULT_GRAYWATER_PROPAGATION_FACTOR,
    )

    zone_shifts: dict[str, dict[str, float]] = {}

    for agent in agents:
        if agent.microflora_disruption_status <= 0:
            continue
        loc = agent.current_location
        if loc == LOCATION_ISOLATED:
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


# ── Wearable monitoring ──────────────────────────────────────────────────

def step_wearable_monitoring(
    _epoch: int,
    engine: KorkinShipEngine,
    monitor: WearableMonitor | None,
    modality: WearableDataStream | None,
    truth: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Generate wearable data and run through the observation modality.

    Returns the modality result dict, or None if wearable monitoring
    is disabled.
    """
    if monitor is None or modality is None:
        return None

    raw_data = monitor.generate_epoch_data(engine.agents, pathogen_profiles)
    result = modality.query_ground_truth(truth, raw_data)
    fleet_cfg = monitor.get_fleet_summary()
    result.setdefault("fleet_summary", {}).update({
        "visibility_breakdown": fleet_cfg.get("visibility_breakdown", {}),
        "device_deployment_counts": fleet_cfg.get("device_deployment_counts", {}),
    })
    return result


# ── Diagnostic cascade ───────────────────────────────────────────────────

def _collect_wearable_red_ids(
    wearable_result: dict[str, Any],
    entry_cfg: Any,
) -> list[int]:
    from crusher_labs.cascade_entry import evaluate_wearable_alert

    wearable_red_ids: list[int] = []
    alert_fusion = entry_cfg.wearable_alert_fusion
    for aid_str, data in wearable_result.get("agent_results", {}).items():
        if evaluate_wearable_alert(data, alert_fusion):
            try:
                wearable_red_ids.append(int(aid_str))
            except (ValueError, TypeError):
                pass
    return wearable_red_ids


def step_diagnostic_cascade(
    epoch: int,
    state: SimulationState,
    agents: list[dict[str, Any]],
    syn_result: dict[str, Any],
    wearable_result: dict[str, Any] | None,
    obs: ObservationEngine,
    wearable_monitor: Any | None = None,
    cascade_entry_config: Any | None = None,
) -> dict[str, Any] | None:
    """Run one epoch of the diagnostic cascade engine.

    Feeds sick-call and wearable RED alerts into the cascade, which
    manages per-agent tier progression and sequential test ordering.
    Agents whose cascade reaches confinement tiers are added to the
    quarantine set.  Returns the cascade epoch result dict, or None
    if the cascade is disabled.
    """
    cascade = state.cascade_engine
    if cascade is None:
        return None

    from crusher_labs.cascade_entry import (
        CascadeEntryConfig,
    )
    from crusher_labs.diagnostic_cascade import build_test_runner

    sick_call_ids = list(syn_result.get("sick_call_agents", []))

    entry_cfg = cascade_entry_config
    if entry_cfg is None and cascade is not None:
        entry_cfg = cascade.entry_config
    if entry_cfg is None:
        entry_cfg = CascadeEntryConfig()

    wearable_red_ids: list[int] = []
    if wearable_result:
        wearable_red_ids = _collect_wearable_red_ids(wearable_result, entry_cfg)

    monitored_ids: set[int] = set()
    if wearable_monitor is not None and hasattr(wearable_monitor, "monitored_agents"):
        monitored_ids = set(wearable_monitor.monitored_agents)
    elif wearable_monitor is not None:
        monitored_ids = set()

    test_runner = build_test_runner(obs)

    result = cascade.evaluate_epoch(
        epoch=epoch,
        sick_call_ids=sick_call_ids,
        wearable_red_ids=wearable_red_ids,
        agents=agents,
        test_runner=test_runner,
        monitored_agent_ids=monitored_ids,
    )

    for aid in result.confinements_ordered:
        if aid not in state.quarantined_ids and aid not in state.isolated_ids:
            state.quarantined_ids.add(aid)
            state.compliance_log.append({
                "epoch": epoch,
                "agent_id": aid,
                "action": "cascade_confinement",
            })

    return result.to_dict()


def build_cascade_context(
    state: SimulationState,
    cascade_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build cascade context dict for protocol engine gating."""
    cascade = state.cascade_engine
    if cascade is None:
        return None

    unlocked = cascade.get_all_unlocked_sops()
    fleet_sops = cascade_result.get("fleet_sops_unlocked", []) if cascade_result else []

    return {
        "unlocked_sops": unlocked,
        "fleet_sops_unlocked": fleet_sops,
        "tier_distribution": cascade.tier_distribution(),
    }


# ── Infection counters ───────────────────────────────────────────────────

VALID_COUNTER_METRICS = {
    "attack_rate",
    "infected_count",
    "symptomatic_count",
    "recovered_count",
    "susceptible_count",
}


def _agent_matches_filter(
    agent: dict[str, Any],
    counter_filter: dict[str, Any],
) -> bool:
    """Check whether an agent matches a counter's filter criteria."""
    if not counter_filter:
        return True
    role_group = counter_filter.get("role_group")
    classes = counter_filter.get("classes")

    agent_class = agent.get("agent_class", "")
    if role_group and not agent_class.startswith(role_group):
        return False
    if classes and agent_class not in classes:
        return False
    return True


def _counter_metric_value(
    metric: str,
    group: list[dict[str, Any]],
    pop: int,
) -> float:
    if metric == "attack_rate":
        n_symptomatic = sum(
            1 for a in group
            if agent_has_symptomatic_presentation(a)
        )
        return (n_symptomatic / pop) if pop > 0 else 0.0
    if metric == "infected_count":
        return float(sum(1 for a in group if agent_is_infected(a)))
    if metric == "symptomatic_count":
        return float(sum(
            1 for a in group
            if agent_has_symptomatic_presentation(a)
        ))
    if metric == "recovered_count":
        return float(sum(
            1 for a in group
            if a.get("infection_state") == INFECTION_RECOVERED
            or a.get("symptom_status") == "recovered"
        ))
    if metric == "susceptible_count":
        return float(sum(
            1 for a in group
            if a.get("infection_state") == INFECTION_SUSCEPTIBLE
            or (
                "infection_state" not in a
                and a.get("symptom_status") == "asymptomatic"
            )
        ))
    return 0.0


def compute_infection_counters(
    agents: list[dict[str, Any]],
    counter_defs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Evaluate all configured infection counters for the current epoch.

    Returns ``{counter_id: {"value": float, "label": str, "exceeded": bool}}``
    where *exceeded* is ``True`` when the value meets or exceeds the
    counter's optional ``threshold``.
    """
    results: dict[str, dict[str, Any]] = {}
    for cdef in counter_defs:
        cid = cdef.get("counter_id", "")
        metric = cdef.get("metric", "infected_count")
        cfilter = cdef.get("filter", {})
        threshold = cdef.get("threshold")
        label = cdef.get("label", cid)

        group = [a for a in agents if _agent_matches_filter(a, cfilter)]
        pop = len(group)
        value = _counter_metric_value(metric, group, pop)

        exceeded = threshold is not None and value >= threshold
        entry: dict[str, Any] = {
            "value": round(value, 6),
            "label": label,
            "population": pop,
        }
        if threshold is not None:
            entry["threshold"] = threshold
            entry["exceeded"] = exceeded
        results[cid] = entry

    return results


def step_counter_thresholds(
    epoch: int,
    agents: list[dict[str, Any]],
    counter_results: dict[str, dict[str, Any]],
    counter_defs: list[dict[str, Any]],
    state: SimulationState,
    syndromic: Any,
) -> None:
    """Apply confinement actions for counters that exceed their thresholds.

    Replaces the legacy engine-internal VSP whole-population check with
    configurable, per-group counter thresholds.
    """
    for cdef in counter_defs:
        cid = cdef.get("counter_id", "")
        on_exceed = cdef.get("on_exceed", "log_only")
        result = counter_results.get(cid, {})
        if not result.get("exceeded", False):
            continue
        if on_exceed == "confine_symptomatic":
            exempt = set(cdef.get("exempt_classes", []))
            confine_agents(
                epoch, agents, state, syndromic,
                include_shedding=False, exempt_classes=exempt,
            )
