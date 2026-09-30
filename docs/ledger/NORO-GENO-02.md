# NORO-GENO-02
**Date:** 2026-09-29
**Commit:** 4f5e7fbed54ad41bce36eb09f3691366ed396e50
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 4f5e7fbed54ad41bce36eb09f3691366ed396e50

Class-magnitude readout for the declared two-class secretor gate
(NORO-GENO-01's gated stage), run as a mass-surface campaign rather than
a single powered cell: 4 hulls × 3 voyage lengths × 4 import conditions
× 3 arms × 20 seeds = **2,880 runs, all SUCCEEDED, 0 wrong-class
founders**. Design frozen before first cell:
`docs/norovirus/noro_geno_02_design.md`; full tables:
`docs/norovirus/noro_geno_02_readout.md`; aggregator:
`tools/noro_diag/geno02_surface_readout.py`.

## Verdict: gate real but compressed — measured 1.76× vs declared ~4.2×

Pooled aboard non-secretor share over the 15 dual-powered cells
(≥40 aboard/20 seeds on both mono arms; mixture runs excluded from
the pools):

- mono_gii4 (rel 0.10): **77/1,102 = 6.99%** [5.6, 8.6] Wilson
- mono_nongii4 (rel 0.45): **157/1,276 = 12.30%** [10.6, 14.2]
- ratio **1.76×**; per-cell ratios 1.22–3.00, 14/15 in the declared
  direction (one powered inversion, spr 21d ship@hi, 3-vs-2 counts)

Both arms land above their naive shares — **A ~3× above** (6.99% vs
the 2.3% formula), B ~1.3× above (12.3% vs ~9.5%) — and the excess
dominates A's small denominator: the class rel does not gate every
aboard acquisition. Which channel bypasses it is not resolved by this
stage (candidate hypotheses: dose-saturated cabinmate/emesis-near-field
challenges, imported-lineage contact chains). The two-class structure is
supported (B > A everywhere mass exists) but its realized share ratio
pools at 1.76× (per-cell 1.22–3.00), materially below the naive ~4.2×.

## Mass surface (the "where does aboard mass exist" map)

- Powered cells: 51/144 (A 16, B 18, mixture 17 of 48 per arm).
- Dominant axis is **hull**: aboard/20 seeds at shipped@hi —
  expedition ~12–17, classic ~43–57, spirit ~49–74, mega ~116–163.
- **Voyage length flat**: cls@hi 43/46/45 across 7/12/21 days — emesis
  ignition is an early-voyage event.
- **Import saturation**: mega rep 341 imports → 34 aboard vs ship@lo
  2,235 → 52 (~6.5× imports for ~1.4× aboard).
- Renewal (`reportable`) rung cold except mega (powered at 21d, 42
  aboard); cls/exp reportable: 0 aboard in 60 runs.
- Postings/1k report-only: ~0.14 rep → ~0.85 ship@hi.

## Mixture arm (attribution on powered mass)

- classes ever-infected **60.2/39.8** on declared 60/40 (+8 dual carriers);
- genotypes: GII.4 60.2%, GII.2 24.1%, GII.17 15.6%;
- classes acquired-aboard 53.8/45.9 — non_gii4 over-acquires vs its
  import share, consistent with the declared rel difference.

## Mechanism records established this stage

- `dose_adjustment` (environmental_release_log10_per_day) is **inert on
  the aboard margin at ×10⁴** (80-cell sweep: byte-identical 3 aboard
  events at adj {4,3,2,1,0}; overrides resolve correctly) — the dial
  only scales `get_pathogen_shedding` into the post-724 dead deposit
  chain; aboard acquisitions are emesis-ignition events.
- `boarding_prevalence_points` resolve only on `shipped`
  (screening_prevalence); renewal rungs derive prevalence from the fixed
  block (~0.0039) and silently drop declared points — a dead axis on
  `reportable`, verified by `initiation.prevalence` witness in-batch.
- mega×21d cells run ~2–4 h wall each under outbreak load (hi-import
  heavy tail); exp/cls cells minutes.

## Batch ids

- Canary `324dc6b1-fc31-46f3-a5b7-69ed36d2d18a` (SUCCEEDED, contract clean)
- Arrays (960 children each, all SUCCEEDED): gii4
  `43793d9e-ecf7-462d-abff-81ea7290d4e1`, nongii4
  `17c7dff4-0101-4bed-82d0-8011ea6db1ac`, mixture
  `145f3fe2-e0ed-4181-991f-995383908444`
- jobdef `picard-campaign:53`, image digest
  `sha256:4d78a94fd05bb9abea2e0e496b05e96b24bedcd0e6bad0b843814f5e376690f9`
- S3: `campaign/noro_geno_02_{gii4,nongii4,mixture}/` (+ `_sweep/`,
  `_canary/`)

## Open question left for the next stage

Which acquisition channel carries the A-arm non-secretor floor — i.e.,
*where* in the emesis-ignition path does the class rel stop gating?
Candidate instruments already exist (lineage census, route attribution);
a small paired-seed probe can disaggregate non-secretor aboard
acquisitions by route/context before any transmissibility_multiplier
sweep is designed.
