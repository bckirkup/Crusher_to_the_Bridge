# NORO-GENO-02 mass-surface readout

**Status:** measured — 2,880/2,880 runs SUCCEEDED, 0 failures, engine
`4f5e7fbe`. Design contract: `docs/norovirus/noro_geno_02_design.md`.
Ledger entry: `docs/ledger/NORO-GENO-02.md`.

- Image `picard-campaign@sha256:4d78a94fd05bb9abea2e0e496b05e96b24bedcd0e6bad0b843814f5e376690f9`
  (tag `noro-geno-02-4f5e7fbe`), jobdef `picard-campaign:53`.
- Canary `324dc6b1-fc31-46f3-a5b7-69ed36d2d18a` (spr_21d shipped@hi cell
  A, s8105): contract clean — shipped@hi resolves `initiation.prevalence`
  0.04/0.03, prior {GII.4: 1.0} + class gates pinned, `strain_attribution`
  populated, all founders gii4.
- Arrays: gii4 `43793d9e-ecf7-462d-abff-81ea7290d4e1`, nongii4
  `17c7dff4-0101-4bed-82d0-8011ea6db1ac`, mixture
  `145f3fe2-e0ed-4181-991f-995383908444`; S3
  `campaign/noro_geno_02_{gii4,nongii4,mixture}/`.
- Grid: 4 hulls × 3 voyage lengths (168/288/504 ep) × 4 import conditions
  (reportable renewal + shipped@lo/mid/hi) × 3 arms × 20 seeds
  (8105–8124); dose_adjustment pinned 4.0; `variant_surveillance` on.
- Aggregator: `tools/noro_diag/geno02_surface_readout.py`; full JSON at
  `geno02_surface_report.json` beside this file's companion data.

## Headline: the gate is real but compressed — 1.52×, not ~4.2×

Pooled over the 15 dual-powered cells (both mono arms ≥40 aboard):

| arm | aboard | non-secretor aboard | share | Wilson 95% |
|---|---|---|---|---|
| A mono_gii4 (rel 0.10) | 1,102 | 77 | 6.99% | [5.6, 8.6] |
| B mono_nongii4 (rel 0.45) | 2,516 | 268 | 10.65% | [9.5, 11.9] |

**Ratio B/A = 1.52×.** The declared shares predicted 2.3% vs 9.5%
(~4.2×). B lands at its naive prediction; **A carries a ~7% floor, ~3×
above the 2.3% formula** — the compression is entirely on the GII.4
side. Whole-surface (all cells incl. unpowered): A 7.15%, B 12.29%,
mixture 8.92%.

Interpretation (inferred, not measured): the naive share
`f·rel/(1−f+f·rel)` assumes the rel gates *every* acquisition. A
floor on A means some fraction of aboard acquisitions bypass the
secretor gate — candidate channels (hypothesis, unproven): high-dose
challenges (cabinmate / emesis near-field) where 0.10× susceptibility
still clears the infection dose, or acquisitions attributed to imported
lineages' immediate contacts where challenge dose saturates. The gate
differentially suppresses non-GII.4 acquisitions as declared, but the
A-arm floor caps the achievable ratio well below ~4×.

## Gate surface (15 dual-powered cells)

