# COVID-THETA-V14 readout — stage-1 Θ re-admission under the repaired hand line: the band slides one notch down to {1.33e11 … 4.22e11}

Measured at `02740187` (image `picard-campaign:covid-theta-v14-02740187`,
digest `sha256:b5280c72…`, jobdef `picard-covid-boarding-screen:44`).
Operative engine difference vs v13: the rebuilt hand reservoir is
default-ON (`delivery.hand_reservoir_mode = hygiene_cycle`) — practice
variability + drying (PR #804, `d0466064`) plus the wash-resistant
protected compartment and own-environment pool (PR #811, `1c94de2d`).
v14 stage 1 re-runs the identical 9-point eighth-decade lattice on the
current default engine; COVID-HAND-AB-01 (`docs/ledger/COVID-HAND-AB-01.md`)
measured the arm contrast as replay-neutral at Θ 2.37e11 — all arms burn
~96%, fomite = 0 during-quarantine acquisitions, and the two labelled
baselines are byte-identical on the COVID seeds — so stage 1 ran
single-arm `hygiene_cycle` only (1,800 cells); the spike_decay pairing
sees nothing on this scenario.

Campaign gate executed: image at merged SHA → digest-pinned jobdef
(`:44`, which also carries the `--index-offset` command arg `:43`
lacked) → 2-cell canary inspected → nine 200-child arrays.

| stage | design | cells | array | prefix |
|-------|--------|------:|-------|--------|
| canary | `covid_theta_screen_v14` | 2 | `a27e884c-2bb6-433a-9c8e-b65b5d1e109e` (θ3.16e11 hygiene_cycle, seeds 20201001-2) | `campaign/covid_theta_screen_v14/02740187/` |
| 1 — Θ lattice (generic voyages) | `covid_theta_screen_v14` | 1,800 | nine 200-cell arrays at INDEX_OFFSET {0,400,…,3200}: `5db41956` `c58b0b4c` `79f94c22` `751629cd` `ef5e75ae` `aefb6abb` `20a2e1a6` `dc3a69eb` `17b12706` | `campaign/covid_theta_screen_v14/02740187/` |

Canary clean: both cells carry the drawn-incubation generic contract
(`cell.infection_age_days` drawn, no declared onset/departure day, no
ascertainment gate), resolved `delivery.hand_reservoir_mode =
hygiene_cycle`, non-degenerate onsets (110 and 23 recorded).

Readout: `tools/covid_theta_v14_readout.py` streams cell payloads
straight off S3 into `merge_screen` (no full-payload materialization),
scores the frozen selector, takes the admissible set from interior rows
only, and pairs cells seed-for-seed against the v13 stage-1 cells for
suppression-shaped delta detection. Committed artifacts:
`covid_theta_screen_v14_surface.csv` and
`covid_theta_screen_v14_pairs.csv`.
1,800/1,800 cells, 0 audit failures, 0 child failures.

## 1. Stage 1 — fleet-shape surface, same lattice, repaired hand line

Selector (frozen, verbatim from v11/v13): median recorded attack ∈
[0.0005, 0.008], IQR overlaps [0.0003, 0.015], mean ≤ 0.06 over 200
generic voyages per Θ (seed base 20201001, 168-epoch voyages). Interior
rows only are admissible; the 1e11/1e12 endpoints verify the bracket.

| Θ | median rec. attack | IQR | mean | P(takeoff) | P(r≥.015) | P(r≥.10) | P(r≤.01) | rec q10/q50/q90 | fleet_shape |
|---|------|------|-----:|-----:|-----:|-----:|-----:|------------|:-----------:|
| 1e11 | 0.00040 | [0, 0.0472] | 0.0130 | 0.445 | 0.245 | 0.02 | 0.72 | 0 / 1.5 / 175 | fail (floor) |
| 1.33e11 | 0.00054 | [0, 0.0563] | 0.0153 | 0.465 | 0.28 | 0.02 | 0.68 | 0 / 2 / 209 | **PASS** |
| 1.78e11 | 0.00094 | [0, 0.0601] | 0.0182 | 0.49 | 0.32 | 0.035 | 0.655 | 0 / 3.5 / 223 | **PASS** |
| 2.37e11 | 0.00445 | [0, 0.0799] | 0.0224 | 0.52 | 0.35 | 0.075 | 0.605 | 0 / 16.5 / 297 | **PASS** |
| 3.16e11 | 0.00525 | [0, 0.0945] | 0.0260 | 0.54 | 0.375 | 0.075 | 0.585 | 0 / 19.5 / 351 | **PASS** |
| 4.22e11 | 0.00660 | [0, 0.1050] | 0.0311 | 0.555 | 0.405 | 0.12 | 0.575 | 0 / 24.5 / 390 | **PASS** |
| 5.62e11 | 0.00808 | [0, 0.1325] | 0.0373 | 0.575 | 0.45 | 0.14 | 0.51 | 0 / 30 / 492 | fail (ceiling) |
| 7.5e11 | 0.01307 | [0, 0.1531] | 0.0435 | 0.615 | 0.49 | 0.17 | 0.49 | 0 / 48.5 / 568 | fail (ceiling) |
| 1e12 | 0.01576 | [0, 0.1567] | 0.0516 | 0.66 | 0.505 | 0.195 | 0.47 | 0 / 58.5 / 582 | fail (ceiling) |

**Admissible set (stage 1): {1.33e11, 1.78e11, 2.37e11, 3.16e11,
4.22e11}** — the band slides one lattice notch down at each edge vs v13
{1.78e11..5.62e11}: 1.33e11 lifts off the floor (median 0.00054 vs
v13's 0.00027) and 5.62e11 tips over the ceiling (0.00808 vs 0.00781).
Window edges resolve to lower ∈ (1e11, 1.33e11], upper ∈ [4.22e11,
5.62e11). The mechanism signature is mild and broad: recorded medians
rise ~1.2–1.6× across the mid-band (largest at 2.37e11: 0.00283 →
0.00445) while the top tail trims (7.5e11: 0.01388 → 0.01307; 1e12:
0.01832 → 0.01576) and takeoff probability rises ~0.02–0.05 at every Θ
(0.445 → 0.66 across the lattice). The bimodal no-takeoff mass persists
(q10 = 0 at every Θ); mean attack stays under the 0.06 cap everywhere
(top row 0.0516).

## 2. Seed-paired deltas vs the v13 cells

All 1,800 cells paired by (theta, seed) to the v13 surface
(`covid_theta_screen_v14_pairs.csv`). Per-row paired recorded_onsets:
median delta **0.0 at every Θ** — the median seed is a no-takeoff zero
in both campaigns, so the row-level shape move lives in the upper
quantiles and the takeoff-class boundary, not in a wholesale shift.
Takeoff-class flips run 17–30/200 per Θ (19 at 1e11, 17 at 1.33e11,
19 at 1.78e11, 20 at 2.37e11, 18 at 3.16e11, 25 at 4.22e11, 26 at
5.62e11, 30 at 7.5e11, 24 at 1e12), inside and just above the
stream-reorder band the pairing criterion tolerates (20/200 at 200
seeds). No row shows a suppression-shaped delta (median ratio criterion
|Δ/parent| ≤ −0.5 with flips beyond the band): the rebuilt hand line
adds mild, broad dose on the path it exercises, consistent with
COVID-HAND-AB-01's replay-neutral reading at Θ 2.37e11.

## 3. Report-immediately review

None of the frozen triggers fired:

- window_illusory — interior rows do not fail on one side; the set is
  non-empty with flanks on both edges.
- boundary_only_admissible — no boundary row passes.
- takeoff_transition_outside_bracket — P(takeoff) runs 0.445 → 0.66,
  strictly inside the bracket.
- suppression_shaped_delta — none (§2).
- child failure rate — 0/1,800 (the design's >5% clause never engaged).

Admissibility **did** move the v13 set — reported immediately per the
campaign gate. Stage 2 (declared replay at the admissible points +
nearest failing flanks {1e11, 5.62e11} + the Θ1e9 QUAR-ATTR-V2 anchor)
is eligible under the frozen rule and stays gated on this verdict.
