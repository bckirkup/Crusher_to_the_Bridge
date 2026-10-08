# ONSET-REC-01
**Date:** 2026-10-08
**Commit:** #972
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** bccc9daa

The onset-recording channel (`observation_model.onset_recording` on
`sars_cov2_resp`, frozen from SERO-CHANNEL-V1:
`{symptomatic_at_confirmation_required: true, report_probability: 0.56}`,
additive and default-off) armed on the boxed crew-mess configuration —
the CREW-MESS-01 `sect_mess_boxed` arm, carried verbatim as the design's
`base_overrides` and composed by `campaigns/covid/onset_rec_01/cell.py`
so the empty-override baseline reproduces it bit-identically.

Design: `picard_framework/runs/covid_onset_rec_01_design.json`,
doc `docs/covid/covid_onset_rec_01_design.md`. 2 arms × 20 seeds =
40 cells at θ7.9e6, seeds 20200205–20200224, on
`picard-analysis-fargate-queue`.

Frozen scoring (nothing below is altered after the surface is seen):

- **Primary:** dated share of lab_confirmed
  (`recorded_onsets / lab_confirmed_total`, pooled + per-cell median) vs
  the record's 0.277 (197/712). Declared expectation band [0.43, 0.55]
  (SERO-CHANNEL-V1's landing on the lambda-cross surface; gate-only
  share on these boxed cells measured ~0.77 in the funnel attribution,
  so the recall draw is expected to carry the remainder). Verdict
  grammar: RECORD-MATCHED ([0.227, 0.327]) / CHANNEL-INSUFFICIENT
  (> 0.327 — the predicted, fully admissible outcome) / OVER-CLOSED
  (< 0.227).
- **Secondary, reported never thresholded:** `lab_confirmed_total` vs
  712; crew share of lab_confirmed pooled + conditioned on DP-scale
  cells (channel is role-flat; ~unchanged 0.435 / ~0.29-scale expected —
  a move investigates, it does not defect); symptomatic-at-specimen
  share; confined-pax takeoff median vs guard [26, 160]; deliveries
  parity ~162k.
- **Bit-identity clause:** `boxed_declared` must reproduce
  `sect_mess_boxed` bit-identically at matched seeds — resolved spec
  equality (contract-pinned) plus voyage event counts equal to the
  landed S3 cells, absent engine drift since their image. A deviation
  is a defect in the base composition, not a finding.

`report_probability` 0.56 is record-derived arithmetic
(197/712 ÷ ~0.49 symptomatic-at-specimen), declared once — never
retuned to the 0.277 anchor.

## Readout

Measured at `bccc9daa` — 40/40 cells landed on
`picard-analysis-fargate-queue` (arrays `0b49e3f6` boxed_declared,
`3391150c` boxed_period; image digest `sha256:812b02bb`), zero child
failures, zero audit-invariant violations. Readout artifact:
`reports/covid_onset_rec_01_readout.md`
(`campaigns/covid/onset_rec_01/readout.py`).

| arm | dated share (pooled / med) | pooled lab_conf | pooled recorded | lab_conf crew share (pooled / DP-scale) | verdict |
|---|---|---|---|---|---|
| boxed_declared | 0.839 / 0.833 | 819 | 687 | 0.435 / 0.293 (n=2) | BASELINE — bit-identity control |
| boxed_period | **0.416 / 0.323** | 819 | 341 | 0.435 / 0.293 (n=2) | **CHANNEL-INSUFFICIENT** |

- **Primary:** pooled dated share 0.416 vs the record's 0.277 — above
  the record band top 0.327 → CHANNEL-INSUFFICIENT, the declared
  admissible outcome. It lands ~0.014 under the declared expectation
  band [0.43, 0.55] (SERO-CHANNEL-V1's ~0.43–0.53 range was on a
  different hull/config; the median 0.323 reads lower because the
  channel removes the most dated mass on the largest cells, so pooling
  is pulled up by takeoff cells).
- **Bit-identity clause:** all 20 `boxed_declared` seeds are
  IDENTICAL to the landed `sect_mess_boxed` cells on every
  voyage-derived field (infections_total, aboard_total,
  lab_confirmed_total, infections_during_window,
  confined_passenger_infections_during_quarantine, recorded_onsets,
  service_deliveries). The campaign-composed `base_overrides` is
  verified in place.
- **Secondaries (reported, never thresholded):** pooled
  lab_confirmed_total 819 vs record 712 — unchanged between arms
  (bit-identical lab confirmations); lab_confirmed crew share
  identical on both arms at 0.435 pooled / 0.293 DP-scale — the
  role-flat channel produced no share move; symptomatic-at-specimen
  median 0.688 both arms; confined-pax takeoff median 28/29 inside
  the [26, 160] guard; deliveries parity 162,184 med vs ~162k.
- **Consequence:** the full declared channel removes ~half the dated
  mass (687 → 341 pooled) and still leaves ~0.14 of confirmed dated
  above the record — the residual is an observation-channel gap, not
  a transmission one.
