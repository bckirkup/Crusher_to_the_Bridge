# COVID-THETA-V12 readout — bisection over (1e11, 1e12): the fleet-shape window is real, but the conditional clause fails at every admissible Θ and passes only at the boundary anchor

Measured at `f42901aa` (v12 design files merged at `51285178`; image
`covid-theta-v12-f42901aa`, digest `sha256:8da85601…`, jobdef
`picard-covid-boarding-screen:27`). Engine-path drift check: all 400
seed-paired endpoint cells (Θ 1e11 and 1e12 × 200 seeds) are byte-identical
in `infections_total`, `attack_rate` and `recorded_onsets` to the rebase_01
cells at `f280e348` — the default engine path did not move between the two
campaigns (commits in between are flu/noro-arm or additive; see
`covid_theta_screen_v12_pairs.csv`).

Three submissions on AWS Batch EC2 Spot, jobdef revision 27:

| stage | design | cells | array | prefix |
|-------|--------|------:|-------|--------|
| bracket canary | `covid_theta_screen_v12` | 60 | `fd4ed3c2` / `3970146b` / `1b2137e5` (20 cells each at Θ 1e11, 3.16e11, 1e12) | `campaign/covid_theta_screen_v12/f42901aa/` |
| 1 — Θ bisection (generic voyages) | `covid_theta_screen_v12` | 1,800 | `6bd58b25-1b7e-48a8-8585-99313cdbfab8` | `campaign/covid_theta_screen_v12/f42901aa/` |
| 2 — declared replay, clause re-measure | `covid_theta_screen_v12_stage2` | 160 | `f3b21376` (Θ1e9 anchor canary, 20) + `e252d350-d5e2-40a6-b35c-e1212ec7e2d0` (140) | `campaign/covid_theta_screen_v12_stage2/f42901aa/` |

Canaries clean: stage-1 bracket canary byte-identical to rebase_01 at
matched seeds (0/60 failures; generic specs carry no declared
onset_day/departure_day/molecular_ascertainment_start_day). Stage-2 Θ1e9
anchor row: all 20 cells carry `index_onset_day = −1.0` and
`index_shedding_at_day0 = true`; the QUAR-ATTR-V2 figure of record
re-measures top-seed 3,365 infections / 0.9068 attack (3365/3711) and
mass-near-197 0.09 vs 0.09 on record.

## 1. Stage 1 — fleet-shape surface, bisection lattice

Selector (frozen, verbatim from v11/rebase_01): median recorded attack ∈
[0.0005, 0.008], IQR overlaps [0.0003, 0.015], mean ≤ 0.06 over 200 generic
voyages per Θ (seed base 20201001, 168-epoch voyages). covid.H3 anchor:
median 0.002, IQR 0.0003–0.015, mean 0.037.

| Θ | median rec. attack | IQR | mean | P(takeoff) | P(r≥.015) | P(r≥.10) | P(r≤.01) | rec q10/q50/q90 | fleet_shape |
|---|------|------|-----:|-----:|-----:|-----:|-----:|------------|:-----------:|
| 1e11 | 0.0002695 | [0, 0.0168] | 0.02471 | 0.41 | 0.28 | 0.10 | 0.69 | 0 / 0.0002695 / 0.0978 | fail (floor) |
| 1.33e11 | 0.0005389 | [0, 0.0265] | 0.02881 | 0.45 | 0.32 | 0.11 | 0.64 | 0 / 0.0005389 / 0.103 | **PASS** |
| 1.78e11 | 0.0005389 | [0, 0.0249] | 0.03192 | 0.47 | 0.33 | 0.12 | 0.59 | 0 / 0.0005389 / 0.138 | **PASS** |
| 2.37e11 | 0.001886 | [0, 0.0426] | 0.03819 | 0.49 | 0.38 | 0.14 | 0.60 | 0 / 0.001886 / 0.148 | **PASS** |
| 3.16e11 | 0.003638 | [0, 0.0469] | 0.04387 | 0.51 | 0.40 | 0.17 | 0.57 | 0 / 0.003638 / 0.17 | **PASS** |
| 4.22e11 | 0.006198 | [0, 0.0678] | 0.05167 | 0.56 | 0.42 | 0.21 | 0.56 | 0 / 0.006198 / 0.185 | **PASS** |
| 5.62e11 | 0.009701 | [0, 0.068] | 0.05678 | 0.56 | 0.45 | 0.21 | 0.50 | 0 / 0.009701 / 0.218 | fail (ceiling) |
| 7.5e11 | 0.01091 | [0, 0.089] | 0.06555 | 0.62 | 0.47 | 0.23 | 0.49 | 0 / 0.01091 / 0.229 | fail (ceiling) |
| 1e12 | 0.01536 | [0, 0.0974] | 0.0733 | 0.61 | 0.51 | 0.24 | 0.47 | 0 / 0.01536 / 0.259 | fail (ceiling) |

