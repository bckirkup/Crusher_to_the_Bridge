# THETA-REFIT-01 bracket refine — (1e6, 1e7) interior: WINDOW-EMPTY-ORDERED, certified

> **Status:** Findings (2026-10-04). Campaign measured at `8f926382`
> (image `picard-campaign@sha256:f19d78be…` / tag
> `campaign-e0d43979-refit-bracket`, jobdef `picard-covid-boarding-screen:52`,
> queue `picard-analysis-queue`, prefix
> `campaign/covid_theta_refit_bracket_v1/8f926382/cells/`).

The floor falsifier (`covid_theta_refit_floor_v1_readout.md`) measured
the count leg passing at Θ1e6 ([149, 760] ∋ 197) while the timing leg
failed below-side (0.051 < 0.073) — the falsifier's projected
mechanism-shaped count floor was itself falsified, and the clause was
revealed as squeezed on two different legs in opposite directions. This
design locates the two leg-crossings inside the (1e6, 1e7) decade and
asks whether any θ satisfies both legs at once.

Design `picard_framework/runs/covid_theta_refit_bracket_v1_design.json`:
5 interior Θ rows {1.4e6, 2e6, 3.16e6, 5.62e6, 7.9e6} × 20 seeds = 100
cells, single `D0_declared` arm at the verbatim `diamond_princess_2020`
replay contract under shipped defaults (caregiver on, propensity party),
the v11-lineage clause and the bracket verdict grammar (LOCATED /
WINDOW-EMPTY-ORDERED / WINDOW-EMPTY-INTERLEAVED / SUB-IGNITION) frozen
in `admissibility` before any cell ran. Submitted as one 100-cell array
(`1e1b3b31`) on the floor image + this design file. 100/100 cells
SUCCEEDED, zero audit failures.

## Clause scorecard (per row, takeoff-conditional)

| Θ | takeoff | rec q05/med/q95 | before_share med [q05,q95] | count leg | timing leg | clause |
|--:|--------:|------------------|---------------------------|:---------:|:----------:|:------:|
| 1.4e6 | 19/20 | 366 / 420 / 840 | 0.064 [0.016, 0.149] | FAIL | FAIL | FAIL |
| 2e6 | 19/20 | 285 / 460 / 930 | 0.066 [0.021, 0.201] | FAIL | FAIL | FAIL |
| 3.16e6 | 19/20 | 399 / 511 / 854 | 0.059 [0.020, 0.166] | FAIL | FAIL | FAIL |
| 5.62e6 | 19/20 | 492 / 589 / 785 | 0.069 [0.022, 0.178] | FAIL | FAIL | FAIL |
| 7.9e6 | 19/20 | 496 / 634 / 1,540 | 0.075 [0.032, 0.231] | FAIL | pass | FAIL |

Boundary rows (already of record): Θ1e6 — 19/20, 149/331/760, bshr
0.051, count PASS / timing FAIL; Θ1e7 — 19/20, 523/704/2,037, bshr
0.097, count FAIL / timing pass.

## The leg map — two crossings, ordered against the clause

- **θ_c (count-leg crossing) ∈ (1e6, 1.4e6)** — narrow. The count
  band's q05 edge climbs off 197 almost immediately above the floor:
  149 → 366 between 1e6 and 1.4e6, then 285 / 399 / 492 / 496 → 523
  at 1e7. The count leg fails on all five interior rows and all nine
  lattice rows; the Θ1e6 pass is the only count-leg pass measured
  anywhere on the shipped-default tree.
- **θ_t (timing-leg crossing) ∈ (5.62e6, 7.9e6)** — before_share med
  sits at 0.059–0.069 through the interior and reaches the 0.073 floor
  only at 7.9e6 (0.0754); it keeps climbing to 0.097 at 1e7 and
  overshoots past 0.173+0.10 only above 3.16e8 on the refit lattice.
- **θ_c < θ_t — the admissible window is empty.** Count leg admissible
  only for θ ≲ θ_c < 1.4e6; timing leg admissible only for θ ≳ θ_t >
  5.62e6. The two half-planes are disjoint by nearly an octave, so no
  interior θ can satisfy both legs: below θ_t timing fails; above θ_c
  count fails. Within the measured resolution this is (b)
  WINDOW-EMPTY-ORDERED — every count-leg fail sits at or above every
  timing-leg-only fail, and the ordering is certified, not projected.
- Non-monotone wiggles on the takeoff-conditional stats (q05 366 at
  1.4e6 vs 285 at 2e6; bshr 0.059 at 3.16e6 between 0.066/0.069) are
  seed-level noise on 19 takeoff cells — no leg flip rides on them.

## Witnesses

| witness | values |
|---------|--------|
| `delivery.caregiver.mode` / propensity mode | `on` / `party` — 100/100 echoes |
| `propensity_draw.units_drawn` med | 2,089 on every row |
| caregiver route, pooled aboard_window | 122 / 116 / 124 / 135 / 138 by row (floor probe: 105; 1e7: 141) |
| caregiver route, pooled during_quarantine | 0 on every row |
| `mass_near_197` | 0.211 / 0.263 / 0.053 / 0.000 / 0.000 — falls from 0.474 at 1e6 to 0 at 5.62e6+: the band sits tightest around 197 exactly at the floor and lifts off |
| takeoff margin | 19/20 on every row — ignition stable across the bracket |

Seed-paired deltas (medians, vs the two boundaries): vs Θ1e6 —
+108/+99/+202/+230/+256 recorded onsets, +0.003/+0.005/+0.026/+0.025/
+0.041 before_share by row; vs Θ1e7 — −288/−250/−199/−138/−57 recorded,
−0.047/−0.040/−0.036/−0.032/−0.005 before_share.

## The verdict: WINDOW-EMPTY-ORDERED

No row clause-passes and the leg-failures order cleanly: the count leg
is the binding failure across the whole interior (all five rows), and
the only timing pass in the bracket (7.9e6) sits where the count leg
fails hardest short of the 1e7 wall. The certified statement after the
floor probe + bracket: **the v11 clause passes nowhere on [1e6, 1e9]
under shipped defaults — 15 measured rows spanning ~3 decades, every
one failing at least one leg, with the two legs' admissible half-planes
provably disjoint.** Below 1e6 the timing leg only worsens toward
fizzle (before_share falls; the takeoff margin approaches the <5-seed
unscored region), so the clause is unreachable in the detuning
direction as well.

The falsifier's intended reading — "the count floor is mechanism-set"
— is refined, not confirmed: the count band does reach 197, once, at
1e6. What the measurement actually shows is stronger and different in
kind: the clause's two legs demand mutually exclusive transmission
rates — the count wants the band's lower edge at ≤197 (which forces θ
low enough that the outbreak arrives too late), while the timing wants
enough pre-split mass (which forces θ high enough that the band lifts
off 197 entirely). The residual is **clause-shaped**, not θ-shaped and
not mechanism-shaped: the anchor itself — the 197 figure, the
0.173 share, the takeoff-conditional scoring — is now the open
question under CAREGIVER-V1, exactly where the refit verdict left it,
but now proven rather than projected.

## Run note

One 100-cell array, indices 0–99, `picard-analysis-queue`, ~2h wall
(CE warm from the floor row; ~60 concurrent children). Zero audit
failures. The overlay image adds only the design file to the floor
image, so cell engine semantics are identical to the refit generation.
