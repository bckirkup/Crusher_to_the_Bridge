# SERO-CHANNEL-V1
**Date:** 2026-09-26
**Commit:** 03a9db9e
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 03a9db9e

Measured extent: canary (20 seeds, cells 340-359 of the 20-seed
revision) and the FULL 1,080-cell surface (60 seeds, array
ee429652-09f3-41fc-aa77-78f040b989b5, image digest 5caf8ef on code
03a9db9e — post-merge main + the 60-seed design revision). (The canary's
Batch image was built from 8ac510b3, the pre-rebase SHA whose code is
identical to the branch tip.)

The observational-channel arm of the ~18x conditional-size hunt, declared
in `picard_framework/runs/covid_sero_channel_v1_design.json` before any
cell ran. SENS-ASSAY-V1 measured the gap unreachable inside the
transmission layer (~4.7x over-burn x ~3.5x dated-onset bookkeeping);
this screen replays the LAMBDA-CROSS-V1 theta axis {1.0 ... 0.001} x
4.22e10 under two onset-recording channels — declared (every confirmed
symptomatic onset dated) and period (onset dated only if the host had
presented on or before the epoch of its confirming specimen, times a
once-per-case recall draw at 0.56, record-derivable as 197/712 / ~0.49
symptomatic-at-specimen) — x the same 20 seeds, 360 cells. The new
anchor, covid.H5 (serology-informed true infections ~840, admissible
band [712, 960] after Hung et al. 2020), is held out forever and scored
per row on `infections_total`, conditional on takeoff — never fitted
against.

The channel is additive and default-off (`observation_model.onset_recording`
on the pathogen profile, reached through the existing `pathogen_overrides`
deep-merge): absent the block, no code path changes and no RNG stream is
touched — onset draws run on a dedicated stream derived from the parent
SeedSequence entropy, so molecular and parent draws are structurally
unperturbed and the declared arm is expected bit-identical to pre-change
main. Validation gate on the PR: paired declared-vs-main payload equality
at matched seed on the new image, spec-lands read-back of the period
block, unit tests for the gate/draw/stream isolation.

Canary (per the bounded-research rule): the period arm at theta x0.001
only, cells 340-359, 20 seeds. If the gate lands dating
far from ~0.28 of confirmed the declared fallback is the recall draw
alone without the symptomatic-at-specimen gate — declared before the
array, never after.

## Canary read-out (measured, 2026-09-26)

Batch array `f340c7b9-1dd0-451c-b76d-3ec65ee46ac5`
(`picard-sero-channel-v1-canary`), job-def `picard-covid-boarding-screen:23`,
image digest `3bff283`, cells 340-359 (P1_period, theta 4.22e7, seeds
20200205-20200224), payloads under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_sero_channel_v1/8ac510b3/cells/`.
20/20 SUCCEEDED.

- **Takeoff share 7/20** (recorded_onsets >= 10): seeds 20200205, 06, 08,
  10, 14, 18, 19. The remaining 13 seeds burned out at infections_total
  0-3 — consistent with the lambda-cross bimodal extinction at deep theta.
- **Serology clause (scorable, >= 5 takeoff seeds): not satisfied.**
  Takeoff-seed infections_total q05-q95 [753, 3025] intersects the band
  [712, 960], but the median (1,025) sits above it. Truth overshoot
  persists at theta x0.001 even conditioned on takeoff.
- **Trajectory clause: not satisfied.** Takeoff-seed recorded_onsets
  q05-q95 [161, 1536] contains 197 (median 315); takeoff-seed median
  before_share 0.020, outside 0.10 of the record's 0.173 — the two
  early-burn seeds (20200205: 0.583, 20200208: 0.442) do not carry the
  median.
- **Channel read — dating share: ~0.43-0.53 of lab-confirmed** on the
  four dense takeoff seeds, vs the record's 197/712 = 0.277. The gate
  does not undershoot — it lands the dated share well ABOVE the record's,
  so the declared fallback (recall alone, no gate) is not engaged.
  Structural reason the share exceeds the declared ~0.49 x 0.56: hosts
  confirmed while already symptomatic pass the gate at ~0.85-0.95, and
  never-symptomatic confirmed hosts sit in the denominator.
- **asymptomatic_at_specimen: 0.23-0.44 of campaign positives** on
  takeoff seeds, vs the record's ~0.51 — the sim swabs symptomatic
  hosts more often than the record did.
- **Seed 20200205 zero-asymptomatics anomaly (ROUTE-ATTR-V1): resolved
  here** — 110 asymptomatic of 248 campaign positives.
- Every payload carries `onset_recording` =
  {symptomatic_at_confirmation_required: true, report_probability: 0.56}
  and `lab_confirmed_total` — the channel read-back is auditable per
  cell.

Inference from the canary (superseded by the array read-out below): the
~0.5 dating share vs the record's 0.28.

## Full-array read-out (measured, 2026-09-26)

Array `ee429652-09f3-41fc-aa77-78f040b989b5`
(`picard-sero-channel-v1-full-60`), job-def
`picard-covid-boarding-screen:24`, image digest `5caf8ef`, all 1,080
cells SUCCEEDED, zero index-geometry violations
(`index_onset_day == -1.0`, `index_shedding_at_day0` on every cell).
Payloads under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_sero_channel_v1/03a9db9e/cells/`.
Takeoff-conditional tables below (gate recorded_onsets >= 10; every row
carries >= 25/60 takeoff seeds, above the frozen 25% mass floor).

