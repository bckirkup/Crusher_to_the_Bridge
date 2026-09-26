# SERO-CHANNEL-V1
**Date:** 2026-09-26
**Commit:** 8ac510b3
**Pathogens:** sars_cov2_resp
**Status:** measured (canary only — period arm, theta x0.001, 20 seeds)
**Measured at:** 8ac510b3

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

Inference (not yet measured): the ~0.5 dating share vs the record's 0.28
means the channel's undershoot arm of the gap decomposition is smaller
than the declared expectation — under the period channel the sim still
dates roughly twice the record's share of confirmed cases at theta
x0.001. Whether that is the channel over-admitting or the record's
denominator differing (sim confirms more infections than the voyage's
712) is exactly what the paired declared arm resolves; the full array is
the user's decision.
