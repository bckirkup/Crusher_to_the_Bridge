# THETA-SCREEN-V13
**Date:** 2026-09-28
**Commit:** d424673d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** edb7fc41

Declared before any v13 cell ran. Re-admission of the admissible Θ band
under capped reach: COVID-EXPOCAP-01 (PR #755, merged d424673d) made the
per-shedder per-epoch contact budget default-on for catalogued cruise
platforms, so the THETA-SCREEN-V12 admissible set {1.33e11..4.22e11} —
admitted under unbounded reach on image `covid-theta-v12-f42901aa` — is
stale. This stage re-runs the v12 lattice verbatim on the current
default engine: same 9-point eighth-decade lattice, same seeds, same
frozen selectors, same declared Diamond Princess replay, with no arm
override — `transmission.exposure_cap.enabled` is the shipped default
the fleet already lives under. If the band survives unchanged the entry
records that as measured fact; otherwise the surviving admissible band
is what this stage admits.

## Declared

Designs (criteria verbatim from v12 — `fleet_shape_selector`,
`conditional_trajectory_clause`, `index_geometry` audit invariant,
`h3_role_change`; the design diff vs v12 shows only the design id and
the `parent_design` chain pointer):

- `picard_framework/runs/covid_theta_screen_v13_design.json` — stage 1,
  generic voyages, 9 Θ × 200 seeds at base 20201001 = 1,800 cells.
  Endpoint rows are bracket-verification boundaries, never candidates.
- `picard_framework/runs/covid_theta_screen_v13_stage2_design.json` —
  stage 2, declared replay (onset_day −1.0, departure_day 5.0,
  dwell_weighted, imports 1, infection_age 6.8, 20 seeds at base
  20200205, 768 epochs). Points list is the candidate universe (Θ 1e9
  QUAR-ATTR-V2 anchor + nine lattice Θ); the parent's frozen rule
  selects which rows submit — admissible set + flanks, the
  window-straddling pair on an empty-but-crossed surface, or nothing if
  the window is illusory.

Selection: admissible set = interior Θ passing the fleet-shape selector
whose replay cells pass the conditional clause; boundary hits are
reported, never selected. Stage 3 (greg_mortimer_2020, H1/H2) stays held
out and gated on stage 2.

## Campaign gate

AWS canary of 60 cells before the array — 20 cells each at Θ 1e11,
3.16e11 (interior midpoint), 1e12 (INDEX_OFFSET 0/800/1600,
ARRAY_SIZE 20). On the v13 image the cap-on default is the operative
engine difference vs v12: the bracket verification read is now the
capped-reach crossing check — where 1e11 and 1e12 sit relative to the
selector window on this image is the measurement, not a precondition.
Every generic spec must be free of declared
onset_day/departure_day/molecular_ascertainment_start_day, and every
canary cell's endpoints pair seed-for-seed with the v12 cells at the
same Θ — their drift is the cap's signature and is reported, not
thresholded. The full 1,800-cell array commits only on a clean canary
readout, the user having directed this campaign contingent on the
canary.

## Report immediately if

No Θ in the screened range restores ignition on the majority of seeds
(the band is empty under capped reach — the engine needs a mechanism,
not a Θ); the surviving band pushes any declared anchor out of its
window; the clause passes only at a boundary endpoint; the takeoff
transition sits outside the bracket; any stage-1 spec carries a declared
onset_day/departure_day; or child failures exceed 5%.

## Result

Measured on image `covid-theta-v13-edb7fc41` (jobdef rev 28): 2,020 cells
(60 canary + 1,800 stage 1 + 160 stage 2), 0 failures. Endpoint drift vs
v12 (cap signature, reported not thresholded): among seeds taking off in
both campaigns, median recorded_onsets compresses to 0.72× of v12 at Θ
1e11 and 0.82× at Θ 1e12; takeoff class flips on 18/200 and 23/200 seeds.

**Stage 1 — the window survives under capped reach, shifted one notch up
at each edge. Admissible set = {1.78e11, 2.37e11, 3.16e11, 4.22e11,
5.62e11}.** Median recorded attack climbs monotonically through the H3
window (0.00081 → 0.00781); 1e11 and 1.33e11 fail the floor (0.00027),
7.5e11 and 1e12 fail the ceiling (0.0139/0.0183); the mean cap never binds
(top row 0.0521 < 0.06 vs v12's 0.0733 at 1e12 — the budget flattens the
outbreak tail). Edges: lower ∈ (1.33e11, 1.78e11], upper ∈ [5.62e11,
7.5e11).

**Stage 2 — the clause fails at every admissible Θ again.** Declared
replay, 20 seeds at base 20200205 (clause needs takeoff seeds' q05–q95 of
recorded_onsets to contain 197 and median before_share within 0.10 of
0.173):

| Θ | role | n_takeoff | rec. onsets q05/med/q95 | before_share med | clause |
|---|------|-----:|----------------------|-----------------|:------:|
| 1e9 | anchor | 7/20 | 115 / 2,966 / 3,134 | 0.175 | PASS (boundary — not selectable) |
| 1.33e11 | flank | 17/20 | 1,987 / 3,432 / 3,544 | 0.810 | FAIL |
| 1.78e11 | admissible | 18/20 | 2,024 / 3,516 / 3,546 | 0.835 | FAIL |
| 2.37e11 | admissible | 17/20 | 1,995 / 3,468 / 3,549 | 0.851 | FAIL |
| 3.16e11 | admissible | 17/20 | 1,797 / 3,484 / 3,563 | 0.904 | FAIL |
| 4.22e11 | admissible | 18/20 | 1,807 / 3,464 / 3,579 | 0.855 | FAIL |
| 5.62e11 | admissible | 19/20 | 1,770 / 3,505 / 3,577 | 0.891 | FAIL |
| 7.5e11 | flank | 18/20 | 1,777 / 3,506 / 3,588 | 0.942 | FAIL |

Every admissible row saturates takeoff seeds at ~1,800–3,590 recorded
onsets — the q05 floor alone is 9–10× the record's 197 (v12 read 11–15×;
the budget trims the slowest burns but not the saturation shape) — and
before_share rises monotonically with Θ (0.81 → 0.94). The only clause
pass is the Θ1e9 anchor, a fleet-shape-inadmissible boundary row whose
re-measure still lands (before_share 0.175 vs 0.173 declared).

**Verdict: same outcome as v12, shifted coordinate.** Under capped reach a
real fleet-shape-admissible set exists — {1.78e11 … 5.62e11} — but no Θ
inside it passes the conditional clause, and the clause's only pass sits
outside the band. The cap moved WHERE the window sits, not WHAT takeoff
trajectories do inside it; the residual is mechanism-shaped, not Θ-shaped.
The Θ axis inside the bracket is exhausted on this engine. No Θ is
admitted, so no held-out cells or pins move.

Full readout: `docs/covid/covid_theta_screen_v13_readout.md`; surfaces
`covid_theta_screen_v13{,_stage2}_surface.csv`, drift table
`covid_theta_screen_v13_pairs.csv`.
