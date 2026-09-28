# THETA-SCREEN-V13
**Date:** 2026-09-28
**Commit:** d424673d
**Pathogens:** sars_cov2_resp
**Status:** declared

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
