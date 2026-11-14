# NORO-HAND-CASCADE-01-POSTED
**Date:** 2026-11-10
**Commit:** f664e368
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** f664e368

Posted-conditioned witness for the default-off arms landed in
`NORO-HAND-CASCADE-01` (`transmission.hand_redeposit_mode=carriers`,
`transmission.intra_epoch_causal_order=ordered`). The earlier expedition
smoke seeds were below the VSP scale, so this entry selects legacy posted
voyages from the delivered `noro_provisioned_sensitivity_01` scan rows and
asks whether the arms make those large events larger.

## Design

Cell: `fl_exp_12d_sens_p06_paxv`, `expedition_cruise_450`, `norwalk_gi`,
288 epochs, passenger-venue provisioned source. Seeds 8073 and 8038 were the
two largest legacy posted rows in that tier (legacy reported passenger AR
0.1646 / 0.1456, ever-ill passenger 0.212 / 0.193; routes dominated by
`common_source_food` with a fomite minority). Specs were materialized with
`campaign_runner.generate_tier_runs` and run through
`tools/noro_diag/hand_cascade_witness.py`, which instruments carrier hand
deposits without changing the legacy RNG path. Arms: `legacy`, `carriers`,
`ordered`, `carriers_ordered`.

## Measured

| seed | arm | infected | symptomatic | dose GEC | delivered GEC | deposited GEC | carrier surface GEC / calls |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8073 | legacy | 105 | 58 | 461,806 | 23,604,864 | 173,930 | 0 / 0 |
| 8073 | carriers | 127 | 71 | 1,377,910 | 39,840,940 | 6,726,414 | 6,431,681 / 7,931 |
| 8073 | ordered | 117 | 64 | 785,458 | 24,512,070 | 315,840 | 0 / 0 |
| 8073 | carriers_ordered | 111 | 70 | 2,133,213 | 78,818,438 | 35,936,284 | 35,675,036 / 8,379 |
| 8038 | legacy | 110 | 53 | 203,185 | 8,956,382 | 163,702 | 0 / 0 |
| 8038 | carriers | 104 | 54 | 1,866,323 | 81,408,455 | 9,197,573 | 9,039,664 / 4,354 |
| 8038 | ordered | 113 | 66 | 446,502 | 19,635,408 | 182,641 | 0 / 0 |
| 8038 | carriers_ordered | 124 | 63 | 302,233 | 10,931,565 | 6,264,823 | 6,095,209 / 6,733 |

Determinism caveat: these witness rows predate `CS-WINDOW-ORDER-01`. Common-source
meal-token order could consume `_cs_rng` in `PYTHONHASHSEED`-dependent order, and
the fixed engine changes at least the seed-8073 `carriers_ordered` M=1 row;
treat the table as the pre-fix witness record, not stable paired-seed evidence.
See `NORO-HAND-CASCADE-01-SUBSTEPS-FIXED` for the fixed-engine DS-M re-pilot.

## Reading

Measured: on both posted seeds, `carriers_ordered` exceeds legacy on
infected, symptomatic, dose, delivered mass, and deposited mass.
`ordered` alone also exceeds legacy on all four size measures on both
seeds. `carriers` alone is mixed on infected count (8073 +22, 8038 -6) but
large on symptomatic/dose/delivered/deposited mass.

Inferred: the earlier small-seed null was a target miss, not a mechanism
null. Once a voyage is already large enough to create whole-copy carrier
hands, opening the carrier dead-end moves material mass: carrier surface
deposits reach 6.1M-35.7M GEC, versus zero under legacy, and the combined
arm enlarges the posted event on every measured size axis.

Hypothesis: this supports the intra-epoch carrier/ordering repair as a
contributor to VSP-scale events. It is not yet an anchor result: this
harness does not recompute role-specific reported attack rates or the VSP
posting crossing, and two seeds from one cell are a gate, not an effect
size.

Limits and next evidence: paired-seed replication across more posted
seeds/hulls, role-AR/VSP accounting, and a hand-load/mass-conservation
audit are required before any default flip. The carriers arm is not
stream-neutral (carrier `_replenish_hand` skips shedder-practice draws),
so infected-count attribution is noisier than the mass/deposited witnesses.
Max observed carrier hand loads were ~2.1M-6.3M GEC, large enough that
the hand reservoir and residue floors need an explicit audit before
substeps or a continuous integrator are designed.
