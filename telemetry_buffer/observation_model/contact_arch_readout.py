"""Section-6 readout for the shipped ``transmission.activity_contacts``.

Reproduces the ``contact_architecture_spec.md`` §8a method: run one voyage of
the shipped configuration, resolve every host's contact activity per epoch
with the engine's own resolver (``_contact_activity`` over
``_direct_contact_units``), and sum each host's expected draw
(``rate x epoch hours``). It reports per-role expected contacts/day, the
night share and the passenger dining share against the §6 references (Pung
medians 20/10, Mossong 13.4, Vanhems 5.9% night, Pung 71% dining).

It measures the declared vector only. It does not license adjusting a rate:
the §6 totals are out-of-sample checks, and a total outside 5-40 is a
declaration error to record, not a number to move. An agent standing in a
Cabin_Corridor zone appears in the hallway residual unit every epoch, so
``corridor`` accrues against cabin residency too -- the readout reports the
shipped semantics as they are.

Usage: PYTHONPATH=. python3 telemetry_buffer/observation_model/contact_arch_readout.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework import PicardRunSpec, ShipSimulation  # noqa: E402

DINING_ACTIVITIES = ("dining_table", "dining_venue")


def _accumulate_epoch(core, agents: list, totals: dict, by_activity: dict,
                      sleep_exp: dict, dining_exp: dict) -> None:
    """One epoch's expected contact draws, per role and resolved activity."""
    zone_occupants: dict[str, list] = defaultdict(list)
    for agent in agents:
        loc = agent.current_location
        if loc in ("Isolated_In_Quarters", "Ashore") or getattr(agent, "ashore", False):
            continue
        zone_occupants[loc].append(agent)
    for unit_name, occupants, hallway in core._direct_contact_units(zone_occupants):
        zone_name = core.compartment_parent(unit_name)
        for agent in occupants:
            activity = core._contact_activity(
                agent, unit_name, zone_name, hallway, 0,
            )
            expected = core.activity_contacts[activity][agent.role] * (
                core.clock.hours_per_epoch
            )
            totals[agent.role] += expected
            by_activity[agent.role][activity] += expected
            token = core._scheduled_activity(agent, 0).split(":", 1)[0]
            if token == "Sleep":
                sleep_exp[agent.role] += expected
            if activity in DINING_ACTIVITIES:
                dining_exp[agent.role] += expected


def main() -> None:
    spec = PicardRunSpec.from_legacy_yaml(
        repo_root=str(REPO_ROOT), num_epochs=24 * 7,  # clock-exempt: hours in a day for the 7-day readout window
    )
    sim = ShipSimulation(spec, display=False)
    core = None
    totals: dict[str, float] = defaultdict(float)
    by_activity: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )
    sleep_exp: dict[str, float] = defaultdict(float)
    dining_exp: dict[str, float] = defaultdict(float)
    for _ in range(spec.num_epochs):
        sim.step()
        if core is None:
            core = sim.tx_core
        _accumulate_epoch(
            core, sim.engine.agents, totals, by_activity, sleep_exp, dining_exp,
        )
    role_counts: dict[str, int] = defaultdict(int)
    for agent in sim.engine.agents:
        role_counts[agent.role] += 1
    days = spec.num_epochs * core.clock.hours_per_epoch / 24.0  # clock-exempt: epoch hours back to days for a per-day readout
    print(f"voyage days: {days}, epoch hours: {core.clock.hours_per_epoch}")
    for role in ("passenger", "crew"):
        n = role_counts[role]
        per_day = totals[role] / n / days
        print(f"{role}: n={n} expected contacts/day = {per_day:.2f}")
        print(f"  night share = {sleep_exp[role] / totals[role] * 100:.1f}%")
        print(f"  dining share = {dining_exp[role] / totals[role] * 100:.1f}%")
        print("  by activity:", {
            activity: round(value / n / days, 2)
            for activity, value in sorted(by_activity[role].items())
        })
    pax_day = totals["passenger"] / role_counts["passenger"]
    crew_day = totals["crew"] / role_counts["crew"]
    print(f"crew:passenger ratio = {crew_day / pax_day:.2f}")


if __name__ == "__main__":
    main()
