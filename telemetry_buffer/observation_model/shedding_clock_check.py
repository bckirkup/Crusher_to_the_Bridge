"""Which authored shedding-curve days a shipped host actually reaches.

The pathogen profiles author a day-indexed shedding curve, and the epoch loop
clears an infection at ``onset + recovery_day``.  Those are two independent
statements about duration, and when the second is shorter than the first the
tail of the curve is unreachable: authored, and never emitted.

This script measures the overlap instead of reasoning about it.  It drives the
real progression seam for one host at a time, records the curve index behind
every epoch that emits, and reports the share of the authored curve integral
the clearance clock allows.  It changes nothing and fits nothing.

Run it as ``python3 telemetry_buffer/observation_model/shedding_clock_check.py``
from the repository root.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    InfectionStatus,
    KorkinAgent,
)
from orchestrator_epoch import (  # noqa: E402
    _advance_agent_pathogen_infections,
)

PROFILE_PATH = REPO_ROOT / "data" / "pathogens" / "active_profiles.json"
HOSTS = 200
HORIZON_DAYS = 40
SEED_DOSE = 1e4


def _profiles() -> dict[str, dict]:
    payload = json.loads(PROFILE_PATH.read_text())
    return {p["pathogen_id"]: p for p in payload["pathogens"]}


def _host(aid: int) -> KorkinAgent:
    return KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone="Cabin_A",
        dining_zone="MainDining_L",
        work_zone="MainDining_L",
        free_zone="Cabin_A",
        schedule=["Cabin_A"] * 24,  # clock-exempt: hour-of-day schedule
    )


def _onset_days(infection: dict, profile: dict, clock: object) -> float:
    """Days from infection to the onset axis the shedding curve is authored on."""
    onset_time = infection.get("onset_time_infected")
    if onset_time is not None:
        return float(clock.days_elapsed(int(onset_time)))
    incubation = infection.get("incubation_days")
    if incubation is not None:
        return float(incubation)
    return float(profile.get("symptom_onset_day", 1.0))


def _one_host(pathogen_id: str, profile: dict, seed: int) -> tuple[int, set[int]]:
    """Return the last day this host sheds on, and the curve indices it reaches."""
    rng = np.random.default_rng(seed)
    agent = _host(1)
    agent.infect_with_pathogen(pathogen_id, SEED_DOSE, 0, rng=rng, profile=profile)
    clock = agent.clock
    epochs_per_day = int(round(1.0 / clock.days_elapsed(1)))
    indices: set[int] = set()
    last_day = 0
    for epoch in range(HORIZON_DAYS * epochs_per_day):
        infection = agent.infections[pathogen_id]
        if infection["status"] != InfectionStatus.INFECTED:
            break
        if agent.get_pathogen_shedding(pathogen_id, profile) > 0.0:
            elapsed = clock.days_elapsed(int(infection["time_infected"] or 0))
            index = math.floor(elapsed - _onset_days(infection, profile, clock))
            indices.add(max(0, index))
            last_day = int(elapsed)
        _advance_agent_pathogen_infections(
            agent, {pathogen_id: profile}, rng, epoch=epoch,
        )
    return last_day, indices


def _integral_share(curve: list[float], reached: set[int]) -> float:
    """Share of the authored curve's linear-scale integral that is emitted."""
    total = sum(10.0**value for value in curve)
    if total <= 0.0:
        return 0.0
    emitted = sum(
        10.0**value for index, value in enumerate(curve) if index in reached
    )
    return emitted / total


def report(pathogen_id: str, profile: dict) -> None:
    reached: set[int] = set()
    last_days: list[int] = []
    for seed in range(HOSTS):
        last_day, indices = _one_host(pathogen_id, profile, seed)
        reached |= indices
        last_days.append(last_day)
    curve = [float(v) for v in profile.get("shedding_curve_log10", [])]
    asymptomatic = [
        float(v) for v in profile.get("asymptomatic_shedding_log10", [])
    ]
    print(f"\n{pathogen_id}")
    print(f"  authored curve days      : {len(curve)}")
    print(f"  recovery_day             : {profile.get('recovery_day')}")
    print(f"  curve indices reached    : {sorted(reached)}")
    print(
        "  last shedding day        : median "
        f"{int(np.median(last_days))} (range {min(last_days)}-{max(last_days)})",
    )
    print(
        "  symptomatic integral emitted : "
        f"{100.0 * _integral_share(curve, reached):.1f}%",
    )
    if asymptomatic:
        print(
            "  asymptomatic integral emitted: "
            f"{100.0 * _integral_share(asymptomatic, reached):.1f}%",
        )


def main() -> None:
    profiles = _profiles()
    for pathogen_id, profile in profiles.items():
        if not profile.get("shedding_curve_log10"):
            continue
        report(pathogen_id, profile)


if __name__ == "__main__":
    main()
