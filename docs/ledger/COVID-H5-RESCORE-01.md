# COVID-H5-RESCORE-01
**Date:** 2026-11-20
**Commit:** eb024892
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** c053e15f

Pure-readout rescore of the committed `COVID-THETA-REFIT-01` surface
with the serology band `covid.H5` reported per θ — the lever
`COVID-ONSET-FUNNEL-01` named ("the scored contract needs an
attack-size/serology-aware observable"). No new cells, no constant
changes, no contract adoption: the same 840 committed `cell_<seed>.json`
payloads (DP `boxed_s1s2` 12 θ × 20 seeds, GM `hygiene_cycle` 12 θ × 50
seeds — cell payloads committed at `c053e15f`; the readout ran at
`eb024892`) decomposed by `tools/covid_h5_rescore.py`; evidence
`reports/h5_rescore/surface.json`. Per θ: verbatim T1+T3 contract loss
(recomputed identically — same `ThetaObjective` machinery), takeoff
fraction under the scorer's gate (`recorded_onsets >= 10`), and
takeoff-conditional `infections_total` against the H5 band [712, 960]
(the anchor's own `scored only on takeoff seeds` declaration).

## Result — the joint T1+T3+H5 admissible set is empty on the Θ axis

**Sanity:** the verbatim contract reproduces THETA-REFIT-01's selection
exactly — θ=3.162e11 at bootstrap frequency 0.736 (paired 2000 resamples,
seed 20200205, ties to smaller θ).

**DP surface (takeoff-conditional medians):**

| θ | takeoff | infections q05/med/q95 | in-band cells | H5 resid | verbatim loss | recorded_onsets | campaign_pos |
|---|---|---|---|---|---|---|---|
| 7.9e6 | 0.45 | 71/171/576 | 1/9 | 1.39 | 50.9 | 8 | 10 |
| 1e7 | 0.45 | 49/161/527 | 0/9 | 1.52 | 57.8 | 4 | 8 |
| 3.16e7 | 0.45 | 69/214/1390 | 0/9 | 1.19 | 53.5 | 5 | 7 |
| 1e8 | 0.80 | 152/448/2366 | 0/16 | 0.81 | 28.0 | 66 | 48 |
| 3.16e8 | 0.80 | 252/677/2807 | 2/16 | 0.48 | 21.8 | 216 | 159 |
| 1e9 | 0.90 | 813/2246/3265 | 1/18 | 0.78 | 19.2 | 1,460 | 596 |
| 3.16e9 | 0.90 | 715/2710/3344 | 1/18 | 0.92 | 20.1 | 1,866 | 683 |
| 1e10 | 0.95 | 2016/3294/3457 | 0/19 | 1.12 | 15.7 | 2,692 | 676 |
| 3.16e10 | 0.95 | 2752/3456/3507 | 0/19 | 1.23 | 15.7 | 2,802 | 672 |
| 1e11 | 0.95 | 3451/3522/3571 | 0/19 | 1.30 | 15.5 | 2,880 | 669 |
| 3.16e11 | 0.95 | 3547/3573/3589 | 0/19 | 1.31 | 13.7 | 2,878 | 443 |
| 1e12 | 0.95 | 3573/3599/3613 | 0/19 | 1.32 | 14.2 | 2,812 | 364 |

- **No θ lands a takeoff-conditional median inside [712, 960]**: the
  band sits in a half-decade gap — θ=3.16e8 reads 677 (just under the
  band floor) and θ=1e9 reads 2,246 (2.3× the band top). Only 5/190
  takeoff cells land in band anywhere on the grid.
- **The truth-band region falsifies the observable record**: at the
  band-adjacent θ≈3.16e8, `campaign_positives` med 159 vs 634 (~4×
  under) and takeoff-conditional `lab_confirmed` med 406 vs infections
  677 — on right-sized truth the model confirms ~0.60 of infections
  (~1.4× under) vs the record's 712/840 ≈ 0.85. The
  binding defect is per-infection capture (the swabbed-and-missed drain
  + campaign roster starvation ONSET-FUNNEL-01/ASYM-CONF-01 measured),
  not dose: Θ compensated by over-infecting ~4.3×.
- **Scoring H5 cannot repair the selection either**: the augmented
  contract (verbatim loss + equal-weight takeoff-conditional band
  residual) still selects θ=3.162e11 at 0.6315 (vs verbatim 0.736;
  runner-up 1e9 rises 0.154→0.1995). The band residual varies only
  0.78–1.32 across the whole working region — too flat against a
  6-log-unit verbatim advantage (13.7 vs ≥19.2) to move the winner.
  A serology term makes the overshoot *visible*; it cannot make it
  *exitable* on the Θ axis.

**GM held-out row (unchanged by the rescore, recorded for the surface):**
at the fitted θ=3.162e11, takeoff 96%, infections median 180 of ~223
aboard (~81%), campaign_positives 108.5 vs 128, asym 0.272 vs 0.8125,
recorded_onsets 46 — the natural-history/observation residual is
invariant, as before. GM carries no H5 band (no serology anchor exists
for it).

## Verdict

1. **Joint admissible set: EMPTY.** No θ satisfies the scored contract
   *and* the serology band simultaneously — truth-in-band requires
   θ≈3–5e8 where the specimen channels run ~4× under the record, and
   the scored-contract region (θ≥1e9) overshoots truth 2.3–4.3×. This
   is stronger than ONSET-FUNNEL-01's hypothesis implied: the mismatch
   is not a scoring-blind-spot story ("Θ landed magnitude the
   observation layer cannot see") — the observation layer at
   right-sized truth *cannot reach* the record's confirmations.
2. **An H5 scored term is measured and insufficient**: equal-weight
   augmentation moves the winner's frequency 0.736 → 0.6315 but not
   the winner. Adding it to the scored contract is a *contract*
   decision with attribution — H5's own declaration forbids selecting
   Θ against it ("Held out forever"), and the rescore is published as
   a readout only.
3. **Next lever is the per-infection capture rate**, not Θ and not a
   new transmission mechanism: at right-sized truth the model's
   `infections_total` (~0.60 at θ=3.16e8 takeoff cells, ~0.91 at
   θ=1e11)
   brackets the record's ~0.85 — the seam where the record's serial
   retesting meets the model's specimen-sensitivity loss
   (ONSET-FUNNEL-01's 6,873 swabbed-while-infected-negative; ASYM-CONF-01's
   ladder starvation; CREW-REACH-01's retest-tier recovery). The
   contract decision — whether `covid.H5` (or a derived
   confirmed-per-infection observable) enters `merge_fit` — is named,
   not taken, here.

No constants touched, no re-runs, no gate changes — a measurement
entry only.
