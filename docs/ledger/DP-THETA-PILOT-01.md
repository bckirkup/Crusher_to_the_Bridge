# DP-THETA-PILOT-01
**Date:** 2026-11-22
**Commit:** b8194d7c
**Pathogens:** sars_cov2_resp
**Status:** declared

## Scope

Checkpoint C of the post-behavior theta protocol (THETA_AFTER_BEHAVIOR),
declared on the DP-REPLAY-ENVIRON-01 environs and anchored on the
DP-REPLAY-DOSE-DIAG-01 measured window. Design doc:
`docs/covid/covid_dp_theta_pilot_01_design.md`; design file:
`picard_framework/runs/covid_dp_theta_pilot_01_design.json`; campaign:
`campaigns/covid/dp_theta_pilot_01/`.

- **Grid:** θ ∈ {1e10, 3.16e10, 1e11, 3.16e11, 1e12}, half-decade
  spacing across the diagnostic's measured normalized window; the prior
  refit's 3.16e11 sits inside it. The shipped 7.9e6 is excluded by
  declaration (expected ~0.006 conversions/seed — below any floor).
- **Seeds:** 24 matched seeds 20200205–20200228 per (θ, arm); seed
  spread cancels in the θ contrast. Benjamin 2026-11-22: "Do 24 seeds
  and the shorter horizon. we can revisit seeds later."
- **Horizon:** 120 epochs declared per cell (the measured window);
  full-voyage compounding is a later checkpoint.
- **Cells:** 240 = 2 arms (replay_baseline null reference +
  replay_niid) × 24 seeds × 5 θ. `replay_journal` excluded — the
  NIID-clock contrast is not part of this question.

## Frozen criteria (before any cell ran)

Selector: paired-seed secondary conversions per (θ, arm) from
`cell_payload` minus the seeded index. Frozen thresholds (design doc):
saturated = median secondaries ≥ 0.95×(aboard−1); dead = zero
secondaries on ≥20/24 seeds; measurable neighbour difference =
same-sign paired difference on ≥18/24 seeds or median ratio ≥1.5.
θ bracket-admissible on `replay_niid` iff neither saturated nor dead
and ≥1 adjacent cell differs measurably.
Audit invariants: NIID `seed_patch` resolved; `close_zones` firing =
FAILED COMPARISON; payload `cell.theta` and run-spec
`susceptibility_scale` (= θ·(α+β)/α, α=0.18 β=58) must match the
declared cell. Report-never-select: dose shares, routes, takeoff
counts (24-seed rare-event resolution is coarse by declaration).

## Judgment calls

- `num_epochs` reaches `prepare_cell_run_spec` through the campaign
  block args — a *declared* horizon, not the pf02 worker's smoke-cap
  use of the same flag.
- Canary = `niid_t1e11_canary` (20 seeds at the middle θ on the arm
  the pilot is about); array awaits readout + user decision per the
  campaign gate.

## Handoff

Next after canary readout: user decision on the 240-cell array;
surviving θ (or interval) gates Checkpoint D densification and the
Greg Mortimer transfer.
