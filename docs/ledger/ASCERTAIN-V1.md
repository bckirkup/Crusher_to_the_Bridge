# ASCERTAIN-V1
**Date:** 2026-09-30
**Commit:** cb519c97
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** cb519c97

The ASCERTAIN-V1 conditioned array: a declared sweep over the shipped
`observation_model.onset_recording` channel (gate × recall) plus the
mild-stratum ascertainment corners via
`syndrome_case_eligibility_by_severity`, splitting the ~18×
recorded-onset gap into channel vs truth shares on the conditioned
lattice θ ∈ {1e11, 2.37e11, 1e12} × seeds 20200205–14 — 270 cells,
design `picard_framework/runs/covid_ascertain_v1_design.json` (PR
#783, admissibility frozen before any cell ran). Scored against both
anchors: covid.T1 (197 recorded onsets / before_share 0.173) and the
held-out serology anchor covid.H5 (infections_total band [712, 960]).
No constants fitted; the mild-interior recall field does not exist and
was reported, not built.

## Execution (measured)

Two AWS Batch arrays, job-def `picard-covid-boarding-screen:33`
digest-pinned to `picard-campaign@sha256:f8f56c23…` (image built at
merged SHA `cb519c97`, design inside image verified). First Spot
submission (`ca09a3e6`) parked >60 min at PENDING with zero children —
Spot capacity drought — terminated and resubmitted on the on-demand
queue `picard-analysis-queue` per the standing approval: canary
`49368fac-a2ad-476b-8677-73dd24f4da39` (cells 0–89, all 9 arms at the
anchor θ), then remainder `3107b5c7-8a09-4ca8-9cff-c845d4f356af`
(cells 90–269). **270/270 cells SUCCEEDED, zero index-geometry
violations** (`index_onset_day == -1.0`, `index_shedding_at_day0` on
every cell), zero child failures, ~10–25 min/cell. Payloads under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_ascertain_v1/cb519c97/cells/`.
(24 stray files from the killed submission exist under
`cells/cells/` — same design+image, excluded from the canonical
prefix; bucket policy denies delete.)

New payload echoes verified on every cell: `onset_recording` resolves
to the arm's declared block (null on D0_declared/M0_declared),
`onset_eligibility_by_severity` shows [0,0,0,1,1] exactly on the two
mild corners and [0,0,1,1,1] elsewhere, and
`recorded_onsets_by_severity` shows `mild` absent exactly on M0 arms.
D0_declared reproduces the coop/v13 baseline class (~2.8–3.5k recorded,
takeoff-conditional) as the cross-image drift check — no drift.

## Channel-vs-truth decomposition (measured, takeoff-conditional, gate
recorded_onsets ≥ 10)

Takeoff-seed medians; `pair` = seed-paired arm/D0 ratio of
recorded_onsets; θ 2.37e11/1e11/1e12 carry 7/8/9 takeoff seeds per row
(fizzles: seeds 07, 10, 11 at anchor — all-arms fizzle, consistent with
the takeoff-conditioned design).

| arm | rec/197 | pair/D0 @2.37e11 | pair/D0 @1e11 | pair/D0 @1e12 |
|---|---|---|---|---|
| D0_declared   | 15.3 / 14.3 / 18.0 | 1.000 | 1.000 | 1.000 |
| G1_gate       | 14.3 / 13.2 / 17.5 | 0.969 | 0.971 | 0.971 |
| P1_period     |  8.1 /  7.5 /  9.8 | 0.547 | 0.546 | 0.549 |
| P28_gate      |  4.0 /  3.8 /  4.8 | 0.273 | 0.272 | 0.274 |
| P15_gate      |  2.0 /  2.0 /  2.6 | 0.150 | 0.146 | 0.148 |
| R56_recall    |  8.7 /  8.1 / 10.2 | 0.567 | 0.567 | 0.562 |
| R28_recall    |  4.2 /  4.1 /  5.0 | 0.279 | 0.283 | 0.280 |
| M0_declared   |  2.2 /  2.0 /  2.5 | 0.133 | 0.134 | 0.136 |
| M0P56_period  |  **1.19 / 1.05 / 1.37** | 0.073 | 0.073 | 0.076 |

The decomposition is multiplicative and near-exact: gate ≈ 0.97, recall
≈ p (0.567 @0.56, 0.28 @0.28), gated ladder ≈ p × 0.97, mild corner ≈
0.13, and M0P56 ≈ 0.073 ≈ 0.13 × 0.55 — every declared point's share
predicts the next from the factors alone. Takeoff-seed medians: D0
3,008 @anchor (q05–q95 [2082, 3542]); M0P56 234 [152, 266].

**IN-BAND LANDINGS (declared report-immediately trigger — rows whose
takeoff median recorded_onsets falls inside ~[150, 250] were
reported):** M0P56_period's takeoff median = **234 @2.37e11**, 207
@1e11, 270 @1e12 — inside the conditional-clause band [98.5, 394] at
ALL three θ; M0_declared lands at 1e11 (390) and P15_gate at the two
lower θ (385/400). These are count-leg landings only.

## The three legs at the declared corners

- **Count leg closes observationally — but only at the degenerate
  corner.** Deleting the mild stratum (M0) alone drops the takeoff
  median to ~390–482 (2.0–2.5×); mild corner × period channel lands
  207–270, i.e. the count gap is *manufacturable* by ascertainment: the
  mild corner carries ~7.5× and the record-derivable recall ~1.8×, of
  the ~15× count gap. The gate is nearly non-binding in-sim (~3–4% of
  dated mass — virtually every confirmed case was already presenting at
  its confirming specimen); recall is the dominant mild-channel term.
- **Timing leg never moves.** before_share takeoff medians are
  0.60–0.84 at every (θ, arm) vs the record's 0.173 — the channel
  cannot touch burn timing, and the per-seed distribution is bimodal
  (early-burning seeds ~0.9–0.98, late seeds ~0.02–0.13). Per the
  frozen grammar, a count landing with a broken timing leg is a
  different failure class.
- **Truth leg is unmoved by every arm.** infections_total takeoff
  medians 3,536–3,599 (q05–q95 [2198, 3609]) at all θ, all arms —
  including the mild-eligibility arms (the ~1% isolation coupling seen
  at e168 is below takeoff-seed noise; arm-paired M0/D0 infections are
  identical to within ~0.3%). The q05–q95 interval never intersects
  [712, 960] — serology clause fails everywhere; the truth overshoot
  the count landing leaves behind is ~3.7–4.2× the band top.
- **Composition is wrong at the corner.** Mild share of dated mass is
  85–88% on every non-M0 arm (matches ROUTE-ATTR-V1's ~85–89%); the
  record's dated set was mild-heavy, so the landing is structurally
  degenerate — right count, zero mild, dating rate of confirmed 0.072
  vs the record's 0.277.

## Frozen-clause scores

- **Trajectory clause fails at every row** (count and timing legs both
  required): even where the count lands in-band (M0P56 all θ; M0 @1e11;
  P15 @{2.37e11, 1e11}), before_share medians miss 0.173 ± 0.10 by
  ~3–5×.
- **Serology clause fails at every row** — infections medians never in
  band; q05–q95 never intersects it. Extends SERO-CHANNEL-V1's
  "unreachable on the Θ axis" to the ascertainment axis: the truth
  overshoot is reachable on NEITHER.
- **Verdict per the frozen grammar: `channel_only`.** At M0P56 the
  channel's full measured share (~0.073×, ~13.7× worth of the 15.3×
  count gap) reaches the record's count and the residual is biology —
  but the landing is degenerate (deletes the record's dominant mild
  stratum; dating rate overshoots to 0.072 vs 0.277) and the truth
  term never moves. The gap factorizes cleanly: **the count leg is
  ~fully observational at the declared corner (mild ≈ 7.5×, recall
  ≈ 1.8×, gate ≈ 1.03×); the real residual is truth-level —
  infections ~3.5–4× the serology band and before_share ~3–5× off,
  neither movable by any observation channel.**

## Limits carried (from the design's `what_this_cannot_settle`)

- A per-severity recall draw is not expressible (uniform
  `report_probability`): the mild corner is 0/1 eligibility, not a mild
  recall interior — the landing point is the corner, so the measured
  "channel share" for mild is a bound, not a fitted interior.
- `lab_confirmed_total` ~3,000–3,565 vs the record's 712 (~4–5×): the
  case-ascertainment denominator overshoot is a separate channel term
  this design measures but does not gate — the dating-share read is
  computed against it directly.
- covid.H5 is a subgroup extrapolation; the band carries the
  uncertainty.

**Next decision named:** the count leg is explained at the corner; the
standing residual is now pure truth+timing — infections ~3.5–4× band
top under takeoff conditioning and before_share ~0.6–0.8 vs 0.173. The
suspects per SERO/COOP remain seed/index structure (day-0 exposure
geometry, ring membership) — i.e. the channel axis is measured out and
the open question is whether a seed-geometry correction can move both
truth legs at once.
