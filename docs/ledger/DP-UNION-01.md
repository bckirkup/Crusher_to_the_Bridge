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
- Worker, argv hook, readout, 45 tests.

## What is held

No θ is declared and the campaign has no block: owner decision 2026-11-23
holds the grid until the airborne fine-share adoption
(`airborne_emission_fraction`) merges and re-denominates θ. No canary was
submitted. No image is built or pinned.

## Local smoke through the registered path (measured, one seed, old units)

**Measured at:** d5273582 with the `SOP-017-DEDQUARTER` rename applied
uncommitted (committed in fecb44c0, which also removed the block under the
hold).

`scripts/campaign run covid/dp_union_01 --block union_t3e9_canary --index
0`, θ=3.16e9, seed 20200205, full voyage. This is a machinery check in the
emission units being retired; **no contract leg is read from it.**

Every audit invariant of the design held on this cell:

- resolved platform `diamond_princess`, quarantine activated at epoch 391,
  no `close_zones`, susceptibility scale = θ·(α+β)/α;
- only `SOP-017-DEDQUARTER` fired; `exempt_fraction` echoed
  {`crew_general`: 0.25}; 261 of 1,045 crew drawn (= round(0.25 × 1,045));
  no zone echo;
- `crew_duty_exclusion.resolved.enabled` true, 732 hosts excluded;
- `retest_negatives_on_sweep` true, `campaign_waves` [`crew_wave`];
- 3,063 specimens through day 31; every later specimen is on day 34 and
  wave-tagged; day-34 positives agree with `observables.campaign_positives`.

Observed on this one cell (hypothesis-grade, one seed, old units):

- The armed crew wave drew **133 specimens**, not the declared 831: 3,196
  specimens through day 34 against the record's 3,894. Confirmed hosts are
  never re-swabbed, and this cell had confirmed 2,351 hosts. Whether the
  wave fills at a record-like attack rate is unmeasured; if it does not,
  the onboard-table denominator is not reproduced and that leg's reading
  needs the caveat.
- Realized exempt share at activation was 0.209 against the 0.25 drawn
  (261 drawn; fewer working at the snapshot). Not investigated.
- Founder yield 11; 2,561 secondaries (attack 0.69); 912 infections during
  the window; 754 positives through day 31, 767 through day 34;
  conditioned capture 0.947 (2,346 / 2,477).

## Next decision

After the fine-share leg merges: declare the θ grid and canary θ in the
design (amendment before any cell), rebuild and pin the image, re-smoke,
submit the 20-seed canary, read out, stop.
