# DP-UNION-01
**Date:** 2026-11-24
**Commit:** fecb44c0
**Pathogens:** sars_cov2_resp
**Status:** declared

Suite 1 of `docs/proposals/covid_theta_unification_plan.md`: the union arm
(`replay_niid` + quarter-exempt confinement + symptomatic-crew removal +
armed retest sweeps and 23 Feb crew wave) scored on the joint
founder-conditioned contract. Design
`docs/covid/covid_dp_union_01_design.md`, design file
`picard_framework/runs/covid_dp_union_01_design.json`, campaign
`campaigns/covid/dp_union_01/`.

## What exists

- `SOP-017-DEDQUARTER` in `data/config/protocols_covid_dp_dedicated.json`:
  SOP-017-DEDICATED with `exempt_work_zones` replaced by `exempt_fraction`
  `crew_general` 0.25. Crew meals stay the dedicated hull's staggered mess
  (QUAR-TAIL-SEAM-01 measured its joint lever with boxed meals on
  `boxed_s1s2`; that difference is declared, not measured).
- Arm `union_niid`: differs from FIT-01's `replay_niid` in exactly
  `scheduled_protocol_id`, `crew_duty_exclusion`, `observation_overrides`
  (test-pinned). No mechanism code, no constant change.
- Seven frozen legs on the founder class (`aboard_window_acquisitions` ≥
  10): ignition day, `before_share`, attack band, during band, conditioned
  capture, T3 through day 31, onboard table through 23 Feb; the
  split-verdict rule; FIT-01's edges and representativeness flag.
- Worker, argv hook, readout and their tests.

## What is held

No θ is declared and the campaign has no block: owner decision 2026-11-23
holds the grid until the airborne fine-share adoption
(`airborne_emission_fraction`) merges and re-denominates θ. No canary was
submitted. No image is built or pinned.

## Machinery smoke

One local cell ran through the registered path before the hold, in the
emission units being retired. It is a machinery check and not a result of
this entry: its record is in `campaigns/covid/dp_union_01/LEDGER.md`, and
nothing from it may be quoted as a measurement of the union arm. This entry
moves to `measured` when the canary is read out.

## Next decision

After the fine-share leg merges: declare the θ grid and canary θ in the
design (amendment before any cell), rebuild and pin the image, re-smoke,
submit the 20-seed canary, read out, stop.
