# DP-THETA-PILOT-01
**Date:** 2026-11-22
**Commit:** b8194d7c
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 086ecc84

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

## Canary readout (measured 2026-11-23)

`niid_t1e11_canary` — 20/20 children SUCCEEDED on jobdef
`picard-covid-dp-theta-pilot-01:1`,
image `picard-campaign@sha256:a65b9aae29b1ff221649181dbb2ca920c6e2384391f8223ea80df9cb53e6f308`
(built at 086ecc84). All audits clean: `cell.theta`=1e11 resolved,
120 epochs, platform `diamond_princess`, `close_zones` never fired.

Secondaries per seed (θ=1e11, replay_niid, 120ep): **median 39,
range 0–1516**; 1 zero-secondary seed (20200217); high seeds
20200205=1228, 20200221=1516, 20200219=1014, 20200216=519. Per frozen
criteria the cell is neither saturated nor dead on the canary seeds;
**bracket-admissibility still requires a measurable difference from an
adjacent grid cell** — pending the full array. Variance is
index-identity driven. Committed readout: `docs/covid/dp_theta_pilot_01_canary_readout.json`;
synced cells under `out/dp_theta_canary/` (untracked).

## Array readout (measured 2026-11-23)

Full array approved by Benjamin ("ok execute" 2026-11-22 21:21 EST);
10 blocks submitted 2026-11-23T02:21Z on jobdef
`picard-covid-dp-theta-pilot-01` (job ids in
`campaigns/covid/dp_theta_pilot_01/LEDGER.md`), same pinned image as
the canary. **240/240 cells SUCCEEDED.**

Median secondaries per seed (120-epoch horizon), θ lo→hi:
- `replay_niid` (diamond_princess, NIID clock): 2.5 / 8 / 37 / 392 / 1054; zero-secondary seeds 7/3/2/1/1.
- `replay_baseline` (mega_cruise_5000 default stack, declared null reference): 41.5 / 95.5 / 232.5 / 599.5 / 1577.5; zero-secondary seeds 1/1/0/0/0.

Frozen criteria: no cell saturated (no median ≥0.95·(aboard−1)), none
dead (no cell with ≥20/24 zero seeds); every adjacent θ pair on both
arms shows a measurable contrast (all ≥18/24 same-sign paired diffs,
median ratios 2.3–10.6×) → **all five θ are bracket-admissible on
`replay_niid`; the grid is a working fitting instrument, not a
straddle.** The declared audit marks `close_zones` firings as FAILED
COMPARISON: on `replay_baseline` that applies to 16 cells (1 at θ=3.16e10,
4 at 1e11, 4 at 3.16e11, 7 at 1e12 — seeds listed in the array readout),
so only baseline θ=1e10 is a clean admissible cell; the other four
baseline cells are measured but comparison-failed under the declared
audit (close_zones never fired on niid, 120/120).

Notable: seed 20200217 draws a dead index — zero secondaries at every
θ on niid (and on baseline at θ≤3.16e10); index-identity lottery
dominates within-cell variance as predicted. niid medians run ~2–16×
below baseline at the same θ — a bundled contrast of the declared
dedicated-stack arm vs the default stack (hull, protocols, NIID clock
change together; the gap does not isolate any one of them).
Audits: susceptibility_scale
= θ·(α+β)/α exact on all 240 cells; close_zones never fired on niid
(120/120), fired on 16/120 baseline cells (default-stack protocol
context, declared).

Committed readout: `docs/covid/dp_theta_pilot_01_array_readout.json`;
synced cells under `out/dp_theta_array/` (untracked).

## Handoff

Checkpoint C pilot measured end-to-end. Next decision (Benjamin):
which θ band to carry into the scored endpoint / densification
(Checkpoint D) and the Greg Mortimer transfer. Note the bracket is
anchored to the 120-epoch window; a full-voyage fit shifts the
effective bracket lower (compounding).
