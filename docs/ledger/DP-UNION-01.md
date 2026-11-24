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

## Staged array (24 seeds each at θ = 3.16e9 and 1e9)

Staging rule committed at 11b759e8 before submission (3.16e9 first; stop
below 5 founder-class seeds; otherwise 1e9). 43 further Batch cells, all
succeeded, same image digest, no audit deviation.

- **3.16e9 is scored (7 of 24 seeds in the founder class) and not
  consistent.** Pass: ignition day 7, conditioned capture 0.964, P31 663
  and P34 663 (both compatible). Fail: `before_share` 0.637 against 0.173
  ± 0.10, attack 3,452 against [712, 960], during 112 against [150, 350].
- **1e9 has no scored row** (4 of 24 in class).
- Descriptively (only 3.16e9 is scored), median secondaries are far above
  the band in every class at 3.16e8, 1e9 and 3.16e9: non-extinct seeds
  infect 2,419–3,474 of 3,710 at the two upper θ and 946–3,268 at 3.16e8;
  3 of 24 seeds are extinct at 3.16e9, 6 of 24 at 1e9.
- The canary hypothesis that the class cannot be scored anywhere on the
  grid is withdrawn.

## Completed grid (24 seeds at each of 1e8, 3.16e8, 1e9, 3.16e9)

The last 23 cells ran on the owner's decision; 116 Batch cells in all,
every one succeeded, one image digest, no audit deviation. No row dead or
saturated.

- Founder-class seeds: 0, 2, 4, 7 of 24 as θ rises. Only 3.16e9 is scored.
- **Joint verdict: no consistent θ.** Ignition, capture, T3 and the
  onboard table pass at 3.16e9 only; `before_share`, attack and during
  pass at no θ (failed on the scored row, unscored on the other three).
  No split verdict.
- Extinct seeds: 13, 10, 6, 3 of 24. Takeoff-class median secondaries
  3,019, 3,128.5, 3,288, 3,383 against [712, 960].

## Next decision

Benjamin decides what follows Suite 1. The contract cannot locate a θ on
this arm because the founder class is reachable only at the top θ, and
there it places the epidemic before quarantine (`before_share` 0.637,
during 112).