**Admissible set (stage 1): {1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11}.**
The rebase_01 bracket is real and resolves to eighth-decade precision: the
window's lower edge sits in (1e11, 1.33e11], its upper edge in
[4.22e11, 5.62e11) — ~0.1 decade on each side. Median recorded attack climbs
monotonically through the H3 window (0.00054 → 0.0062); the q10 of the
recorded distribution stays 0 at every interior Θ (the bimodal
no-takeoff mass persists — takeoff probability reaches only 0.45–0.56 in the
generic arm).

Per the frozen stage-2 rule (non-empty admissible set), the clause was
re-measured at all five admissible Θ plus the nearest failing flanks
{1e11 below, 5.62e11 above} plus the Θ1e9 QUAR-ATTR-V2 anchor.

## 2. Stage 2 — conditional clause at the admissible points

Declared replay (onset_day −1.0, departure_day 5.0, dwell_weighted,
imports 1, infection_age 6.8, 20 seeds at base 20200205, 768 epochs).
Clause: among takeoff seeds (recorded_onsets ≥ 10), the q05–q95 band of
recorded_onsets contains 197 AND median before_share is within 0.10 of
0.173. Audit invariants hold on all 160 cells (`index_onset_day = −1.0`,
`index_shedding_at_day0`, `index_geometry_pass_fraction` 1.0).

| Θ | role | n_takeoff | rec. onsets q05/med/q95 | ∋197? | before_share med [q05,q95] | |Δ| to 0.173 | mass∈[98.5,394] | clause |
|---|------|-----:|----------------------|:-----:|----------------------------|-----------:|:-----:|:------:|
| 1e9 | anchor | 11/20 | 85 / 862 / 3,164 | yes | 0.087 [0.006, 0.677] | 0.086 | 0.09 | **PASS** |
| 1e11 | boundary | 20/20 | 2,966 / 3,471 / 3,523 | no | 0.699 [0.144, 0.961] | 0.526 | 0.00 | FAIL |
| 1.33e11 | admissible | 20/20 | 2,877 / 3,500 / 3,534 | no | 0.789 [0.384, 0.969] | 0.616 | 0.00 | FAIL |
| 1.78e11 | admissible | 20/20 | 2,693 / 3,496 / 3,538 | no | 0.876 [0.551, 0.974] | 0.703 | 0.00 | FAIL |
| 2.37e11 | admissible | 20/20 | 2,563 / 3,468 / 3,551 | no | 0.905 [0.568, 0.976] | 0.732 | 0.00 | FAIL |
| 3.16e11 | admissible | 20/20 | 2,407 / 3,484 / 3,570 | no | 0.921 [0.604, 0.981] | 0.748 | 0.00 | FAIL |
| 4.22e11 | admissible | 20/20 | 2,393 / 3,513 / 3,564 | no | 0.920 [0.822, 0.981] | 0.747 | 0.00 | FAIL |
| 5.62e11 | flank | 20/20 | 2,190 / 3,390 / 3,565 | no | 0.956 [0.737, 0.982] | 0.783 | 0.00 | FAIL |

**The clause fails at every admissible interior Θ** in the same ~17× mass
class as v11 (197 × 17 ≈ 3,350): every takeoff seed saturates at
~2,200–3,580 recorded onsets (93–97% attack among takeoff seeds), so the
q05 floor alone is 11–15× the record. `before_share` runs 0.70–0.96 and
climbs monotonically with Θ — more transmission pulls the burn earlier
into the pre-split window, exactly the wrong direction. The only clause
pass on the whole surface is the Θ1e9 anchor — a boundary row whose
generic arm fails the stage-1 fleet-shape floor (rebase_01 stage-A: median
0 at Θ1e9). Boundary hits are reported, never selected.

## 3. Verdict

The H3-admissible fleet-shape window exists — {1.33e11 … 4.22e11} — but no
Θ inside it passes the conditional clause, and the only Θ that passes the
clause is fleet-shape-inadmissible. Per the v12 declaration this is the
"clause passes only at a boundary" outcome: the window and the takeoff
trajectory decouple — inside the window every takeoff seed burns to
near-saturation, so no transmission-scaling Θ can land 197 aboard at the
declared geometry. The takeoff transition sits above the whole fitted
band (generic P(takeoff) 0.41–0.62 at the admissible Θs vs the replay's
20/20 saturation), so the residual is a mechanism-shaped gap, not a
Θ-shaped one. The Θ axis is exhausted inside the bracket: the next move is
a mechanism, not a finer Θ.

Cells of record: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v12{,_stage2}/f42901aa/cells/cells/` (double-nested `cells/` per the entrypoint contract). Surfaces: `covid_theta_screen_v12_surface.csv`, `covid_theta_screen_v12_stage2_surface.csv`, `covid_theta_screen_v12_pairs.csv` (seed-paired drift table vs rebase_01 at the two bracket endpoints).
