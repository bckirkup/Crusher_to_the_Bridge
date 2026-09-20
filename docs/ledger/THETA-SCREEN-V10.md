# THETA-SCREEN-V10
**Date:** 2026-09-20
**Commit:** 1da4211
**Pathogens:** sars_cov2_resp
**Status:** declared

## Declared (before any cell ran)

`covid_theta_screen_v10`
(`picard_framework/runs/covid_theta_screen_v10_design.json`) re-measures the
v9 Θ surface on the repaired engine. It is the v9 design with the infection-age
axis removed and nothing else changed: ten decade Θ from 1e1 to 1e10 × the same
20 matched seeds at base 20200205 = **200 cells** on `diamond_princess_2020`,
the same frozen v9 admissibility block (`covid.T1` sole selection criterion,
index-geometry invariant, `covid.T2`/`T3`/`T4`, fleet-shape, burn-tail and
`onset_mass_near_target` diagnostics, all verbatim), the same worker payload.
Authored as a refinement (explicit `points`, `parent_design:
covid_theta_screen_v9`) for the reason v9 was. Nothing has run; this entry is
the declaration the campaign-preflight rule requires before any cell exists.

**Why it exists.** THETA-SCREEN-V9 was measured at `0fb186b` with
post-clearance reinfection active: a cleared host was immediately susceptible
again and the truth channel could count second episodes. REINFECT-01 (#636,
`d62f10d`, `docs/ledger/REINFECT-01.md`) gives cleared hosts the declared
90-day refractory window and episode-keeping records, so no second episode is
possible on a ≤35-day voyage. Every Θ-conditioned conclusion upstream of that
fix — v7, v9, the change-detector pins, the "no near-critical band" finding —
was measured on an engine that no longer exists. The decision to re-measure Θ
before acting on the QUAR-ATTR-V2 attribution is recorded in
`docs/covid/covid_theta_handoff_2026_09_19.md` §16.

**What is dropped, and why it is not a changed criterion.** The infection-age
axis. THETA-SCREEN-V9 measured it inert under the scenario's declared
`onset_day = -1.0`: 200 of 200 (Θ, seed) triples byte-identical across
3.3 / 6.8 / 12.8 d, because `engines/initiation.py::_apply_one_seed` sets the
incubation to `age + onset_day − seed_day` and stamps the history from
`elapsed_since_onset`, so the age cancels. The single value 3.3 d is carried so
the v10 cell keys and run specs match the QUAR-ATTR-V2 `A0_declared` cells
(`…_theta1e9p00_age3p3d_imports1_seed20200205`, minus the arm suffix). The
worker still writes the value into the seed record; the local smoke below shows
it inert, not absent. Removing a measured-inert axis changes no criterion, no
threshold and no constant.

**Canary cell of record** (QUAR-ATTR-V2, `d62f10d`, arm `A0_declared`, seed
20200205, inside the campaign image `python:3.11-slim`): Θ 1e5 →
`infections_total` 950 / `attack_rate` 0.2560 / before–during–after quarantine
745–198–7; Θ 1e9 → 3458 / 0.9318 / 3414–43–1. The v10 cells at those
coordinates must reproduce these exactly; a mismatch invalidates the run rather
than becoming a finding. Note the committed v9 cells reproduce byte-for-byte
only inside the image (handoff §13): a CPython 3.12 host follows a different
trajectory, so local runs are compared with local runs.

**Campaign gate, pre-committed.** Canary = Θ 1e9, all 20 seeds (array indices
160–179 in enumeration order). Read `index_onset_day == -1.0` and
`index_shedding_at_day0` in every cell, exact reproduction at the shared seed,
and takeoff fraction / conditional attack against v9's Θ 1e9 row (takeoff 0.85,
median recorded onsets given takeoff 3,103). Stop and report; the user decides
whether the remaining 180 cells run. Report immediately if any Θ shows takeoff
where v9 showed none (or vice versa) outside a 2/20 seed band, if any cell
reports an episode ≥ 2, or if the child failure rate exceeds 5%.

**The v9 `stage_1b_refinement` block is withdrawn** in this design
(`covid_quarantine_attribution_v1` already recorded two of its three axes
void). Whether any refinement exists is decided from this surface, in its own
design file, before its cells run.

## Validation gate (local, this PR)

- `DESIGN=covid_theta_screen_v10 deploy/aws/submit_covid_boarding_screen.sh --dry-run`
  prints array size **200** (v9 still 600).
- Local smoke of the (Θ 1e9, seed 20200205) cell at 240 epochs on CPython
  3.12: the run spec carries one explicit seed with `onset_day −1.0`, no arm
  channel is set (`pathogen_pool_transport`, `near_field_air`,
  `route_efficiency_multipliers` all unset; scheduled SOP-017 unchanged), the
  payload carries no `arm_id`, `index_onset_day == -1.0` and
  `index_shedding_at_day0` true, and the payload is byte-identical at
  `infection_age_days` 3.3 and 12.8 — the age path is inert.
- The `diamond_princess_2020` slow-tier change-detector pin in
  `tests/test_covid_hull_change_detector.py` is repinned to the post-REINFECT-01
  reading on CPython 3.12, (3522, 2934, 1706, 252, 73) →
  (3418, 2942, 1894, 209, 68). The move is **not** REINFECT-01 alone: the
  cell was read at each merge commit, and QUAR-EXEMPT-01 (#633, `861a0b9`)
  had already moved it to (3464, 2982, 1847, 232, 68) before REINFECT-01
  (#636, `d62f10d`) moved it the rest of the way. The CPython 3.11 reading at
  the same commit differs, (3399, 2963, 1987, 195, 64), consistent with the
  Greg Mortimer cell's per-interpreter pins; it is left unpinned pending a CI
  reading. The slow tier passes locally at the new 3.12 pin (2 passed,
  35 min).

## Result

Not run. Nothing here may be quoted as a Θ result until the canary has been read
out and this entry carries `**Measured at:**`.
