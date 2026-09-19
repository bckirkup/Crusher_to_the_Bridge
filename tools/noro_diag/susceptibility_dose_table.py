#!/usr/bin/env python3
"""Norovirus dose-response frailty arithmetic, for ledger NORO-SUSCEPT-01.

Purpose
-------
Answer, from the shipped profile alone, three questions that a zero-secondary
voyage raises once protection, dose crediting and route coverage have already
been eliminated as blockers:

1. What susceptibility does a host actually draw, and what dose does that host
   then need for a 50% single-epoch hazard? The engine draws one persistent
   ``Beta(alpha, beta)`` per host (``TransmissionCore._dose_response_suscepti\
bility``) and applies ``1 - exp(-s * D)`` (``_dose_response_hazard``), so the
   population-level beta-Poisson curve is *not* what any individual host sees.
2. What does the shipped curve predict for a given per-host delivered dose?
3. Is an observed whole-run summed naive hazard consistent with an observed
   total credited dose? Under frozen per-host frailty the sum concentrates
   only when the dose does, so the pair (total dose, summed hazard) bounds the
   number of hosts the dose effectively reached. This is the discriminator
   between "correct rare draw" and "dose is reaching the wrong hosts".

Inputs
------
Read from ``data/pathogens/active_profiles.json`` (no overrides, no RNG state
from a run): ``dose_response.alpha`` and ``dose_response.beta`` for the
``--pathogen`` profile id. Optional ``--total-dose`` and ``--hazard-sum``
enable check 3; ``--hosts`` sets the complement used for the per-host mean.

Outputs
-------
Three tables on stdout: susceptibility quantiles with their 50%-hazard doses,
the population beta-Poisson response at a set of doses, and (when the
observed pair is supplied) a Monte Carlo of the summed naive hazard against
the number of hosts sharing the dose. Nothing is written to disk and no
profile value is read back into the engine.

Runtime
-------
Under 10 s (20,000 Monte Carlo replicates per host-count row).

How to read the result
----------------------
Table 1: if the median-host 50%-hazard dose is far *above* the delivered dose
range, the median host is unchallengeable and the frailty distribution is the
suspect. If it sits inside the delivered range, it is not.
Table 3: read off the largest host count whose ``P(sum <= observed)`` is not
negligible. That is the upper bound on how many hosts the credited dose can
have effectively reached. If that bound is far below the number of hosts the
accumulator actually touched, the dose and the hazard are being taken over
different host sets, and no constant is implicated.

No constant in this file is fitted, and nothing here may be used to choose a
parameter value: it reports what the shipped pair implies.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist

PROFILES = Path(__file__).resolve().parents[2] / "data/pathogens/active_profiles.json"
QUANTILES = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999)
HOST_COUNTS = (1, 2, 5, 10, 50, 200, 1910)
REPLICATES = 20_000


def load_dose_response(pathogen_id: str) -> tuple[float, float]:
    """Return the shipped ``(alpha, beta)`` for one pathogen profile."""
    profiles = json.loads(PROFILES.read_text())["pathogens"]
    for profile in profiles:
        if profile.get("pathogen_id") == pathogen_id:
            dose_response = profile["dose_response"]
            return float(dose_response["alpha"]), float(dose_response["beta"])
    raise SystemExit(f"no profile with pathogen_id {pathogen_id!r}")


def quantile_table(alpha: float, beta: float) -> None:
    """Per-host susceptibility quantiles and their 50%-hazard doses."""
    print(f"alpha={alpha}  beta={beta}  mean s={alpha / (alpha + beta):.6e}")
    print("\nquantile |   susceptibility |  dose for 50% host hazard (GEC)")
    for quantile in QUANTILES:
        susceptibility = float(beta_dist.ppf(quantile, alpha, beta))
        print(
            f"{quantile:8.3f} | {susceptibility:16.3e} | "
            f"{math.log(2) / susceptibility:16.3e}",
        )


def population_table(alpha: float, beta: float, doses: list[float]) -> None:
    """Closed-form beta-Poisson response, i.e. the across-host mean."""
    n50 = beta * (2.0 ** (1.0 / alpha) - 1.0)
    print(f"\nclosed-form population N50 = {n50:.4g} GEC")
    print("\n   dose (GEC) | population P(infection)")
    for dose in doses:
        print(f"{dose:13.4g} | {1.0 - (1.0 + dose / beta) ** -alpha:23.4f}")


def concentration_table(
    alpha: float,
    beta: float,
    total_dose: float,
    hazard_sum: float,
    hosts: int,
) -> None:
    """Bound how few hosts the credited dose can have effectively reached."""
    mean_s = alpha / (alpha + beta)
    print(f"\ntotal credited dose {total_dose:.6g} GEC over {hosts} hosts")
    print(f"observed summed naive hazard          {hazard_sum:.6g}")
    print(f"dose-weighted mean susceptibility     {hazard_sum / total_dose:.4e}")
    print(f"shipped mean susceptibility           {mean_s:.4e}")
    print(f"expected summed hazard if dose ind. r {mean_s * total_dose:.4g}")
    print(f"mean per-host dose                    {total_dose / hosts:.4g} GEC")
    rng = np.random.default_rng(8105)
    print("\n hosts sharing dose | median summed hazard | P(sum <= observed)")
    for count in HOST_COUNTS:
        draws = rng.beta(alpha, beta, size=(REPLICATES, count))
        sums = -np.expm1(-draws * (total_dose / count)).sum(axis=1)
        print(
            f"{count:19d} | {float(np.median(sums)):20.4g} | "
            f"{float((sums <= hazard_sum).mean()):18.4f}",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pathogen", default="norwalk_gi")
    parser.add_argument(
        "--doses",
        default="206,1500,15000,17211,49572",
        help="comma-separated doses in GEC for the population table",
    )
    parser.add_argument("--total-dose", type=float, default=None)
    parser.add_argument("--hazard-sum", type=float, default=None)
    parser.add_argument("--hosts", type=int, default=1910)
    args = parser.parse_args()

    alpha, beta = load_dose_response(args.pathogen)
    quantile_table(alpha, beta)
    population_table(alpha, beta, [float(d) for d in args.doses.split(",")])
    if args.total_dose is not None and args.hazard_sum is not None:
        concentration_table(
            alpha, beta, args.total_dose, args.hazard_sum, args.hosts,
        )


if __name__ == "__main__":
    main()
