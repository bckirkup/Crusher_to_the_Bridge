---
status: Design, frozen pre-run (2026-10-08)
pathogens: [sars_cov2_resp]
---

# COVID-GM-RESCORE-02 — held-out Greg Mortimer re-score under post-DP-era physics

Design of record: `picard_framework/runs/covid_gm_rescore_v2_design.json`
(+ sibling `covid_gm_rescore_v2_imports3_design.json`).
Campaign: `campaigns/covid/gm_rescore_02/`.
Prior measurement: `docs/ledger/COVID-GM-RESCORE-01.md` (image `591d21b1`).

## Why re-score

RESCORE-01 measured the held-out hull `mixed`: H1 lands envelope-only
(q05 at 1), the asymptomatic share misses H2's 0.81 ± 0.10 by ~10× on
every row, and imports:3 proved the residual is an ignition defect, not a
transmission-size defect. Since `591d21b1` the DP believability line
landed a stack of default-ON machinery that reaches this voyage; the
question is whether the misses moved and which mechanism class moved them.

Shipped since and load-bearing on an as-declared covid GM replay:
CAREGIVER-V1/SVC-01 + MEAL-SVC-02 `contact_factor_to_host` (R3 service
door-drops under SOP-017), PROPENSITY-V1 party propensity, HOST-AGE-01
age-band susceptibility + symptomatic-fraction (the H2 composition lever),
PRESENT-SHARE-01 `once_per_course` (the ~15× symptomatic re-roll defect
the H2 decomposition surfaced — measured 0→1 asym positives on the GM
detector cell), DEFIANT-ESC-01, ISO-QUARTERS-01. Campaign-arm and
norovirus-scoped machinery does not fire as-declared.

## Frozen contract (identical grammar to RESCORE-01)

- Scenario `greg_mortimer_2020` as-declared, `split_role: held_out`
  (load-verified). 223 aboard, 672 epochs, SOP-017 day 8→27, day-20 screen.
- θ {1e11, 2.37e11, 1e12} — the v13 lattice verbatim (kept for row-pairing;
  THETA-REFIT-01 measured NO-ADMISSIBLE, no successor lattice exists).
- Arms `hygiene_cycle` (shipped, empty overrides) / `spike_decay`
  (labelled baseline). Seeds 20200205+50. 300 scoring cells + 50
  imports:3 diagnostic cells.
- Verdict grammar verbatim: H1 lands = median ∈ [64,256] with q05–q95 ∋
  128; `replays` = anchor row lands H1 AND H2 share ∈ 0.71–0.91;
  `under_fires` / `over_fires` / `mixed` as v1.
- New declared v2 reads: (a) H2 movement direction (once_per_course +
  age-graded presentation should close the ~10× asym miss if that defect
  was presentation-draw-driven); (b) ignition tail survival; (c) envelope
  width under PROPENSITY-V1; (d) v2-vs-v1 row deltas distribution-level —
  per-seed bit-pairing NOT claimed (drift re-rolls RNG streams).
- Audit invariants: v1 set (hand_reservoir_mode echo, seed_ring, 223
  aboard, lattice key) PLUS shipped-echo witnesses — `delivery.caregiver`
  resolved block present, `delivery.participation_propensity` resolved or
  declared-null, `delivery.presentation_draw_mode == once_per_course`.
- Report immediately: anchor loses H1 vs v1; P(takeoff)≈0; asym share
  lands H2; spike−hygiene delta materially nonzero (v1 measured ~0).

## Execution

`campaigns/covid/gm_rescore_02/` on `picard-analysis-queue`, 1 vCPU/2048
MB, ~5 min/cell expected. Blocks: `canary_t2e11_hygiene` (anchor row,
seeds 20200205–224 = 20 cells) canary first — audit invariants green +
non-degenerate voyage, then **STOP AND REPORT** per the campaign gate; the
seven fleet blocks (300 scoring − 20 canary + 50 diagnostic = 330 cells)
run only on the author's go-ahead. The anchor row's 50 payloads pool
canary + `t2e11_hygiene` (seeds 225–254) prefixes.

Readout: `scripts/campaign readout covid/gm_rescore_02 -- --prefix <s3>`
→ `campaigns/covid/gm_rescore_02/readout.py` pools blocks into the flat
staging dirs and runs `tools/covid_gm_rescore_readout.py` for both
designs with each as the other's `--pair-cells`.
