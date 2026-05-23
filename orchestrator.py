#!/usr/bin/env python3
"""
orchestrator.py – The Master Intercom Loop  (Phase 3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Real infection-dynamics engine integration:

1. **Real ABM Core (Korkin Lab infection-dynamics):**
   Agent graph initialised from the actual Norwalk model parameters
   (shedding curves, dose-response, SEIQR progression, spatial nodes).
   Replaces all mock agent/space generation.

2. **Structural Environment (GRUMB):**
   Ship graph zones seeded with multi-kingdom log-ratio abundance arrays.

3. **Human Behavior (FRED reference):**
   Categorized background sick-call noise + quarantine compliance
   multiplier with stochastic behavioral failure.

4. **Clinical Progression (EMOD reference):**
   Shedding-phase-gated RDT sensitivity with early/peak/late caps.

Usage::

    python orchestrator.py
"""

from __future__ import annotations

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
from engines.infection_dynamics_bridge import KorkinShipEngine
from engines.py_contam_bridge import build_transport_engine, ContamTransportEngine

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
            agents_out.append(make_agent(
                agent_id=aid,
                symptom_status="isolated",
                shedding_rate=0.0,
                location="Isolated_In_Quarters",
            ))
        elif aid in quarantine_refusers:
            agents_out.append(make_agent(
                agent_id=aid,
                symptom_status="non_compliant",
                shedding_rate=a.get("shedding_rate", 0.0),
                location=a.get("location", "unknown"),
            ))
        else:
            agents_out.append(make_agent(
                agent_id=aid,
                symptom_status=a["symptom_status"],
                shedding_rate=a.get("shedding_rate", 0.0),
                location=a.get("location"),
            ))

    spaces_out: dict[str, dict[str, Any]] = {}
    for zname, zdata in engine_payload.get("spaces", {}).items():
        spaces_out[zname] = make_space(
            pathogen_mass=zdata.get("pathogen_mass", 0.0),
            microbiome_id=zdata.get("microbiome_id", f"profile_{zname.lower()}"),
        )

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

def run() -> None:
    sep = "═" * 80
    thin = "─" * 80

    print(sep)
    print("  CRUSHER TO THE BRIDGE  ·  Phase 3.5 – CONTAM Aerosol Transport")
    print(sep)
    print()

    cfg = load_config()
    seed = cfg.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    modalities = build_modalities(cfg, rng, total_epochs=24)

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

    grumb_seeds = _initialize_grumb_seeding(seq, ship["zones"])
    _print_initialization(ship, grumb_seeds, cfg)

    trigger_status = STATUS_BASELINE
    isolated_ids: set[int] = set()
    quarantine_refusers: set[int] = set()
    quarantine_order_epoch: dict[int, int] = {}
    escalation_log: list[dict[str, Any]] = []
    compliance_log: list[dict[str, Any]] = []
    simulation_history: list[dict[str, Any]] = []

    num_epochs = 24

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

        # ── 2. Real engine step ───────────────────────────────────────
        # Feed FRED isolation overrides into engine before stepping
        engine.isolated_ids = set(isolated_ids)
        engine_payload = engine.step()

        # ── 2b. CONTAM aerosol mass transport ─────────────────────────
        # After shedding deposits are added by the engine, run the
        # CONTAM multi-zone transport to distribute airborne pathogen
        # mass through the HVAC network with filter efficiency applied.
        if contam_engine is not None:
            updated_masses = contam_engine.transport_step(
                engine.zone_pathogen_mass,
            )
            engine.zone_pathogen_mass = updated_masses
            # Re-export payload with updated zone masses
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

        # ── 7. Metagenomic sequencing ───────────────────────────────
        seq_result = None
        seq_cadence = cfg.get("sequencing", {}).get("cadence", 8)
        if epoch % seq_cadence == 0:
            seq_result = seq.query_ground_truth(truth)

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
            },
            "hvac": {
                "filter_type": cfg.get("hvac", {}).get("filter_type", "none"),
                "filter_efficiency": (
                    contam_engine.filter_efficiency if contam_engine else 0.0
                ),
                "transport_active": contam_engine is not None,
            },
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

            epoch_record["agents"].append({
                "agent_id": a["agent_id"],
                "status": status,
                "shedding_rate": a.get("shedding_rate", 0.0),
                "location": a.get("location", "unknown"),
            })

        for zname, zdata in spaces.items():
            zone_entry: dict[str, Any] = {
                "pathogen_mass": zdata.get("pathogen_mass", 0.0),
            }
            if contam_engine is not None:
                node = contam_engine.zone_nodes.get(zname)
                if node is not None:
                    zone_entry["concentration_per_m3"] = round(
                        node.concentration(zdata.get("pathogen_mass", 0.0)), 3,
                    )
                    zone_entry["volume_m3"] = node.volume_m3
            epoch_record["spaces"][zname] = zone_entry

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

        simulation_history.append(epoch_record)

        # ── 11. Console output ──────────────────────────────────────
        _print_epoch(
            epoch, trigger_status, syn_result, rdt_result,
            pcr_result, seq_result, active_symptomatic,
            len(isolated_ids), len(quarantine_refusers), prev_status,
        )

    # ── Save simulation history ──────────────────────────────────────
    history_path = os.path.join(
        _REPO_ROOT, "telemetry_buffer", "simulation_history.json",
    )
    with open(history_path, "w", encoding="utf-8") as fh:
        json.dump(simulation_history, fh, indent=2)
    print(f"\n  Simulation history saved to: {history_path}")

    # ── Summary ──────────────────────────────────────────────────────
    print()
    print(sep)

    # Engine final state
    final_summary = engine.get_summary()
    print("  KORKIN LAB ENGINE – FINAL STATE")
    print(thin)
    print(f"  Susceptible: {final_summary['susceptible']}")
    print(f"  Infected:    {final_summary['infected']}")
    print(f"  Symptomatic: {final_summary['symptomatic']}")
    print(f"  Recovered:   {final_summary['recovered']}")
    print(f"  Immune:      {final_summary['immune']}")
    print(f"  Isolated:    {final_summary['isolated']}")
    print(f"  VSP triggered: {final_summary['vsp_triggered']}")
    print()

    if contam_engine is not None:
        print("  CONTAM TRANSPORT ENGINE – FINAL STATE")
        print(thin)
        transport_final = contam_engine.get_transport_summary(engine.zone_pathogen_mass)
        hvac_cfg = cfg.get("hvac", {})
        print(f"  Filter type:        {hvac_cfg.get('filter_type', 'MERV-13')}")
        print(f"  Filter efficiency:  {contam_engine.filter_efficiency:.1%}")
        print(f"  Natural decay rate: {contam_engine.natural_decay_rate:.1%} per epoch")
        for zname, zdata in transport_final["zone_concentrations"].items():
            print(f"    {zname:15s}  mass={zdata['mass']:8.3f}  "
                  f"conc={zdata['concentration_per_m3']:8.3f}/m³  "
                  f"vol={zdata['volume_m3']}m³")
        print()

    print("  ESCALATION TIMELINE")
    print(thin)
    for entry in escalation_log:
        print(f"  Epoch {entry['epoch']:02d}:  {entry['from']}  →  {entry['to']}")
    if not escalation_log:
        print("  (no escalations triggered)")

    if compliance_log:
        print()
        print("  FRED COMPLIANCE LOG")
        print(thin)
        refused = [c for c in compliance_log if c["action"] == "refused_quarantine"]
        delayed = [c for c in compliance_log if c["action"] == "delayed_compliance"]
        immediate = [c for c in compliance_log if c["action"] == "immediate_compliance"]
        print(f"  Immediate compliance: {len(immediate)}")
        print(f"  Refused (then delayed): {len(refused)} refused, {len(delayed)} eventually complied")

    print(thin)
    print(f"  Final status: {trigger_status}")
    print(f"  Agents isolated: {len(isolated_ids)}/{num_agents}")
    print(f"  Non-compliant remaining: {len(quarantine_refusers)}")
    print(f"  All {num_epochs} epochs completed.  Data bridged cleanly.")
    print(sep)


