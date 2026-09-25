# covid_plume_dose_assay_v1 — readout

Head commit of record: `2bcdeb7` (merged main the campaign image was built
from). Design: `picard_framework/runs/covid_plume_dose_assay_v1_design.json`
(frozen before any assay cell ran). Ledger: `docs/ledger/PLUME-DOSE-V1.md`.

This is a **complete** readout: all 10 arms × 20 seeds = 200 cells measured
end to end. Nothing below is fitted to 197.

## Execution record

- Platform: AWS Batch EC2 Spot, job definition `picard-covid-boarding-screen`
  **revision 20**, image
  `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign@sha256:aca8d6b81c4ae9cbee54e67a34a0a3ec297fbc9132ad0b79218f01c64f48792f`
  (built from `2bcdeb7`, `Dockerfile` + `deploy/aws/Dockerfile.covid_hull`).
- Canary: array job `09526af1`-preceded submission
  (`24a6733d-8340-4079-afd1-1abf2defc1bf`), size 20, stride 1,
  `INDEX_OFFSET 20` → cell indices 20–39 = arm `D1_dose_0p05`, all 20 seeds.
- Full array: job `09526af1-c234-4398-b95e-d2cd319dbc5c`, size 200, stride 1,
  `INDEX_OFFSET 0` → all 10 arms; canary cells skipped idempotently
  (`_already_complete`).
