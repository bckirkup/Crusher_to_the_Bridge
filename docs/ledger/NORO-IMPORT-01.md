# NORO-IMPORT-01
**Date:** 2026-09-28
**Commit:** 402a4df632c9f0f28a307838dc4d59e64ee10e63
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 402a4df632c9f0f28a307838dc4d59e64ee10e63

Map of the sourced admissible region on the import axes, answered to one
question: *does any licensed point produce establishment
(ignition -> takeoff -> posting), and which axis carries it?*

Settled inputs: NORO-RHYTHM-01 (`3d9d59c6`, rhythm layer null at dose
7.57, "the surviving path to expedition takeoff and posting remains in
the dose/import structure"); NORO-FRAIL-01 (`27efdbd4`, L4 real under
Beta(0.111, 32.81); GI.1-pair-on-GII-profile provenance caveat open);
NORO-DOSE-REFIT-01 (`dose_adjustment` 7.57, interval [7.14, 8.86] —
every dose figure in the repo is withdrawn pending refit; 7.57 is used
here only because all arms share it). All runs on the current default
stack (rhythm on + EXPO-CAP-01 cap on).

## Design

Fractional cross, not a full grid:

- **Axis A — boarding prevalence:** pax/crew corner pairs
  {lo 0.025/0.007, mid 0.0325/0.0185, hi 0.040/0.030} — the declared
  `boarding_prevalence` interval (Grade B, Kobayashi/Qi/Jeong).
- **Axis B — never_symptomatic regime:** `adult_challenge`
  {0.22, 0.29, 0.36}; ONE `community_cohort` point (0.635) flagged
  population-mismatched and reported separately.
- **Axis C — symptomatic stream:** off vs on (`rate_mode: renewal`) —
  first measurement of the implemented-but-unmeasured arm.
- **Axis D — dose_adjustment endpoints:** {7.14, 8.86} once each at
  A-mid/B-mid/C-off.
- **Flagged sensitivity:** alpha = 0.15 (GII-fitted provenance candidate)
  on one expedition block, reported separately, never mixed into the
  licensed map.

Cells: expedition 7d + 12d at 1000/cell; spirit/classic/mega 12d at
200/cell at the A×B×C corners. Paired seeds 8105/8106+.

## Instruments

Per cell: emesis-fired (`ignited` = any emesis emit row), establishment
(`acq>0` = >=1 onboard acquisition, the NORO-RHYTHM-01 ignition
convention), takeoff (`peak_prevalence >= 10`, import-inclusive — see
the caveat under Verdict), posting (VSP trigger epoch set),
peak-prevalence distribution, growth depth (concurrent-peak from the
census), emesis placement partition.

## Campaign artifacts

