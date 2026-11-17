"""Continuous within-epoch hand-mediated contamination flow.

The discrete pathway deposits hands to surfaces/food and then picks up once
per epoch, which makes the answer depend on the arbitrary epoch boundary.
This module integrates the same pooled mass exchange in continuous time: hand
mass moves to surface and food pools, surface mass moves back to hands, food
is eaten, and hand-to-mouth contact removes dose continuously. It is a
staged-aggregate solver: it reuses the engine's contact/transfer kernels as
constant per-epoch rates and integrates the resulting linear flow, rather
than introducing new epidemiological constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable


@dataclass
class FlowResult:
    """Endpoint masses and cumulative dose fluxes for one pathogen epoch."""

    hand: dict[Hashable, float] = field(default_factory=dict)
    surface: dict[str, float] = field(default_factory=dict)
    food: dict[str, float] = field(default_factory=dict)
    mouth_dose: dict[Hashable, float] = field(default_factory=dict)
    food_dose: dict[Hashable, float] = field(default_factory=dict)
    pickup_mass: dict[Hashable, float] = field(default_factory=dict)


def _rk4_step(
    y: list[float],
    dt: float,
    rhs: Any,
) -> list[float]:
    k1 = rhs(y)
    y2 = [v + 0.5 * dt * k for v, k in zip(y, k1, strict=True)]
    k2 = rhs(y2)
    y3 = [v + 0.5 * dt * k for v, k in zip(y, k2, strict=True)]
    k3 = rhs(y3)
    y4 = [v + dt * k for v, k in zip(y, k3, strict=True)]
    k4 = rhs(y4)
    return [
        v + (dt / 6.0) * (a + 2.0 * b + 2.0 * c + d)
        for v, a, b, c, d in zip(y, k1, k2, k3, k4, strict=True)
    ]


def integrate_hand_flow(
    *,
    hours: float,
    agent_ids: list[Hashable],
    surface_units: list[str],
    food_zones: list[str],
    hand0: dict[Hashable, float],
    surface0: dict[str, float],
    food0: dict[str, float],
    surface_deposit: dict[tuple[Hashable, str], float],
    surface_pickup: dict[tuple[Hashable, str], float],
    food_deposit: dict[tuple[Hashable, str], float],
    mouth_rate: dict[Hashable, float],
    food_growth_rate: dict[str, float],
    food_removal_rate: dict[str, float],
    food_dose_rate: dict[tuple[Hashable, str], float],
    food_dose_denominator: dict[str, float],
    steps: int = 24,
) -> FlowResult:
    """Integrate hand/surface/food mass exchange over ``hours``.

    Rates are per hour. ``surface_pickup`` is a fraction of the surface pool
    transferred to one hand per hour; ``surface_deposit``/``food_deposit`` are
    fractions of one hand transferred per hour. ``food_removal_rate`` is the
    fraction of a food pool eaten per hour and ``food_dose_rate`` carries the
    susceptible-diner share (already divided by occupants) for each diner.
    """
    agents = list(agent_ids)
    units = list(surface_units)
    zones = list(food_zones)
    a_count = len(agents)
    u_count = len(units)
    z_count = len(zones)
    agent_index = {agent: i for i, agent in enumerate(agents)}
    unit_index = {unit: i for i, unit in enumerate(units)}
    zone_index = {zone: i for i, zone in enumerate(zones)}

    deposit_by_unit: list[list[tuple[int, float]]] = [[] for _ in units]
    deposit_rate_by_agent = [0.0] * a_count
    pickup_by_agent: list[list[tuple[int, float]]] = [[] for _ in agents]
    pickup_rate_by_unit = [0.0] * u_count
    food_deposit_by_zone: list[list[tuple[int, float]]] = [[] for _ in zones]
    food_deposit_rate_by_agent = [0.0] * a_count
    food_dose_by_agent: list[list[tuple[int, float]]] = [[] for _ in agents]

    for (agent, unit), rate in surface_deposit.items():
        if rate <= 0.0 or agent not in agent_index or unit not in unit_index:
            continue
        i = agent_index[agent]
        u = unit_index[unit]
        deposit_by_unit[u].append((i, rate))
        deposit_rate_by_agent[i] += rate
    for (agent, unit), rate in surface_pickup.items():
        if rate <= 0.0 or agent not in agent_index or unit not in unit_index:
            continue
        i = agent_index[agent]
        u = unit_index[unit]
        pickup_by_agent[i].append((u, rate))
        pickup_rate_by_unit[u] += rate
    for (agent, zone), rate in food_deposit.items():
        if rate <= 0.0 or agent not in agent_index or zone not in zone_index:
            continue
        i = agent_index[agent]
        z = zone_index[zone]
        food_deposit_by_zone[z].append((i, rate))
        food_deposit_rate_by_agent[i] += rate
    for (agent, zone), coeff in food_dose_rate.items():
        if coeff <= 0.0 or agent not in agent_index or zone not in zone_index:
            continue
        food_dose_by_agent[agent_index[agent]].append((zone_index[zone], coeff))

    mouth = [max(0.0, float(mouth_rate.get(agent, 0.0))) for agent in agents]
    hand_out = [
        mouth[i] + deposit_rate_by_agent[i] + food_deposit_rate_by_agent[i]
        for i in range(a_count)
    ]
    growth = [float(food_growth_rate.get(zone, 0.0)) for zone in zones]
    removal = [max(0.0, float(food_removal_rate.get(zone, 0.0))) for zone in zones]
    dose_denominator = [
        max(1.0, float(food_dose_denominator.get(zone, 1.0))) for zone in zones
    ]

    mass_count = a_count + u_count + z_count
    mouth_offset = mass_count
    food_offset = mass_count + a_count
    pickup_offset = mass_count + 2 * a_count
    n = mass_count + 3 * a_count
    y = [0.0] * n
    for agent, value in hand0.items():
        if agent in agent_index:
            y[agent_index[agent]] = max(0.0, float(value))
    for unit, value in surface0.items():
        if unit in unit_index:
            y[a_count + unit_index[unit]] = max(0.0, float(value))
    for zone, value in food0.items():
        if zone in zone_index:
            y[a_count + u_count + zone_index[zone]] = max(0.0, float(value))

    def rhs(state: list[float]) -> list[float]:
        deriv = [0.0] * n
        hand = state[:a_count]
        surface = state[a_count:a_count + u_count]
        food = state[a_count + u_count:mass_count]
        for u, edges in enumerate(deposit_by_unit):
            inflow = sum(rate * hand[i] for i, rate in edges)
            outflow = pickup_rate_by_unit[u] * surface[u]
            deriv[a_count + u] = inflow - outflow
        for z, edges in enumerate(food_deposit_by_zone):
            inflow = sum(rate * hand[i] for i, rate in edges)
            net = (growth[z] - removal[z]) * food[z]
            deriv[a_count + u_count + z] = inflow + net
        for i, edges in enumerate(pickup_by_agent):
            inflow = sum(rate * surface[u] for u, rate in edges)
            deriv[i] = inflow - hand_out[i] * hand[i]
            deriv[pickup_offset + i] = inflow
        for i in range(a_count):
            deriv[mouth_offset + i] = mouth[i] * hand[i]
            dose = 0.0
            for z, coeff in food_dose_by_agent[i]:
                dose += coeff * food[z] / dose_denominator[z]
            deriv[food_offset + i] = dose
        return deriv

    steps = max(1, int(steps))
    dt = float(hours) / steps
    for _ in range(steps):
        y = _rk4_step(y, dt, rhs)
        # Mass compartments cannot go negative; dose accumulators are
        # integrals of nonnegative fluxes and are clamped with them.
        for idx in range(n):
            if y[idx] < 0.0:
                y[idx] = 0.0

    hand = {
        agent: max(0.0, y[i]) for agent, i in agent_index.items()
    }
    surface = {
        unit: max(0.0, y[a_count + unit_index[unit]]) for unit in units
    }
    food = {
        zone: max(0.0, y[a_count + u_count + zone_index[zone]]) for zone in zones
    }
    mouth_dose = {
        agent: max(0.0, y[mass_count + i]) for agent, i in agent_index.items()
    }
    food_dose = {
        agent: max(0.0, y[food_offset + i]) for agent, i in agent_index.items()
    }
    pickup_mass = {
        agent: max(0.0, y[pickup_offset + i])
        for agent, i in agent_index.items()
    }
    return FlowResult(
        hand, surface, food, mouth_dose, food_dose, pickup_mass,
    )
