#!/usr/bin/env python3
"""
orchestrator.py – The Master Intercom Loop  (Phase 4+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thin coordinator that wires together initialization, epoch stepping,
recording, and display modules.  All domain logic lives in:

- ``orchestrator_types.py``   – dataclasses and constants
- ``orchestrator_init.py``    – spatial / engine / observation setup
- ``orchestrator_epoch.py``   – per-epoch step functions
- ``orchestrator_record.py``  – history recording and finalization
- ``orchestrator_display.py`` – terminal output helpers

Usage::

    python orchestrator.py              # uses num_epochs from config.yaml (default 24)
    python orchestrator.py --epochs 250 # override to 250 epochs
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from telemetry_buffer.schema import (
    make_ground_truth,
    read_ground_truth,
    write_ground_truth,
)
from crusher_labs import build_modalities, load_config
from engines.py_contam_bridge import (
    build_transport_engine,
    load_air_flow_paths,
)
from engines.infection_dynamics_bridge import VSP_THRESHOLD_FRACTION
from engines.transmission_core import (
    TransmissionCore,
    build_hvac_downstream_map,
)
from crusher_labs.protocol_engine import (
    compute_stoplights,
    apply_hvac_modifiers,
    apply_transmission_modifiers,
    reset_modifiers,
)

from orchestrator_types import (
    STATUS_SUSPECTED,
    STATUS_CONFIRMED,
    REPO_ROOT,
    SimulationState,
)
from orchestrator_init import (
    initialize_ship_graph,
    initialize_grumb_seeding,
    build_engine,
    engine_payload_to_schema,
    check_escalation,
    load_pathogen_profiles,
    init_multi_pathogen,
    init_observation_engine,
    init_protocol_engine,
    init_wearable_monitors,
)
from orchestrator_epoch import (
    sync_vsp_isolation,
    step_fred_compliance,
    step_mid_cruise_introductions,
    step_infection_progression,
    run_observation_sampling,
    step_quarantine_confinement,
    step_cost_accounting,
    compute_zone_microflora_shifts,
    step_wearable_monitoring,
    apply_surface_decontamination,
    apply_zone_closures,
)
from orchestrator_record import (
    record_epoch,
    finalize_simulation,
)
from orchestrator_display import (
    print_initialization,
    print_korkin_engine,
    print_wearable_monitoring,
    print_contam_engine,
    print_multi_pathogen,
    print_transmission_core,
    print_progress,
)


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
    ship = initialize_ship_graph(cfg)
    num_agents = ship["num_agents"]
    zone_names = ship["zone_names"]
    high_traffic = ship["high_traffic_zones"]

    engine = build_engine(cfg, seed=seed)
    print_korkin_engine(engine)

    contam_engine = build_transport_engine(REPO_ROOT, cfg)
    if contam_engine is not None:
        engine.enable_external_transport()
    print_contam_engine(contam_engine, engine, cfg)

    pathogen_profiles = load_pathogen_profiles(cfg)
    mp_cfg = cfg.get("multi_pathogen", {})
    mf_cfg = cfg.get("microflora", {})
    enable_dual_signal = mf_cfg.get("enable_dual_signal", True)

    immunocompromised_ids = init_multi_pathogen(engine, pathogen_profiles, cfg, rng)
    imm_mult = mp_cfg.get("immunocompromised_multiplier", 2.0)
    print_multi_pathogen(pathogen_profiles, immunocompromised_ids, engine, imm_mult, enable_dual_signal)

    airflow_data = load_air_flow_paths(REPO_ROOT, cfg)
    zone_volumes = {
        z["name"]: z.get("volume_m3", 100.0)
        for z in ship.get("zones", [])
    }
    zone_types = {
        z["name"]: z.get("type", "")
        for z in ship.get("zones", [])
    }
    hvac_downstream = build_hvac_downstream_map(airflow_data) if airflow_data else {}
    tx_core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=zone_volumes,
        pathogen_profiles=pathogen_profiles,
        zone_types=zone_types,
    )
    tx_core.initialize_zones(zone_names)
    engine.enable_external_transmission()
    print_transmission_core(hvac_downstream, pathogen_profiles)

    obs = init_observation_engine(cfg, seed)
    proto_ctx = init_protocol_engine(cfg, contam_engine)

    wearable_monitor, wearable_modality = init_wearable_monitors(engine, cfg, seed)
    print_wearable_monitoring(wearable_monitor)

    grumb_seeds = initialize_grumb_seeding(seq, ship["zones"])
    print_initialization(ship, grumb_seeds, cfg)

    state = SimulationState()

    # ── EPOCH LOOP ───────────────────────────────────────────────────
    for epoch in range(num_epochs):
        step_fred_compliance(epoch, state, syndromic)
        step_mid_cruise_introductions(epoch, engine, pathogen_profiles, rng)

        engine.isolated_ids = set(state.isolated_ids)
        engine_payload = engine.step()
        sync_vsp_isolation(epoch, engine, state)

        step_infection_progression(engine, pathogen_profiles)

        tracing_matrix, tx_events = tx_core.execute_transmission(
            epoch=epoch,
            agents=engine.agents,
            zone_pathogen_mass=engine.zone_pathogen_mass,
            hvac_downstream_zones=hvac_downstream,
            multi_pathogen_mass=(
                engine.multi_pathogen_mass if pathogen_profiles else None
            ),
        )

        if contam_engine is not None:
            updated_masses = contam_engine.transport_step(engine.zone_pathogen_mass)
            engine.zone_pathogen_mass = updated_masses

        zone_microflora_shifts: dict[str, dict[str, float]] = {}
        if pathogen_profiles and enable_dual_signal:
            zone_microflora_shifts = compute_zone_microflora_shifts(
                engine.agents, pathogen_profiles, cfg,
            )

        engine_payload = engine._export_payload()

        agents, spaces = engine_payload_to_schema(
            engine_payload, state.isolated_ids, state.quarantine_refusers,
        )

        payload = make_ground_truth(epoch=epoch, agents=agents, spaces=spaces)
        write_ground_truth(payload)

        truth = read_ground_truth()
        assert truth is not payload, "Shared-memory leak!"

        wearable_result = step_wearable_monitoring(
            epoch, engine, wearable_monitor, wearable_modality,
            truth, pathogen_profiles,
        )

        syn_result = syndromic.query_ground_truth(truth)

        sick_call_ids = syn_result["sick_call_agents"]
        rdt_result = rdt.query_ground_truth(truth, sick_call_ids=sick_call_ids)

        pcr_result = None
        if state.trigger_status == STATUS_SUSPECTED:
            pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=high_traffic)
        elif state.trigger_status == STATUS_CONFIRMED:
            pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=zone_names)
        else:
            pcr_cadence = cfg.get("targeted_pcr", {}).get("cadence", 4)
            if epoch % pcr_cadence == 0:
                pcr_result = pcr.query_ground_truth(truth)

        seq_result = None
        seq_cadence = cfg.get("sequencing", {}).get("cadence", 8)
        if epoch % seq_cadence == 0:
            seq_result = seq.query_ground_truth(
                truth, zone_microflora_shifts=zone_microflora_shifts,
            )

        (air_results, swab_results, ww_results,
         clin_rdt_results, clin_qpcr_results, clin_microbio_results) = (
            run_observation_sampling(
                epoch, obs, agents, spaces, zone_names, zone_volumes,
                zone_microflora_shifts, state.trigger_status, high_traffic,
                syn_result, engine, pathogen_profiles, cfg,
            )
        )

        prev_status = state.trigger_status
        state.trigger_status = check_escalation(
            state.trigger_status, syn_result, pcr_result, cfg,
        )
        if state.trigger_status != prev_status:
            state.escalation_log.append({
                "epoch": epoch,
                "from": prev_status,
                "to": state.trigger_status,
            })
            obs.notebook.log_trigger_transition(epoch, prev_status, state.trigger_status)

        stoplights = compute_stoplights(
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )
        reset_modifiers(contam_engine, tx_core, proto_ctx.original_filter_eff)
        engine.vsp_threshold_fraction = VSP_THRESHOLD_FRACTION
        active_mods = proto_ctx.protocol_engine.evaluate_epoch(epoch, stoplights)
        merged_mods = proto_ctx.protocol_engine.get_merged_modifiers(active_mods)

        if merged_mods:
            apply_hvac_modifiers(contam_engine, merged_mods)
            apply_transmission_modifiers(tx_core, merged_mods)

            # SOP-009: close specified zones, relocating agents
            if "close_zones" in merged_mods:
                apply_zone_closures(engine, merged_mods["close_zones"])

            # SOP-010: surface decontamination
            if "surface_decontamination_factor" in merged_mods:
                apply_surface_decontamination(
                    engine, merged_mods["surface_decontamination_factor"],
                )

            # SOP-010: override engine VSP threshold from protocol config
            if "vsp_isolation_threshold_fraction" in merged_mods:
                engine.vsp_threshold_fraction = merged_mods["vsp_isolation_threshold_fraction"]

        step_cost_accounting(
            epoch, proto_ctx,
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )

        step_quarantine_confinement(
            epoch, agents, merged_mods, state.trigger_status, state, syndromic,
        )

        epoch_cost = proto_ctx.cost_ledger.get_epoch_summary(epoch)
        epoch_record = record_epoch(
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
            wearable_result=wearable_result,
        )
        state.simulation_history.append(epoch_record)

        n_active_sops = len(active_mods)
        total_spent = proto_ctx.cost_ledger.starting_financial_usd - proto_ctx.cost_ledger.financial_balance
        print_progress(epoch, num_epochs, state.trigger_status, n_active_sops, total_spent, prev_status)

    # ── FINALIZATION ─────────────────────────────────────────────────
    finalize_simulation(
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
