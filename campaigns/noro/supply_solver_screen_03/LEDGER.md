# noro_supply_solver_screen_03

## Scope

Mega extension of the supply solver screen: `mega_cruise_5000` (`fl_meg_12d_sens_p06_paxv`, 7000 agents), paired `transmission.contamination_solver` `discrete` vs `continuous` on stratified contaminated supply seeds plus quiet controls. Design is frozen in `DESIGN.md`; the frozen seed list is `seed_selection.json`.

## Frozen inputs

- Campaign: `noro_supply_solver_screen_03`
- Manifest: `campaigns/noro/supply_solver_screen_03/manifest.json`
- Cells: 88 runs = 1 hull x 2 solver arms x 44 seeds. Per solver: `station_lots` 16 contaminated + 8 quiet, `single_line_receipt` 10 contaminated, `declared_receipts` 10 contaminated.
- Seed source: `noro_supply_seed_scan_01` mega JSONL rows (boarding census only).
- Worker: `tools/noro_diag/growth_chain_census.py`, payload `lean`, `PYTHONHASHSEED=1`.
- Queue: `picard-campaign-queue`; resources 1 vCPU / 8192 MB / 512 MB shm.

## Preflight

- [x] Frozen design and seed-selection rule written before cells.
- [x] `seed_selection.json` generated from the mega seed census: station 16 / single 10 / declared 10 / quiet 8.
- [x] `scripts/campaign describe noro/supply_solver_screen_03` resolves 8 blocks, array sizes 16+16+10+10+10+10+8+8 (88 total).
- [x] `scripts/campaign submit --dry-run --block <all 8 blocks> --account 994254241749 --bucket crusherbucket-994254241749-us-east-1-an` OK.
- [x] Local 24-epoch smoke, mega `station_lots_continuous` tier index 0 seed 1020931: zip members `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_meg_12d_sens_p06_paxv_station_lots_continuous`; `num_agents=7000`; `payload_profile=lean`; `hand_occupancy.counters.continuous_path_calls=50750`; `common_source.provisioned_source.n_contaminated=3`; `common_source.telemetry.events_provisioned_lot=28`, `takers_served=2126`; derived attack_rate 0.0521, passenger reported-case AR 0.0, crew reported-case AR 0.0005, `vsp_trigger_epoch=None` (24-epoch smoke).
- [x] Image built and digest pinned in `campaign.json`.
- [x] Manifest uploaded to S3 (`manifest.json`, `seed_selection.json`).
- [x] In-container build check: canary zip has expected members, `parameters.engine_git_sha=db899fd375b1c59585edab2d57864b46f4f7e60d`, `parameters.tier_id=fl_meg_12d_sens_p06_paxv_station_lots_continuous`, `num_agents=7000`, and seed 1020931 resolved in the station_lots_continuous tier.
- [x] Full-length canary.
- [x] AWS canary child inspected.
- [x] ETA reported.
- [ ] User approved array.

## AWS Batch pins

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver03@sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a`
- `ENGINE_GIT_SHA`: `db899fd375b1c59585edab2d57864b46f4f7e60d`
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/`

## Canaries

- meg `station_lots_continuous` index 0: Batch job `7d205140-f72c-42ae-834a-bc29be879d89`, jobdef `picard-noro-supply-solver-screen-03:1`, image digest `sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a`. Wall 1805 s. Zip `fl_norovirus_mega_cruise_5000_dose7p57_rung-shipped_nsf29_bp25c30_n7000_ep288_syndromic_comp65_s1020931.zip` (132,443,423 bytes); members `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_meg_12d_sens_p06_paxv_station_lots_continuous`; `engine_git_sha=db899fd375b1c59585edab2d57864b46f4f7e60d`; `hand_occupancy.counters.continuous_path_calls=361620`; derived attack_rate 0.0821, passenger reported-case AR 0.0445, crew reported-case AR 0.0148, `vsp_trigger_epoch=75`; `mechanisms.common_source_events=511`, `common_source_takers=15984`, provisioned_source `n_contaminated=3`.

ETA basis: 88 cells; canary wall 1805 s (30.1 min) for the continuous station_lots cell. Using ~44.1 vCPU-hours total and the campaign compute environment (`picard-abm-campaign-spot`, max 256 vCPU, desired 32), expect roughly 1.5-2.5 h depending on Spot concurrency; array submission is held for user approval.

## Measurements

pending
