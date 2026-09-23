# COVID Theta screen v11 — stage-1 refinement readout: the admissible set is non-empty — Θ ∈ {3.16e10, 4.22e10, 5.62e10} — an interior band ~0.25 decades wide

> **Status:** Findings (2026-09-22), refine stage 1 complete; stage 2
> declared, not yet run. Campaign `covid_theta_screen_v11_refine`, declared
> in `picard_framework/runs/covid_theta_screen_v11_refine_design.json`.
> **All 1,400 stage-1 cells have run** on AWS Batch at `main` = `79a3ac3`,
> image `picard-campaign:theta-v11-refine-79a3ac3`
> (`sha256:ab3c0026dfb5af45bab59aeeb3f1bab4c02d9c22fcb07348885f7586e6a4b309`),
> job definition `picard-covid-boarding-screen:15`, array job
> `45cfb31d-eb50-4042-9d6d-17499d9a3934` (size 1400) on
> `picard-campaign-queue`. 1,400 of 1,400 children SUCCEEDED, zero failures.
> Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v11_refine/79a3ac3/cells/`.
> Merge: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_theta_screen_v11_refine_design.json --cells
> <cells> --out
> telemetry_buffer/observation_model/covid_theta_screen_v11_refine.json`;
> flat table `docs/covid/covid_theta_screen_v11_refine_surface.csv`. No Theta
> is claimed here; nothing below may be quoted as a fit.

Every figure below is measured at `79a3ac3` inside the campaign image, seeds
`20201001 + k`, k = 0..199 per Θ — the same seed base as the v11 decade
rows, so each refinement row shares the decade rows' per-seed voyage
streams — `diamond_princess_2020` hull, one introduction whose infection
age is drawn from the profile incubation distribution, 168 epochs (7 days,
hourly), no intervention, molecular ascertainment open from embarkation.

## 0. What this run is

The v11 decade-lattice stage 1 (`7660392`, 1,600/1,600) measured an empty
admissible set with the H3 median window bracketed between 1e10 (median
0.00027, floor miss) and 1e11 (median 0.0158, mean 0.075 > 0.06) — readout
`docs/covid/covid_theta_screen_v11_readout.md`. This design re-ran the
IDENTICAL stage-1 cell shape on the eighth-decade interior lattice
{1.33, 1.78, 2.37, 3.16, 4.22, 5.62, 7.5}e10 × 200 seeds = 1,400 cells,
per the user's direction: a tighter grid bought with more runs in the same
session, not a further session. Same worker, same image family, same
frozen fleet_shape_selector, verbatim. Canary before the array: the Θ
3.16e10 row's first 50 seeds (array `04144ec5-dcf6-4582-b780-642afee00d44`,
50/50 SUCCEEDED) — spec audit clean (no `onset_day`/`departure_day`, no
molecular-ascertainment key, 168 epochs, contract unchanged) and the row
non-degenerate (attack 0 → 0.91, takeoff 32/50).

## 1. Refined stage-1 surface — recorded-channel fleet shape vs covid.H3

Selector (frozen, unchanged): median recorded attack rate ∈
[0.0005, 0.008] AND IQR overlapping [0.0003, 0.015] AND mean ≤ 0.06.
H3 target (Willebrand 2022): median 0.002, IQR 0.0003–0.015, mean 0.037.

| Θ | P(takeoff) | takeoff seeds | recorded median | q25 | q75 | mean | fleet_shape_ok |
|---|-----------:|--------------:|----------------:|----:|----:|-----:|:--------------:|
| 1.33e10 | 0.385 | 77/200  | 0.00027 | 0 | 0.0181 | 0.0291 | False |
| 1.78e10 | 0.415 | 83/200  | 0.00027 | 0 | 0.0230 | 0.0339 | False |
| 2.37e10 | 0.440 | 88/200  | 0.00027 | 0 | 0.0296 | 0.0375 | False |
| **3.16e10** | 0.470 | 94/200  | **0.00067** | 0 | 0.0371 | 0.0434 | **True** |
| **4.22e10** | 0.505 | 101/200 | **0.00269** | 0 | 0.0472 | 0.0502 | **True** |
| **5.62e10** | 0.505 | 101/200 | **0.00364** | 0 | 0.0610 | 0.0561 | **True** |
| 7.50e10 | 0.570 | 114/200 | 0.00889 | 0 | 0.0799 | 0.0653 | False |

## 2. Verdict: a non-empty admissible set, interior on both sides

**Θ ∈ {3.16e10, 4.22e10, 5.62e10} pass the fleet-shape selector.** The
band is ~0.25 decades wide at eighth-decade resolution and is interior —
flanked by failures on both clauses:

