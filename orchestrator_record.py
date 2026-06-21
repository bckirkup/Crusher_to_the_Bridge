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

from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    InfectionStatus,
    IllnessStatus,
)
from engines.py_contam_bridge import ContamTransportEngine
from crusher_labs.lab_notebook import load_logging_profile
from orchestrator_types import (
    REPO_ROOT,
    SimulationState,
    ObservationEngine,
    ProtocolContext,
)
from orchestrator_display import print_executive_summary
from telemetry_buffer.agent_axes import (
    agent_has_symptomatic_presentation,
    agent_is_infected,
    agent_is_isolated,
    INFECTION_RECOVERED,
    INFECTION_IMMUNE,
    resolve_agent_axes,
)


def record_epoch(
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
) -> dict[str, Any]:
    """Build a complete epoch record for simulation_history.

    Validates that key data structures have the expected shape before
    recording, to catch seam corruption between modules early.
    """
    if not isinstance(agents, list):
        raise TypeError(f"record_epoch: agents must be list, got {type(agents).__name__}")
    if not isinstance(spaces, dict):
        raise TypeError(f"record_epoch: spaces must be dict, got {type(spaces).__name__}")
    if not isinstance(stoplights, dict):
        raise TypeError(f"record_epoch: stoplights must be dict, got {type(stoplights).__name__}")

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
            "quarantined": len(state.quarantined_ids),
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
        "infection_counters": infection_counters or {},
    }

    for a in agents:
        infection_state, symptom_presentation, compliance_status = resolve_agent_axes(a)

        if agent_is_infected(a):
            epoch_record["summary"]["infected"] += 1
        elif infection_state == INFECTION_RECOVERED:
            epoch_record["summary"]["recovered"] += 1
        elif infection_state == INFECTION_IMMUNE:
            epoch_record["summary"]["immune"] += 1
        else:
            epoch_record["summary"]["susceptible"] += 1

        if agent_has_symptomatic_presentation(a) and not agent_is_isolated(a):
            epoch_record["summary"]["symptomatic"] += 1

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
        "air_sniffer": air_results,
        "surface_swab": swab_results,
        "wastewater_sequencing": ww_results,
        "clinical_rdt": clin_rdt_results,
        "clinical_qpcr": clin_qpcr_results,
        "clinical_microbiology": clin_microbio_results,
        "long_read_verification": long_read_results or {},
        "logging_fidelity": obs.fidelity_name,
    }

    if wearable_result is not None:
        fleet = wearable_result.get("fleet_summary", {})
        epoch_record["wearable_monitoring"] = {
            "total_monitored": fleet.get("total_monitored", 0),
            "fever_count": fleet.get("fever_count", 0),
            "fever_rate": fleet.get("fever_rate", 0.0),
            "anomaly_count": fleet.get("anomaly_count", 0),
            "anomaly_rate": fleet.get("anomaly_rate", 0.0),
            "channel_anomaly_counts": fleet.get("channel_anomaly_counts", {}),
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
    contam_engine: ContamTransportEngine | None,
    cfg: dict[str, Any],
    *,
    history_path: str | None = None,
    lab_notebook_path: str | None = None,
    logging_profile_path: str | None = None,
    display: bool = True,
) -> None:
    """Save simulation history, lab notebook, and print executive summary."""
    if history_path is None:
        history_path = os.path.join(
            REPO_ROOT, "telemetry_buffer", "simulation_history.json",
        )
    with open(history_path, "w", encoding="utf-8") as fh:
        json.dump(state.simulation_history, fh, indent=2)
    print(f"\n  Simulation history saved to: {history_path}")

    logging_config_path = os.path.join(REPO_ROOT, "data", "config", "logging_profile.json")
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
            nb_path = lab_notebook_path
        else:
            nb_output = logging_config.get("lab_notebook", {}).get(
                "output_path", "telemetry_buffer/artificial_lab_notebook.json",
            )
            nb_path = os.path.join(REPO_ROOT, nb_output)
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
            contam_engine=contam_engine,
            zone_pathogen_mass=engine.zone_pathogen_mass,
            hvac_cfg=cfg.get("hvac", {}),
            pathogen_profiles=pathogen_profiles,
            infection_counters=final_counters,
        )
