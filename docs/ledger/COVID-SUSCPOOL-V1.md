# COVID-SUSCPOOL-V1
**Date:** 2026-09-28
**Commit:** 6085e726
**Pathogens:** sars_cov2_resp
**Status:** declared

Declared before any cell ran. Mechanism candidate 3 of the
THETA-SCREEN-V13 residual hunt, shape (a) per the user's pick: a hard
non-susceptible fraction — a per-host zero draw at initialization on the
shipped secretor-negative grammar (`secretor_negative_fraction` +
`secretor_negative_relative_susceptibility: 0.0` on `sars_cov2_resp` via
`pathogen_overrides`). Drawn hosts take susceptibility x0 for this
pathogen: they can neither infect nor shed, which bounds the truth
channel — takeoff seeds currently burn ~94% of 3,711 aboard vs the
serology-informed ~840/~22% (SERO-CHANNEL-V1's ~2x+ truth-overshoot
factor), and this is the only mechanism class that bounds truth without
flattening takeoff (LAMBDA-CROSS-V1 measured hazard-rate scaling can't
close it).

No engine change: `pathogen_overrides` deep-merge onto the profile is a
shipped grammar (SENS-ASSAY-V2 declared the same arms at {0.5, 0.75} on
the stale band and stood down). The sweep {0.25, 0.5, 0.75} is a
declared axis resolving a response curve — the fractions are arm labels,
not adopted constants; nothing is fitted to the 197 record. The f>0 draw
consumes `genetics_rng` per agent (the f=0 baseline short-circuits it),
so armed cells are their own cohort — declared, not an accident.

## Declared

- `picard_framework/runs/covid_susc_pool_v1_design.json` — declared-replay
  clause assay: {1e9 anchor + the five v13 admissible Thetas} x arms
  {declared, f025, f050, f075} x 20 seeds (base 20200205) = 480 cells,
  verbatim v13 stage-2 shape.
- `picard_framework/runs/covid_susc_pool_v1_fleet_design.json` — coarse
  generic-voyage fleet-shape response: five admissible Thetas x same
  arms x 50 seeds (base 20201001) = 1,000 cells. Response check only.

## Frozen criteria

`conditional_trajectory_clause` and `index_geometry` audit invariant
carried verbatim from covid_theta_screen_v13_stage2. Verdict grammar
(frozen in the design): clause outcome class per (theta, fraction);
monotone shape of recorded_onsets vs fraction at fixed Theta (the
mechanism's signature); before_share direction. A clause PASS inside the
sweep triggers a re-screen design on that arm — it is not an adoption.

## Report-immediately-if (carried)

Audit-invariant failure in any cell; every f075 row reporting
insufficient takeoff mass (the mechanism killed takeoff before bounding
it — a geometry finding); clause PASS confined to a boundary endpoint;
non-monotone response in fraction at two consecutive admissible Thetas
(stream-disruption suspicion, not biology); child failures >5%.

## Result

Pending.
