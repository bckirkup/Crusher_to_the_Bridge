# COVID-GM-RESCORE-02
**Date:** 2026-10-08
**Commit:** 6bb0e996
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 6bb0e996 (canary only — 20 of 300 scoring cells + 0 of 50
diagnostic; the fleet runs only on the author's go-ahead)

Re-score of `greg_mortimer_2020` (held out) under the post-DP-era engine —
image built at merge commit `6bb0e996` (design PR #970), against the same
anchors measured at `591d21b1` by `COVID-GM-RESCORE-01`. Lattice frozen
before any cell ran, grammar verbatim from v1: scenario as-declared ×
`hand_reservoir_mode` ∈ {hygiene_cycle (baseline, empty overrides),
spike_decay (labelled baseline)} × θ ∈ {1e11, 2.37e11, 1e12} × 50 seeds
@20200205 = 300 cells; plus the declared imports:3 diagnostic (50 cells).
Designs `picard_framework/runs/covid_gm_rescore_v2{,_imports3}_design.json`;
campaign `campaigns/covid/gm_rescore_02/`; readout
`tools/covid_gm_rescore_readout.py` (+ campaign pooler
`campaigns/covid/gm_rescore_02/readout.py`); jobdef
`picard-covid-gm-rescore-02` (rev 1 single canary `143e6ed8`, rev 2
20-cell array `2d485e4d`) on image `sha256:c8325d40…`; cells under
`campaign/covid_gm_rescore_02/6bb0e996…/<block>/` (no per-SHA subdir —
blocks self-describe; prefix is campaign-name-scoped).

New since v1: the audit invariants carry the post-drift shipped-echo
witnesses (`delivery.caregiver` resolved, `delivery.participation_propensity`
resolved-or-null, `delivery.presentation_draw_mode == once_per_course`) on
top of the v1 set. The v2-vs-v1 read is distribution-level per (θ, arm)
row on identical seed lists — per-seed bit-pairing is not claimed because
engine drift re-rolls RNG streams wherever new machinery reaches.

## Canary: anchor row θ 2.37e11 × hygiene_cycle, seeds 20200205–224 (20/20, 0 audit failures)

| read | v1 same row (50 seeds) | v2 canary (20 seeds) |
|---|---|---|
| P(takeoff ≥10 recorded onsets) | 0.80 | **1.00** |
| campaign positives med [q05–q95] | 105 [1, 131] | **116 [56, 133]** |
| H1 lands (median ∈ [64,256], interval ∋ 128) | yes (envelope-only, q05 at 1) | **yes (q05 lifts 1 → 56)** |
| asym share med [q05–q95] | 0.064 | 0.252 [0.168, 0.333] |
| H2 hit (0.81 ± 0.10) | — | — |

The single-cell Batch↔dev-venv check is bit-identical (seed 20200205:
58 onsets, 123/217, asym 0.252, 187 infections) — toolchain parity holds.

## Read (canary-grade, provisional)

- **The ignition tail closed.** Every one of the 20 canary seeds reaches
  ≥10 recorded onsets — v1's ~1-in-5 fizzle is absent on this block and
  the q05 floor lifted 1 → 56 positives. On canary evidence the
  imports/early-contact residual (v1 residual class b) is resolved by
  machinery shipped since 591d21b1 — most plausibly the R3
  service-door-drop channel keeping early-seed secondary pressure alive
  under SOP-017; attribution is hypothesis, not yet measured.
- **H1 lands tighter.** Median 116 vs v1's 105, interval [56, 133] vs
  [1, 131] — the envelope now sits inside the record's reach rather than
  straddling a dead tail.
- **H2 still misses, but moved ~3×.** Asym share median 0.252 vs v1's
  0.064 — direction consistent with once_per_course + age-graded
  presentation repairing part of the ~10× composition gap (the declared
  v2 probe); still far outside 0.71–0.91, so residual class (a) stands,
  narrowed.
- Verdict grammar so far: the anchor row lands H1 AND misses H2 →
  `mixed` on the 20-seed prefix, same class as v1 with the residual order
  re-sorted (composition now dominates; ignition no longer on the list).

## Open

Fleet = 330 cells (6 scoring blocks' remaining seeds + imports3) —
author's call per the campaign gate. The spike_decay column will say
whether hand physics became load-bearing on GM (v1 measured ~0 deltas);
imports3 says whether the import-rescue still holds now that ignition is
not the binding constraint.