| cell | A aboard/nonsec (share) | B aboard/nonsec (share) | ratio |
|---|---|---|---|
| cls 168 ship_hi | 43/4 (9.3%) | 51/13 (25.5%) | **2.74** |
| cls 288 ship_hi | 46/3 (6.5%) | 57/8 (14.0%) | 2.15 |
| cls 504 ship_hi | 45/4 (8.9%) | 43/6 (14.0%) | 1.57 |
| mega 168 ship_hi | 123/8 (6.5%) | 163/23 (14.1%) | 2.17 |
| mega 168 ship_lo | 52/4 (7.7%) | 55/6 (10.9%) | 1.42 |
| mega 168 ship_mid | 79/7 (8.9%) | 106/13 (12.3%) | 1.38 |
| mega 288 ship_hi | 135/11 (8.1%) | 159/25 (15.7%) | 1.93 |
| mega 288 ship_lo | 48/3 (6.2%) | 52/4 (7.7%) | 1.23 |
| mega 288 ship_mid | 93/6 (6.5%) | 108/13 (12.0%) | 1.87 |
| mega 504 ship_hi | 129/6 (4.7%) | 158/19 (12.0%) | 2.59 |
| mega 504 ship_mid | 91/12 (13.2%) | 81/13 (16.0%) | 1.22 |
| spr 168 ship_hi | 49/1 (2.0%) | 52/3 (5.8%) | 2.83 |
| spr 288 ship_hi | 51/1 (2.0%) | 68/4 (5.9%) | 3.00 |
| spr 504 ship_mid | 49/4 (8.2%) | 49/5 (10.2%) | 1.25 |
| spr 504 ship_hi | 69/3 (4.3%) | 74/2 (2.7%) | **0.62** inversion |

14/15 dual-powered cells in the declared direction; the single powered
inversion (spr 504 ship_hi) rests on 3-vs-2 non-secretor counts — noise
class, reported because it is powered, not because it changes the pool.

## Mass surface: where aboard events live

Per-arm powered cells: A 16/48, B 18/48, mixture 17/48. Aboard
acquisitions (20 seeds, per arm, pooled hull×import):

| import condition | imports (240 runs) | aboard A | aboard B | aboard M | postings/1k |
|---|---|---|---|---|---|
| reportable (renewal ~0.39%) | 1,824 | 119 | 135 | 105 | ~0.14 |
| shipped@lo (0.025/0.007) | 11,985 | 249 | 295 | 293 | ~0.32 |
| shipped@mid (0.0325/0.0185) | 17,154 | 440 | 499 | 518 | ~0.41 |
| shipped@hi (0.04/0.03) | 21,972 | 731 | 869 | 799 | ~0.83–0.89 |

Measured structure:

- **Hull is the dominant axis.** At shipped@hi: exp ~12–17, cls ~43–57,
  spr ~49–74, mega ~116–163 aboard/20 seeds — a ~10× hull gradient.
- **Voyage length is flat.** cls@hi 43/46/45, spr@hi 49/51/69,
  mega@hi 123/135/129 across 7/12/21d — emesis ignitions are
  early-voyage events; extra epochs add little aboard mass.
- **Aboard mass saturates against imports.** Mega: rep 341 imp → 34
  aboard vs ship@lo 2,235 imp → 52 aboard (~6.5× imports, ~1.4× aboard).
- **Renewal rung is cold except mega.** exp/cls reportable cells ran
  0 aboard in 60 runs; mega reportable powered at 504ep (42 aboard).
- Prevalence axis live on `shipped` only (measured this stage:
  `initiation.prevalence` = declared point on shipped, renewal-derived
  ~0.0039 on reportable regardless of declared point — recorded in the
  design file).

## Mixture-arm attribution

| readout | measured | declared |
|---|---|---|
| classes ever-infected | gii4 60.2% / non_gii4 39.8% / dual 0.01% | 60/40 era-pre |
| genotypes ever-carried | GII.4 60.2%, GII.2 24.1%, GII.17 15.6% | 60%, ~0.4·0.625=25%, ~0.4·0.375=15% |
| classes acquired-aboard | gii4 53.8% / non_gii4 45.9% | — |

Aboard acquisitions skew toward non_gii4 relative to its import share
(45.9% of aboard vs 39.8% of ever-infected) — the higher non-secretor
rel of the non-GII.4 class shows up downstream of challenge, as
declared. A dual-lineage "gii4+non_gii4" carrier class exists (8 ever,
5 aboard).

## Checks (all clean)

- Wrong-class founders: **0** across 2,880 runs.
- Attribution present on every zip (`strain_attribution` + lineage
  census + resolved profiles).
- Priors pinned: mono arms carry their declared singleton priors in
  `resolved_pathogen_profiles.json`; genotype_classes rels 0.10/0.45,
  multiplier 1.0 everywhere.
- No cell selected on postings (reported only, per contract).
