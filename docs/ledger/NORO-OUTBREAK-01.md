# NORO-OUTBREAK-01
**Date:** 2026-10-02
**Commit:** bc4de6f5bb3f386e773631ee2f1ad81c4db8fb07
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** bc4de6f5bb3f386e773631ee2f1ad81c4db8fb07

Anchor assessment of simulated norovirus outbreaks on the smaller VSP hull
classes after the hand-reservoir rebuild (`a3c76061`: hygiene_cycle +
protected sequestration + own-pool, shipped default) and the
presentation-share repair (`890bfce3`: `presentation_draw_mode:
once_per_course`, shipped default, `daily_hazard` labelled baseline).
Design frozen in `docs/norovirus/noro_outbreak_01_design.md`; canonical
tables in `docs/norovirus/noro_outbreak_01_readout.md`. 12 cells x 1000
seeds = 12,000 voyages (expedition_cruise_450 {7d, 12d} +
classic_cruise_1900 {12d}, scr lo/mid/hi + ren at shipped nsf 0.29, dose
7.57, syndromic_comp65), all Batch children SUCCEEDED on
`picard-campaign-queue`, jobdef `picard-noro-outbreak-01:4`, image
`noro-outbreak-01-bc4de6f5` (digest `3dfaaf5f`), S3 prefix
`campaign/noro_outbreak_01/`. Canary: 20/20 seeds at
`0cdb87485902b8fd5c8062bd272f4dea35ef2cb7` (pre-merge branch SHA, same
tree).

## Measured — frequency

- Screening cells carry a strong prevalence x length gradient on
  expedition: takeoff 53.3/80.6/94.7% (7d lo/mid/hi) and
  79.1/92.7/98.4% (12d lo/mid/hi); ignition 31-88%.
- Classic 1900 is saturated on the screening arm (100% takeoff at all
  three prevalence points, median acquired 107-123) and still 77.9%
  takeoff on the renewal arm.
- Posting now happens: 8 posted voyages (exp-12d scr 2+2+2 at
  lo/mid/hi, exp-12d ren 1, cls-12d scr-hi 1), i.e. A9 0.1-0.2% on the
  cells that post vs the MIDRS ~0.5% reference — under the band but
  non-null, where IMPORT-01 found a single posting map-wide.

## Measured — progression (takeoff voyages)

- Onset epoch 0 everywhere: imported infections seed the voyage at
  boarding, then smolder.
- Detection and VSP flag arrive late: detection ~ep253-282 of 288 (88-98%
  through the 12d voyage); vsp_flag ~ep251-282 where it fires at all.
- Peaks are end-censored: peak_epoch ~ep271-285 of 288 (12d) and
  ~ep143-163 of 168 (7d) — most outbreak curves are still accelerating
  at disembarkation, so within-voyage attack rates read low by
  truncation.
- Posted voyages' reported pax AR medians 0.019-0.036 — below the
  class IQR floors (expedition 4.0%, classic 4.15%) even where posting
  occurs.

## Measured — anchors (era=pre, takeoff-conditional)

Every cell fails every scored anchor. The deficit concentrates in the
illness-expression channel, not transmission:

- A1 ever-ill pax 0.0-2.0% vs band (10%, 22%) — order-of-magnitude under.
- A2 ill/infected 6-17% vs (59%, 81%).
- A4 reported pax AR median ~0 vs class IQR 4-10% — takeoff voyages
  produce essentially zero reported cases on the median voyage.
- A8 incidence runs hot instead: pax ratios 2.4-9.5x and crew 2.5-9.5x
  the end-of-period reference on scr cells — acquisition incidence
  exceeds the field's; infections arrive, symptom/reporting does not
  follow.
- A9 posting 0-0.2% vs the MIDRS reference (~0.5%).

## Measured — paired delta vs NORO-IMPORT-01 (same seeds, nsf29 cells)

The hand-reservoir + presentation stack is a large amplification:

- Establishment gained on 855-901/1000 expedition scr seeds, 119-155/200
  classic scr seeds, 230-306/1000 exp ren seeds (losses 0-8/1000).
- Takeoff gained up to 605/1000 (exp-12d scr-lo); classic scr was
  already 100% takeoff before, so its gain shows in depth: +105 to +123
  median acquisitions, +79 to +85 median peak prevalence.
- Posting: 8 gained, 0 lost. Median acquired +5 to +19 on exp scr,
  +45 cls ren; delta reported pax AR +0.0032-0.0075.

## Interpretation

Measured: onboard establishment/progression under the shipped stack is
materially stronger than at IMPORT-01, outbreaks reach VSP-class sizes on
the small hulls, and posting is non-null. The anchor miss is no longer
transmission-side: it sits in infection->illness->report conversion
(A1/A2/A4 under by ~4-10x while A8 acquisition incidence over-delivers).
Hypothesis (unproven): the ever-ill coupling or symptom-probability path
expresses illness too weakly for the anchor bands, or reporting
(sick-call x comp65) censors too deeply — the instruments measure the
gap, not which link carries it. That attribution is the open next
question; the readout cannot separate them at summary level.

## Harness note

`tools/noro_diag/outbreak_anchor_readout.py` streams `summary.json` via
S3 range reads (EOCD -> central directory -> member blob); classic zips
are ~45 MB mostly census member, so ranged reads keep a 12k-run readout
off disk. Canonical artifacts under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_outbreak_01/`.
