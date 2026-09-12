> **Status:** Implemented — current record of a completed measurement; states
> what the two introduction mechanisms measured and what neither reaches.
> No constant was changed, adopted or withdrawn by this campaign.

# The introduction mechanism A/B: boarding prevalence against a fiat index case

Findable record of `boarding_posting_v1` (8,550 voyages, AWS Batch job
`8041311d-fb54-4735-a1df-d10fdb9f3a06`, image `boarding-posting-v1-02e0052`,
256/256 children succeeded, 0 failed simulations) and of the matched fiat-index
arms it is read against (`expedition_posting_v2`, `hull_posting_v1`).

Readout: `telemetry_buffer/observation_model/boarding_posting_readout.py`.
Manifest: `picard_framework/runs/mega_cruise_campaign/boarding_posting_v1_manifest.json`.
Ledger item: `norovirus_open_ledger.md` §4 item 32.

## 1. What was varied, and what was not

One coordinate: whether the voyage's pathogen arrives through the boarding
channel `norwalk_gi` already ships (`mode: prevalence`, passenger 0.0325,
crew 0.0185, `never_symptomatic_fraction` 0.29,
`presymptomatic_share_of_presenting` 0.04) or through the campaign's
`fiat_index_case` override, which withdraws the `initiation` block and seeds
exactly one case at embarkation. Same three hulls, same two voyage lengths,
same release rung (`environmental_faecal_release_log10_g_per_epoch` 4.0), same
surveillance (`syndromic_comp65`), 1,000 voyages a cell, disjoint seeds.

Swept around the default: the two sourced prevalence intervals at their crossed
corners (passenger 0.025/0.040 × crew 0.007/0.030) and the Grade C
presymptomatic share at 0.02/0.04/0.08. Nothing else moved, and no constant was
chosen against an anchor.

## 2. Posting frequency: the two mechanisms bracket A9 by two orders of magnitude

Passenger-or-crew postings per 1,000 voyages at the shipped rung, n = 1,000 a
cell. A9 pre-2020 fleet-pooled is 4.187–5.583 per 1,000 eligible voyages; its
length bands are 0.332 (6–7 d) and 18.322 (11–14 d).

| hull | fiat 7 d | boarding 7 d | fiat 12 d | boarding 12 d |
|---|---:|---:|---:|---:|
| expedition 450 | 9 | 108 | 54 | 304 |
| classic 1,910 | 10 | 555 | 75 | 944 |
| spirit 3,000 | 6 | 695 | 64 | 992 |

Boarding raises posting by 11–116×, not lowers it, and on classic and spirit at
12 days posting is near-universal again — the ceiling the composition repairs
removed, reintroduced from the initiation side. The direction was declared
before the campaign ran; the magnitude was not.

This is not a new floor. Ledger item 22(d) already recorded that the
import-only stratum posts ~4.5% of voyages with essentially no onboard
transmission, and that the lowest sourced prevalence quartile stays above the
A9 band. This campaign measures the same floor on the repaired chain, where it
is 10–20× higher still.

## 3. Why: the imported cohort alone overshoots the reported-incidence anchor

Boarding imports are a per-role per-person draw, so they scale with complement:
mean imports at the default are 10.1 (expedition), 43.4 (classic) and 68.2
(spirit) per voyage, against the fiat arm's 1.

The overshoot is visible without any transmission at all. A 3.25% passenger
boarding prevalence on a 7-day voyage is 3,250 infected boarders per 100,000
passengers, i.e. **464 imported infections per 100,000 passenger travel-days**,
against A8's observed **17.8 reported cases** per 100,000 passenger travel-days
in the 6–7 day band. At the model's own ascertainment on these voyages
(reported/infected ≈ 0.21) the imports alone still deliver ~97 per 100,000 —
5.5× A8 — before a single secondary case. No transmission-side change can
subtract that.

Mean reported passenger incidence per 100,000 passenger travel-days, model
against A8 (17.8 at 6–7 d, 35.0 at 11–14 d):

| hull | fiat 7 d | boarding 7 d | fiat 12 d | boarding 12 d |
|---|---:|---:|---:|---:|
| expedition 450 | 59 | 112 | 54 | 148 |
| classic 1,910 | **20** | 407 | **35** | 530 |
| spirit 3,000 | 13 | 482 | 26 | 590 |

The fiat arm on classic reproduces A8 at both lengths (20 vs 17.8; 35 vs 35.0).
The boarding arm exceeds it 15–23×. The single-index arm's agreement with A8 is
therefore an agreement about the *mean*, obtained with an introduction process
that is one case a voyage; the boarding arm's disagreement is an agreement about
the introduction process obtained at 15–23× the observed level.

