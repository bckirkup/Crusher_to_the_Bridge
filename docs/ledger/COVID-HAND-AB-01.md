# COVID-HAND-AB-01
**Date:** 2026-10-01
**Commit:** 1c94de2d
**Pathogens:** sars_cov2_resp
**Status:** measured

The 60-cell three-arm canary of the rebuilt hand line on the Diamond
Princess record leg (design
`picard_framework/runs/covid_hand_ab_v1_design.json`, job-def
`picard-covid-boarding-screen:43`, image digest `sha256:5f4485e5…`,
prefix `campaign/covid_hand_carriage01/`) is measured:
`docs/covid/covid_hand_ab_v1_readout.md`.

Verdict `hand_line_replay_neutral`:

- All three arms burn at Θ 2.37e11 (~96% attack, recorded medians
  ~3.4e3, before_share 0.82–0.89 vs the record's 197/0.173) — no arm
  approaches the record legs.
- The two labelled baselines are byte-identical on all 20 seeds: the
  RESERVOIR-01-vs-v13 contrast the design was built to decompose does
  not exist on this scenario (their difference lives on the stool-event
  path, which the COVID arm never exercises). The same-seed baseline
  spread the frozen attribution criterion quotes is 0 by degeneracy.
- `hygiene_cycle` vs baseline paired deltas (Δrec med +27, Δinf +10,
  Δbshr +0.057, Δduring −15.5, takeoff flips 5/20) sit inside the
  stream-reorder band the extra arm draws induce; the arm reads
  directionally *more* burn, not the suppression the
  report-immediately clause watched for.
- Route decomposition: fomite = 0 during-quarantine acquisitions pooled
  across all 60 cells; the window is ~99.5% droplet. The hand reservoir
  is not the during-quarantine carrier on this hull at this Θ.

Open decision carried on the outstanding ledger
(`docs/covid/covid_open_ledger.md` §3): whether `covid_theta_screen_v14`
stage 1 runs verbatim (3,600 cells, arm pairing kept), single-arm
(hygiene_cycle only, 1,800 cells), or not at all — the canary's
neutrality plus the baseline degeneracy argues the pairing measures
nothing at these coordinates.
