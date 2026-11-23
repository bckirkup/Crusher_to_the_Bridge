# covid-dp-theta-pilot-01 — Checkpoint C theta pilot (declared)

**Status:** declared. Criteria below are frozen before any cell ran;
no criterion may be altered after the surface is seen.

## Scope

Checkpoint C of the post-behavior theta protocol (THETA_AFTER_BEHAVIOR):
a log-spaced theta grid on matched seeds over the DP-REPLAY-ENVIRON-01
environs, at the 120-epoch window DP-REPLAY-DOSE-DIAG-01 measured.

- Design file: `picard_framework/runs/covid_dp_theta_pilot_01_design.json`
  (`design_id` `covid-dp-theta-pilot-01`, parent `covid-dp-replay-01`).
- Arms: `replay_baseline` (required empty-override first arm; rides
  `mega_cruise_5000` under the journal clock — the null reference) and
  `replay_niid` (the frozen replay movement kernel).
- Thetas: **{1e10, 3.16e10, 1e11, 3.16e11, 1e12}** — five half-decade
  values spanning the diagnostic's measured normalized window
  (~1e10–1e12 for non-trivial conversion on the 120 h dose tail). The
  prior refit's selected 3.16e11 sits inside the grid. The cells'
  inherited 7.9e6 is NOT in the grid: the diagnostic put expected
  conversions at ~0.006 per seed — below any useful floor.
- Seeds: 24 matched seeds, 20200205–20200228 (matched across every
  θ × arm cell — seed-to-seed dose spread cancels in the θ contrast).
- Horizon: **120 epochs**, declared per cell via the campaign's block
  `num_epochs` — the window the diagnostic measured. Secondary
  compounding past that window is out of scope by declaration; a
  full-voyage bracket is a later checkpoint.
- Cells: 240 (2 arms × 24 seeds × 5 θ).

## Frozen criteria

**Selector:** per (θ, arm), secondary conversions over the 120-epoch
window across the 24 seeds — per-cell `cell_payload` infection fields
minus the seeded index — compared across θ on the SAME seed (paired).
Frozen thresholds for `replay_niid`:

- **saturated cell:** median seedwise secondaries ≥ 0.95 ×
  (`aboard_total` − 1 index);
- **dead cell:** zero secondaries on ≥ 20 of 24 seeds;
- **neighbour differs measurably:** the paired seedwise difference in
  secondaries between adjacent grid θs is same-sign on ≥ 18 of 24
  seeds, or the ratio of seedwise medians (higher-θ / lower-θ) is
  ≥ 1.5. Ratio edge cases are frozen: lower-median 0 with
  higher-median > 0 counts as infinitely different (measurable);
  0/0 counts as no measurable difference.

θ is **bracket-admissible** on `replay_niid` iff its cell is neither
saturated nor dead AND at least one adjacent grid cell differs
measurably from it (edge θs need differ only from the one existing
neighbour). Interior θs differing measurably from both neighbours are
the pilot's working shortlist; a θ bounded only below or only above
marks the bracket edge.

**Reported, never selected on:** cabin/outdoor dose share, route
composition, takeoff/onset counts versus `takeoff_recorded_onsets`,
quarantine attribution tallies, `hvac_airborne` share. Rare-event
resolution at 24 seeds is coarse (~±10pp) — acknowledged in the
declaration, not a defect.

**Audit invariants (deviation = defect, not failed criterion):**

- index onset clock: `seed_patch` NIID correction must resolve
  (onset_day 3.0, infection_age_days 2.8) on `replay_niid` cells;
- `close_zones` protocol firings flag a FAILED COMPARISON cell
  (quarantine zone closure changes the kernel being measured);
- the swept axis must resolve: payload's `cell.theta` equals the
  block's declared θ and the run spec's susceptibility_scale equals
  θ·(α+β)/α with α=0.18, β=58.

**Later stages:** a surviving θ (or θ-interval) on `replay_niid` gates
a denser grid or added seeds (Checkpoint D) and the Greg Mortimer
transfer. If no θ is admissible, the finding is that the window
does not contain a usable θ — a reportable result, not a failure.

## Campaign

`campaigns/covid/dp_theta_pilot_01/` — 11 blocks (niid_t1e11 split
canary 20 + rest 4; five other θ-blocks per arm × 24 seeds).
Canary gate: `niid_t1e11_canary` (20 seeds, θ=1e11, replay_niid) read
out before any array submit.
