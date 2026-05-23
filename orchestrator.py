#!/usr/bin/env python3
"""
orchestrator.py – The Master Intercom Loop  (Phase 2.5)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Full human and clinical envelope initialization:

1. **Structural Environment (infection-dynamics + GRUMB):**
   Ship graph zones seeded with multi-kingdom log-ratio abundance arrays.

2. **Human Behavior (FRED reference):**
   Categorized background sick-call noise + quarantine compliance
   multiplier with stochastic behavioral failure.

3. **Clinical Progression (EMOD reference):**
   Shedding-phase-gated RDT sensitivity with early/peak/late caps.

Usage::

    python orchestrator.py
"""

from __future__ import annotations

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

# ── Trigger status constants ─────────────────────────────────────────────
STATUS_BASELINE = "BASELINE"
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"


# ── Initialization ───────────────────────────────────────────────────────

def _initialize_ship_graph(cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the ship graph from config (infection-dynamics reference).

    Returns zone list, agent role assignments, and traffic classifications.
    """
    graph_cfg = cfg.get("ship_graph", {})
    zones = graph_cfg.get("zones", [])
    num_agents = graph_cfg.get("num_agents", 20)
    roles_cfg = graph_cfg.get("agent_roles", {})
    passenger_frac = roles_cfg.get("passenger_fraction", 0.70)

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


# ── Mock Bridge engine helpers ───────────────────────────────────────────

def _generate_mock_agents(
    epoch: int,
    num_agents: int,
    isolated_ids: set[int],
    quarantine_refusers: set[int],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    """Create agent states with a realistic outbreak curve.

    Agents in ``quarantine_refusers`` are ordered to isolate but have not
    yet complied (FRED behavioral failure).
    """
    agents: list[dict[str, Any]] = []
    for aid in range(num_agents):
        if aid in isolated_ids:
            agents.append(make_agent(
                agent_id=aid,
                symptom_status="isolated",
                shedding_rate=0.0,
                location="Isolated_In_Quarters",
            ))
            continue

        if aid in quarantine_refusers:
            shedding = _shedding_curve(epoch, aid)
            agents.append(make_agent(
                agent_id=aid,
                symptom_status="non_compliant",
                shedding_rate=round(shedding, 2),
                location="Mess_Hall",
            ))
            continue

        infection_prob = _infection_probability(epoch, aid, num_agents)
        is_infected = rng.random() < infection_prob

        if is_infected:
            shedding = _shedding_curve(epoch, aid)
            agents.append(make_agent(
                agent_id=aid,
                symptom_status="symptomatic",
                shedding_rate=round(shedding, 2),
            ))
        else:
            agents.append(make_agent(
                agent_id=aid,
                symptom_status="asymptomatic",
                shedding_rate=0.0,
            ))
    return agents


def _infection_probability(epoch: int, aid: int, num_agents: int) -> float:
    """Logistic infection curve: slow start, accelerating spread."""
    onset = 3 + (aid % 5)
    if epoch < onset:
        return 0.0
    x = (epoch - onset) / 4.0
    return min(0.85, 1.0 / (1.0 + math.exp(-1.5 * (x - 1.5))))


def _shedding_curve(epoch: int, aid: int) -> float:
    """Shedding ramps up over time from initial infection."""
    onset = 3 + (aid % 5)
    days_infected = max(0, epoch - onset)
    peak = 80.0 + (aid % 3) * 10.0
    return peak * (1.0 - math.exp(-0.5 * days_infected))


def _generate_mock_spaces(
    epoch: int,
    active_agent_count: int,
    zone_names: list[str],
    rng: np.random.Generator,
) -> dict[str, dict[str, Any]]:
    """Create zone states with pathogen mass from shedding agents."""
    spaces: dict[str, dict[str, Any]] = {}
    for i, zone in enumerate(zone_names):
        base_mass = max(0.0, (epoch - 2) * 2.5 * (1.0 + i * 0.3))
        agent_contribution = active_agent_count * 0.6 * epoch * 0.2
        noise = rng.normal(0, 0.5)
        mass = max(0.0, base_mass + agent_contribution + noise)
        spaces[zone] = make_space(
            pathogen_mass=round(mass, 3),
            microbiome_id=f"profile_{zone.lower()}",
        )
    return spaces


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
    print("  CRUSHER TO THE BRIDGE  ·  Phase 2.5 – Full Envelope Initialization")
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

    grumb_seeds = _initialize_grumb_seeding(seq, ship["zones"])
    _print_initialization(ship, grumb_seeds, cfg)

    trigger_status = STATUS_BASELINE
    isolated_ids: set[int] = set()
    quarantine_refusers: set[int] = set()
    quarantine_order_epoch: dict[int, int] = {}
    escalation_log: list[dict[str, Any]] = []
    compliance_log: list[dict[str, Any]] = []

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

        # ── 2. Bridge writes ground-truth ────────────────────────────
        agents = _generate_mock_agents(
            epoch, num_agents, isolated_ids, quarantine_refusers, rng,
        )
        active_symptomatic = sum(
            1 for a in agents
            if a["symptom_status"] in ("symptomatic", "non_compliant")
        )
        spaces = _generate_mock_spaces(epoch, active_symptomatic, zone_names, rng)

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

        # ── 10. Console output ──────────────────────────────────────
        _print_epoch(
            epoch, trigger_status, syn_result, rdt_result,
            pcr_result, seq_result, active_symptomatic,
            len(isolated_ids), len(quarantine_refusers), prev_status,
        )

    # ── Summary ──────────────────────────────────────────────────────
    print()
    print(sep)
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