Per-row medians among takeoff seeds, declared | period:

| theta | takeoff D/P | infections med D/P | recorded med D/P | before_share D/P | dating share D/P |
|---|---|---|---|---|---|
| x1.0   | 56/56 | 3542/3542 | 3469/1874 | .83/.85 | .99/.54 |
| x0.3   | 56/56 | 3468/3468 | 3229/1776 | .48/.51 | .99/.53 |
| x0.1   | 53/52 | 3244/3278 | 2952/1596 | .27/.25 | .98/.52 |
| x0.03  | 43/41 | 3081/3128 | 2871/1537 | .19/.20 | .98/.51 |
| x0.01  | 39/34 | 2810/3112 | 2542/1534 | .18/.29 | .98/.51 |
| x0.005 | 30/28 | 2593/2742 | 2332/1250 | .19/.21 | .98/.51 |
| x0.003 | 25/25 | 2955/2955 | 2800/1457 | .29/.31 | .98/.52 |
| x0.002 | 28/26 | 2747/2912 | 2518/1413 | .29/.37 | .99/.51 |
| x0.001 | 28/26 | 1584/1738 | 1257/ 656 | .18/.23 | .97/.48 |

Frozen-clause score:

- **Serology clause fails at every theta under both channels.** The
  takeoff-conditional infections median is 1,584-3,542 — always above
  the band top (960). The q05-q95 interval intersects [712,960] on most
  mid/deep rows but the median never lands inside. Per the declared
  counterfactual: truth stays outside the band at every theta, so the
  attack overshoot is not reachable on the hazard axis — the suspect
  moves to seed/index structure (or the takeoff-conditioned burn class
  itself: the lowest reachable takeoff median is ~1.7x band top).
- **Trajectory clause satisfied on the period channel at x0.005 and
  x0.001** (and on declared at x0.03/x0.01/x0.005/x0.001): the
  takeoff-seed recorded_onsets q05-q95 contains 197 and median
  before_share sits within 0.10 of 0.173 on those rows. But no takeoff
  row's recorded MEDIAN reaches [98.5, 394] — the closest is 656 at
  x0.001 period, still ~3.3x over 197; 10/26 takeoff seeds on that row
  individually land in the band.
- **Channel contrast is a clean multiplier**: seed-paired
  period/declared recorded_onsets ratio = 0.50-0.54 across all nine
  theta — the symptomatic-at-specimen gate + 0.56 recall draw removes
  about half the dated mass, everywhere, independent of theta.
- **asymptomatic_at_specimen ~0.35-0.41** on takeoff seeds (identical
  across arms — the channel touches dating, not swabs) vs the record's
  ~0.51; combined with the lab_confirmed denominator (the sim confirms
  ~2x the voyage's 712 on dense rows) this is why the period dating
  share sits at ~0.5 rather than the record's 0.277.

Surface verdict per the frozen bands: **unreachable on the Theta axis
under either channel** — no row closes the gap (no row satisfies both
clauses, and truth never lands its clause). What the surface DID measure
is the decomposition's shape: the observational channel is worth a
uniform ~2x reduction in dated mass (uniform across theta — a channel
term, not a theta interaction), while the residual attack overshoot is a
truth-level term the hazard axis cannot reach (floor ~1.6x above the
serology band at the deepest theta that still takes off).

So the gap factorizes: ~2x channel (period-faithful dating measured
directly) x a truth term of ~2x+ that does not move under any reachable
theta. Next suspect per the declared counterfactual: seed/index
structure — i.e. how many effective index cases the takeoff class
carries, not how fast they burn.
