# NORO-HAND-CASCADE-01-SUBSTEPS
**Date:** 2026-11-12
**Commit:** bbabcf9d
**Pathogens:** all
**Status:** open
**Measured at:** bbabcf9d

Second stage of the hand/fomite cascade repair: the fixed-step arm for the
solver gate proposed in `docs/proposals/noro_hand_cascade_solver_gate.md`.
This entry records the landed mechanism, not a campaign result. No anchor was
fitted and no VSP/Park/attack-rate target was used to choose a constant.

## Landed mechanism (default-off arm)

`transmission.intra_epoch_substeps` defaults to `1`, which keeps the ordered
M=1 call sequence. `M > 1` requires `transmission.intra_epoch_causal_order =
"ordered"` and supports pooled fomite with `sanitary_visit_mode =
"dwell_weighted"`; the `per_surface` fomite arm still raises `ValueError` at
`TransmissionCore` construction.

For `M > 1`, the engine repeats the hand-mediated contamination cycle `M`
times per epoch: hand maintenance, dwell-weighted sanitary deposit/pickup,
emesis-patch pickup, surface deposits/pickups, food-pool hand
deposits/growth/ingestion, and per-substep hand hygiene. The sanitary visit
schedule is drawn once per epoch; each substep exposes that schedule with the
same epoch-fixed dwell share while contact counts use the shorter substep
clock, and a stool-event venue is exposed once per epoch on the first substep
after `_replenish_hand` records it. Emesis and isolated-quarter deposits,
aerosol/common-source/environmental/caregiver routes, and the epoch-boundary
infection challenge stay outside the loop. Substep duration is derived as
`SimClock.hours_per_epoch / M`; per-hour contact rates are exercised through
the same kernels at the shorter clock, and count-like rates use the existing
`SimClock.probability_per_epoch` / decay conversions rather than a hard-coded
"10-minute" assumption.

The witness harness gains `carriers_ordered_sub2`, `carriers_ordered_sub4`,
and `carriers_ordered_sub12` arms, and its mode key now carries `m<M>` so
substep rows do not collapse into the M=1 rows.

## Scope limits

- This is the DS-M arm only. The continuous/event-driven reference and the
  convergence decision are still open in the solver-gate proposal.
- The per-surface fomite arm is still rejected for `M > 1`; sanitary visits
  are now inside the loop with an epoch-fixed visit schedule.
- `M > 1` is not stream-neutral with `M = 1`: it repeats hand-hygiene and
  contact draws per substep by design, so paired-seed attribution must treat
  it as a different stochastic realization, not a pure refinement.
- Infection-serial transmission still cannot chain inside an epoch; challenge
  resolution remains once per epoch after all pathogen pathways.

## Posted-cell DS-M pilot (measured)

Measured at `bbabcf9d` on `fl_exp_12d_sens_p06_paxv`
(`expedition_cruise_450`, `norwalk_gi`, 288 epochs), posted seeds 8073 and
8038. Each row is a fresh single-seed witness process; a multi-seed run in one
process produced M=1 rows that did not reproduce the posted-gate artifacts, so
it was discarded as harness/run-order contamination rather than an engine move.

| seed | arm | infected | symptomatic | dose GEC | delivered GEC | deposited GEC | carrier surface GEC / calls |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8073 | `carriers_ordered` | 111 | 70 | 2,133,213 | 78,818,438 | 35,936,284 | 35,675,036 / 8,379 |
| 8073 | `carriers_ordered_sub2` | 103 | 63 | 2,963,373 | 126,174,772 | 55,330,072 | 55,131,556 / 15,041 |
| 8073 | `carriers_ordered_sub4` | 104 | 59 | 1,476,907 | 72,284,787 | 30,169,618 | 29,936,058 / 46,017 |
| 8038 | `carriers_ordered` | 124 | 63 | 302,233 | 10,931,565 | 6,264,823 | 6,095,209 / 6,733 |
| 8038 | `carriers_ordered_sub2` | 100 | 47 | 400,571 | 23,092,988 | 11,869,687 | 11,716,128 / 13,858 |
| 8038 | `carriers_ordered_sub4` | 97 | 54 | 486,683 | 24,769,603 | 10,916,897 | 10,752,567 / 28,658 |

Measured runtime was about 74s for M=1, 74s for sub2, and 78-80s for sub4 per
voyage on this cell. Inferred: fixed-M is not converged by M=4 on these two
seeds; seed 8073 peaks at sub2 then falls below M=1 at sub4, while seed 8038
rises from M=1 to sub2/sub4. Carrier surface calls grow with M while deposit
mass is non-monotone, so this is resolution/stochastic sensitivity rather than
a smooth refinement. Hypothesis: two seeds are a pilot, not the solver gate;
replicated paired posted seeds and sub12 are required before choosing DS-M*
versus the continuous/event-driven reference.