- **Below (1.33–2.37e10):** all three rows fail the median floor alone —
  median pinned at 0.00027 (one recorded onset on the 3,711-host hull)
  against the 0.0005 floor, a 1.85× miss, while the IQR overlaps and the
  mean passes at every point. The failure is monotone in Θ within
  precision: the median cell is a no-takeoff voyage at every lower row.
- **Above (7.5e10):** fails the median ceiling (0.0089 > 0.008) AND the
  mean cap (0.065 > 0.06) — the same pair of clauses the 1e11 decade row
  failed, confirming the high-side closure mechanism is the mean cap
  arriving together with median overshoot, not the mean cap alone.

None of the `report_immediately_if` triggers fired: the set is
three-point, not single-point; the band does not run to either lattice
flank; no clause fails uniformly; zero child failures; the canary spec
audit was clean.

**Mechanistic read (reported, not thresholded):** the recorded-rate
distribution per voyage is bimodal — non-takeoff voyages record ~0–3
onsets (median-cell rate ~0.00027), takeoff voyages record ~100–1,000
(rate ~0.02–0.3). The median clause is therefore effectively a gate on
where the median seed sits relative to the takeoff class: admissible rows
are those where P(takeoff) ≈ 0.47–0.51 places the median voyage just
inside the smoldering edge (2–30 recorded onsets). The H3 window is
crossed by the median exactly where the takeoff transition passes through
50% — the selector is, mechanically, a near-criticality selector, which
is what the design's bimodality note predicted of the real fleet.

## 3. Diagnostics

- **Index geometry.** `index_geometry_pass_fraction` = 0.52 on every row —
  unchanged from the decade lattice (a property of the incubation draw,
  Θ-independent); below its 0.80 witness bar, feeds no gate.
- **Conditional-on-takeoff recorded mass.** Among takeoff seeds, median
  `recorded_onsets` rises through the admissible band: 158 (1.33e10) →
  161 (3.16e10) → 175 (4.22e10) → 225 (5.62e10) → 247 (7.5e10), with
  q05–q95 intervals roughly 17–1,220. Every row's interval comfortably
  contains the record's 197. This is the free read on how the stage-2
  conditional clause may fare on the declared replay: the takeoff-class
  recorded mass at admissible Θ sits at DP order on the generic voyage
  already.
- **`before_share`** is trivially 1.0 on generic rows (no day-17 split on
  a 7-day voyage); quoted, never gated.

## 4. What stage 2 is now enumerated to run

Per the design's `stage_2_declared_replay.theta_points` clause — every
admissible Θ in the union of this lattice and the v11 decade rows (the
decade rows admitted nothing), plus the nearest failing lattice point on
each side as boundary flanks — the declared-replay stage runs at
**{2.37e10, 3.16e10, 4.22e10, 5.62e10, 7.5e10}** × 20 matched seeds at
base 20200205 = **100 cells**, verbatim v10 cell shape (onset_day −1.0,
departure_day 5.0, dwell_weighted, imports 1, age 3.3 carried, 768
epochs). No decade-lattice point is among them, so no v10 cell is quoted
in place of a replay cell. The stage-2 design is frozen in this change as
`picard_framework/runs/covid_theta_screen_v11_stage2_design.json`; the
conditional_trajectory_clause and the declared audit invariant are carried
verbatim. The two flank rows are boundary cells — reported as the band's
edges, never selected on.

## 5. Trigger review (`report_immediately_if`, all evaluated)

- Single-point admissible set → not met (three contiguous points).
- Band running to a lattice flank → not met (failures on both sides).
- Every interior point failing the same clause 1e11 failed → not met
  (lower flank fails the median floor, a different clause; three interior
  points pass).
- Child failure rate > 5% → 0/1,400.
- Any cell carrying declared geometry → canary audit clean (no onset_day,
  no departure_day, no ascertainment key, 168 epochs).

## 6. Next decision — for the user

The admissible set is measured non-empty, so **stage 2 is the enumerated
next step, not a new question**: 100 declared-replay cells at the five
Θ points above, submitted under the same prefix machinery. It requires
the stage-2 design file on main (it is in this PR) → image → job-def →
20-seed canary row at 3.16e10 → the remaining 80 cells; ~30 min per
replay cell, under an hour of fleet wall-clock. If any candidate Θ's
takeoff seeds straddle 197 with a near-0.173 before_share, the arm has a
fitted Θ to take to the held-out Greg Mortimer stage 3; if none does, the
empty admissible set is measured at eighth-decade resolution and the
deficit is localised to conditional outbreak size — the result this
screen was built to produce.
