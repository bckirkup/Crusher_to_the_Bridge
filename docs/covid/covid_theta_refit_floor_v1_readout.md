# THETA-REFIT-01 floor falsifier — Θ1e6 row under shipped defaults: count leg PASSES, timing leg fails (bracket reopens)

> **Status:** Findings (2026-10-04). Campaign measured at `8f49652f`
> (image `picard-campaign@sha256:8f1f116b…` / tag
> `campaign-e0d43979-refit-floor`, jobdef `picard-covid-boarding-screen:51`,
> queue `picard-analysis-queue`, prefix
> `campaign/covid_theta_refit_floor_v1/8f49652f/cells/`).

The refit lattice (`covid_theta_refit_v1_readout.md`) measured
NO-ADMISSIBLE on [1e7, 1e9]: every row fails the count leg on the same
overshoot side (takeoff q05 ≥ 523 > 197), and the frozen grammar declared
that closure is **not a reason to extend downward** — the residual was
reported as mechanism-shaped on the strength of the boundary row. This
design is the cheap falsifier of that extrapolation: one 20-seed row at
Θ1e6, a decade below the lattice floor, on the verbatim
`diamond_princess_2020` replay contract under shipped defaults — to
certify empirically that the count floor is mechanism-set rather than an
unmeasured projection.

Design `picard_framework/runs/covid_theta_refit_floor_v1_design.json`:
1 Θ row × 20 seeds = 20 cells, single `D0_declared` arm (empty
overrides — shipped defaults, caregiver ON), the v11-lineage conditional
clause and the falsifier verdict grammar (FLOOR-CERTIFIED /
FLOOR-CROSSED / SUB-IGNITION) frozen in `admissibility` before any cell
ran. Submitted as one 20-cell array (`ee5360f9`) on a thin overlay image
(`FROM picard-campaign:campaign-e0d43979-refit` + this design file —
engine-identical to the refit generation by construction). 20/20 cells
SUCCEEDED, zero audit failures.

## Clause scorecard (takeoff-conditional)

| Θ | takeoff | rec q05/med/q95 | before_share med [q05,q95] | count leg | timing leg | clause |
|--:|--------:|------------------|---------------------------|:---------:|:----------:|:------:|
| 1e6 | 19/20 | 149 / 331 / 760 | 0.051 [0.014, 0.125] | **PASS** | FAIL | FAIL |

Reference rows: refit Θ1e7 (the boundary this row falsifies) — 19/20,
523/704/2,037, bshr 0.097, count FAIL / timing pass; refit Θ1e9 —
19/20, 1,518/2,321/2,445, bshr 0.452, FAIL/FAIL; CG_OFF — 11/20, q05 10,
band ∋197, share 0.200, PASS.

## What the row measured

- **The count leg passes.** [149, 760] contains 197 — the first and only
  count-leg pass on the shipped-default tree. The projection that the
  floor was mechanism-set (q05 ~450–550 at 1e6) was wrong by ~3×: the
  band's lower edge does reach below 197 exactly one decade under the
  lattice floor. `mass_near_197` = **0.474** (9 of 19 takeoff seeds
  record in [98.5, 394]) — it was 0.000 on all nine refit rows.
- **The timing leg fails below-side.** before_share med 0.051 vs the
  0.073 floor of 0.173±0.10 — at Θ1e6 the outbreak develops too slowly;
  too few onsets land before the split day. This is the second wall the
  refit readout projected (timing already at 0.097 against the floor at
  1e7), now measured.
- **The mechanism was exercised.** Caregiver pooled tallies: aboard
  window 105 (extrapolation of the 141-at-1e7 floor put it at ~100–140
  — the signature persists at the floor), during-quarantine 0. The
  count-band dip below 197 is therefore not a caregiver collapse: the
  route still delivers ~105 infections pre-quarantine, and the recorded
  band still straddles 197 because the band is wide, not because the
  mechanism went quiet.
- **Seed-paired deltas:** vs refit Θ1e7 row −391 med recorded /
  −0.049 before_share (19 pairs); vs Θ1e9 −1,877 / −0.383; vs
  CAREGIVER-ATTR-01 D0 −1,877 / −0.383 (the 1e9 rows are identical); vs
  CG_OFF −1,098 / −0.114 (11 pairs — the off-tree takeoff margin).

## The verdict: spirit-FLOOR-CROSSED — the bracket reopens

The frozen grammar's letter enumerates three outcomes: (a)
FLOOR-CERTIFIED (count fails overshoot-side, q05 > 197), (b)
FLOOR-CROSSED (clause passes, or count reads below-side q95 < 197), (c)
SUB-IGNITION (takeoff < 5). The measured row is none of them exactly —
it is the case the grammar did not write down: **the count leg passes
while the timing leg fails on the other side**. In spirit this is (b):
the boundary extrapolation was wrong — the count band IS reachable —
and the bracket between 1e6 and 1e7 reopens for refine.

What the row rules out and rules in:

- **Ruled out:** "no Θ can pass the count leg under shipped defaults"
  — false at 1e6. The mechanism-shaped-floor reading was a projection
  and is now falsified.
- **Ruled in:** the clause is squeezed on two different legs in
  opposite directions. The count leg passes only below θ_c (where q05
  climbs above 197); the timing leg passes only above θ_t (where
  before_share reaches 0.073). Both crossings sit inside (1e6, 1e7); an
  admissible window exists iff θ_t ≤ θ_c. That ordering question is
  `covid_theta_refit_bracket_v1` (see `covid_theta_refit_bracket_v1_readout.md`).

## Run note

One array job, indices 0–19. All 20 children SUCCEEDED on
`picard-analysis-queue` (Fargate fallback unused); the CE was still
warm from the refit array and the row ran ~45 min wall. The overlay
image adds only the design file to the refit image, so cell engine
semantics are identical to the refit/attribution generation; the audit
found caregiver `on`, propensity `party`, `units_drawn` med 2,089, and
index geometry clean on all 20 cells.