def _print_epoch(
    epoch: int,
    trigger_status: str,
    syn: dict[str, Any],
    rdt: dict[str, Any],
    pcr: dict[str, Any] | None,
    seq: dict[str, Any] | None,
    symptomatic_count: int,
    isolated_count: int,
    refuser_count: int,
    prev_status: str,
) -> None:
    """Print a single epoch's diagnostic summary line."""
    status_icon = {
        STATUS_BASELINE: "●",
        STATUS_SUSPECTED: "▲",
        STATUS_CONFIRMED: "■",
    }.get(trigger_status, "?")

    rdt_pos = sum(1 for r in rdt["results"] if r["positive"])
    rdt_total = rdt["tested_count"]

    # Show clinical phases for RDT results
    phases = {}
    for r in rdt["results"]:
        ph = r.get("clinical_phase", "—")
        if ph:
            phases[ph] = phases.get(ph, 0) + 1

    pcr_str = "—"
    if pcr is not None:
        detected = sum(1 for z in pcr["zone_results"].values() if z["detected"])
        total_z = len(pcr["zone_results"])
        best_ct = min(
            (z["ct_value"] for z in pcr["zone_results"].values() if z["ct_value"] is not None),
            default=None,
        )
        ct_label = f"Ct={best_ct:.1f}" if best_ct is not None else "Ct=n/a"
        mode = "WIPE" if pcr.get("surface_wipe_mode") else "env"
        pcr_str = f"{detected}/{total_z} {ct_label} [{mode}]"

    seq_str = "—"
    if seq is not None:
        first_zone = next(iter(seq["zone_results"].values()), {})
        regime = first_zone.get("regime", "?")
        drift = first_zone.get("drift_alpha", 0)
        path_reads = sum(
            z.get("pathogen_reads", 0) for z in seq["zone_results"].values()
        )
        seq_str = f"{regime}(α={drift:.2f}) pReads={path_reads}"

    transition = ""
    if trigger_status != prev_status:
        transition = f"  *** {prev_status} → {trigger_status} ***"

    noise_reasons = syn.get("noise_reasons", [])
    noise_str = ""
    if noise_reasons:
        reasons = [r["reason"] for r in noise_reasons]
        noise_str = f" [{','.join(reasons)}]"

    print(
        f"[Epoch {epoch:02d}] {status_icon} {trigger_status:<10s} | "
        f"Sick: {syn['sick_call_count']:2d} "
        f"(TP:{len(syn['true_positive_ids'])} noise:{len(syn['noise_ids'])}){noise_str} | "
        f"RDT: {rdt_pos}/{rdt_total} | "
        f"PCR: {pcr_str} | "
        f"Seq: {seq_str} | "
        f"Symp:{symptomatic_count:2d} Iso:{isolated_count:2d} Ref:{refuser_count:1d}"
        f"{transition}"
    )


if __name__ == "__main__":
    run()
    sys.exit(0)