## 4. Boarding fixes what it was predicted to fix

The hypothesis boarding was run to test was over-dispersion: the fiat arm's
all-or-nothing establishment lottery, where 70% of 7-day voyages carry the
index case alone and the mean sits in a ~1.5% tail. Boarding does what was
predicted of it.

| cell | zero-secondary voyages | top 10% share of secondaries |
|---|---:|---:|
| boarding expedition 7 d | 15.6% | 33.9% |
| boarding expedition 12 d | 14.9% | 29.7% |
| boarding classic 7 d | ~0% | 17.8% |
| boarding classic 12 d | ~0% | 13.3% |
| boarding spirit 7 d | ~0% | 15.4% |
| boarding spirit 12 d | ~0% | 12.3% |

The distributional defect is genuinely repaired: no establishment lottery, no
mean carried by a thin tail. It is repaired at a level the reported-incidence
anchor rejects. Both halves are results.

## 5. Secondary yield per import: what the fiat arm was hiding

Mean secondary infections divided by mean imports, same cells:

| hull | fiat 7 d | boarding 7 d | fiat 12 d | boarding 12 d |
|---|---:|---:|---:|---:|
| expedition 450 | 3.12 | 1.62 | 6.19 | 2.67 |
| classic 1,910 | 7.77 | 4.45 | 25.96 | 6.92 |
| spirit 3,000 | 9.54 | 5.18 | 33.92 | 7.49 |

Two readings, both of the chain rather than of the introduction:

1. **Per-import yield is density-dependent and falls as imports rise** (7.77 →
   4.45 on classic at 7 days). Imports are not independent; they compete for
   the same susceptibles, surfaces and food channels, so 43 imports do not
   deliver 43× one import's epidemic.
2. **The yield is far too high for the sourced prevalence to be compatible with
   A9 at any transmission level the campaign visited.** For a ~2.5–3.25%
   passenger import prevalence to post ~0.5% of voyages, the per-import yield
   would have to sit well below 1. The fiat arm never exposed this because one
   seed times a yield of 8 is still one small epidemic; boarding multiplies the
   same yield by the whole imported cohort. The single-index-case initiation was
   masking the chain's per-introduction yield, not the chain's level.

These per-import figures are ratios of cell means, not per-voyage reproduction
numbers, and `r_effective_at_peak` remains a peak-epoch diagnostic, not a
global reproduction number.

## 6. The open question this leaves is a unit question, not a tuning question

The prevalence intervals are Grade B on **asymptomatic faecal RNA carriage on
its own denominator** (Kobayashi 2021 / Qi 2018 / Jeong 2021; outbreak-population
positivity excluded as circular — ledger §1). The engine composes them with
`never_symptomatic_fraction` = 0.29, which is adult-challenge **infections**, so
71% of the RNA-positive boarders are given a presenting course (convalescent, or
presymptomatic) with full shedding and full reportability.

That composition is the part this campaign puts in question, and it is a
provenance question — what population and case definition the prevalence
denominator is, and whether a state split measured on challenge infections may
be applied to a carriage-defined prevalence — not a licence to move either
number toward A9. Two admissible readings exist and they point opposite ways: if
the carriage prevalence *is* the never-symptomatic stratum, total infection
prevalence is higher still; if it is total infection prevalence, the challenge
split is the wrong split for it.

The untested axis that bears on this is `never_symptomatic_fraction` itself —
the campaign swept `presymptomatic_share_of_presenting` (0.02–0.08, within the
presenting group) and found posting nearly flat in it, but never swept the
0.29 adult-challenge against the 0.635 community-cohort regime, which is what
actually controls the presenting fraction (71% → 36.5%).

## 7. What this campaign does not license

* No change to the sourced prevalence intervals, the 0.29 never-symptomatic
  fraction, the 0.04 presymptomatic share, the release rung, or any route
  constant. Nothing here was tuned, and the overshoot is reported rather than
  rescued.
* No conclusion that the fiat index case is the better mechanism. It agrees with
  A8's mean while being a mechanism nobody claims is real, and its
  over-dispersion is a measured defect (item 22, §4 above).
* No conclusion about selective attention in the VSP numerator. The crew control
  recorded in item 32 (observed crew case rates flat to declining with voyage
  length while passenger rates rise) argues against surveillance intensity
  scaling with length, and this campaign adds nothing to that question.
* Every dose figure stays withdrawn.
