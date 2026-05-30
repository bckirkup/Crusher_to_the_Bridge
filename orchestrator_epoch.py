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
    for aid in list(state.quarantine_refusers):
        epochs_since = epoch - state.quarantine_order_epoch.get(aid, epoch)
        if syndromic.check_quarantine_compliance(aid, epochs_since):
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
                    agent.infect_with_pathogen(pid, 1e4, epoch, time_infected=dpi)


# ── Infection progression ────────────────────────────────────────────────

def step_infection_progression(
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
                if engine.rng.random() < ill_prob:
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


# ── Observation sampling ─────────────────────────────────────────────────

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

    obs.notebook.log_air_sniffer(epoch, air_results)
    obs.notebook.log_surface_swab(epoch, swab_results)
    obs.notebook.log_wastewater_seq(epoch, ww_results)
    obs.notebook.log_clinical_rdt(epoch, clin_rdt_results)
    obs.notebook.log_clinical_qpcr(epoch, clin_qpcr_results)
    obs.notebook.log_clinical_microbiology(epoch, clin_microbio_results)
    obs.notebook.log_agent_summary(epoch, agents)

    long_read_results: dict[str, dict[str, Any]] = {}
    if obs.long_read is not None:
        from crusher_labs.long_read_escalation import collect_long_read_escalation_requests

        requests = collect_long_read_escalation_requests(
            cfg,
            ww_results=ww_results,
            swab_results=swab_results,
            clin_rdt_results=clin_rdt_results,
            clin_qpcr_results=clin_qpcr_results,
            clin_microbio_results=clin_microbio_results,
        )
        if requests:
            long_read_results = obs.long_read.run_requests(requests)
            obs.notebook.log_long_read_verification(epoch, long_read_results)

    return (
        air_results, swab_results, ww_results,
        clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        long_read_results,
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
        if syndromic.check_quarantine_compliance(aid, 0):
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
        if syndromic.check_quarantine_compliance(aid, 0):
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
    for zname in list(engine.zone_pathogen_mass):
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
    # Observation engine surface swabs are PCR-style (Ct/LOD), not culture.
    ledger.debit_per_test(epoch, "surface_swab_pcr", len(swab_results), per_test)
    # Wastewater instrument is a sequencing grid.
    ledger.debit_per_test(epoch, "wastewater_sequencing_panel", len(ww_results), per_test)
    n_sick = len(clin_rdt_results)
    ledger.debit_per_test(epoch, "clinical_rdt", n_sick, per_test)
    ledger.debit_per_test(epoch, "clinical_qpcr", n_sick, per_test)
    ledger.debit_per_test(epoch, "clinical_microbiology", n_sick, per_test)


def step_long_read_cost_accounting(
    epoch: int,
    proto_ctx: ProtocolContext,
    long_read_results: dict[str, dict[str, Any]],
) -> None:
    """Debit long-read verification runs when escalation produced results."""
    if not long_read_results:
        return
    per_test = proto_ctx.resource_costs_cfg.get("per_test_costs", {})
    proto_ctx.cost_ledger.debit_per_test(
        epoch, "long_read_verification", len(long_read_results), per_test,
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
    graywater_zones = mf_cfg.get("graywater_zones", [])
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
    epoch: int,
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
    return result


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

        if metric == "attack_rate":
            n_symptomatic = sum(
                1 for a in group
                if agent_has_symptomatic_presentation(a)
            )
            value = (n_symptomatic / pop) if pop > 0 else 0.0
        elif metric == "infected_count":
            value = float(sum(1 for a in group if agent_is_infected(a)))
        elif metric == "symptomatic_count":
            value = float(sum(
                1 for a in group
                if agent_has_symptomatic_presentation(a)
            ))
        elif metric == "recovered_count":
            value = float(sum(
                1 for a in group
                if a.get("infection_state") == INFECTION_RECOVERED
                or a.get("symptom_status") == "recovered"
            ))
        elif metric == "susceptible_count":
            value = float(sum(
                1 for a in group
                if a.get("infection_state") == INFECTION_SUSCEPTIBLE
                or (
                    "infection_state" not in a
                    and a.get("symptom_status") == "asymptomatic"
                )
            ))
        else:
            value = 0.0

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
