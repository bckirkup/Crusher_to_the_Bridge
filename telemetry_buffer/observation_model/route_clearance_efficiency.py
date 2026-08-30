"""What route-specific pre-establishment clearance actually does to infectivity.

A single pathogen-wide lambda cannot change infection risk: the accumulated
hazard stays linear in total delivered dose (see
`clearance_additivity_findings.md`).  Route-*varying* lambda is a different
object.  Under the retained-pool hazard with a per-route pool decaying at
lambda_j, a delivery D_j accrues total hazard

    integral_0^inf  r_rate * D_j * exp(-lambda_j * t) dt  =  r_rate * D_j / lambda_j

so per-virion infectivity is proportional to 1 / lambda_j.  Clearance therefore
supplies the route efficiency multiplier as a derived quantity rather than an
assumed one, and the mean residence time 1 / lambda_j is what converts a rate
into a survival fraction -- no separate portal residence time is needed.

Calibration: the beta-Poisson constants alpha = 0.111, beta = 32.81 were fitted
to *administered oral* Norwalk inoculum, so every loss between mouth and gut
epithelium is already inside r.  The oral route is therefore the reference:
r_rate = r * lambda_food, which makes route j's effective dose

    D_j * lambda_food / lambda_j

and leaves a pure-oral exposure reproducing Teunis exactly.

This script checks that closed form against simulation and reports what the
Edison v2 norovirus rates do to a route mix.
"""

from __future__ import annotations

import math

import numpy as np

ALPHA = 0.111
BETA = 32.81
ETA = 0.508
GAMMA = 0.095
HOURS_PER_DAY = 24.0

# Edison pre_establishment_clearance_params_v2.json, norovirus_gii4, per hour.
LAMBDA_PER_HOUR = {
    "food": 0.05,
    "direct_contact": 0.1,
    "fomite": 0.1,
    "droplet": 0.7,
    "hvac_airborne": 0.7,
}
REFERENCE_ROUTE = "food"


def illness_probability(dose: float) -> float:
    """P(ill | infected) for the acquired inoculum."""
    if dose <= 0.0:
        return 0.0
    return min(1.0, 1.0 - math.pow(1.0 + ETA * dose, -GAMMA))


def route_efficiency(lam_per_hour: dict[str, float]) -> dict[str, float]:
    """Per-virion infectivity relative to the oral reference route."""
    reference = lam_per_hour[REFERENCE_ROUTE]
    return {
        route: reference / lam for route, lam in lam_per_hour.items()
    }


def simulate(
    route_doses: dict[str, float],
    lam_per_hour: dict[str, float],
    n_increments: int,
    horizon_days: float,
    population: int,
    seed: int,
    epoch_hours: float = 1.0,
    exposure_days: float = 5.0,
) -> tuple[float, float]:
    """Return (infection fraction, mean P(ill) among the infected).

    Each route keeps its own retained pool decaying at its own lambda; the
    hazard is the sum over routes of r_rate * R_j, with r_rate calibrated on
    the oral reference so a pure-food exposure reproduces the fitted response.
    """
    rng = np.random.default_rng(seed)
    r = rng.beta(ALPHA, BETA, size=population)
    r_rate = r * lam_per_hour[REFERENCE_ROUTE]

    dt_hours = epoch_hours
    n_epochs = int(round(horizon_days * HOURS_PER_DAY / dt_hours))
    exposure_epochs = max(1, int(round(exposure_days * HOURS_PER_DAY / dt_hours)))

    schedule: dict[int, float] = {}
    for k in range(n_increments):
        epoch = min(exposure_epochs - 1, int(k * exposure_epochs / n_increments))
        schedule[epoch] = schedule.get(epoch, 0.0) + 1.0 / n_increments

    retained = {route: np.zeros(population) for route in route_doses}
    phi = {
        route: math.exp(-lam_per_hour[route] * dt_hours) for route in route_doses
    }
    infected = np.zeros(population, dtype=bool)
    acquired = np.zeros(population)

    for epoch in range(n_epochs):
        share = schedule.get(epoch, 0.0)
        hazard = np.zeros(population)
        for route, total in route_doses.items():
            retained[route] += total * share
            # exact within-step integral of r_rate * R_j * exp(-lambda_j * s)
            hazard += (
                r_rate
                * retained[route]
                * (1.0 - phi[route])
                / lam_per_hour[route]
            )
            retained[route] *= phi[route]
        newly = (~infected) & (rng.random(population) < 1.0 - np.exp(-hazard))
        if newly.any():
            # illness conditions on the retained pool that drove the draw
            pool = sum(retained[route] for route in route_doses)
            acquired[newly] = pool[newly]
            infected |= newly

    if not infected.any():
        return 0.0, 0.0
    ill = np.array([illness_probability(d) for d in acquired[infected]])
    return float(infected.mean()), float(ill.mean())


def closed_form_infection(
    route_doses: dict[str, float],
    lam_per_hour: dict[str, float],
) -> float:
    """Beta-frailty response on the effective (efficiency-weighted) dose."""
    efficiency = route_efficiency(lam_per_hour)
    effective = sum(dose * efficiency[route] for route, dose in route_doses.items())
    return 1.0 - math.pow(1.0 + effective / BETA, -ALPHA)


def main() -> None:
    population = 40_000
    horizon_days = 7.0
    total = 1000.0

    print("Per-virion efficiency relative to the oral reference")
    for route, eff in route_efficiency(LAMBDA_PER_HOUR).items():
        print(f"  {route:<16} lambda={LAMBDA_PER_HOUR[route]:.2f}/h  eff={eff:.4f}")

    # Measured establishment composition is droplet-dominated (94-95%); the
    # emission weights are not the same object, so both are shown.
    mixes = {
        "pure food (reference)": {"food": total},
        "pure droplet": {"droplet": total},
        "emission weights": {
            "direct_contact": 0.35 * total,
            "fomite": 0.30 * total,
            "food": 0.20 * total,
            "droplet": 0.10 * total,
            "hvac_airborne": 0.05 * total,
        },
        "droplet-dominated (as measured)": {
            "droplet": 0.94 * total,
            "direct_contact": 0.03 * total,
            "fomite": 0.02 * total,
            "food": 0.01 * total,
        },
    }

    print(f"\ntotal dose {total:.0f}, {horizon_days:.0f}-day horizon, N={population}")
    header = f"{'mix':<32}{'n':>5}{'sim AR':>10}{'closed':>10}{'ill/inf':>10}"
    print(header)
    for name, mix in mixes.items():
        predicted = closed_form_infection(mix, LAMBDA_PER_HOUR)
        for n_increments in (1, 24, 168):
            attack, ill = simulate(
                mix,
                LAMBDA_PER_HOUR,
                n_increments,
                horizon_days,
                population,
                seed=20260829,
            )
            print(
                f"{name if n_increments == 1 else '':<32}"
                f"{n_increments:>5}{attack:>10.4f}{predicted:>10.4f}{ill:>10.4f}",
            )


if __name__ == "__main__":
    main()
