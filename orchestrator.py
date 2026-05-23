#!/usr/bin/env python3
"""
orchestrator.py – The Master Intercom Loop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs a skeletal 24-epoch time-loop that:

1. Simulates a fake "Bridge update" by writing an incrementing mock payload
   to ``telemetry_buffer/ground_truth.json``.
2. Calls every ``crusher_labs`` modality to consume that file.
3. Prints a clean console confirmation showing successful data bridging
   without cross-contaminating memory spaces.

Usage::

    python orchestrator.py
"""

from __future__ import annotations

import math
import os
import sys

# Ensure the project root is on sys.path so sub-packages are importable
# regardless of the caller's working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telemetry_buffer.schema import (
    make_agent,
    make_ground_truth,
    make_space,
    read_ground_truth,
    write_ground_truth,
)
from crusher_labs import ALL_MODALITIES

# ── Configuration ────────────────────────────────────────────────────────
NUM_EPOCHS = 24
NUM_AGENTS = 6
ZONES = ["Bridge", "MedBay", "Mess_Hall", "Engine_Room"]

# ── Helpers ──────────────────────────────────────────────────────────────


def _generate_mock_agents(epoch: int) -> list[dict]:
    """Create a list of agent states that evolve with each epoch."""
    agents = []
    for aid in range(NUM_AGENTS):
        symptomatic = (epoch + aid) % 5 == 0
        agents.append(
            make_agent(
                agent_id=aid,
                symptom_status="symptomatic" if symptomatic else "asymptomatic",
                shedding_rate=round(50.0 * math.sin(epoch + aid) + 50.0, 2)
                if symptomatic
                else 0.0,
            )
        )
    return agents


def _generate_mock_spaces(epoch: int) -> dict[str, dict]:
    """Create zone states with pathogen mass that ramps over time."""
    return {
        zone: make_space(
            pathogen_mass=round((epoch + i) * 0.5, 2),
            microbiome_id=f"profile_{zone.lower()}",
        )
        for i, zone in enumerate(ZONES)
    }


# ── Main loop ────────────────────────────────────────────────────────────


def run() -> None:
    separator = "─" * 72

    print(separator)
    print("  CRUSHER TO THE BRIDGE  ·  Phase 1 Orchestration Verification")
    print(separator)
    print()

    modality_instances = [cls() for cls in ALL_MODALITIES]

    for epoch in range(NUM_EPOCHS):
        # 1. Bridge writes ground-truth state
        payload = make_ground_truth(
            epoch=epoch,
            agents=_generate_mock_agents(epoch),
            spaces=_generate_mock_spaces(epoch),
        )
        write_ground_truth(payload)

        # 2. Crusher Labs reads from the neutral buffer (separate IO call)
        truth = read_ground_truth()

        # Verify no shared-memory contamination: the dict we read back must
        # equal the dict we wrote, but must NOT be the same Python object.
        assert truth == payload, "Data mismatch between write and read!"
        assert truth is not payload, "Shared-memory leak detected!"

        # 3. Each modality queries the ground-truth independently
        results = {}
        for modality in modality_instances:
            results[modality.name] = modality.query_ground_truth(truth)

        # 4. Console confirmation
        syndromic = results["syndromic"]
        rdt = results["clinical_rdt"]
        pcr = results["targeted_pcr"]
        seq = results["sequencing"]

        positives_rdt = sum(1 for r in rdt["results"] if r["positive"])
        zones_detected_pcr = sum(
            1 for z in pcr["zone_results"].values() if z["detected"]
        )
        zones_detected_seq = sum(
            1 for z in seq["zone_results"].values() if z["pathogen_detected"]
        )

        print(
            f"[Epoch {epoch:02d}]  "
            f"Syndromic flags: {len(syndromic['flagged_agents'])}/{syndromic['total_screened']}  |  "
            f"RDT +ve: {positives_rdt}/{len(rdt['results'])}  |  "
            f"PCR zones: {zones_detected_pcr}/{len(pcr['zone_results'])}  |  "
            f"Seq zones: {zones_detected_seq}/{len(seq['zone_results'])}  |  "
            f"IO ✓"
        )

    print()
    print(separator)
    print("  All 24 epochs completed.  Data bridged cleanly – no leaks.")
    print(separator)


if __name__ == "__main__":
    run()
    sys.exit(0)
