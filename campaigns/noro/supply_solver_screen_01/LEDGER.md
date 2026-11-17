# noro_supply_solver_screen_01 — ledger

**Status:** design frozen; no cells run yet.
**Date:** 2026-11-16

## Scope

Expedition p06 screen requested by Benjamin: stratified contaminated supply seeds plus quiet controls on `fl_exp_12d_sens_p06_paxv`, paired `transmission.contamination_solver` `discrete` vs `continuous` to assess sensitivity and range of AR, timing, and role partition.

## Frozen inputs

- Design: `campaigns/noro/supply_solver_screen_01/DESIGN.md`
- Seed selection: `campaigns/noro/supply_solver_screen_01/seed_selection.json`
- Manifest: `campaigns/noro/supply_solver_screen_01/manifest.json`
- Spec: `campaigns/noro/supply_solver_screen_01/campaign.json`

## Counts

- 88 cells total: 2 solver arms x 44 seeds.
- Per solver: station_lots 16 contaminated + 8 quiet, single_line_receipt 10, declared_receipts 10.
- Campaign blocks: 8 (supply arm x solver, with station quiet split into two blocks).

## AWS Batch pins

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver01@sha256:f25d74cd225bc4ade19a012ba801b25f91289f80f3c3778bfd6c27c343a0053a`
- `ENGINE_GIT_SHA`: `3500c205426cc49f1b4075fb5fc5f8ff0d057021`
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_01/`
- S3 manifest/seed files: `manifest.json`, `seed_selection.json` uploaded at the prefix root.
- Canary: Batch job `287b2a2a-c6a1-4fb0-8171-40b33bf958e4`, jobdef `picard-noro-supply-solver-screen-01:1`.

## Preflight status

- [x] Local smoke: solver override reaches engine; output contract unchanged.
  - 24-epoch smoke, seed 900470 station_lots: discrete `acquired=47`, continuous `acquired=53`; both zips carry `parameters.tier_id` = `fl_exp_12d_sens_p06_paxv_station_lots_{discrete,continuous}` and the same summary/census/rss members.
- [x] Dry-run count matches 88 (block array sizes 16+16+10+10+10+10+8+8).
- [x] Local full-length canary, seed 900470 station_lots, 288 epochs, payload lean:
  - discrete: attack_rate 0.2489, pax_reported 0.1329, crew_reported 0.0299, `vsp_trigger_epoch=57`, peak 110 at epoch 224, acquired 108, wall 66.4 s, RSS 385824 KB.
  - continuous: attack_rate 0.2067, pax_reported 0.1108, crew_reported 0.0299, `vsp_trigger_epoch=53`, peak 92 at epoch 119, acquired 89, wall 82.7 s, RSS 449764 KB.
  - One seed only; this is plumbing/timing evidence, not solver attribution.
- [x] Image built and digest pinned in `campaign.json`.
- [x] Manifest uploaded to S3.
- [x] In-container build check: required campaign/tools/manifest files present, `ENGINE_GIT_SHA=3500c205426cc49f1b4075fb5fc5f8ff0d057021`, seed 900470 resolves to index 0 / run_id `fl_norovirus_expedition_cruise_450_dose7p57_rung-shipped_nsf29_bp25c30_n450_ep288_syndromic_comp65_s900470`; `campaign_entrypoint.py --local` completed the full 288-epoch voyage and produced the block zip.
- [x] AWS canary child inspected: job `287b2a2a-c6a1-4fb0-8171-40b33bf958e4` SUCCEEDED on jobdef `picard-noro-supply-solver-screen-01:1`; S3 object `campaign/noro_supply_solver_screen_01/exp_station_lots_continuous/fl_norovirus_expedition_cruise_450_dose7p57_rung-shipped_nsf29_bp25c30_n450_ep288_syndromic_comp65_s900470.zip` (8.7 MB). Zip members are `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_exp_12d_sens_p06_paxv_station_lots_continuous`; `growth_census.json.gz` `hand_occupancy.counters.continuous_path_calls=31029`; derived attack_rate 0.2067, passenger reported-case AR 0.1108, crew reported-case AR 0.0299, `vsp_trigger_epoch=53`, matching the local continuous canary. Batch container wall time was ~78 s.
- [ ] ETA reported; user decides on array.

## Measurements

No sweep measurements yet. The two full-length canary rows above are preflight witnesses only.
