# COVID-THETA-V15 readout — the v14 lattice + declared DP replay under the repaired presentation draw: band reverts to {1.78e11 … 5.62e11}, clause still fails at every admissible Θ

Measured at `6efec855` (image `picard-campaign:covid-theta-v15-6efec855`,
digest `sha256:19169427…`, jobdef `picard-covid-boarding-screen:45`).
Operative engine difference vs v14: the presentation spend is once per
course (`delivery.presentation_draw_mode = once_per_course`, shipped
default-ON under PRESENT-SHARE-01, PR #825 merged `890bfce3`) — the
declared share is now drawn once at the incubation crossing instead of
re-rolled daily through `NOT_ILL`, and `daily_hazard` survives only as
the labelled baseline arm. The hand line is unchanged
(`delivery.hand_reservoir_mode = hygiene_cycle`). v15 stage 1 re-runs
the identical 9-point eighth-decade lattice single-arm
`once_per_course` (1,800 cells); stage 2 re-runs the declared replay on
the frozen rule's row selection, paired seed-for-seed against the v13
stage-2 surface of record (`edb7fc41`) — the last executed stage-2
surface, since the v14 stage-2 enumeration never submitted.

The stage-2 design declares a single baseline arm
(`arms: [once_per_course]`) because `cell_payload` gates the resolved
`delivery` echo block on `design.arms`: an armless declared design
ships a lean payload with no `presentation_draw_mode` echo, and this
campaign exists precisely to audit that echo.

Campaign gate executed: image at merged SHA → digest-pinned jobdef
(`:45`) → 2-cell canary inspected → nine 200-child stage-1 arrays →
stage-2 anchor-row canary (20 cells) inspected → seven selected-row
arrays. Mid-campaign the us-east-1 Spot CE provisioned zero instances
for >1 h (desired 256, running null) — a capacity drought, not a job
error; per the standing On-Demand convention the same jobdef revision
resubmitted to `picard-analysis-queue` (EC2 On-Demand,
`picard-analysis-compute-ondemand`) and ran clean.

| stage | design | cells | array | prefix |
|-------|--------|------:|-------|--------|
| 1 canary | `covid_theta_screen_v15` | 2 | `153296e3-3f3e-40eb-b0c1-82d941c0e313` (θ3.16e11, seeds 20201001-2; Spot parent `65063e66` terminated in the drought) | `campaign/covid_theta_screen_v15/6efec855/` |
| 1 — Θ lattice (generic voyages) | `covid_theta_screen_v15` | 1,800 | nine 200-cell arrays at INDEX_OFFSET {0,200,…,1600}: `d14031fd` `502caf80` `8929480c` `f5bc75a9` `1e3abdbc` `15a8886c` `ee46fd27` `76da2cdb` `f2560553` | same |
| 2 anchor canary | `covid_theta_screen_v15_stage2` | 20 | `ae3f173d-934c-483c-9c93-3c69015babb7` (Θ1e9, seeds 20200205+) | `campaign/covid_theta_screen_v15_stage2/6efec855/` |
| 2 — selected rows | `covid_theta_screen_v15_stage2` | 140 | seven 20-cell arrays at INDEX_OFFSET {40,60,…,160}: `d7d7c5c8` `fe6529a7` `0155c9f9` `a89ee0d9` `16bb080a` `5577ec9e` `68a8b6f3` | same |

Canaries clean. Stage-1 canary: both cells carry the generic-voyage
contract (no top-level onset/departure day), resolved
`presentation_draw_mode = once_per_course` and `hand_reservoir_mode =
hygiene_cycle`, non-degenerate onsets (105 and 24 recorded at
θ3.16e11). Stage-2 anchor canary: index geometry invariant holds on
every inspected cell (`index_onset_day = -1.0`,
`index_shedding_at_day0 = true`), echoes resolved, and the Θ1e9
re-measurement on seed 20200205 (3,378 infections / 0.9102 attack)
sits beside the QUAR-ATTR-V2 record (3,365 / 0.9068) inside
cross-generation drift.

Readouts: `tools/covid_theta_v15_readout.py` (thin wrapper pinning the
two audit echoes) over the shared v14 engine — streams cells off S3,
scores the frozen selector on interior rows, pairs seed-for-seed vs
v14. `tools/covid_theta_v15_stage2_readout.py` applies the parent's
frozen theta_points rule to the stage-1 surface, audits per-cell index
geometry + echoes, scores the verbatim clause on takeoff seeds, and
pairs vs the v13 stage-2 cells. Committed artifacts:
`covid_theta_screen_v15_surface.csv` and
`covid_theta_screen_v15_pairs.csv`.
1,800/1,800 stage-1 and 160/160 stage-2 cells; 0 audit failures; 0
child failures; no report-immediately trigger fired at either stage.

## 1. Stage 1 — fleet-shape surface, same lattice, repaired presentation draw

Selector (frozen, verbatim from v11/v13/v14): median recorded attack ∈
[0.0005, 0.008], IQR overlaps [0.0003, 0.015], mean ≤ 0.06 over 200
generic voyages per Θ (seed base 20201001, 168-epoch voyages). Interior
rows only are admissible; the 1e11/1e12 endpoints verify the bracket.

| Θ | median rec. attack | IQR | mean | P(takeoff) | P(r≥.015) | P(r≥.10) | P(r≤.01) | rec q10/q50/q90 | fleet_shape |
|---|------|------|-----:|-----:|-----:|-----:|-----:|------------|:-----------:|
| 1e11 | 0.00027 | [0, 0.0112] | 0.0113 | 0.42 | 0.23 | 0.01 | 0.74 | 0 / 1 / 156 | fail (floor) |
| 1.33e11 | 0.00040 | [0, 0.0171] | 0.0133 | 0.48 | 0.26 | 0.01 | 0.69 | 0 / 1.5 / 179 | fail (floor) |
| 1.78e11 | 0.00108 | [0, 0.0224] | 0.0155 | 0.47 | 0.285 | 0.02 | 0.66 | 0 / 4 / 194 | **PASS** |
| 2.37e11 | 0.00337 | [0, 0.0234] | 0.0192 | 0.515 | 0.335 | 0.045 | 0.62 | 0 / 12.5 / 255 | **PASS** |
| 3.16e11 | 0.00431 | [0, 0.0294] | 0.0222 | 0.525 | 0.365 | 0.055 | 0.595 | 0 / 16 / 290 | **PASS** |
| 4.22e11 | 0.00552 | [0, 0.0410] | 0.0266 | 0.55 | 0.395 | 0.09 | 0.575 | 0 / 20.5 / 336 | **PASS** |
| 5.62e11 | 0.00687 | [0, 0.0472] | 0.0318 | 0.57 | 0.435 | 0.11 | 0.525 | 0 / 25.5 / 440 | **PASS** |
| 7.5e11 | 0.01172 | [0.0002, 0.0577] | 0.0370 | 0.605 | 0.48 | 0.155 | 0.495 | 0 / 43.5 / 467 | fail (ceiling) |
| 1e12 | 0.01603 | [0, 0.0752] | 0.0438 | 0.645 | 0.50 | 0.175 | 0.475 | 0 / 59.5 / 493 | fail (ceiling) |

**Admissible set (stage 1): {1.78e11, 2.37e11, 3.16e11, 4.22e11,
5.62e11}** — one lattice notch up at each edge vs the pre-repair v14
band {1.33e11 … 4.22e11}, i.e. a reversion to the v13 coordinates:
1.33e11 falls back under the floor (0.00040 vs 0.0005; v14 0.00054)
and 5.62e11 clears the ceiling again (0.00687; v14 0.00808). Window
edges resolve to lower ∈ (1.33e11, 1.78e11], upper ∈ [5.62e11,
7.5e11). The direction is the repair's signature: with presentation
drawn once per course, ~31% of courses never present, so recorded
counts sit lower at a given transmission scale — the fleet-shape
median floor needs one notch more Θ to clear. The bimodal no-takeoff
mass persists (q10 = 0 at every Θ); mean attack stays under the 0.06
cap everywhere (top row 0.0438); the interior fail sides are clean
(floor rows below, ceiling rows above — the band is a bounded interior
window, not boundary-clipped).

## 2. Seed-paired deltas vs the v14 cells

All 1,800 cells paired by (theta, seed) to the pre-repair v14 surface
(`covid_theta_screen_v15_pairs.csv`). Per-row paired recorded_onsets:
median delta ≈ 0 at every Θ (0 to −6) — the median seed is still a
no-takeoff zero on both sides, so the shape move lives in the tails:
the q05 leg drops −31 → −108 across the lattice (deeper fizzle/zero
floors under once-per-course presentation) while q95 holds ~0–3 and
takeoff-class flips run 1–5/200. `suppression_candidate` is False at
every row — the repair does not suppress takeoff mass; it trims the
recorded-onset tail of the ignited voyages exactly as the mechanism
predicts.

## 3. Stage 2 — declared Diamond Princess replay (frozen rule)

The parent's frozen rule (a) selected: Θ1e9 anchor (always) + nearest
non-admissible flanks {1.33e11, 7.5e11} + the five admissible interior
rows — 8 rows × 20 seeds = 160 declared-replay cells (768 epochs,
index onset day −1, shedding at day 0, imports 1, seeds @20200205).
Rows 1e11 and 1e12 stay unrun and unmerged per the candidate-universe
declaration. Clause (verbatim): among takeoff seeds (recorded_onsets
≥ 10), the q05–q95 band of recorded_onsets contains 197 AND the
takeoff-seed median before_share is within 0.10 of 0.173; scored only
when ≥ 5 takeoff seeds.

| Θ | role | takeoff | rec q05/med/q95 | count leg | before_share med [q05,q95] | inf med | mass≈T1 | clause |
|---|------|-----:|----------------------|:-----:|----------------------------|-----------:|:-----:|:------:|
| 1e9 | anchor | 10/20 | 153 / 1,882 / 2,438 | yes | 0.090 [0.004, 0.916] | 2,695 | 0.10 | PASS |
| 1.33e11 | flank | 19/20 | 1,743 / 2,546 / 2,604 | no | 0.735 [0.055, 0.984] | 3,559 | 0.00 | FAIL |
| 1.78e11 | admissible | 19/20 | 1,735 / 2,576 / 2,619 | no | 0.873 [0.214, 0.982] | 3,580 | 0.00 | FAIL |
| 2.37e11 | admissible | 20/20 | 1,739 / 2,578 / 2,618 | no | 0.904 [0.275, 0.987] | 3,588 | 0.00 | FAIL |
| 3.16e11 | admissible | 20/20 | 1,610 / 2,591 / 2,641 | no | 0.951 [0.467, 0.985] | 3,597 | 0.00 | FAIL |
| 4.22e11 | admissible | 19/20 | 1,471 / 2,596 / 2,630 | no | 0.944 [0.594, 0.986] | 3,601 | 0.00 | FAIL |
| 5.62e11 | admissible | 19/20 | 1,487 / 2,588 / 2,639 | no | 0.957 [0.466, 0.985] | 3,609 | 0.00 | FAIL |
| 7.5e11 | flank | 19/20 | 1,444 / 2,596 / 2,639 | no | 0.955 [0.573, 0.988] | 3,611 | 0.00 | FAIL |

**The clause fails at every admissible interior Θ** — the same verdict
v13 delivered under capped reach, at one magnitude class up: takeoff
seeds still saturate (q05 floors 1,444–1,743 recorded onsets, 7–9× the
record's 197) and before_share medians run 0.73–0.96, rising with Θ as
in v13. The anchor is again the only pass on the surface — a
fleet-shape-inadmissible boundary row, reported never selected.

### Seed-paired deltas vs the v13 stage-2 cells

Paired by (theta, seed) to `edb7fc41` (20/20 per row): median
recorded_onsets deltas run **−751 to −938** across the lattice rows —
the once-per-course spend removes ~800 median recorded onsets per
ignited seed, the largest mechanism-level move the replay surface has
ever registered. But the residual is an order of magnitude deeper than
the repair's reach: the paired medians land at ~2,550–2,600 recorded
onsets where the clause wants ~197, and the q95 leg even spreads
upward (+1,882…+2,587 at most rows) because fewer presentations re-time
quarantines differently per seed. The repair moved the recorded mass
measurably and in the intended direction — it did not bend the
saturation shape.

## 4. Verdict

Under the repaired presentation draw the fleet-shape window survives
and reverts to the v13 coordinates {1.78e11 … 5.62e11} — but no Θ
inside it passes the conditional clause, and the only Θ that passes
the clause is the fleet-shape-inadmissible Θ1e9 anchor. Three engine
generations have now scored this bracket (v13 capped reach, v14
rebuilt hand line, v15 once-per-course presentation); the band has
moved a notch in each direction while the takeoff-trajectory residual
stays in the same 7–17× mechanism-shaped class. **The presentation
defect was real, its repair measurably moved the replay surface, and
the DP clause failure survives it — the residual is not the
presentation channel.** Per the standing interpretation the failure
remains mechanism-shaped, not axis-shaped; covid.H1/H2/H5 stay held
out and the live suspects are the declared ring-cap / susceptible-pool
mechanism assays (COVID-RINGCAP-V1, COVID-SUSCPOOL-V1), not another Θ
screen.

Cells of record: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v15/6efec855/cells/` (1,800) and `…/covid_theta_screen_v15_stage2/6efec855/cells/` (160). Surfaces: `covid_theta_screen_v15_surface.csv`, `covid_theta_screen_v15_pairs.csv`; stage-2 readout JSON `telemetry_buffer/covid_theta_v15_stage2_readout.json`.
