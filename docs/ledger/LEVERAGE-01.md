# LEVERAGE-01
**Date:** 2026-09-26
**Commit:** fbad8738
**Pathogens:** norwalk_gi, sars_cov2_resp
**Status:** measured
**Measured at:** fbad8738

## Contract and method

The `docs/sourcing_protocol.md` §3 pass: one-at-a-time endpoint perturbation
across each register row's declared interval, scored through the two live
channels. **L2** = an endpoint flips an anchor verdict; **L1** = an endpoint
moves an anchor measurably without flipping; **L0** = no detectable movement
in any scored output across the whole interval.

Frozen design: `picard_framework/runs/leverage01_design.json` (66 axes over
56 register rows; endpoint realizations and transforms recorded there).
Driver: `picard_framework/leverage_screen.py`; Batch worker:
`deploy/aws/leverage01_entrypoint.py`.

- **Noro channel**: isolated `norwalk_gi` on `classic_cruise_1900` (1910
  agents, 168 epochs, renewal boarding), paired seeds **8105/8106**, scored by
  `telemetry_buffer/observation_model/score_anchors.py` (A1/A2/A5/A8/A9,
  era `pre`).
- **Covid channel**: `covid_theta_fit` hull scenarios at the shipped
  `covid_first_look_v6` fit (Theta = 3.16e11, cabin_compartment, airflow
  pool): Diamond Princess seeds 20200205/06, Greg Mortimer 20200315/16,
  scored on H1/H2 hit-miss and H3 cross-hull placement.
- **Noise gate**: a scored quantity moves only if both seeds shift in the
  same direction and the mean shift exceeds the baseline seed-pair spread;
  a zero-spread baseline requires any same-sign nonzero shift.
- **Shared rows**: a register row covered by several axes takes the maximum
  level over its axes (route multipliers, symptom vector).
- Perturbation was override-only (config_overrides / pathogen_overrides);
  no model or constant was changed. One realization caveat: row 274's
  declared interval is the shipped incubation truncation window itself, and
  the engine requires `min < median < max` strictly, so the endpoint-side
  truncation bound was relaxed by 1e-9 relative to admit the endpoint
  median (found by canary; recorded in the design file).

## Campaign record

AWS Batch account 994254241749, queue `picard-campaign-queue`, bucket
prefix `s3://crusherbucket-994254241749-us-east-1-an/campaign/leverage01/`.
346 cells (198 noro + 148 covid). Canary: one noro row end-to-end on
jobdef `picard-leverage01:2` (image digest
`sha256:4173548dbe3736dcf46f927e29714e9421f5e9776c13ed282534541e3daae441`)
— override landed in the engine (`resolved_witness` = 0.1 for the
incubation-median endpoint) and the record is scorer-conformant.
Main array `d57dbe0b-4cce-4832-8c5e-762699ee9027` on jobdef rev 3: 306/346
succeeded; 40 cells on int-valued endpoints failed on a filename-formatting
defect in the worker (expected `5`, driver wrote `5.0` — the sim itself ran
to completion each attempt). Fixed in the worker and resubmitted as 40
single jobs on `picard-leverage01:4` (image digest
`sha256:216ce7391bc040c3cead75959c22e818df36d2df28fd1db577196c04c93450ff`)
— all 40 landed. All 346 records uploaded; every endpoint perturbation's
`resolved_witness` confirms the override reached the engine.

## Results — per-row endpoint outcomes

| Axis | Register row(s) | Lev | Endpoint outcomes |
|---|---|---|---|
| cov_theta | 383 | **L2** | 1e4 flips H3, moves DP+GM positive share; 1e9 flips H3, moves GM share |
| noro_illness_duration | 284 | **L1** | 13 d moves A1 ever-ill + reported-case rate; 1 d no move |
| noro_import_prevalence | 296 | **L1** | 0.0164 moves A1 + infection + reported rates; 0.0014 no move |
| noro_never_symptomatic | 341 | **L1** | 0.68 moves infection attack rate; 0.22/0.36/0.59 no move |
| all 62 remaining axes | — | **L0** | no detectable movement at either endpoint on any scored output |

