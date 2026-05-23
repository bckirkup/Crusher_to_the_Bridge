#!/usr/bin/env python3
"""
orchestrator.py – The Master Intercom Loop  (Phase 2)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs a 24-epoch time-loop with:

- **Noise-injected modalities** driven by ``crusher_labs/config.yaml``.
- **Shifting marine baseline** (Coastal Port → Open Ocean → Port).
- **Triggered Escalation Matrix** that transitions the simulation
  through BASELINE → SUSPECTED → CONFIRMED states, dynamically
  altering sampling cadence, surface-wipe routing, and agent
  quarantine schedules.

Usage::

    python orchestrator.py
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any

# Ensure the project root is on sys.path.
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

# ── Configuration ────────────────────────────────────────────────────────
NUM_EPOCHS = 24
NUM_AGENTS = 20
ZONES = ["Bridge", "MedBay", "Mess_Hall", "Engine_Room", "Galley", "Berthing"]
HIGH_TRAFFIC_ZONES = ["Mess_Hall", "Galley", "Engine_Room"]

# ── Trigger status constants ─────────────────────────────────────────────
STATUS_BASELINE = "BASELINE"
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"


# ── Mock Bridge engine helpers ───────────────────────────────────────────

def _generate_mock_agents(
    epoch: int,
    num_agents: int,
    isolated_ids: set[int],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    """Create agent states with a realistic outbreak curve.

    An outbreak begins quietly around epoch 3-4, accelerates through
    the mid-simulation, and is suppressed when agents are isolated.
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
    rng: np.random.Generator,
) -> dict[str, dict[str, Any]]:
    """Create zone states with pathogen mass from shedding agents."""
    spaces: dict[str, dict[str, Any]] = {}
    for i, zone in enumerate(ZONES):
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
    print("  CRUSHER TO THE BRIDGE  ·  Phase 2 – Triggered Escalation Matrix")
    print(sep)
    print()

    cfg = load_config()
    seed = cfg.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    modalities = build_modalities(cfg, rng, total_epochs=NUM_EPOCHS)

    syndromic = modalities["syndromic"]
    rdt = modalities["clinical_rdt"]
    pcr = modalities["targeted_pcr"]
    seq = modalities["sequencing"]

    trigger_status = STATUS_BASELINE
    isolated_ids: set[int] = set()
    escalation_log: list[dict[str, Any]] = []

    for epoch in range(NUM_EPOCHS):
        # ── 1. Bridge writes ground-truth ────────────────────────────
        active_symptomatic = 0
        agents = _generate_mock_agents(epoch, NUM_AGENTS, isolated_ids, rng)
        active_symptomatic = sum(
            1 for a in agents
            if a["symptom_status"] == "symptomatic"
        )
        spaces = _generate_mock_spaces(epoch, active_symptomatic, rng)

        payload = make_ground_truth(epoch=epoch, agents=agents, spaces=spaces)
        write_ground_truth(payload)

        # ── 2. Read back from neutral buffer (decoupled IO) ─────────
        truth = read_ground_truth()
        assert truth is not payload, "Shared-memory leak!"

        # ── 3. Syndromic surveillance (every epoch) ─────────────────
        syn_result = syndromic.query_ground_truth(truth)
        sick_call_ids = syn_result["sick_call_agents"]

        # ── 4. Clinical RDT on sick-call agents ─────────────────────
        rdt_result = rdt.query_ground_truth(truth, sick_call_ids=sick_call_ids)

        # ── 5. Targeted PCR ─────────────────────────────────────────
        pcr_result = None
        if trigger_status == STATUS_SUSPECTED:
            pcr_result = pcr.query_ground_truth(
                truth, surface_wipe_zones=HIGH_TRAFFIC_ZONES,
            )
        elif trigger_status == STATUS_CONFIRMED:
            pcr_result = pcr.query_ground_truth(
                truth, surface_wipe_zones=list(spaces.keys()),
            )
        else:
            pcr_cadence = cfg.get("targeted_pcr", {}).get("cadence", 4)
            if epoch % pcr_cadence == 0:
                pcr_result = pcr.query_ground_truth(truth)

        # ── 6. Metagenomic sequencing ───────────────────────────────
        seq_result = None
        seq_cadence = cfg.get("sequencing", {}).get("cadence", 8)
        if epoch % seq_cadence == 0:
            seq_result = seq.query_ground_truth(truth)

        # ── 7. Escalation check ─────────────────────────────────────
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

        # ── 8. CONFIRMED → quarantine symptomatic/shedding agents ───
        if trigger_status == STATUS_CONFIRMED:
            for agent in agents:
                if (
                    agent["symptom_status"] == "symptomatic"
                    or agent.get("shedding_rate", 0.0) > 0.0
                ):
                    isolated_ids.add(agent["agent_id"])

        # ── 9. Console output ───────────────────────────────────────
        _print_epoch(
            epoch, trigger_status, syn_result, rdt_result,
            pcr_result, seq_result, active_symptomatic,
            len(isolated_ids), prev_status,
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
    print(thin)
    print(f"  Final status: {trigger_status}")
    print(f"  Agents isolated: {len(isolated_ids)}/{NUM_AGENTS}")
    print(f"  All {NUM_EPOCHS} epochs completed.  Data bridged cleanly.")
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
        seq_str = f"{regime}(α={drift:.2f}) pathReads={path_reads}"

    transition = ""
    if trigger_status != prev_status:
        transition = f"  *** {prev_status} → {trigger_status} ***"

    print(
        f"[Epoch {epoch:02d}] {status_icon} {trigger_status:<10s} | "
        f"Sick-call: {syn['sick_call_count']:2d} "
        f"(TP:{len(syn['true_positive_ids'])} noise:{len(syn['noise_ids'])}) | "
        f"RDT: {rdt_pos}/{rdt_total} | "
        f"PCR: {pcr_str} | "
        f"Seq: {seq_str} | "
        f"Symp: {symptomatic_count:2d} Iso: {isolated_count:2d}"
        f"{transition}"
    )


if __name__ == "__main__":
    run()
    sys.exit(0)
