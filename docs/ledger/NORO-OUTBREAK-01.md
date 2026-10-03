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

## Measured — spirit-class extension (d6c51c14)

Per `noro_outbreak_01_spirit_design.md`: 4 more cells x 1,000 seeds
(spirit_cruise_3000 @12d, scr lo/mid/hi + ren, seeds 8105-9104) ran at
`d6c51c14` (jobdef `picard-noro-outbreak-01:5`, image
`noro-outbreak-01-d6c51c14`), all SUCCEEDED — 16 cells, 16,000 voyages
total in the canonical readout. Between the two stamps, #846 added the
ENV-HAZARD arm + source-model hooks (additive, orthogonal to pathogen
transmission); the CHANNEL-03 funnel at `d6c51c14` reproduced scored
voyages seed-for-seed, so the stamps measure the same dynamics.

- Takeoff 91.4% on ren, 100% on all three scr cells; median acquired
  89 (ren) to 175-199 (scr) — outbreaks get bigger with hull size, and
  spirit scr cells saturate as classic's did.
- **Zero postings on all 4,000 spirit voyages** — the larger hull does
  not rescue the reporting channel.
- Anchors: same all-FAIL shape (A1 0.01-0.02, A2 0.15-0.18, A4 ~0, A9
  0/4000) with two isolated passes that pass nowhere else: A5 pax/crew
  2.70 PASS on scr-bp25c7 (still FAIL at 1.31-1.96 on the other spirit
  cells) and A8 pax incidence PASS on ren (17.91) while scr runs
  ~66-77x over reference.
- Paired vs IMPORT-01 (200 shared seeds): establishment gained 93-168,
  +93 to +199 median acquisitions on scr cells — the hands+presentation
  amplification scales with hull size.

## Interpretation

Measured: onboard establishment/progression under the shipped stack is
materially stronger than at IMPORT-01, outbreaks reach VSP-class sizes on
the small hulls, and posting is non-null. The anchor miss is no longer
transmission-side: it sits in infection->illness->report conversion
(A1/A2/A4 under by ~4-10x while A8 acquisition incidence over-delivers).
The spirit extension extends the same shape to the 3000-agent class:
bigger outbreaks, still essentially zero reporting. Link attribution is
now measured, not hypothesised — NORO-CHANNEL-03 (180 funnel voyages on
the exact scored cells, `d6c51c14`) finds the gap **shared**: the
symptom-course draw is the first broken link on all 9 cells
(symp/infected 0.170-0.413 vs the 0.6 declared threshold) AND the
infirmary report hazard under-fires on 8/9 (rep/elig 0.168-0.321 vs
0.4), with no severity/eligibility wall anywhere. Both links must move;
neither alone reaches the anchors.

## Harness note

`tools/noro_diag/outbreak_anchor_readout.py` streams `summary.json` via
S3 range reads (EOCD -> central directory -> member blob); classic zips
are ~45 MB mostly census member, so ranged reads keep a 12k-run readout
off disk. Canonical artifacts under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_outbreak_01/`.
