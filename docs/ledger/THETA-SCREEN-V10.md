# THETA-SCREEN-V10
**Date:** 2026-09-20
**Commit:** 1da4211
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** a9b4f1f

Fully measured: 200 of 200 cells (canary Θ 1e9 first, then the remaining 180;
see Result).

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

## Result — canary only

The pre-committed canary ran on AWS Batch at `main` = `a9b4f1f` (engine
identical to `d62f10d`; the only diff is this design file), image
`picard-campaign:theta-v10-a9b4f1f`
(`sha256:325dde73ac57039dee318f451700fd1886fa3c35d60f880d060ea93146b4d3b1`,
the campaign base layered with `deploy/aws/Dockerfile.covid_hull` so the
screen entrypoint is present), job definition
`picard-covid-boarding-screen:12`, queue `picard-campaign-queue`, prefix
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v10/a9b4f1f/`.
Child `6555b89d-f44f-420e-b607-41ebd239c1b9` ran index 160 (shared seed), then
array `cf4865ef-2a4b-48ef-bf31-6830d062fd0c` (size 19) ran indices 161–179.
**20 of 20 cells SUCCEEDED; 180 of 200 cells have not run.** Full readout:
`docs/covid/covid_theta_screen_v10_readout.md`, with
`docs/covid/covid_theta_screen_v10_canary_surface.csv` (the one Θ 1e9 row) and
`docs/covid/covid_theta_screen_v10_canary_pairs.csv` (all 20 seeds paired to
their v9 cells).

Gate outcome: `index_onset_day` −1.0 and `index_shedding_at_day0` true in
20/20; no `invalid_reason`; child failure rate 0/20; the shared seed
(20200205) reproduces the QUAR-ATTR-V2 `A0_declared` record exactly at
`infections_total` 3458 / `attack_rate` 0.9318, matching an in-image local
run of the same cell. The screen payload carries no quarantine-window or
episode fields, so the 3414–43–1 split and the "no episode ≥ 2" check are not
readable from these cells and are not asserted here. Takeoff at Θ 1e9 is
0.60 (12/20) against v9's 0.60 at the same seeds — **no seed changes takeoff
class**, well inside the declared 2/20 band. The gate text above quotes v9's
Θ 1e9 takeoff as 0.85; the v9 surface CSV gives 0.60 at 1e9 and 0.85 at 1e10,
and the comparison uses the CSV row. Conditional median recorded onsets
3,103 → 2,991.5; conditional median attack rate 0.865 → 0.865;
`infections_total` moves by at most 69 hosts (≤ 2.1%) on any takeoff seed and
is identical on all eight extinct seeds.

The entrypoint gained `--index-offset` in the same change: Batch overwrites a
user-supplied `AWS_BATCH_JOB_ARRAY_INDEX`, so this canary had to be launched
through a `runpy` wrapper that added the 160/161 offset. The flag is in the
tree, not in the image that ran; the remaining sub-blocks below were launched
through the same wrapper against the same pinned digest.

## Result — full surface (200 of 200)

The user chose to run the rest. Arrays `a83a2b5b-1b73-475c-8857-71ef9d0cbeae`
(size 160, offsets 0–159) and `dfe080e6-b83b-42d9-9177-1c3991e99f85` (size
20, offsets 180–199), same job definition `:12`, image digest, queue and
prefix. **Both arrays SUCCEEDED, 180/180 children; child failure rate over
the campaign 0/200.** S3 holds exactly 200 cell payloads, one per (Θ, seed);
`fit_covid_theta.py screen` merged them against the design without
`--allow-partial`. Full readout `docs/covid/covid_theta_screen_v10_readout.md`,
surface `docs/covid/covid_theta_screen_v10_surface.csv` (ten rows), all 200
seeds paired to their v9 cells in `docs/covid/covid_theta_screen_v10_pairs.csv`
(v9 parents synced from `campaign/covid_theta_screen_v9/cells/`, age 3.3 d).

Gate outcome, per Θ against v9 (`0fb186b`): takeoff fraction identical at
every decade (0, 0, 0, 0.10, 0.15, 0.10, 0.20, 0.35, 0.60, 0.90); **zero
takeoff-class flips in 200 paired seeds** (band was 2/20 per row);
`index_onset_day` −1.0, `index_shedding_at_day0` true and no `invalid_reason`
in 200/200; `index_geometry_ok` true on every row; `covid.T1` true only at
Θ 1e9 in both versions; `covid.T3` false at every row except the Θ 1e9 flip
already recorded above; `onset_mass_near_target` identical to v9 at every
decade (0.05 at 1e4 and 1e8, 0.10 at 1e5, 0 elsewhere). `infections_total`
is byte-identical to v9 on 154/200 cells (20/20 at Θ ≤ 1e4, falling to 2/20
at 1e10 where every seed burns); every non-identical cell is a takeoff seed
except one (Θ 1e8, seed 20200224: 48 → 46 hosts). The two largest paired
moves are Θ 1e5 seed 20200205 (1110 → 950, the QUAR-ATTR-V2 A0 record at
that Θ, reproduced exactly) and Θ 1e7 seed 20200214 (457 → 621); all others
are within 7% of the v9 total. Row medians move ≤ 1% at 1e9 and 1e10
(1008 → 1004, 3381.5 → 3354 recorded onsets).

Verdict: QUAR-EXEMPT-01 + REINFECT-01 leave the v9 Θ surface structurally
unchanged — extinction-or-burn at every decade, Θ moving takeoff probability
rather than size, no near-critical band at one declared import. Every v9 row
is now **confirmed on the repaired engine at `a9b4f1f`**; the v10 CSV
supersedes the v9 CSV as the surface of record. Still no Θ is fitted or
selected: `covid.T1` passing at 1e9 is the same interval-span artefact the v9
readout named. The screen payload still carries no quarantine-window or
episode fields, so the "no episode ≥ 2" check remains unread by this campaign
and rests on REINFECT-01's own tests.
