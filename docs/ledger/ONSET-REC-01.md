# ONSET-REC-01
**Date:** 2026-10-08
**Commit:** #972
**Pathogens:** sars_cov2_resp
**Status:** declared

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

_pending — canary submitted; fills when the 40 cells land._