- Results:
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_plume_dose_assay_v1/2bcdeb7/cells/cells/`
  (200 objects, one per cell).
- All 200 children SUCCEEDED; child failure rate 0% (threshold 5%).
- Local preflight (before submission): `tools/covid_plume_dose_smoke.py` —
  200 cells in declared arm blocks, the `near_field_air` override lands in
  the run spec on all dose arms (engine reads back β 4080 + flushed volume
  4080 on D1), the real `_near_field_droplet_dose` scales exactly 1/β
  (observed ratio 0.05 = expected), each knockout zeroes its activity's
  rates *and* its ring draws, and the pool witness draws zero ring partners.

## §1 Per-arm results (n = 20 seeds each)

Declared replay: Diamond Princess, Θ 4.22e10, index onset_day −1.0,
dwell_weighted sanitary visits, imports 1, infection_age 3.3, seeds
20200205–20200224, full 32-day voyage, `droplet_field_split: partition`.

Audit invariant: `index_onset_day` = −1.0 and `index_shedding_at_day0` = true
on **200/200** cells.

Conditional recorded mass vs the record's 197 (takeoff seeds only,
recorded_onsets ≥ 10):

| arm | takeoff | q05 | median | q95 | contains 197 | before_med |
|-----|--------:|----:|-------:|----:|:------------:|-----------:|
| D0_declared (β 204, ×1.00) | 20/20 | 2,082 | 3,486 | 3,535 | no | 0.954 |
| D1_dose_0p05 (β 4080) | 19/20 | 2,253 | 3,435 | 3,489 | no | 0.936 |
| D2_dose_0p10 (β 2040) | 19/20 | 1,574 | 3,448 | 3,471 | no | 0.932 |
| D3_dose_0p25 (β 816) | 19/20 | 2,772 | 3,462 | 3,507 | no | 0.942 |
| D4_dose_0p50 (β 408) | 19/20 | 2,493 | 3,453 | 3,512 | no | 0.964 |
| K1_dining_off | 20/20 | 2,613 | 3,484 | 3,522 | no | 0.947 |
| K2_work_off | 20/20 | 2,874 | 3,490 | 3,526 | no | 0.954 |
| K3_cabin_corridor_off | 20/20 | 2,512 | 3,492 | 3,537 | no | 0.969 |
| K4_leisure_off | 20/20 | 2,442 | 3,441 | 3,523 | no | 0.943 |
| W_pool_witness (mode off) | 19/20 | 2,418 | 3,517 | 3,546 | no | 0.986 |

Near-target share (recorded_onsets in [98.5, 394]): **0/20 on every arm**.
before_share target band 0.173 ± 0.10: **no arm inside** (all ≥ 0.93).

Per-seed recorded onsets:

| seed | D0 | D1 | D2 | D3 | D4 | K1 | K2 | K3 | K4 | W |
|------|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20200205 | 2469 | 2497 | 2633 | 2561 | 2560 | 2418 | 2518 | 2516 | 2449 | 2195 |
| 20200206 | 3494 | 3456 | 1745 | 3482 | 3509 | 3504 | 3462 | 2435 | 3528 | 3441 |
| 20200207 | 3461 | 2522 | 3292 | 2796 | 3344 | 3419 | 3474 | 3468 | 3429 | 3522 |
| 20200208 | 3084 | 3262 | 3167 | 3158 | 3107 | 3127 | 3169 | 2927 | 3037 | 2794 |
| 20200209 | 3502 | 3488 | 3456 | 3499 | 3500 | 3533 | 3530 | 3523 | 3507 | 3545 |
| 20200210 | 3484 | 2920 | 2634 | 3206 | 1888 | 2623 | 3456 | 3537 | 2665 | 3337 |
| 20200211 | 3519 | 3474 | 3450 | 3485 | 3512 | 3485 | 3506 | 3467 | 3523 | 3498 |
| 20200212 | 3501 | 3435 | 3467 | 3507 | 3499 | 3504 | 3497 | 3526 | 3490 | 3545 |
| 20200213 | 3547 | 3497 | 3469 | 3510 | 3478 | 3521 | 3508 | 3519 | 3507 | 3527 |
| 20200214 | 3488 | 3459 | 3457 | 3450 | 3466 | 3499 | 3492 | 3489 | 3407 | 3431 |
| 20200215 | 3534 | 3412 | 3257 | 3484 | 3460 | 3493 | 3502 | 3545 | 3521 | 3546 |
| 20200216 | 3428 | 3267 | 3215 | 3327 | 3320 | 3251 | 3207 | 3373 | 3411 | 3519 |
| 20200217 | 1968 | 0 | 0 | 0 | 0 | 3001 | 3028 | 3502 | 2301 | 0 |
| 20200218 | 3463 | 3451 | 3450 | 3467 | 3516 | 3514 | 3496 | 3502 | 3374 | 3517 |
| 20200219 | 2849 | 3071 | 3000 | 2934 | 2917 | 2962 | 2893 | 2903 | 2888 | 2443 |
| 20200220 | 3514 | 3475 | 3460 | 3486 | 3501 | 3520 | 3502 | 3522 | 3507 | 3547 |
| 20200221 | 3169 | 3465 | 3489 | 3465 | 3252 | 3193 | 3485 | 3485 | 3496 | 3290 |
| 20200222 | 2088 | 54 | 31 | 3006 | 3426 | 3177 | 3489 | 3239 | 2488 | 3533 |
| 20200223 | 3499 | 3465 | 3448 | 3459 | 3453 | 3491 | 3492 | 3507 | 3495 | 3516 |
| 20200224 | 3493 | 3370 | 3454 | 3462 | 3448 | 3484 | 3526 | 3496 | 3453 | 3518 |

## §2 Frozen response-curve reads

- **dose_binding**: conditional median vs dose multiplier on
  {0.05, 0.10, 0.25, 0.50, 1.00} = {3435, 3448, 3462, 3453, 3486} — flat,
  not monotone; the mass does not respond to a 20× range of per-partner
  plume dose.
- **linearity_elasticity**: log-log slope of conditional median vs
  multiplier over 0.05–1.00 = **0.004** — dose-insensitive at this grid.
- **elbow**: **no dose arm's q05–q95 contains 197**, down to ×0.05. There
  is no dose-only closure scale on the declared grid; the report-immediately
  trigger is recorded as fired-and-negative.
- **collapse_point**: the lowest dose on the grid, 0.05, still clears the
  takeoff gate (19/20 ≥ 5/20). The grid never reaches the dose at which the
  ring stops sustaining takeoff.
- **knockout_table**: zeroing each activity's sampled ring one at a time
  leaves the conditional median at 3,441–3,492 vs D0's 3,486 and takeoff at
  20/20 everywhere — **no single activity's sampled ring carries the mass**;
  no venue class is the binding one.
- **witness_delta**: W_pool_witness median 3,517 vs D0 3,486 (takeoff 19/20
  vs 20/20) — partition and pool are indistinguishable on this metric on
  current main; the partition itself is not the source of the gap.

Tail events (distribution-level, per the declared RNG caveat — rate/dose
scaling reorders draws): seed 20200217 collapses to 0 on **all four dose
arms and the pool witness** while standing at 1,968–3,502 on D0 and the
knockouts — the one seed whose takeoff was dose-marginal through the
near-field route; seed 20200222 collapses to 54/31 on D1/D2 but recovers
to ≥3,006 on D3/D4/W — marginal-takeoff seeds exist, but their outcomes do
not order with dose.

## §3 What the array decides (declared counterfactual)

The design froze this in advance: *if even D1 (dose ×0.05) over-produces,
plume dose concentration is not the binding constraint either — the suspect
moves to the ring's structure beyond per-activity composition (the fixed
cabin-mate/table rings, the seeded index's day-0 exposure geometry) or the
observational channel.*

**That trigger fired, and the knockout table sharpens it.** Neither reach
(PARTNER-RATE-V1: flat at ×0.25 rates), nor per-partner dose (this assay:
flat across ×0.05–×1.00, elasticity 0.004), nor any single activity's
sampled ring (knockouts flat at 20/20 takeoff) carries the ~18× conditional
gap — and the pool witness sitting inside the same band says the partition
architecture itself is not the carrier. The measured implication: the
conditional mass is not borne on the sampled proximity ring at all; what
remains, in the order the counterfactual names, is

1. the ring's **fixed structure** — cabin-mate and meal-table rings that
   persist through every knockout by construction (the declared limit of
   the K-arm grammar);
2. the **seeded index's day-0 exposure geometry** — who is exposed before
   the first threshold trips, independent of the sampled ring;
3. the **observational channel** — dated-onset bookkeeping (the v1
   assay's decomposition already measured ~4.7× over-burn × ~3.5× dated-
   onset bookkeeping; before_share ~0.95 vs the record's 0.173 is
   consistent with most recorded mass being pre-quarantine burn that the
   record never dated as onsets).

Declared design limits honoured: dose arms are mechanism probes, never β
proposals; no constant was moved toward 197; all reads are
distribution-level per the RNG-pairing caveat.
