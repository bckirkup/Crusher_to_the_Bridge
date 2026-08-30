"""Does exponential pre-establishment clearance break dose additivity?

Model under test (Edison formal_spec_v2 acceptance-test form, PEC-03):
    R(t)   retained viable inoculum, decaying at lambda per day
    hazard = r_rate * R(t)  dt
    r ~ Beta(alpha, beta) persistent per host

Calibration requirement: a single bolus D, integrated to t -> infinity, must
reproduce the beta-frailty single-hit response 1 - exp(-r D), otherwise lambda
silently rescales all infectivity.  Total hazard from a bolus is r_rate * D /
lambda, so r_rate = r * lambda.

Question 1: with that calibration, does splitting a fixed total dose into n
increments change infection risk?
Question 2: what does it do to the retained inoculum at establishment, which is
what conditions the illness draw (A2)?
"""

from __future__ import annotations

import math

import numpy as np

ALPHA = 0.111
BETA = 32.81
ETA = 0.508
GAMMA = 0.095
HOURS_PER_DAY = 24.0


def illness_probability(dose: float) -> float:
    """P(ill | infected) for the acquired inoculum."""
    if dose <= 0.0:
        return 0.0
    return min(1.0, 1.0 - math.pow(1.0 + ETA * dose, -GAMMA))


def simulate(
    total_dose: float,
    n_increments: int,
    lam_per_day: float,
    horizon_days: float,
    population: int,
    seed: int,
    epoch_hours: float = 1.0,
    exposure_days: float = 5.0,
) -> tuple[float, float]:
    """Return (infection fraction, mean P(ill) among the infected).

    Dose is delivered as `n_increments` equal boluses, evenly spaced over the
    first `exposure_days`, then the host is followed to `horizon_days` with no
    further exposure.  lambda = 0 uses the additive limit hazard r * R * dt,
    which is the uncalibrated case shown for contrast.
    """
    rng = np.random.default_rng(seed)
    r = rng.beta(ALPHA, BETA, size=population)
    dt = epoch_hours / HOURS_PER_DAY
    phi = math.exp(-lam_per_day * dt)

    n_epochs = int(round(horizon_days / dt))
    exposure_epochs = max(1, int(round(exposure_days / dt)))
    dose_epochs: dict[int, float] = {}
    for k in range(n_increments):
        epoch = min(
            exposure_epochs - 1,
            int(k * exposure_epochs / n_increments),
        )
        dose_epochs[epoch] = dose_epochs.get(epoch, 0.0) + total_dose / n_increments

    retained = np.zeros(population)
    infected = np.zeros(population, dtype=bool)
    acquired = np.zeros(population)

    for epoch in range(n_epochs):
        retained += dose_epochs.get(epoch, 0.0)
        if lam_per_day > 0.0:
            # calibrated: r_rate = r * lambda  =>  H = r * R_plus * (1 - phi)
            hazard = r * retained * (1.0 - phi)
        else:
            hazard = r * retained * dt
        draw = rng.random(population) < -np.expm1(-hazard)
        newly = draw & ~infected
        acquired[newly] = retained[newly]
        infected |= newly
        retained[infected] = 0.0
        retained *= phi

    ill = np.array([illness_probability(d) for d in acquired[infected]])
    return infected.mean(), float(ill.mean()) if ill.size else 0.0


def main() -> None:
    total = 1000.0
    horizon = 7.0
    pop = 40_000
    print(f"total dose {total:g}, horizon {horizon:g} d, exposure 5 d, N={pop}")
    print(f"closed-form additive target: {1.0 - (1.0 + total / BETA) ** -ALPHA:.4f}")
    print()
    header = f"{'lambda/day':>10} {'n':>5} {'inf AR':>8} {'ill|inf':>8}"
    print(header)
    for lam in (0.0, 0.5, 2.0, 12.0):
        for n in (1, 24, 168):
            ar, ill = simulate(total, n, lam, horizon, pop, seed=4200 + n)
            print(f"{lam:>10g} {n:>5d} {ar:>8.4f} {ill:>8.4f}")
        print()


if __name__ == "__main__":
    main()
