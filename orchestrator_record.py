"""
orchestrator_record.py – Epoch recording and simulation finalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Builds per-epoch history records and handles end-of-simulation
output serialization (simulation history JSON, lab notebook,
executive summary).
"""

from __future__ import annotations

import json
import os
from typing import Any

from crusher_labs.lab_notebook import load_logging_profile
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinShipEngine,
)
from engines.py_contam_bridge import ContamTransportEngine
from orchestrator_display import print_executive_summary
from orchestrator_init import role_group_for_agent
from orchestrator_types import (
    REPO_ROOT,
    ObservationEngine,
    ProtocolContext,
    SimulationState,
)
from simulation_utils.paths import prepare_output_directory, resolve_repo_path, validated_open
from telemetry_buffer.agent_axes import (
    INFECTION_IMMUNE,
    INFECTION_RECOVERED,
    agent_has_symptomatic_presentation,
    agent_is_infected,
    agent_is_isolated,
    resolve_agent_axes,
)


def _multi_pathogen_summary(
    engine: KorkinShipEngine,
    pathogen_profiles: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    if not pathogen_profiles:
        return summary
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
        summary[pid] = mp_s
    return summary


def _update_summary_from_agent(summary: dict[str, Any], agent: dict[str, Any]) -> None:
    infection_state, _, _ = resolve_agent_axes(agent)
    if agent_is_infected(agent):
        summary["infected"] += 1
    elif infection_state == INFECTION_RECOVERED:
        summary["recovered"] += 1
    elif infection_state == INFECTION_IMMUNE:
        summary["immune"] += 1
    else:
        summary["susceptible"] += 1
    if agent_has_symptomatic_presentation(agent) and not agent_is_isolated(agent):
        summary["symptomatic"] += 1


def _space_entries(
    spaces: dict[str, dict[str, Any]],
    contam_engine: ContamTransportEngine | None,
    pathogen_profiles: dict[str, dict[str, Any]],
    *,
    compact: bool,
) -> dict[str, dict[str, Any]]:
    """Per-zone mass / concentration for history (compact omits by-id maps)."""
    out: dict[str, dict[str, Any]] = {}
    for zname, zdata in spaces.items():
        zone_entry: dict[str, Any] = {
            "pathogen_mass": zdata.get("pathogen_mass", 0.0),
        }
        if pathogen_profiles and not compact:
            zone_entry["pathogen_mass_by_id"] = zdata.get("pathogen_mass_by_id", {})
        if contam_engine is not None:
            node = contam_engine.zone_nodes.get(zname)
            if node is not None:
                zone_entry["concentration_per_m3"] = round(
                    node.concentration(zdata.get("pathogen_mass", 0.0)), 3,
                )
                if not compact:
                    zone_entry["volume_m3"] = node.volume_m3
        out[zname] = zone_entry
    return out


def _summary_counts(
    agents: list[dict[str, Any]],
    engine: KorkinShipEngine,
    state: SimulationState,
    syn_result: dict[str, Any],
) -> dict[str, Any]:
    reported_counts = {"passenger": 0, "crew": 0}
    ill_counts = {"passenger": 0, "crew": 0}
    population_counts = {"passenger": 0, "crew": 0}
    for agent in agents:
        aid = int(agent["agent_id"])
        group = role_group_for_agent(agent)
        population_counts[group] += 1
        if aid in state.ever_reported_ids:
            reported_counts[group] += 1
        if aid in state.ever_ill_ids:
            ill_counts[group] += 1
    reported_rates = {
        group: reported_counts[group] / population_counts[group]
        if population_counts[group] else 0.0
        for group in ("passenger", "crew")
    }
    ever_ill_rates = {
        group: ill_counts[group] / population_counts[group]
        if population_counts[group] else 0.0
        for group in ("passenger", "crew")
    }
    disrupted_count = sum(
        1 for a in engine.agents if a.microflora_disruption_status > 0
    )
    summary: dict[str, Any] = {
        "susceptible": 0,
        "infected": 0,
        "symptomatic": 0,
        "recovered": 0,
        "immune": 0,
        "isolated": len(state.isolated_ids),
        "quarantined": len(state.quarantined_ids),
        "quarantine_refusers": len(state.quarantine_refusers),
        "sick_call_count": syn_result["sick_call_count"],
        "disrupted_microflora_count": disrupted_count,
        "cumulative_reported_cases": len(state.ever_reported_ids),
        "cumulative_reported_cases_passenger": reported_counts["passenger"],
        "cumulative_reported_cases_crew": reported_counts["crew"],
        "cumulative_reported_noise_cases": len(state.ever_reported_noise_ids),
        "cumulative_ever_ill": len(state.ever_ill_ids),
        "cumulative_ever_ill_passenger": ill_counts["passenger"],
        "cumulative_ever_ill_crew": ill_counts["crew"],
        "reported_case_rate_passenger": round(reported_rates["passenger"], 6),
        "ever_ill_rate_passenger": round(ever_ill_rates["passenger"], 6),
    }
    for a in agents:
        _update_summary_from_agent(summary, a)
    return summary


def record_epoch(  # NOSONAR
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
    wearable_result: dict[str, Any] | None = None,
    infection_counters: dict[str, dict[str, Any]] | None = None,
    long_read_results: dict[str, dict[str, Any]] | None = None,
    cascade_result: dict[str, Any] | None = None,
    history_retention: str = "full",
    final_epoch: bool = False,
) -> dict[str, Any]:
    """Build an epoch record for simulation_history.

    ``history_retention="compact"`` keeps only scalars needed for campaign
    timeseries / summary (no per-agent, contact-tracing, or raw assay blobs).
    """
    if not isinstance(agents, list):
        raise TypeError(f"record_epoch: agents must be list, got {type(agents).__name__}")
    if not isinstance(spaces, dict):
        raise TypeError(f"record_epoch: spaces must be dict, got {type(spaces).__name__}")
    if not isinstance(stoplights, dict):
        raise TypeError(f"record_epoch: stoplights must be dict, got {type(stoplights).__name__}")

    compact = str(history_retention).strip().lower() == "compact"
    summary = _summary_counts(agents, engine, state, syn_result)
    space_map = _space_entries(
        spaces, contam_engine, pathogen_profiles, compact=compact,
    )

    if compact:
        return {
            "epoch": epoch,
            "trigger_status": trigger_status,
            "summary": summary,
            "spaces": space_map,
            "multi_pathogen": _multi_pathogen_summary(engine, pathogen_profiles),
            "infection_counters": infection_counters or {},
            "hvac": {
                "filter_type": cfg.get("hvac", {}).get("filter_type", "none"),
                "filter_efficiency": (
                    contam_engine.filter_efficiency if contam_engine else 0.0
                ),
                "transport_active": contam_engine is not None,
            },
            "reactive_protocols": {
                "active_protocols": [
                    {"protocol_id": m["protocol_id"], "name": m["name"],
                     "newly_activated": m["newly_activated"]}
                    for m in active_mods
                ],
                "stoplights": stoplights,
                "trigger_status": trigger_status,
            },
            "cost_accounting": epoch_cost,
        }

    multi_pathogen_summary = _multi_pathogen_summary(engine, pathogen_profiles)

    epoch_record: dict[str, Any] = {
        "epoch": epoch,
        "trigger_status": trigger_status,
        "agents": [],
        "spaces": space_map,
        "summary": summary,
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
        "infection_counters": infection_counters or {},
    }

    for a in agents:
        infection_state, symptom_presentation, compliance_status = resolve_agent_axes(a)

        agent_record: dict[str, Any] = {
            "agent_id": a["agent_id"],
            "infection_state": infection_state,
            "symptom_presentation": symptom_presentation,
            "compliance_status": compliance_status,
            "shedding_rate": a.get("shedding_rate", 0.0),
            "location": a.get("location", "unknown"),
            "agent_class": a.get("agent_class", "unknown"),
            "gender": a.get("gender", "unknown"),
        }
        if pathogen_profiles:
            agent_record["pathogen_infections"] = a.get("pathogen_infections", {})
            agent_record["susceptibility_multiplier"] = a.get("susceptibility_multiplier", {})
            agent_record["microflora_disruption"] = a.get("microflora_disruption", 0.0)
        if "chronic_disease_ids" in a:
            agent_record["chronic_disease_ids"] = a["chronic_disease_ids"]
        epoch_record["agents"].append(agent_record)

    for zname in zone_names:
        mf_shift = zone_microflora_shifts.get(zname, {})
        if mf_shift:
            epoch_record["microflora_shifts"][zname] = {
                "disruption_types": list(mf_shift.keys()),
                "magnitudes": {k: round(v, 4) for k, v in mf_shift.items()},
                "total_magnitude": round(sum(mf_shift.values()), 4),
            }

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
    epoch_record["crusher_ops"]["quarantined_agents"] = sorted(state.quarantined_ids)

    epoch_record["observation_engine"] = {
        "syndromic": {
            "sick_call_agents": syn_result.get("sick_call_agents", []),
            "true_positive_ids": syn_result.get("true_positive_ids", []),
            "first_detection_events": syn_result.get(
                "first_detection_events", [],
            ),
        },
        "air_sniffer": air_results,
        "surface_swab": swab_results,
        "wastewater_sequencing": ww_results,
        "clinical_rdt": clin_rdt_results,
        "clinical_qpcr": clin_qpcr_results,
        "clinical_microbiology": clin_microbio_results,
        "long_read_verification": long_read_results or {},
        "logging_fidelity": obs.fidelity_name,
    }
    if final_epoch:
        epoch_record["observation_engine"]["syndromic"][
            "episode_detection_telemetry"
        ] = syn_result.get("episode_detection_telemetry", [])

    if wearable_result is not None:
        fleet = wearable_result.get("fleet_summary", {})
        epoch_record["wearable_monitoring"] = {
            "total_monitored": fleet.get("total_monitored", 0),
            "total_staff_visible": fleet.get("total_staff_visible", 0),
            "fever_count": fleet.get("fever_count", 0),
            "fever_rate": fleet.get("fever_rate", 0.0),
            "anomaly_count": fleet.get("anomaly_count", 0),
            "anomaly_rate": fleet.get("anomaly_rate", 0.0),
            "channel_anomaly_counts": fleet.get("channel_anomaly_counts", {}),
            "staff_visible_agents": wearable_result.get("staff_visible_agents", []),
            "wearer_only_agents": wearable_result.get("wearer_only_agents", []),
            "visibility_breakdown": fleet.get("visibility_breakdown", {}),
            "device_deployment_counts": fleet.get("device_deployment_counts", {}),
        }

    if cascade_result is not None:
        epoch_record["diagnostic_cascade"] = cascade_result

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

def finalize_simulation(
    state: SimulationState,
    engine: KorkinShipEngine,
    obs: ObservationEngine,
    proto_ctx: ProtocolContext,
    pathogen_profiles: dict[str, dict[str, Any]],
    zone_names: list[str],
    num_agents: int,
    num_epochs: int,
    *,
    history_path: str | None = None,
    lab_notebook_path: str | None = None,
    logging_profile_path: str | None = None,
    display: bool = True,
) -> None:
    """Save simulation history, lab notebook, and print executive summary."""
    if history_path is None:
        history_path = resolve_repo_path(
            REPO_ROOT, "telemetry_buffer/simulation_history.json",
        )
    else:
        history_path = resolve_repo_path(REPO_ROOT, history_path)
    prepare_output_directory(
        os.path.dirname(history_path),
        allowed_roots=(REPO_ROOT,),
    )
    with validated_open(history_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(state.simulation_history, fh, indent=2)
    print(f"\n  Simulation history saved to: {history_path}")

    logging_config_path = resolve_repo_path(
        REPO_ROOT,
        logging_profile_path or "data/config/logging_profile.json",
    )
    _, _, logging_config = load_logging_profile(logging_config_path)

    if obs.lab_notebook_enabled:
        obs.notebook.set_run_metadata(
            num_agents=num_agents,
            num_epochs=num_epochs,
            pathogens=list(pathogen_profiles.keys()) if pathogen_profiles else [],
            zones=zone_names,
            trigger_timeline=state.escalation_log,
        )
        if lab_notebook_path:
            nb_path = resolve_repo_path(REPO_ROOT, lab_notebook_path)
        else:
            nb_output = logging_config.get("lab_notebook", {}).get(
                "output_path", "telemetry_buffer/artificial_lab_notebook.json",
            )
            nb_path = resolve_repo_path(REPO_ROOT, nb_output)
        financial_audit = proto_ctx.cost_ledger.generate_financial_audit()
        protocol_summary = proto_ctx.protocol_engine.generate_protocol_summary()
        obs.notebook.serialize(
            nb_path,
            financial_audit=financial_audit,
            protocol_summary=protocol_summary,
        )
        print(f"  Lab notebook saved to: {nb_path} ({len(obs.notebook.records)} records)")

    final_summary = engine.get_summary()
    audit = proto_ctx.cost_ledger.generate_financial_audit()
    proto_summary = proto_ctx.protocol_engine.generate_protocol_summary()

    final_counters: dict[str, dict[str, Any]] = {}
    if state.simulation_history:
        final_counters = state.simulation_history[-1].get("infection_counters", {})

    if display:
        print_executive_summary(
            num_agents=num_agents,
            num_epochs=num_epochs,
            engine_summary=final_summary,
            audit=audit,
            proto_summary=proto_summary,
            escalation_log=state.escalation_log,
            compliance_log=state.compliance_log,
            trigger_status=state.trigger_status,
            isolated_count=len(state.isolated_ids),
            quarantined_count=len(state.quarantined_ids),
            refuser_count=len(state.quarantine_refusers),
            pathogen_profiles=pathogen_profiles,
            infection_counters=final_counters,
        )
