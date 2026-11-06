# NORO-PROVISIONED-SENSITIVITY-01 — ledger

**Status: declared — design frozen, no cells submitted.** Paper-1
sensitivity screen, Child B: 16 Res-V profiles × 4 hulls × 3 venue
arms = 192 cells, seed-paired with NORO-PROVISIONED-VENUE-02, 1.5.0
emitter. Design: `DESIGN.md`; profile table: `PROFILE_TABLE.md`;
execution manifest: `SEED_MANIFEST.json`.

**Submit gate:** design PR merged → image built FROM the post-merge SHA
(must contain PR #1156's emitter AND this PR's `tier_pathogen_overrides`
/ `tier_illness_duration_draw` seams) → digest pinned here → manifest
mirrored to S3 → scout wave → STOP for the user.

Image: _not yet built_. Pinned SHA: _pending merge_. Digest: _pending_.

## Measured before submit (local, repo HEAD 76a44890 + branch)

- D override order: confirmed in code — `shipped` rung overwrote a
  tier-requested `empirical_survival` with `point` (`boarding_axis.
  IndexCaseAxis.pathogen_overrides`); venue02 therefore ran at D =
  `point`. Fixed by the tier-declared-draw seam (this PR); the paired
  probe below shows the flipped draw reaching the engine.
- Loaded values at spec level (`generate_tier_runs` →
  `apply_pathogen_overrides`): p16/p01/meg-p09 all resolve to the
  design values (DESIGN.md §5).
- Dry-run: manifest `--tier all` = 11,520 runs across 192 tiers
  (11,136 main + 384 reserve); `scripts/campaign list` = 288 blocks /
  9,984 cells (small hulls) + 96 blocks / 1,152 cells (mega).
- Local smoke, exp seed 8000, 288 epochs: `scout_fl_exp_12d_sens_p01_crewv`
  1m41 wall; `scout_fl_exp_12d_sens_p16_mixv` 1m44 wall; zip =
  summary.json 0.42 MB + growth_census.json.gz 9.7 MB + rss_samples.json;
  `role_checkpoints` schema 1.0 present with days 3/7/10/12.
- Paired D-probe (p01 coordinates, exp, seed 8000, 288 epochs, draw
  `point` vs `empirical_survival`, everything else identical): the two
  summaries differ (terminal infected 30 vs 29, symptomatic 4 vs 3,
  quarantined 4 vs 7; stamped `illness_duration_draw` follows the
  request), so the tier-declared draw reaches the engine under the
  `shipped` rung. Operational evidence only — one seed, no inference.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| scout | 192 × `scout_<tier>` (8 seeds each) | 1,536 | not submitted |
| main | 192 × `<tier>` (n−8 seeds each) | 9,600 | not submitted — user gate after scout |
