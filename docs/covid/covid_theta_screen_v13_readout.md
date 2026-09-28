# COVID-THETA-V13 readout — re-admission under capped reach: the band shifts to {1.78e11 … 5.62e11}, and the clause still fails at every admissible Θ, passing only at the boundary anchor

Measured at `edb7fc41` (v13 design files merged at `d424673d`, PR #756; image
`picard-campaign:covid-theta-v13-edb7fc41`, digest `sha256:43bf8d1d…`, jobdef
`picard-covid-boarding-screen:28`). Operative engine difference vs v12:
COVID-EXPOCAP-01 (PR #755) — the per-shedder per-epoch contact budget is
default-on for catalogued cruise platforms, so the v12 admissible set
{1.33e11..4.22e11} was admitted under unbounded reach and went stale. v13
re-runs the identical lattice and declared replay on the current default
engine; the design diff vs v12 shows only the design id and the
`parent_design` chain pointer.

Engine-drift check (cap signature, reported not thresholded per the v13
declaration): at the bracket endpoints, seed-paired vs the v12 cells, the
per-epoch budget compresses outbreaks as declared — among seeds that take
off in both campaigns, median recorded_onsets drops to 0.72× of v12 at Θ
1e11 (130 → 89, 72 seeds) and 0.82× at Θ 1e12 (302 → 274, 115 seeds);
takeoff class flips on 18/200 and 23/200 seeds respectively. See
`covid_theta_screen_v13_pairs.csv` (all 1,800 cells paired).

Five submissions on AWS Batch EC2 Spot, jobdef revision 28:

| stage | design | cells | array | prefix |
|-------|--------|------:|-------|--------|
| canary | `covid_theta_screen_v13` | 60 | `f81cdf97` / `d9f9f7a9` / `a28aaac2` (20 cells each at Θ 1e11, 3.16e11, 1e12) | `campaign/covid_theta_screen_v13/edb7fc41/` |
| 1 — Θ lattice (generic voyages) | `covid_theta_screen_v13` | 1,800 | `f77b46f2-28f7-4e73-83ee-995cd4f01085` | `campaign/covid_theta_screen_v13/edb7fc41/` |
| 2 — declared replay, clause re-measure | `covid_theta_screen_v13_stage2` | 160 | `7759da86` (Θ1e9 anchor canary, 20) + `a04fcadb-5474-4fdf-a99b-8ba915a918db` (140) | `campaign/covid_theta_screen_v13_stage2/edb7fc41/` |

Canaries clean: stage-1 canary 60/60 with intact contract (takeoff-seed
compression ~30–60% vs the same 20 v12 seeds visible at all three points);
stage-2 Θ1e9 anchor row all 20 cells carry `index_onset_day = −1.0` and
`index_shedding_at_day0 = true`; the QUAR-ATTR-V2 figure of record
re-measures top-seed 3,262 infections / 0.8790 attack (3262/3711) and
mass-near-197 0.14 vs 0.09 in v12.

## 1. Stage 1 — fleet-shape surface, same lattice, capped reach

Selector (frozen, verbatim from v12/rebase_01): median recorded attack ∈
[0.0005, 0.008], IQR overlaps [0.0003, 0.015], mean ≤ 0.06 over 200 generic
voyages per Θ (seed base 20201001, 168-epoch voyages). covid.H3 anchor:
median 0.002, IQR 0.0003–0.015, mean 0.037.

| Θ | median rec. attack | IQR | mean | P(takeoff) | P(r≥.015) | P(r≥.10) | P(r≤.01) | rec q10/q50/q90 | fleet_shape |
|---|------|------|-----:|-----:|-----:|-----:|-----:|------------|:-----------:|
| 1e11 | 0.00027 | [0, 0.0140] | 0.0137 | 0.40 | 0.24 | 0.015 | 0.69 | 0 / 0.00027 / 0.050 | fail (floor) |
| 1.33e11 | 0.00027 | [0, 0.0166] | 0.0156 | 0.41 | 0.26 | 0.03 | 0.685 | 0 / 0.00027 / 0.061 | fail (floor) |
| 1.78e11 | 0.00081 | [0, 0.0228] | 0.0184 | 0.475 | 0.31 | 0.04 | 0.66 | 0 / 0.00081 / 0.061 | **PASS** |
| 2.37e11 | 0.00283 | [0, 0.0286] | 0.0223 | 0.50 | 0.345 | 0.06 | 0.61 | 0 / 0.00283 / 0.079 | **PASS** |
| 3.16e11 | 0.00472 | [0, 0.0372] | 0.0257 | 0.55 | 0.37 | 0.08 | 0.60 | 0 / 0.00472 / 0.088 | **PASS** |
| 4.22e11 | 0.00728 | [0, 0.0505] | 0.0336 | 0.57 | 0.41 | 0.11 | 0.53 | 0 / 0.00728 / 0.122 | **PASS** |
| 5.62e11 | 0.00781 | [0, 0.0610] | 0.0393 | 0.585 | 0.43 | 0.16 | 0.525 | 0 / 0.00781 / 0.138 | **PASS** |
| 7.5e11 | 0.01388 | [0.0003, 0.0769] | 0.0448 | 0.615 | 0.49 | 0.18 | 0.49 | 0 / 0.01388 / 0.144 | fail (ceiling) |
| 1e12 | 0.01832 | [0.0003, 0.0843] | 0.0521 | 0.65 | 0.54 | 0.22 | 0.44 | 0 / 0.01832 / 0.167 | fail (ceiling) |

**Admissible set (stage 1): {1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11}.**
The capped-reach band shifts one lattice notch up at each edge vs v12:
1.33e11 now fails the floor (0.00027) and 5.62e11 now clears the ceiling
(0.00781; v12 read 0.0097). Window edges resolve to lower ∈ (1.33e11,
1.78e11], upper ∈ [5.62e11, 7.5e11). The per-epoch budget flattens the
outbreak tail: the row mean no longer breaches the 0.06 cap anywhere on the
lattice (top row 0.0521 vs v12's 0.0733 at 1e12) and median attack sits
below v12's at every shared Θ. Takeoff probability still climbs
monotonically (0.40 → 0.65); the bimodal no-takeoff mass persists (q10 = 0
at every interior Θ).

Per the frozen stage-2 rule (non-empty admissible set), the clause was
re-measured at all five admissible Θ plus the nearest failing flanks
{1.33e11 below, 7.5e11 above} plus the Θ1e9 QUAR-ATTR-V2 anchor.

## 2. Stage 2 — conditional clause at the admissible points

Declared replay (onset_day −1.0, departure_day 5.0, dwell_weighted,
imports 1, infection_age 6.8, 20 seeds at base 20200205, 768 epochs).
Clause: among takeoff seeds (recorded_onsets ≥ 10), the q05–q95 band of
recorded_onsets contains 197 AND median before_share is within 0.10 of
0.173. Audit invariants hold on all 160 cells (`index_onset_day = −1.0`,
`index_shedding_at_day0`).

| Θ | role | n_takeoff | rec. onsets q05/med/q95 | ∋197? | before_share med [q05,q95] | |Δ| to 0.173 | mass∈[98.5,394] | clause |
|---|------|-----:|----------------------|:-----:|----------------------------|-----------:|:-----:|:------:|
| 1e9 | anchor | 7/20 | 115 / 2,966 / 3,134 | yes | 0.175 [0.065, 0.734] | 0.002 | 0.14 | **PASS** |
| 1.33e11 | flank | 17/20 | 1,987 / 3,432 / 3,544 | no | 0.810 [0.026, 0.973] | 0.637 | 0.00 | FAIL |
| 1.78e11 | admissible | 18/20 | 2,024 / 3,516 / 3,546 | no | 0.835 [0.043, 0.978] | 0.662 | 0.00 | FAIL |
| 2.37e11 | admissible | 17/20 | 1,995 / 3,468 / 3,549 | no | 0.851 [0.118, 0.978] | 0.678 | 0.00 | FAIL |
| 3.16e11 | admissible | 17/20 | 1,797 / 3,484 / 3,563 | no | 0.904 [0.175, 0.979] | 0.731 | 0.00 | FAIL |
| 4.22e11 | admissible | 18/20 | 1,807 / 3,464 / 3,579 | no | 0.855 [0.225, 0.982] | 0.682 | 0.00 | FAIL |
| 5.62e11 | admissible | 19/20 | 1,770 / 3,505 / 3,577 | no | 0.891 [0.236, 0.984] | 0.718 | 0.00 | FAIL |
| 7.5e11 | flank | 18/20 | 1,777 / 3,506 / 3,588 | no | 0.942 [0.341, 0.987] | 0.769 | 0.00 | FAIL |

**The clause fails at every admissible interior Θ**, same outcome as v12 at
a shifted coordinate and a slightly lower mass class: takeoff-seed q05
floors sit at 1,770–2,024 recorded onsets (9–10× the record's 197 vs v12's
11–15×) — the per-epoch budget trims the slowest burns but does not bend
the saturation shape. `before_share` still rises with Θ (0.81 → 0.94 over
the run rows): more transmission pulls the burn earlier into the pre-split
window, the wrong direction as in v12. The only clause pass on the surface
is the Θ1e9 anchor — a fleet-shape-inadmissible boundary row; boundary hits
are reported, never selected.

## 3. Verdict

Under capped reach the fleet-shape window survives and moves to
{1.78e11 … 5.62e11} — but no Θ inside it passes the conditional clause, and
the only Θ that passes the clause is fleet-shape-inadmissible. Per the v13
declaration this is again the "clause passes only at a boundary endpoint"
outcome: inside the window every takeoff seed still burns to
near-saturation, so no transmission-scaling Θ lands ~197 aboard at the
declared geometry. The cap moved WHERE the window sits, not WHAT the
takeoff trajectories do inside it — the residual remains mechanism-shaped.
The Θ axis inside the bracket is exhausted on this engine too.

Cells of record: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v13{,_stage2}/edb7fc41/cells/cells/` (double-nested `cells/` per the entrypoint contract). Surfaces: `covid_theta_screen_v13_surface.csv`, `covid_theta_screen_v13_stage2_surface.csv`, `covid_theta_screen_v13_pairs.csv` (all 1,800 stage-1 cells seed-paired vs v12).