The 62 L0 axes include every route-efficiency multiplier on both arms
(`route_efficiency_multipliers.*` swept over [0, 1] — including 0, which
zeroes the route), all covid profile axes except Theta, the noro dose alpha
interval [0.072, 0.161], both HVAC/blackwater/sanitary config axes, and the
emesis titre pair. `resolved_witness` confirms the overrides resolved —
the L0 is a measured absence of scored movement, not a dead override. In
particular `noro_route_direct_contact` at 0.0/1.0/baseline produced
identical ever-ill, infection and peak figures on both seeds: on the
exercised cell, direct contact carries no measurable load at any point of
its interval.

`cov_theta` is the only L2. It is the register's one fitted row (class F,
interval = the declared fit grid) — a fit axis flipping the cross-hull
placement at its grid edges is the expected calibration sensitivity, and
the "declared-basis row reads L2" report trigger does not fire. Both
endpoints flip **H3** only; H1/H2 hit/miss status is unchanged.

## Override-blocked rows (module constants with no override path; Lev left `L?`)

- 313 `EMESIS_DETECTABLE_MIN_EPISODES` — module constant, transmission_core
- 314 `EMESIS_SINGLE_EPISODE_FRACTION` — module constant
- 319/320 `SURFACE_TO_HAND` / `HAND_TO_SURFACE` transfer fractions — module constants; no declared interval either
- 327/328 `HAND_TO_FOOD_TRANSFER_FRACTION_RANGE` — module constant
- 332 `ENV_DELIVERY_FRACTION_PER_DAY` / `ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION` — module constants
- 333 `DROPLET_AEROSOL_FRACTION` — module constant; emesis_conditioned mode also gates the droplet share to 0 on this arm
- 349 `SANITARY_FLOOR_AREA_M2_PER_WC` — module constant
- 351 `SANITARY_CEILING_HEIGHT_M` — module constant; bound is one-sided
- 352 `SANITARY_EXHAUST_M3H_PER_WC` — module constant
- 353/354 sanitary dwell/voids — module constants; shipped `sanitary_visit_mode` is `none`
- 355 `SURFACE_CONTACTS_PER_HOUR[sanitary]` — module constant dict
- 356–358 swab recovery/LOD/nominal efficiency — TargetedSurfaceSwab built with module defaults, no wiring
- 362 `FLUSH_VOLUME_L` — constructor default; the blackwater override covers other fields only
- 364–367 WW assay LOD/LOQ/volumes/recovery/inhibition — WastewaterHoldingTankAssay built with module defaults, no wiring

22 register rows, ~17% of the `L?` population — below the report threshold.

## Not-rankable rows (no scored channel or no endpoints; Lev left `L?` — not L0)

- 277 illness_probability eta/gamma — declared interval unbounded, no endpoints
- 280/281 withdrawn quantity + provenance note
- 286 curve-selection defect note — not a quantity
- 293/396 immunocompromised_multiplier — removed from the tree on both arms
- 297/298 mode rows — no interval
- 304/305 NPI reference multipliers and removal_log10 — no shipped measure / inert act channel
- 309/318/334/359 pre-marked dash rows — non-quantities or refused mechanisms
- 315–317 retired emesis draws — blank interval
- 322 hand-load pair — joint with row 287, no separate interval
- 323 cabin-localization f — structural ceiling, not a parameter
- 324–326 observation-model numbers / voyage denominator / boarding prevalence — no declared intervals (prevalence is ranked through the renewal row 296)
- 335/336/338/339/342/348 absent or refused mechanisms
- 337 hand-hygiene reachability bound — not a constant
- 380 covid shedding magnitude — occupied by Theta (ranked through cov_theta)
- 381 covid dose alpha/beta — enters only through the Theta map
- 382 copies-per-infectious-unit — inside the Theta composite
- 384 asymptomatic_shedding — declared equal to symptomatic, no independent quantity
- 386/388/392/393 severity fraction / PCR sensitivity / airborne_emission_fraction / secretor+innate — absent or form-only on this arm
- 389 testing-campaign records — history, not a parameter
- 394 base_susceptibility — no declared interval
- 440–455 influenza_a, all rows — the influenza arm has no scored anchor; not-rankable is not L0

## Report-trigger check

- Declared-basis L2: none (the only L2 is the fitted Theta row).
- Seed-pair spread vs anchor margin: no endpoint outcome was
  noise-dominated — every reported move exceeded the paired-seed spread.
- Override-blocked share: 22/127 ≈ 17% — below the ~1/3 trigger.
- Movement through a dead/withdrawn channel: none.
