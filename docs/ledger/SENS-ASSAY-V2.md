# SENS-ASSAY-V2
**Date:** 2026-09-22
**Commit:** b88e0ad
**Pathogens:** sars_cov2_resp
**Status:** declared

Second sensitivity assay for the ~18× conditional-size gap in the COVID
arm, covering the two channels covid_sensitivity_assay_v1 measured it
could not reach: the observational channel (dated-onset bookkeeping,
~3.5× of the gap) and natural history / mixing reach (the ~4.7×
over-burn, attack ~0.95 vs the record's ~712/3,711 ≈ 0.19). Declared in
`picard_framework/runs/covid_sensitivity_assay_v2_design.json` (frozen
before any assay cell ran). Nothing in this entry is a result; it moves
to measured when the canary is read out.

## Declared (before any cell runs)

SENS-ASSAY-V1's A11 arrest bound — crew confined, airborne pool off,
quarantine retimed to day 12, perfect cabin confinement, contact dose
×0.25 — still recorded median 2,868 onsets (q05–q95 [1,363–3,422]) on
takeoff seeds vs the record's 197: the gap is not reachable inside the
transmission layer, so this assay interrogates the two remaining named
suspects. Same declared-replay axis as v1: Θ 4.22e10, the same 20 seeds
(base 20200205), same cell shape — B0 is an exact A0 rerun.

Eleven arms × 20 seeds, 220 cells:

- B0 declared replay — witness; must reproduce A0_declared
  seed-for-seed.
- B1, observational: half of every severity band's `mild` mass moved
  into `subclinical` (onset-ineligible) — the bookkeeping
  counterfactual measuring how much of the over-read is
  classification, not biology.
- B2, symptomatic_fraction 0.69 → 0.40 (confounded biology +
  observation; read as a bound).
- B3, shedding_duration_days 15 → 8 — the infectious-window bound.
- B4, shedding_variance_log10 1.2 → 2.0 — the superspreading-tail
  probe.
- B5/B6, secretor_negative_fraction 0.5 / 0.75 — the effective-
  susceptible-pool bound (sterile innate immunity flagged at init).
- B7, activity_contacts partner rates ×0.5 — reach on the partner
  channel (vs v1's dose-side A6/A7).
- B8, CONTACT-ARCH-02 saturation_hours switched on per activity — the
  per-visit plateau that keeps long dwells from yielding linearly more
  partners.
- B9, B7 + B8 combined.
- B10, the mixed floor (B1 + B2-lite + B3 + B5 + B8): if even the
  combined observational + natural-history + reach bound cannot place
  197 inside the conditional q05–q95, the residual is structural —
  zone-pool well-mixing or the Θ composite — and the next step is
  engine surgery, not parameter assay.

Grammar wired in the same change: the `pathogen_overrides` arm key
(deep-merges {pathogen_id: patch} into the spec-level block, screened
to sars_cov2_resp; reserved `remove`/`add` forms refused) plus the
declared fact that `transmission_overrides.activity_contacts` replaces
the block wholesale, so each contact arm declares the complete block.

Frozen verdict bands identical to v1's: closes_the_gap / load_bearing
(≥50% cut) / partial (20–50%) / inert (<20%) / takeoff_collapse. An
observational annex (zero cells) computes the dated-onset-equivalent
bookkeeping rescale on v1+v2 payloads so both metrics' gaps are
visible.

Pairing caveat carried from the design: every arm here perturbs
profile RNG draws, so seed realisations are not draw-aligned with B0 —
reads are distribution-level, not seed-paired.

## Report immediately if

- any arm's conditional q05–q95 contains 197;
- any arm collapses takeoff below 5/20;
- B10_mixed_floor still over-produces by ~4× or more — the residual is
  then structural (well-mixed zones / Θ composite), not parametric;
- the B0 witness fails to reproduce A0_declared seed-for-seed.
