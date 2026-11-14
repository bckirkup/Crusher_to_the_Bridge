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
| 8073 | `carriers_ordered_sub12` | 105 | 61 | 1,936,929 | 70,154,167 | 30,283,267 | 30,123,774 / 118,841 |
| 8038 | `carriers_ordered` | 124 | 63 | 302,233 | 10,931,565 | 6,264,823 | 6,095,209 / 6,733 |
| 8038 | `carriers_ordered_sub2` | 100 | 47 | 400,571 | 23,092,988 | 11,869,687 | 11,716,128 / 13,858 |
| 8038 | `carriers_ordered_sub4` | 97 | 54 | 486,683 | 24,769,603 | 10,916,897 | 10,752,567 / 28,658 |
| 8038 | `carriers_ordered_sub12` | 97 | 61 | 770,283 | 39,314,281 | 15,625,049 | 15,476,026 / 99,049 |

Measured runtime was about 74s for M=1, 74s for sub2, 78-80s for sub4, and
86-100s for sub12 per voyage on this cell. Inferred: fixed-M is not converged
through M=12 on these two seeds. Seed 8038 delivered/dose rise monotonically
from M=1 to sub12, while seed 8073 is non-monotone and ends below M=1 on
delivered/dose; carrier surface calls grow roughly with M while deposit mass
does not follow a stable refinement pattern. Hypothesis: two seeds are a
pilot, not the solver gate; replicated paired posted seeds are required before
choosing DS-M* versus the continuous/event-driven reference.

## Replicated posted-cell DS-M pilot (measured)

Measured at `bbabcf9d` on the same cell/hull/pathogen/epochs, adding posted
seeds 8046, 8047, and 8077 (the next three legacy posted rows by reported
passenger AR after 8073/8038). Each row is again a fresh single-seed witness
process.

Determinism caveat: these rows were generated without a fixed `PYTHONHASHSEED`.
`CS-WINDOW-ORDER-01` later found that common-source meal-token iteration
consumed `_cs_rng` in hash-seed-dependent order when a dining zone had two meal
tokens in one epoch; seed 8038 was confirmed hash-sensitive and the fixed engine
now canonicalizes the order at `07106b7b`. Treat the uncontrolled-hash pilot
rows below as suspect until re-run at or after that fix; they are retained as
the pre-fix pilot record, not as stable paired-seed evidence.

| seed | arm | infected | symptomatic | dose GEC | delivered GEC | deposited GEC | carrier surface GEC / calls |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8046 | `carriers_ordered` | 93 | 44 | 355,616 | 15,710,148 | 8,288,760 | 8,067,270 / 5390 |
| 8046 | `carriers_ordered_sub2` | 110 | 53 | 1,506,132 | 66,839,038 | 30,517,106 | 30,301,317 / 18473 |
| 8046 | `carriers_ordered_sub4` | 105 | 51 | 2,073,157 | 76,223,886 | 36,629,009 | 36,413,060 / 32167 |
| 8046 | `carriers_ordered_sub12` | 106 | 58 | 717,652 | 52,099,676 | 26,463,327 | 26,062,902 / 174971 |
| 8047 | `carriers_ordered` | 76 | 38 | 972,162 | 31,772,698 | 16,602,056 | 16,497,637 / 3054 |
| 8047 | `carriers_ordered_sub2` | 88 | 46 | 415,221 | 18,117,819 | 11,818,652 | 10,419,990 / 11879 |
| 8047 | `carriers_ordered_sub4` | 72 | 35 | 2,188,529 | 80,239,875 | 34,749,035 | 34,634,302 / 28866 |
| 8047 | `carriers_ordered_sub12` | 77 | 41 | 227,401 | 11,659,924 | 8,141,003 | 8,001,865 / 82735 |
| 8077 | `carriers_ordered` | 88 | 42 | 1,252,237 | 46,361,762 | 20,554,374 | 20,417,330 / 8411 |
| 8077 | `carriers_ordered_sub2` | 73 | 32 | 167,313 | 9,850,040 | 5,895,804 | 5,820,923 / 15690 |
| 8077 | `carriers_ordered_sub4` | 65 | 31 | 127,934 | 8,123,406 | 4,109,881 | 3,895,931 / 31216 |
| 8077 | `carriers_ordered_sub12` | 87 | 40 | 352,030 | 27,218,796 | 14,824,379 | 14,193,885 / 241934 |

Ratio check vs M=1 (delivered / dose / deposited): seed 8038 M12 is
3.60x/2.55x/2.49x, seed 8046 M12 is 3.32x/2.02x/3.19x, seed 8047 M12 is
0.37x/0.23x/0.49x, seed 8073 M12 is 0.89x/0.91x/0.84x, and seed 8077 M12 is
0.59x/0.28x/0.72x. M=2/4/12 are non-monotone within seeds and inconsistent
across seeds; carrier surface calls reach ~82k-242k at M=12.

Inferred: fixed-M is not converged through M=12 on five posted seeds; the
substeps change the stochastic realization enough that deposited/delivered
mass and dose do not refine toward M=1 or a stable limit. Hypothesis: the next
solver branch should be the continuous/event-driven contamination reference or
a redesigned stochastic substep rule; a larger fixed M is not yet justified by
these data. Runtime stayed ~57-100s per voyage, so runtime is not the current
blocker.

The uncontrolled-hash ratio check above is superseded for paired DS-M
comparisons by `NORO-HAND-CASCADE-01-SUBSTEPS-FIXED`, measured after
`CS-WINDOW-ORDER-01`.
