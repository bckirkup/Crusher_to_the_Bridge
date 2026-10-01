# COVID-GM-RESCORE-01
**Date:** 2026-10-01
**Commit:** f881b809
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 591d21b1

Re-score of `greg_mortimer_2020` (held out) under the post-PRACTICE-01
physics — image built at merge commit `591d21b1` (post #811
NORO-HAND-CARRIAGE-01 repin + #812 INFO-SUPPRESS-V1, default OFF; nothing
later on `main` through `f881b809` touches the engine). Scoring lattice
frozen before any cell ran: scenario as-declared ×
`hand_reservoir_mode` ∈ {hygiene_cycle (baseline, empty overrides),
spike_decay (v13-era labelled baseline)} × θ ∈ {1e11, 2.37e11, 1e12} × 50
seeds @20200205 = 300 cells; plus the declared diagnostics (imports:3 at
anchor θ × hygiene_cycle × 50 seeds; takeoff-conditional H1 read on every
scoring row). Designs `picard_framework/runs/covid_gm_rescore_v1_design.json`
/ `..._imports3_design.json`; readout `tools/covid_gm_rescore_readout.py`;
jobdef `picard-covid-boarding-screen:42` pinned to image
`sha256:74721d9d39175489133cf95f1eb66fc5a75a0d71cb2f55cfb41489cfa39d3b7c`;
cells under `campaign/covid_gm_rescore_v1/591d21b1…/cells/` (canary
`ee98024f`, full array `a1edb1b1`, diagnostics `8fd9a517`).
300/300 + 50/50 cells, **0 audit failures** (`delivery.hand_reservoir_mode`
echo on every cell; pairing keyed on (θ, seed)).

## Verdict: `mixed`

The stale first-look score (v3, pre-refine Θ 1e9, spike-decay-era physics:
P(takeoff) ≤ 0.04–0.06, campaign positives median ~3, q95 ≤ 18 —
`docs/covid/covid_first_look_readout.md`) is retired: ignition is now the
norm (P(takeoff) 0.76–0.86) and the positive-count envelope reaches the
record's 128 at both higher θs on both arms. But the landing is
**envelope-only** — the q05 tail sits at 1 (ignition-or-bust), ~1-in-5
seeds fizzle at every θ, and the asymptomatic share misses the record's
0.81 ± 0.10 everywhere by ~10×.

## Scoring rows (50 seeds each, measured)

| θ | arm | P(takeoff) | campaign positives med [q05–q95] | H1 lands | asym share med | H2 hit |
|---|---|---|---|---|---|---|
| 1e11 | hygiene_cycle | 0.76 | 82 [1, 122] | — | 0.094 | — |
| 1e11 | spike_decay | 0.76 | 61 [1, 123] | — | 0.122 | — |
| 2.37e11 | hygiene_cycle | 0.80 | 105 [1, 131] | **yes** | 0.064 | — |
| 2.37e11 | spike_decay | 0.84 | 96 [1, 132] | **yes** | 0.072 | — |
| 1e12 | hygiene_cycle | 0.86 | 116 [1, 131] | **yes** | 0.029 | — |
| 1e12 | spike_decay | 0.84 | 111 [1, 135] | **yes** | 0.026 | — |

H1 grammar (frozen): median ∈ [64, 256] AND q05–q95 contains 128 — lands
on four of six rows; at θ 1e11 the interval tops out at 122/123, six
under the record. H2 needs asym share within 0.81 ± 0.10 — misses
everywhere (medians 0.026–0.122). Replay verdict (H1 AND H2) is excluded
on every row.

**Takeoff-conditional H1 read** (frozen diagnostic): among ignited seeds
at anchor θ the count stays landed — hygiene_cycle median 108 [35, 131]
(n=40), spike_decay 103 [44, 132] (n=42); the ignition-seed interior
still spans a ~4× spread, so the fizzle tail is *added* on top of an
already-wide conditional distribution, not the sole defect.

## Onset timing under the day-20 screen channel

Pooled onset curve peaks days 13–16; first-onset median day 9–10
[q05 ~6–8, q95 ~17–19]; median onset day 15–16. The share of recorded
onsets on/after split day 20 is median 0.05–0.16 per row — ~85–95% of
onsets precede the single ship-wide screen, consistent with the record's
shape (the day-20 swab caught a nearly-complete outbreak).

## Reported-not-selected: recorded attack share vs H3

`attack_share_recorded` (recorded onsets / aboard) medians 0.19–0.26
[q05 ~0.004, q95 ~0.34–0.39] vs the Willebrand cross-ship aggregate IQR
[0.0003, 0.015] — declared for context only; denominators differ by
construction (single-hull recorded share vs cross-ship aggregate).

## Seed-paired arm deltas — repair signal on the held-out leg

Δ(hygiene_cycle − spike_decay) medians on all three shared fields
(recorded_onsets, campaign_positives, infections_total) are 0–2 at every
θ, q05–q95 straddling zero (50 pairs/row): the repair's dry-floor deposit
suppression is **not measurable on the GM leg** at this sample. The
DELTA-REVERSAL clause did not fire (needs positive medians on all three
fields — none; HAND-AB's DP read stands).

## imports:3 diagnostic (labelled, non-scoring)

θ 2.37e11 × hygiene_cycle, 50 seeds: **P(takeoff) = 1.0** (vs 0.80 at
imports 1 — 10 fizzle→ignition class flips), positives median 113
[89, 129] — the fatter import tail lifts the entire q05 tail from 1 to
89 and lands H1 with a tight envelope. Seed-paired vs the imports-1 row:
Δ positives −12, Δ infections_total −21 (baseline minus armed). The "one
import too few" probe is supported: ignition, not transmission size, is
the dominant residual at imports 1.

## Measured / inferred / hypothesis

- **Measured:** everything above — all cells at `591d21b1`, designs frozen
  before any cell ran, 0 audit failures.
- **Inferred:** the residual ordering — (a) asymptomatic composition
  (H2), ~10× miss, largest single defect; (b) imports/early-contact
  ignition tail, rescued fully by imports:3; (c) count dispersion —
  median lands but the ignited-seed spread still runs ~35→131.
- **Hypothesis:** whether the H2 miss is a detection-channel defect
  (day-20 screen reads what the model calls symptomatic) or a
  natural-history defect (the model truly emits fewer asymptomatic
  courses) — this readout does not separate them; it re-orders the
  queued work either way.