Image `picard-campaign@sha256:7d86a251e4f6dd4e49e93b6a9d3d1d7b0342dce0c9c07c867f3f9c09806a1b0`
(tag `import-map-402a4df6`, `ENGINE_GIT_SHA=402a4df6`), job definition
`picard-import-map:3`, queue `picard-campaign-queue`, results under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_import_01/`.
43,000 runs across 13 tiers.

## Gates

- **Canary: PASS with a find.** The spirit-12d midpoint and
  expedition-12d renewal canaries verified overrides land
  (`initiation.resolved` carries the swept point) and the renewal arm
  consumes the symptomatic partition (`p_sym = 0.02746%`, drawn
  symptomatic boarders binomial-consistent). The canary caught a real
  defect pre-array: `point_factors` wrote the mechanism rung's canned
  prevalence (0.0325/0.0185) over the swept point whenever a tier
  combined `boarding_mechanism_rungs` + `boarding_prevalence_points`, so
  every Axis-A tag silently re-ran the midpoint. Fixed in `402a4df6`
  (swept point wins under `prevalence_swept`); regression test
  `test_swept_prevalence_overrides_the_rungs_reference_point`. No prior
  manifest combined those keys — no earlier results are void.
- **Skip-if-uploaded repair:** the 20 low-cell canary zips recorded
  under stale mid-point parameters were superseded by a fresh-prefix
  rerun (`campaign/noro_import_01_r2/`) copied back over the same
  run-ids; the readout groups on `parameters`, not run-id tags.
- **Stream witness: PASS.** Stream-on cells resolve `rate_mode=renewal`,
  `stream=True`, `p_sym = 0.02746%`; drawn symptomatic boarders ~100/1000
  expedition voyages and ~142/200 spirit voyages vs binomial expectation
  ~123.6 / ~164.7 (z -1.5 to -2.1). Stream-off renewal cells draw zero.

## 1. Licensed map — expedition (1000 voyages/cell)

`emit` = >=1 emesis emit; `acq>0` = establishment (>=1 onboard
acquisition); `takeoff` = peak >=10; `posted` = VSP trigger.

### Expedition 7d — screening (Axis A x Axis B, stream off)

| nsf \ prev | 0.025/0.007 | 0.0325/0.0185 | 0.040/0.030 |
|---|---|---|---|
| 0.22 emit | 14.5% [12.5,16.8] | 20.6% [18.2,23.2] | 25.9% [23.3,28.7] |
| 0.22 acq>0 | 5.8% [4.5,7.4] | 8.8% [7.2,10.7] | 9.6% [7.9,11.6] |
| 0.22 takeoff | 18.9% | 58.7% | 86.4% |
| 0.29 emit | 15.0% [12.9,17.4] | 19.6% [17.3,22.2] | 24.8% [22.2,27.6] |
| 0.29 acq>0 | 5.3% [4.1,6.9] | 8.3% [6.8,10.2] | 9.0% [7.4,10.9] |
| 0.29 takeoff | 18.4% | 58.6% | 87.3% |
| 0.36 emit | 12.8% [10.9,15.0] | 18.1% [15.8,20.6] | 24.4% [21.8,27.2] |
| 0.36 acq>0 | 5.3% [4.1,6.9] | 6.7% [5.3,8.4] | 9.2% [7.6,11.2] |
| 0.36 takeoff | 19.0% | 57.6% | 86.9% |

### Expedition 12d — screening

| nsf \ prev | 0.025/0.007 | 0.0325/0.0185 | 0.040/0.030 |
|---|---|---|---|
| 0.22 emit | 14.7% [12.6,17.0] | 20.8% [18.4,23.4] | 26.0% [23.4,28.8] |
| 0.22 acq>0 | 5.4% [4.2,7.0] | 8.2% [6.7,10.1] | 9.7% [8.0,11.7] |
| 0.22 takeoff | 18.8% | 58.7% | **86.5% — 1/1000 posted** |
| 0.29 emit | 15.3% [13.2,17.7] | 19.9% [17.5,22.5] | 25.0% [22.4,27.8] |
| 0.29 acq>0 | 5.1% [3.9,6.6] | 9.0% [7.4,10.9] | 10.0% [8.3,12.0] |
| 0.29 takeoff | 18.6% | 58.7% | 87.2% |
| 0.36 emit | 12.9% [11.0,15.1] | 18.2% [15.9,20.7] | 24.5% [21.9,27.3] |
| 0.36 acq>0 | 5.0% [3.8,6.5] | 7.1% [5.7,8.9] | 9.3% [7.7,11.3] |
| 0.36 takeoff | 18.8% | 57.6% | 86.9% |

**Posting: 1/1000 at nsf 0.22 x prevalence hi** (Wilson [0.02, 0.56]%)
— voyage s8908, 12 imports -> 27 onboard acquisitions -> peak 35 ->
VSP trigger at epoch 200. The campaign's first post-fix posting,
inside the declared interval at its upper corner.

### Expedition — renewal arms (Axis C)

| arm | nsf | emit | acq>0 | takeoff | posted |
|---|---|---|---|---|---|
| renewal stream-off | 0.22 | 2.8% [1.9,4.0] | 1.2% [0.7,2.1] | 0/1000 | 0/1000 |
| renewal stream-off | 0.29 | 3.9% [2.9,5.3] | 1.4% [0.8,2.3] | 0/1000 | 0/1000 |
| renewal stream-off | 0.36 | 2.8% [1.9,4.0] | 0.5% [0.2,1.2] | 0/1000 | 0/1000 |
| renewal stream-on | 0.22 | 5.9% [4.6,7.5] | 1.6% [1.0,2.6] | 0/1000 | 0/1000 |
| renewal stream-on | 0.29 | 5.9% [4.6,7.5] | 1.9% [1.2,3.0] | 0/1000 | 0/1000 |
| renewal stream-on | 0.36 | 7.3% [5.9,9.1] | 2.3% [1.5,3.4] | 0/1000 | 0/1000 |

(7d renewal identical within noise.) Stream-on roughly doubles emit and
establishment on expedition; 0/2000 takeoff combined.

## 2. Licensed map — big ships (200 voyages/cell, 12d)

### Spirit — screening

| nsf \ prev | 0.025/0.007 | 0.0325/0.0185 | 0.040/0.030 |
|---|---|---|---|
| 0.22 emit | 71.5% | 84.5% | 89.0% |
| 0.22 acq>0 | 44.0% [37.3,50.9] | 55.0% [48.1,61.7] | 56.0% [49.1,62.7] |
| 0.22 takeoff | 100% | 100% | 100% |
| 0.29 emit | 61.0% | 72.0% | 84.5% |
| 0.29 acq>0 | 33.5% [27.3,40.3] | 47.0% [40.2,53.9] | 53.5% [46.6,60.3] |
| 0.29 takeoff | 100% | 100% | 100% |
| 0.36 emit | 60.0% | 76.5% | 83.0% |
| 0.36 acq>0 | 33.0% [26.9,39.8] | 44.0% [37.3,50.9] | 58.5% [51.6,65.1] |
| 0.36 takeoff | 100% | 100% | 100% |

Posted 0/200 in every cell (upper bound 1.9%).

### Spirit — renewal

| arm | nsf | emit | acq>0 | takeoff | posted |
|---|---|---|---|---|---|
| stream-off | 0.22 | 15.5% | 4.0% [2.0,7.7] | 7.5% | 0/200 |
| stream-off | 0.29 | 19.5% | 5.5% [3.1,9.6] | 14.0% | 0/200 |
| stream-off | 0.36 | 13.5% | 5.5% [3.1,9.6] | 19.0% | 0/200 |
| stream-on | 0.22 | 34.5% | 16.0% [11.6,21.7] | 7.0% | 0/200 |
| stream-on | 0.29 | 33.5% | 12.0% [8.2,17.2] | 10.5% | 0/200 |
| stream-on | 0.36 | 35.0% | 12.5% [8.6,17.8] | 21.0% | 0/200 |

### Classic — screening

| nsf \ prev | 0.025/0.007 | 0.0325/0.0185 | 0.040/0.030 |
|---|---|---|---|
| 0.22 emit | 51.0% | 65.5% | 73.5% |
| 0.22 acq>0 | 29.5% [23.6,36.2] | 40.0% [33.5,46.9] | 45.0% [38.3,51.9] |
| 0.22 takeoff | 100% | 100% | 100% |
| 0.29 emit | 46.5% | 60.0% | 65.0% |
| 0.29 acq>0 | 22.5% [17.3,28.8] | 34.0% [27.8,40.8] | 40.5% [33.9,47.4] |
| 0.29 takeoff | 100% | 100% | 100% |
| 0.36 emit | 43.5% | 56.0% | 70.5% |
| 0.36 acq>0 | 27.0% [21.3,33.5] | 34.0% [27.8,40.8] | 37.0% [30.6,43.9] |
| 0.36 takeoff | 100% | 100% | 100% |

Posted 0/200 in every cell.

### Classic — renewal

| arm | nsf | emit | acq>0 | takeoff | posted |
|---|---|---|---|---|---|
| stream-off | 0.22 | 8.5% | 7.0% [4.2,11.4] | 1.5% | 0/200 |
| stream-off | 0.29 | 15.0% | 8.0% [5.0,12.6] | 2.0% | 0/200 |
| stream-off | 0.36 | 9.5% | 4.0% [2.0,7.7] | 3.0% | 0/200 |
| stream-on | 0.22 | 21.5% | 4.5% [2.4,8.3] | 0.0% | 0/200 |
| stream-on | 0.29 | 25.0% | 4.0% [2.0,7.7] | 1.5% | 0/200 |
| stream-on | 0.36 | 25.0% | 6.5% [3.8,10.8] | 1.0% | 0/200 |

### Mega — screening (partial: array stopped at user direction)

| nsf \ prev | 0.025/0.007 | 0.0325/0.0185 | 0.040/0.030 |
|---|---|---|---|
| 0.22 emit | 95.5% | 98.5% | 99.5% |
| 0.22 acq>0 | 67.0% [60.2,73.1] | 80.5% [74.5,85.4] | 89.5% [84.5,93.0] |
| 0.22 takeoff | 100% | 100% | 100% |
| 0.29 emit | 89.5% | 97.2% | 98.5% |
| 0.29 acq>0 | 67.5% [60.7,73.6] | 75.7% [68.9,81.4] | 90.9% [81.6,95.8] |
| 0.29 takeoff | 100% | 100% | 100% |

(n: 200, 200, 200, 200, 177, 66; the nsf=0.36 row and the entire mega
renewal tier never ran — `fl_mega_12d_scr` stopped at 1043/1800 zips.
Posted 0 everywhere, including the hi cell at 90.9% establishment.)

**Hull gradient at fixed prevalence hi, licensed screening cells:**
expedition-450 ~10% -> classic-1900 ~37-45% -> spirit-3000 ~54-58.5% ->
mega-5000 ~90% establishment; posting 1/6000 + 0/200 + 0/200 + 0/443.

## 3. Flagged arms — outside the licensed map

- **alpha = 0.15** (GII-fitted provenance candidate), expedition-12d
  renewal+stream nsf 0.29: emit 5.8%, acq>0 2.6%, takeoff 0/1000,
  posted 0/1000. vs the licensed alpha cell (same arm): emit 5.9%,
  acq>0 1.9%. **The GI.1->GII provenance decision is not load-bearing**
  — no expedition takeoff under either alpha.
- **community_cohort nsf = 0.635** (population-mismatched bound),
  expedition-12d renewal+stream: emit 6.5%, acq>0 2.1%, takeoff 0/1000.
- **dose endpoints** {7.14, 8.86} at A-mid/B-mid/C-off: byte-identical
  counts (emit 199/1000, takeoff 587/1000, acq>0 90/1000 both) —
  asserted-not-consumed confirmed; Axis D collapses.

## 4. Paired discordance (shared seeds, stream-off vs stream-on)

| tier | nsf | shared | off-only | on-only |
|---|---|---|---|---|
| exp_12d | 0.22 | 1000 | 26 | 57 |
| exp_12d | 0.29 | 1000 | 31 | 51 |
| exp_12d | 0.36 | 1000 | 22 | 67 |
| spr_12d | 0.22 | 200 | 17 | 55 |
| spr_12d | 0.29 | 200 | 21 | 49 |
| spr_12d | 0.36 | 200 | 15 | 58 |
| cls_12d | 0.22 | 200 | 11 | 37 |
| cls_12d | 0.29 | 200 | 23 | 43 |
| cls_12d | 0.36 | 200 | 10 | 41 |

The stream-on arm adds emits asymmetrically (on-only 2-3x off-only) —
consistent with the acq>0 doubling/tripling; a real stream effect, not
RNG-stream shuffling.

## 5. Emesis placement partition (ignited voyages)

Cabin_Corridor dominates everywhere: spirit ~88-91%, expedition ~85-92%
of emits; Free ~5-10%, Dining ~3-6%. No axis moves the partition.

## Verdict

**Axis A — boarding prevalence — is the load-bearing axis.** Ignition,
establishment, and (import-inclusive) takeoff all rise monotone with the
licensed prevalence interval on every hull measured, and the campaign's
single posting sits at its upper corner on expedition-12d. Axis B
(never_symptomatic) moves establishment weakly at best — all CIs
overlap. Axis C is not null: turning the symptomatic stream on roughly
doubles emit and establishment on expedition (1.2-1.4% -> 1.6-2.3%)
and triples it on spirit (4-5.5% -> 12-16%), but converts nothing to
takeoff or posting. Axis D is confirmed inert.

**Caveat on the takeoff column:** at expedition-hi the takeoff threshold
(peak >=10) is crossed mainly by the import cohort itself — median
imports 13 vs median acquired 0 — so takeoff overstates growth there;
`acq>0` is the establishment readout. On spirit every cell trivially
"takes off" on imports alone while true establishment runs 33-58.5%.

The binding boundary is **posting**, not establishment — and the hull
gradient makes the inversion stark: establishment climbs
~10% (expedition) -> ~40% (classic) -> ~55% (spirit) -> ~90% (mega) at
the hi corner, yet posting is 1 across all licensed cells (a single
expedition voyage, Wilson [0.02, 0.56]%). A 5000-pax hull with 9 in 10
voyages acquiring onboard still cannot post: the block sits between
acquisition depth and VSP trigger, not at the border crossing. Where it
does stand, it stands on acquisition *depth* — median acquired stays 0-2
in every licensed cell while the posted voyage grew 27 secondaries.

## Coverage note

`fl_mega_12d_scr` stopped at 1043/1800 zips and `fl_mega_12d_ren` never
ran (arrays terminated at user direction — Spot throughput ~5 runs/min
on the heaviest hull, ~8h remaining). The missing cells bound nothing
the landed cells don't already show: the mega gradient was saturated
(67-91% establishment, 0 posting) where it did measure.
