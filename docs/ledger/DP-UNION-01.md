# DP-UNION-01
**Date:** 2026-11-24
**Commit:** c8b7315d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** c7f7f927

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

## Grid

Declared on the post-adoption emission scale (`airborne_emission_fraction`
0.85), with no conversion from old θ: a half-decade lattice 1e5–1e10, a
5-seed pilot at each decade read for its T3 side only, and a selection
rule, all committed (c7f7f927) before any cell. Pilot median P31: 0, 0, 0,
494, 879, 625 at 1e5 … 1e10. Scored grid {1e8, 3.16e8, 1e9, 3.16e9};
canary at 3.16e8.

## Canary (20 seeds at θ = 3.16e8, provisional)

Readout `docs/covid/covid_dp_union_01_readout.md`. 50 Batch cells (30
pilot, 20 canary), all succeeded, no audit deviation.

- **No scored row:** 1 of 20 seeds is in the founder class (needs 5).
- Reported only, takeoff class (13 seeds): attack median 3,124 secondaries
  against [712, 960]; during-quarantine 1,919 against [150, 350];
  `before_share` 0.004 against 0.173; ignition day 13 against ≤ 9;
  conditioned capture 0.887; P31 793 and P34 830, both compatible with
  634 and 691.
- 7 of 20 seeds produce no secondary infection. Not dead, not saturated.
- The crew wave under-fills on seeds with outbreaks (median 3,353
  specimens through day 34 against 3,894).

## Next decision

Benjamin decides whether the 66-cell array runs. The canary suggests
(hypothesis, one θ) that it would return "insufficient class mass" at
every θ, which would make the founder class rather than θ the binding
constraint.
