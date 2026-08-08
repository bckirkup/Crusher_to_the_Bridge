"""Epidemic takeoff vs fizzle labels for campaign derived metrics / Stan Stage A.

``ever_infected > 2`` only means a few secondary infections occurred. For
hurdle Stage A we need **fizzle vs takeoff**: did cumulative attack leave the
seed-noise regime?
"""

from __future__ import annotations

import math

# Attack-rate floor: 1% of the ship (VSP-suspect order of magnitude).
TAKEOFF_ATTACK_RATE = 0.01
# Absolute floor so tiny counts never count as takeoff on mid/large ships.
TAKEOFF_MIN_CASES = 5


def min_takeoff_cases(num_agents: int) -> int:
    """Minimum cumulative cases to count as takeoff on a ship of this size."""
    if num_agents <= 0:
        return TAKEOFF_MIN_CASES
    scaled = int(math.ceil(TAKEOFF_ATTACK_RATE * num_agents))
    return max(TAKEOFF_MIN_CASES, scaled)


def epidemic_took_off(ever_infected: int, num_agents: int) -> bool:
    """True if the epidemic took off (vs fizzled after seeding).

    Requires cumulative infections at least ``max(5, ceil(0.01 * N))`` —
    i.e. ≥1% attack rate and at least five cases.
    """
    if num_agents <= 0 or ever_infected <= 0:
        return False
    return ever_infected >= min_takeoff_cases(num_agents)


def seed_established(ever_infected: int) -> bool:
    """Legacy weak signal: more than the usual 1–2 index cases."""
    return ever_infected > 2
